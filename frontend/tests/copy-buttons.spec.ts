import { expect, type Page, test } from "@playwright/test"

// The signed-in pages that copy through useCopyToClipboard, with the API answered here (no backend needed) and the
// clipboard API refused, as the Claude desktop app's browser pane does
test.use({ storageState: { cookies: [], origins: [] } })

const REPORT_LINK_TOKEN = "copy-test-token"

async function signIn(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("access_token", "copy-test")
    const refuse = () =>
      Promise.reject(
        new DOMException("Write permission denied.", "NotAllowedError"),
      )
    navigator.clipboard.write = refuse
    navigator.clipboard.writeText = refuse
  })
  // Anything not answered below fails, as it would without a backend; the last route added wins
  await page.route("**/api/v1/**", (route) =>
    route.fulfill({ status: 404, json: { detail: "Not Found" } }),
  )
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({
      json: {
        id: "00000000-0000-0000-0000-000000000001",
        email: "admin@example.com",
        is_active: true,
        is_superuser: true,
      },
    }),
  )
}

test("The outreach page copies a report link where the clipboard API is refused", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read"])
  await signIn(page)
  await page.route("**/api/v1/outreach/reports", (route) =>
    route.fulfill({
      json: [
        {
          token: REPORT_LINK_TOKEN,
          company: "Northgate Logistics",
          url: "https://jobs.example.com/northgate",
          created_at: "2026-10-27T12:00:00Z",
          postings: 3,
          to_fix: 2,
          saved_at: null,
          views: 0,
          first_viewed_at: null,
          saved_by: null,
        },
      ],
    }),
  )
  await page.goto("/outreach")

  // By its row: the button's name changes to "Copied"
  const button = page
    .getByRole("row", { name: /Northgate Logistics/ })
    .getByRole("button")
  await expect(button).toHaveText("Copy link")
  await button.click()
  await expect(button).toContainText("Copied")
  await expect(button).toBeFocused()
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(
    `${new URL(page.url()).origin}/report/${REPORT_LINK_TOKEN}`,
  )
})

test("The audit report copies its summary where the clipboard API is refused", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read"])
  await signIn(page)
  await page.route("**/api/v1/audits/copy-test-audit", (route) =>
    route.fulfill({
      json: {
        id: "copy-test-audit",
        created_at: "2026-10-27T12:00:00Z",
        url: "https://jobs.lever.co/northgate",
        source: "lever",
        board_name: "Northgate Logistics",
        workspace_id: null,
        workspace_name: null,
        found: 1,
        outside_ontario: 0,
        postings: [
          {
            id: "posting-1",
            title: "Warehouse Associate",
            location: "Mississauga, ON",
            url: "https://jobs.lever.co/northgate/1",
            where: "ontario",
            status: "not_compliant",
            issues: [{ rule: "ON-VAC-01", verdict: "fail" }],
            note: null,
            checked_at: "2026-10-27T12:00:00Z",
            check_open: false,
          },
        ],
      },
    }),
  )
  await page.goto("/audits/copy-test-audit")

  const button = page.getByRole("button", { name: "Copy the summary" })
  const summary = await button
    .locator("xpath=preceding-sibling::p")
    .textContent()
  expect(summary).toBeTruthy()
  await button.click()
  await expect(button).toContainText("Copied")
  await expect(button).toBeFocused()
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(
    summary,
  )
})
