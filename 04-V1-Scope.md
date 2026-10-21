# Ontario Job Posting Compliance Checker – v1 Scope

Oct 19, 2026 · Mehrad

v1 is phase 1 of the PRD roadmap: the engine plus the free paste check. This document says what is in it, what waits, and when it is done. Where it differs from the PRD or the Technical Design, this document wins for v1 (section 4 lists every difference).

## 1. What v1 is

A public web page where anyone pastes one English job posting and gets, once a week with no sign-up:

- a verdict per rule, pointing at the exact sentence;
- a compliant rewrite, shown as highlighted changes the user accepts or rejects one by one;
- a final text to copy.

It is also the research instrument from the Research guide: every result asks one short question and offers a "run this on my HR system" request form.

**v1 is done when:**

1. The release gates in Technical Design §8 pass on the English golden set.
2. An employment lawyer has signed off every rule marked interpretation and the wording library.
3. The page is live on the lean GCP stack with the free limit enforced on the server.

## 2. User flow

1. **Paste:** the posting (up to 8,000 characters). An invisible CAPTCHA runs in the background.
2. **Gate:** headcount is never asked. A web search looks up the employer named in the posting; the rules apply unless it clearly shows fewer than 25 employees, and are assumed to apply when the employer isn't named or nothing is found. Public posting, specific position and Ontario location come from the text. Anything unclear becomes a `needs_input` question. If the gate fails, the page says the rules don't apply and why.
3. **Verdicts:** one result per rule, with the failing sentence highlighted and the rule's citation.
4. **Questions:** one-click answers for facts the tool can't know: existing vacancy, AI use in hiring, hours per week for an hourly range.
5. **Rewrite:** one patch per failing rule, labelled with its rule. Missing pay becomes the placeholder `[Pay range: add before publishing]`.
6. **Approve and copy:** accept or reject each patch; the status is recomputed on the accepted version; the user copies the text.
7. **Feedback:** thumbs up or down on each finding and patch, a "this looks wrong" button, the research question and the request form.

## 3. In and out

**In v1**

| Area | What ships | Reference |
| --- | --- | --- |
| Rule pack | `CA-ON@1.0.0` as YAML: ON-APPL-01, ON-APPL-02, ON-PAY-01, ON-PAY-02, ON-VAC-01, ON-AI-01, ON-CEX-01, each with citation, effective dates and test cases | Tech §2, §6 |
| Inspector | Pipeline steps 1–8 for English: normalise with offsets, extract (Haiku 5.5), verify spans, parse pay twice, classify (Haiku 5.5) with the keyword safety net, rules as code, aggregate | Tech §4 |
| Refiner | Every patch type in Tech §5 except "pay confirmed" (needs the pay service): pay placeholder, range options computed by code, vacancy and AI wording, AI-statement removal, Canadian-experience rewrite and borderline suggestion. Acceptance tests 1–5, retry once, then drop the patch | Tech §5 |
| Repeatability | Result cache keyed on the five versions; every report stores them | Tech §4 |
| API | `POST /v1/inspect`, `/v1/refine`, `/v1/answers`, `/v1/patches/accept`, anonymous only | Tech §11 |
| Web page | Paste form, verdicts with highlights, questions, patch accept/reject, copy, "not legal advice" note | PRD §5 |
| Research hooks | One question per result, request form, thumbs with reasons, "this looks wrong" button | Research guide |
| Free-check limits | Lean set, section 4 | Tech §11 |
| Evaluation | Golden-set runner computing every release gate, 3-run consistency and the injection slice; runs in CI on every rule, prompt or model change | Tech §8 |
| Hosting | Lean GCP stack: Cloud Run, Cloud SQL (also holds the cache and quotas), Secret Manager, GitHub Actions deploy, Langfuse Cloud Hobby with posting text masked | Tech §12, §13 |

**Golden set for v1:** 300 English postings (150 real, 100 synthetic, 25 out of scope, 25 adversarial). Synthetic cases that need an application form wait for phase 3.

**Not in v1**

