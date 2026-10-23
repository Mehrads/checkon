# Ontario Job Posting Compliance Checker – PRD

Oct 19, 2026 · Mehrad

## 1. Overview and problem

**Product:** a pre-publish checker that validates a job posting against Ontario's job posting rules, rewrites it into a compliant version with every change highlighted, and runs inside the tools employers already use.

**Problem:** since January 1, 2026, Ontario employers with 25 or more employees must include pay, a vacancy statement and an AI disclosure in public postings, must not ask for Canadian experience, and must keep records. Postings are written by HR generalists and recruiters across many tools (ATS, LinkedIn, job boards, careers pages). Templates drift, agencies post for many clients with different rules, and fixing a posting means rewriting it by hand. Missing pay also costs applicants: 64% of Canadian job seekers have skipped a posting with no salary.

**Value proposition:** open or paste a posting and get, before publishing and without leaving the tool:

- a definitive pass/fail per rule, pointing at the exact sentence;
- a compliant rewrite with changes highlighted and tied to the rule;
- a suggested pay range with its sources.

## 2. Goals, non-goals and success metrics

**Goals**

1.  Validate any posting against the v1 rules with a definitive verdict per rule.
2.  Produce a compliant rewrite with highlighted changes that the user approves.
3.  Work where postings are written: browser extension first, native integrations second.
4.  Reach 3 paying customers (paid pilot or subscription) within 10 weeks of starting.

**Non-goals for v1**

- Other provinces and US states (the rules engine is designed for them, but they ship later).
- Legal advice or legal sign-off.
- Publishing anything without human approval.
- Scraping LinkedIn, Indeed or Glassdoor.
- Enterprise features (SSO, procurement, custom SLAs).

**Success metrics**

| Metric                                | Target                            |
|---------------------------------------|-----------------------------------|
| Verdict accuracy on the 300-posting golden set | Passes the release gates in Technical Design §8 before launch |
| Checks run per week                   | Steady week-over-week growth      |
| Returning users within 30 days        | 20%+                              |
| Custom solution requests              | 10+ in first 8 weeks after launch |
| Paying customers                      | 3+ by week 10                     |
| p95 time per check                    | Under 15 seconds                  |

## 3. Target users

| User                                                                             | Context                                                                         | What they need                                                    | Priority                                 |
|----------------------------------------------------------------------------------|---------------------------------------------------------------------------------|-------------------------------------------------------------------|------------------------------------------|
| Recruiter at a staffing or recruiting agency                                     | Posts for many clients, often uses its own AI screening tools                   | Per-client settings, high volume, proof of compliance for clients | Primary paying segment                   |
| HR generalist or office manager at an Ontario business with 25 to ~500 employees | 3+ postings a month, uses BambooHR, Workable, Employment Hero, LinkedIn or none | Fix it fast without learning the rules                            | Primary user, smaller budget             |
| HR consultant or employment lawyer                                               | Advises many employers                                                          | Something to recommend to clients                                 | Partner and referral channel, not a user |

Out of scope: employers under 25 employees (not covered by the rules) and large enterprises.

## 4. Rules covered in v1 (Ontario)

**Applicability gate (asked once per company, then remembered; the v1 free check never asks headcount: it searches the web for the employer named in the posting and assumes the rules apply when it finds nothing):** 25+ employees in Ontario on the posting date, external public posting, and work performed in Ontario. If the gate fails, the tool says the rules don't apply and why. Once the gate passes, every verdict is definitive.

| \#  | Rule                                                                                                     | Check method                           | How the tool fixes it                                                        |
|-----|----------------------------------------------------------------------------------------------------------|----------------------------------------|------------------------------------------------------------------------------|
| 1   | Expected pay or pay range; range no wider than \$50,000; exempt if pay or top of range is over \$200,000 | Extraction + deterministic check       | Insert or narrow the range from the pay suggestion; user confirms the number |
| 2   | Statement on whether the posting is for an existing vacancy                                              | Extraction + deterministic check       | One-click question, then insert standard wording                             |
| 3   | Disclosure if AI is used to screen, assess or select applicants                                          | Company setting + text check           | Insert standard statement; answer remembered for all postings                |
| 4   | No Canadian experience requirement in the posting or application form                                    | LLM classifier (catches rephrasings)   | Remove or reword the sentence, shown as a highlighted change                 |
| 5   | Tell interviewees within 45 days of their last interview whether a decision was made                     | Not posting text; needs interview data | Reminder feature (integration tier)                                          |
| 6   | Keep each posting and application form for 3 years after it closes                                       | Not posting text                       | Archive of approved versions (paid tier)                                     |

Rules are stored as versioned configuration with an effective date and a citation to the regulation, so new provinces and states are added as data, not code. An employment lawyer reviews the rule set before launch and after each change.

