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
5. Click **Check this posting**, answer any questions, apply the fixes, then **Insert into page** (or copy).

You can also select text and right-click › **Check with CheckON**.

Chrome lets the panel read a page only after you click the CheckON icon (or the menu item) on that page. After switching tabs, click the icon again and the open panel reads the new tab.

After changing the code, run the build again and click the reload arrow on the extension's card in `chrome://extensions`.

## Permissions

The Chrome Web Store asks why each permission is needed:

| Permission | Why |
| --- | --- |
| `sidePanel` | The check runs in the browser's side panel |
| `activeTab`, `scripting` | Read the posting from the current tab, and write the approved version back into the job form. Only after you click the CheckON icon or menu item, and only in that tab |
| `contextMenus` | The right-click "Check with CheckON" item |
| `storage` | Passes the right-click request to the side panel (session storage, cleared when the browser closes), and keeps a paying customer signed in (local storage, until they log out) |
| `https://checkon.ca/*` | The check runs on CheckON's API |

## Publish

1. Create a Chrome Web Store developer account with your personal Google account: https://chrome.google.com/webstore/devconsole (one-time registration fee).
2. Run `bun run --filter extension package` and upload `extension/checkon-extension.zip` as a new item.
3. Fill in the listing: description, screenshots of the side panel, privacy policy URL `https://checkon.ca/privacy`, and the data disclosure. The extension sends the posting text you check to checkon.ca, and, for customers who log in, their email, password and sign-in code to checkon.ca's sign-in. It stores only the sign-in token. In the Web Store's data form that's "Personally identifiable information" (email) and "Authentication information"; neither is sold or used for anything but signing in.
4. Copy the item's ID from the dashboard and add it to the API's allowed extensions (`EXTENSION_IDS`, see `infra/README.md`). Until then the store version gets "Requests must come from the checker's own page".
5. Edge: upload the same zip at https://partner.microsoft.com/dashboard/microsoftedge and add its ID too.
