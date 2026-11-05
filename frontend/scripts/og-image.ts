/** The link preview image (public/og-image.png, 1200 × 630) that LinkedIn, Slack and search results show for every
 * public page (src/lib/seo.ts). Drawn in the site's palette and fonts; run `bun scripts/og-image.ts` after changing it. */

import { join } from "node:path"
import { chromium } from "@playwright/test"

const ROOT = join(import.meta.dir, "..")
const font = (name: string) =>
  `file://${join(ROOT, "..", "node_modules", "@fontsource-variable", name, "files", `${name}-latin-wght-normal.woff2`)}`

// The logo's icon (lucide file-check-2), as in components/Common/Logo.tsx
const ICON = `<svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round"><path d="M10.5 22H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1
  1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v6"/><path d="M14 2v5a1 1 0 0 0 1 1h5"/><path d="m14 20 2 2 4-4"/></svg>`

const RULES = [
  "Pay range",
  "Canadian experience",
  "AI disclosure",
  "Existing vacancy",
]

const html = `<!doctype html><html><head><style>
  @font-face { font-family: Newsreader; src: url(${font("newsreader")}); font-weight: 200 800; }
  @font-face { font-family: Hanken; src: url(${font("hanken-grotesk")}); font-weight: 100 900; }
  * { box-sizing: border-box; margin: 0; }
  body { width: 1200px; height: 630px; overflow: hidden; background: #0f3d38; color: #f3efe6;
    font-family: Hanken, sans-serif; padding: 64px 72px; display: flex; flex-direction: column; }
  .brand { display: flex; align-items: center; gap: 16px; font-size: 34px; font-weight: 650; letter-spacing: -0.01em; }
  .mark { width: 60px; height: 60px; border-radius: 15px; background: #009485; color: #fff; display: grid; place-items: center; }
  .brand b { color: #7fd8cc; font-weight: 650; }
  .main { flex: 1; display: flex; align-items: center; gap: 56px; }
  h1 { font-family: Newsreader, serif; font-weight: 500; font-size: 72px; line-height: 1.04; letter-spacing: -0.02em; width: 600px; text-wrap: balance; }
  .card { flex: 1; background: #f3efe6; color: #1c2a28; border-radius: 18px; padding: 30px 32px; font-size: 25px; line-height: 1.35;
    box-shadow: 0 24px 60px rgba(0,0,0,.28); }
  .label { font-size: 15px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #5d6e6a; }
  del { text-decoration-color: #d4573a; text-decoration-thickness: 3px; color: #5d6e6a; }
  .fix { margin-top: 18px; padding-top: 18px; border-top: 1px solid #d9d2c3; }
  .rules { display: flex; flex-wrap: wrap; gap: 12px; }
  .rules span { border: 1.5px solid rgba(127,216,204,.55); color: #d5ece8; border-radius: 999px; padding: 9px 18px; font-size: 21px; }
  .foot { display: flex; justify-content: space-between; align-items: flex-end; }
  .site { color: #b9c7c3; font-size: 24px; }
</style></head><body>
  <div class="brand"><span class="mark">${ICON}</span><span>Check<b>ON</b></span></div>
  <div class="main">
    <h1>Ontario job posting compliance, in one click.</h1>
    <div class="card">
      <p class="label">Before</p>
      <p><del>3+ years supervising, with Canadian experience required</del></p>
      <div class="fix"><p class="label">After</p><p>3+ years supervising required</p></div>
    </div>
  </div>
  <div class="foot">
    <div class="rules">${RULES.map((rule) => `<span>${rule}</span>`).join("")}</div>
    <span class="site">Open source · Apache-2.0</span>
  </div>
</body></html>`

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1200, height: 630 } })
await page.setContent(html, { waitUntil: "load" })
await page.evaluate(() => document.fonts.ready)
await page.screenshot({ path: join(ROOT, "public", "og-image.png") })
await browser.close()
console.log("public/og-image.png")
