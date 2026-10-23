import { createFileRoute } from "@tanstack/react-router"

import { rulePage } from "@/components/Site/RulePage"

export const Route = createFileRoute(
  "/fr/ontario-poste-vacant-existant-offre-emploi",
)(rulePage("vacancy", "fr"))
