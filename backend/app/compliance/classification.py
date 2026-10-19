"""Sentence classification with constrained labels (Technical Design §4, step 5).

v1 sends every label to Haiku 5.5 directly; the Jev cascade is not in v1 (04-V1-Scope.md, section 4).
The prompt carries each rule's citation and labelled examples from the rule pack, never a paraphrase of the law.
"""

import re
from typing import Literal

from pydantic import BaseModel

from app.compliance.extraction import PROMPTS_DIR
from app.compliance.llm import LLMError, ModelSettings, StructuredLLM
from app.compliance.normalise import NormalisedText
from app.compliance.rulepack import Rule, RulePack

# Keyword safety net: sentences the extraction may have missed still get a Canadian-experience label.
SAFETY_NET = re.compile(r"canad|local|domestic|ontario|in-country", re.IGNORECASE)


class CexLabel(BaseModel):
    sentence: int
    label: Literal["violation", "borderline", "ok"]
    reason: str


class VacancyLabel(BaseModel):
    sentence: int
    label: Literal["existing", "not_existing", "vague", "none"]
    reason: str


class AILabel(BaseModel):
    sentence: int
    label: Literal["uses_ai", "no_ai", "none"]
    reason: str


class Classification(BaseModel):
    canadian_experience: list[CexLabel]
    vacancy: list[VacancyLabel]
    ai: list[AILabel]


TASKS = {"canadian_experience": "ON-CEX-01", "vacancy": "ON-VAC-01", "ai": "ON-AI-01"}


def safety_net(doc: NormalisedText) -> set[int]:
    return {s.id for s in doc.sentences if SAFETY_NET.search(s.text)}


def _rule_block(rule: Rule) -> str:
    labels = list(dict.fromkeys(example["label"] for example in rule.examples))
    lines = [f"Rule {rule.id}: {rule.citation}", f"Labels: {', '.join(labels)}", "Examples:"]
    lines += [f'- "{e["text"]}" -> {e["label"]}: {e["reason"]}' for e in rule.examples]
    return "\n".join(lines)


def system_prompt(pack: RulePack) -> str:
    prompt = (PROMPTS_DIR / "classify.md").read_text(encoding="utf-8")
    rules = {rule.id: rule for rule in pack.rules}
    for rule_id in TASKS.values():
        prompt = prompt.replace("{{" + rule_id + "}}", _rule_block(rules[rule_id]))
    return prompt


def _missing(result: Classification, wanted: dict[str, list[int]]) -> dict[str, list[int]]:
    missing = {}
    for task, ids in wanted.items():
        labelled = {label.sentence for label in getattr(result, task)}
        if gaps := [i for i in ids if i not in labelled]:
            missing[task] = gaps
    return missing


def classify(
    doc: NormalisedText,
    wanted: dict[str, list[int]],
    pack: RulePack,
    llm: StructuredLLM,
    settings: ModelSettings,
) -> Classification:
    """Label every wanted sentence once; retry once for gaps, then fail closed."""
    if not any(wanted.values()):
        return Classification(canadian_experience=[], vacancy=[], ai=[])
    texts = {s.id: s.text for s in doc.sentences}
    blocks = [f"{task}:\n" + "\n".join(f"[{i}] {texts[i]}" for i in ids) for task, ids in wanted.items() if ids]
    user = "<sentences>\n" + "\n\n".join(blocks) + "\n</sentences>"
    system = system_prompt(pack)

    result = llm.parse(system=system, user=user, schema=Classification, settings=settings)
    if missing := _missing(result, wanted):
        gaps = "; ".join(f"{task}: " + ", ".join(f"[{i}]" for i in ids) for task, ids in missing.items())
        retry = f"{user}\n\nA previous answer left these sentences without a label: {gaps}. Label every listed sentence."
        result = llm.parse(system=system, user=retry, schema=Classification, settings=settings)
        if missing := _missing(result, wanted):
            raise LLMError(f"sentences left unlabelled after a retry: {missing}")
    return result
