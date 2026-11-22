/** Generate sitemap.xml from the manifest written by prerender.mjs. */
import { readFile, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)));
const DIST = join(ROOT, "dist");

const { site, routes } = JSON.parse(await readFile(join(DIST, ".routes.json"), "utf8"));
const base = site.replace(/\/$/, "");

const escapeXml = (value) =>
  String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const entries = routes
  .filter((route) => !route.noindex && route.path !== "/404")
  .map((route) => {
    const loc = base + (route.path === "/" ? "/" : route.path);
    return [
      "  <url>",
      `    <loc>${escapeXml(loc)}</loc>`,
      `    <lastmod>${escapeXml(route.lastmod)}</lastmod>`,
      "  </url>",
    ].join("\n");
  });

const xml = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
  ...entries,
  "</urlset>",
  "",
].join("\n");

await writeFile(join(DIST, "sitemap.xml"), xml, "utf8");
console.log(`sitemap.xml written with ${entries.length} URLs`);
