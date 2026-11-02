import { expect, type Page, test } from "@playwright/test"

// The public page's hero, its sample result and the guides, signed out, with the Umami events each call to action
// and content action sends
test.use({ storageState: { cookies: [], origins: [] } })

const GUIDES = [
  {
    path: "/ontario-job-posting-checklist",
    h1: "Ontario job posting checklist",
  },
  {
    path: "/ontario-job-posting-template",
    h1: "A job posting template for Ontario",
  },
  {
    path: "/ontario-job-posting-rules-for-recruiters",
    h1: "Ontario's job posting rules for recruiters and staffing agencies",
  },
  { path: "/accuracy", h1: "How accurate is CheckON?" },
]

type Event = [string, Record<string, string | number> | null]

/** Record what `track` sends: it calls window.umami.track whenever that's there (no script loads in tests). */
async function recordEvents(page: Page) {
  await page.addInitScript(() => {
    const events: unknown[] = []
    Object.assign(window, {
      __events: events,
      umami: {
        track: (name: string, data?: unknown) =>
          events.push([name, data ?? null]),
      },
    })
  })
}

const events = (page: Page) =>
  page.evaluate(() => (window as unknown as { __events: Event[] }).__events)

/** The app has rendered over the HTML built at build time (what the API serves in CI), so its buttons work. */
async function open(page: Page, path: string) {
  await page.goto(path)
  await expect(page.locator("[data-prerendered]")).toHaveCount(0)
}

for (const { path, h1 } of GUIDES) {
  test(`${path} has its title, description, canonical, one h1 and structured data`, async ({
    page,
  }) => {
    await open(page, path)
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(h1)
    await expect(page.locator("h1")).toHaveCount(1)
    await expect(page).toHaveTitle(/ \| CheckON$/)
    expect(
      await page.locator('meta[name="description"]').getAttribute("content"),
    ).toMatch(/.{80,}/)
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
      "href",
      `https://checkon.ca${path}`,
    )
    await expect(page.locator('meta[name="robots"]')).toHaveCount(0)
    const data = JSON.parse(
      (await page
        .locator('script[type="application/ld+json"]')
        .textContent()) ?? "{}",
    )
    const types = data["@graph"].map(
      (item: { "@type": string }) => item["@type"],
    )
    expect(types).toEqual(expect.arrayContaining(["Article", "BreadcrumbList"]))
    // Nothing wider than a phone
    await page.setViewportSize({ width: 375, height: 812 })
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true)
  })
}

test("The footer and the requirements guide link to every guide", async ({
  page,
}) => {
  await open(page, "/check")
  const footer = page.getByRole("contentinfo")
  for (const name of [
    "Job posting checklist",
    "Job posting template",
    "For recruiters and agencies",
    "How accurate CheckON is",
  ])
    await expect(footer.getByRole("link", { name })).toBeVisible()

  await open(page, "/ontario-job-posting-requirements")
  await page
    .getByRole("main")
    .getByRole("link", { name: /Job posting template/ })
    .click()
  await expect(page).toHaveURL("/ontario-job-posting-template")
})

test("On a phone, the first check fits on the first screen", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 })
  await open(page, "/check")
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "line by line",
  )
  await expect(page.getByLabel("Paste one job posting")).toBeInViewport()
  await expect(
    page.getByRole("button", { name: "Check my posting" }),
  ).toBeInViewport({ ratio: 1 })
})

test("The hero's sample link opens the sample result, and its calls to action are counted", async ({
  page,
}) => {
  await recordEvents(page)
  await open(page, "/check")
  await page
    .getByRole("link", { name: /No posting at hand\? See a real result/ })
    .click()
  await expect(page).toHaveURL("/check#sample")
  const sample = page.getByRole("article", { name: "Sample result" })
  await expect(sample).toBeInViewport()
  await expect(sample).toContainText(
    "The pay range is $55,000 a year wide; the limit is $50,000.",
  )

  await sample.getByText("See the finished posting").click()
  await expect(sample).toContainText("This posting is for an existing vacancy.")

  await page.getByRole("link", { name: "Check your own posting" }).click()
  await expect(page).toHaveURL("/check#check")

  const sent = await events(page)
  expect(sent).toContainEqual(["hero-sample", null])
  expect(sent).toContainEqual(["sample-view", null])
  expect(sent).toContainEqual(["sample-open", { part: "finished" }])
  expect(sent).toContainEqual(["sample-check", null])
})

