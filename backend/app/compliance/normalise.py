"""Normalise pasted posting text and split it into sections and sentences (Technical Design §4, step 1).

The normalised text is what the LLM sees and what every span points into. `offsets` maps each of its
characters back to the pasted original, so evidence can be highlighted where the user wrote it.
v1 takes plain text; HTML input arrives with the extension (phase 3).
"""

import re
import unicodedata
import warnings
from functools import cache

from pydantic import BaseModel, ConfigDict

with warnings.catch_warnings():  # pysbd 0.3.4 has unescaped regex strings; the warnings are harmless
    warnings.simplefilter("ignore", SyntaxWarning)
    import pysbd

from app.compliance.models import Span, TextFact

# One-character folds: odd spaces, invisible characters, curly quotes and dash variants.
_FOLD: dict[str, str] = {
    **dict.fromkeys("\t              　", " "),
    **dict.fromkeys("​‌‍⁠﻿­", ""),
    **dict.fromkeys("‘’‚‛′", "'"),
    **dict.fromkeys("“”„‟″", '"'),
    **dict.fromkeys("‐‑‒–—―−", "-"),
    **dict.fromkeys("  \x0b\x0c\x85", "\n"),
    "…": "...",
}

_BULLET = re.compile(r"(?:[-*•·▪◦‣○●■□➢➤✓✔]|\d{1,2}[.)]|[a-z][.)])\s+")
_HEADING_WORDS = re.compile(
    r"(about(\s+(us|you|the\s+\w+))?|(key\s+)?responsibilities|requirements|((preferred|required)\s+)?qualifications"
    r"|duties|benefits|perks|compensation|salary|pay|how\s+to\s+apply|nice\s+to\s+have|skills|education|overview"
    r"|summary|job\s+(summary|description|details)|what\s+(you'll|you\s+will|we\s+offer)(\s+(do|bring|need))?"
    r"|who\s+you\s+are|why\s+join\s+us|equal\s+(opportunity|employment)|accommodations?|accessibility|location|schedule)",
    re.IGNORECASE,
)
# Dotted abbreviations such as P.Eng., B.Sc. or Ph.D., which pySBD would otherwise split.
_ABBREVIATION = re.compile(r"\b[A-Za-z]{1,2}\.(?:[A-Za-z]{1,4}\.)+")
_MASK = ""  # private-use character, same length as the dot it hides


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Sentence(_Frozen):
    id: int
    span: Span
    text: str
    section: int


class Section(_Frozen):
    id: int
    heading: TextFact | None
    span: Span


class NormalisedText(_Frozen):
    original: str
    text: str
    offsets: list[int]  # offsets[i] is the index in `original` of text[i]; the last entry is len(original)
    sections: list[Section]
    sentences: list[Sentence]

    def to_original(self, span: Span) -> Span:
        start, end = span
        if end <= start:
            return (self.offsets[start], self.offsets[start])
        return (self.offsets[start], self.offsets[end - 1] + 1)

    def original_slice(self, span: Span) -> str:
        start, end = self.to_original(span)
        return self.original[start:end]


def _fold(original: str) -> list[tuple[str, int]]:
    chars: list[tuple[str, int]] = []
    for index, ch in enumerate(original):
        if ch == "\r":
            if original[index + 1 : index + 2] != "\n":
                chars.append(("\n", index))
            continue
        folded = _FOLD.get(ch, ch)
        if folded == ch and ch != "\n" and unicodedata.category(ch) == "Cc":
            continue
        chars.extend((out, index) for out in folded)
    return chars


def fold(text: str) -> str:
    """The character folds normalise() applies, for a short text such as a rewritten sentence."""
    return "".join(ch for ch, _ in _fold(text))


def _tidy(chars: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Collapse runs of spaces, trim each line, keep at most one blank line, trim the ends."""
    out: list[tuple[str, int]] = []
    for ch, index in chars:
        if ch == " ":
            if out and out[-1][0] not in " \n":
                out.append((ch, index))
        elif ch == "\n":
            while out and out[-1][0] == " ":
                out.pop()
            if not out or (len(out) >= 2 and out[-1][0] == "\n" and out[-2][0] == "\n"):
                continue
            out.append((ch, index))
        else:
            out.append((ch, index))
    while out and out[-1][0] in " \n":
        out.pop()
    return out


def _is_heading(line: str) -> bool:
    if not line or len(line) > 80:
        return False
    if line.endswith(":"):
        return True
    bare = line.strip("*#_ ")
    if len(bare.split()) > 6 or bare[-1:] in ".!?,;":
        return False
    letters = [ch for ch in bare if ch.isalpha()]
    return (bool(letters) and bare.isupper()) or bool(_HEADING_WORDS.fullmatch(bare))


def _mask_abbreviations(line: str) -> str:
    def mask(match: re.Match[str]) -> str:
        token = match.group()
        after = line[match.end() :]
        sentence_ends = after == "" or re.match(r"\s+[A-Z]", after) is not None
        inner = token[:-1].replace(".", _MASK)
        return inner + ("." if sentence_ends else _MASK)

    return _ABBREVIATION.sub(mask, line)


@cache
def _segmenter() -> pysbd.Segmenter:
    return pysbd.Segmenter(language="en", clean=False)


def _split_sentences(line: str) -> list[Span]:
    """Sentence spans within one line; the masked copy has the same length, so spans carry over."""
    masked = _mask_abbreviations(line)
    spans: list[Span] = []
    cursor = 0
    for piece in _segmenter().segment(masked):
        piece = piece.strip()
        if not piece:
            continue
        start = masked.find(piece, cursor)
        if start < 0:  # pySBD changed the text; keep the rest of the line whole
            rest = line[cursor:].strip()
            if rest:
                start = line.index(rest, cursor)
                spans.append((start, start + len(rest)))
            return spans
        spans.append((start, start + len(piece)))
        cursor = start + len(piece)
    return spans


def normalise(original: str) -> NormalisedText:
    chars = _tidy(_fold(original))
    text = "".join(ch for ch, _ in chars)
    offsets = [index for _, index in chars] + [len(original)]

    sections: list[Section] = []
    sentences: list[Sentence] = []
    section_start = 0
    heading: TextFact | None = None

    def close_section(end: int) -> None:
        has_sentences = any(sentence.section == len(sections) for sentence in sentences)
        if heading or has_sentences:
            sections.append(Section(id=len(sections), heading=heading, span=(section_start, end)))

    line_start = 0
    for line in text.split("\n"):
        line_end = line_start + len(line)
        bullet = _BULLET.match(line)
        content_start = line_start + (bullet.end() if bullet else 0)
        content = text[content_start:line_end]
        if content and not bullet and _is_heading(content):
            close_section(len(text[:line_start].rstrip()))
            section_start = line_start
            heading = TextFact(value=content, span=(line_start, line_end))
        elif content:
            for start, end in _split_sentences(content):
                span = (content_start + start, content_start + end)
                sentences.append(
                    Sentence(id=len(sentences), span=span, text=text[span[0] : span[1]], section=len(sections))
                )
        line_start = line_end + 1
    close_section(len(text))

    return NormalisedText(original=original, text=text, offsets=offsets, sections=sections, sentences=sentences)
