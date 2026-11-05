import { expect, test } from "@playwright/test"
import { waitForEmailHtml } from "./utils/mailpit"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test.use({ storageState: { cookies: [], origins: [] } })

const CLOSED = "Sign-up is closed on this server. Ask its admin for an account."

test("A visitor signs up and logs in, when the server's sign-up is open", async ({
  page,
  request,
}) => {
  const email = randomEmail()
  const password = `${randomPassword()}Aa1`

  await page.goto("/signup")
  await expect(
    page.getByRole("heading", { name: "Create an account" }),
  ).toBeVisible()
  await page.getByTestId("email-input").fill(email)
  await page.getByRole("button", { name: "Email me a link" }).click()
  const sent = page.getByRole("heading", { name: "Check your email" })
  const closed = page.getByRole("heading", { name: "Sign-up is closed" })
  await expect(sent.or(closed)).toBeVisible()
  test.skip(
    await closed.isVisible(),
    "Sign-up is closed on this server (SIGNUP_OPEN isn't set)",
  )

  // Sent after the response, so it can take a moment longer than a sign-in code
  const emailHtml = await waitForEmailHtml({
    request,
    query: `to:${email}`,
    timeout: 20000,
  })
  expect(emailHtml).toContain("account is ready")
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
  await expect(page.getByRole("heading", { name: "Past checks" })).toBeVisible()
  await expect(page.getByRole("group", { name: "Checks used" })).toContainText(
    "0",
  )
})

test("A closed sign-up shows the server's message instead of the form", async ({
  page,
}) => {
  await page.route("**/api/v1/signup", (route) =>
    route.fulfill({
      status: 403,
      json: { detail: { reason: "signup_closed", message: CLOSED } },
    }),
  )
  await page.goto("/signup")
  await page.getByTestId("email-input").fill(randomEmail())
  await page.getByRole("button", { name: "Email me a link" }).click()
  await expect(
    page.getByRole("heading", { name: "Sign-up is closed" }),
  ).toBeVisible()
  await expect(page.getByText(CLOSED)).toBeVisible()
  await expect(page.getByTestId("email-input")).toHaveCount(0)
  await page.getByRole("link", { name: "Log in" }).click()
  await expect(page).toHaveURL("/login")
})

test("The log-in page links to sign-up", async ({ page }) => {
  await page.goto("/login")
  await page.getByRole("link", { name: "Create one" }).click()
  await expect(page).toHaveURL("/signup")
})
