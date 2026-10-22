"""The posting's application form: ESA s. 8.3 (1) bars Canadian-experience requirements "in the posting or in any
associated application form" (Technical Design §4, inputs).

The form arrives as text, pasted on the website or read from the page by the extension: one question per line,
its answer options on the lines after it, each starting with "-" (or indented). A trailing "*" or "(required)"
marks a required question, "(optional)" an optional one. Each question is labelled once with the rule pack's
form examples; the rule engine decides the verdict.
"""

import re
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel

from app.compliance.classification import rule_block
from app.compliance.extraction import PROMPTS_DIR
from app.compliance.llm import LLMError, ModelSettings, StructuredLLM
from app.compliance.models import FormQuestion, Span
from app.compliance.normalise import fold
from app.compliance.rulepack import Rule, RulePack

MAX_FORM_CHARS = 4000  # Technical Design §11
RULE = "ON-CEX-01"

_NUMBER = re.compile(r"^(?:\d{1,2}[.)]|Q\d{1,2}[.):]?)\s+")
# Not "*": a leading "*" marks a required question ("* Email").
_OPTION = re.compile(r"^(?:[-•·▪◦‣○●■□☐➢➤]|[a-z][.)]|\(\s?\)|\[\s?\])\s*")
_REQUIRED = re.compile(r"\s*(?:\*+|\((?:required|mandatory)\)|\[(?:required|mandatory)\])$", re.IGNORECASE)
_OPTIONAL = re.compile(r"\s*(?:\(optional\)|\[optional\])$", re.IGNORECASE)


@dataclass
class _Question:
    text: str
    start: int
    end: int
    required: bool | None
    options: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FormText:
    text: str  # the normalised form: every question's span points into it
    questions: list[_Question]


def _marks(line: str) -> tuple[str, bool | None]:
    """The question without its required or optional mark, and what the mark says."""
    if _OPTIONAL.search(line):
        return _OPTIONAL.sub("", line), False
    if _REQUIRED.search(line):
        return _REQUIRED.sub("", line), True
    if line.startswith("*"):
        return line.lstrip("* "), True
    return line, None


def parse_form(raw: str) -> FormText:
    text = "\n".join(line.rstrip() for line in fold(raw).replace("\t", " ").split("\n")).strip("\n")
    questions: list[_Question] = []
    position = 0
    for line in text.split("\n"):
        start, end = position, position + len(line)
        position = end + 1
        content = line.strip()
        if not content:
            continue
        indent = len(line) - len(line.lstrip())
        option = _OPTION.match(content)
        if questions and (option or indent):
            question = questions[-1]
            question.options.append(content[option.end() :].strip() if option else content)
            question.end = end
            continue
        body, required = _marks(_NUMBER.sub("", content[option.end() :] if option else content).strip())
        if body:
            questions.append(_Question(text=body, start=start + indent, end=end, required=required))
    return FormText(text=text, questions=questions)


class FormLabel(BaseModel):
    question: int
    label: Literal["violation", "borderline", "ok"]
    reason: str


class FormLabels(BaseModel):
    questions: list[FormLabel]


def _rule(pack: RulePack) -> Rule:
    rule = next(r for r in pack.rules if r.id == RULE)
    if rule.form is None:
        raise ValueError(f"{RULE} has no form block in the rule pack")
    return rule


def system_prompt(pack: RulePack) -> str:
    rule = _rule(pack)
    block = rule_block(rule.model_copy(update={"examples": rule.form.examples if rule.form else []}))
    return (PROMPTS_DIR / "classify_form.md").read_text(encoding="utf-8").replace("{{" + RULE + "}}", block)


def _user(form: FormText) -> str:
    items = []
    for number, question in enumerate(form.questions, start=1):
        options = f"\nOptions: {' | '.join(question.options)}" if question.options else ""
        items.append(f"[{number}] {question.text}{options}")
    return "<questions>\n" + "\n".join(items) + "\n</questions>"


def classify_form(form: FormText, pack: RulePack, llm: StructuredLLM, settings: ModelSettings) -> list[FormQuestion]:
    """Label every question once; retry once for gaps, then fail closed."""
    wanted = set(range(1, len(form.questions) + 1))
    system, user = system_prompt(pack), _user(form)
    result = llm.parse(system=system, user=user, schema=FormLabels, settings=settings)
    if missing := wanted - {label.question for label in result.questions}:
        gaps = ", ".join(f"[{number}]" for number in sorted(missing))
        retry = f"{user}\n\nA previous answer left these questions without a label: {gaps}. Label every listed question."
        result = llm.parse(system=system, user=retry, schema=FormLabels, settings=settings)
        if missing := wanted - {label.question for label in result.questions}:
            raise LLMError(f"questions left unlabelled after a retry: {sorted(missing)}")
    labels: dict[int, FormLabel] = {}
    for label in result.questions:
        labels.setdefault(label.question, label)
    found = []
    for number, question in enumerate(form.questions, start=1):
        span: Span = (question.start, question.end)
        found.append(FormQuestion(
            id=number, text=question.text, span=span, options=question.options, required=question.required,
            cex_label=labels[number].label, reason=labels[number].reason,
        ))  # fmt: skip
    return found
