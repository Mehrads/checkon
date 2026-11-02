import { expect, test } from "@playwright/test"

// The page an outreach note links to, signed out, with the API's answer fixed: "may need changes" must match the note
test.use({ storageState: { cookies: [], origins: [] } })

const TOKEN = "report-count-test"
const QUESTION = {
  rule: "ON-AI-01",
  verdict: "needs_input",
  message: "The posting doesn't say whether AI screens applicants.",
  quotes: [],
}

const posting = (title: string, changes: object) => ({
  title,
  location: "Toronto, ON",
  url: `https://jobs.lever.co/acme/${title}`,
  where: "ontario",
  status: "needs_input",
  findings: [],
  form_status: null,
  form_findings: [],
  note: null,
  ...changes,
})

const REPORT = {
  token: TOKEN,
  company: "Acme",
  url: "https://jobs.lever.co/acme",
  created_at: "2026-11-02T12:00:00Z",
  found: 7,
  outside_ontario: 0,
  postings: [
    posting("Question", { findings: [QUESTION] }),
    posting("Another question", { findings: [QUESTION] }),
    posting("Fail", {
      status: "not_compliant",
      findings: [
        {
          rule: "ON-PAY-01",
          verdict: "fail",
          message: "There's no pay range.",
          quotes: [],
        },
        QUESTION,
      ],
    }),
    posting("Warning", {
      status: "not_compliant",
      findings: [
        {
          rule: "ON-VAC-01",
          verdict: "warning",
          message: "It may not say it's an existing vacancy.",
          quotes: [],
        },
      ],
    }),
    posting("Form", {
      status: "compliant",
      form_status: "not_compliant",
      form_findings: [
        {
          rule: "ON-CEX-01",
          verdict: "fail",
          message: "A required question asks for Canadian experience.",
          quotes: [],
        },
      ],
    }),
    posting("Form warning", {
      status: "compliant",
      form_status: "compliant",
      form_findings: [
        {
          rule: "ON-CEX-01",
          verdict: "warning",
          message: "A question may ask for Canadian experience.",
          quotes: [],
        },
      ],
    }),
    posting("Clean", { status: "compliant", form_status: "compliant" }),
  ],
  checklist: {},
  saved: false,
  mine: false,
  expires_on: "2026-12-02T12:00:00Z",
}

test("The tile leaves out postings that only ask a question, and the posting stays on the report", async ({
  page,
}) => {
  await page.route(`**/api/v1/reports/${TOKEN}`, (route) =>
    route.fulfill({ json: REPORT }),
  )
  await page.goto(`/report/${TOKEN}`)

  const tile = page.getByText("may need changes", { exact: true }).locator("..")
  await expect(tile.locator("p").first()).toHaveText("4")

  // By its title's link: the findings inside a card are list items too
  const card = (title: string) =>
    page.getByRole("listitem").filter({
      has: page.getByRole("link", { name: title, exact: true }),
    })

  const question = card("Question")
  await expect(question.getByText("Needs answers")).toBeVisible()
  await expect(question.getByText("Nothing to fix")).toHaveCount(0)
  await expect(
    question.getByRole("link", { name: "Get the fix free" }),
  ).toBeVisible()

  await expect(card("Form warning").getByText("nothing to fix")).toHaveCount(0)

  const clean = card("Clean")
  await expect(clean.getByText("Nothing to fix")).toBeVisible()
  await expect(
    clean.getByRole("link", { name: "Get the fix free" }),
  ).toHaveCount(0)
})
