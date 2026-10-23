import { createFileRoute } from "@tanstack/react-router"

import { rulePage } from "@/components/Site/RulePage"

export const Route = createFileRoute("/ontario-existing-vacancy-job-posting")(
  rulePage("vacancy", "en"),
)
