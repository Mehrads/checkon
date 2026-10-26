# CheckON browser extension

A side panel for Chrome and Edge that checks a job posting where it's written: it reads the posting from the page, runs the same free check as checkon.ca, and writes the fixes you approve back into the job form.

It is a thin client. Rules, prompts and rule data stay on the server, and the extension only calls the check API on checkon.ca. Without signing in it shares the website's limit: one free check a week per browser and IP address, no sign-up.

Paying customers can **Log in** in the panel with their CheckON email, password and the emailed code, like on the website. Their checks then count against their plan (the panel shows "12 of 50 checks this period"), and **Log out** goes back to the free check. The sign-in token is kept in the extension's own storage (`chrome.storage.local`) until it expires after 8 days or they log out.

## Build

From the repository root:

```bash
bun run --filter extension build
```

That builds the Chrome Web Store version into `extension/dist`. Two variants:

| Command | What it builds |
| --- | --- |
| `bun run --filter extension build:unpacked` | The same build with a fixed ID, `lfepfedddcabkigmmhbhacdllgljpdbe`, for loading unpacked (the API only accepts allowed extension IDs) |
| `VITE_API_URL=http://localhost:8000 bun run --filter extension build:unpacked` | Talks to a local backend instead of checkon.ca |
| `bun run --filter extension package` | The store build, zipped as `extension/checkon-extension.zip` |

The unpacked ID comes from `unpacked-public-key.txt`. Only the public half of that key exists; it just pins the ID.

## Try it in Chrome

