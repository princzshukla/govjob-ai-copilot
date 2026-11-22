// Minimal production static server for the built Vite SPA.
// No dependencies — uses only Node built-ins. Run `npm run build` first.
import { createServer } from "node:http";
import { createReadStream, existsSync, statSync } from "node:fs";
import { extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(fileURLToPath(new URL(".", import.meta.url)), "dist");
const PORT = Number(process.env.PORT || 3000);
const HOST = process.env.HOST || "0.0.0.0";

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".webmanifest": "application/manifest+json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
  ".txt": "text/plain; charset=utf-8",
};

function send(res, status, message, extra = {}) {
  res.writeHead(status, {
    "Content-Type": "text/plain; charset=utf-8",
    "X-Content-Type-Options": "nosniff",
    ...extra,
  });
  res.end(message);
}

const server = createServer((req, res) => {
  if (req.method !== "GET" && req.method !== "HEAD") {
    return send(res, 405, "Method not allowed", { Allow: "GET, HEAD" });
  }

  let pathname;
  try {
    pathname = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
  } catch {
    return send(res, 400, "Bad request");
  }

  // Resolve inside ROOT only, then fall back to index.html for SPA routes.
  const filePath = resolve(ROOT, pathname.replace(/^\/+/, ""));
  if (filePath !== ROOT && !filePath.startsWith(ROOT + sep)) {
    return send(res, 403, "Forbidden");
  }

  let target = filePath;
  let status = 200;
  if (!existsSync(target) || !statSync(target).isFile()) {
    const asDirectory = join(filePath, "index.html");
    if (existsSync(asDirectory) && statSync(asDirectory).isFile()) {
      target = asDirectory;
    } else if (existsSync(join(ROOT, "404.html"))) {
      target = join(ROOT, "404.html");
      status = 404;
    } else {
      target = join(ROOT, "index.html");
    }
  }
  if (!existsSync(target)) {
    return send(res, 500, "Build the frontend first: npm run build");
  }

  const ext = extname(target).toLowerCase();
  res.writeHead(status, {
    "Content-Type": MIME[ext] || "application/octet-stream",
    "Cache-Control": ext === ".html" ? "no-cache" : "public, max-age=31536000, immutable",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
  });
  if (req.method === "HEAD") return res.end();
  createReadStream(target).pipe(res);
});

server.listen(PORT, HOST, () => {
  console.log(`RozgarBoard frontend listening on http://${HOST}:${PORT}`);
});
