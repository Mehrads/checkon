"""Answers to needs_input questions: they change the context or settle a pay reading, never the text.

Verdicts are re-run in code from the stored facts, so answering costs no LLM call.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.compliance.engine import evaluate
from app.compliance.inspector import Inspection, content_hash
from app.compliance.models import Context, PayKind
from app.compliance.rulepack import RulePack


class Answers(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meets_headcount_threshold: bool | None = None
    specific_position: bool | None = None
    internal_only: bool | None = None
    work_in_ontario: bool | None = None
    uses_ai_in_hiring: bool | None = None
    existing_vacancy: bool | None = None
    pay_exemption_confirmed: bool | None = None
    hours_per_week: Decimal | None = Field(default=None, gt=0, le=80)
    pay_reading: Literal[0, 1] | None = None  # 0: the first reading, 1: the second


def apply_answers(
    inspection: Inspection, ctx: Context, answers: Answers, pack: RulePack, posting_date: date
) -> tuple[Inspection, Context]:
    ctx = ctx.model_copy(update=answers.model_dump(exclude_none=True, exclude={"pay_reading"}))
    facts = inspection.facts
    if answers.pay_reading is not None:
        pay = []
        for mention in facts.pay:
            if mention.kind == PayKind.WAGE and not mention.parsers_agree:
                second = mention.alternate
                if answers.pay_reading == 0:
                    mention = mention.model_copy(update={"parsers_agree": True})
                elif second is not None and second.unit is not None:
                    update = {"min": second.min, "max": second.max, "unit": second.unit, "parsers_agree": True}
                    mention = mention.model_copy(update=update)
            pay.append(mention)
        facts = facts.model_copy(update={"pay": pay})
    report = evaluate(facts, ctx, pack, posting_date)
    versions = {**inspection.report.versions, **report.versions, "profile_hash": content_hash(ctx.model_dump_json())}
    report = report.model_copy(update={"versions": versions})
    return replace(inspection, facts=facts, report=report), ctx
