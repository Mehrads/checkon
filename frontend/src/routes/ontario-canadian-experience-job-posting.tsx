import { createFileRoute } from "@tanstack/react-router"

import { rulePage } from "@/components/Site/RulePage"

export const Route = createFileRoute(
  "/ontario-canadian-experience-job-posting",
)(rulePage("cex", "en"))
