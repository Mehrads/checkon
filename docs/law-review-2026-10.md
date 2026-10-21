# CheckON against Ontario's job posting law: review of October 2026

Reviewed on 2026-10-21 against the official text. Nothing here is legal sign-off: every rule marked `interpretation: true` in `backend/rulepacks/CA-ON/rules.yaml` still needs an employment lawyer's review, and the questions for that review are in section 6.

**Result in one paragraph.** The thresholds in the rule pack match the law (25 employees inclusive; $50,000 range limit inclusive; $200,000 exemption strict). Twelve mismatches were found and fixed, each with a test: citations now name verified sections; the $200,000 exemption is read from the posting itself instead of always asking the employer; commission is treated as wages; "automated system" wording no longer counts as an AI disclosure; the Canadian-experience examples now carry the Ministry's categories (education credentials, professional network, and the licensing exclusion); the applicability questions follow the Ministry's counting rule and no longer fire on every posting; and the results page shows each rule's citation. Live Claude runs labelled 32 of 32 sample sentences as expected and gave the expected verdicts on four edge-case postings, for about US$0.07 in API fees. Fourteen points of interpretation are left for the lawyer.

## 1. Sources

All retrieved on 2026-10-21.

| Source | Where | State on retrieval |
| --- | --- | --- |
| *Employment Standards Act, 2000*, S.O. 2000, c. 41 (ESA), Part III.1 "Job Postings" (ss. 8.1–8.7), s. 1 (1) "wages", s. 3 (1), s. 15 (7.1), (7.1.1) | [ontario.ca/laws/statute/00e41](https://www.ontario.ca/laws/statute/00e41) (text pulled from the e-Laws API, `laws/api/v2/legislation/en/doc-search/statute/00e41`, because the page renders in the browser only) | "Consolidation Period: From January 1, 2026 to the e-Laws currency date." Last amendment: 2025, c. 13, Sched. 2. Contains "not yet in force" provisions (see section 9). |
| O. Reg. 476/24, *Rules and Exemptions re Job Postings*, under the ESA | [ontario.ca/laws/regulation/240476](https://www.ontario.ca/laws/regulation/240476) | "Consolidation period: January 1, 2026 – e-Laws currency date (October 16, 2026). No amendments." The regulation was filed November 29, 2024; its sections came into force January 1, 2026. |
| O. Reg. 285/01, *When Work Deemed to be Performed, Exemptions and Special Rules*, s. 2.1 (Crown exemption) | [ontario.ca/laws/regulation/010285](https://www.ontario.ca/laws/regulation/010285) | Consolidation from July 1, 2025. |
| Ministry of Labour, Immigration, Training and Skills Development, *Your guide to the Employment Standards Act*, chapter "Requirements related to publicly advertised job postings" | [ontario.ca/document/your-guide-employment-standards-act-0/requirements-related-publicly-advertised-job](https://www.ontario.ca/document/your-guide-employment-standards-act-0/requirements-related-publicly-advertised-job) | Published February 4, 2026; updated February 24, 2026. Guidance, not law: quoted below as "the guide". |

Amending Acts, from the e-Laws section notes: ss. 8.1–8.4 and s. 15 (7.1) by 2024, c. 3, Sched. 2 (*Working for Workers Four Act, 2024*), in force 01/01/2026; ss. 8.5, 8.6 and s. 15 (7.1.1) by 2024, c. 19, Sched. 2 (*Working for Workers Five Act, 2024*), in force 01/01/2026; s. 8.7, the "job posting platform" definition and s. 15 (8.3) by 2025, c. 13, Sched. 2, in force 01/01/2026.

## 2. What the law says

Quotations are from the texts above. Section numbers are the ESA's unless marked "Reg." (O. Reg. 476/24).

### 2.1 Who is covered

- **Employer size.** Reg. s. 1: "Part III.1 of the Act does not apply to an employer that employs fewer than 25 employees on the day the publicly advertised job posting is posted." So 25 employees are covered; 24 are not.
- **How employees are counted** (guide): "It is the individual number of employees that are counted, and not the number of 'full-time equivalents.' Part-time employees and casual employees each count as 1 employee, regardless of the number of hours they work." All Ontario locations count together; related employers treated as one under ESA s. 4 are counted together; employees on leave, on lay-off, on strike, probationary and fixed-term employees all count; a temporary help agency's assignment employees count for the agency, not for the client. The guide frames the count as employees "employed in Ontario", consistent with ESA s. 3 (1).
- **Prospective employers.** S. 8.1: "'employer' means an employer as defined in subsection 1 (1) and includes a prospective employer".
- **Crown bodies.** O. Reg. 285/01, s. 2.1 (1): "The Crown, a Crown agency or an authority, board, commission or corporation all of whose members are appointed by the Crown, and any employees of such an employer, are exempt from every provision of the Act except for those listed in subsection (2)." Part III.1 is not in that list. The guide says the same.
- **Start date.** Every section of Part III.1 is in force from January 1, 2026. The guide: "These rules generally apply to publicly advertised job postings that are posted on or after January 1, 2026."

### 2.2 What is a "publicly advertised job posting"

Reg. s. 2 (1): "'publicly advertised job posting' means an external job posting that an employer or a person acting on behalf of an employer advertises to the general public in any manner but does not include,
(a) a general recruitment campaign that does not advertise a specific position,
(b) a general help wanted sign that does not advertise a specific position,
(c) a posting for a position that is restricted to existing employees of the employer, or
(d) a posting for a position for which work is to be, (i) performed outside Ontario, or (ii) performed outside Ontario and in Ontario and the work performed outside Ontario is not a continuation of work performed in Ontario."

Guide: "A specific position refers to a defined function that an individual performs for the employer." Examples of excluded campaigns: an advertisement that only reads "we are hiring" or "we are always looking for talent". Also: "where an employer includes in the posting a link to a website or a copy of a document containing information relevant to the posting, the information included in those sources is considered to be part of the posting." And: when a third party or a job board carries the posting, "the employer is responsible for ensuring the requirements are followed."

### 2.3 Expected compensation

- S. 8.2 (1): "Every employer who advertises a publicly advertised job posting shall include in the posting information about the expected compensation for the position or the range of expected compensation for the position."
- Reg. s. 2 (2): "'compensation' means wages". ESA s. 1 (1): wages means "(a) monetary remuneration payable by an employer to an employee under the terms of an employment contract ... (b) any payment required to be made by an employer to an employee under this Act, and (c) any allowances for room or board ... but does not include, (d) tips or other gratuities, (e) any sums paid as gifts or bonuses that are dependent on the discretion of the employer and that are not related to hours, production or efficiency, (f) expenses and travelling allowances, or (g) ... employer contributions to a benefit plan and payments to which an employee is entitled from a benefit plan". Guide: "compensation includes items such as an hourly rate, salary, commission, piece work rate, or a bonus that is related to the employee's hours of work, production or efficiency" and "excludes items such as tips, travel expense reimbursements, stock options, or bonuses that are both discretionary and unrelated to hours of work, production or efficiency."
- **Exemption.** S. 8.2 (2) with Reg. s. 3: subsection 8.2 (1) does not apply where "1. The publicly advertised job posting is for a position that has an expected compensation equivalent to more than $200,000 annually. 2. The publicly advertised job posting is for a position that has a range of expected compensation that ends at an amount equivalent to more than $200,000 annually." Guide example: "$210,000, or ... from $170,000 to $210,000" is exempt. Exactly $200,000 is not.
- **Range limit.** S. 8.2 (3) with Reg. s. 4: "a range of expected compensation shall not exceed an amount equivalent to $50,000 annually." Guide: "$85,000 to $135,000 may be included ... $85,000 to $140,000 cannot". So a width of exactly $50,000 is allowed.
- Guide on form: a figure or a range, "they are not required to include both"; "If the expected compensation package includes more than one type of compensation, the employer must include information about each type" (hourly rate plus commission: both); "Where a monetary amount cannot be provided, the employer may provide information about how the compensation would be earned. For example: a bonus of up to 10% of the annual salary"; for commissions "the employer may state that the successful candidate can expect to earn up to a certain amount in sales commissions".

### 2.4 Existing vacancy

S. 8.5 (1): "Every employer who advertises a publicly advertised job posting shall include in the posting, (a) a statement disclosing whether the posting is for an existing vacancy or not; and (b) such other information as may be prescribed." Nothing is prescribed under (b). Guide: "if the posting is for an existing vacancy, the employer must state that it is for an existing vacancy; if the posting is not for an existing vacancy, the employer must state that there is no existing vacancy. An existing vacancy means a position that is imminently available for a qualified candidate to fill."

### 2.5 Artificial intelligence

- S. 8.4 (1): "Every employer who advertises a publicly advertised job posting and who uses artificial intelligence to screen, assess or select applicants for the position shall include in the posting a statement disclosing the use of the artificial intelligence."
- Reg. s. 2 (1): "'artificial intelligence' means a machine-based system that, for explicit or implicit objectives, infers from the input it receives in order to generate outputs such as predictions, content, recommendations or decisions that can influence physical or virtual environments". Guide: "Whether a particular system falls within the scope of the definition ... will depend on the specific facts of each case."
- Guide: the duty "applies equally where the employer engages a third party (for example, a recruiting firm) to screen, assess or select applicants on their behalf", and "It is enough for the employer to state that artificial intelligence is used to screen, assess or select applicants."

### 2.6 Canadian experience

S. 8.3 (1): "No employer who advertises a publicly advertised job posting shall include in the posting or in any associated application form any requirements related to Canadian experience." S. 8.3 (2) allows prescribed exceptions; none are prescribed. Guide: the prohibition covers requirements "including: work experience, education credentials, a requirement to have an established professional network or client base" and "does not apply to professional licensing or registration requirements." The guide also points to the Ontario Human Rights Code and the OHRC policy on removing the "Canadian experience" barrier.

### 2.7 After the posting: interviews and records

- S. 8.6 with Reg. s. 5: an employer who interviews an applicant must, "within 45 days after the date of the interview or, if the employer interviews the applicant more than once ..., within 45 days after the date of the last interview", tell the applicant "Whether a hiring decision has been made in respect of the publicly advertised job posting", "in person, in writing or using technology". Reg. s. 2 (2) defines "interview" and excludes "preliminary screening before the selection of applicants for such a meeting". Guide: this duty applies to interviews on or after January 1, 2026 even for postings published earlier.
- S. 15 (7.1): retain "copies of every publicly advertised job posting within the meaning of Part III.1 and any associated application form for three years after access to the posting by the general public is removed." S. 15 (7.1.1): retain the information given under s. 8.6 "for three years after the day the information was provided to the applicant." Guide: keep each revised version, and any linked document that forms part of the posting.

### 2.8 Other provisions in force that touch postings

- S. 8.7 and s. 15 (8.3): duties on persons operating job posting platforms (fraud-reporting mechanism and policy). An employer's own careers site is not a platform; CheckON does not display postings and is not one.
- The Human Rights Code and the AODA's recruitment accommodation notice are outside the ESA and outside CheckON's scope; the guide flags the Code for Canadian-experience wording.
- S. 8.2 carries the note "On a day to be named by proclamation ... section 8.2 of the Act is repealed. (See: 2024, c. 3, Sched. 2, s. 2 (2))". Not in force; see section 9.

## 3. Requirement matrix

Legend: **covered** (matches the text), **partly** (right direction, a gap remains), **wrong** (fixed in this review), **missing** (not checked; see section 5). "Now" describes the branch after the fixes in section 4.

| # | Requirement | Law | Rule / code / prompt | Before | Now |
| --- | --- | --- | --- | --- | --- |
| 1 | Fewer than 25 employees exempt; 25 covered | Reg. s. 1 | ON-APPL-01, `employer_size`: `headcount >= 25` | covered (citation named only the Part) | covered; citation names s. 1; question carries the counting rule |
| 2 | Count on the posting day, every employee incl. part-time/casual/on leave, all Ontario locations, related employers | guide; ESA s. 4 | question text; `employer.py` search uses worldwide or Ontario totals | partly: question didn't say how to count | partly: question fixed; the search's worldwide figure is a proxy (section 6, Q9) |
| 3 | Crown bodies exempt | O. Reg. 285/01, s. 2.1 | nothing | missing | missing (section 5) |
| 4 | External posting to the general public; exclusions (a)–(d) | Reg. s. 2 (1) | ON-APPL-02, `public_posting`; `extract.md` facts | partly: `internal_only` came back unknown on every posting, so every check asked the internal-only question (live run); hybrid roles unaddressed | covered for (a)–(c) and (d)(i); (d)(ii) "continuation" defaults to covered (section 6, Q9) |
| 5 | Linked documents are part of the posting | guide | nothing | missing | missing (section 5) |
| 6 | Include expected compensation or a range | s. 8.2 (1) | ON-PAY-01, `pay_disclosed` | covered | covered |
| 7 | Compensation = wages; commission and production bonuses count; discretionary bonus, tips, benefits, stock options don't | Reg. s. 2 (2); ESA s. 1 (1); guide | `PayKind`: wage / commission / bonus / equity / benefits | wrong: commission-only was a warning saying the point is "not settled" | covered: commission passes; `no_wages` message states what wages are; a bonus-only posting still fails (section 6, Q5) |
| 8 | Exempt above $200,000 (strictly), on the pay or the top of the range | Reg. s. 3 | `_exempt`, `_range_width` | wrong: exemption applied only after the employer confirmed it, even when the posting said $150,000–$250,000; a wide range ending above $200,000 was `needs_input` | covered: read from the posting when pay is by the year, month or week, or by the hour with hours known; otherwise the employer is asked |
| 9 | Range not wider than $50,000 a year, inclusive | Reg. s. 4 | ON-PAY-02: `width <= cap` | covered | covered; boundary cases added by unit (year, hour, week, month) |
| 10 | "Equivalent to ... annually" for hourly, weekly, monthly pay | Reg. ss. 3–4 | `annualise`: hours × 52, × 52, × 12; 40 h default, ±10% asks hours | partly (interpretation) | unchanged (section 6, Q2–3) |
| 11 | Open-ended pay ("$70,000+", "up to $90,000") | s. 8.2 (1), (3) | ON-PAY-02 fails as "not a range" | partly (interpretation) | unchanged (Q1) |
| 12 | Packages with several parts: each part disclosed | guide | nothing beyond extracting figures | missing | missing (Q4) |
| 13 | Statement whether the posting is for an existing vacancy or not | s. 8.5 (1) (a) | ON-VAC-01, `vacancy_statement`; wording library | covered; vague = warning is interpretation | covered; question carries the guide's definition (Q6) |
| 14 | Disclose AI used to screen, assess or select applicants | s. 8.4 (1) | ON-AI-01, `ai_disclosure`; wording library | partly: "automated tools" wording counted as an AI disclosure | covered: only wording that names AI / machine learning counts; third-party use named in the question (Q7) |
| 15 | AI definition | Reg. s. 2 (1) | question's examples (ATS ranking, resume scoring, chat screening) | interpretation | unchanged (Q7) |
| 16 | No Canadian-experience requirement in the posting | s. 8.3 (1) | ON-CEX-01 classifier | partly: examples lacked education credentials, professional network, and the licensing/registration exclusion | covered for the guide's categories; "preferred", "Ontario", "North American", "knowledge of" wording stays borderline (Q8) |
| 17 | ... or in any associated application form | s. 8.3 (1) | not in v1 | missing | missing (section 5) |
| 18 | 45-day notice to interviewed applicants | s. 8.6; Reg. s. 5 | ON-INT-01 (process rule, not checked) | missing from the posting check by design | citation corrected (section 5) |
| 19 | Record retention, 3 years | s. 15 (7.1), (7.1.1) | ON-REC-01 (process rule) | missing by design; citation vague | citation names the sections and the trigger dates (section 5) |
| 20 | In force for postings posted on or after 2026-01-01 | amendment notes; guide | `effective_from: 2026-01-01`; `not_in_force` message | covered | covered; "posted on the day" case added |
| 21 | Citation shown with each verdict | product (04-V1-Scope §2) | `RuleResult.citation` existed; the results page didn't render it | wrong | covered: `Findings.tsx` shows it |

Wording library (`wording.yaml`): "This posting is for an existing vacancy." / "This posting is not for an existing vacancy." use the statute's own words for s. 8.5 (1) (a); "We use artificial intelligence to screen, assess or select applicants for this position." matches what the guide says is enough under s. 8.4 (1). Both still need the lawyer's sign-off (`reviewed_by` is empty). The pay placeholder is a marker, not wording that satisfies anything.

## 4. Mismatches found and how each was fixed

Each fix has a test; the file is named. Rule pack version is now `CA-ON@1.1.0` (Technical Design §10: a rule change is a new pack version; result-cache keys include it).

1. **Citations named only "Part III.1"; the file header said section numbers were unverified.** Every rule now cites the section: Reg. s. 1 (ON-APPL-01), Reg. s. 2 (1) (ON-APPL-02), s. 8.2 (1) + Reg. ss. 2 (2), 3 (ON-PAY-01), s. 8.2 (3) + Reg. ss. 3, 4 (ON-PAY-02), s. 8.5 (1) (a) (ON-VAC-01), s. 8.4 (1) + Reg. s. 2 (1) (ON-AI-01), s. 8.3 (1) (ON-CEX-01), s. 8.6 + Reg. s. 5 (ON-INT-01), s. 15 (7.1), (7.1.1) (ON-REC-01). ESA rules link to the statute, not the regulation. Test: `test_rulepack.py::test_every_rule_cites_a_section`.
2. **The $200,000 exemption always needed the employer's confirmation.** Reg. s. 3 is met on the face of a posting whose pay, or top of range, is more than $200,000 a year. `checks.py::_exempt` now reads it from the posting when pay is stated by the year, month or week, or by the hour with the hours known; the employer is asked only for hourly pay with unknown hours (`confirm_exemption`) or when no pay is stated. An explicit "no" from the employer still wins (Q11). Tests: `tests/pay.yaml` "wide range ending above 200,000 is exempt on its face", "single figure just above 200,000 ...", "wide range ending exactly at 200,000 is not exempt", "monthly pay above 200,000 ...", the three hourly $80–$110 cases.
3. **Commission-only was a warning whose message said the point is "not settled".** Commission is wages (ESA s. 1 (1); guide). `commission_only_verdict` is now `pass` with an accurate message; the parameter stays so the lawyer can set it back. Test: `pay.yaml` "commission only is expected pay".
4. **`no_wages` said "Expected pay means wages" without saying what wages are.** The message now lists salary, hourly rate, commission and a bonus tied to hours, production or efficiency.
5. **The AI classifier counted "automated tools" as an AI disclosure.** S. 8.4 (1) asks for "a statement disclosing the use of the artificial intelligence". `classify.md` and the ON-AI-01 examples now label "automated system" / "applicant tracking system" sentences `none` and "AI-assisted" / "machine learning" sentences `uses_ai`. Tests: `test_inspector.py::test_classifier_prompt_carries_rule_citations_and_examples`; `ai.yaml` "uses AI, posting mentions only an automated system"; live sample 8/8.
6. **The AI question didn't cover recruiters acting for the employer** (guide). Question text updated; `test_engine.py` adjusted.
7. **Canadian-experience examples lacked the guide's categories.** Added: "Bachelor's degree from a Canadian university" and "An established network of clients in Canada" (violation); "Registered with the College of Nurses of Ontario" (ok). Tests: `cex.yaml` two new cases; live sample 18/18.
8. **The headcount question didn't say how to count.** Now: on the day the job is posted, every employee including part-time, casual and on leave (guide). `test_engine.py` adjusted.
9. **Every live check asked "Is this posting open only to your existing employees?"** because `extract.md` let the model answer unknown when the text said nothing. Reg. s. 2 (1) (c) excludes a posting "restricted to existing employees": no restriction in the text means not restricted. The prompt now says so; the live posting sample went from 4/4 `needs_input` to the expected gate verdicts. The same prompt now treats an Ontario-based role with travel or hybrid work as work in Ontario (Reg. s. 2 (1) (d)(ii) excludes it only where the outside work is not a continuation of Ontario work; the continuation test itself is Q9). Tests: `applicability.yaml` "hybrid role based in Ontario", "remote role ..." cases; `test_live.py::test_live_law_review_postings`.
10. **The vacancy question lacked the guide's definition.** Now asks about "a position that is imminently available for a qualified candidate to fill".
11. **The results page did not show the rule's citation** although 04-V1-Scope §2 promises it and the API returns it. `frontend/src/components/Check/Findings.tsx` renders `result.citation` under each finding (biome clean; the landing page was not touched).
12. **Design doc drift.** `02-Technical-Design.md` §2 sources line (sections verified, guide linked), the ON-PAY-01 row ("employer confirms" removed; commission is wages), the §8 Layer 1 table, and the §14 commission question.

Not a mismatch, but checked: the 25-employee boundary (24 / 25 / 26 cases), the $50,000 boundary by unit, the $200,000 boundary at exactly $200,000 and $200,001, the posting-date boundary (2025-12-31 vs 2026-01-01), "competitive salary" / "DOE" (no figure → fail), the pay placeholder (needs_input), talent-pool postings (public posting; must say there is no existing vacancy), the employer's vacancy answer alone not satisfying s. 8.5 (the posting must say it), and AI use unknown with a "we don't use AI" statement (still asks). Multiple postings and French text are refused before any verdict (`test_inspector.py`, existing).

## 5. Gaps outside the posting text, and how CheckON should say so

| Gap | Law | What CheckON does today | Recommendation |
| --- | --- | --- | --- |
| 45-day notice to interviewed applicants | s. 8.6; Reg. s. 5 | ON-INT-01 exists as a process rule; the report omits it | Return process rules in the report as reminders (new `reminders` list built from `kind: process` rules: citation + one line) and show an "After you post" box under the findings: "Within 45 days of an interview (or the last one), tell the applicant whether a hiring decision has been made, in person, in writing or by email, text or portal update." |
| Record retention | s. 15 (7.1), (7.1.1) | ON-REC-01, same | Same box: "Keep a copy of this posting, every revised version, any linked document and any application form for 3 years after it comes down, and what you told each interviewed applicant for 3 years." Offer "download this version" on the finished posting. |
| Application forms | s. 8.3 (1); s. 15 (7.1) | Not checked in v1 (04-V1-Scope §4) | One line under the result: "Checked: the text you pasted. Not checked: your application form, documents the posting links to, and what happens after you post." Phase 3 checks the form. |
| Linked documents are part of the posting | guide | Not checked | Same line; the paste form's help text can say "paste any linked document too". |
| Crown bodies exempt | O. Reg. 285/01, s. 2.1 | Not known; such postings are checked as if covered | Low priority: a "we are a Crown agency" answer could set the gate to not applicable. Listed for the lawyer (Q9). |
| Third-party and job-board postings | guide | Nothing to do: the employer stays responsible | Covered by the FAQ's "recruiting agencies that post for them". |
| Headcount from a web search | Reg. s. 1; guide | Worldwide figures are a proxy for Ontario; "assumed" when nothing is found | Keep (the safe direction is to apply the rules); the `search_pass` message already says "we treat the employer as having 25 or more employees in Ontario". |

Site copy (`frontend/src/components/Site/Landing.tsx`, not edited because another session owns its layout): the FAQ answers are accurate as far as they go. Suggested extra FAQ entry, in generic words (marketing copy must not name specific legal rules): *"What doesn't it check? Only the text you paste. An application form, a document the posting links to, and anything that happens after you post are outside the check."* The hero line "shows what doesn't comply" is backed by the engine for the posting text; the FAQ entry above keeps it honest.

## 6. Questions for the employment lawyer

Each is a point where the text needs a reading. CheckON's current reading is stated so the answer can be "yes" or a correction.

1. **Open-ended pay.** "$70,000+" or "up to $90,000": is that "information about the expected compensation" (pass), or not a range at all (CheckON: ON-PAY-02 fail, with the fix being to give both ends)?
2. **Hourly ranges.** What converts an hourly range to "an amount equivalent to $50,000 annually"? CheckON uses hours stated by the employer, else 40 h/week, and asks for the hours when the result is within 10% of the limit. Should hours stated in the posting (e.g. "30 hours/week") be read and used, and should a part-time job's actual hours decide?
3. **Weeks and months.** 52 weeks a year and 12 months, with no allowance for 52.14 weeks: acceptable?
4. **Commission and packages.** (a) Does the $50,000 limit apply to a range of expected commission, to on-target earnings, or only to base pay? (CheckON applies it to base pay only.) (b) "Salary $60,000 plus commission" with no commission figure: does the salary alone satisfy s. 8.2 (1), given the guide's "each type" statement? (c) "Commission only, 10% of sales", no dollar figure: enough under the guide's "how the compensation would be earned"? (CheckON fails it: no amount.)
5. **Bonus without base pay.** A posting giving only a production or performance bonus: wages (pass) or not (CheckON: fail)?
6. **Vacancy statements.** (a) "We may hire for this role in the future" or "applications accepted on an ongoing basis": a failure to state (fail) or a weak statement (CheckON: warning)? (b) Is "This role is currently open" a statement that the posting is for an existing vacancy? (c) Does the statement have to use the words "existing vacancy"?
7. **AI.** (a) Is a sentence that says "automated system" or "applicant tracking system" without the words AI/machine learning a disclosure under s. 8.4 (1)? (CheckON: no.) (b) Are rule-based knockout questions, keyword matching and ATS auto-ranking "artificial intelligence" under Reg. s. 2 (1)? (CheckON's question says ranking, scoring and chat screening count.) (c) Is "Screening is AI-assisted" enough of a statement?
8. **Canadian experience.** (a) "Canadian experience preferred / an asset": a "requirement related to Canadian experience"? (CheckON: violation.) (b) "Ontario experience"? (CheckON: borderline, warning.) (c) "North American experience"? (The classifier gave borderline for one phrasing and ok for another.) (d) "Knowledge of Canadian tax legislation" or "Canadian GAAP"? (CheckON: borderline.) (e) "Experience with Canadian clients"? (f) A licensing requirement that embeds Canadian practice, e.g. "two years of Ontario practice under the College"?
9. **Applicability.** (a) An Ontario-based job with travel or hybrid work outside Ontario, and the reverse: how should the "continuation of work performed in Ontario" test be applied from posting text alone? (CheckON: Ontario-based → covered; "Remote (Canada)" → asks.) (b) For an agency posting on a client's behalf, the client's headcount decides? (c) May a worldwide headcount stand in for the Ontario count when nothing better is found (CheckON applies the rules in that case)? (d) Should CheckON ask whether the employer is a Crown body (O. Reg. 285/01, s. 2.1)?
10. **Linked documents.** Since linked documents are part of the posting, should CheckON require them to be pasted before giving a "compliant" result?
11. **Employer override.** If a posting says "$150,000–$250,000" but the employer answers that expected pay is not above $200,000, CheckON fails the range. Is that the right reading, or does the posted range govern?
12. **Wording library.** Do the four sentences in `wording.yaml` satisfy ss. 8.4 (1) and 8.5 (1) (a) as written, formal and plain variants alike?
13. **Posting date.** A posting first published before January 1, 2026 and edited afterwards: is it "posted" anew, so that the rules apply from the edit?
14. **Pending repeal of s. 8.2.** Section 8.2 is repealed on proclamation (2024, c. 3, Sched. 2, s. 2 (2)). What is expected to replace it, and should CheckON prepare a rule version for that day?

## 7. Test results

**Deterministic (fake LLM), `uv run pytest -q` in `backend/`:** 340 passed, 8 skipped (the 8 are the live tests, which need `RUN_LIVE_LLM=1`). The rule-pack cases in `backend/rulepacks/CA-ON/tests/*.yaml` number 89 (before: 52), covering: width at / just under / just over the limit by year, hour (40 h and 37.5 h, hours known and unknown), week and month; pay at $200,000, $200,001, ranges ending at and above $200,000, monthly pay above the threshold, hourly pay above it with hours unknown, known at 40 h and at 30 h; competitive salary / DOE / placeholder; internal, talent-pool and general-recruitment postings; hybrid, remote and outside-Ontario work; 18, 24, 25, 26 and unknown employees; AI with every combination of employer answer and posting statement; Canadian experience labels incl. a Canadian credential and legal entitlement to work; vacancy present, vague, missing, and present only as an employer answer; posting dates on both sides of 2026-01-01.

**Live (real Claude API; `RUN_LIVE_LLM=1 uv run pytest -s tests/compliance/test_live.py`), three runs on 2026-10-21:**

| Test | What it checks | Result | Fees |
| --- | --- | --- | --- |
| `test_live_law_review_classifier_sample` | 32 sentences: 18 Canadian-experience, 8 AI, 6 vacancy, each with the accepted label(s) | 32/32 accepted (every clear violation and every "ok" item labelled as expected; "preferred" and "asset" came back `violation`; "North American experience is required" came back `borderline`; "Knowledge of Canadian tax legislation" `borderline`) | $0.0009 |
| `test_live_law_review_postings[...]` ×4 | Full inspections: competitive salary + "Canadian work experience preferred" + "automated system"; $25–$48/h + Remote (Canada) + talent pool; commission only $40,000–$90,000 + "AI-assisted" + "North American sales experience"; $150,000–$250,000 + Canadian degree + CNO registration | 4/4 expected verdicts after the `internal_only` prompt fix (before it, all four asked the internal-only question). The commission range read as `commission`, pay passed; the exempt posting gave `not_applicable` for both pay rules without a question; "North American sales experience" as a bare bullet came back `ok` (see Q8c) | $0.0007 each |
| `test_live_inspection_of_the_sample_posting` (existing) | The Payroll Specialist sample | pass | $0.0008 |
| `test_live_refinement_rewrites_the_canadian_experience_sentence` (existing) | Sonnet rewrite "2+ years of Canadian payroll experience" → "2+ years of payroll experience" | pass | $0.0035 |
| `test_live_employer_size_search` (existing) | Web search for Shopify | pass | $0.0225 |

Total measured fees across the three runs: about US$0.07 (budget was US$2). Model: `claude-haiku-5-5` for extraction, classification and search; `claude-sonnet-5-5` for the rewrite.

What the live runs do not prove: accuracy on real postings at scale. The 300-posting golden set (04-V1-Scope §3) is still the release gate.

## 8. Docs and site copy checked

- `01-PRD.md` §4: the six rules and "25+ employees in Ontario on the posting date" match the law. Row 6 "3 years after it closes" matches s. 15 (7.1) ("after access ... is removed").
- `02-Technical-Design.md` §2: updated as in section 4, item 12. The ON-APPL-02 row already carried the (d)(ii) continuation wording.
- `04-V1-Scope.md`: no legal claims beyond the rule list; the headcount-by-search decision is recorded there and discussed in section 5.
- `Landing.tsx`: accurate; one FAQ entry suggested (section 5). The footer's "Not legal advice" stands.
- Results page: now shows the citation. The `interpretation` flag is still not shown to users; whether to say "our reading, pending legal review" on those rules is a product decision for before launch.

## 9. Things to watch

- **S. 8.2 repeal on proclamation** (2024, c. 3, Sched. 2, s. 2 (2)): check e-Laws' "not yet in force" list in the weekly source check; if proclaimed, ON-PAY-01/02 need an `effective_to` and whatever replaces them needs a new rule.
- **Guide updates:** the chapter was updated on February 24, 2026; it is the source for "imminently available", the counting rules and the Canadian-experience categories, so diff it too.
- **O. Reg. 476/24 s. 8.3 (2) / 8.4 (2) / 8.5 (2) prescribed exceptions:** none today; a new regulation could add some.

## 10. Files changed on this branch

`backend/rulepacks/CA-ON/rules.yaml` (pack 1.1.0), `backend/rulepacks/CA-ON/tests/{pay,applicability,cex,vacancy,ai}.yaml`, `backend/app/compliance/checks.py`, `backend/prompts/extract.md`, `backend/prompts/classify.md`, `backend/tests/compliance/{test_rulepack,test_engine,test_inspector,test_live}.py`, `frontend/src/components/Check/Findings.tsx`, `02-Technical-Design.md`, this report. `wording.yaml` is unchanged; `reviewed_by` stays empty everywhere.
