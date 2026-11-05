import { Source } from "./Source"
import { type Cite, type Rule, type RuleId, SOURCES, type Words } from "./types"

const { act, reg, guide, ohrc } = SOURCES.en
const esa = (section: string): Cite => ({
  label: `ESA, s. ${section}`,
  href: act,
})
const oreg = (section: string): Cite => ({
  label: `O. Reg. 476/24, s. ${section}`,
  href: reg,
})
const GUIDE: Cite = { label: "Ministry's guide", href: guide }

export const WORDS: Words = {
  home: "CheckON",
  guide: {
    name: "Ontario job posting requirements",
    path: "/ontario-job-posting-requirements",
  },
  eyebrow: "Ontario job posting rules",
  updated: "Updated October 23, 2026. A summary, not legal advice.",
  other: { label: "En français", lang: "fr" },
  short: "In short",
  law: "What the law says",
  before: "Before",
  after: "After",
  example: "Before and after",
  header: "Check a posting",
  checkHeading: "How CheckON checks it",
  checkButton: "Check a posting free",
  scope: {
    heading: "Who the rules apply to",
    text: "Employers with 25 or more employees in Ontario on the day the job is posted, for public postings of a specific job done in Ontario, on your careers page, a job board or a recruiter's site. A posting open only to current employees, or a general \"we're hiring\" campaign that names no job, isn't covered.",
    cites: [oreg("1"), oreg("2 (1)")],
  },
  faq: "Questions people ask",
  rules: "The other rules",
  copy: "Copy",
  copied: "Copied",
  copyAll: "Copy the list",
  source: (
    <>
      Sources: the <Source href={act}>Employment Standards Act, 2000</Source>{" "}
      (ESA), Part III.1 and s. 15, <Source href={reg}>O. Reg. 476/24</Source>{" "}
      and the Government of Ontario's{" "}
      <Source href={guide}>guide to the job posting requirements</Source>. This
      page summarises them and isn't legal advice; for your situation, talk to
      an employment lawyer.
    </>
  ),
  footer: "Ontario job posting compliance. Not legal advice.",
}

