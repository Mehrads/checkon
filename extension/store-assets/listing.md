# Chrome Web Store listing: CheckON

Item ID `mbpmobhcmimbohoijbbhckhinhggchdp`. Images in this folder: three 1280 x 800 screenshots and the 440 x 280
small promo tile. The 128 x 128 store icon is `extension/public/icons/icon-128.png`.

## Store listing

**Summary** (from the manifest): Ontario compliance check for your job postings, in one click. Reads the posting on
the page and writes the fixes you approve back.

**Category:** Workflow & Planning. **Language:** English.

**Description:**

Check a job posting against Ontario's job posting rules where you write it, in your applicant tracking system or
job board, before you publish.

Click the CheckON icon on the page with your posting. CheckON reads the job description from the page and checks it
in a few seconds:

• Pay: is the expected pay or a pay range there, and is the range narrow enough?
• Canadian experience: does any requirement ask for experience, education or a network gained in Canada?
• AI in hiring: if you use AI to screen, assess or select applicants, does the posting say so?
• Vacancy: does the posting say whether the job is an existing vacancy?

Each problem is highlighted in your posting, with a card beside it showing the fix: the sentence rewritten, or the
statement to add. Accept or skip each one, or accept them all, and CheckON writes the fixes straight into your job
form. It only changes what the rules require; everything else stays as you wrote it. Where only you can say what goes
in, such as the pay range, it leaves a clearly marked placeholder and tells you what's left before you publish.

Works in rich text editors, plain text boxes and editors inside frames. Select part of a page and right-click
"Check with CheckON" to check just that text. You can also check the application form's questions.

One free check a week, no sign-up. Paying customers log in to use their plan's checks, company profiles and client
workspaces.

CheckON is a compliance aid, not legal advice. We keep the date, job title and result of a check, never the posting
itself. Privacy policy: https://checkon.ca/privacy

**Homepage URL:** https://checkon.ca
**Support URL:** https://checkon.ca (contact form), info@checkon.ca

## Privacy practices

**Single purpose:** Check the job posting the user is writing against Ontario's job posting rules, and write the
fixes the user accepts back into the job form.

**Permission justifications:**

- `sidePanel`: The check runs in the browser's side panel.
- `activeTab`: Reads the job posting, or the application form's questions, from the current tab, and writes the
  fixes the user accepts back into the job form. Only after the user clicks the CheckON icon or menu item, and only in
  that tab.
- `scripting`: Runs the code that reads the posting from the page, highlights the problems in it and writes the
  accepted fixes into the job form's editor, on the tab the user clicked CheckON on.
- `contextMenus`: Adds the right-click "Check with CheckON" item for checking selected text.
- `storage`: Passes the right-click request to the side panel (session storage, cleared when the browser closes),
  and keeps a paying customer signed in (local storage, until they log out).
- Host permission `https://checkon.ca/*`: The check runs on CheckON's own API at checkon.ca.

**Remote code:** No, I am not using remote code. All scripts are in the package.

**Data usage (what the extension collects):**

- Website content: the job posting text (and application form questions) on the page, sent to checkon.ca to run
  the check the user asked for.
- Personally identifiable information and authentication information: only for paying customers who log in, their
  email address and password are sent to checkon.ca to sign in, and the sign-in token is kept in the extension's
  storage.

**Certifications** (each must be ticked; they match the privacy policy):

- I do not sell or transfer user data to third parties, outside of the approved use cases.
- I do not use or transfer user data for purposes that are unrelated to my item's single purpose.
- I do not use or transfer user data to determine creditworthiness or for lending purposes.

**Privacy policy URL:** https://checkon.ca/privacy

## Distribution

Public, all regions. Payments: contains in-app purchases (logging in unlocks a paid plan's features; the plans are
bought on checkon.ca).
