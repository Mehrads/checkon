import { createFileRoute } from "@tanstack/react-router"

import { rulePage } from "@/components/Site/RulePage"

export const Route = createFileRoute("/fr/ontario-reponse-45-jours-entrevue")(
  rulePage("interview", "fr"),
)
