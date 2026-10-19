# Backend

Compliance core for the Ontario job posting checker. Steps 1–2 of `../04-V1-Scope.md`: the rule pack, the rule engine, the normaliser and the money parser, with no LLM.

- `rulepacks/CA-ON/rules.yaml`: the rules, with citations, effective dates, params, messages and questions.
- `rulepacks/CA-ON/tests/`: table-driven rule cases (Technical Design §8, layer 1).
- `app/compliance/checks.py`: one pure function per rule check.
- `app/compliance/engine.py`: applicability gate, content rules, report.
- `app/compliance/normalise.py`: pasted text to normalised text, with an offset map back to the original, sections and sentences.
- `app/compliance/money.py`: the deterministic pay parser, the second reading checked against the LLM.

Run the tests:

```bash
uv run pytest
```
