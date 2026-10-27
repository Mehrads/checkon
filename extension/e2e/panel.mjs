// The side panel signed out: the toolbar button, reading the job form and the application form, tab
// switching, and (full) a real check whose fixes are written back into the page.
import {
  API_URL,
  answer,
  check,
  click,
  launch,
  log,
  pageUrl,
  pressIcon,
  sleep,
} from "./lib.mjs"

const VACANCY_Q = /Is this posting for an existing vacancy/
const AI_Q = /Do you, or a recruiter acting for you, use AI/

async function openForm(browser, mode) {
  const page = await browser.newPage()
  await page.goto(pageUrl("form", mode), { waitUntil: "networkidle0" })
  if (mode === "tinymce")
    await page.waitForFunction(() => window.tinyReady === true, {
      timeout: 20000,
    })
  if (mode === "quill")
    await page.waitForFunction(() => !!window.quill, { timeout: 20000 })
  await page.bringToFront()
  return page
}

const panelState = (panel) =>
  panel.evaluate(() => ({
    // The posting's source line sits right above its textarea (under the Text tab since the link input).
    source:
      document.querySelector("#posting")?.previousElementSibling?.innerText ??
      document.querySelector("label + p")?.innerText ??
      null,
    text: document.querySelector("#posting")?.value ?? "",
    form: document.querySelector("#application-form")?.value ?? "",
    notice:
      [...document.querySelectorAll("section p")]
        .map((p) => p.innerText)
        .find((t) => /CheckON can read|didn't find/.test(t)) ?? null,
    body: document.body.innerText,
  }))

async function waitPanel(panel, test, what, timeout = 60000) {
  const started = Date.now()
  while (Date.now() - started < timeout) {
    const state = await panelState(panel)
    if (test(state)) return state
    await sleep(500)
  }
  throw new Error(
    `timed out waiting for ${what}: ${(await panelState(panel)).body.slice(0, Number(process.env.BODY ?? 400))}`,
  )
}

async function formContent(page, mode) {
  return page.evaluate((m) => {
    let html = ""
    let text = ""
    if (m === "tinymce") {
      html = window.tinymce.activeEditor.getContent()
      text = new DOMParser().parseFromString(html, "text/html").body.innerText
    } else if (m === "quill") {
      html = window.quill.getSemanticHTML()
      text = window.quill.getText()
    } else if (m === "iframe") {
      const b = document.getElementById("desc-frame").contentDocument.body
      html = b.innerHTML
      text = b.innerText
    } else if (m === "textarea") {
      text = document.getElementById("desc").value
    } else {
      const d = document.getElementById("desc")
      html = d.innerHTML
      text = d.innerText
    }
    const doc = new DOMParser().parseFromString(html, "text/html")
    return {
      headings: doc.querySelectorAll("h1,h2,h3").length,
      bullets:
        m === "textarea"
          ? (text.match(/^• /gm) || []).length
          : doc.querySelectorAll("li").length,
      nested: doc.querySelectorAll("h2 p, h3 p, h2 ul, h3 ul").length,
      pay: text.includes("[Pay range: add before publishing]"),
      rewrite:
        text.includes("2+ years of payroll experience") &&
        !text.includes("Canadian payroll"),
      vacancy: text.includes("existing vacancy"),
      note: document.getElementById("note").value,
    }
  }, mode)
}

/** Read only: the toolbar button opens the panel, which reads the posting from the job form. */
export async function smoke(extensionDir, mode) {
  const { browser, extension } = await launch(extensionDir)
  try {
    const page = await openForm(browser, mode)
    const { panel, type } = await pressIcon(browser, extension, page)
    const state = await waitPanel(
      panel,
      (s) => s.text.length > 100 || !!s.notice,
      "the panel to read the page",
      15000,
    )
    log(
      `[${mode}] side panel opened (target ${type}); source: ${state.source}; notice: ${state.notice}`,
    )
    check(
      `smoke ${mode}: the posting is read`,
      state.text.length > 100,
      `${state.text.length} chars`,
    )
  } finally {
    await browser.close()
  }
}

/** A real check: answers the AI and vacancy questions, applies the fixes and inserts them into the form. */
export async function full(extensionDir, mode) {
  const { browser, extension } = await launch(extensionDir)
  try {
    const page = await openForm(browser, mode)
    const { panel } = await pressIcon(browser, extension, page)
    await waitPanel(
      panel,
      (s) => s.text.length > 100,
      "the posting to be read",
      15000,
    )
    const started = Date.now()
    await click(panel, "Check this posting")
    let state = await waitPanel(
      panel,
      (s) =>
        /\d+ of \d+ fixes selected/.test(s.body) ||
        /couldn't finish/.test(s.body),
      "the fixes",
      90000,
    )
    if (/couldn't finish/.test(state.body)) {
      const at = state.body.indexOf("We couldn't")
      throw new Error(state.body.slice(at, at + 200))
    }
    log(
      `[${mode}] findings and fixes in ${((Date.now() - started) / 1000).toFixed(1)}s: ${state.body.match(/\d+ to fix[^\n]*/)?.[0]}; ${state.body.match(/\d+ of \d+ fixes selected/)?.[0]}`,
    )
    // Answer each open question by its text: no AI screening, and an existing vacancy.
    for (const [question, label] of [
      [AI_Q, "No"],
      [VACANCY_Q, "Yes"],
    ]) {
      if (!question.test(state.body)) continue
      await answer(panel, question, label)
      state = await waitPanel(
        panel,
        (s) =>
          !question.test(s.body) && /\d+ of \d+ fixes selected/.test(s.body),
        `the answer to ${question}`,
        60000,
      )
    }
    log(
      `[${mode}] after answers: ${state.body.match(/\d+ to fix[^\n]*/)?.[0]}; ${state.body.match(/\d+ of \d+ fixes selected/)?.[0]}`,
    )
    await click(panel, "Apply and edit")
    await waitPanel(
      panel,
      (s) => s.body.includes("Insert into page"),
      "the editor",
      30000,
    )
    await click(panel, "Insert into page")
    await waitPanel(
      panel,
      (s) => s.body.includes("Inserted") || /couldn't write/.test(s.body),
      "the insert",
      10000,
    )
    const form = await formContent(page, mode)
    const apiHost = new URL(API_URL).hostname
    const cookies = (await browser.cookies())
      .filter((c) => c.domain.includes(apiHost))
      .map((c) => c.name)
    log(`[${mode}] ${apiHost} cookies: ${cookies}`)
    check(
      `full ${mode}: the fixes are written into the form, the note is untouched`,
      form.pay &&
        form.rewrite &&
        form.vacancy &&
        form.bullets === 8 &&
        form.nested === 0 &&
        (mode === "textarea" || form.headings === 5) &&
        form.note.startsWith("Hiring manager"),
      JSON.stringify(form),
    )
  } finally {
    await browser.close()
  }
}

/** A real check reviewed on the page instead of in the editor: the questions answered, Accept all on the page,
 * the fixes in the form, and the panel saying what's left before publishing. */
export async function onPage(extensionDir, mode) {
  const { browser, extension } = await launch(extensionDir)
  try {
    const page = await openForm(browser, mode)
    const { panel } = await pressIcon(browser, extension, page)
    await waitPanel(
      panel,
      (s) => s.text.length > 100,
      "the posting to be read",
      15000,
    )
    await click(panel, "Check this posting")
    let state = await waitPanel(
      panel,
      (s) =>
        (/highlighted on the page/.test(s.body) &&
          /\d+ of \d+ fixes selected/.test(s.body)) ||
        /couldn't finish/.test(s.body),
      "the problems and their fixes on the page",
      90000,
    )
    if (/couldn't finish/.test(state.body)) {
      const at = state.body.indexOf("We couldn't")
      throw new Error(state.body.slice(at, at + 200))
    }
    for (const [question, label] of [
      [AI_Q, "No"],
      [VACANCY_Q, "Yes"],
    ]) {
      if (!question.test(state.body)) continue
      await answer(panel, question, label)
      state = await waitPanel(
        panel,
        (s) =>
          !question.test(s.body) &&
          /highlighted on the page/.test(s.body) &&
          /\d+ of \d+ fixes selected/.test(s.body),
        `the answer to ${question}`,
        60000,
      )
    }
    log(
      `[${mode}] ${state.body.match(/\d+ problems? highlighted on the page/)?.[0]}`,
    )
    await click(panel, "Accept all on the page")
    state = await waitPanel(
      panel,
      (s) =>
        /Everything on the page is reviewed/.test(s.body) &&
        /Before you publish|Ready to publish/.test(s.body),
      "the page reviewed",
      30000,
    )
    const form = await formContent(page, mode)
    check(
      `on page ${mode}: Accept all writes the fixes into the form, the note is untouched`,
      form.pay &&
        form.rewrite &&
        form.vacancy &&
        form.bullets === 8 &&
        form.nested === 0 &&
        form.note.startsWith("Hiring manager"),
      JSON.stringify(form),
    )
    const left = state.body.match(/Before you publish[^\n]*\n+[^\n]*/)?.[0]
    check(
      `on page ${mode}: the panel names what's left to fill in`,
      /Before you publish, fill in what's marked in brackets on the page/.test(
        state.body,
      ) && state.body.includes("[Pay range: add before publishing]"),
      left?.replace(/\n+/g, " "),
    )
  } finally {
    await browser.close()
  }
}

