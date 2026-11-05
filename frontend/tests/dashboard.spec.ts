import { expect, type Page, test } from "@playwright/test"

// The signed-in frame and its dashboard. Signed in as the first superuser (auth.setup.ts); the API's answers about
// the account's checks and its workspace are stood in for here.

const DAY = 24 * 60 * 60 * 1000

const STATUSES = ["compliant", "not_compliant", "needs_input"] as const

const CHECKS = Array.from({ length: 24 }, (_, index) => ({
  id: `check-${index}`,
  created_at: new Date(Date.now() - index * 2 * DAY).toISOString(),
  title: index === 3 ? "Payroll Administrator" : `Warehouse Associate ${index}`,
  status: STATUSES[index % 3],
  final_status: null,
  workspace_name: null,
}))

// A server that limits each account to 50 checks in any 30 days
const ACCOUNT = { checks_used: 24, checks_limit: 50, signup_open: false }

async function withChecks(page: Page) {
  await page.route("**/api/v1/account", (route) =>
    route.fulfill({ json: ACCOUNT }),
  )
  await page.route("**/api/v1/account/checks*", (route) =>
    route.fulfill({ json: { data: CHECKS, count: CHECKS.length } }),
  )
  await page.route("**/api/v1/workspaces/", (route) =>
    route.fulfill({
      json: {
        data: [{ id: "workspace-1", name: "Harbour Foods" }],
        current_id: "workspace-1",
        can_create: true,
      },
    }),
  )
}

async function openDashboard(page: Page) {
  await withChecks(page)
  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Past checks" })).toBeVisible()
}

const dock = (page: Page) =>
  page.getByRole("navigation", { name: "On this page" })

const tab = (page: Page, name: string) =>
  dock(page).getByRole("button", { name, exact: true })

const panelTop = (page: Page) =>
  page.locator("#app-scroll").evaluate((panel) => panel.scrollTop)

test("Only the panel scrolls: the bar, the rail and the dock stay in view", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await openDashboard(page)
  expect(
    await page.evaluate(
      () => document.documentElement.scrollHeight <= window.innerHeight,
    ),
  ).toBe(true)

  await page
    .locator("#app-scroll")
    .evaluate((panel) => panel.scrollTo({ top: panel.scrollHeight }))
  await expect(page.getByTestId("user-menu")).toBeInViewport()
  await expect(
    page
      .getByRole("navigation", { name: "Account pages" })
      .getByRole("link", { name: "Checks" }),
  ).toBeInViewport()
  await expect(tab(page, "Past checks")).toBeInViewport()
  await expect(page.getByTestId("theme-button")).toBeInViewport()
})

test("The dock's tabs jump to a section and follow the one on screen", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await openDashboard(page)
  await expect(tab(page, "Overview")).toHaveAttribute("aria-current", "true")

  await tab(page, "Past checks").click()
  await expect(
    page.getByRole("heading", { name: "Past checks" }),
  ).toBeInViewport()
  await expect(tab(page, "Past checks")).toHaveAttribute("aria-current", "true")

  // Scrolling by hand moves the lit tab
  await page.locator("#app-scroll").hover()
  await page.locator("#app-scroll").evaluate((panel) => {
    panel.scrollTop = 0
  })
  await expect(tab(page, "Overview")).toHaveAttribute("aria-current", "true")
})

test("Back to the top shows once the page has moved, and takes you there", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await openDashboard(page)
  const toTop = dock(page).getByRole("button", { name: "Back to the top" })
  await expect(toTop).toBeHidden()

  await tab(page, "Past checks").click()
  await toTop.click()
  await expect.poll(() => panelTop(page)).toBe(0)
  await expect(toTop).toBeHidden()
})

test("The keyboard scrolls the panel as soon as a page opens", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await openDashboard(page)
  await page.keyboard.press("PageDown")
  await expect.poll(() => panelTop(page)).toBeGreaterThan(100)
})