test("The hero's accuracy link and the agency band are counted", async ({
  page,
}) => {
  await recordEvents(page)
  await open(page, "/check")
  await page
    .getByRole("link", { name: "Tested on 150 real Ontario postings" })
    .click()
  await expect(page).toHaveURL("/accuracy")
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "How accurate is CheckON?",
  )

  await page.goBack()
  await expect(page).toHaveURL("/check")
  await page.getByRole("link", { name: "See the Agency plan" }).click()
  await expect(page).toHaveURL("/check#pricing")
  await page
    .getByRole("link", { name: "Read the guide for recruiters" })
    .click()
  await expect(page).toHaveURL("/ontario-job-posting-rules-for-recruiters")

  const sent = await events(page)
  expect(sent).toContainEqual(["hero-accuracy", null])
  expect(sent).toContainEqual(["agency-plan", null])
  expect(sent).toContainEqual(["agency-guide", null])
})

test("The hero links to the Chrome extension on a computer, and the click is counted", async ({
  page,
  context,
}) => {
  const store =
    "https://chromewebstore.google.com/detail/checkon-ontario-job-posti/mbpmobhcmimbohoijbbhckhinhggchdp"
  // The click opens a new tab; it never reaches the real store
  await context.route(`${store}*`, (route) => route.fulfill({ body: "" }))
  await recordEvents(page)
  await open(page, "/check")
  const link = page.getByRole("link", { name: /free Chrome extension/ })
  await expect(link).toHaveAttribute("href", store)
  const popup = page.waitForEvent("popup")
  await link.click()
  expect((await popup).url()).toBe(store)
  expect(await events(page)).toContainEqual(["hero-extension", null])

  await page.setViewportSize({ width: 375, height: 812 })
  await expect(link).toBeHidden()
})

test("The template copies, and the copy is counted", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"])
  await recordEvents(page)
  await open(page, "/ontario-job-posting-template")
  const button = page.getByRole("button", { name: "Copy the template" })
  await button.click()
  await expect(button).toContainText("Copied")
  const copied = await page.evaluate(() => navigator.clipboard.readText())
  expect(copied.startsWith("[Job title]\n")).toBe(true)
  expect(copied).toContain(
    "This posting is [for / not for] an existing vacancy.",
  )
  expect(await events(page)).toContainEqual([
    "content-copy",
    { page: "template", item: "template" },
  ])
})

test("The checklist copies and prints, and both are counted", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"])
  await recordEvents(page)
  await page.addInitScript(() => {
    window.print = () => {
      document.body.dataset.printed = "yes"
    }
  })
  await open(page, "/ontario-job-posting-checklist")
  const copy = page.getByRole("button", { name: "Copy the checklist" })
  await copy.click()
  await expect(copy).toContainText("Copied")
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain(
    "[ ] A sentence says whether the posting is for an existing vacancy",
  )
  await page.getByRole("button", { name: "Print" }).click()
  await expect(page.locator("body")).toHaveAttribute("data-printed", "yes")

  const sent = await events(page)
  expect(sent).toContainEqual([
    "content-copy",
    { page: "checklist", item: "checklist" },
  ])
  expect(sent).toContainEqual(["content-print", { page: "checklist" }])
})

test("A guide's calls to action are counted", async ({ page }) => {
  await recordEvents(page)
  // Each page load starts a new list, so each page's events are checked before the next
  await open(page, "/ontario-job-posting-rules-for-recruiters")
  await page
    .getByRole("main")
    .getByRole("link", { name: "See the Agency plan" })
    .click()
  await expect(page).toHaveURL("/check#pricing")
  expect(await events(page)).toContainEqual([
    "content-cta",
    { page: "recruiters", cta: "agency-plan" },
  ])

  await open(page, "/accuracy")
  await page
    .getByRole("main")
    .getByRole("link", { name: "Check a posting free" })
    .click()
  await expect(page).toHaveURL("/check#check")
  expect(await events(page)).toContainEqual([
    "content-cta",
    { page: "accuracy", cta: "check" },
  ])
})

test("A rule page's copy and check buttons are counted", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"])
  await recordEvents(page)
  await open(page, "/fr/ontario-divulgation-ia-offre-emploi")
  await page
    .getByRole("button", { name: /^Copier: / })
    .first()
    .click()
  // Counted once the clipboard has the text
  await expect
    .poll(() => events(page))
    .toContainEqual([
      "content-copy",
      expect.objectContaining({ page: "rule-ai-fr" }),
    ])

  await open(page, "/ontario-ai-disclosure-job-posting")
  await page.getByRole("button", { name: "Copy: Formal" }).click()
  await expect
    .poll(() => events(page))
    .toContainEqual(["content-copy", { page: "rule-ai-en", item: "Formal" }])
  await page.getByRole("link", { name: "Check a posting free" }).click()
  await expect(page).toHaveURL("/check#check")
  expect(await events(page)).toContainEqual([
    "content-cta",
    { page: "rule-ai-en", cta: "check" },
  ])
})
