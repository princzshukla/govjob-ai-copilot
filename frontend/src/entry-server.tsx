import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router-dom";
import { AppContent } from "./App";
import { AuthProvider } from "./lib/auth";
import type { PrerenderData } from "./lib/prerender-data";

export { metaFor, headHtml, SITE_URL } from "./seo/meta";
export { schemasFor, siteSchemas, faqSchema, breadcrumbSchema, webPageSchema } from "./seo/schema";
export { serialisePrerenderData } from "./lib/prerender-data";
export { slugFor } from "./lib/slug";
export { jobFaqs } from "./seo/faq";
export { toolFaqs } from "./lib/specs";

/** Render a URL to HTML at build time. Effects never run here. */
export function render(url: string, data: PrerenderData): { html: string } {
  (globalThis as { __SSR_DATA__?: PrerenderData }).__SSR_DATA__ = data;

  const html = renderToString(
    <AuthProvider>
      <StaticRouter location={url}>
        <AppContent />
      </StaticRouter>
    </AuthProvider>,
  );

  return { html };
}
