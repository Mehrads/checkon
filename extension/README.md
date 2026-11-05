# CheckON browser extension

A side panel for Chrome and Edge that checks a job posting where it's written: it reads the posting from the page, runs the same check as the CheckON website, and writes the fixes you approve back into the job form.

It is a thin client. Rules, prompts and rule data stay on the server, and the extension only calls the check API of the CheckON server it was built for. Without signing in it shares the website's free check: the server's weekly limit per browser and IP address, no sign-up.

Anyone with an account on that server can **Log in** in the panel with their email, password and the emailed code, like on the website. Their checks are then saved to their account and start from their company profile, with the client switcher when the account has several workspaces. The panel shows the account's checks for the last 30 days ("12 checks in the last 30 days", or "12 of 50…" when the server sets `ACCOUNT_CHECKS_PER_30_DAYS`), and **Log out** goes back to the free check. The sign-in token is kept in the extension's own storage (`chrome.storage.local`) until it expires after 8 days or they log out.

## Build it for your server

The server is fixed at build time. From the repository root:

```bash
VITE_API_URL=https://checkon.example.org bun run --filter extension build
```

| Variable | Default | What it sets |
| --- | --- | --- |
| `VITE_API_URL` | `http://localhost:8000` | The CheckON API the panel calls, and the one host the extension may reach (`host_permissions`) |
| `VITE_SITE_URL` | `VITE_API_URL` | The website the panel links to: password help, the company profile, the archive, privacy. Set it only if the website isn't served by the API, as it is by default |

The server only answers extensions it knows: add the extension's ID to the server's `EXTENSION_IDS` (a comma-separated list), or its checks get "Requests must come from the checker's own page".

| Command | What it builds |
| --- | --- |
| `bun run --filter extension build` | The extension in `extension/dist`; Chrome gives it an ID when you load or publish it |
| `bun run --filter extension build:unpacked` | The same build with a fixed ID, `lfepfedddcabkigmmhbhacdllgljpdbe`, for loading unpacked: put that ID in `EXTENSION_IDS` |
| `bun run --filter extension package` | The build, zipped as `extension/checkon-extension.zip`, for the Chrome Web Store or Edge Add-ons |

The unpacked ID comes from `unpacked-public-key.txt`. Only the public half of that key exists; it just pins the ID.

## Try it in Chrome

1. Run `bun run --filter extension build:unpacked` (with `VITE_API_URL` set, unless your server is the local one on `:8000`).
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
| `bun run --filter extension e2e:onpage` | The same check reviewed on the page: Accept all on the page writes the fixes into the form, and the panel says what's left to fill in | One free check per mode |
| `bun run --filter extension e2e:signed` | Log in with the emailed code, the account's usage line, the workspace switcher, a check with the client's profile, a pay range, insert, log out | One account check |
| `bun run --filter extension e2e` | smoke, tabs, form and signed: what CI runs | One account check (none in CI) |

`bun run --filter extension e2e full:rich,tinymce` runs suites with the modes you pick. `HEADFUL=1` shows the browser.

The local stack is the one in the main README (the API on `:8000`) plus Mailpit for the sign-in codes (`docker compose up -d mailpit`, with `SMTP_HOST=localhost` and `SMTP_PORT=1025`; `MAILPIT_HOST` points the tests elsewhere). Its `.env` needs:

- `FASTAPI_ENV=development`, for the private user API, and `EXTENSION_IDS=lfepfedddcabkigmmhbhacdllgljpdbe`. `compose.override.yml` sets both for the Docker backend.
- `ANTHROPIC_API_KEY` for the steps that run a check. Without it, or with `E2E_CHECKS=0`, `signed` skips them. That's how CI runs it.
- `FREE_CHECKS_PER_WEEK` above 1 to run `full` more than once a week.

`signed` makes a user of its own each run: the private user API creates it, and it gets a "Harbour Foods" client workspace that uses AI in hiring.

### Against a deployed server

Only when you mean to: `E2E_API_URL=https://checkon.example.org bun run --filter extension e2e:full`. Each check there uses this IP's free check for the week, and the next one is refused until the week is up. `smoke`, `tabs` and `form` don't call the API. `signed` refuses to run there, since it would sign in on production.

Puppeteer rather than the website's Playwright setup: Playwright can load an unpacked extension but can't press its toolbar button, and the tests need that click for Chrome's `activeTab` grant. `puppeteer-core` and `@puppeteer/browsers` are pinned, and so is the Chrome for Testing build in `e2e/lib.mjs`; update them together. The plain `puppeteer` package would download Chrome on every `bun install`, including the production image's.

## Permissions

The Chrome Web Store asks why each permission is needed:

| Permission | Why |
| --- | --- |
| `sidePanel` | The check runs in the browser's side panel |
| `activeTab`, `scripting` | Read the posting, or the application form's questions, from the current tab, highlight the problems in it, and write the fixes you accept back into the job form. Only after you click the CheckON icon or menu item, and only in that tab |
| `contextMenus` | The right-click "Check with CheckON" item |
| `storage` | Passes the right-click request to the side panel (session storage, cleared when the browser closes), and keeps a signed-in user signed in (local storage, until they log out) |
| Your server, `VITE_API_URL` | The check runs on that CheckON server's API, and nowhere else |

## Publish

To offer the extension to your own users, publish your build:

1. Build it for your server and run `bun run --filter extension package`, then upload `extension/checkon-extension.zip` as a new item in the Chrome Web Store developer dashboard (https://chrome.google.com/webstore/devconsole) or Edge Add-ons (https://partner.microsoft.com/dashboard/microsoftedge).
2. `store-assets/` has a listing to start from: `listing.md` has the description, the single purpose and a reason for each permission, alongside three 1280 x 800 screenshots and the 440 x 280 promo tile (the store icon is `public/icons/icon-128.png`). Replace its addresses with your own; `bash store-assets/paste-fields.sh` puts each answer on the clipboard in turn. The privacy policy URL is your site's `/privacy`. The extension sends the posting text you check, and any application form questions you read, to your server, and, for users who log in, their email, password and sign-in code to its sign-in. It stores only the sign-in token. In the store's data form that's "Personally identifiable information" (email) and "Authentication information"; neither is sold or used for anything but signing in.
3. Copy the item's ID from the dashboard and add it to the server's `EXTENSION_IDS`.
