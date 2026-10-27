# CheckON accuracy against the law, and demand: October 27, 2026

Measured on 2026-10-27 against the official text and 150 real Ontario postings. Nothing here is legal sign-off: the labels below are Claude's reading of the law, and they never count toward the two-human release gate in `backend/evals/README.md`.

**Result in one paragraph.** The law hasn't changed since the October 21 review, and the rule pack still matches it. On real postings the pay, range, applicability and AI checks agree with an independent reading of the law 94–97% of the time, and their remaining misses are mostly a currency-prefix parser bug and points a lawyer has to settle. Two checks are not good enough yet. The vacancy check finds 98% of missing statements but calls 25 of them a "vague" warning instead of a failure, so 9 non-compliant postings would get a passing result. The Canadian-experience check raised 24 flags on real postings that contained one real violation; most flags change between runs, and in some the model's label contradicts its own reason. The Refiner never invented a fact, and its code-built and library fixes are correct, but its Canadian-experience rewrites inherit the classifier's false alarms. On demand: the problem is real (two thirds of the real postings break at least one rule, mostly the vacancy statement), but the fix is one template line, there is no enforcement yet, and the posting check is turning into a free or bundled feature. The paid case is agencies buying proof across many clients, not the check itself. Model fees for all of this: about US$0.90.

**Update, same day.** Fixes 1–3 in section 4 are in rule pack CA-ON@1.3.0. On the same 150 real postings, the vacancy check now agrees with the independent labels 94% of the time (was 77%) and the Canadian-experience check 97% (was 85%). No non-compliant posting gets a passing result any more (was 9), and talent-pool postings are checked again. Before/after numbers are in section 7.

## 1. How this was measured

| Step | What | Cost |
| --- | --- | --- |
| Law | Re-fetched ESA 2000 and O. Reg. 476/24 from the e-Laws API and the Ministry guide page | free |
| Real postings | The 150 real postings in `backend/evals/golden/real` (48 employers; Lever 72, Greenhouse 60, Ashby 18) through the Inspector and Refiner once. Context: 25+ employees and `uses_ai_in_hiring: true`, so ON-AI-01 shows whether the posting carries an AI disclosure | US$0.31 |
| Independent labels | Four Claude subagents labelled every posting from the law text alone (section 2 of `docs/law-review-2026-10.md`), without seeing the rule pack, prompts, code or checker output. I then reviewed every disagreement against the law text | (subagents) |
| Stability | The 88 postings with any flag ran twice more | US$0.28 |
| Golden set | The 158 labelled synthetic, out-of-scope and adversarial cases, once, with `--refine` (`backend/evals/reports/2026-10-27-100603.md`). Their labels are Claude drafts too | US$0.28 |

Data: `backend/evals/reports/2026-10-27-real-blind-labels.json`, `-real-checker.json`, `-real-reruns.json` (the reports folder is gitignored, so these stay on this machine).

**Law check.** ESA: consolidated from January 1, 2026, last amendment still 2025, c. 13, Sched. 2; the repeal of s. 8.2 on proclamation (2024, c. 3, Sched. 2, s. 2 (2)) is still not in force. O. Reg. 476/24: "No amendments". Guide chapter: still "Updated: February 24, 2026". The rule pack changes since the review (1.2.0 form check under s. 8.3 (1), which names "any associated application form"; 1.2.1 awards and foreign-only experience labelled ok) are consistent with the text.

## 2. Accuracy on real postings

"Clear errors" are disagreements I side with the independent label on after reading the law. "Lawyer calls" are points the text doesn't settle (section 5).

| Rule | Scored | Agrees with the independent label | Clear checker errors | Lawyer calls | Same verdict in 3 runs (88 flagged postings) |
| --- | --- | --- | --- | --- | --- |
| ON-APPL-02 public posting in Ontario | 143 | 94% (135) | 2 | 9 | 98% |
| ON-PAY-01 pay shown | 129 | 95% (123) | 3 | 15 | 97% |
| ON-PAY-02 range ≤ $50,000 | 141 | 96% (135) | 3 | 3 | 97% |
| ON-AI-01 AI disclosure present | 144 | 97% (139) | 3 | 2 | 93% |
| ON-VAC-01 vacancy statement | 144 | 77% (111) | 27 | 6 | 76% |
| ON-CEX-01 Canadian experience | 144 | 85% (122) | 16 | 6 | 81% |

