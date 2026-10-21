import type { APIRequestContext } from "@playwright/test"

type EmailSummary = {
  ID: string
}

async function latestEmail(request: APIRequestContext, query: string) {
  const response = await request.get(
    `${process.env.MAILPIT_HOST}/api/v1/search`,
    {
      params: { query, limit: 1 },
    },
  )
  const { messages }: { messages: EmailSummary[] } = await response.json()
  return messages[0] as EmailSummary | undefined
}

/** The ID of the newest email matching `query`, to pass as `skipId` later. */
export async function latestEmailId({
  request,
  query,
}: {
  request: APIRequestContext
  query: string
}) {
  return (await latestEmail(request, query))?.ID
}

export async function waitForEmailHtml({
  request,
  query,
  skipId,
  timeout = 5000,
}: {
  request: APIRequestContext
  query: string
  skipId?: string
  timeout?: number
}) {
  const deadline = Date.now() + timeout

  while (Date.now() < deadline) {
    const email = await latestEmail(request, query)

    if (email && email.ID !== skipId) {
      const htmlResponse = await request.get(
        `${process.env.MAILPIT_HOST}/view/${email.ID}.html`,
      )

      if (!htmlResponse.ok()) {
        throw new Error(
          `Could not get the HTML for email "${email.ID}": ${htmlResponse.status()}`,
        )
      }

      return htmlResponse.text()
    }

    await new Promise((resolve) => setTimeout(resolve, 100))
  }

  throw new Error(`Timeout while trying to get the latest email for "${query}"`)
}
