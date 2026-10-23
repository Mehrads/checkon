import { createFileRoute } from "@tanstack/react-router"

import { rulePage } from "@/components/Site/RulePage"

export const Route = createFileRoute("/ontario-ai-disclosure-job-posting")(
  rulePage("ai", "en"),
)
