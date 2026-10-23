import { createFileRoute } from "@tanstack/react-router"

import { rulePage } from "@/components/Site/RulePage"

export const Route = createFileRoute("/fr/ontario-conservation-offres-emploi")(
  rulePage("records", "fr"),
)