## 5. Product surfaces and user flow

**Surfaces**

| Surface             | What it does                                                                                                                                                           | Tier                         |
|---------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------|
| Browser extension   | Side panel that reads the posting from any form or page (BambooHR, Workable, LinkedIn's job form, Indeed employer, a careers-page CMS) and checks it before publishing | Sign-up required; paid plans |
| Web app             | Paste text or a public posting link (free and paid), plus the application form's questions (one more check); company profile, history, settings, archive                                          | Free tier + paid             |
| Native integrations | Connect to the HR system's API: pull openings, write fixes back, archive, 45-day reminders                                                                             | Paid / custom                |
| API                 | For agencies and small ATS vendors to embed the checker                                                                                                                | Later                        |

The extension is the integration that works with every platform on day one, so users never switch tools. Native integrations come one system at a time, in order of demand.

**Core flow**

1.  **Capture:** the user opens a posting draft; the extension reads the text (or the user pastes it).
2.  **Gate:** the company profile answers applicability; asked only the first time.
3.  **Validate:** a verdict for each rule, with the failing sentence highlighted.
4.  **Fill gaps:** one-click questions for facts the tool cannot know (vacancy, AI use, pay).
5.  **Rewrite:** a compliant version, with each change highlighted and labelled with its rule; optional style suggestions are shown separately.
6.  **Approve:** accept all or change by change; the extension writes the text back into the form (copy as fallback).
7.  **Remember and archive:** confirmed answers are reused next time; the approved version is stored with a timestamp (paid).

## 6. Functional requirements

| ID   | Requirement                                                                               | Priority |
|------|-------------------------------------------------------------------------------------------|----------|
| FR1  | Capture posting text from a form, a page, a paste or a URL                                | P0       |
| FR2  | Company profile: headcount, AI use, standard wording; one profile per client for agencies | P0       |
| FR3  | Rule engine: verdict per rule, with the evidence span and the rule citation               | P0       |
| FR4  | Compliant rewrite that changes only what the rules require and keeps tone and structure   | P0       |
| FR5  | Highlighted diff with accept/reject per change                                            | P0       |
| FR6  | Check quota and metering per plan                                                         | P0       |
| FR7  | Rule versioning with effective dates; weekly monitoring of official sources for changes   | P0       |
| FR8  | Write the approved text back into the form (copy fallback is P0)                          | P1       |
| FR9  | Pay range suggestion with sources                                                         | P1       |
| FR10 | Per-client workspaces for agencies                                                        | P1       |
| FR11 | Archive of approved versions for 3 years, with export                                     | P1       |
| FR12 | 45-day reminders from interview dates (needs integration)                                 | P2       |
| FR13 | Re-check published postings on channels the customer owns (careers page, ATS job board)   | P2       |

**Non-functional requirements**

- Same input gives the same verdict: deterministic checks wherever possible, plus a result cache keyed on the input (the models don't allow temperature 0); the LLM is used for extraction, classification and rewriting.
- Pass the release gates (Technical Design, section 8) on the 300-posting golden set before launch: 98%+ recall on pay, vacancy and AI violations, 95%+ recall on Canadian experience, 90%+ precision on every `fail`. Re-run on every rule, prompt or model change.
- p95 under 15 seconds per check.
- Privacy: posting text is not used for training; individual employee salaries never leave the customer's system.
- Every result carries a short "not legal advice" note.

## 7. Data sources: postings and salary

**Postings**

| Source                                                                                                   | Used for                  | Status                                     |
|----------------------------------------------------------------------------------------------------------|---------------------------|--------------------------------------------|
| The user's own draft (extension or paste)                                                                | Every check               | Allowed                                    |
| The user's own published posting on any site, read by the extension while they view it                   | Re-checking live postings | Allowed (user-initiated)                   |
| Public ATS job boards (e.g. Greenhouse, Lever, SmartRecruiters) and careers pages, respecting robots.txt | Data report and outreach  | Allowed                                    |
| Licensed job-data providers                                                                              | Market report at scale    | Allowed, subject to the provider's licence |
| LinkedIn or Indeed scraping, directly or through a third-party scraping tool                             | Not used                  | See Risks                                  |

**Salary suggestion, in priority order**

1.  The pay or range already stored on the opening in the customer's system (the most common gap: stored but not shown).
2.  A band the customer confirmed for this role earlier.
3.  Government of Canada Job Bank wages by occupation (NOC) and region: open data, citable.
4.  Web search for current postings for the same role and city, shown with links.

The LLM maps the job title to a NOC code and summarises the sources; it is never the source of the number itself. Glassdoor is not used (no public API, scraping prohibited); licensed compensation data can be added later.

**Guardrail:** the tool never inserts a range the employer has not confirmed. The posted range must be what they genuinely expect to pay.

## 8. Pricing and unit economics

**Cost per check and hosting (estimate as of October 19, 2026; details in the Technical Design, section 13)**

| Item                                                                                      | Estimate (USD)      |
|-------------------------------------------------------------------------------------------|---------------------|
| Model fees per check (Haiku 5.5 for extraction and re-inspection, Sonnet 5.5 for rewrites, thinking off) | about \$0.013       |
| Pay suggestion with web search (paid tiers)                                               | about \$0.03        |
| Fixed hosting on GCP, lean launch                                                         | about \$41 a month  |
| Fixed hosting on GCP, production                                                          | about \$169 a month |

Model fees are small: about \$0.67 a month for a Starter customer using all 50 checks. Margin depends on spreading the fixed hosting across customers, so price on value (hours saved, more applicants), not on cost. These figures are replaced by measured numbers from the test set before launch.

**Subscription plans (CAD, starting points to test)**

| Plan    | Includes                                                                                 | Price (CAD) | Model fees at full use (USD)                        |
|---------|------------------------------------------------------------------------------------------|-------------|-----------------------------------------------------|
| Free    | 1 pasted check per week, no sign-up; full verdict and rewrite, pay left as a placeholder | \$0         | about \$0.06 a month per user                       |
| Starter | 50 checks/month, company profile, history, pay suggestions                               | \$79/month  | about \$0.67, plus up to \$1.50 for pay suggestions |
| Agency  | 300 checks/month, per-client workspaces, archive                                         | \$249/month | about \$4, plus up to \$9 for pay suggestions       |
| Overage | Extra checks on any paid plan                                                            | \$1/check   | about \$0.013                                       |

**Custom solutions**

| Package                  | Scope                                                                                             | Price (starting point)                    |
|--------------------------|---------------------------------------------------------------------------------------------------|-------------------------------------------|
| Standard connector setup | Connect a supported system (e.g. BambooHR), configure wording and rules, test on 10 real postings | \$1,000–1,500 one-time, plus subscription |
| Custom integration       | Unsupported system or workflow (internal careers CMS, approval flow, reporting)                   | \$4,000–8,000 fixed scope                 |
| Advisory                 | Anything outside a package                                                                        | \$150/hour                                |

Pricing rule for custom work: estimated hours × hourly rate × 1.3 buffer, quoted as a fixed price. The hourly rate assumes senior freelance AI engineering in Ontario at roughly \$120–180/hour; validate it with the first quotes. Any custom request that comes up three times becomes a standard feature.

## 9. Free version and go-to-market

**Free check (no sign-up):** paste a job description into the web app and get one check per week: the verdict per rule and the compliant rewrite with highlighted changes. Where pay is missing, the rewrite leaves a marked placeholder. Everything else needs an account. Everything runs on our servers; the rules engine, prompts and rule data are closed source and never ship to the client.

| Feature                                      | Free (no sign-up)               | Signed up / paid                 |
|----------------------------------------------|---------------------------------|----------------------------------|
| How it works                                 | Copy and paste into the web app | Web app, extension, integrations |
| Checks                                       | 1 per week                      | Per plan (50+ per month)         |
| Verdict per rule and compliant rewrite       | Yes                             | Yes                              |
| Pay range suggestion with sources            | No (placeholder in rewrite)     | Yes                              |
| Browser extension                            | No                              | Yes                              |
| Company profile memory and history           | No                              | Yes                              |
| Per-client workspaces, archive, integrations | No                              | Yes                              |

**Enforcing the free limit:** with no account, the weekly limit is counted per browser (device identifier plus a cookie) and per IP address, with a cap on posting length. Some abuse is acceptable; the free check is marketing. The sign-up wall sits on pay suggestions, the extension and history, which is where the conversion happens.

**Pitch for the free version**

Lead with more applicants and put compliance second. Enforcement is complaint-driven, so fear of a fine won't drive sign-ups (Research guide).

> 64% of Canadian job seekers skip postings with no salary. Paste yours and get a rewrite that attracts more applicants and meets Ontario's 2026 rules. Free once a week.

**Channels, in order**

1.  Chrome Web Store listing and a landing page with a 20-second before/after demo.
2.  Data report: "We checked 1,000 Ontario job postings: what's most often missing", anonymised, from public ATS boards and careers pages; pitched to HR media.
3.  LinkedIn posts with real before/after rewrites (anonymised).
4.  HR communities: HRPA chapters, Ontario chambers of commerce, r/humanresources and r/recruiting (following each community's rules).
5.  Partners: HR consultants and employment lawyers who recommend it, with a referral fee.
6.  Direct outreach to agencies, 10–20 checked emails a week, each with one corrected posting as a free sample.

**Outreach rules (CASL):** only business addresses the company publishes; your name, mailing address and a working unsubscribe link in every email. In-product verdicts are definitive, but cold emails say a posting "doesn't appear to include" a disclosure, because you don't yet know their headcount or exemptions.

**Upgrade triggers in the product:** hitting the free quota, "connect your HR system", "save to archive", and an agency adding a second client.

## 10. Risks and legal constraints

| Risk                                                                | Why it matters                                                                                                                                                                                                                                    | Mitigation                                                                                                               |
|---------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| Scraping LinkedIn or Indeed, directly or through a third-party tool | Both prohibit it in their terms; in hiQ v. LinkedIn the court found hiQ breached LinkedIn's User Agreement (2022). A vendor does not take the risk off you: account bans, cease-and-desist letters, and a product built on data you can't rely on | Not used. The extension checks the user's own postings; outreach uses public ATS boards, careers pages and licensed data |
| Scraping Glassdoor for pay data                                     | Same terms problem; no public API                                                                                                                                                                                                                 | Job Bank, the employer's own data, licensed data later                                                                   |
| Using the LLM's own knowledge for pay                               | Not citable, often out of date, can be wrong; a wrong range is itself a compliance problem                                                                                                                                                        | LLM maps titles and summarises sources only                                                                              |
| Wrong verdict or missed violation                                   | Liability and lost trust                                                                                                                                                                                                                          | Deterministic checks, a 300-posting golden set, lawyer-reviewed rules, user approval, "not legal advice" note              |
| Rule changes                                                        | Stale verdicts                                                                                                                                                                                                                                    | Versioned rules, weekly monitoring of official sources                                                                   |
| Commoditisation (free checkers, ChatGPT, ATS vendors adding fields) | Free tier has no moat                                                                                                                                                                                                                             | Win on rewrite quality, working inside every tool, agency features and multi-jurisdiction rules                          |
| SMBs pay little                                                     | Slow revenue                                                                                                                                                                                                                                      | Prioritise agencies for paid plans                                                                                       |
| Extension breaks when an ATS changes its UI                         | Broken capture                                                                                                                                                                                                                                    | Generic text capture with paste fallback; monitor top sites                                                              |
| Employment contract                                                 | IP or outside-work clauses could claim the code                                                                                                                                                                                                   | Check the employment contract before building or launching                                                               |
| Candidate data in the 45-day feature                                | Privacy obligations (PIPEDA)                                                                                                                                                                                                                      | Defer to P2; store only dates, not candidate details                                                                     |

## 11. Roadmap, kill criteria and open questions

| Phase                 | Weeks | Deliverable                                                                                         |
|-----------------------|-------|-----------------------------------------------------------------------------------------------------|
| 0\. Prep              | 1     | Contract check, rule spec, English golden set: 150 real and 25 out-of-scope postings labelled, 100 synthetic and 25 adversarial written |
| 1\. Core (v1)         | 2–4   | Inspector + Refiner + API (hosted, closed source) for English postings, free paste check on the website, misuse controls; full scope in `04-V1-Scope.md` |
| 2\. Launch v1         | 5     | Website live on the lean GCP stack, data report, outreach; paid pilots invoiced by hand, so selling starts here rather than after phase 3 |
| 3\. Accounts and paid | 6–7   | Sign-up, payments, quotas, pay suggestions, application form checks, browser extension, Chrome Web Store |
| 4\. First integration | 8–10  | BambooHR (if the careers-page crawl confirms it), archive                                           |
| Later                 | —     | French and bilingual postings, scheduled by demand (share of French postings in free checks and the data-report crawl); BC, PEI, New Brunswick; then US states (NY, CA, CO, WA, IL first); API for agencies and ATS vendors |

**Kill criteria at week 10:** fewer than 3 paying customers and fewer than 10 custom requests → stop or pivot to the most common request. 3+ paying customers → continue past phase 4: the next integration and the next jurisdiction. A paid pilot counts as a paying customer.

**Open questions (answered in the technical doc unless noted)**

- Which HR systems let us read and write job openings through their API, and does any offer a pre-publish hook?
- Measured token cost and latency per check for each candidate model.
- How reliably a no-account weekly limit can be enforced (device identifier plus IP), and how much abuse to tolerate.
- Cost of a lawyer's review of the rule set (business).
- Who is the second labeller for the golden set (the Technical Design requires two labels per posting), and what it costs (business).
- Product name, business registration and whether errors-and-omissions insurance is needed (business).

---

Companion documents: `02-Technical-Design.md` (how it is built), `03-Research-and-Interview-Guide.md` (market research and the discovery-call script) and `04-V1-Scope.md` (what ships first).
