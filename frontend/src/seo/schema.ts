/** JSON-LD builders. Every field here must be visible on the page. */

import { SITE_URL, type PageMeta } from "./meta";

const CONTEXT = "https://schema.org";

export function siteSchemas(): object[] {
  return [
    {
      "@context": CONTEXT,
      "@type": "Organization",
      name: "RozgarBoard",
      url: SITE_URL,
      logo: `${SITE_URL}/favicon.svg`,
      description:
        "Government job notifications linked to official sources, with eligibility checks and study plans.",
    },
    {
      "@context": CONTEXT,
      "@type": "WebSite",
      name: "RozgarBoard",
      url: SITE_URL,
      inLanguage: "en-IN",
    },
  ];
}

export function breadcrumbSchema(path: string, label: string): object {
  const trail = [{ name: "Home", item: SITE_URL + "/" }];
  if (path !== "/") trail.push({ name: label, item: SITE_URL + path });
  return {
    "@context": CONTEXT,
    "@type": "BreadcrumbList",
    itemListElement: trail.map((entry, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: entry.name,
      item: entry.item,
    })),
  };
}

export function webPageSchema(meta: PageMeta): object {
  return {
    "@context": CONTEXT,
    "@type": "WebPage",
    name: meta.title,
    description: meta.description,
    url: meta.canonical,
    inLanguage: "en-IN",
    isPartOf: { "@type": "WebSite", name: "RozgarBoard", url: SITE_URL },
  };
}

/** Only used where the matching questions are visible in the rendered HTML. */
export function faqSchema(qa: Array<[string, string]>): object {
  return {
    "@context": CONTEXT,
    "@type": "FAQPage",
    mainEntity: qa.map(([question, answer]) => ({
      "@type": "Question",
      name: question,
      acceptedAnswer: { "@type": "Answer", text: answer },
    })),
  };
}

export function schemasFor(path: string, meta: PageMeta): object[] {
  if (path === "/404") return [];
  const label = meta.title.split(" — ")[0] ?? meta.title;
  return [webPageSchema(meta), ...(path === "/" ? [] : [breadcrumbSchema(path, label)])];
}
