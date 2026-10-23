import { expect, type Page, test } from "@playwright/test"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random.ts"
import { expectSignedIn, submitLogIn } from "./utils/user"

test.use({ storageState: { cookies: [], origins: [] } })

const fillForm = async (page: Page, email: string, password: string) => {
  await page.getByTestId("email-input").fill(email)
  await page.getByTestId("password-input").fill(password)
}

/** A user of the test's own, as parallel sign-ins to one account read each other's codes. */
const newUser = async () => {
  const email = randomEmail()
  const password = randomPassword()
  await createUser({ email, password })
  return { email, password }
}

const verifyInput = async (page: Page, testId: string) => {
  const input = page.getByTestId(testId)
  await expect(input).toBeVisible()
  await expect(input).toHaveText("")
  await expect(input).toBeEditable()
}

test("Inputs are visible, empty and editable", async ({ page }) => {
  await page.goto("/login")

  await verifyInput(page, "email-input")
  await verifyInput(page, "password-input")
})

test("Log In button is visible", async ({ page }) => {
  await page.goto("/login")

  await expect(page.getByRole("button", { name: "Log In" })).toBeVisible()
})

test("Forgot Password link is visible", async ({ page }) => {
  await page.goto("/login")

  await expect(
    page.getByRole("link", { name: "Forgot your password?" }),
  ).toBeVisible()
})

test("Log in with valid email and password ", async ({ page }) => {
  const { email, password } = await newUser()
  await page.goto("/login")

  await fillForm(page, email, password)
  await submitLogIn(page, email)

  await expectSignedIn(page, email)
})

test("Log in with invalid email", async ({ page }) => {
  await page.goto("/login")

  await fillForm(page, "invalidemail", firstSuperuserPassword)
  await page.getByRole("button", { name: "Log In" }).click()

  await expect(page.getByText("Invalid email address")).toBeVisible()
})

test("Log in with invalid password", async ({ page }) => {
  const password = randomPassword()

  await page.goto("/login")
  await fillForm(page, firstSuperuser, password)
  await page.getByRole("button", { name: "Log In" }).click()

  await expect(page.getByText("Incorrect email or password")).toBeVisible()
})

test("Password alone asks for the emailed code", async ({ page }) => {
  const { email, password } = await newUser()
  await page.goto("/login")

  await fillForm(page, email, password)
  await page.getByRole("button", { name: "Log In" }).click()

  await expect(
    page.getByRole("heading", { name: "Check your email" }),
  ).toBeVisible()
  await page.getByTestId("code-input").fill("000000")
  await page.getByRole("button", { name: "Verify" }).click()

  await expect(page.getByText("Incorrect code")).toBeVisible()
  await expect(page).toHaveURL("/login")
})

test("Successful log out", async ({ page }) => {
  const { email, password } = await newUser()
  await page.goto("/login")

  await fillForm(page, email, password)
  await submitLogIn(page, email)

  await expectSignedIn(page, email)

  await page.getByTestId("user-menu").click()
  await page.getByRole("menuitem", { name: "Log out" }).click()
  await page.waitForURL("/login")
})

test("Logged-out user cannot access protected routes", async ({ page }) => {
  const { email, password } = await newUser()
  await page.goto("/login")

  await fillForm(page, email, password)
  await submitLogIn(page, email)

  await expectSignedIn(page, email)

  await page.getByTestId("user-menu").click()
  await page.getByRole("menuitem", { name: "Log out" }).click()
  await page.waitForURL("/login")

  await page.goto("/settings")
  await page.waitForURL("/login?redirect=%2Fsettings")
})

test("Redirects to /login when token is wrong", async ({ page }) => {
  await page.goto("/settings")
  await page.evaluate(() => {
    localStorage.setItem("access_token", "invalid_token")
  })
  await page.goto("/settings")
  await page.waitForURL("/login?redirect=%2Fsettings")
})

test("A link to an account page logs in, then opens that page", async ({
  page,
}) => {
  const { email, password } = await newUser()
  await page.goto("/archive?posting=abc")
  await page.waitForURL(/\/login\?redirect=/)

  await fillForm(page, email, password)
  await submitLogIn(page, email)

  await page.waitForURL("/archive?posting=abc")
})

test("The page after logging in is always on this site", async ({ page }) => {
  const { email, password } = await newUser()
  await page.goto("/login?redirect=%2F%2Fexample.com")

  await fillForm(page, email, password)
  await submitLogIn(page, email)

  await page.waitForURL("/")
})
