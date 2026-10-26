// Shared by the browser tests (run.mjs): the extension build, the test pages, Chrome for Testing with the
// unpacked extension, the side panel helpers and the PASS/FAIL list.
import { spawnSync } from "node:child_process"
import { mkdtempSync, readFileSync } from "node:fs"
import { createServer } from "node:http"
import os from "node:os"
import path from "node:path"
import { Browser, computeExecutablePath, install } from "@puppeteer/browsers"
import puppeteer from "puppeteer-core"

export const EXTENSION_DIR = path.join(import.meta.dirname, "..")
export const REPO_DIR = path.join(EXTENSION_DIR, "..")
export const EXT_ID = "lfepfedddcabkigmmhbhacdllgljpdbe"
// The Chrome for Testing build puppeteer-core 25.13.0 is made for; update the two together.
const CHROME_BUILD = "155.0.8059.39"
const CHROME_CACHE =
  process.env.PUPPETEER_CACHE_DIR ??
  path.join(os.homedir(), ".cache", "puppeteer")

// The API the extension is built against: the local stack unless E2E_API_URL says otherwise.
export const API_URL = (
  process.env.E2E_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "")
const API_HOST = new URL(API_URL).hostname
export const LOCAL_API = ["localhost", "127.0.0.1"].includes(API_HOST)

const PAGES_DIR = path.join(import.meta.dirname, "pages")
const PORT = 5181
/** A test page: form.html (the job form) or apply.html (the application form), in one of its modes. */
export const pageUrl = (name, mode) =>
  `http://127.0.0.1:${PORT}/${name}.html?mode=${mode}`

export const log = (...args) =>
  console.log(new Date().toISOString().slice(11, 19), ...args)
export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const results = []
export function check(test, ok, detail = "") {
  results.push({ test, ok })
  log(`${ok ? "PASS" : "FAIL"} ${test}${detail ? `: ${detail}` : ""}`)
}
/** Prints the totals; true when everything passed. */
export function report() {
  const failed = results.filter((r) => !r.ok)
  console.log(
    `\n${results.length - failed.length} passed, ${failed.length} failed`,
  )
  for (const r of failed) console.log(`  FAIL ${r.test}`)
  return results.length > 0 && failed.length === 0
}

/** The unpacked build (fixed ID) for API_URL, in e2e/dist; EXT_DIR uses a build you already have. */
export function buildExtension() {
  if (process.env.EXT_DIR) return path.resolve(process.env.EXT_DIR)
  const outDir = path.join("e2e", "dist", LOCAL_API ? "local" : API_HOST)
  log(`building the extension for ${API_URL} into extension/${outDir}`)
  const build = spawnSync(
    "bunx",
    [
      "vite",
      "build",
      "--mode",
      "unpacked",
      "--outDir",
      outDir,
      "--logLevel",
      "error",
    ],
    {
      cwd: EXTENSION_DIR,
      env: { ...process.env, VITE_API_URL: API_URL },
      stdio: "inherit",
    },
  )
  if (build.status !== 0) throw new Error("the extension build failed")
  return path.join(EXTENSION_DIR, outDir)
}

/** Serves e2e/pages on 127.0.0.1:5181. */
export function servePages() {
  const types = { ".html": "text/html; charset=utf-8" }
  const server = createServer((request, response) => {
    const name = path.basename(new URL(request.url, "http://x").pathname)
    try {
      const body = readFileSync(path.join(PAGES_DIR, name))
      response.writeHead(200, {
        "content-type": types[path.extname(name)] ?? "text/plain",
      })
      response.end(body)
    } catch {
      response.writeHead(404).end()
    }
  })
  return new Promise((resolve) =>
    server.listen(PORT, "127.0.0.1", () => resolve(server)),
  )
}

async function chromePath() {
  const options = {
    browser: Browser.CHROME,
    buildId: CHROME_BUILD,
    cacheDir: CHROME_CACHE,
  }
  await install(options) // downloads it once; already there, it returns at once
  return computeExecutablePath(options)
}

/** Chrome for Testing with the extension installed, in a fresh profile. HEADFUL=1 shows the window. */
export async function launch(extensionDir, profile = "checkon-e2e-") {
  const browser = await puppeteer.launch({
    executablePath: await chromePath(),
    headless: !process.env.HEADFUL,
    pipe: true,
    enableExtensions: true,
    userDataDir: mkdtempSync(path.join(os.tmpdir(), profile)),
    defaultViewport: null,
    // GitHub's Ubuntu runners don't allow Chrome's sandbox
    args: [
      "--window-size=1400,900",
      ...(process.env.CI ? ["--no-sandbox"] : []),
    ],
  })
  const id = await browser.installExtension(extensionDir) // Chrome dropped --load-extension; this loads it over the pipe
  await sleep(1000)
  const extensions = await browser.extensions()
  const extension = extensions.get(id === EXT_ID ? id : "")
  if (!extension) {
    await browser.close()
    throw new Error(`extension ${EXT_ID} not loaded: ${[...extensions.keys()]}`)
  }
  return { browser, extension }
}

/** Press the toolbar button and return the side panel page. */
export async function pressIcon(browser, extension, page) {
  const panelUrl = `chrome-extension://${EXT_ID}/sidepanel.html`
  const known = new Set(browser.targets())
  await extension.triggerAction(page)
  const target = await browser
    .waitForTarget((t) => t.url().startsWith(panelUrl) && !known.has(t), {
      timeout: 10000,
    })
    .catch(() => browser.targets().find((t) => t.url().startsWith(panelUrl)))
  if (!target) throw new Error("the side panel didn't open")
  return { panel: await target.asPage(), type: target.type() }
}

export const bodyText = (panel) => panel.evaluate(() => document.body.innerText)

/** Polls the panel's text until `test` passes. */
export async function waitForText(panel, test, what, timeout = 60000) {
  const started = Date.now()
  while (Date.now() - started < timeout) {
    const text = await bodyText(panel)
    if (test(text)) return text
    await sleep(400)
  }
  throw new Error(
    `timed out waiting for ${what}: ${(await bodyText(panel)).slice(0, Number(process.env.BODY ?? 1500))}`,
  )
}

/** Click the enabled button (or listbox option) labelled `label`: the first one, or the last. */
export async function click(panel, label, { last = false } = {}) {
  const handle = await panel.evaluateHandle(
    (l, lastOne) => {
      const all = [
        ...document.querySelectorAll("button, [role=option]"),
      ].filter((b) => b.innerText.trim() === l && !b.disabled)
      return (lastOne ? all.at(-1) : all[0]) ?? null
    },
    label,
    last,
  )
  const element = handle.asElement()
  if (!element) throw new Error(`no enabled "${label}" button`)
  await element.click()
}

/** Click the answer button that belongs to the question matching `question`. */
export async function answer(panel, question, label) {
  const handle = await panel.evaluateHandle(
    (source, l) => {
      const re = new RegExp(source)
      const text = [
        ...document.querySelectorAll("p, legend, label, span, div"),
      ].find((e) => e.children.length === 0 && re.test(e.textContent ?? ""))
      for (let box = text?.parentElement; box; box = box.parentElement) {
        const button = [...box.querySelectorAll("button")].find(
          (b) => b.innerText.trim() === l,
        )
        if (button) return button
      }
      return null
    },
    question.source,
    label,
  )
  const element = handle.asElement()
  if (!element) throw new Error(`no "${label}" answer for ${question}`)
  await element.click()
}