What the errors are:

- **Pay and range.** Every pass/fail on pay and width was right. All 5 ranges wider than $50,000 were caught (Gore Mutual $56,000, Alimentiv $66,500, Otilumionics $70,000, two P3 Vet postings $110,000 ending exactly at $200,000, which is not exempt). The 3 errors are one parser bug: "CAD $95,000 to CAD $125,000" reads as two single figures and "CAD$20.70-CAD$23.10" doesn't read at all, so the user is asked "which is right?" for a plain range. Asking on the two typo'd ranges ("$191,000K", "$100,00") is the right call.
- **Applicability.** Errors: Alan's Toronto/Europe engineering job was called "a general recruitment campaign", and Quantum Coffee's plain Toronto job asked a question. The other 6 disagreements are remote-in-Canada jobs, where asking is the current design (law review Q9a).
- **AI.** Missed Cohere's "We may use AI-enabled tools to screen and assess applicants". Accepted a job duty as a disclosure (Terminal: "use AI and automation to increase efficiency") and an NYC-only Covey notice. Real-posting false passes on AI tell an employer who must disclose that they're fine.
- **Vacancy.** In 25 postings with no statement, the classifier picked a title ("Electrical Intern (Fall 26)"), a location line ("Toronto / Full Time Permanent") or a recruiting line ("We're hiring a pharmacist to join our dynamic team") and called it vague. S. 8.5 (1) (a) requires "a statement disclosing whether the posting is for an existing vacancy or not", and the guide says the employer "must state" it; none of these do. Two more were passed outright ("We're currently seeking experienced veterinarians"; "You'll take over an established, full caseload").
- **Canadian experience.** Real postings held one clear violation (DoorDash: "You recently graduated from a Canadian university"), which was caught and fixed. The checker also raised 14 fails and 10 warnings. Wrong fails include security clearance ("obtain clearance under the Canadian Controlled Goods Program", 3 Telesat postings), licensing ("RIBO Level 2 Licence", "admitted to the bar of any Canadian province"), an American certification (AAADM), and sentences that never mention a place ("2-5 years across business operations"). The guide excludes "professional licensing or registration requirements". Only 6 of the 14 fails repeat across three runs. Two causes are visible in the model's own output: the label comes before the reason, and the prompt says to pick "the stricter one" when unsure, so it returns `violation` with reasons like "a generic degree is not a Canadian credential, so this is ok" and "borderline at most; labeled borderline".

**The result a user sees.** Leaving out the AI rule, which depends on the employer's answer: of the 90 postings that break a rule, 9 would get "Meets the rules", every one because a missing vacancy statement became a warning. Of the 52 compliant postings, 2 would get "Doesn't meet the rules" from a false Canadian-experience fail. Separately, 4 of the 150 postings (2.7%) were refused as French although each is in English; they only mention French as a skill ("Proficiency in French is considered an asset", "Bilingual").

## 3. Accuracy of the Refiner

| Fix | Real postings | Correct? |
| --- | --- | --- |
| AI disclosure inserted from the wording library | 91 of 91 fixed and verified | Yes. The sentence uses the statute's words, which the guide says is enough |
| Missing pay | 41 of 41 got the placeholder and a question, never an invented figure | Yes, by design |
| Range too wide | 5 of 5 got three code-built ranges | Yes. Each is exactly $50,000 wide, which Reg. s. 4 allows |
| Missing vacancy statement | Asks the employer, then inserts "This posting is (not) for an existing vacancy." | Yes (s. 8.5 (1) (a) wording). But the 25 that were called vague get only a warning |
| Canadian-experience rewrites | 14 fails: 4 rewritten and verified, 10 left with "the rewrite call gave no usable sentence" | Mixed: see below |

