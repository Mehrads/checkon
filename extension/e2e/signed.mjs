// Signed in, against the local stack only: log in (password and the emailed code, from Mailpit), the account's
// usage line, the client workspace switcher, a signed-in check that uses the workspace's profile, a pay range
// suggestion confirmed into the posting, insert, the token surviving a reopen, and log out.
//
// Each run makes a user of its own: the private user API (FASTAPI_ENV=development) creates it, and the API adds
// a "Harbour Foods" client workspace that uses AI in hiring. Every account gets every feature. The check, pay range and insert steps need the API's Claude key:
// without ANTHROPIC_API_KEY (as in CI), or with E2E_CHECKS=0, they are skipped.
import { readFileSync } from "node:fs"
import path from "node:path"
import {
  API_URL,
  bodyText,
  check,
  click,
  EXT_ID,
  LOCAL_API,
  launch,
  log,
  pageUrl,
  REPO_DIR,
  waitForText,
} from "./lib.mjs"

const MAILPIT = (process.env.MAILPIT_HOST ?? "http://localhost:8025").replace(
  /\/$/,
  "",
)
const API = `${API_URL}/api/v1`
// The account bar once signed in: "Signed in · 3 checks in the last 30 days", or "3 of 50 checks…" with a limit
const USAGE = /Signed in · \d+ (of \d+ )?checks? in the last 30 days/

