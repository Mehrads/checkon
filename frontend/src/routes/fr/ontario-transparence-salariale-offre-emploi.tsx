import { createFileRoute } from "@tanstack/react-router"

import { rulePage } from "@/components/Site/RulePage"

export const Route = createFileRoute(
  "/fr/ontario-transparence-salariale-offre-emploi",
)(rulePage("pay", "fr"))