1. Run `bun run --filter extension build:unpacked`.
2. Open `chrome://extensions`, turn on **Developer mode**, click **Load unpacked** and pick `extension/dist`.
3. Pin CheckON from the puzzle-piece menu.
4. Open a job form, or any page with a posting, and click the CheckON icon. The side panel reads the posting: the selected text first, then the job description field, then the page.
5. To check the application form too, open it and click **Read form** (on a page you haven't clicked the icon on, it asks for one icon click first). The questions, their choices and required marks appear in the panel; edit them if needed. The form uses one more check.
6. Click **Check this posting** and answer any questions. The problems are highlighted on the page: accept or skip each fix there (see below), or apply them in the panel and **Insert into page** (or copy).

You can also select text and right-click › **Check with CheckON**, or check a posting by its public link under **Link** (the server reads the page; not LinkedIn, Indeed or Glassdoor).

## Fixes on the page

After a check, each problem is highlighted in yellow where it sits in the posting on the page, and a small card beside it shows the fix:

- **Accept** writes that fix into the job form right away. It's typed in the way you would (select the text, then insert), so the form's own editor and its undo (Ctrl+Z / ⌘Z) see it. Accepted fixes turn green.
- **Skip** leaves the text as it is. **Accept all**, on the page or in the panel, does the rest in one go (pay ranges you have to pick, and optional fixes, are left for you).
- A problem CheckON can't fix shows its card with **Fix this yourself**.
- On a page CheckON can't edit (a published posting), the cards offer **Copy fix** instead.

The side panel stays the summary: it counts what's fixed and skipped, and its fix list follows the choices made on the page. **Hide highlights** takes everything off the page. Highlights use the CSS Custom Highlight API (a textarea gets a see-through copy with the marks), so the form isn't touched until you accept a fix. The code is `src/overlay.ts`, injected with the same `activeTab` and `scripting` permissions, and `src/OnPage.tsx`.

Chrome lets the panel read a page only after you click the CheckON icon (or the menu item) on that page. After switching tabs, click the icon again and the open panel reads the new tab.

After changing the code, run the build again and click the reload arrow on the extension's card in `chrome://extensions`.

## Browser tests

`e2e/` drives the real extension in Chrome for Testing with Puppeteer: it installs the unpacked build, presses the toolbar button (which is what gives the panel `activeTab` on a page), and works the side panel on the test pages in `e2e/pages`. Those are plain HTML: `form.html` is a job form whose description field is a rich editor, a textarea, an iframe, TinyMCE or Quill (`?mode=`; the last two load from jsDelivr), and `apply.html` is an application form.

Each run first builds the extension into `e2e/dist` for the API it tests: the local stack, `http://localhost:8000`, unless `E2E_API_URL` says otherwise. The first run downloads Chrome for Testing into `~/.cache/puppeteer`.

From the repository root:

| Command | What it tests | Checks used |
| --- | --- | --- |
| `bun run --filter extension e2e:smoke` | The panel reads the posting from each kind of description field | None |
| `bun run --filter extension e2e:tabs` | Switching tabs (the icon is needed again) and a partial selection (copy only) | None |
| `bun run --filter extension e2e:form` | **Read form** on the application form: on its own tab, in a frame, and under the posting | None; two with `CHECK=1` |
| `bun run --filter extension e2e:full` | A real check signed out: answers the AI and vacancy questions, applies the fixes and inserts them | One free check per mode |
| `bun run --filter extension e2e:signed` | Log in with the emailed code, the plan meter, the workspace switcher, a check with the client's profile, a pay range, insert, log out | One plan check |
| `bun run --filter extension e2e` | smoke, tabs, form and signed: what CI runs | One plan check (none in CI) |

`bun run --filter extension e2e full:rich,tinymce` runs suites with the modes you pick. `HEADFUL=1` shows the browser.

The local stack is the one in the main README (the API on `:8000`) plus Mailpit for the sign-in codes (`docker compose up -d mailpit`, with `SMTP_HOST=localhost` and `SMTP_PORT=1025`; `MAILPIT_HOST` points the tests elsewhere). Its `.env` needs:

- `FASTAPI_ENV=development`, for the private user API, and `EXTENSION_IDS=lfepfedddcabkigmmhbhacdllgljpdbe`. `compose.override.yml` sets both for the Docker backend.
- `ANTHROPIC_API_KEY` for the steps that run a check. Without it, or with `E2E_CHECKS=0`, `signed` skips them. That's how CI runs it.
- `FREE_CHECKS_PER_WEEK` above 1 to run `full` more than once a week.

`signed` makes a user of its own each run: the private user API creates it, `uv run python -m app.test_account` (in `backend/`, on the database in `.env`) gives it a complimentary Agency plan, and it gets a "Harbour Foods" client workspace that uses AI in hiring.

### Against checkon.ca

Only when you mean to: `E2E_API_URL=https://checkon.ca bun run --filter extension e2e:full`. Each check there uses this IP's free check for the week, and the next one is refused until the week is up. `smoke`, `tabs` and `form` don't call the API. `signed` refuses to run there, since it would sign in on production.

Puppeteer rather than the website's Playwright setup: Playwright can load an unpacked extension but can't press its toolbar button, and the tests need that click for Chrome's `activeTab` grant. `puppeteer-core` and `@puppeteer/browsers` are pinned, and so is the Chrome for Testing build in `e2e/lib.mjs`; update them together. The plain `puppeteer` package would download Chrome on every `bun install`, including the production image's.

## Permissions

The Chrome Web Store asks why each permission is needed:

| Permission | Why |
| --- | --- |
| `sidePanel` | The check runs in the browser's side panel |
| `activeTab`, `scripting` | Read the posting, or the application form's questions, from the current tab, highlight the problems in it, and write the fixes you accept back into the job form. Only after you click the CheckON icon or menu item, and only in that tab |
| `contextMenus` | The right-click "Check with CheckON" item |
| `storage` | Passes the right-click request to the side panel (session storage, cleared when the browser closes), and keeps a paying customer signed in (local storage, until they log out) |
| `https://checkon.ca/*` | The check runs on CheckON's API |

## Publish

1. Create a Chrome Web Store developer account with your personal Google account: https://chrome.google.com/webstore/devconsole (one-time registration fee).
2. Run `bun run --filter extension package` and upload `extension/checkon-extension.zip` as a new item.
3. Fill in the listing: description, screenshots of the side panel, privacy policy URL `https://checkon.ca/privacy`, and the data disclosure. The extension sends the posting text you check, and any application form questions you read, to checkon.ca, and, for customers who log in, their email, password and sign-in code to checkon.ca's sign-in. It stores only the sign-in token. In the Web Store's data form that's "Personally identifiable information" (email) and "Authentication information"; neither is sold or used for anything but signing in.
4. Copy the item's ID from the dashboard and add it to the API's allowed extensions (`EXTENSION_IDS`, see `infra/README.md`). Until then the store version gets "Requests must come from the checker's own page".
5. Edge: upload the same zip at https://partner.microsoft.com/dashboard/microsoftedge and add its ID too.