/** Tab switching and a partial selection, no check. */
export async function tabs(extensionDir) {
  const { browser, extension } = await launch(extensionDir)
  try {
    // 1. Open on one tab, then switch to another without pressing the icon there.
    const first = await openForm(browser, "rich")
    const { panel } = await pressIcon(browser, extension, first)
    await waitPanel(panel, (s) => s.text.length > 100, "the first read", 15000)
    const second = await openForm(browser, "textarea")
    await second.evaluate(() => {
      document.getElementById("desc").value =
        "Office Coordinator\nToronto, Ontario\n\nWhat you will do\n• Greet visitors and manage the front desk\n• Order supplies"
    })
    await click(panel, "Read page")
    let state = await waitPanel(
      panel,
      (s) => !!s.notice || s.text.startsWith("Office"),
      "a read on the second tab",
      10000,
    )
    check(
      "tabs: Read page on a tab without an icon click explains or reads it",
      !!state.notice || state.text.startsWith("Office"),
      `${state.notice ? "asks to click the icon" : "read it"} (${state.source})`,
    )
    // 2. Press the icon on the second tab: the open panel re-reads it.
    await extension.triggerAction(second)
    state = await waitPanel(
      panel,
      (s) => s.text.startsWith("Office"),
      "the re-read after the icon",
      10000,
    )
    check(
      "tabs: the icon re-reads the current tab",
      true,
      state.text.split("\n")[0],
    )
    // 3. A partial selection is read but not written back.
    await first.bringToFront()
    await first.evaluate(() => {
      const d = document.getElementById("desc")
      const h = [...d.querySelectorAll("h3")].find(
        (x) => x.textContent === "What we are looking for",
      )
      const range = document.createRange()
      range.setStartBefore(h)
      range.setEndAfter(h.nextElementSibling)
      getSelection().removeAllRanges()
      getSelection().addRange(range)
    })
    await extension.triggerAction(first)
    state = await waitPanel(
      panel,
      (s) => s.text.startsWith("What we are looking for"),
      "the selection",
      10000,
    )
    const marked = await first.evaluate(
      () => !!document.querySelector("[data-checkon-target]"),
    )
    check(
      "tabs: a partial selection is copy-only",
      !marked && /Copy the result back/.test(state.source ?? ""),
      `"${state.source}"; marked for write-back: ${marked}`,
    )
  } finally {
    await browser.close()
  }
}

