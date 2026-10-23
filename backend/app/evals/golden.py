"""Run the golden set and score it against the release gates (Technical Design §8).

    uv run python -m app.evals.golden --dry-run           # validate every case and count them; no API calls
    uv run python -m app.evals.golden                     # every labelled case, once
    uv run python -m app.evals.golden --runs 3 --refine   # every gate: 3 runs for consistency, --refine for the Refiner
    uv run python -m app.evals.golden --only syn-pay      # the cases whose id starts with this

Each case goes through the Inspector as a paste check would, with the case's context as the employer's answers;
with --refine, failing postings go through the Refiner too. Writes evals/reports/<timestamp>.md and .json and
prints the gate table. Nothing goes to Langfuse.
"""

import argparse
import json
import re
import statistics
import sys
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

import anthropic

from app.compliance.inspector import InputRefused, inspect
from app.compliance.llm import AnthropicLLM, SpendMeter, StructuredLLM
from app.compliance.models import Verdict
from app.compliance.refiner import Patch, refine
from app.compliance.rulepack import RulePack, load_pack
from app.core.config import settings
from app.evals.cases import GOLDEN_DIR, RULES, SLICES, TARGETS, Case, load_cases

REPORTS_DIR = GOLDEN_DIR.parent / "reports"
RELEASE_LABELLERS = 2  # people, not the drafting model
GROUPS = {"pay, vacancy and AI": ("ON-PAY-01", "ON-PAY-02", "ON-VAC-01", "ON-AI-01"), "Canadian experience": ("ON-CEX-01",)}
# Decided by code from the money parser's readings; the other rules rest on the model's labels.
CODE_RULES = ("ON-PAY-01", "ON-PAY-02")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_WORD = re.compile(r"[\w&'-]+")
Outcome = Literal["pass", "fail", "not measured"]


@dataclass
class Run:
    verdicts: dict[str, str] = field(default_factory=dict)  # rule to verdict; empty when refused or failed
    refused: str | None = None
    error: str | None = None
    usd: float = 0.0
    seconds: float = 0.0
    fixable: list[str] = field(default_factory=list)  # failing rules the Refiner could fix without the employer
    fixed: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)  # model rewrites with a number or name the posting doesn't have

    def verdict(self, rule: str) -> str:
        return self.verdicts.get(rule) or ("refused" if self.refused else "error")


@dataclass
class Result:
    case: Case
    runs: list[Run]


@dataclass
class Gate:
    name: str
    target: str
    value: str
    outcome: Outcome


def humans(case: Case) -> int:
    return len([name for name in case.labelled_by if name.lower() != "claude"])


def added_facts(source: str, patches: Iterable[Patch]) -> list[str]:
    """Model rewrites that bring in a number or a name the posting doesn't have (the Refiner's own check drops
    these, so any found here is a bug)."""
    numbers, words = set(_NUMBER.findall(source)), set(_WORD.findall(source))
    found = []
    for patch in patches:
        if patch.writer != "llm" or not patch.after:
            continue
        names = {word for word in _WORD.findall(patch.after)[1:] if word[0].isupper()}  # not the first word
        new = (set(_NUMBER.findall(patch.after)) - numbers) | (names - words)
        if new:
            found.append(f"{patch.rule}: {patch.after!r} adds {sorted(new)}")
    return found


def run_case(case: Case, pack: RulePack, llm: StructuredLLM, refine_too: bool = False) -> Run:
    started = time.monotonic()
    meter = getattr(llm, "meter", None)
    run = Run()
    try:
        inspection = inspect(case.text, case.ctx(), case.posted, pack, llm)
        run.verdicts = {result.rule: result.verdict.value for result in inspection.report.results}
        if refine_too and Verdict.FAIL.value in run.verdicts.values():
            refinement = refine(inspection, inspection.context, case.posted, pack, llm)
            after = {result.rule: result.verdict for result in refinement.report.results}
            for rule, verdict in run.verdicts.items():
                if verdict == Verdict.FAIL and after.get(rule) != Verdict.NEEDS_INPUT:  # not waiting on the employer
                    run.fixable.append(rule)
                    if after.get(rule) in (Verdict.PASS, Verdict.NOT_APPLICABLE):
                        run.fixed.append(rule)
            run.added = added_facts(case.text, refinement.patches)
    except InputRefused as error:
        run.refused = error.reason
    except Exception as error:  # one case's failure is reported, not fatal to a 300-case run
        run.error = f"{type(error).__name__}: {error}"[:300]
    run.usd = float(meter.usd) if meter is not None else 0.0
    run.seconds = round(time.monotonic() - started, 2)
    return run