| Feature | When |
| --- | --- |
| Application form checks | Phase 3, with accounts |
| Accounts, company profile, history, overrides, edit-and-recheck of a patch | Phase 3 |
| Pay suggestions | Phase 3 |
| Archive, BambooHR, 45-day reminders | Phase 4 and later |
| French and bilingual postings | Later, by demand |
| Jev decision-model cascade | Only if measured cost needs it |
| Device fingerprinting, IP-reputation blocking, Cloud Armor, Redis | When abuse data or volume needs them (production stack) |
| Automated weekly rule-source monitoring | Later; v1 uses a manual weekly check of the official sources |
| Style suggestions | Later |
| Data-report crawl | Phase 2; it reuses the v1 engine as a separate job |

## 4. Changes from the PRD and Technical Design

| Topic | Before | v1 | Why |
| --- | --- | --- | --- |
| Application form | Posting and form both checked (Tech §14) | Posting only | Your call: free users rarely have the form text at hand |
| Classification | Jev first, Haiku on low confidence (Tech §7) | Haiku 5.5 only | The cascade saves well under a cent per check and adds a vendor and a data-retention review |
| Free-check limits | Full set in Tech §11 | Weekly quota per cookie and per IP in Postgres, 8,000-character cap, origin check, per-IP rate limit, daily spend cap. No CAPTCHA: Turnstile was dropped on 2026-10-20 | PRD §9 already accepts some abuse; add the rest, or a bot check, when the logs show it is needed |
| Result cache and quotas | Redis (Tech §11, §12) | Postgres tables | The lean stack has no Redis |
| One-posting check | Separate decision-model call (Tech §11) | A field in the extraction output; non-postings and multiple postings are refused before refine | One call instead of two |
| Applicability, headcount | Company profile, asked once (PRD §4) | Web search on the employer named in the posting; never asked; assumed to apply when nothing is found | Your call: no question on the form. Search figures are worldwide, rarely Ontario-only, so verdicts rest on an estimate |
| Rule-source monitoring | Weekly automated job (Tech §10) | Manual weekly check | The automated diff can follow; the rule pack is versioned either way |
| Browser extension | Phase 3, paid plans, sign-up required (PRD §5, §9) | Free, now: a Chrome and Edge side panel with the same access as the web check (one check a week per browser and IP, no sign-up). It reads the posting from the page and writes the approved text back. Closed source and a thin client: rules, prompts and rule data stay on the server | Your call (2026-10-21): checks wherever postings are written, without waiting for accounts |
| Native integrations | Standard connectors and setup packages (PRD §5, §8) | Custom work per client only: a connector to that client's HR system, built on our API, quoted as Custom setup | Your call (2026-10-21): build connectors only when a paying client needs one |

## 5. Build order

Each step ends in something that runs and can be checked.

| # | Step | Done when |
| --- | --- | --- |
| 0 | Prep: contract check, rule spec as YAML, golden set labelled | Contract cleared; 300 English postings with per-rule labels in the repo |
| 1 | Rule engine, no LLM | Every Layer 1 case in Tech §8 passes as a unit test |
| 2 | Normaliser and money parser | Offsets map back to the original text; parser tests pass for hourly, `k`, ranges, "up to" and "+" |
| 3 | Extraction, span verification, classification | The golden set runs end to end through the Inspector and the gates are measured |
| 4 | Refiner and acceptance tests | Refiner gates pass: 95%+ of fixable failures fixed, 0 patches with a new fact |
| 5 | API and web page | Paste, answer, review patches and copy works end to end locally |
| 6 | Free-check limits and research hooks | A second check from the same cookie or IP in a week is refused; feedback and requests are stored |
| 7 | Deploy | The release gates pass on the deployed build, p95 is under 15 seconds, lawyer sign-off is recorded in the rule records |

## 6. Open before launch

- Who the lawyer is and what the review costs (needed for step 7).
- Who the second golden-set labeller is (needed for step 0).
- Product name and domain (needed for deploy).
- An API account with no training on inputs, and Langfuse masking turned on.

---

Companion documents: `01-PRD.md`, `02-Technical-Design.md`, `03-Research-and-Interview-Guide.md`.
