import { expect, type Page, test } from "@playwright/test"

// The free check's updated posting, signed out, with the check API answered here: no backend or model calls
test.use({ storageState: { cookies: [], origins: [] } })

const POSTING = `Pharmacist
Toronto, ON

We're hiring a pharmacist to join our team.

Salary: $110,000 - $125,000 per year.`
const STATEMENT = "This posting is for an existing vacancy."
const FIXED = `${POSTING}\n\n${STATEMENT}`

const report = (status: "compliant" | "not_compliant") => ({
  status,
  results: [
    {
      rule: "ON-VAC-01",
      verdict: status === "compliant" ? "pass" : "fail",
      message:
        status === "compliant"
          ? "The posting says whether it is for an existing vacancy."
          : "The posting doesn't say whether it is for an existing vacancy.",
      citation: "ESA 2000, s. 8.5 (1) (a)",
      interpretation: true,
    },
  ],
  reminders: [],
  versions: { rule_pack: "CA-ON@1.3.0" },
})

const check = {
  check_id: "copy-test",
  text: POSTING,
  report: report("not_compliant"),
  questions: [],
  research_question: {
    id: "who",
    text: "Who are you posting this job for?",
    options: ["My own company"],
  },
}

async function openUpdatedPosting(page: Page) {
  await page.route("**/api/v1/inspect", (route) =>
    route.fulfill({ json: check }),
  )
  await page.route("**/api/v1/refine", (route) =>
    route.fulfill({
      json: {
        ...check,
        refinement: {
          patches: [
            {
              id: "vacancy",
              rule: "ON-VAC-01",
              op: "insert",
              span: [POSTING.length, POSTING.length],
              original_span: [POSTING.length, POSTING.length],
              before: "",
              after: `\n\n${STATEMENT}`,
              writer: "wording_library",
              default: true,
              verified: true,
            },
          ],
          questions: [],
          dropped: [],
          text: FIXED,
          report: report("compliant"),
        },
      },
    }),
  )
  await page.route("**/api/v1/patches/accept", (route) =>
    route.fulfill({
      json: {
        check_id: check.check_id,
        text: FIXED,
        report: report("compliant"),
      },
    }),
  )
  await page.goto("/check")
  await page
    .getByPlaceholder("Job title, location, duties, requirements, pay…")
    .fill(POSTING)
  await page.getByRole("button", { name: "Check my posting" }).click()
  await page.getByRole("button", { name: "Apply and edit" }).click()
  await expect(
    page.getByRole("heading", { name: "Your updated posting" }),
  ).toBeVisible()
}

// Like the Claude desktop app's browser pane, which refuses clipboard writes but allows the copy command
const refuseClipboardApi = () => {
  const refuse = () =>
    Promise.reject(
      new DOMException("Write permission denied.", "NotAllowedError"),
    )
  navigator.clipboard.write = refuse
  navigator.clipboard.writeText = refuse
}

test("Copy still works where the clipboard API is refused", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read"])
  await page.addInitScript(refuseClipboardApi)
  await openUpdatedPosting(page)

  const plain = page.getByRole("button", { name: "Copy plain text" })
  await plain.click()
  await expect(page.getByRole("button", { name: "Copied" })).toBeVisible()
  await expect(page.getByRole("button", { name: "Copied" })).toBeFocused()
  const text = await page.evaluate(() => navigator.clipboard.readText())
  expect(text).toContain("Pharmacist")
  expect(text).toContain(STATEMENT)

  await page.getByRole("button", { name: "Copy formatted" }).click()
  await expect(page.getByRole("button", { name: "Copied" })).toBeVisible()
  const html = await page.evaluate(async () => {
    const [item] = await navigator.clipboard.read()
    return (await item.getType("text/html")).text()
  })
  expect(html).toContain("<p>")
  expect(html).toContain(STATEMENT)
  await expect(page.getByText("We couldn't copy here.")).toBeHidden()
})

test("Copy says so when nothing can copy", async ({ page }) => {
  await page.addInitScript(refuseClipboardApi)
  await page.addInitScript(() => {
    document.execCommand = () => false
  })
  await openUpdatedPosting(page)

  await page.getByRole("button", { name: "Copy plain text" }).click()
  await expect(
    page.getByText(
      "We couldn't copy here. Select the posting below and copy it.",
    ),
  ).toBeVisible()
  await expect(page.getByRole("button", { name: "Copied" })).toBeHidden()
})