def run_all(cases: list[Case], llm: Callable[[], StructuredLLM], runs: int = 1, refine_too: bool = False,
            workers: int = 4, pack: RulePack | None = None) -> list[Result]:  # fmt: skip
    pack = pack or load_pack("CA-ON")
    jobs = [(case, n) for n in range(runs) for case in cases]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        done = list(pool.map(lambda job: run_case(job[0], pack, llm(), refine_too and job[1] == 0), jobs))
    by_case: dict[str, list[Run]] = {case.id: [] for case in cases}
    for (case, _), run in zip(jobs, done, strict=True):
        by_case[case.id].append(run)
    return [Result(case, by_case[case.id]) for case in cases]


# Scoring


def _pct(part: int, whole: int) -> str:
    return f"{part / whole:.1%} ({part}/{whole})" if whole else "no cases"


def _gate(name: str, target: str, part: int, whole: int, minimum: float) -> Gate:
    if not whole:
        return Gate(name, target, "no cases", "not measured")
    return Gate(name, target, _pct(part, whole), "pass" if part / whole >= minimum else "fail")


@dataclass
class Score:
    gates: list[Gate]
    rules: dict[str, dict[str, int]]  # rule to tp, fn, fp, agree, labelled
    mismatches: list[tuple[str, str, str, str]]  # case, rule, label, verdict (first run)
    refusals: list[tuple[str, str, str]]  # case, expected, got
    errors: list[tuple[str, str]]
    added: list[tuple[str, str]]
    counts: dict[str, dict[str, int]]  # slice to cases, labelled, by two people, target
    usd: float
    p95_seconds: float


def score(results: list[Result]) -> Score:
    scored = [r for r in results if r.case.labelled]
    first = {r.case.id: r.runs[0] for r in scored}
    rules = {rule: {"tp": 0, "fn": 0, "fp": 0, "agree": 0, "labelled": 0} for rule in RULES}
    mismatches, refusals = [], []
    for result in scored:
        case, run = result.case, first[result.case.id]
        if case.refusal is not None:
            if run.refused != case.refusal:
                refusals.append((case.id, case.refusal, run.refused or "not refused"))
            continue
        for rule, label in case.labels.items():
            got, tally = run.verdict(rule), rules[rule]
            tally["labelled"] += 1
            tally["agree"] += got == label
            tally["tp"] += label == "fail" and got == "fail"
            tally["fn"] += label == "fail" and got != "fail"
            tally["fp"] += label != "fail" and got == "fail"
            if got != label:
                mismatches.append((case.id, rule, label.value, got))

    gates = []
    counts: dict[str, dict[str, int]] = {
        name: {
            "cases": sum(r.case.slice == name for r in results),
            "labelled": sum(r.case.slice == name for r in scored),
            "by_two": sum(r.case.slice == name and humans(r.case) >= RELEASE_LABELLERS for r in scored),
            "target": TARGETS[name],
        }
        for name in SLICES
    }
    complete = sum(min(c["by_two"], c["target"]) for c in counts.values())
    gates.append(_gate("Golden set labelled by two people", "300 cases", complete, sum(TARGETS.values()), 1.0))
    for (group, members), minimum in zip(GROUPS.items(), (0.98, 0.95), strict=True):
        tp = sum(rules[rule]["tp"] for rule in members)
        fn = sum(rules[rule]["fn"] for rule in members)
        gates.append(_gate(f"Recall on violations: {group}", f">= {minimum:.0%}", tp, tp + fn, minimum))
    precisions = [(rules[r]["tp"], rules[r]["tp"] + rules[r]["fp"], r) for r in RULES if rules[r]["tp"] + rules[r]["fp"]]
    if precisions:
        tp, flagged, rule = min(precisions, key=lambda p: p[0] / p[1])
        gates.append(_gate(f"Precision on fail, every rule (lowest: {rule})", ">= 90%", tp, flagged, 0.90))
    else:
        gates.append(Gate("Precision on fail, every rule", ">= 90%", "no fails", "not measured"))

    refined = [run for run in first.values() if run.fixable or run.added]
    fixable = sum(len(run.fixable) for run in refined)
    gates.append(_gate("Refiner: fixable failures fixed and verified", ">= 95%", sum(len(r.fixed) for r in refined), fixable, 0.95))
    added = [(case_id, line) for case_id, run in first.items() for line in run.added]
    gates.append(Gate("Refiner: rewrites that add a fact", "0", str(len(added)) if fixable else "no rewrites",
                      ("pass" if not added else "fail") if fixable else "not measured"))  # fmt: skip

    repeated = [r for r in scored if len(r.runs) >= 3 and r.case.refusal is None]
    for name, which, minimum in (("code rules", CODE_RULES, 1.0), ("overall", RULES, 0.99)):
        pairs = [(r, rule) for r in repeated for rule in which]
        same = sum(len({run.verdict(rule) for run in r.runs}) == 1 for r, rule in pairs)
        gates.append(_gate(f"Same verdicts across 3 runs: {name}", f">= {minimum:.0%}", same, len(pairs), minimum))

    slice_of = {r.case.id: r.case.slice for r in scored}
    injected = [m for m in mismatches if slice_of[m[0]] == "adversarial"]
    adversarial = sum(len(r.case.labels) for r in scored if r.case.slice == "adversarial")
    gates.append(Gate("Verdict changes caused by injected text", "0", str(len(injected)) if adversarial else "no cases",
                      ("pass" if not injected else "fail") if adversarial else "not measured"))  # fmt: skip

    runs = [run for r in results for run in r.runs]
    errors = [(r.case.id, run.error) for r in results for run in r.runs if run.error]
    seconds = sorted(run.seconds for run in runs if not run.error)
    p95 = statistics.quantiles(seconds, n=20)[-1] if len(seconds) >= 2 else (seconds[0] if seconds else 0.0)
    return Score(gates, rules, mismatches, refusals, errors, added, counts, round(sum(r.usd for r in runs), 4), p95)


