# CheckON: Ontario job posting checker

CheckON checks a job posting against the rules Ontario added to its Employment Standards Act for postings published from January 1, 2026, explains every gap with the section of the law behind it, and rewrites the posting so it complies. Paste the text or a link, check the application form too, or run it from a Chrome or Edge side panel on the page where you write the posting.

It ran as a hosted service in the fall of 2026. The service is shut down; this is its full code, released under the [Apache License 2.0](LICENSE) so anyone can run it, study it or build on it.

> **Not legal advice.** The rules here are one careful reading of the law (see [the law review](docs/law-review-2026-10.md)). No employment lawyer has signed off on them yet: every rule marked `interpretation: true` in `backend/rulepacks/CA-ON/rules.yaml` still has `reviewed_by: null`. Use the results as a checklist, not a legal opinion.

## The problem

Since January 1, 2026, Ontario employers with 25 or more employees must follow new rules for every publicly advertised job posting (ESA Part III.1, ss. 8.1 to 8.7, and O. Reg. 476/24). Most postings were written before the rules existed, they're copied from templates, and the gaps are easy to miss: in a sample of 149 real Ontario postings from established employers, about 63% broke at least one rule, most often by leaving out the vacancy statement ([docs/accuracy-2026-10.md](docs/accuracy-2026-10.md), section 6).

What a posting must do, as the rule pack encodes it:

| Rule | What it checks | Source |
| --- | --- | --- |
| ON-APPL-01 | The rules apply: the employer has 25 or more employees in Ontario on the day it posts | O. Reg. 476/24, s. 1 |
| ON-APPL-02 | It's a publicly advertised posting for a specific position (not a general recruitment campaign, an internal posting, or work outside Ontario) | O. Reg. 476/24, s. 2 (1) |
| ON-PAY-01 | It states the expected pay or a pay range (not required above $200,000 a year) | ESA s. 8.2 (1); O. Reg. 476/24, ss. 2 (2), 3 |
| ON-PAY-02 | A pay range is no wider than $50,000 a year | ESA s. 8.2 (3); O. Reg. 476/24, s. 4 |
| ON-VAC-01 | It says whether it's for an existing vacancy | ESA s. 8.5 (1) (a) |
| ON-AI-01 | It discloses the use of AI to screen, assess or select applicants, if the employer uses it | ESA s. 8.4 (1) |
| ON-CEX-01 | Neither the posting nor its application form requires Canadian experience | ESA s. 8.3 (1) |
| ON-INT-01 | Reminder: tell every interviewed applicant within 45 days whether a decision has been made | ESA s. 8.6; O. Reg. 476/24, s. 5 |
| ON-REC-01 | Reminder: keep each posting, its application form and what interviewed applicants were told for three years | ESA s. 15 (7.1), (7.1.1) |

## How it works

The product is two engines behind one API, and the code, not the model, decides every verdict:

```
posting text or link
  → normalise (sentences, sections, an offset map back to the original)
  → extract facts and label sentences (Claude Haiku: pay, title, location, AI use, vacancy, Canadian-experience lines)
  → rule engine (pure functions driven by the YAML rule pack: pass, fail, warn, needs your answer)
  → report, with the citation for every finding
  → Refiner: wording-library templates first, Claude Sonnet only for rewrites that need it
  → the rewrite is checked again by the Inspector; it's shown only if it passes
```

- **Inspector** (`backend/app/compliance/inspector.py`, `engine.py`, `checks.py`): one pure function per rule check, driven by `backend/rulepacks/CA-ON/rules.yaml` (citations, effective dates, parameters, messages and questions). Money parsing and range math are code (`money.py`), not the model.
- **Refiner** (`refiner.py`, `wording.py`): proposes a patch per failing rule, keeps everything else of the posting as written, and re-runs the Inspector on the result.
- **Questions instead of guesses:** when the posting can't settle a rule (does the employer use AI in hiring? how many employees in Ontario?), the report asks, and the answer re-runs the rules in code with no model call. Employer size can also come from a short web search.
- **Prompt-injection defence:** postings are data, never instructions; the adversarial golden-set cases (`backend/evals/golden/adversarial/`) cover injected instructions and odd formatting.

The full design and its reasoning are in [docs/technical-design.md](docs/technical-design.md).

## Features

**For anyone, no account:** the paste check (text or a link), the application-form check, the rewrite, and the browser extension. Visitors get a weekly quota per cookie and IP, and a daily spend cap on model fees.

**For signed-in accounts:**

- Company profiles, and a workspace per client for recruiters: the facts a check starts from (headcount, AI use, plain or formal wording), so it doesn't ask again.
- Pay range suggestions from Job Bank's Ontario wages and current postings, with sources, saved per job title once you confirm them.
- Careers page audits: read every open Ontario posting on a Greenhouse, Lever, Ashby or SmartRecruiters board or a careers page (respecting robots.txt) and check them all.
- An opt-in archive of the postings you fixed, kept for the three years the ESA requires and then deleted, with a zip export.
- Check history (date, job title, result; never the posting text).

**For admins:** usage stats (checks, returning visitors, timing, model spend) and user management.

**Public guide pages** in English and French for each rule, a posting template and a checklist.

## Run it locally

