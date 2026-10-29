/** The guides, the template and the accuracy page (routes of the same paths, built on Guide.tsx). English only for
 * now, like the requirements guide. The build renders each to HTML (src/prerender.tsx) and the API serves it
 * (PRERENDERED in backend/app/main.py). `page` names the page in analytics events. */
export const GUIDES = {
  checklist: {
    path: "/ontario-job-posting-checklist",
    page: "checklist",
    name: "Job posting checklist",
    blurb:
      "Everything to check before and after you publish, to copy or print.",
  },
  template: {
    path: "/ontario-job-posting-template",
    page: "template",
    name: "Job posting template",
    blurb: "A posting with the lines the rules ask for already in place.",
  },
  recruiters: {
    path: "/ontario-job-posting-rules-for-recruiters",
    page: "recruiters",
    name: "For recruiters and agencies",
    blurb: "Posting for clients: who's responsible, AI tools, talent pools.",
  },
  accuracy: {
    path: "/accuracy",
    page: "accuracy",
    name: "How accurate CheckON is",
    blurb: "Tested on 150 real Ontario postings, rule by rule.",
  },
} as const

export type GuideId = keyof typeof GUIDES

export const GUIDE_IDS = Object.keys(GUIDES) as GuideId[]

export const GUIDE_PATHS = GUIDE_IDS.map((id) => GUIDES[id].path)

/** The day the guides were last checked against the law and the product. */
export const GUIDES_UPDATED = "2026-10-28"
