import { expect, test } from "@playwright/test"
import { waitForEmailHtml } from "./utils/mailpit"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test.use({ storageState: { cookies: [], origins: [] } })

test("A visitor signs up for a free account and logs in to it", async ({
  page,
  request,
}) => {
  const email = randomEmail()
  const password = `${randomPassword()}Aa1`

  await page.goto("/signup")
  await expect(
    page.getByRole("heading", { name: "Create a free account" }),
  ).toBeVisible()
  await page.getByTestId("email-input").fill(email)
  await page.getByRole("button", { name: "Email me a link" }).click()
  await expect(
    page.getByRole("heading", { name: "Check your email" }),
  ).toBeVisible()

  // Sent after the response, so it can take a moment longer than a sign-in code
  const emailHtml = await waitForEmailHtml({
    request,
    query: `to:${email}`,
    timeout: 20000,
  })
  expect(emailHtml).toContain("Your free account is ready")
  const setUrl = emailHtml
    .match(/\/reset-password\?token=[^"]+/)?.[0]
    ?.replace(/&amp;/g, "&")
  expect(setUrl).toBeDefined()

  await page.goto(setUrl!)
  await page.getByTestId("new-password-input").fill(password)
  await page.getByTestId("confirm-password-input").fill(password)
  await page.getByRole("button", { name: "Set password" }).click()
  await page.waitForURL(/\/login/)

  await logInUser(page, email, password)
  await expect(page.getByRole("heading", { name: "Free account" })).toBeVisible()
  await expect(page.getByText("of 5 checks this period")).toBeVisible()
})

test("The log-in page offers a free account", async ({ page }) => {
  await page.goto("/login")
  await page.getByRole("link", { name: "Create a free one" }).click()
  await expect(page).toHaveURL("/signup")
})

test("A report link that doesn't exist says so", async ({ page }) => {
  await page.goto("/report/not-a-real-report")
  await expect(
    page.getByRole("heading", { name: "This report isn't available" }),
  ).toBeVisible()
})