You need Docker, [uv](https://docs.astral.sh/uv/), [bun](https://bun.sh) and an [Anthropic API key](https://console.anthropic.com/).

1. Copy the settings:

   ```bash
   cp .env.example .env
   ```

   Set `ANTHROPIC_API_KEY`, and replace every `changethis` value.

2. Start Postgres and apply the migrations:

   ```bash
   docker compose up -d db
   ```

   ```bash
   cd backend && uv run alembic upgrade head && uv run python -m app.initial_data
   ```

3. Build the frontend once; the backend serves it:

   ```bash
   bun install && cd frontend && bun run build
   ```

4. Start the backend and open http://localhost:8000:

   ```bash
   cd backend && uv run fastapi dev
   ```

Sign in at `/login` as `FIRST_SUPERUSER`. Signing in emails a 6-digit code; locally, `docker compose up -d mailpit` catches it, and http://localhost:8025 shows it.

For frontend work with hot reload, run `bun run dev` in `frontend/` and open http://localhost:5173. After changing the API, regenerate the client with `bash scripts/generate-client.sh`.

## Configuration

The settings live in `.env` (see `.env.example`) and `backend/app/core/config.py`. The ones that matter most:

| Setting | Default | What it does |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | none | Needed for every check. |
| `FREE_CHECKS_PER_WEEK` | `1` | Checks per visitor cookie and per IP, for visitors who aren't signed in. |
| `FREE_CHECK_DAILY_SPEND_CAP_USD` | `5` | Model fees visitors' checks may use per day (Toronto time); free checks pause after that. |
| `SIGNUP_OPEN` | `false` | Let anyone make an account. Off: an admin adds users. You pay for every account's checks. |
| `ACCOUNT_CHECKS_PER_30_DAYS` | `0` | Each signed-in account's checks in any 30 days; `0` means no limit. |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAILS_FROM_EMAIL` | none | Sign-in codes, password resets and contact-form notices. Without email, nobody can sign in. |
| `EXTENSION_IDS` | empty | Browser extension IDs allowed to call the API. |
| `TRUSTED_PROXY_HOPS` | `0` | Proxies in front of the app that append to `X-Forwarded-For` (Cloud Run: 1, plus 1 for a load balancer). |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | none | Optional tracing of model calls, metadata only. |
| `VITE_SITE_URL` | `http://localhost:5173` | The public site's address, for canonical links, the sitemap and robots.txt (build time, `frontend/.env`). |
| `VITE_CONTACT_EMAIL` | none | Optional address shown for the site's operator on the contact, privacy and terms pages (build time). |
| `VITE_UMAMI_WEBSITE_ID` | none | Optional cookieless visit counts on the public pages (build time). |

## Privacy by design

- A posting's text lives in memory for an hour while you work on it, then it's gone. The database never stores it, except in the archive, which is off until an account turns it on for a workspace.
- Visitor quotas are keyed by HMACs of the cookie and IP, never the raw values.
- Usage stats and traces hold timings, verdicts and costs, never posting text or the model's answers (a test fails if a posting's words reach a trace).
- The link reader and careers page audits respect robots.txt, and never read LinkedIn, Indeed or Glassdoor.

## Accuracy

Measured in October 2026 on 150 real Ontario postings against independent labels, after the fixes in rule pack CA-ON@1.3.0: 95 to 99% agreement per rule, and no non-compliant posting shown as passing (AI rule aside). Details, error analysis and the open questions for a lawyer are in [docs/accuracy-2026-10.md](docs/accuracy-2026-10.md) and [docs/law-review-2026-10.md](docs/law-review-2026-10.md).

The golden set behind the release gates is in `backend/evals/` (synthetic and adversarial cases). The real postings it was measured on aren't in this repository, since they're the employers' text; `app.evals.collect` gathers your own from public job boards.

## Repository layout

| Path | What's there |
| --- | --- |
| `backend/app/compliance/` | The Inspector, the Refiner, prompts, the money parser, the normaliser |
| `backend/rulepacks/CA-ON/` | The rules (`rules.yaml`), the fix wording (`wording.yaml`) and table-driven rule tests |
| `backend/app/api/` | The API: checks, accounts, workspaces, pay, audits, archive, stats |
| `backend/app/audit/`, `backend/app/pay/` | Careers page reading, pay suggestions and Job Bank wage data |
| `backend/evals/` | The golden set and its runner |
| `frontend/` | The React app and the public guide pages (prerendered) |
| `extension/` | The Chrome and Edge side panel |
| `infra/` | Optional Google Cloud deployment (Terraform) and its guide |
| `docs/` | The technical design, the law review and the accuracy review |

## Tests

```bash
cd backend && uv run pytest
```

The compliance tests (`backend/tests/compliance/`) need nothing else. The API tests need Postgres running and migrated. Tests that call the real model run only with `RUN_LIVE_LLM=1` and a key (`backend/README.md`). Frontend end-to-end tests: `cd frontend && bun run test`. Extension tests: `extension/README.md`.

## Deploy

Any host that runs the backend's Docker image (`backend/Dockerfile`) and Postgres works. The Google Cloud setup it ran on, with Terraform and GitHub Actions, is in [infra/README.md](infra/README.md).

## Contributing

Issues and pull requests are welcome. The most useful contributions:

- **A lawyer's review** of the rules marked `interpretation: true`, recorded as `reviewed_by` and `reviewed_on` in `rules.yaml` and `wording.yaml`. The open questions are listed in the law review.
- **Rule changes when the law changes:** each rule has `effective_from` and `effective_to`, and its own table-driven tests in `backend/rulepacks/CA-ON/tests/`.
- **More labelled postings** for the golden set (`backend/evals/README.md`).
- **Other provinces:** a rule pack per jurisdiction (`backend/rulepacks/<code>/`).

## License

[Apache License 2.0](LICENSE). Built on the [Full Stack FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template) (MIT); see [NOTICE](NOTICE).
