# CheckON engagement plan: October 2026

Written on 2026-10-28 from the Umami numbers for October 21–28, a read of every public page, `docs/accuracy-and-demand-2026-10.md`, `docs/law-review-2026-10.md`, the PRD, the research guide and the v1 scope.

**Pull request:** [Mehrads/checkon#5](https://github.com/Mehrads/checkon/pull/5) (not merged, not deployed: it needs your review of the copy and the legal wording listed in section 6).

## What to watch in Umami next week

Compare with the baseline: 39 visits, 22 on `/check`, `check` 7 (6 of them on launch day), `plan-click` 5, `apply-fixes` 3.

| Question | Watch | Good sign |
| --- | --- | --- |
| Do visitors reach a first check? | `check` per visit to `/check`; `check-not-run` | `check` happens on days other than launch day, from visitors who aren't you |
| Does the sample help people without a posting? | `hero-sample` → `sample-view` → `sample-open` (`part`: `finished`, `pasted`) → `sample-check` → `check` | `sample-check` followed by `check` in the same visit |
| Does proof matter to them? | `hero-accuracy`, `sample-accuracy`, page views of `/accuracy`, `content-cta` with `page: accuracy` | `/accuracy` is read and followed by a check |
| Do the guides bring and keep visitors? | Page views of the 4 new pages and of the rule pages (now counted); `content-copy`, `content-print`, `content-cta` by `page` | Copies of the template, checklist or intake list; any visit from Google to a guide |
| Do agencies respond? | `agency-plan`, `agency-guide`, `content-cta` with `cta: agency-plan`, `plan-click` with `plan: agency` | Clicks to the Agency plan from people who aren't you |

Read the numbers with three things in mind:

- The rule pages, the requirements guide, privacy and terms never loaded the Umami script before this change (only `/check` did). Page views on them will rise because they are now counted, not only because more people come.
- Your own visits count when you use checkon.ca. Testing on the local stack keeps them out (`loadAnalytics` only counts the public domain).
- New pages take weeks to be found by search. Submitting `https://checkon.ca/sitemap.xml` in Google Search Console and Bing Webmaster Tools speeds that up (your accounts; not done here).

### Every event this change adds

| Event | Data | Sent when |
| --- | --- | --- |
| `hero-sample` | none | The hero's "No posting at hand? See a real result on a sample posting" is clicked |
| `hero-accuracy` | none | The hero's "Tested on 150 real Ontario postings" is clicked |
| `sample-view` | none | A quarter of the sample result section has been on screen (once per page load) |
| `sample-open` | `part`: `finished` or `pasted` | The finished posting, or the posting as pasted, is opened in the sample |
| `sample-check` | none | "Check your own posting" in the sample section |
| `sample-accuracy` | none | "How accurate is it?" in the sample section |
| `agency-plan` | none | "See the Agency plan" in the agencies band |
| `agency-guide` | none | "Read the guide for recruiters" in the agencies band |
| `content-cta` | `page`, `cta` | A button or header link from a guide, the requirements guide or a rule page to the checker, a sample, the pricing or the audit |
| `content-copy` | `page`, `item` | A copy button on a guide or a rule page (template, example, checklist, intake list, wording) |
| `content-print` | `page` | "Print" on the checklist |

`page` is `checklist`, `template`, `recruiters`, `accuracy`, `requirements`, or `rule-<rule>-<language>` (for example `rule-ai-fr`).

## 1. Funnel diagnosis

**Getting found.** One visit in a week came from Google; the rest were direct, most likely you and people from outreach emails. The site had 14 indexable pages, all created since October 23: the check page, the requirements guide and six rule pages in two languages. Nothing answered the practical searches an HR person or recruiter makes while writing a posting ("job posting template", "checklist", "rules for recruiters"). And the rule pages and the guide never loaded Umami, so a search visitor landing on one was invisible.

**From landing to a first check.** 22 visits to `/check` gave 7 checks, 6 of them on launch day and none since October 22. Reading the page, the reasons are on screen:

- The page asks for a whole posting before it shows anything. A visitor from a search or an email rarely has one at hand, and there was nothing to try without one: the only example was one sentence.
- On a phone (375×812), the check button was below the first screen: a tall text box and the application form sat between the headline and the button (`docs/engagement-2026-10/before-check-mobile-fold.jpg`).
- The headline, "Ontario job posting compliance, in one click", named a category, not a reason to try it, and "one click" doesn't match a paste, a question or two and approvals.
- Nothing showed that the check is right. Free checkers cover the same items (demand study, section 6), so a visitor has no reason to prefer this one.
- The audience line, "HR teams and recruiters in Ontario", didn't speak to agencies, the segment most likely to pay, and no section said what the Agency plan is for.

**After a first check.** `apply-fixes` 3 and `plan-click` 5 against 7 checks: people who run a check go on to use it. The leak is before the first check, not after it.

## 2. Positioning

**Chosen:** "Check a job posting line by line before it goes live." For recruiters, agencies and HR teams in Ontario. The page sells proof and accuracy: each verdict quotes the line and names its source, a real sample result shows it, and an accuracy page gives the measured numbers with their limits.

**Why:**

- The demand study's verdict: the pain is real but cheap to fix and not enforced, the check alone is turning free or bundled, and the paid case is agencies buying consistency and proof across clients (section 6). Copy built on fear of fines would overstate a risk nobody has seen enforced.
- Accuracy is the one edge the study found over competitors, and it only counts if it's shown. The October fixes brought every rule to 95–99% agreement on 150 real postings (section 7), which is now worth publishing with its method.
- The PRD names agency recruiters as the primary paying segment; the research guide asks what proof they need for clients.

**What this rules out:** naming specific legal rules in the hero, calls to action or plan cards (your rule), invented numbers or testimonials, and fine amounts.

## 3. Changes, ranked

Ranked by how much each should raise first checks per visit, then search visits.

| # | Change | Status |
| --- | --- | --- |
| 1 | A first check that fits the first screen on a phone: shorter hero, smaller text box, check button right under it | Built |
| 2 | A real sample result for visitors without a posting, linked from under the check button | Built |
| 3 | New hero: "Check a job posting line by line before it goes live", for recruiters, agencies and HR teams, with a link to the accuracy page | Built |
| 4 | Count every public page in Umami and send an event for each new call to action and content action | Built |
| 5 | Accuracy page: the 150-posting results by rule, how they were measured, what real postings miss, what CheckON still gets wrong | Built |
| 6 | Three practical guides: checklist, template, guide for recruiters and agencies, linked from the footer, the header ("Guides") and the requirements guide | Built |
| 7 | "For agencies" band on the check page: what the Agency plan adds when you post for many clients | Built |
| 8 | Let the sample run in the live checker without using the visitor's free check (the backend would exempt the sample text from the weekly quota and serve it from the cache) | Next: needs a backend change to the free-check limits, which I left alone |
| 9 | Submit the sitemap to Google Search Console and Bing | Next: your accounts |
| 10 | French versions of the four new pages, like the rule pages | Next |
| 11 | The checker labels wording-library fixes "Approved wording" (`WRITER_TEXT` in `components/Check/labels.ts`), but `wording.yaml` isn't signed off yet. The sample uses "Standard wording" | Next: your call |
| 12 | Count the outreach report page | Not planned as is: its address carries the report's private token, which would be sent to Umami |

## 4. Content plan

| Page | For | Searches it answers | Measured by |
| --- | --- | --- | --- |
| `/ontario-job-posting-checklist` (built) | HR generalists and recruiters reviewing a posting before it goes up | "ontario job posting checklist", "ontario job posting requirements 2026", "what must a job posting include ontario" | Page views; `content-copy` (`item: checklist`), `content-print`, `content-cta` with `page: checklist` |
| `/ontario-job-posting-template` (built) | Anyone writing a posting from scratch, and agencies writing for clients | "ontario job posting template", "job posting template pay transparency ontario", "existing vacancy statement wording" | Page views; `content-copy` (`item: template` or `example`), `content-cta` with `page: template` |
| `/ontario-job-posting-rules-for-recruiters` (built) | Recruiters and owners at staffing and recruiting agencies | "ontario job posting rules recruiters", "staffing agency ai disclosure ontario", "recruitment agency pay transparency ontario", "talent pool posting existing vacancy" | Page views; `content-copy` (`item: intake` or `ai-wording`), `content-cta` (`cta: agency-plan` or `check`), then `plan-click` |
| `/accuracy` (built) | People comparing tools before trusting one; people looking for data on Ontario postings | "how many ontario job postings include salary", "ontario job posting compliance study", "checkon accuracy" | Page views; `hero-accuracy`, `sample-accuracy`; `content-cta` with `page: accuracy` |
| French versions of the four pages (next) | Francophone HR teams; the rule pages already have French twins | The French equivalents of the searches above | The same events, with French `page` values |
| A 3-year posting record log to download (next) | HR teams keeping the records the law asks for; a competitor offers a free one | "job posting record keeping ontario template" | A new `content-download` event |
| Other provinces' posting rules (later) | Agencies hiring across provinces | "new brunswick pay transparency job posting" | When the rule engine covers them |

Every guide carries the same parts: an "Updated" line and "not legal advice", sources linked to e-Laws and the Ministry's guide, a call to action to the checker, links to the other guides, and Article and BreadcrumbList structured data (plus FAQPage where it has questions).

## 5. What was built and how it was checked

- **Check page** (`routes/check.tsx`, `components/Site/Landing.tsx`, `components/Check/Checker.tsx`): new hero and description, the sample link under the check button, the check button moved up on phones, "Sample result" in place of the one-line example, the agencies band, two FAQ entries updated, header links to Accuracy and Guides, a footer list of the guides.
- **Sample result** (`components/Site/SampleReport.tsx`, `sample.ts`): CheckON's own output for a made-up posting, run on the local stack on 2026-10-28 with rule pack CA-ON@1.3.0. The API responses are saved in `docs/engagement-2026-10/sample-check-2026-10-28.json`. Re-run it when the rule pack or the messages change.
- **Guides** (`components/Site/Guide.tsx`, `guides.ts`, four routes): prerendered (`src/prerender.tsx`), served by the API (`PRERENDERED` in `backend/app/main.py`) and in the sitemap (20 pages).
- **Measurement** (`RulePage.tsx`, the requirements guide, the guides): Umami loads on every public page except the report page, and the events above.
- **Checks run:** `bun run lint`; `bunx tsc -p tsconfig.build.json --noEmit`; `bun run build` (prerenders all 20 pages); backend `uv run pytest` (821 passed, 13 skipped); Playwright signed-out specs (`engagement`, `rule-pages`, `copy-buttons`, `posting-copy`: 26 passed) against the dev server and against the built site served by the API. The signed-in specs didn't run locally: the local superuser's password doesn't match `.env`, and I didn't change it. CI runs them on a fresh database.
- **Looked at** 375px and 1280px in the browser pane and in screenshots: `docs/engagement-2026-10/before-*.jpg` and `after-*.jpg`. On a 375×812 screen the check button now ends at 639px; before, it was below the first screen.

## 6. Wording that needs your sign-off

Legal wording on the new pages (content pages may name the rules and cite sections; none of it is lawyer-reviewed):

1. **Checklist** (`routes/ontario-job-posting-checklist.tsx`): every item and its citation, including "If the pay, or the top of the range, is more than $200,000 a year, the pay rule doesn't apply" and "Each part of the pay is described".
2. **Template** (`routes/ontario-job-posting-template.tsx`): the template's required lines (from `wording.yaml`, itself unsigned) and "Why each line is there".
3. **Recruiters guide** (`routes/ontario-job-posting-rules-for-recruiters.tsx`):
   - that an agency's postings for a client are covered (Reg. s. 2 (1), "a person acting on behalf of an employer");
   - that the client's posting needs the AI statement when the agency uses AI (the guide's "recruiting firm" sentence);
   - that a named job for a talent pool is a specific position and needs the "not for an existing vacancy" statement (CheckON's reading, from the accuracy review's fix 3);
   - whose headcount counts, which the page leaves to a lawyer (law review Q9b);
   - the intake checklist.
4. **Accuracy page** (`routes/accuracy.tsx`): publishing agreement numbers measured against Claude-written labels. The page says the labels are AI reviewers' reading of the law text, checked by us, not a lawyer's, and that the percentages count every disagreement. Your golden-set rule says Claude drafts never count as labellers for the release gate; this page isn't the gate, but if you'd rather wait for a human labeller, remove the route and the two links to it (hero and sample).
5. **Sample result**: it shows CheckON's real messages, which name the rules, on the check page. It's output, not marketing copy, but it sits on the landing page.

Marketing copy (hero, calls to action, agencies band, plan cards) names no specific legal rule.

## 7. Decisions I made for you

- The sample is a saved result, not a live run, so it costs nothing and doesn't use the visitor's free check (change 8 would make it live).
- The new pages are English only, like the requirements guide.
- Plan cards and prices are unchanged; the agencies band links to them.
- The page title stays "CheckON: Ontario job posting compliance check in one click": it's your own example of acceptable wording and it carries the main search.
- No competitor is named on the site, though the demand study names several.