/** A job page with the form under the posting: the posting is read without the form, then the form. */
async function postingPage(extensionDir) {
  const { browser, extension } = await launch(extensionDir)
  try {
    const page = await browser.newPage()
    await page.goto(pageUrl("apply", "posting"), { waitUntil: "networkidle0" })
    await page.bringToFront()
    const { panel } = await pressIcon(browser, extension, page)
    let state = await waitPanel(
      panel,
      (s) => s.text.length > 100,
      "the posting",
      15000,
    )
    const clean =
      state.text.includes("About the role") &&
      state.text.includes("existing vacancy") &&
      !/First name|Submit application|Select\.\.\./.test(state.text)
    check(
      "form posting: the posting is read without the form",
      clean,
      `${state.text.length} chars`,
    )
    await click(panel, "Read form")
    state = await waitPanel(panel, (s) => s.form.length > 0, "the form", 10000)
    const expected = await page.evaluate(() => window.expectedForm)
    if (state.form !== expected)
      log(`[form posting] got:\n${state.form}\n--- expected:\n${expected}`)
    check(
      "form posting: the form, without dropdown placeholders",
      state.form === expected,
    )
  } finally {
    await browser.close()
  }
}

/** The application form (apply.html) on a second tab: "Read form" there first asks for the icon (Chrome
 * hasn't granted that tab), the icon then reads the form and leaves the posting alone. With CHECK=1 it also
 * checks the posting and the form: two checks. */
