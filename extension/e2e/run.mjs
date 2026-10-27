// The extension's browser tests, in Chrome for Testing with the unpacked build (extension/README.md, "Browser
// tests"). They build the extension for E2E_API_URL, the local stack (http://localhost:8000) unless set.
//   node e2e/run.mjs                      smoke, tabs, form and signed: what CI runs
//   node e2e/run.mjs full                 a real check on the rich editor
//   node e2e/run.mjs onpage               a real check reviewed on the page, with Accept all
//   node e2e/run.mjs full:rich,tinymce    a suite with its modes, comma-separated
import {
  API_URL,
  buildExtension,
  check,
  LOCAL_API,
  log,
  report,
  servePages,
} from "./lib.mjs"
import { form, full, onPage, smoke, tabs } from "./panel.mjs"
import { signed } from "./signed.mjs"

const SUITES = {
  smoke: { run: smoke, modes: "rich,textarea,iframe,tinymce,quill" },
  tabs: { run: tabs, modes: "" },
  form: { run: form, modes: "native,iframe,posting" },
  full: { run: full, modes: "rich" },
  onpage: { run: onPage, modes: "rich" },
  signed: { run: signed, modes: "" },
}

const requested = (
  process.argv.length > 2
    ? process.argv.slice(2)
    : ["smoke", "tabs", "form", "signed"]
).map((arg) => {
  const [name, modes] = arg.split(":")
  if (!SUITES[name])
    stop(`no suite "${name}": use ${Object.keys(SUITES).join(", ")}`)
  if (name === "signed" && !LOCAL_API)
    stop(`signed runs against the local stack only, not ${API_URL}`)
  return { name, modes: (modes ?? SUITES[name].modes).split(",") }
})
function stop(message) {
  console.error(message)
  process.exit(1)
}
if (
  !LOCAL_API &&
  requested.some(
    (s) => s.name === "full" || (s.name === "form" && process.env.CHECK),
  )
)
  log(`against ${API_URL}: each check uses that IP's free check for the week`)

const extensionDir = buildExtension()
const server = await servePages()
try {
  for (const { name, modes } of requested) {
    for (const mode of modes) {
      const label = mode ? `${name} ${mode}` : name
      log(`--- ${label}`)
      await SUITES[name]
        .run(extensionDir, mode)
        .catch((error) => check(label, false, error.message))
    }
  }
} finally {
  server.close()
}
process.exitCode = report() ? 0 : 1
