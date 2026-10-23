import { createFileRoute } from "@tanstack/react-router"

import { rulePage } from "@/components/Site/RulePage"

export const Route = createFileRoute("/ontario-45-day-interview-response")(
  rulePage("interview", "en"),
)
