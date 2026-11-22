/**
 * Build-time renderer for the static site.
 *
 * Reads the Vite client build (dist/index.html) as a template, renders each
 * public route with react-dom/server, injects per-page <head> and hydration
 * data, and writes one HTML file per route.
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)));
const DIST = join(ROOT, "dist");
const SSR_ENTRY = join(ROOT, "dist-ssr", "entry-server.js");
// CI and Vercel previews have no backend on localhost. Default to the public
// production API so the build works with zero configuration; local setups can
// still override it with API_BASE_URL.
const API = process.env.API_BASE_URL || "https://govjob-ai-copilot.onrender.com/api/v1";
const SITE = process.env.SITE_URL || "https://www.rozgarboard.in";

const STATIC_ROUTES = [
  { path: "/", file: "index.html" },
  { path: "/admit-cards", file: "admit-cards/index.html" },
  { path: "/closed-jobs", file: "closed-jobs/index.html" },
  { path: "/eligibility", file: "eligibility/index.html" },
  { path: "/roadmap", file: "roadmap/index.html" },
  { path: "/tools/photo-signature-resizer", file: "tools/photo-signature-resizer/index.html" },
  { path: "/privacy", file: "privacy/index.html" },
  { path: "/404", file: "404.html" },
];

async function getJson(path) {
  let lastError;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const res = await fetch(API + path, {
        headers: { "User-Agent": "RozgarBoard-Build/1.0" },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status} for ${API + path}`);
      return await res.json();
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError;
}

const [examsRes, cardsRes] = await Promise.all([
  getJson("/eligibility/exams?status=all"),
  getJson("/admit-cards"),
]);

const data = {
  exams: examsRes.exams ?? [],
  admitCards: cardsRes.admit_cards ?? [],
};

const ssr = await import(pathToFileURL(SSR_ENTRY).href);
const {
  render,
  metaFor,
  headHtml,
  schemasFor,
  siteSchemas,
  faqSchema,
  breadcrumbSchema,
  webPageSchema,
  serialisePrerenderData,
  slugFor,
  jobFaqs,
  toolFaqs,
} = ssr;

const detailRoutes = [];

for (const exam of data.exams) {
  const key = slugFor(exam.title, exam.id);
  detailRoutes.push({
    path: `/jobs/${key}`,
    file: `jobs/${key}/index.html`,
    kind: "exam",
    record: exam,
    title: `${exam.title} — Eligibility, Dates & Official PDF | RozgarBoard`,
    description: `Check eligibility, age limit, dates and the official notification for ${exam.title}.`,
    faqs: jobFaqs(exam),
    lastmod: exam.verified_on || exam.last_checked_at || exam.notification_date,
  });
}

for (const card of data.admitCards) {
  const key = slugFor(card.title, card.id);
  detailRoutes.push({
    path: `/admit-cards/${key}`,
    file: `admit-cards/${key}/index.html`,
    kind: "card",
    record: card,
    title: `${card.title} — Admit Card Link & Exam Date | RozgarBoard`,
    description: `Official admit card link and exam date for ${card.title}.`,
    faqs: [],
    lastmod: card.last_checked_at || card.notification_date,
  });
}

const routes = [...STATIC_ROUTES, ...detailRoutes];
const template = await readFile(join(DIST, "index.html"), "utf8");
const manifest = [];
const today = new Date().toISOString().slice(0, 10);

for (const route of routes) {
  // Detail pages only need their own record plus a few related links. Shipping
  // the whole feed into every one of them would bloat the static output.
  let pageData;
  if (route.kind === "exam") {
    pageData = {
      path: route.path,
      exam: route.record,
      exams: data.exams
        .filter((e) => e.id !== route.record.id && e.organizing_body === route.record.organizing_body)
        .slice(0, 5),
    };
  } else if (route.kind === "card") {
    pageData = {
      path: route.path,
      admitCard: route.record,
      admitCards: data.admitCards.filter((c) => c.id !== route.record.id).slice(0, 5),
    };
  } else {
    pageData = { ...data, path: route.path };
  }
  const { html } = render(route.path, pageData);

  const meta = metaFor(route.path, route.kind ? {
    title: route.title,
    description: route.description,
    canonical: SITE + route.path,
  } : undefined);

  const schemas = [...siteSchemas(), webPageSchema(meta)];
  if (route.path !== "/") {
    schemas.push(breadcrumbSchema(route.path, meta.title.split(" | ")[0]));
  }
  const asTuples = (items) => items.map((item) => [item.question, item.answer]);
  if (route.faqs?.length) schemas.push(faqSchema(asTuples(route.faqs)));
  if (route.path === "/tools/photo-signature-resizer") schemas.push(faqSchema(asTuples(toolFaqs())));
  if (!route.kind) {
    // static routes keep the baseline schema set
    schemas.length = 0;
    schemas.push(...siteSchemas(), ...schemasFor(route.path, meta));
    if (route.path === "/tools/photo-signature-resizer") schemas.push(faqSchema(asTuples(toolFaqs())));
  }

  const head = headHtml(meta, schemas);
  let out = template
    .replace(/<title>[\s\S]*?<\/title>/i, "")
    .replace(/<meta\s+name="description"[^>]*\/?>/i, "")
    .replace("</head>", `    ${head}\n  </head>`)
    .replace('<div id="root"></div>', `<div id="root">${html}</div>`)
    .replace(
      "</body>",
      `<script>window.__DATA__=${serialisePrerenderData(pageData)}</script>\n  </body>`,
    );

  const target = join(DIST, route.file);
  await mkdir(dirname(target), { recursive: true });
  await writeFile(target, out, "utf8");

  manifest.push({
    path: route.path,
    lastmod: route.lastmod || today,
    noindex: /noindex/i.test(meta.robots),
  });
}

await writeFile(join(DIST, ".routes.json"), JSON.stringify({ site: SITE, routes: manifest }, null, 2));
console.log(`prerendered ${routes.length} routes (${detailRoutes.length} detail pages)`);
