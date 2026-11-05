import { Source } from "./Source"
import { type Cite, type Rule, type RuleId, SOURCES, type Words } from "./types"

// The law's own French terms (Loi de 2000 sur les normes d'emploi, Règl. de l'Ont. 476/24): « annonce publique de
// poste », « rémunération prévue », « trier, évaluer ou sélectionner », « poste vacant existant », « entrevue ».
const { act, reg, guide, ohrc } = SOURCES.fr
const lne = (section: string): Cite => ({ label: `LNE, ${section}`, href: act })
const oreg = (section: string): Cite => ({
  label: `Règl. de l'Ont. 476/24, ${section}`,
  href: reg,
})
const GUIDE: Cite = { label: "Guide du ministère", href: guide }

export const WORDS: Words = {
  home: "CheckON",
  eyebrow: "Règles d'affichage de postes en Ontario",
  updated: "Mis à jour le 23 octobre 2026. Un résumé, pas un avis juridique.",
  other: { label: "In English", lang: "en" },
  short: "En bref",
  law: "Ce que dit la loi",
  before: "Avant",
  after: "Après",
  example: "Avant et après",
  header: "Vérifier une offre",
  checkHeading: "Comment CheckON le vérifie",
  checkButton: "Vérifier une offre gratuitement",
  checkNote:
    "Le site et la vérification sont en anglais pour le moment, et la vérification lit les offres rédigées en anglais.",
  scope: {
    heading: "À qui s'appliquent les règles",
    text: "Aux employeurs qui comptent 25 employés ou plus en Ontario le jour où le poste est affiché, pour les annonces publiques d'un poste précis dont le travail s'effectue en Ontario, que ce soit sur votre site carrières, un site d'emploi ou celui d'un recruteur. Une annonce réservée aux employés actuels, ou une campagne générale « nous embauchons » qui ne nomme aucun poste, n'est pas visée.",
    cites: [oreg("art. 1"), oreg("par. 2 (1)")],
  },
  faq: "Questions fréquentes",
  rules: "Les autres règles",
  copy: "Copier",
  copied: "Copié",
  copyAll: "Copier la liste",
  source: (
    <>
      Sources : la{" "}
      <Source href={act}>Loi de 2000 sur les normes d'emploi</Source> (LNE),
      partie III.1 et art. 15, le{" "}
      <Source href={reg}>Règlement de l'Ontario 476/24</Source> et le{" "}
      <Source href={guide}>
        guide du gouvernement de l'Ontario sur les annonces publiques de postes
      </Source>
      . Cette page les résume et ne constitue pas un avis juridique; pour votre
      situation, consultez un avocat en droit de l'emploi.
    </>
  ),
  footer: "Conformité des offres d'emploi en Ontario. Pas un avis juridique.",
}

