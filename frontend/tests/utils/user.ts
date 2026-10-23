import { expect, type Page } from "@playwright/test"
import { latestEmailId, waitForEmailHtml } from "./mailpit"

/** Clicks "Log In" on the filled-in form, then enters the code emailed to `email`. */
export async function submitLogIn(page: Page, email: string) {
  const query = `to:${email} subject:"sign-in code"`
  const skipId = await latestEmailId({ request: page.request, query })
  await page.getByRole("button", { name: "Log In" }).click()

  const html = await waitForEmailHtml({ request: page.request, query, skipId })
  const code = html.match(/id="login-code"[^>]*>(\d{6})</)?.[1]
  if (!code) throw new Error(`No sign-in code in the email to ${email}`)
  await page.getByTestId("code-input").fill(code)
  await page.getByRole("button", { name: "Verify" }).click()
}

/** The account page after logging in: "Check a posting", signed in as `email`. */
export async function expectSignedIn(page: Page, email: string) {
  await page.waitForURL("/")
  await expect(page.getByText(`Signed in as ${email}`)).toBeVisible()
}

export async function logInUser(page: Page, email: string, password: string) {
  await page.goto("/login")

  await page.getByTestId("email-input").fill(email)
  await page.getByTestId("password-input").fill(password)
  await submitLogIn(page, email)
  await expectSignedIn(page, email)
}

export async function logOutUser(page: Page) {
  await page.getByTestId("user-menu").click()
  await page.getByRole("menuitem", { name: "Log out" }).click()
  await page.goto("/login")
}
