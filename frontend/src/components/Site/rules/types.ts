import type { ReactNode } from "react"

import type { Lang } from "@/lib/seo"

/** One page per rule, in English (en.tsx) and French (fr.tsx). Every statement matches the rule pack
 * (backend/rulepacks/CA-ON/rules.yaml, wording.yaml) and docs/law-review-2026-10.md; change the pages when they
 * change. Unlike the landing page, these pages cite the sections. */
export const RULE_IDS = [
  "pay",
  "cex",
  "ai",
  "vacancy",
  "interview",
  "records",
] as const
export type RuleId = (typeof RULE_IDS)[number]

export const UPDATED = "2026-10-23"

/** The official texts, in each language: the Act, O. Reg. 476/24 and the Ministry's guide. */
export const SOURCES = {
  en: {
    act: "https://www.ontario.ca/laws/statute/00e41",
    reg: "https://www.ontario.ca/laws/regulation/240476",
    guide:
      "https://www.ontario.ca/document/your-guide-employment-standards-act-0/requirements-related-publicly-advertised-job",
    ohrc: "https://www.ohrc.on.ca/en/policy-removing-canadian-experience-barrier",
  },
  fr: {
    act: "https://www.ontario.ca/lois/loi/00e41",
    reg: "https://www.ontario.ca/lois/reglement/240476",
    guide:
      "https://www.ontario.ca/fr/document/votre-guide-de-la-loi-sur-les-normes-demploi-0/exigences-relatives-aux-annonces-publiques",
    ohrc: "https://www.ohrc.on.ca/fr/politique-sur-la-suppression-des-obstacles-lies-l-experience-canadienne",
  },
} satisfies Record<Lang, Record<string, string>>

/** A section of the law or the Ministry's guide, linked to the official text. */
export type Cite = { label: string; href: string }

export type Rule = {
  path: string
  /** The page's title, before " | CheckON" */
  title: string
  description: string
  /** Its name and one line about it, in the list of rules */
  name: string
  blurb: string
  h1: string
  intro: string
  summary: string[]
  law: { text: ReactNode; cites: Cite[] }[]
  /** Wording to copy into a posting or a message, or a checklist */
  copy: {
    heading: string
    kind: "wording" | "checklist"
    items: { label?: string; text: string }[]
  }
  example: { before: string; after: string; note: string }
  check: string
  faq: { q: string; a: string }[]
}

/** The words around the content, in each language. */
export type Words = {
  home: string
  guide?: { name: string; path: string }
  eyebrow: string
  updated: string
  other: { label: string; lang: Lang }
  short: string
  law: string
  before: string
  after: string
  example: string
  header: string
  checkHeading: string
  checkButton: string
  checkNote?: string
  scope: { heading: string; text: ReactNode; cites: Cite[] }
  faq: string
  rules: string
  copy: string
  copied: string
  copyAll: string
  source: ReactNode
  footer: string
}
