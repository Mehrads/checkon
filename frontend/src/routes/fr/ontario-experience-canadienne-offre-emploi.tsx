import { createFileRoute } from "@tanstack/react-router"

import { rulePage } from "@/components/Site/RulePage"

export const Route = createFileRoute(
  "/fr/ontario-experience-canadienne-offre-emploi",
)(rulePage("cex", "fr"))
