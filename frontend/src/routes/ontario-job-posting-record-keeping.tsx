import { createFileRoute } from "@tanstack/react-router"

import { rulePage } from "@/components/Site/RulePage"

export const Route = createFileRoute("/ontario-job-posting-record-keeping")(
  rulePage("records", "en"),
)
