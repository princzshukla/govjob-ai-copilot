/** Pure, server-side page metadata. No React, no browser globals. */

export const SITE_URL = "https://www.rozgarboard.in";

export interface PageMeta {
  title: string;
  description: string;
  canonical: string;
  robots: string;
  ogType: string;
}

const DEFAULT: Omit<PageMeta, "canonical"> = {
  title: "RozgarBoard — Government Jobs in India",
  description:
    "Government job notifications from official sources, eligibility check and week-by-week study plan. Free.",
  robots: "index, follow, max-image-preview:large",
  ogType: "website",
};

const PAGES: Record<string, Partial<PageMeta>> = {
  "/": {
    title: "Government Jobs 2026 — Verified Notifications & Deadlines",
    description:
      "Live government job notifications with official PDF links, verified deadlines and eligibility in seconds. Updated daily.",
  },
  "/admit-cards": {
    title: "Admit Cards 2026 — Download Links & Exam Dates",
    description:
      "Government exam admit cards and exam-city intimations with official download links, checked regularly against the boards.",
  },
  "/eligibility": {
    title: "Government Job Eligibility Checker — Free, No Signup",
    description:
      "Check which government jobs you qualify for using age, qualification and domicile rules taken from the official notifications.",
  },
  "/roadmap": {
    title: "My Study Roadmap — RozgarBoard",
    description: "A personal week-by-week study plan. Sign in to view your roadmap.",
    robots: "noindex, nofollow",
  },
  "/tools/photo-signature-resizer": {
    title: "SSC / IBPS / UPSC Photo & Signature Resizer",
    description:
      "Resize and compress government-exam photos and signatures to exact board limits. Every file is processed in your browser.",
  },
  "/privacy": {
    title: "Privacy Policy — RozgarBoard",
    description: "How RozgarBoard handles your data, cookies and account information.",
    robots: "index, follow",
  },
  "/404": {
    title: "Page Not Found — RozgarBoard",
    description: "The page you were looking for could not be found.",
    robots: "noindex, follow",
  },
};

export function metaFor(path: string): PageMeta {
  const page = PAGES[path] ?? {};
  return {
    ...DEFAULT,
    ...page,
    canonical: SITE_URL + path.replace(/\/$/, "") + (path === "/" ? "/" : ""),
  };
}

/** Escape a value for use inside an HTML attribute. */
export function esc(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/** Build the `<head>` fragment injected into a prerendered page. */
export function headHtml(meta: PageMeta, schemas: object[]): string {
  const json = schemas
    .map((s) => `<script type="application/ld+json">${JSON.stringify(s).replace(/</g, "\\u003c")}</script>`)
    .join("\n    ");

  return [
    `<title>${esc(meta.title)}</title>`,
    `<meta name="description" content="${esc(meta.description)}" />`,
    `<meta name="robots" content="${esc(meta.robots)}" />`,
    `<link rel="canonical" href="${esc(meta.canonical)}" />`,
    `<meta property="og:type" content="${esc(meta.ogType)}" />`,
    `<meta property="og:title" content="${esc(meta.title)}" />`,
    `<meta property="og:description" content="${esc(meta.description)}" />`,
    `<meta property="og:url" content="${esc(meta.canonical)}" />`,
    `<meta property="og:image" content="${SITE_URL}/favicon.svg" />`,
    `<meta name="twitter:card" content="summary" />`,
    json,
  ].join("\n    ");
}
