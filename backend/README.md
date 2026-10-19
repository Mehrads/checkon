# Backend

FastAPI backend from the Full Stack FastAPI Template, plus the compliance core. Steps 1–5 of `../04-V1-Scope.md`: the rule pack, the rule engine, the normaliser, the money parser, the Inspector, the Refiner and the free-check API.

- `app/api/routes/checks.py`: `POST /api/v1/inspect`, `/refine`, `/answers`, `/patches/accept`. Checks live in memory for an hour (`app/api/check_store.py`).
- `app/compliance/answers.py`: answers to questions re-run the rules in code, with no LLM call.

- `rulepacks/CA-ON/rules.yaml`: the rules, with citations, effective dates, params, messages and questions.
- `rulepacks/CA-ON/tests/`: table-driven rule cases (Technical Design §8, layer 1).
- `app/compliance/checks.py`: one pure function per rule check.
- `app/compliance/engine.py`: applicability gate, content rules, report.
- `app/compliance/normalise.py`: pasted text to normalised text, with an offset map back to the original, sections and sentences.
- `app/compliance/money.py`: the deterministic pay parser, the second reading checked against the LLM.
- `app/compliance/inspector.py`: text in, report out. Calls `extraction.py` (facts, span checks, pay cross-check) and `classification.py` (labels, keyword safety net) through `llm.py`.
- `app/compliance/refiner.py`: one patch per failing finding, applied together, re-inspected and checked against acceptance tests 1–5; LLM rewrites get one retry, anything still failing is dropped with guidance.
- `rulepacks/CA-ON/wording.yaml`: the wording library (draft, needs lawyer sign-off).
- `prompts/`: the extraction, classification and rewrite prompts. Their hash is the `prompts` version in every report.

Run the tests (the live API tests are skipped; `tests/api` and `tests/crud` need Postgres, see `../README.md`):

```bash
uv run pytest
```

Run a real inspection and refinement against the Claude API (a few cents at most):

```bash
RUN_LIVE_LLM=1 uv run pytest tests/test_live.py -v
```

It needs `ANTHROPIC_API_KEY` set in your shell.