export async function form(extensionDir, mode) {
  if (mode === "posting") return postingPage(extensionDir)
  const { browser, extension } = await launch(extensionDir)
  try {
    const editor = await openForm(browser, "rich")
    const { panel } = await pressIcon(browser, extension, editor)
    const read = await waitPanel(
      panel,
      (s) => s.text.length > 100,
      "the posting",
      15000,
    )
    const apply = await browser.newPage()
    await apply.goto(pageUrl("apply", mode), { waitUntil: "networkidle0" })
    await apply.bringToFront()
    await click(panel, "Add the application form").catch(() => {})
    await click(panel, "Read form")
    let state = await waitPanel(
      panel,
      (s) => /Click the CheckON icon|Read \d+ question/.test(s.body),
      "the form read",
      10000,
    )
    const asked = /Click the CheckON icon/.test(state.body)
    if (asked) {
      await extension.triggerAction(apply)
      state = await waitPanel(
        panel,
        (s) => s.form.length > 0,
        "the form after the icon",
        10000,
      )
    }
    const expected = await apply.evaluate(() => window.expectedForm)
    if (state.form !== expected)
      log(`[form ${mode}] got:\n${state.form}\n--- expected:\n${expected}`)
    check(`form ${mode}: the icon is needed on a new tab`, asked)
    check(
      `form ${mode}: questions, required marks and choices`,
      state.form === expected,
      `${state.form.split("\n").length} lines`,
    )
    check(`form ${mode}: the posting is kept`, state.text === read.text)
    if (!process.env.CHECK) return
    const started = Date.now()
    await click(panel, "Check this posting")
    state = await waitPanel(
      panel,
      (s) =>
        (/Application form\n/.test(s.body) &&
          /\d+ of \d+ fixes selected/.test(s.body)) ||
        /couldn't finish/.test(s.body),
      "the posting and form results",
      120000,
    )
    const failed = state.body.match(
      /Your application form asks about Canadian experience[^\n]*/,
    )?.[0]
    log(
      `[form ${mode}] checked in ${((Date.now() - started) / 1000).toFixed(1)}s: ${state.body.match(/\d+ to fix[^\n]*/)?.[0]}`,
    )
    check(
      `form ${mode}: the form's Canadian-experience question fails`,
      !!failed,
    )
    check(
      `form ${mode}: the report says the form was checked`,
      /Checked: [^\n]*and your application form\./.test(state.body),
      state.body.match(/Checked: [^\n]*/)?.[0],
    )
  } finally {
    await browser.close()
  }
}
