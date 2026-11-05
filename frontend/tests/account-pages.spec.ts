import { expect, test } from "@playwright/test"

// Signed in as the first superuser (auth.setup.ts). Every signed-in user gets every page: there are no plans.

const PAGES = [
  { path: "/archive", heading: "Archive" },
  { path: "/audits", heading: "Audit a careers page" },
  { path: "/profile", heading: /^(Company profile|Client workspaces)$/ },
]

for (const { path, heading } of PAGES) {
  test(`${path} opens for any signed-in user`, async ({ page }) => {
    await page.goto(path)
    await expect(
      page.getByRole("heading", { level: 1, name: heading }),
    ).toBeVisible()
    await expect(page).toHaveURL(path)
    await expect(page.getByText(/paid plan|See the plans/)).toHaveCount(0)
    expect(
      await page.evaluate(() => localStorage.getItem("access_token")),
    ).not.toBeNull()
  })
}
