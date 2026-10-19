# Ontario Job Posting Compliance Checker – Research and Interview Guide

Oct 19, 2026 · Mehrad

Background research and the discovery-call script behind the PRD (`01-PRD.md`). Use the interview script for people who request a custom solution.

## What public research already answers

Most interview questions can be answered from public data: adoption is high, enforcement is weak, and the strongest selling point is more applicants, not avoiding fines.

| Question                          | What the evidence says                                                                                                                                        | Source                                                                                                                                                                                                                                                 |
|-----------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Are employers complying?          | Ontario postings with pay info rose from 49% before the law to 71% by June 2026; about 29% still show none (some are exempt).                                 | [Indeed Hiring Lab](https://www.hiringlab.org/en-ca/2026/07/23/growth-in-canadian-salary-transparency-driven-by-two-provinces/)                                                                                                                        |
| How is the AI disclosure handled? | Postings mentioning AI tripled, 9% to 28% (Oct 2025 to May 2026), as many employers add blanket statements.                                                   | [Indeed Hiring Lab](https://www.hiringlab.org/en-ca/2026/07/08/ontario-job-postings-highlight-the-widespread-use-of-ai-in-hiring-processes/)                                                                                                           |
| How strong is enforcement?        | Complaint-driven; lawyers called the rules largely toothless in January 2026. Top violations found in 2025–26 were wages and vacation pay, not postings.      | [Globe and Mail](https://www.theglobeandmail.com/business/article-ontario-hiring-pay-transparency-rules-enforcement/), [Ontario.ca](https://www.ontario.ca/document/your-guide-employment-standards-act-0/employment-standards-enforcement-statistics) |
| What do job seekers do?           | 64% of Canadian job seekers have skipped a posting with no salary listed.                                                                                     | [Employment Hero survey](https://www.businesswire.com/news/home/20260127936923/en)                                                                                                                                                                     |
| Are agencies affected?            | Yes: rules cover anyone posting for an employer; an agency's own AI screening tools trigger the disclosure, and many agencies have not updated postings.      | [Recruitly](https://recruitly.io/resources/ai-act-for-recruiters-ontario), [Retail Insider](https://retail-insider.com/retail-insider/2026/01/ontario-job-posting-rules-raise-the-stakes-for-retail/)                                                  |
| What do employers do today?       | Standard templates with fixed fields for pay, vacancy status and AI use.                                                                                      | [HR Insider](https://hrinsider.ca/changes-to-ontario-job-posting-requirements-what-employers-need-to-know-for-2026/)                                                                                                                                   |
| Who else sells this?              | Datapeople already covers Ontario with locked templates, AI disclosure text, a compliance report and records; a free Ontario checker and Sheets add-on exist. | [Datapeople](https://help.datapeople.io/article/327-geting-compliant-with-pay-transparency-laws), [Ontario Employer Tools](https://ontario-employer-tools.pages.dev/)                                                                                  |
| Do reposted copies keep the pay?  | Not reliably: in a New York City study, 44% of Google for Jobs listings lacked the required range, mostly from scraped reposts.                               | [NYC Council](https://council.nyc.gov/data/salary-transparency)                                                                                                                                                                                        |
| Is the market growing?            | New Brunswick added pay transparency on June 12, 2026, covering internal postings too; BC and PEI already require pay.                                        | [Lexology](https://www.lexology.com/library/detail.aspx?g=31e3f1f1-a03e-43a7-82b0-04ff6190a64c)                                                                                                                                                        |

**What this means for the product:**

- Sell **more and better applicants** first and compliance second; fear of a \$250 fine will not drive purchases.
- **Agencies** remain the best paying segment: more postings, their own AI tools, and accountability to clients.
- **Monitoring live and reposted copies** is a real gap: templates fix the original, not the copies on aggregators.
- Keep it **simple and cheap**; one agency-software vendor warns that clients are already buying expensive compliance products for duties they don't have.

What public data cannot tell you is whether *your* product gets paid for. The free tool answers that (next section).

## The free tool as the research instrument

Launch the free checker first and let its usage replace most interviews; custom work starts only when a user asks for it.

1.  **Free checker:** paste a posting and get a verdict on the four posting rules (pay, vacancy statement, AI disclosure, Canadian experience) plus a compliant rewrite. One check per week, no sign-up. The 45-day and record-keeping rules can't be checked from posting text; they are paid features. URL capture needs an account.
2.  **Built-in questions:** after each result, ask one short question in the tool (e.g. "Which HR system do you use?", "How many postings a month?", "Agency or employer?"). This collects the interview data at scale.
3.  **Request button:** "Want this to run automatically on your HR system?" opens a short form: system used, number of postings, what they want automated, contact email.
4.  **Custom solution:** each request becomes a short call and a quoted setup (e.g. a BambooHR connection with alerts and an archive). Repeated requests become standard product features.

**What to measure in the first 8 weeks:**

| Signal                    | Meaning                          | Target to keep going          |
|---------------------------|----------------------------------|-------------------------------|
| Weekly checks run         | Is anyone using it?              | Steady growth week over week  |
| Returning users           | Is it part of their workflow?    | 20%+ come back within a month |
| Custom requests submitted | Is there demand beyond free?     | 10+ requests                  |
| Paid setups or pilots     | Will they pay?                   | 3+ paying customers           |
| Most named HR system      | Which integration to build first | The clear leader              |

Use the interview script below only for the people who submit a request: it turns their request into a well-scoped, priced custom solution.

## Goal and who to talk to

The goal is to learn, in about 10 conversations, whether Ontario employers or recruiting agencies will pay to stay compliant with the 2026 job posting rules, and which version they would pay for. You are not selling yet; you are collecting facts about their real process.

**Who to interview (aim for a mix):**

| Segment                                                 | Target count | Why they matter                                                   |
|---------------------------------------------------------|--------------|-------------------------------------------------------------------|
| Recruiting / staffing agency owners or leads in Ontario | 4–5          | Post the most jobs, for many clients; carry the risk with clients |
| HR managers at Ontario companies with 25–500 employees  | 4–5          | Directly covered by the rules; usually no compliance team         |
| Employment lawyers or HR consultants                    | 1–2          | See many clients' mistakes; possible referral partners            |

**Where to find them:** LinkedIn (search "recruiter" or "HR manager" + Ontario city), HRPA chapter events, local chamber of commerce groups, and your own network. A short, honest message works best: you are researching how companies handle the new posting rules, it takes 20 minutes, and you are not selling anything.

**Rules for a good interview:**

- Ask about what they **actually did** in the past, not what they would do. "Tell me about the last posting you published" beats "Would you use a tool that...".
- Do not pitch until the last 5 minutes. If you describe your idea early, people get polite and stop being useful.
- Listen for **money, time and fear**: what they already spend, how many hours it takes, what happened when something went wrong.
- Let silence work. After an answer, wait a few seconds; people often add the most useful detail then.
- One goal per call: leave with a clear next step (a demo, a pilot, an introduction) or a clear "not for us".

## 1. Opening (2 minutes)

Say something close to this, in your own words:

> "Thanks for making time. I'm a software engineer based in Ontario, and I'm researching how companies are handling the new job posting rules that started in January: pay ranges, the AI disclosure, the vacancy statement, the 45-day follow-up and the record keeping. I'm not selling anything today. I just want to understand how you handle it in practice, what's easy and what's annoying. Is it okay if I take notes?"

Then confirm two facts before the questions:

- Roughly how many people does the company have in Ontario? (Under 25 means the rules don't apply; note it and adjust.)
- Roughly how many public job postings do they publish in a typical month?

## 2. Their current process (8 minutes)

Goal: map how a posting goes from idea to published, and who touches it.

1.  Walk me through the last job posting you published. Who wrote it, who approved it, and where did it go live?
2.  Where do your postings appear? (Careers page, Indeed, LinkedIn, job boards, agencies posting for you.)
3.  Do you start from a template? Who maintains it, and when was it last updated?
4.  When the rules changed in January, what did you change? Who did that work, and how long did it take?
5.  How do you decide the pay range on a posting today?
6.  How do you handle the AI disclosure? Do you use any AI or automatic screening in your hiring tools?
7.  After interviews, how do candidates hear back? How would you know if someone waited more than 45 days?
8.  Where are old postings stored? If an inspector asked for a posting from last spring, exactly what it looked like, how would you find it?

**Agency version:** ask the same questions per client. Also ask: how many clients do you post for, do they each send their own templates, and who is responsible if a posting breaks the rules?

## 3. Pain and stakes (6 minutes)

Goal: find out whether this is a real problem with real cost, or a minor chore.

1.  What part of the new rules has been the most annoying or confusing?
2.  Have you ever found a posting that didn't meet the rules after it went live? What happened, and how did you find out?
3.  Has a candidate, a client, a job board or anyone else ever raised a question about a posting? Tell me about it.
4.  How many hours a month does someone spend checking postings, chasing follow-ups or saving records?
5.  Who would be blamed if a posting broke the rules? How much does that worry them?
6.  What have you already tried to make this easier? (Templates, checklists, a lawyer, a spreadsheet, a free online checker.) What didn't work about it?
7.  **Agencies:** has a client ever asked you to prove your postings were compliant, or written it into a contract?

**Strong signals to listen for:** a specific incident, a named person who owns the problem, hours spent every month, money already spent on templates or legal advice, or a client contract that requires compliance.

**Weak signals:** "it's fine, we just added a line to our template", or no one can remember the last time they thought about it.

## 4. Tools and integrations (5 minutes)

Goal: learn which systems to connect to first, and how much access they would give.

1.  Which HR or recruiting system do you use? (BambooHR, Employment Hero/Humi, Collage, ADP, Workday, Greenhouse, Lever, Workable, JazzHR, something else, or none.)
2.  Do job postings get published directly from that system, or copied by hand to job boards?
3.  Are interviews tracked in that system or in calendars and email?
4.  If a tool could connect to that system and check everything automatically, with no change to how you work, who would need to approve the connection? IT, HR lead, owner?
5.  Would read-only access be acceptable? What would make you uncomfortable about connecting a new tool?
6.  Would you rather it send alerts (email or Slack) or show everything on a dashboard?

**Why this matters:** BambooHR's API already exposes job openings and applications, and unified ATS APIs (Merge, Kombo, Unified.to) connect to 50–110 ATSs through one integration. Their answers tell you which system to support first and whether a unified API is worth its monthly cost.

## 5. Solution reactions and willingness to pay (5 minutes)

Only now describe the idea, in two sentences, then test which parts matter:

> "I'm thinking about a tool that connects to your HR system, checks every live posting against the Ontario rules, keeps a dated copy of each posting for the 3-year record, and reminds you before any interviewed candidate passes 45 days. You wouldn't change how you work."

1.  Which part of that would be most useful to you? Which part wouldn't you use?
2.  What's missing that would make it a must-have?
3.  Who in your company would decide to buy something like this, and who controls that budget?
4.  What do you pay today for similar tools (HR software add-ons, compliance tools, legal templates)?
5.  If this saved the hours you mentioned earlier, what would feel like a fair monthly price? (Let them say a number first.)
6.  **Agencies:** would you pay per client, per posting, or one flat price? Could you charge clients for it as part of your service?

**Ideas to test, one at a time, after their own answer:** live monitoring of published postings, automatic archive, 45-day reminders, multi-province rules (BC, PEI), a browser extension while writing a posting, custom setup for their specific system.

## 6. Closing (2 minutes)

1.  Is there anything about job postings or hiring compliance that I didn't ask but should have?
2.  If I build an early version in the next few weeks, would you try it on a few of your real postings?
3.  Would you be open to a paid pilot at an early-customer price? (Ask this even if it feels awkward; a "yes" to paying is worth ten "sounds great".)
4.  Who else should I talk to? Could you introduce me to one or two people who deal with this?

End with: "Thank you, this was really useful. I'll follow up by email with what I learn." Send that email within 24 hours.

## 7. Notes template and scoring

Copy this block for each interview and fill it in right after the call, while it's fresh.

| Field                                 | Notes |
|---------------------------------------|-------|
| Name, role, company                   |       |
| Segment (agency / employer / lawyer)  |       |
| Ontario headcount, postings per month |       |
| HR or recruiting system used          |       |
| Biggest pain, in their words          |       |
| Specific incident or cost mentioned   |       |
| Hours per month spent today           |       |
| What they already pay for             |       |
| Most wanted feature                   |       |
| Price they suggested                  |       |
| Next step agreed (pilot, intro, none) |       |

**Score each interview from 0 to 3:**

| Score | Meaning                                                                 |
|-------|-------------------------------------------------------------------------|
| 0     | No real pain; already handled with a template                           |
| 1     | Some annoyance, but no time or money spent on it                        |
| 2     | Real pain with a specific incident or hours spent; interested in trying |
| 3     | Agreed to a paid pilot, or offered an introduction to a buyer           |

**Decision rule after 10 interviews:** if at least 3 people score a 3, build the version they asked for. If most score 0–1, stop or pivot, and look at which neighbouring problem came up most often in section 3. That problem is your next idea.

**Sources:** [BambooHR API (packagist)](https://root.packagist.org/packages/bamboohr/api) · [Unified.to – ATS unified APIs compared](https://unified.to/blog/ats_unified_apis_what_to_look_for_use_cases_and_options) · [Kombo ATS docs](https://docs.kombo.dev/ats/implementation-guide/context)
