# Backend

Compliance core for the Ontario job posting checker. Step 1 of `../04-V1-Scope.md`: the rule pack and the rule engine, with no LLM.

- `rulepacks/CA-ON/rules.yaml`: the rules, with citations, effective dates, params, messages and questions.
- `rulepacks/CA-ON/tests/`: table-driven rule cases (Technical Design §8, layer 1).
- `app/compliance/checks.py`: one pure function per rule check.
- `app/compliance/engine.py`: applicability gate, content rules, report.

Run the tests:

```bash
uv run pytest
```
