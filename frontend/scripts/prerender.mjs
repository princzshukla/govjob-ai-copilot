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

const ROUTES = [
  { path: "/", file: "index.html" },
  { path: "/admit-cards", file: "admit-cards/index.html" },
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
const { render, metaFor, headHtml, schemasFor, siteSchemas, serialisePrerenderData } = ssr;

const template = await readFile(join(DIST, "index.html"), "utf8");
const manifest = [];

for (const route of ROUTES) {
  const pageData = { ...data, path: route.path };
  const { html } = render(route.path, pageData);
  const meta = metaFor(route.path);
  const schemas = [...siteSchemas(), ...schemasFor(route.path, meta)];
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

  const dates = data.exams
    .map((e) => e.verified_on || e.last_checked_at || e.notification_date)
    .filter(Boolean)
    .sort();
  manifest.push({
    path: route.path,
    lastmod: dates.length ? dates[dates.length - 1] : new Date().toISOString().slice(0, 10),
    noindex: /noindex/i.test(meta.robots),
  });

  console.log(`prerendered ${route.path} -> ${route.file} (${out.length} bytes)`);
}

await writeFile(join(DIST, ".routes.json"), JSON.stringify({ site: SITE, routes: manifest }, null, 2));
console.log(`prerendered ${ROUTES.length} routes`);
