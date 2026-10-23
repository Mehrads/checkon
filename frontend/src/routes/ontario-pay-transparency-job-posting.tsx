import { createFileRoute } from "@tanstack/react-router"

import { rulePage } from "@/components/Site/RulePage"

export const Route = createFileRoute("/ontario-pay-transparency-job-posting")(
  rulePage("pay", "en"),
)
