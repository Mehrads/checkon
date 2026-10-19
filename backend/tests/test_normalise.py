"""Normaliser: folding, offsets back to the original, sections and sentences."""

import pytest

from app.compliance.normalise import normalise

POSTING = (
    "Payroll Specialist\r\n"
    "Mississauga, ON  (hybrid)\r\n"
    "\r\n"
    "\r\n"
    "About the role\r\n"
    "We’re growing. You’ll run payroll for 400 employees.\r\n"
    "\r\n"
    "Requirements:\r\n"
    "• 2+ years of Canadian payroll experience\r\n"
    "• P.Eng. designation preferred — or CPP certification.\r\n"
    "- Excellent communication skills\r\n"
    "\r\n"
    "Compensation\r\n"
    "Salary: $60,000 – $80,000 per year…\r\n"
)


@pytest.fixture(scope="module")
def doc():
    return normalise(POSTING)


def test_folds_spaces_quotes_dashes_and_line_endings(doc) -> None:
    assert "\r" not in doc.text
    assert " " not in doc.text
    assert "We're growing." in doc.text
    assert "$60,000 - $80,000 per year..." in doc.text
    assert "Mississauga, ON (hybrid)" in doc.text


def test_keeps_at_most_one_blank_line(doc) -> None:
    assert "\n\n\n" not in doc.text
    assert doc.text.startswith("Payroll Specialist\nMississauga")


def test_every_character_maps_back_to_its_source(doc) -> None:
    folds = {"'": "’", '"': "”", "-": "–—", " ": "  ", ".": "…", "\n": "\n"}
    assert len(doc.offsets) == len(doc.text) + 1
    assert doc.offsets[-1] == len(POSTING)
    for i, ch in enumerate(doc.text):
        source = POSTING[doc.offsets[i]]
        assert source == ch or source in folds.get(ch, ""), (i, ch, source)


def test_offsets_increase(doc) -> None:
    assert all(a <= b for a, b in zip(doc.offsets, doc.offsets[1:]))


def test_sentence_maps_back_to_the_pasted_text(doc) -> None:
    sentence = next(s for s in doc.sentences if "Canadian" in s.text)
    assert sentence.text == "2+ years of Canadian payroll experience"
    assert doc.original_slice(sentence.span) == "2+ years of Canadian payroll experience"


def test_ellipsis_span_maps_to_the_single_source_character(doc) -> None:
    sentence = next(s for s in doc.sentences if s.text.startswith("Salary"))
    assert sentence.text.endswith("per year...")
    assert doc.original_slice(sentence.span) == "Salary: $60,000 – $80,000 per year…"


def test_bullets_are_not_part_of_the_sentence(doc) -> None:
    texts = [s.text for s in doc.sentences]
    assert "Excellent communication skills" in texts
    assert not any(t.startswith(("•", "-")) for t in texts)


def test_splits_sentences_within_a_line(doc) -> None:
    texts = [s.text for s in doc.sentences]
    assert "We're growing." in texts
    assert "You'll run payroll for 400 employees." in texts


def test_dotted_abbreviations_do_not_split_a_sentence(doc) -> None:
    texts = [s.text for s in doc.sentences]
    assert "P.Eng. designation preferred - or CPP certification." in texts


def test_sections_follow_headings(doc) -> None:
    headings = [s.heading.value if s.heading else None for s in doc.sections]
    assert headings == [None, "About the role", "Requirements:", "Compensation"]
    by_id = {s.id: s for s in doc.sections}
    canadian = next(s for s in doc.sentences if "Canadian" in s.text)
    assert by_id[canadian.section].heading.value == "Requirements:"


def test_section_spans_cover_their_sentences(doc) -> None:
    for sentence in doc.sentences:
        start, end = doc.sections[sentence.section].span
        assert start <= sentence.span[0] and sentence.span[1] <= end


def test_sentence_ids_and_spans_are_stable() -> None:
    first, second = normalise(POSTING), normalise(POSTING)
    assert first == second
    assert [s.id for s in first.sentences] == list(range(len(first.sentences)))


def test_short_line_without_heading_words_is_a_sentence() -> None:
    doc = normalise("Requirements\nExcel and SQL\nStrong attention to detail")
    assert [s.text for s in doc.sentences] == ["Excel and SQL", "Strong attention to detail"]


def test_uppercase_line_is_a_heading() -> None:
    doc = normalise("WHAT WE OFFER\nA pension plan.")
    assert doc.sections[0].heading is not None
    assert doc.sections[0].heading.value == "WHAT WE OFFER"


def test_zero_width_characters_are_removed() -> None:
    doc = normalise("Pay​ is $25﻿/hour.")
    assert doc.text == "Pay is $25/hour."
    assert doc.original_slice((0, len(doc.text))) == "Pay​ is $25﻿/hour."


def test_empty_input() -> None:
    doc = normalise(" \r\n\t ")
    assert doc.text == ""
    assert doc.sentences == []
    assert doc.sections == []
    assert doc.offsets == [5]