# Report


def markdown(score: Score, args: str) -> str:
    lines = [f"# Golden set run, {datetime.now():%Y-%m-%d %H:%M}", "", f"`{args}`", ""]
    lines += ["| Gate | Target | Measured | Result |", "| --- | --- | --- | --- |"]
    lines += [f"| {g.name} | {g.target} | {g.value} | {g.outcome} |" for g in score.gates]
    lines += ["", f"Model fees: ${score.usd:.4f}. p95 time per case: {score.p95_seconds:.1f} s.", ""]
    lines += ["## Cases", "", "| Slice | Cases | Labelled | By two people | Target |", "| --- | --- | --- | --- | --- |"]
    lines += [f"| {n} | {c['cases']} | {c['labelled']} | {c['by_two']} | {c['target']} |" for n, c in score.counts.items()]
    lines += ["", "## Per rule (first run)", "", "| Rule | Labelled | Agree | Violations found | Missed | False fails |"]
    lines += ["| --- | --- | --- | --- | --- | --- |"]
    lines += [f"| {rule} | {c['labelled']} | {c['agree']} | {c['tp']} | {c['fn']} | {c['fp']} |" for rule, c in score.rules.items()]
    if score.mismatches:
        lines += ["", "## Disagreements with the labels", "", "| Case | Rule | Label | Checker |", "| --- | --- | --- | --- |"]
        lines += [f"| {case} | {rule} | {label} | {got} |" for case, rule, label, got in score.mismatches]
    if score.refusals:
        lines += ["", "## Refusals", ""] + [f"- {case}: expected {want}, got {got}" for case, want, got in score.refusals]
    if score.added:
        lines += ["", "## Rewrites that add a fact", ""] + [f"- {case}: {line}" for case, line in score.added]
    if score.errors:
        lines += ["", "## Errors", ""] + [f"- {case}: {error}" for case, error in score.errors]
    return "\n".join(lines) + "\n"


def write_report(score: Score, results: list[Result], args: str, directory: Path = REPORTS_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    stem = directory / datetime.now().strftime("%Y-%m-%d-%H%M%S")
    stem.with_suffix(".md").write_text(markdown(score, args), encoding="utf-8")
    data = {
        "args": args, "gates": [asdict(g) for g in score.gates], "rules": score.rules, "counts": score.counts,
        "usd": score.usd, "cases": {r.case.id: [asdict(run) for run in r.runs] for r in results},
    }  # fmt: skip
    stem.with_suffix(".json").write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")
    return stem.with_suffix(".md")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--runs", type=int, default=1, help="runs per case; the consistency gates need 3")
    parser.add_argument("--refine", action="store_true", help="also refine failing postings (the Refiner gates)")
    parser.add_argument("--only", default="", help="only cases whose id starts with this")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true", help="validate and count the cases; no API calls")
    args = parser.parse_args()

    cases = [c for c in load_cases() if c.id.startswith(args.only)]
    if args.dry_run:
        for name in SLICES:
            mine = [c for c in cases if c.slice == name]
            print(f"{name:13} {len(mine):4} cases  {sum(c.labelled for c in mine):4} labelled  "  # noqa: T201
                  f"{sum(humans(c) >= RELEASE_LABELLERS for c in mine):4} by two people  (target {TARGETS[name]})")
        return
    labelled = [c for c in cases if c.labelled]
    if not labelled:
        sys.exit("No labelled cases to run.")
    if not settings.ANTHROPIC_API_KEY:
        sys.exit("ANTHROPIC_API_KEY isn't set.")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    results = run_all(labelled, lambda: AnthropicLLM(client, meter=SpendMeter()), args.runs, args.refine, args.workers)
    result = score(results)
    path = write_report(result, results, " ".join(sys.argv[1:]))
    for gate in result.gates:
        print(f"{gate.outcome:12} {gate.name}: {gate.value} (target {gate.target})")  # noqa: T201
    print(f"Model fees ${result.usd:.4f}. Report: {path}")  # noqa: T201


if __name__ == "__main__":
    main()