- The DoorDash and CapIntel rewrites are right.
- Two rewrites removed a requirement the law allows: "member in good standing of a Canadian bar association" became "a bar association", and the physiotherapy line lost the credential-assessment route the College uses. Both are licensing requirements.
- The 10 with no usable rewrite had nothing to fix (false fails), so the user is stuck with a failure they can't clear.
- Golden set: 5 of 26 planted violations weren't fixed. In one, "an established book of clients in / Canada that you can transition" is split across two sentences, so each half fails verification. The others are "Local home care experience required" and "An established network of donors ... in the Greater Toronto Area".
- No rewrite added a number or name (golden gate: 0). The golden gate "fixable failures fixed: 53.8%" mostly measures the scorer: 31 of its 36 misses are vacancy and range fixes that wait for the employer's choice by design.

## 4. Fixes, ranked by legal risk

Items 1–3 are fixed (section 7). Items 4–8 are still open.

1. **Missing vacancy statement shown as a warning** (9 false passing results in 150). Add classifier examples: titles, location or schedule lines and "we're hiring a X" are `none`. Consider making "vague" a fail, since s. 8.5 asks for a statement.
2. **Canadian-experience false alarms** (16 errors; flips between runs). Put `reason` before `label` in `CexLabel`. Limit "choose the stricter one" to violation vs borderline. Add examples for security clearance, bar admission and College registration, industry certifications, "based in the GTA", and duties that mention local clients.
3. **Talent-pool and "always hiring" postings for a named job told the rules don't apply** (golden: syn-vac-04, syn-vac-06, syn-mix-10; real: Alan). Reg. s. 2 (1) (a) excludes only a campaign "that does not advertise a specific position", and the guide's "must state that there is no existing vacancy" exists for these postings. Fix the `specific_position` line in `prompts/extract.md`.
4. **Tips counted as pay** (golden: syn-pay01-20, adv-04). ESA s. 1 (1) (d) excludes "tips or other gratuities" from wages. Add a `tips` pay kind.
5. **AI**: product or job-duty AI sentences accepted as a disclosure (golden syn-mix-15 and its adversarial copy adv-25, which is why the "injected text" gate failed; real: Terminal), and a clear disclosure missed (Cohere).
6. **English postings refused as French** (4 of 150). `contains_french` in `prompts/extract.md` should say that naming French as a skill doesn't count.
7. **"CAD $X to CAD $Y" and "CAD$X-CAD$Y"** in `app/compliance/money.py` (3 of 150).
8. **Refiner**: don't rewrite licensing requirements; join a requirement split across sentences before rewriting.

## 5. New questions for the employment lawyer

These add to the 14 in `docs/law-review-2026-10.md`, section 6.

15. A Toronto job whose posted range "covers geographical markets within British Columbia" (4 DoorDash postings): does that meet s. 8.2 (1)? CheckON: pass.
16. A company-wide band, "$100k - $500k" for all engineers in every country (3 Tenstorrent postings): exempt under Reg. s. 3, para. 2 as written, or not "expected compensation for the position"? CheckON: exempt.
17. Pay with a figure for base but none for commission or bonus ("+ Commission eligible"; on-target earnings only). The guide says "each type" must be described. CheckON: pass on the base figure.
18. Implied vacancy wording: "This position is a replacement role", "for our new store opening in September", "We are actively hiring": statements under s. 8.5 (1) (a)?
19. "We use an AI scribe to help us take notes and review interviews", and "We may use AI tools to support certain stages of the hiring process": disclosures under s. 8.4 (1)?
20. Co-op internships (ESA s. 3 (5)) and "Full-Time Contractor" clinic roles: covered by Part III.1?

CheckON's reading that an exempt posting's range may be wider than $50,000 (Cohere, Faire, General Magic) follows the text: s. 8.2 (3) applies "for the purposes of subsection (1)", and (1) doesn't apply to an exempt posting.

## 6. Is there demand?

**Verdict.** The pain is real and measurable, but cheap to fix and not yet enforced, and the core check is already free elsewhere. A paid product has to sell volume, consistency and proof to agencies, not a one-off check.

**What the real postings show** (independent labels, 149 covered postings from established employers on modern applicant tracking systems):

| Finding | Postings |
| --- | --- |
| No plain vacancy statement | 99 (66%) |
| No pay (not exempt) | 43 (29%), the same share Indeed reported for Ontario in June 2026 |
| Range wider than $50,000 | 5 (3%) |
| No AI statement (a breach only if they use AI) | 88 (59%) |
| Canadian-experience violation | 1 (0.7%) |
| Break at least one rule (AI aside) | about 63% |

