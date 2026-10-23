import { createFileRoute } from "@tanstack/react-router"

import { rulePage } from "@/components/Site/RulePage"

export const Route = createFileRoute("/fr/ontario-divulgation-ia-offre-emploi")(
  rulePage("ai", "fr"),
)
