import { expect, test } from "@playwright/test"

// Signed in as the first superuser (auth.setup.ts), who has no plan

test("A page the plan doesn't include keeps you signed in", async ({
  page,
}) => {
  await page.goto("/archive")

  await expect(
    page.getByRole("heading", { name: "The archive comes with a paid plan" }),
  ).toBeVisible()
  await expect(page).toHaveURL("/archive")
  expect(
    await page.evaluate(() => localStorage.getItem("access_token")),
  ).not.toBeNull()
})
