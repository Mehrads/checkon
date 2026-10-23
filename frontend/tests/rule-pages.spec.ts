import { expect, test } from "@playwright/test"

// The public rule pages, signed out: what a visitor or a search engine sees once the app runs
test.use({ storageState: { cookies: [], origins: [] } })

const PAGES = [
  {
    en: "/ontario-pay-transparency-job-posting",
    fr: "/fr/ontario-transparence-salariale-offre-emploi",
  },
  {
    en: "/ontario-canadian-experience-job-posting",
    fr: "/fr/ontario-experience-canadienne-offre-emploi",
  },
  {
    en: "/ontario-ai-disclosure-job-posting",
    fr: "/fr/ontario-divulgation-ia-offre-emploi",
  },
  {
    en: "/ontario-existing-vacancy-job-posting",
    fr: "/fr/ontario-poste-vacant-existant-offre-emploi",
  },
  {
    en: "/ontario-45-day-interview-response",
    fr: "/fr/ontario-reponse-45-jours-entrevue",
  },
  {
    en: "/ontario-job-posting-record-keeping",
    fr: "/fr/ontario-conservation-offres-emploi",
  },
]

for (const { en, fr } of PAGES) {
  test(`${en} and its French page link to each other`, async ({ page }) => {
    for (const [path, other, lang] of [
      [en, fr, "fr-CA"],
      [fr, en, "en-CA"],
    ]) {
      await page.goto(path)
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
      await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
        "href",
        `https://checkon.ca${path}`,
      )
      await expect(
        page.locator(`link[rel="alternate"][hreflang="${lang}"]`),
      ).toHaveAttribute("href", `https://checkon.ca${other}`)
      await expect(page.locator('meta[name="robots"]')).toHaveCount(0)
      await expect(page.locator('meta[property="og:image"]')).toHaveAttribute(
        "content",
        "https://checkon.ca/og-image.png",
      )
    }
  })
}

test("Copy puts the wording on the clipboard", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"])
  await page.goto("/ontario-ai-disclosure-job-posting")
  await page.getByRole("button", { name: "Copy: Formal" }).click()
  await expect(
    page.getByRole("button", { name: "Copy: Formal" }),
  ).toContainText("Copied")
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(
    "We use artificial intelligence to screen, assess or select applicants for this position.",
  )
})

test("The landing page and the guide link to the rule pages", async ({
  page,
}) => {
  await page.goto("/check")
  await page
    .locator("#rules")
    .getByRole("link", { name: /Canadian experience/ })
    .click()
  await expect(page).toHaveURL("/ontario-canadian-experience-job-posting")
  await page.getByRole("link", { name: "En français" }).click()
  await expect(page).toHaveURL("/fr/ontario-experience-canadienne-offre-emploi")
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "expérience canadienne",
  )

  await page.goto("/ontario-job-posting-requirements")
  await page.getByRole("link", { name: "More on pay ranges" }).click()
  await expect(page).toHaveURL("/ontario-pay-transparency-job-posting")
})

test("Account pages are kept out of search results", async ({ page }) => {
  await page.goto("/login")
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
    "content",
    "noindex",
  )
})