export const RULES: Record<RuleId, Rule> = {
  pay: {
    path: "/ontario-pay-transparency-job-posting",
    title: "Ontario pay transparency: salary ranges in job postings",
    description:
      "Since January 1, 2026, Ontario job postings must show the expected pay or a pay range no wider than $50,000 a year. What counts as pay, the $200,000 exemption, and wording you can copy.",
    name: "Pay range",
    blurb: "Show the expected pay, or a range no wider than $50,000 a year.",
    h1: "Pay ranges in Ontario job postings",
    intro:
      "Every public job posting in Ontario must include the expected pay for the job, or a range of expected pay. A range can be at most $50,000 a year wide. Here's what that means in practice, with wording you can copy.",
    summary: [
      "Put the expected pay, or a pay range, in every public posting.",
      "A range can be at most $50,000 a year wide: $85,000 to $135,000 is fine, $85,000 to $140,000 is not.",
      "Hourly, weekly and monthly pay count too: the limit is the yearly equivalent of $50,000.",
      "Postings where the pay, or the top of the range, is more than $200,000 a year are exempt.",
    ],
    law: [
      {
        text: "A public job posting must include information about the expected pay for the position, or the range of expected pay.",
        cites: [esa("8.2 (1)")],
      },
      {
        text: "Pay means wages: a salary, an hourly rate, commission, piece rates, and bonuses tied to hours, production or efficiency. Tips, expense and travel allowances, benefits, stock options and purely discretionary bonuses aren't wages.",
        cites: [oreg("2 (2)"), esa("1 (1)"), GUIDE],
      },
      {
        text: "A range can't be wider than the equivalent of $50,000 a year. A range exactly $50,000 wide is allowed.",
        cites: [esa("8.2 (3)"), oreg("4")],
      },
      {
        text: "The rule doesn't apply when the expected pay, or the top of the range, is more than $200,000 a year. Exactly $200,000 is still covered.",
        cites: [esa("8.2 (2)"), oreg("3")],
      },
      {
        text: "If the pay has more than one part, say something about each. Where a dollar amount can't be given, the Ministry's guide says you can explain how it's earned, for example a bonus of up to 10% of the annual salary based on individual performance, or up to a certain amount in sales commissions.",
        cites: [GUIDE],
      },
    ],
    copy: {
      heading: "Wording you can copy",
      kind: "wording",
      items: [
        {
          label: "Salary range",
          text: "Expected pay: $62,000 to $74,000 a year.",
        },
        { label: "Hourly range", text: "Pay: $24.50 to $28.00 an hour." },
        {
          label: "Base plus commission",
          text: "Expected pay: a base salary of $55,000 a year, plus commission. The successful candidate can expect to earn up to $20,000 a year in commission.",
        },
        {
          label: "Salary plus bonus",
          text: "Expected pay: $70,000 to $85,000 a year, plus a bonus of up to 10% of annual salary based on individual performance.",
        },
      ],
    },
    example: {
      before:
        "Salary: Competitive, based on experience.\nBenefits: Health, dental and RRSP matching.",
      after:
        "Expected pay: $62,000 to $74,000 a year, based on experience.\nBenefits: Health, dental and RRSP matching.",
      note: '"Competitive" says nothing about the expected pay. The fix adds a range less than $50,000 wide and leaves the rest as it was.',
    },
    check:
      "CheckON finds the pay in your posting, works out how wide a range is (hourly, weekly and monthly pay included) and applies the $200,000 exemption. If the pay is missing or the range is too wide, it marks the line to fix; it never makes up a figure, and nothing changes until you approve it.",
    faq: [
      {
        q: "Do Ontario job postings have to include a salary range?",
        a: "Yes, for employers with 25 or more employees in Ontario. Since January 1, 2026, every public job posting must include the expected pay or a range of expected pay (ESA, s. 8.2 (1)). Postings where the pay, or the top of the range, is more than $200,000 a year are exempt.",
      },
      {
        q: "How wide can a pay range be in Ontario?",
        a: "At most the equivalent of $50,000 a year (O. Reg. 476/24, s. 4). $85,000 to $135,000 is allowed; $85,000 to $140,000 is not.",
      },
      {
        q: "How does the $50,000 limit work for hourly pay?",
        a: "The regulation says \"equivalent to $50,000 annually\" but not how to convert. CheckON multiplies by the job's weekly hours (40 if you don't say) and 52 weeks, and asks for the hours when the result is close to the limit. At 40 hours a week, $25 to $48 an hour is $52,000 to $99,840 a year: $47,840 wide, so it's within the limit.",
      },
      {
        q: 'Can I write "competitive salary" or "depending on experience"?',
        a: 'Not on its own. Neither tells applicants the expected pay. Give a figure or a range; you can still add "based on experience".',
      },
      {
        q: "Do commission and bonuses count as pay?",
        a: "Commission and bonuses tied to hours, production or efficiency are wages, so they count. Tips, expense allowances, benefits, stock options and purely discretionary bonuses don't. If the pay has more than one part, say something about each, for example a base salary and how much commission the person can expect to earn.",
      },
      {
        q: 'What about "$70,000+" or "up to $90,000"?',
        a: "The law doesn't settle open-ended pay. CheckON treats it as not a range and asks for both ends, the cautious reading.",
      },
    ],
  },

  cex: {
    path: "/ontario-canadian-experience-job-posting",
    title: "Canadian experience in Ontario job postings: the 2026 ban",
    description:
      "Ontario job postings and application forms can't require Canadian experience. What that covers (work experience, Canadian degrees, a client network in Canada), what's still allowed, and how to reword it.",
    name: "Canadian experience",
    blurb:
      "Don't require Canadian experience in the posting or its application form.",
    h1: "No Canadian experience requirements in Ontario job postings",
    intro:
      "Since January 1, 2026, an Ontario job posting, and any application form that goes with it, can't include a requirement related to Canadian experience. Ask for the skill and the years of experience, not where they were gained.",
    summary: [
      "Don't ask for Canadian work experience, in the posting or its application form.",
      "The same goes for a Canadian degree or diploma, and for an established network or client base in Canada.",
      "Professional licensing and registration requirements are still allowed.",
      "Ask for the skill and the years of experience instead.",
    ],
    law: [
      {
        text: "A public job posting, and any application form that goes with it, can't include any requirement related to Canadian experience.",
        cites: [esa("8.3 (1)")],
      },
      {
        text: "The Ministry's guide says this covers Canadian work experience, education credentials, and a requirement to have an established professional network or client base.",
        cites: [GUIDE],
      },
      {
        text: "It doesn't apply to professional licensing or registration requirements.",
        cites: [GUIDE],
      },
      {
        text: "Exceptions can be set by regulation; none have been.",
        cites: [esa("8.3 (2)")],
      },
      {
        text: 'The guide also points to the Ontario Human Rights Code and the Ontario Human Rights Commission\'s policy on removing the "Canadian experience" barrier.',
        cites: [GUIDE, { label: "OHRC policy", href: ohrc }],
      },
    ],
    copy: {
      heading: "Wording you can copy",
      kind: "wording",
      items: [
        {
          label: "Experience",
          text: "3+ years of experience in payroll administration.",
        },
        {
          label: "Education",
          text: "A degree in accounting or a related field, or equivalent education.",
        },
        {
          label: "Licensing (allowed)",
          text: "Registered, or eligible for registration, with the College of Nurses of Ontario.",
        },
        {
          label: "Client network",
          text: "Experience building and keeping client relationships.",
        },
      ],
    },
    example: {
      before:
        "Requirements:\n• 3+ years of Canadian payroll experience\n• Degree from a Canadian university\n• An established network of clients in Canada",
      after:
        "Requirements:\n• 3+ years of payroll experience\n• A degree in accounting or a related field\n• Experience building and keeping client relationships",
      note: "Each line asked for experience, education or a network gained in Canada. The fix keeps the skill and the years and drops where they came from.",
    },
    check:
      "CheckON reads each requirement in your posting, and in the application form if you add its questions, and flags anything tied to Canadian experience, quoting the line. The suggested fix keeps the skill and drops the place; you approve each change.",
    faq: [
      {
        q: "Can Ontario employers ask for Canadian experience?",
        a: "Not in a public job posting or its application form, for employers with 25 or more employees in Ontario (ESA, s. 8.3 (1), in force since January 1, 2026). Ask for the skill or the years of experience instead.",
      },
      {
        q: 'Is "Canadian experience preferred" or "an asset" allowed?',
        a: 'The law bans any requirement "related to" Canadian experience, and hasn\'t been tested on "preferred". CheckON treats "preferred" and "an asset" as a requirement, the cautious reading, and suggests dropping the word "Canadian".',
      },
      {
        q: "Can I still require a professional licence?",
        a: "Yes. The Ministry's guide says the rule doesn't apply to professional licensing or registration requirements, such as registration with a regulatory college.",
      },
      {
        q: "Does it cover application forms?",
        a: 'Yes. A question like "Do you have Canadian work experience?" on the application form breaks the same rule. CheckON can check the form\'s questions too, as one more check.',
      },
      {
        q: 'What about "Ontario experience" or "North American experience"?',
        a: "The law names Canadian experience; Ontario and North American experience aren't settled. CheckON marks them as a warning so you can decide. The safe fix is to drop the place.",
      },
      {
        q: "Can I ask whether someone can legally work in Canada?",
        a: "Yes. That's about the right to work, not about experience.",
      },
    ],
  },

  ai: {
    path: "/ontario-ai-disclosure-job-posting",
    title: "AI disclosure in Ontario job postings (2026): what to say",
    description:
      "If you use AI to screen, assess or select applicants, your Ontario job posting must say so. What counts as AI, recruiters who use AI for you, and a sentence you can copy.",
    name: "AI disclosure",
    blurb: "Say so if AI screens, assesses or selects applicants.",
    h1: "Disclosing AI in Ontario job postings",
    intro:
      "If you use artificial intelligence to screen, assess or select applicants, your Ontario job posting must say so. One plain sentence is enough.",
    summary: [
      "If AI screens, assesses or selects applicants for the job, the posting must say so.",
      "It applies when a recruiter or a vendor uses AI for you, too.",
      "One sentence is enough; you don't have to describe the tool.",
      'Name AI: a line about an "automated system" or an "applicant tracking system" may not count.',
    ],
    law: [
      {
        text: "An employer who uses artificial intelligence to screen, assess or select applicants for the position must include a statement in the posting disclosing that use.",
        cites: [esa("8.4 (1)")],
      },
      {
        text: "Artificial intelligence is a machine-based system that, for explicit or implicit objectives, infers from the input it receives to generate outputs such as predictions, content, recommendations or decisions.",
        cites: [oreg("2 (1)")],
      },
      {
        text: "The Ministry's guide says the rule applies when a third party, such as a recruiting firm, screens, assesses or selects applicants for you, and that it's enough to state that AI is used. Whether a particular tool is AI depends on the facts.",
        cites: [GUIDE],
      },
    ],
    copy: {
      heading: "Wording you can copy",
      kind: "wording",
      items: [
        {
          label: "Formal",
          text: "We use artificial intelligence to screen, assess or select applicants for this position.",
        },
        {
          label: "Plain",
          text: "We use AI tools to help screen, assess or select applicants.",
        },
        {
          label: "A recruiter uses AI",
          text: "Our recruiting partner uses artificial intelligence to screen, assess or select applicants for this position.",
        },
      ],
    },
    example: {
      before:
        "How to apply: Send your resume through our careers page. Applications are reviewed by our automated system.",
      after:
        "How to apply: Send your resume through our careers page. We use artificial intelligence to screen, assess or select applicants for this position.",
      note: "\"Automated system\" doesn't tell applicants that AI is used. The fix says it in the law's own words.",
    },
    check:
      "CheckON looks for a sentence that discloses AI and asks whether you, or a recruiter working for you, use AI on this job. If you do and the posting doesn't say so, it adds the formal sentence above; nothing changes until you approve it.",
    faq: [
      {
        q: "Do Ontario job postings have to disclose AI?",
        a: "Yes, when the employer uses artificial intelligence to screen, assess or select applicants for that job (ESA, s. 8.4 (1)). If you don't use AI, the posting doesn't need an AI statement.",
      },
      {
        q: "Does my applicant tracking system count as AI?",
        a: "It depends on what it does. The regulation defines AI as a machine-based system that infers from its input to produce outputs such as predictions, recommendations or decisions, and the Ministry says it depends on the facts. CheckON treats resume ranking, scoring and matching, and chat screening, as AI, the cautious reading; storing applications and sending emails isn't.",
      },
      {
        q: "Our recruiter uses AI, not us. Do we still disclose it?",
        a: "Yes. The Ministry's guide says the rule applies when a third party, such as a recruiting firm, screens, assesses or selects applicants for you.",
      },
      {
        q: "How detailed does the statement have to be?",
        a: "Not detailed. The Ministry's guide says it's enough to state that artificial intelligence is used to screen, assess or select applicants. You can say more if you want to.",
      },
      {
        q: "Should the posting say we don't use AI?",
        a: "The law doesn't ask for it. If you don't use AI to screen, assess or select applicants, you can leave AI out of the posting.",
      },
    ],
  },

  vacancy: {
    path: "/ontario-existing-vacancy-job-posting",
    title: "Existing vacancy statement in Ontario job postings (2026)",
    description:
      "Every Ontario job posting must say whether it's for an existing vacancy. What an existing vacancy is, talent pools and evergreen postings, and the sentence to copy.",
    name: "Existing vacancy",
    blurb: "Say whether the job is an existing vacancy, or not.",
    h1: "The existing vacancy statement in Ontario job postings",
    intro:
      "Every public job posting in Ontario must say whether it's for an existing vacancy or not. One sentence covers it, whichever the answer is.",
    summary: [
      "Every posting must say whether it's for an existing vacancy.",
      "An existing vacancy is a position that's imminently available for a qualified candidate to fill.",
      "A talent pool or evergreen posting for a specific job must say there's no existing vacancy.",
      "The statement doesn't commit you to hiring.",
    ],
    law: [
      {
        text: "A public job posting must include a statement disclosing whether the posting is for an existing vacancy or not.",
        cites: [esa("8.5 (1) (a)")],
      },
      {
        text: "The Ministry's guide defines an existing vacancy as a position that is imminently available for a qualified candidate to fill. If there isn't one, the posting must say so. The rule doesn't require you to fill the vacancy.",
        cites: [GUIDE],
      },
      {
        text: "Exceptions can be set by regulation; none have been.",
        cites: [esa("8.5 (2)")],
      },
    ],
    copy: {
      heading: "Wording you can copy",
      kind: "wording",
      items: [
        {
          label: "Existing vacancy",
          text: "This posting is for an existing vacancy.",
        },
        {
          label: "Existing vacancy, plain",
          text: "This job is an existing vacancy.",
        },
        {
          label: "No existing vacancy",
          text: "This posting is not for an existing vacancy.",
        },
        {
          label: "Talent pool",
          text: "This posting is not for an existing vacancy. We're collecting applications for future openings.",
        },
      ],
    },
    example: {
      before:
        "Join our talent community! We're always looking for Customer Service Representatives to join our Mississauga team.",
      after:
        "Join our talent community! We're always looking for Customer Service Representatives to join our Mississauga team. This posting is not for an existing vacancy. We're collecting applications for future openings.",
      note: "A talent pool posting for a specific job is still a public job posting. It must say there's no existing vacancy.",
    },
    check:
      "CheckON looks for the statement and, when the posting doesn't have one, asks whether the job is an existing vacancy. Your answer picks the sentence to add, from the wording above.",
    faq: [
      {
        q: "What is an existing vacancy?",
        a: "The Ministry's guide defines it as a position that is imminently available for a qualified candidate to fill. A job you're hiring for now is one; a talent pool or a posting for future openings isn't.",
      },
      {
        q: 'Do I have to use the words "existing vacancy"?',
        a: 'The law doesn\'t prescribe the words, but using them, as in "This posting is for an existing vacancy", leaves no doubt. Vague lines like "applications accepted on an ongoing basis" may not count; CheckON marks them as a warning.',
      },
      {
        q: "Does a talent pool posting need the statement?",
        a: "Yes, if it advertises a specific job to the public: it should say there's no existing vacancy. A general \"we're hiring\" campaign that names no specific job isn't covered.",
      },
      {
        q: 'Does saying "existing vacancy" commit me to hiring?',
        a: "No. The Ministry's guide says the rule doesn't require you to fill the vacancy.",
      },
      {
        q: "Where in the posting should it go?",
        a: "Anywhere in the posting. Near the end, with the pay and any AI statement, is easy for applicants to find.",
      },
    ],
  },

  interview: {
    path: "/ontario-45-day-interview-response",
    title: "Ontario's 45-day rule for interviewed applicants",
    description:
      "Since January 1, 2026, Ontario employers must tell each interviewed applicant within 45 days whether a hiring decision has been made. Who it covers, how to send it, and messages you can copy.",
    name: "45-day reply",
    blurb:
      "Tell each interviewed applicant within 45 days whether a decision was made.",
    h1: "The 45-day rule for interviewed applicants in Ontario",
    intro:
      "If you interview someone for a publicly advertised job, you must tell them within 45 days whether a hiring decision has been made. This rule isn't about what the posting says; it's about what you do after.",
    summary: [
      "Within 45 days of an interview, tell the applicant whether a hiring decision has been made.",
      "With several interviews, the 45 days run from the last one; interviews more than 45 days apart each need an update.",
      "In person, in writing, or by email, text or your applicant portal.",
      "Keep a copy of what you told them for three years.",
    ],
    law: [
      {
        text: "An employer who interviews an applicant for a publicly advertised job must give them the prescribed information within the prescribed time.",
        cites: [esa("8.6")],
      },
      {
        text: "The information is whether a hiring decision has been made. The time is 45 days after the interview, or after the last interview if there were several. It can be given in person, in writing or using technology.",
        cites: [oreg("5")],
      },
      {
        text: "An interview is a meeting, in person or using technology such as a phone or video call, where questions are asked to assess the applicant. Preliminary screening before choosing who to meet isn't an interview.",
        cites: [oreg("2 (2)")],
      },
      {
        text: "The Ministry's guide says interviews less than 45 days apart need one update and interviews more than 45 days apart need one after each, and that the rule applies to interviews on or after January 1, 2026, even when the job was posted earlier.",
        cites: [GUIDE],
      },
      {
        text: "Keep a copy of the information for three years after the day you gave it.",
        cites: [esa("15 (7.1.1)")],
      },
    ],
    copy: {
      heading: "Messages you can copy",
      kind: "wording",
      items: [
        {
          label: "Decision made",
          text: "Thank you for interviewing with us for the [job title] position. We've made a hiring decision, and we won't be moving forward with your application. We appreciate your time and interest.",
        },
        {
          label: "No decision yet",
          text: "Thank you for interviewing with us for the [job title] position. We haven't made a hiring decision yet. We'll let you know when we have.",
        },
      ],
    },
    example: {
      before:
        "Interview on March 3. No message after it: on April 17, day 45, the applicant still hasn't heard anything.",
      after:
        "Interview on March 3. Email on April 10: \"We haven't made a hiring decision yet. We'll let you know when we have.\" A copy goes in the posting's file.",
      note: 'Silence breaks the rule once 45 days pass. A short "no decision yet" message meets it.',
    },
    check:
      "A posting can't break this rule, so it isn't part of the check. Every CheckON result ends with a reminder of it under \"After you post\".",
    faq: [
      {
        q: "How long do Ontario employers have to respond after an interview?",
        a: "45 days from the interview, or from the last interview if there were several (O. Reg. 476/24, s. 5). The update says whether a hiring decision has been made.",
      },
      {
        q: "Does a phone screen count as an interview?",
        a: "Not if it's preliminary screening before you choose who to interview. The regulation defines an interview as a meeting, in person or using technology, where questions are asked to assess the applicant, and leaves preliminary screening out.",
      },
      {
        q: "Can I send it by email or through our applicant portal?",
        a: "Yes. The information can be given in person, in writing or using technology, so email, text or an update in your applicant portal all fit. The Ministry's guide has details on portal updates.",
      },
      {
        q: "Does it apply to jobs posted before 2026?",
        a: "Yes, for interviews on or after January 1, 2026. The Ministry's guide says it applies even when the job was posted before that date.",
      },
      {
        q: "Do I have to tell them who got the job?",
        a: "No. The rule asks only whether a hiring decision has been made.",
      },
    ],
  },

  records: {
    path: "/ontario-job-posting-record-keeping",
    title: "Ontario job posting records: what to keep for 3 years",
    description:
      "Ontario employers must keep every public job posting and its application form for 3 years after it comes down, and what they told interviewed applicants. What to keep, revised versions, and a checklist.",
    name: "3-year records",
    blurb:
      "Keep each posting, its form and your interview updates for 3 years.",
    h1: "Keeping job posting records for three years in Ontario",
    intro:
      "Ontario employers must keep a copy of every publicly advertised job posting, and any application form that goes with it, for three years after the posting comes down. What you told interviewed applicants is kept for three years too.",
    summary: [
      "Keep a copy of every public posting and its application form for 3 years after it comes down.",
      "If you change a posting while it's up, keep each version that was public.",
      "Keep what you told each interviewed applicant for 3 years after you told them.",
      "A recruiter or a vendor can keep them for you.",
    ],
    law: [
      {
        text: "Keep, or arrange for someone else to keep, a copy of every publicly advertised job posting and any application form that goes with it, for three years after the public can no longer see the posting.",
        cites: [esa("15 (7.1)")],
      },
      {
        text: "Keep a copy of what you told interviewed applicants under the 45-day rule for three years after the day you told them.",
        cites: [esa("15 (7.1.1)")],
      },
      {
        text: "The Ministry's guide says that if a posting is revised while it's up, you keep a copy of each version that was public, and that a document or web page the posting links to is part of the posting.",
        cites: [GUIDE],
      },
    ],
    copy: {
      heading: "A checklist for each posting",
      kind: "checklist",
      items: [
        {
          text: "Each version of the posting that was public, with the dates it went up and came down.",
        },
        { text: "Any document or web page the posting links to." },
        { text: "The application form, with its questions." },
        {
          text: "For each interviewed applicant: the interview dates, what you told them and when.",
        },
        {
          text: "The date the three years end: from when the posting came down, and from each update you gave.",
        },
      ],
    },
    example: {
      before:
        "The posting was edited twice on the job board; only the current version is saved. The application form lives in the applicant tracking system and changes every month.",
      after:
        "Each version saved as a PDF with its dates (January 6 to 20, then January 20 to February 14). The form's questions saved with them. Kept until at least February 14, 2029.",
      note: "Each version that was public needs a copy, not just the last one.",
    },
    check:
      "A posting can't break this rule, so it isn't part of the check. Every CheckON result ends with a reminder of it under \"After you post\". With a CheckON account you can turn on an archive that keeps the final version of each posting you approve, with its application form and linked documents, for three years after the takedown date you enter. It keeps the final version only, so keep earlier versions yourself.",
    faq: [
      {
        q: "How long do Ontario employers keep job postings?",
        a: "Three years after the posting comes down: a copy of every public job posting and any application form that goes with it (ESA, s. 15 (7.1)).",
      },
      {
        q: "Do I keep every version of a posting?",
        a: "Yes. The Ministry's guide says that if the posting is revised while it's up, you keep a copy of each version that was public.",
      },
      {
        q: "What about the 45-day updates to interviewed applicants?",
        a: "Keep a copy of what you told each one for three years after the day you told them (ESA, s. 15 (7.1.1)).",
      },
      {
        q: "Can our applicant tracking system or recruiter keep the records?",
        a: "Yes. The law lets you arrange for someone else to keep them. The duty to keep them is still yours.",
      },
      {
        q: "Does CheckON keep my postings?",
        a: "Not unless you turn on the archive in a CheckON account. It keeps the final version of each posting you approve, not every revision.",
      },
    ],
  },
}