export const RULES: Record<RuleId, Rule> = {
  pay: {
    path: "/fr/ontario-transparence-salariale-offre-emploi",
    title:
      "Transparence salariale en Ontario : la fourchette dans l'offre d'emploi",
    description:
      "Depuis le 1er janvier 2026, les offres d'emploi en Ontario doivent indiquer la rémunération prévue ou une fourchette d'au plus 50 000 $ par année. Ce qui compte comme rémunération, l'exemption de 200 000 $ et des formulations à copier.",
    name: "Fourchette salariale",
    blurb:
      "Indiquez la rémunération prévue, ou une fourchette d'au plus 50 000 $ par année.",
    h1: "La fourchette salariale dans les offres d'emploi en Ontario",
    intro:
      "Toute annonce publique de poste en Ontario doit indiquer la rémunération prévue pour le poste, ou une fourchette de rémunération prévue. L'écart d'une fourchette ne peut pas dépasser 50 000 $ par année. Voici ce que cela veut dire en pratique, avec des formulations à copier.",
    summary: [
      "Indiquez la rémunération prévue, ou une fourchette, dans chaque annonce publique.",
      "L'écart d'une fourchette est d'au plus 50 000 $ par année : de 85 000 $ à 135 000 $, c'est permis; de 85 000 $ à 140 000 $, non.",
      "Le salaire horaire, hebdomadaire ou mensuel compte aussi : la limite est l'équivalent annuel de 50 000 $.",
      "Les annonces dont la rémunération, ou le haut de la fourchette, dépasse 200 000 $ par année sont exemptées.",
    ],
    law: [
      {
        text: "Une annonce publique de poste doit inclure des renseignements sur la rémunération prévue pour le poste, ou sur la fourchette de rémunération prévue.",
        cites: [lne("par. 8.2 (1)")],
      },
      {
        text: "La rémunération s'entend du salaire : traitement, taux horaire, commission, rémunération à la pièce et primes liées aux heures, à la production ou à l'efficacité. Les pourboires, les indemnités de dépenses et de déplacement, les avantages sociaux, les options d'achat d'actions et les primes purement discrétionnaires n'en font pas partie.",
        cites: [oreg("par. 2 (2)"), lne("par. 1 (1)"), GUIDE],
      },
      {
        text: "L'écart d'une fourchette ne peut pas dépasser l'équivalent de 50 000 $ par année. Un écart d'exactement 50 000 $ est permis.",
        cites: [lne("par. 8.2 (3)"), oreg("art. 4")],
      },
      {
        text: "La règle ne s'applique pas lorsque la rémunération prévue, ou le haut de la fourchette, dépasse 200 000 $ par année. Exactement 200 000 $ reste visé.",
        cites: [lne("par. 8.2 (2)"), oreg("art. 3")],
      },
      {
        text: "Si la rémunération comporte plusieurs éléments, donnez des renseignements sur chacun. Lorsqu'un montant ne peut pas être fourni, le guide du ministère indique qu'on peut expliquer comment il est gagné, par exemple une prime pouvant aller jusqu'à 10 % du salaire annuel selon le rendement individuel, ou jusqu'à un certain montant en commissions de vente.",
        cites: [GUIDE],
      },
    ],
    copy: {
      heading: "Formulations à copier",
      kind: "wording",
      items: [
        {
          label: "Fourchette annuelle",
          text: "Rémunération prévue : de 62 000 $ à 74 000 $ par année.",
        },
        {
          label: "Fourchette horaire",
          text: "Salaire : de 24,50 $ à 28,00 $ l'heure.",
        },
        {
          label: "Salaire de base et commissions",
          text: "Rémunération prévue : salaire de base de 55 000 $ par année, plus commissions. La personne retenue peut s'attendre à gagner jusqu'à 20 000 $ par année en commissions.",
        },
        {
          label: "Salaire et prime",
          text: "Rémunération prévue : de 70 000 $ à 85 000 $ par année, plus une prime pouvant aller jusqu'à 10 % du salaire annuel selon le rendement individuel.",
        },
      ],
    },
    example: {
      before:
        "Salaire : concurrentiel, selon l'expérience.\nAvantages : assurance maladie et dentaire, cotisations REER de contrepartie.",
      after:
        "Rémunération prévue : de 62 000 $ à 74 000 $ par année, selon l'expérience.\nAvantages : assurance maladie et dentaire, cotisations REER de contrepartie.",
      note: "« Concurrentiel » ne dit rien de la rémunération prévue. La correction ajoute une fourchette de moins de 50 000 $ et laisse le reste tel quel.",
    },
    check:
      "CheckON repère la rémunération dans votre annonce, calcule l'écart d'une fourchette (salaire horaire, hebdomadaire et mensuel compris) et applique l'exemption de 200 000 $. Si la rémunération manque ou si la fourchette est trop large, il signale la ligne à corriger; il n'invente jamais de montant, et rien ne change sans votre approbation.",
    faq: [
      {
        q: "Les offres d'emploi en Ontario doivent-elles indiquer une fourchette salariale?",
        a: "Oui, pour les employeurs qui comptent 25 employés ou plus en Ontario. Depuis le 1er janvier 2026, toute annonce publique de poste doit indiquer la rémunération prévue ou une fourchette de rémunération prévue (LNE, par. 8.2 (1)). Les annonces dont la rémunération, ou le haut de la fourchette, dépasse 200 000 $ par année sont exemptées.",
      },
      {
        q: "Quel écart une fourchette salariale peut-elle avoir en Ontario?",
        a: "Au plus l'équivalent de 50 000 $ par année (Règl. de l'Ont. 476/24, art. 4). De 85 000 $ à 135 000 $, c'est permis; de 85 000 $ à 140 000 $, non.",
      },
      {
        q: "Comment la limite de 50 000 $ s'applique-t-elle au salaire horaire?",
        a: "Le règlement parle d'une somme « équivalant à 50 000 $ par année » sans dire comment convertir. CheckON multiplie par les heures hebdomadaires du poste (40 si vous ne les indiquez pas) et par 52 semaines, et demande les heures quand le résultat est proche de la limite. À 40 heures par semaine, de 25 $ à 48 $ l'heure donne de 52 000 $ à 99 840 $ par année : un écart de 47 840 $, donc sous la limite.",
      },
      {
        q: "Puis-je écrire « salaire concurrentiel » ou « selon l'expérience »?",
        a: "Pas seulement. Ni l'un ni l'autre n'indique la rémunération prévue. Donnez un montant ou une fourchette; vous pouvez ajouter « selon l'expérience ».",
      },
      {
        q: "Les commissions et les primes comptent-elles?",
        a: "Les commissions et les primes liées aux heures, à la production ou à l'efficacité font partie du salaire, donc elles comptent. Les pourboires, les indemnités de dépenses, les avantages sociaux, les options d'achat d'actions et les primes purement discrétionnaires, non. Si la rémunération comporte plusieurs éléments, donnez des renseignements sur chacun, par exemple le salaire de base et le montant de commissions auquel la personne peut s'attendre.",
      },
      {
        q: "Et « 70 000 $ et plus » ou « jusqu'à 90 000 $ »?",
        a: "La loi ne tranche pas le cas d'un montant sans plancher ou sans plafond. CheckON le traite comme une fourchette incomplète et demande les deux bornes, la lecture prudente.",
      },
    ],
  },

  cex: {
    path: "/fr/ontario-experience-canadienne-offre-emploi",
    title: "Expérience canadienne dans les offres d'emploi en Ontario (2026)",
    description:
      "Les offres d'emploi et les formulaires de candidature en Ontario ne peuvent pas exiger d'expérience canadienne. Ce que cela vise (expérience de travail, diplômes canadiens, clientèle au Canada), ce qui reste permis et comment reformuler.",
    name: "Expérience canadienne",
    blurb:
      "N'exigez pas d'expérience canadienne, ni dans l'annonce ni dans le formulaire de candidature.",
    h1: "Aucune exigence d'expérience canadienne dans les offres d'emploi en Ontario",
    intro:
      "Depuis le 1er janvier 2026, une annonce publique de poste en Ontario, et tout formulaire de candidature qui l'accompagne, ne peut contenir aucune exigence relative à l'expérience canadienne. Demandez la compétence et les années d'expérience, pas l'endroit où elles ont été acquises.",
    summary: [
      "N'exigez pas d'expérience de travail canadienne, ni dans l'annonce ni dans le formulaire de candidature.",
      "Il en va de même pour un diplôme canadien et pour un réseau professionnel ou une clientèle établie au Canada.",
      "Les exigences de permis d'exercice et d'inscription à un ordre professionnel restent permises.",
      "Demandez plutôt la compétence et les années d'expérience.",
    ],
    law: [
      {
        text: "Une annonce publique de poste, et tout formulaire de candidature afférent, ne peut contenir aucune exigence relative à l'expérience canadienne.",
        cites: [lne("par. 8.3 (1)")],
      },
      {
        text: "Selon le guide du ministère, cela vise l'expérience professionnelle, les attestations d'études et l'obligation de disposer d'un réseau professionnel ou d'une clientèle établie.",
        cites: [GUIDE],
      },
      {
        text: "L'interdiction ne s'applique pas aux exigences de permis d'exercice et d'inscription des professionnels.",
        cites: [GUIDE],
      },
      {
        text: "Des exceptions peuvent être prévues par règlement; aucune ne l'a été.",
        cites: [lne("par. 8.3 (2)")],
      },
      {
        text: "Le guide renvoie aussi au Code des droits de la personne de l'Ontario et à la politique de la Commission ontarienne des droits de la personne sur la suppression des obstacles liés à l'expérience canadienne.",
        cites: [GUIDE, { label: "Politique de la CODP", href: ohrc }],
      },
    ],
    copy: {
      heading: "Formulations à copier",
      kind: "wording",
      items: [
        {
          label: "Expérience",
          text: "3 ans ou plus d'expérience en administration de la paie.",
        },
        {
          label: "Formation",
          text: "Diplôme en comptabilité ou dans un domaine connexe, ou formation équivalente.",
        },
        {
          label: "Permis d'exercice (autorisé)",
          text: "Inscription, ou admissibilité à l'inscription, à l'Ordre des infirmières et infirmiers de l'Ontario.",
        },
        {
          label: "Clientèle",
          text: "Expérience dans l'établissement et le maintien de relations avec la clientèle.",
        },
      ],
    },
    example: {
      before:
        "Exigences :\n• 3 ans ou plus d'expérience canadienne en paie\n• Diplôme d'une université canadienne\n• Clientèle établie au Canada",
      after:
        "Exigences :\n• 3 ans ou plus d'expérience en paie\n• Diplôme en comptabilité ou dans un domaine connexe\n• Expérience dans l'établissement et le maintien de relations avec la clientèle",
      note: "Chaque ligne demandait une expérience, une formation ou une clientèle acquise au Canada. La correction garde la compétence et les années, et retire l'endroit.",
    },
    check:
      "CheckON lit chaque exigence de votre annonce, et du formulaire de candidature si vous en ajoutez les questions, et signale tout ce qui touche l'expérience canadienne en citant la ligne. La correction proposée garde la compétence et retire l'endroit; vous approuvez chaque changement.",
    faq: [
      {
        q: "Les employeurs de l'Ontario peuvent-ils exiger une expérience canadienne?",
        a: "Non, ni dans une annonce publique de poste ni dans son formulaire de candidature, pour les employeurs qui comptent 25 employés ou plus en Ontario (LNE, par. 8.3 (1), en vigueur depuis le 1er janvier 2026). Demandez plutôt la compétence ou les années d'expérience.",
      },
      {
        q: "« Expérience canadienne, un atout » : est-ce permis?",
        a: "La loi interdit toute exigence « relative à » l'expérience canadienne, et le cas de l'« atout » n'a pas encore été tranché. CheckON traite « un atout » et « de préférence » comme une exigence, la lecture prudente, et propose de retirer le mot « canadienne ».",
      },
      {
        q: "Puis-je encore exiger un permis d'exercice?",
        a: "Oui. Le guide du ministère indique que la règle ne s'applique pas aux exigences de permis d'exercice ou d'inscription à un ordre professionnel.",
      },
      {
        q: "Les formulaires de candidature sont-ils visés?",
        a: "Oui. Une question comme « Avez-vous de l'expérience de travail canadienne? » dans le formulaire enfreint la même règle. CheckON peut aussi vérifier les questions du formulaire, ce qui compte comme une vérification de plus.",
      },
      {
        q: "Et l'« expérience en Ontario » ou l'« expérience nord-américaine »?",
        a: "La loi vise l'expérience canadienne; l'expérience en Ontario ou nord-américaine n'est pas tranchée. CheckON la signale comme un avertissement pour que vous décidiez. La correction prudente est de retirer l'endroit.",
      },
      {
        q: "Puis-je demander si la personne a le droit de travailler au Canada?",
        a: "Oui. C'est une question de droit de travailler, pas d'expérience.",
      },
    ],
  },

  ai: {
    path: "/fr/ontario-divulgation-ia-offre-emploi",
    title: "Divulgation de l'IA dans les offres d'emploi en Ontario (2026)",
    description:
      "Si vous utilisez l'IA pour trier, évaluer ou sélectionner des candidats, votre offre d'emploi en Ontario doit le dire. Ce qui compte comme IA, les recruteurs qui l'utilisent pour vous et une phrase à copier.",
    name: "Divulgation de l'IA",
    blurb: "Dites-le si l'IA trie, évalue ou sélectionne des candidats.",
    h1: "Divulguer l'IA dans les offres d'emploi en Ontario",
    intro:
      "Si vous avez recours à l'intelligence artificielle pour trier, évaluer ou sélectionner des candidats, votre annonce de poste en Ontario doit le dire. Une phrase simple suffit.",
    summary: [
      "Si l'IA trie, évalue ou sélectionne des candidats au poste, l'annonce doit le dire.",
      "C'est aussi le cas quand un recruteur ou un fournisseur utilise l'IA pour vous.",
      "Une phrase suffit; vous n'avez pas à décrire l'outil.",
      "Nommez l'IA : une phrase sur un « système de suivi des candidatures » pourrait ne pas suffire.",
    ],
    law: [
      {
        text: "L'employeur qui a recours à l'intelligence artificielle pour trier, évaluer ou sélectionner des candidats au poste inclut dans l'annonce une déclaration divulguant ce recours.",
        cites: [lne("par. 8.4 (1)")],
      },
      {
        text: "L'intelligence artificielle est un système automatisé qui, pour des objectifs explicites ou implicites, fait des déductions à partir des entrées qu'il reçoit afin de générer des résultats tels que des prévisions, des contenus, des recommandations ou des décisions.",
        cites: [oreg("par. 2 (1)")],
      },
      {
        text: "Selon le guide du ministère, la règle s'applique aussi quand un tiers, comme une agence de recrutement, trie, évalue ou sélectionne des candidats pour vous, et il suffit d'indiquer que l'intelligence artificielle est utilisée. Savoir si un outil donné est de l'IA dépend des faits.",
        cites: [GUIDE],
      },
    ],
    copy: {
      heading: "Formulations à copier",
      kind: "wording",
      items: [
        {
          label: "Formelle",
          text: "Nous avons recours à l'intelligence artificielle pour trier, évaluer ou sélectionner les candidats à ce poste.",
        },
        {
          label: "Simple",
          text: "Nous utilisons des outils d'IA pour nous aider à trier, évaluer ou sélectionner les candidats.",
        },
        {
          label: "Un recruteur utilise l'IA",
          text: "Notre partenaire de recrutement a recours à l'intelligence artificielle pour trier, évaluer ou sélectionner les candidats à ce poste.",
        },
      ],
    },
    example: {
      before:
        "Pour postuler : envoyez votre CV par notre site carrières. Les candidatures sont examinées par notre système de suivi.",
      after:
        "Pour postuler : envoyez votre CV par notre site carrières. Nous avons recours à l'intelligence artificielle pour trier, évaluer ou sélectionner les candidats à ce poste.",
      note: "« Notre système de suivi » ne dit pas aux candidats que l'IA est utilisée. La correction le dit avec les mots de la loi.",
    },
    check:
      "CheckON cherche une phrase qui divulgue l'IA et vous demande si vous, ou un recruteur qui travaille pour vous, utilisez l'IA pour ce poste. Si c'est le cas et que l'annonce ne le dit pas, il ajoute une phrase de divulgation; rien ne change sans votre approbation.",
    faq: [
      {
        q: "Les offres d'emploi en Ontario doivent-elles divulguer l'IA?",
        a: "Oui, lorsque l'employeur a recours à l'intelligence artificielle pour trier, évaluer ou sélectionner les candidats à ce poste (LNE, par. 8.4 (1)). Si vous n'utilisez pas l'IA, l'annonce n'a pas besoin de déclaration sur l'IA.",
      },
      {
        q: "Mon système de suivi des candidatures compte-t-il comme de l'IA?",
        a: "Cela dépend de ce qu'il fait. Le règlement définit l'IA comme un système automatisé qui fait des déductions à partir de ses entrées pour produire des résultats comme des prévisions, des recommandations ou des décisions, et le ministère précise que cela dépend des faits. CheckON considère le classement, la notation et l'appariement de CV, ainsi que la présélection par agent conversationnel, comme de l'IA, la lecture prudente; conserver des candidatures et envoyer des courriels, non.",
      },
      {
        q: "C'est notre recruteur qui utilise l'IA, pas nous. Faut-il quand même le divulguer?",
        a: "Oui. Le guide du ministère indique que la règle s'applique quand un tiers, comme une agence de recrutement, trie, évalue ou sélectionne des candidats pour vous.",
      },
      {
        q: "La déclaration doit-elle être détaillée?",
        a: "Non. Le guide du ministère indique qu'il suffit de dire que l'intelligence artificielle est utilisée pour trier, évaluer ou sélectionner les candidats. Vous pouvez en dire plus si vous le souhaitez.",
      },
      {
        q: "L'annonce doit-elle dire que nous n'utilisons pas l'IA?",
        a: "La loi ne le demande pas. Si vous n'utilisez pas l'IA pour trier, évaluer ou sélectionner les candidats, vous pouvez ne pas en parler.",
      },
    ],
  },

  vacancy: {
    path: "/fr/ontario-poste-vacant-existant-offre-emploi",
    title:
      "Poste vacant existant : la mention dans les offres d'emploi en Ontario",
    description:
      "Toute offre d'emploi en Ontario doit indiquer si elle concerne un poste vacant existant. Ce qu'est un poste vacant existant, les banques de candidatures et la phrase à copier.",
    name: "Poste vacant existant",
    blurb: "Indiquez si le poste est un poste vacant existant, ou non.",
    h1: "La mention de poste vacant existant dans les offres d'emploi en Ontario",
    intro:
      "Toute annonce publique de poste en Ontario doit indiquer si elle concerne un poste vacant existant ou non. Une phrase suffit, quelle que soit la réponse.",
    summary: [
      "Chaque annonce doit indiquer si elle concerne un poste vacant existant.",
      "Un poste vacant existant est un poste disponible de façon imminente pour un candidat qualifié.",
      "Une banque de candidatures pour un poste précis doit indiquer qu'il n'y a pas de poste vacant existant.",
      "La mention ne vous oblige pas à embaucher.",
    ],
    law: [
      {
        text: "Une annonce publique de poste doit inclure une déclaration indiquant si elle concerne un poste vacant existant ou non.",
        cites: [lne("al. 8.5 (1) a)")],
      },
      {
        text: "Le guide du ministère définit le poste vacant comme un poste disponible de façon imminente pour un candidat qualifié. S'il n'y en a pas, l'annonce doit le dire. La règle ne vous oblige pas à pourvoir le poste.",
        cites: [GUIDE],
      },
      {
        text: "Des exceptions peuvent être prévues par règlement; aucune ne l'a été.",
        cites: [lne("par. 8.5 (2)")],
      },
    ],
    copy: {
      heading: "Formulations à copier",
      kind: "wording",
      items: [
        {
          label: "Poste vacant existant",
          text: "Cette annonce concerne un poste vacant existant.",
        },
        {
          label: "Poste vacant existant, simple",
          text: "Il s'agit d'un poste vacant existant.",
        },
        {
          label: "Aucun poste vacant existant",
          text: "Cette annonce ne concerne pas un poste vacant existant.",
        },
        {
          label: "Banque de candidatures",
          text: "Cette annonce ne concerne pas un poste vacant existant. Nous recueillons des candidatures pour de futures ouvertures de postes.",
        },
      ],
    },
    example: {
      before:
        "Joignez-vous à notre communauté de talents! Nous sommes toujours à la recherche de représentants du service à la clientèle pour notre équipe de Mississauga.",
      after:
        "Joignez-vous à notre communauté de talents! Nous sommes toujours à la recherche de représentants du service à la clientèle pour notre équipe de Mississauga. Cette annonce ne concerne pas un poste vacant existant. Nous recueillons des candidatures pour de futures ouvertures de postes.",
      note: "Une banque de candidatures pour un poste précis reste une annonce publique de poste. Elle doit indiquer qu'il n'y a pas de poste vacant existant.",
    },
    check:
      "CheckON cherche la mention et, si l'annonce n'en a pas, vous demande si le poste est un poste vacant existant. Votre réponse choisit la phrase à ajouter.",
    faq: [
      {
        q: "Qu'est-ce qu'un poste vacant existant?",
        a: "Le guide du ministère le définit comme un poste disponible de façon imminente pour un candidat qualifié. Un poste que vous pourvoyez maintenant en est un; une banque de candidatures ou une annonce pour de futures ouvertures, non.",
      },
      {
        q: "Dois-je utiliser les mots « poste vacant existant »?",
        a: "La loi n'impose pas de formulation, mais ces mots, comme dans « Cette annonce concerne un poste vacant existant », ne laissent aucun doute. Une phrase vague comme « candidatures acceptées en continu » pourrait ne pas suffire; CheckON la signale comme un avertissement.",
      },
      {
        q: "Une annonce de banque de candidatures a-t-elle besoin de la mention?",
        a: "Oui, si elle annonce un poste précis au public : elle doit indiquer qu'il n'y a pas de poste vacant existant. Une campagne générale « nous embauchons » qui ne nomme aucun poste précis n'est pas visée.",
      },
      {
        q: "La mention m'oblige-t-elle à embaucher?",
        a: "Non. Le guide du ministère précise que la règle n'oblige pas l'employeur à pourvoir le poste.",
      },
      {
        q: "Où placer la mention dans l'annonce?",
        a: "N'importe où dans l'annonce. Vers la fin, avec la rémunération et toute déclaration sur l'IA, les candidats la trouvent facilement.",
      },
    ],
  },

  interview: {
    path: "/fr/ontario-reponse-45-jours-entrevue",
    title: "La règle des 45 jours après une entrevue en Ontario",
    description:
      "Depuis le 1er janvier 2026, les employeurs de l'Ontario doivent dire à chaque candidat reçu en entrevue, dans les 45 jours, si une décision d'embauche a été prise. Qui est visé, comment l'envoyer et des messages à copier.",
    name: "Réponse en 45 jours",
    blurb:
      "Dites à chaque candidat reçu en entrevue, dans les 45 jours, si une décision a été prise.",
    h1: "La règle des 45 jours pour les candidats reçus en entrevue en Ontario",
    intro:
      "Si vous faites passer une entrevue à un candidat pour un poste ayant fait l'objet d'une annonce publique, vous devez lui dire dans les 45 jours si une décision d'embauche a été prise. Cette règle ne porte pas sur le contenu de l'annonce, mais sur ce que vous faites ensuite.",
    summary: [
      "Dans les 45 jours suivant une entrevue, dites au candidat si une décision d'embauche a été prise.",
      "Avec plusieurs entrevues, les 45 jours courent à partir de la dernière; des entrevues à plus de 45 jours d'intervalle demandent chacune une réponse.",
      "En personne, par écrit, ou par courriel, texto ou votre portail de candidature.",
      "Conservez une copie de ce que vous lui avez dit pendant trois ans.",
    ],
    law: [
      {
        text: "L'employeur qui fait passer une entrevue à un candidat à un poste ayant fait l'objet d'une annonce publique lui fournit les renseignements prescrits dans les délais prescrits.",
        cites: [lne("art. 8.6")],
      },
      {
        text: "Le renseignement : si une décision d'embauche a été prise. Le délai : 45 jours suivant l'entrevue, ou suivant la dernière entrevue s'il y en a eu plusieurs. Il est fourni en personne, par écrit ou à l'aide de moyens technologiques.",
        cites: [oreg("art. 5")],
      },
      {
        text: "Une entrevue est une rencontre, en personne ou à l'aide de moyens technologiques comme le téléphone ou la vidéoconférence, où des questions sont posées pour évaluer le candidat. La présélection qui précède le choix des personnes rencontrées n'en est pas une.",
        cites: [oreg("par. 2 (2)")],
      },
      {
        text: "Le guide du ministère précise que des entrevues à moins de 45 jours d'intervalle demandent une seule réponse, que des entrevues à plus de 45 jours d'intervalle en demandent une après chacune, et que la règle s'applique aux entrevues tenues à partir du 1er janvier 2026, même pour un poste affiché avant cette date.",
        cites: [GUIDE],
      },
      {
        text: "Conservez une copie des renseignements pendant trois ans après le jour où vous les avez fournis.",
        cites: [lne("par. 15 (7.1.1)")],
      },
    ],
    copy: {
      heading: "Messages à copier",
      kind: "wording",
      items: [
        {
          label: "Décision prise",
          text: "Merci d'avoir passé une entrevue avec nous pour le poste de [titre du poste]. Nous avons pris une décision d'embauche et nous ne donnerons pas suite à votre candidature. Nous vous remercions de votre temps et de votre intérêt.",
        },
        {
          label: "Pas encore de décision",
          text: "Merci d'avoir passé une entrevue avec nous pour le poste de [titre du poste]. Nous n'avons pas encore pris de décision d'embauche. Nous vous en informerons dès que ce sera fait.",
        },
      ],
    },
    example: {
      before:
        "Entrevue le 3 mars. Aucun message ensuite : le 17 avril, 45e jour, le candidat n'a toujours rien reçu.",
      after:
        "Entrevue le 3 mars. Courriel le 10 avril : « Nous n'avons pas encore pris de décision d'embauche. Nous vous en informerons dès que ce sera fait. » Une copie va au dossier de l'annonce.",
      note: "Le silence enfreint la règle après 45 jours. Un court message « pas encore de décision » la respecte.",
    },
    check:
      "Une annonce ne peut pas enfreindre cette règle, alors elle ne fait pas partie de la vérification. Chaque résultat de CheckON se termine par un rappel de cette règle, sous « After you post » (après l'affichage).",
    faq: [
      {
        q: "De combien de temps les employeurs de l'Ontario disposent-ils pour répondre après une entrevue?",
        a: "45 jours à partir de l'entrevue, ou de la dernière entrevue s'il y en a eu plusieurs (Règl. de l'Ont. 476/24, art. 5). La réponse indique si une décision d'embauche a été prise.",
      },
      {
        q: "Un appel de présélection compte-t-il comme une entrevue?",
        a: "Pas s'il s'agit d'une présélection avant de choisir les personnes à rencontrer. Le règlement définit l'entrevue comme une rencontre, en personne ou à l'aide de moyens technologiques, où des questions sont posées pour évaluer le candidat, et en exclut la présélection.",
      },
      {
        q: "Puis-je répondre par courriel ou par notre portail de candidature?",
        a: "Oui. Les renseignements peuvent être fournis en personne, par écrit ou à l'aide de moyens technologiques : un courriel, un texto ou une mise à jour dans votre portail conviennent. Le guide du ministère donne des précisions sur les mises à jour par portail.",
      },
      {
        q: "La règle s'applique-t-elle aux postes affichés avant 2026?",
        a: "Oui, pour les entrevues tenues à partir du 1er janvier 2026. Le guide du ministère précise qu'elle s'applique même si le poste a été affiché avant cette date.",
      },
      {
        q: "Dois-je dire qui a obtenu le poste?",
        a: "Non. La règle demande seulement si une décision d'embauche a été prise.",
      },
    ],
  },

  records: {
    path: "/fr/ontario-conservation-offres-emploi",
    title: "Conservation des offres d'emploi en Ontario : quoi garder 3 ans",
    description:
      "Les employeurs de l'Ontario doivent conserver chaque annonce publique de poste et son formulaire de candidature pendant 3 ans après son retrait, ainsi que ce qu'ils ont dit aux candidats reçus en entrevue. Quoi garder, les versions modifiées et une liste de contrôle.",
    name: "Dossiers pendant 3 ans",
    blurb:
      "Conservez chaque annonce, son formulaire et vos réponses après entrevue pendant 3 ans.",
    h1: "Conserver les dossiers d'affichage de postes pendant trois ans en Ontario",
    intro:
      "Les employeurs de l'Ontario doivent conserver une copie de chaque annonce publique de poste, et de tout formulaire de candidature afférent, pendant trois ans après le retrait de l'annonce. Ce que vous avez dit aux candidats reçus en entrevue se conserve aussi trois ans.",
    summary: [
      "Conservez une copie de chaque annonce publique et de son formulaire de candidature pendant 3 ans après son retrait.",
      "Si vous modifiez une annonce pendant qu'elle est affichée, conservez chaque version publiée.",
      "Conservez ce que vous avez dit à chaque candidat reçu en entrevue pendant 3 ans après le lui avoir dit.",
      "Un recruteur ou un fournisseur peut les conserver pour vous.",
    ],
    law: [
      {
        text: "Conservez, ou chargez un tiers de conserver, une copie de chaque annonce publique de poste et de tout formulaire de candidature afférent pendant trois ans après qu'il est mis fin à l'accès du grand public à l'annonce.",
        cites: [lne("par. 15 (7.1)")],
      },
      {
        text: "Conservez une copie de ce que vous avez dit aux candidats reçus en entrevue, en application de la règle des 45 jours, pendant trois ans après le jour où vous le leur avez dit.",
        cites: [lne("par. 15 (7.1.1)")],
      },
      {
        text: "Selon le guide du ministère, si une annonce est révisée pendant la période d'affichage, il faut conserver une copie de chaque version publiée, et un document ou une page Web vers lequel l'annonce renvoie fait partie de l'annonce.",
        cites: [GUIDE],
      },
    ],
    copy: {
      heading: "Une liste de contrôle pour chaque annonce",
      kind: "checklist",
      items: [
        {
          text: "Chaque version publiée de l'annonce, avec ses dates d'affichage et de retrait.",
        },
        { text: "Tout document ou page Web vers lequel l'annonce renvoie." },
        { text: "Le formulaire de candidature, avec ses questions." },
        {
          text: "Pour chaque candidat reçu en entrevue : les dates d'entrevue, ce que vous lui avez dit et quand.",
        },
        {
          text: "La date de fin des trois ans : à partir du retrait de l'annonce, et de chaque réponse fournie.",
        },
      ],
    },
    example: {
      before:
        "L'annonce a été modifiée deux fois sur le site d'emploi; seule la version actuelle est conservée. Le formulaire de candidature est dans le système de suivi des candidatures et change chaque mois.",
      after:
        "Chaque version enregistrée en PDF avec ses dates (du 6 au 20 janvier, puis du 20 janvier au 14 février). Les questions du formulaire enregistrées avec elles. Conservées au moins jusqu'au 14 février 2029.",
      note: "Chaque version publiée doit être conservée, pas seulement la dernière.",
    },
    check:
      "Une annonce ne peut pas enfreindre cette règle, alors elle ne fait pas partie de la vérification. Chaque résultat de CheckON se termine par un rappel de cette règle, sous « After you post » (après l'affichage). Un compte CheckON offre une archive facultative qui conserve la version finale de chaque annonce approuvée, avec son formulaire de candidature et ses documents liés, pendant trois ans après la date de retrait que vous indiquez. Elle ne garde que la version finale : conservez vous-même les versions antérieures.",
    faq: [
      {
        q: "Pendant combien de temps les employeurs de l'Ontario conservent-ils les offres d'emploi?",
        a: "Trois ans après le retrait de l'annonce : une copie de chaque annonce publique de poste et de tout formulaire de candidature afférent (LNE, par. 15 (7.1)).",
      },
      {
        q: "Dois-je conserver chaque version d'une annonce?",
        a: "Oui. Le guide du ministère précise que si l'annonce est révisée pendant la période d'affichage, il faut conserver une copie de chaque version publiée.",
      },
      {
        q: "Et les réponses de la règle des 45 jours?",
        a: "Conservez une copie de ce que vous avez dit à chaque candidat pendant trois ans après le jour où vous le lui avez dit (LNE, par. 15 (7.1.1)).",
      },
      {
        q: "Notre système de suivi des candidatures ou notre recruteur peut-il conserver les dossiers?",
        a: "Oui. La loi permet de charger un tiers de les conserver. L'obligation de les conserver reste la vôtre.",
      },
      {
        q: "CheckON conserve-t-il mes annonces?",
        a: "Seulement si vous activez l'archive dans un compte CheckON. Elle conserve la version finale de chaque annonce approuvée, pas chaque révision.",
      },
    ],
  },
}