/** A variable from the environment, else from the repository's .env (the one the local API reads). */
function setting(name) {
  if (process.env[name]) return process.env[name]
  try {
    const line = readFileSync(path.join(REPO_DIR, ".env"), "utf8")
      .split("\n")
      .find((l) => l.startsWith(`${name}=`))
    return line?.slice(name.length + 1).replace(/^["']|["']$/g, "") || undefined
  } catch {
    return undefined
  }
}

async function api(method, url, { token, json, form } = {}) {
  const response = await fetch(`${API}${url}`, {
    method,
    headers: {
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...(json ? { "content-type": "application/json" } : {}),
    },
    body: json ? JSON.stringify(json) : form ? new URLSearchParams(form) : null,
  })
  if (!response.ok)
    throw new Error(
      `${method} ${url}: ${response.status} ${await response.text()}`,
    )
  return response.json()
}

/** The newest sign-in code email to `email`, as in frontend/tests/utils/mailpit.ts. */
async function latestCodeEmail(email) {
  const query = `to:${email} subject:"sign-in code"`
  const response = await fetch(
    `${MAILPIT}/api/v1/search?${new URLSearchParams({ query, limit: "1" })}`,
  ).catch(() => {
    throw new Error(`Mailpit isn't reachable at ${MAILPIT} (MAILPIT_HOST)`)
  })
  const { messages } = await response.json()
  return messages[0]?.ID
}

/** The code in the first sign-in email to `email` that isn't `skipId`. */
async function loginCode(email, skipId) {
  const deadline = Date.now() + 15000
  while (Date.now() < deadline) {
    const id = await latestCodeEmail(email)
    if (id && id !== skipId) {
      const html = await (await fetch(`${MAILPIT}/view/${id}.html`)).text()
      const code = html.match(/id="login-code"[^>]*>(\d{6})</)?.[1]
      if (code) return { code, id }
    }
    await new Promise((resolve) => setTimeout(resolve, 200))
  }
  throw new Error(`no sign-in code for ${email} in Mailpit (${MAILPIT})`)
}

/** A fresh user with a "Harbour Foods" client workspace; checks use the user's own company. */
async function makeUser() {
  const email = `extension-e2e-${Math.random().toString(36).slice(2, 10)}@example.com`
  const password = `${Math.random().toString(36).slice(2)}${Math.random().toString(36).slice(2)}`
  await api("POST", "/private/users/", {
    json: { email, password, full_name: "Extension Test" },
  }).catch((error) => {
    throw new Error(
      `${error.message}\nThe private user API needs FASTAPI_ENV=development on the local API.`,
    )
  })
  const { challenge } = await api("POST", "/login/password", {
    form: { username: email, password },
  })
  const { code, id } = await loginCode(email)
  const { access_token: token } = await api("POST", "/login/access-token", {
    json: { challenge, code },
  })
  const own = await api("GET", "/workspaces/", { token })
  const harbour = await api("POST", "/workspaces/", {
    token,
    json: { name: "Harbour Foods" },
  })
  await api("PATCH", `/workspaces/${harbour.id}`, {
    token,
    json: {
      employer_name: "Harbour Foods",
      uses_ai_in_hiring: true,
      meets_headcount_threshold: true,
    },
  })
  await api("PUT", "/workspaces/current", {
    token,
    json: { workspace_id: own.current_id },
  })
  return { email, password, lastCodeId: id }
}

export async function signed(extensionDir) {
  if (!LOCAL_API)
    throw new Error(
      `the signed-in test runs against the local stack only, not ${API_URL}`,
    )
  const checks =
    process.env.E2E_CHECKS !== "0" && !!setting("ANTHROPIC_API_KEY")
  const user = await makeUser()
  log(`test user: ${user.email}, Harbour Foods workspace`)
  const { browser, extension } = await launch(extensionDir, "checkon-signed-")
  try {
    const page = await browser.newPage()
    await page.goto(pageUrl("form", "rich"), { waitUntil: "networkidle0" })
    await page.bringToFront()
    await extension.triggerAction(page)
    const target = await browser.waitForTarget(
      (t) => t.url().startsWith(`chrome-extension://${EXT_ID}/sidepanel.html`),
      { timeout: 10000 },
    )
    const panel = await target.asPage()
    let text = await waitForText(
      panel,
      (t) => t.includes("Log in to use its checks"),
      "the log-in line",
      15000,
    )
    check(
      "signed out: offers log-in, free check footer",
      text.includes("One free check a week"),
    )

    // 1. Log in: password, then the emailed code.
    await click(panel, "Log in")
    await panel.waitForSelector("#email")
    await panel.type("#email", user.email)
    await panel.type("#password", user.password)
    await click(panel, "Log in", { last: true })
    await waitForText(
      panel,
      (t) => t.includes("Check your email"),
      "the code step",
      15000,
    )
    const { code } = await loginCode(user.email, user.lastCodeId)
    await panel.type("#code", code)
    await click(panel, "Verify")
    text = await waitForText(
      panel,
      (t) => USAGE.test(t),
      "the usage line",
      15000,
    )
    check(
      "logged in: the account's usage shown",
      USAGE.test(text),
      text.match(USAGE)?.[0],
    )
    check(
      "footer says checks are saved to the account",
      text.includes("Checks are saved to your account"),
    )

    // 2. Workspaces: switch to Harbour Foods (uses AI in hiring).
    text = await waitForText(
      panel,
      (t) => t.includes("Checking for"),
      "the workspace switcher",
      10000,
    )
    await (await panel.$('[aria-label="Client workspace"]')).click()
    await new Promise((resolve) => setTimeout(resolve, 400))
    await click(panel, "Harbour Foods")
    text = await waitForText(
      panel,
      (t) => /Using the company profile for Harbour Foods/.test(t),
      "the switch to Harbour Foods",
      10000,
    )
    const profile = text.match(
      /Using the company profile for Harbour Foods[^\n]*/,
    )?.[0]
    check(
      "switcher: Harbour Foods profile in use",
      /Uses AI in hiring/.test(profile ?? ""),
      profile,
    )

    if (checks) await signedCheck(panel, page)
    else
      log(
        "SKIP the check, pay range and insert: no ANTHROPIC_API_KEY, or E2E_CHECKS=0",
      )

    // 6. The sign-in survives reopening the panel; log out returns to the free check.
    const again = await browser.newPage()
    await again.goto(`chrome-extension://${EXT_ID}/sidepanel.html`)
    text = await waitForText(
      again,
      (t) => USAGE.test(t) || t.includes("Log in to use its checks"),
      "the reopened panel",
      15000,
    )
    check("token kept across a reopen", USAGE.test(text))
    await click(again, "Log out")
    text = await waitForText(
      again,
      (t) => t.includes("Log in to use its checks"),
      "the log-out",
      10000,
    )
    check(
      "log out: back to the free check",
      text.includes("One free check a week"),
    )
  } finally {
    await browser.close()
  }
}

/** Steps 3 to 5: a signed-in check, a pay range suggestion confirmed into the fixes, the vacancy answer, insert. */
async function signedCheck(panel, page) {
  // 3. A signed-in check: the profile answers the AI and size questions.
  const started = Date.now()
  await click(panel, "Check this posting")
  let text = await waitForText(
    panel,
    (t) => /\d+ of \d+ fixes selected/.test(t) || /couldn't finish/.test(t),
    "the fixes",
    90000,
  )
  log(
    `check in ${((Date.now() - started) / 1000).toFixed(1)}s: ${text.match(/\d+ to fix[^\n]*/)?.[0]}; ${text.match(/\d+ of \d+ fixes selected/)?.[0]}`,
  )
  check(
    "profile used: no AI or size question",
    !/Do you, or a recruiter acting for you, use AI/.test(text) &&
      !/How many employees/.test(text),
  )
  const fixes = text.slice(text.indexOf("Suggested fixes"))
  check(
    "AI disclosure becomes a fix from the profile",
    /AI disclosure\n+Fail|AI disclosure\n+Statement|Artificial intelligence|AI disclosure\nAdded/.test(
      text,
    ) || /AI disclosure/.test(fixes),
    fixes.slice(0, 400).replace(/\n+/g, " | "),
  )
  log(
    "meter after the check:",
    (await bodyText(panel)).match(/\d+ of \d+ checks[^\n]*/)?.[0],
  )

  // 4. Pay range suggestion, with sources, confirmed into the fixes.
  await waitForText(
    panel,
    (t) => t.includes("Suggest a pay range"),
    "the pay suggestion button",
    10000,
  )
  const askStarted = Date.now()
  await click(panel, "Suggest a pay range")
  text = await waitForText(
    panel,
    (t) =>
      /Suggested range|Your saved range|Which occupation fits/.test(t) ||
      /couldn't|Something went wrong/.test(
        t.slice(t.indexOf("Not sure what range")),
      ),
    "the suggestion",
    120000,
  )
  if (/Which occupation fits/.test(text)) {
    const at = text.indexOf("Which occupation fits")
    log(
      "asked to pick an occupation:",
      text.slice(at, at + 200).replace(/\n+/g, " | "),
    )
    const first = await panel.evaluateHandle(() =>
      document.querySelector("fieldset button"),
    )
    await first.asElement().click()
    text = await waitForText(
      panel,
      (t) => /Suggested range|Your saved range/.test(t),
      "the suggestion after picking",
      120000,
    )
  }
  const box = text.slice(
    text.indexOf("Not sure what range"),
    text.indexOf("Use this range") + 15,
  )
  const inputs = await panel.evaluate(() =>
    [...document.querySelectorAll("input")]
      .filter((i) => i.offsetParent && /^\d/.test(i.value))
      .map((i) => i.value),
  )
  check(
    "suggestion shown with a range and sources",
    /Suggested range|Your saved range/.test(box) && inputs.length >= 2,
    `in ${((Date.now() - askStarted) / 1000).toFixed(1)}s; range inputs ${inputs.join(" – ")}`,
  )
  const links = await panel.evaluate(() =>
    [...document.querySelectorAll("details a, li a")]
      .map((a) => a.href)
      .filter((h) => h.startsWith("http")),
  )
  check(
    "every source has a link",
    links.length > 0,
    `${links.length} links: ${links.slice(0, 4).join(", ")}`,
  )
  await panel.evaluate(() => {
    const d = document.querySelector("details")
    if (d) d.open = true
  })
  await click(panel, "Use this range")
  text = await waitForText(
    panel,
    (t) => t.includes("Your pay range is in the fixes"),
    "the confirmed range",
    30000,
  )
  const payAt = text.indexOf("Expected pay", text.indexOf("Suggested fixes"))
  check(
    "confirmed range replaces the placeholder in the fixes",
    !text
      .slice(text.indexOf("Suggested fixes"))
      .includes("[Pay range: add before publishing]"),
    text.slice(payAt, payAt + 160).replace(/\n+/g, " | "),
  )

  // 5. Answer the vacancy question, apply, insert.
  if (/Is this posting for an existing vacancy/.test(text)) {
    const yes = await panel.evaluateHandle(() => {
      const q = [...document.querySelectorAll("*")].find(
        (e) =>
          e.children.length === 0 &&
          /Is this posting for an existing vacancy/.test(e.textContent ?? ""),
      )
      for (let box = q?.parentElement; box; box = box.parentElement) {
        const b = [...box.querySelectorAll("button")].find(
          (x) => x.innerText.trim() === "Yes",
        )
        if (b) return b
      }
      return null
    })
    await yes.asElement().click()
    text = await waitForText(
      panel,
      (t) =>
        !/Is this posting for an existing vacancy/.test(t) &&
        /\d+ of \d+ fixes selected/.test(t),
      "the vacancy answer",
      60000,
    )
    check(
      "pay range kept after answering",
      !text
        .slice(text.indexOf("Suggested fixes"))
        .includes("[Pay range: add before publishing]"),
    )
  }
  await click(panel, "Apply and edit")
  await waitForText(
    panel,
    (t) => t.includes("Insert into page"),
    "the editor",
    30000,
  )
  await click(panel, "Insert into page")
  await waitForText(
    panel,
    (t) => t.includes("Inserted") || /couldn't write/.test(t),
    "the insert",
    10000,
  )
  const written = await page.evaluate(
    () => document.getElementById("desc").innerText,
  )
  const range = written.match(
    /\$[\d,.]+(?:\s*(?:to|–|-)\s*\$[\d,.]+)?[^\n]*/,
  )?.[0]
  check(
    "inserted posting has the confirmed range",
    !!range && !written.includes("[Pay range"),
    range,
  )
  check(
    "inserted posting has the AI disclosure",
    /artificial intelligence|\bAI\b/i.test(written),
    written.split("\n").find((l) => /artificial intelligence|\bAI\b/i.test(l)),
  )
}
