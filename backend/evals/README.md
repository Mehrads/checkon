# Golden set

The labelled postings behind the release gates (Technical Design §8, layer 2; 04-V1-Scope §3). Nothing ships until the gates pass on the full set: 300 English postings, each labelled per rule by two people.

| Slice | Target | What goes in it |
| --- | --- | --- |
| `real` | 150 | Ontario postings from public job boards (Greenhouse, Lever, Ashby, SmartRecruiters) and careers pages, collected with `app.evals.collect`. Never LinkedIn or Indeed scraping (PRD §7). |
| `synthetic` | 100 | Written cases, at least 20 per content rule (pay, vacancy, AI, Canadian experience): boundaries and rephrasings. |
| `out_of_scope` | 25 | Work outside Ontario (collected), internal-only postings, general recruitment campaigns, employers under 25. |
| `adversarial` | 25 | A labelled case with injected instructions or odd formatting (tables, bullets, HTML). Its labels are the original's, since the injection mustn't change a verdict. |

## Commands (in `backend/`)

```bash
uv run python -m app.evals.collect https://boards.greenhouse.io/<token> --max 5
uv run python -m app.evals.collect https://jobs.lever.co/<company> --outside-ontario --max 2
uv run python -m app.evals.golden --dry-run      # validate every case and show the counts; no API calls
uv run python -m app.evals.golden                # every labelled case once (needs ANTHROPIC_API_KEY)
uv run python -m app.evals.golden --runs 3 --refine   # the full gate run
```

The runner writes `evals/reports/<timestamp>.md` and `.json`. It never sends anything to Langfuse.

## A case

One file per posting: `golden/<slice>/<id>.yaml`, where the file name is the id (lowercase letters, digits, hyphens).

```yaml
id: syn-pay-02-width-over-cap
slice: synthetic
purpose: An annual range $1 over the $50,000 width limit.
posted: '2026-10-01'          # the day the rules are checked for (default 2026-10-01)
context:                      # the answers an employer gives in the check (Context fields)
  uses_ai_in_hiring: false
text: |
  Payroll Specialist
  ...
labels:
  ON-APPL-01: pass
  ON-APPL-02: pass
  ON-PAY-01: pass
  ON-PAY-02: fail
  ON-VAC-01: pass
  ON-AI-01: not_applicable
  ON-CEX-01: pass
labelled_by: [mehrad]
notes: ''
```

- **`context`** holds what the posting can't show. Headcount defaults to 25 or more (`meets_headcount_threshold: true`), so no employer-size search runs. Set `uses_ai_in_hiring` on every case; set `hours_per_week` when an hourly range is near the limit. Without an answer the rule's verdict is `needs_input`, and then the label must be `needs_input` too.
- **`refusal`** replaces `labels` when the checker should refuse the input: `not_a_posting`, `multiple_postings`, `french` or `empty`.
- **Real postings** also carry `source` (url, board, employer, location, fetched). The collector masks email addresses and phone numbers. While labelling, remove a person's name if one appears (for example a hiring manager's).
- **Adversarial cases** carry `variant_of: <id>` and the same labels as that case.

## Labelling

Label what the law requires of this posting with this context, not what CheckON says. Work from the posting without running the checker, so its answer can't sway yours. Each label is one of `pass`, `fail`, `warning`, `not_applicable`, `needs_input`.

| Rule | `pass` | `fail` | Other |
| --- | --- | --- | --- |
| ON-APPL-01 (25+ employees) | The employer has 25 or more employees in Ontario | | `not_applicable`: fewer than 25 |
| ON-APPL-02 (public posting) | A public posting for a specific job in Ontario | | `not_applicable`: general campaign or help-wanted sign, internal only, or work outside Ontario |
| ON-PAY-01 (pay disclosed) | Expected pay or a range is stated (commission counts; bonus, equity or benefits alone don't) | No wages stated | `not_applicable`: the expected pay is over $200,000 a year, or the rules don't apply. `needs_input`: a pay placeholder such as "[add pay]" |
| ON-PAY-02 (range width) | The range is at most $50,000 a year wide (inclusive), or a single figure | Wider than $50,000 a year, or open-ended ("$70,000+") | `not_applicable`: no pay at all, over $200,000, or the rules don't apply. Hourly ranges convert at the context's hours (default 40 a week, 52 weeks); `needs_input` when the answer turns on hours the context doesn't give. |
| ON-VAC-01 (vacancy statement) | Says plainly whether the job is an existing vacancy (either way) | No statement | `warning`: a vague statement ("we may hire for this role") |
| ON-AI-01 (AI disclosure) | AI is used and disclosed, or AI isn't used and the posting doesn't say it is | AI is used (context) and not disclosed, or the posting says no AI while it is used | `warning`: the posting says AI is used but the employer says it isn't |
| ON-CEX-01 (Canadian experience) | No condition on where experience or credentials were gained | Requires Canadian experience, local experience, a Canadian degree or a Canadian client base | `warning`: borderline wording ("Ontario experience is an asset", "knowledge of Canadian tax rules") |

When the rules don't apply at all (ON-APPL-01 or ON-APPL-02 is `not_applicable`), every content rule is `not_applicable` too. The wording behind each rule is in `rulepacks/CA-ON/rules.yaml` and the reasons in `docs/law-review-2026-10.md`. Where you're unsure, write the question in `notes`: it goes to the lawyer.

**Two labellers:** the first labels and adds their name to `labelled_by`. The second labels without seeing the first's labels (open the file with the `labels` block folded, or label in a copy) and adds their name. Write disagreements in `notes` with both answers. The lawyer settles them, and `labels` keeps the settled answer. The runner scores every labelled case, but the release gates count only cases with two names.