The outreach run of 2026-10-26 points the same way: 30 postings from 10 Ontario tech employers, 11 compliant, 9 not compliant, 9 needing answers, 1 refused.

**For paying demand**

- Gaps remain: 71% of Ontario postings showed pay in June 2026 and no occupation passed 90% ([Indeed Hiring Lab, Jul 23 2026](https://hiringlab.indeed.com/en-ca/2026/07/23/growth-in-canadian-salary-transparency-driven-by-two-provinces/)). Only 55% of 200 Canadian employers had updated postings ([Littler, Oct 21 2026](https://www.littler.com/press/press-release/77-canadian-employers-make-workforce-changes-amid-economic-pressures-us-tariffs)).
- The AI rule is undefined and agencies carry the client's tools ([Osler in HR Reporter, Feb 23 2026](https://www.hrreporter.com/news/hr-news/ai-in-hiring-ontario-employers-grappling-with-new-job-posting-disclosure-requirement/394101); [Staffing Journal, Jul 29 2026](https://www.staffingjournal.ca/the-undefined-word-ontarios-new-ai-disclosure-and-the-recruiters-risk/)).
- Vendors are building paid products: WorkSignal from US$197/month (checked), Tanda, Ontario Employer Tools kits at CA$19–59.
- Rules are spreading: New Brunswick since June 12 2026; Newfoundland passed, not in force ([Agendrix, Oct 7 2026](https://www.agendrix.com/blog/pay-transparency-canada)).

**Against**

- No enforcement found: no blitz, ticket or published count for Part III.1; the Minister spoke of "repeated and habitual violations" ([Globe and Mail, Jan 13 2026](https://www.theglobeandmail.com/business/article-ontario-hiring-pay-transparency-rules-enforcement/)). A first notice is likely $250 (O. Reg. 289/01; the research agent's reading).
- Employers comply with templates: the most common failure above is one missing sentence.
- A free checker covers the same four items with fix wording, plus a free Sheets add-on for the 45-day and 3-year dates ([ontarioemployertools.com](https://ontarioemployertools.com/), checked).
- The check is being bundled: WorkSignal blocks wide ranges, locks the AI line, flags Canadian experience and syncs with Greenhouse, Lever and Ashby ([worksignal.com/compliance](https://worksignal.com/compliance), checked). A job board checks drafts in its own form ([Hire a Canadian, Oct 20 2026](https://hirea.ca/guides/ontario-job-posting-rules-2026)).

**Competitors**

| Name | Ontario coverage | Price |
| --- | --- | --- |
| Ontario Employer Tools | Paste check of the four posting items, fix wording, Sheets hiring log | Free; kits CA$19–59 |
| WorkSignal | Range validator, AI line, Canadian-experience scan, 45-day and records, ATS sync; sold with voice screening | From US$197/month |
| Datapeople (Payscale) | Missing pay and AI line, templates | Quote |
| Tanda | Pre-publish range and AI checks | Not stated |
| Hire a Canadian | Check inside its posting form | Not stated |

**Where CheckON can win.** Accuracy is a real differentiator: WorkSignal's compliance page says candidates "must be notified within 45 days of an AI-based decision", which isn't the rule (45 days after the last interview, Reg. s. 5). That edge only holds once the vacancy and Canadian-experience problems in section 4 are fixed, since false alarms are what a recruiter notices first. Sell the Agency plan: checks across every client's postings, per-client AI wording, the 3-year record, and other provinces next. Starter at $79 competes with free tools.

**Not measured here.** CheckON's own usage (weekly checks, returning users, contact requests: the PRD's 8-week targets). The `/stats` page needs the admin sign-in, and the browser pane is signed in to the test account.

## 7. After fixes 1–3 (rule pack CA-ON@1.3.0)

**What changed**

- **Vacancy** (`prompts/classify.md`, `prompts/extract.md`, ON-VAC-01 1.2.0): "vague" is now only for a line about whether or when the job is open that doesn't settle it, such as future hiring or ongoing applications. A title, a location or contract line, a description of the work, or "we're hiring a X" is `none`, because every posting says it is hiring. Four new examples, taken from the real postings, show this.
- **Canadian experience** (`prompts/classify.md`, `prompts/classify_form.md`, ON-CEX-01 1.3.0):
  - The model writes its reason before its label (`CexLabel`, `VacancyLabel`, `AILabel` and `FormLabel` field order).
  - "Borderline over ok" is gone. A sentence that names no place (Canada, a province, North America or the local area) is ok.
  - Canadian experience stays a violation even when it is only an asset. Ontario or another province as an asset is borderline.
  - New ok lines cover licences and registrations (RIBO, bar admission, Ontario colleges, CPA), security clearances, where the applicant must live, and duties of the job. Five examples were added.
- **Talent pools** (`prompts/extract.md`): a named job is a specific position even when it is for a talent pool, future openings or ongoing hiring. "We're always looking for talented people" and "Now hiring, all positions" stay general campaigns.

**Real postings, same 150, same independent labels**

| Rule | Before | After |
| --- | --- | --- |
| ON-VAC-01 vacancy statement | 77% (111/144) | 94% (136/145) |
| ON-CEX-01 Canadian experience | 85% (122/144) | 97% (140/145) |
| ON-AI-01 AI disclosure present | 97% (139/144) | 99% (144/145) |
| ON-APPL-02 public posting in Ontario | 94% (135/143) | 96% (137/143) |
| ON-PAY-01 / ON-PAY-02 (code unchanged) | 95% / 96% | 95% / 97% |
| Non-compliant postings shown as passing (AI rule aside) | 9 | 0 |
| Canadian-experience fails raised | 14 (1 real violation) | 2 (the real one and the physiotherapy credential, a lawyer call) |
| Canadian-experience fails the Refiner couldn't clear | 11 | 0 |
| Missing vacancy statements shown only as a warning | 25 | 0 |

**Same verdict in 3 runs (the same 88 flagged postings)**

| Rule | Before | After |
| --- | --- | --- |
| ON-CEX-01 | 81% | 94% |
| ON-VAC-01 | 76% | 94% |
| ON-AI-01 | 93% | 98% |
| ON-PAY-01 / ON-PAY-02 | 97% / 97% | 98% / 98% |
| ON-APPL-02 | 98% | 95% |

**What's left on these postings.** None of the remaining vacancy or Canadian-experience disagreements is a clear error; each is a lawyer call:
- Vacancy:
  - 5 lines that one reading calls vague and the checker calls no statement ("Expected start date: November 2", "we hire continuously"). Both readings say the posting doesn't comply.
  - Club Monaco's "for our new store opening" and Smile's "new role" / "replacement role" (question 18).
- Canadian experience: borderline wording such as the CIP designation, PHIPA knowledge and "Canadian or U.S. credentials are an asset".
- AI: one clear error, the NYC-only Covey notice read as a disclosure.
- Applicability: the extra questions are remote-in-Canada jobs, as before, plus run-to-run noise. Alan's Toronto/Europe job now asks whether the work is in Ontario, where it used to say the rules don't apply.

**Golden set (158 Claude-drafted cases), before → after**

| Rule | Before | After |
| --- | --- | --- |
| ON-APPL-02 | 154/158 (4 talent-pool or always-hiring misses) | 158/158 |
| ON-VAC-01 | 151/158 | 158/158 |
| ON-CEX-01 | 153/158, 1 false fail | 155/158, 2 false fails, recall 25/25 |
| Gate: recall on Canadian-experience violations | 100% | 100% |
| Gate: refiner rewrites that add a fact | 0 | 0 |

- The two golden Canadian-experience false fails are "Knowledge of Canadian GAAP" with a CPA designation, which was already failing before, and "Ontario winter" plowing experience as an asset. Both flip between runs.
- The other gates are unchanged: they rest on items 4–8 and on the scorer issue in section 3.

**Tests**
- 376 compliance tests pass without the database. The whole suite (819) passed earlier in the session, before the local database stopped.
- 13 live tests pass, including 44/44 sample sentences (11 new, from the real postings) and 4 new live postings: a talent pool, always hiring with no statement, a title plus a hiring line, and a general campaign.
- Data: `backend/evals/reports/2026-10-27-real-checker-after.json` and `-real-reruns-after.json`. Golden run: `2026-10-27-112837.md`. Fees for the fixes and re-runs: about US$3.