test("A new page starts at the top, and Back returns to where you were", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await openDashboard(page)
  await page.locator("#app-scroll").evaluate((panel) => {
    panel.scrollTop = 500
  })
  await expect.poll(() => panelTop(page)).toBe(500)

  await page
    .getByRole("navigation", { name: "Account pages" })
    .getByRole("link", { name: "Settings" })
    .click()
  await expect(page).toHaveURL("/settings")
  await expect.poll(() => panelTop(page)).toBe(0)

  await page.goBack()
  await expect(page).toHaveURL("/")
  await expect(page.getByRole("heading", { name: "Past checks" })).toBeVisible()
  await expect.poll(() => panelTop(page)).toBe(500)
})

test("A page that fits on screen has no tabs to jump to", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await withChecks(page)
  await page.goto("/settings")
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
  await expect(dock(page).getByRole("listitem")).toHaveCount(0)
  await expect(
    dock(page).getByRole("button", { name: "Check a posting" }),
  ).toBeVisible()
})

test("The + opens the check from any page, ready to paste into", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await withChecks(page)
  await page.goto("/settings")
  await dock(page).getByRole("button", { name: "Check a posting" }).click()
  await expect(page).toHaveURL("/")
  await expect(page.getByLabel("Paste one job posting")).toBeFocused()
  await expect(page.getByLabel("Paste one job posting")).toBeInViewport()
})

test("A link pasted in the top bar opens in the checker", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await withChecks(page)
  await page.goto("/settings")
  const link = "https://jobs.example.com/warehouse-associate"
  await page.getByLabel("A posting's link to check").fill(link)
  await page.getByLabel("A posting's link to check").press("Enter")
  await expect(page.locator("#posting-link")).toHaveValue(link)
  await expect(page.locator("#posting-link")).toBeInViewport()
})

test("The overview's numbers come from the account's checks", async ({
  page,
}) => {
  await openDashboard(page)
  const tile = (name: string) => page.getByRole("group", { name })
  await expect(tile("Checks used")).toContainText("24")
  await expect(tile("Checks used")).toContainText("of 50 in the last 30 days")
  await expect(tile("Checks left")).toContainText("26")
  await expect(tile("Meet the rules")).toContainText("8")
  await expect(tile("Meet the rules")).toContainText("Latest 24 checks")
  await expect(tile("Need work")).toContainText("16")
  await expect(
    page.getByRole("img", { name: /^Week of .*: \d+ meet the rules/ }),
  ).toHaveCount(8)
})

test("Past checks can be searched and filtered, and show ten at a time", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await openDashboard(page)
  const rows = page.getByRole("row", { name: /Warehouse|Payroll/ })
  await expect(rows).toHaveCount(10)
  await expect(page.getByText("Showing 10 of 24 checks.")).toBeVisible()

  await page.getByRole("button", { name: "Show 10 more" }).click()
  await expect(rows).toHaveCount(20)

  await page.getByLabel("Search past checks").fill("payroll")
  await expect(rows).toHaveCount(1)
  await expect(page.getByText("Showing 1 of 1 matching checks.")).toBeVisible()

  await page.getByLabel("Search past checks").fill("")
  await page.getByLabel("Filter past checks by result").click()
  await page.getByRole("option", { name: "Needs answers" }).click()
  await expect(rows).toHaveCount(8)

  await page.getByLabel("Search past checks").fill("nothing like this")
  await expect(
    page.getByText("No past checks match that search."),
  ).toBeVisible()
})

test("On a phone nothing scrolls sideways, and the pages are in the menu", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await openDashboard(page)
  await expect(
    page.getByRole("navigation", { name: "Account pages" }),
  ).toBeHidden()
  expect(
    await page
      .locator("#app-scroll")
      .evaluate((panel) => panel.scrollWidth <= panel.clientWidth),
  ).toBe(true)
  // Past checks are short blocks here, not a table wider than the screen
  await tab(page, "Past checks").click()
  await expect(page.getByRole("table")).toHaveCount(0)
  await expect(page.getByText("Payroll Administrator")).toHaveCount(1)

  await page.getByRole("button", { name: "Open the menu" }).click()
  await page.getByRole("dialog").getByRole("link", { name: "Settings" }).click()
  await expect(page).toHaveURL("/settings")
  await expect(page.getByRole("dialog")).toBeHidden()
})
