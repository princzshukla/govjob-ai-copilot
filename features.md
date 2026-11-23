# RozgarBoard — Features

RozgarBoard is a free government-exam discovery and eligibility platform for
Indian recruitment notifications (SSC, UPSC, IBPS, RRB, state boards, PSUs).
It pairs a static React frontend with a FastAPI backend and an automated
notification pipeline.

## User-facing features

### 1. Latest Jobs
- Live feed of government job notifications with official notification PDF
  links and official application deadlines.
- Filters/chips for closing soon, graduate, 12th-pass and 10th-pass jobs.
- Every row links the **official notification**; a separate **Apply** button
  is shown only when a known official application portal URL exists.
- Deadlines and windows are checked against official sources; expired jobs
  drop out of the open-jobs feed automatically.
- SEO-prerendered job detail pages with structured data / FAQ schema.

### 2. Admit Cards
- Admit-card listing with official download links and exam dates.
- Link liveness checks (404/410 links are hidden and the admin is alerted).
- SEO-prerendered admit-card detail pages.

### 3. Eligibility Checker
- Checks a candidate profile against age, qualification, stream, domicile and
  reservation/relaxation rules from the official notifications.
- Rule-by-rule explanations for every verdict, with the source notification
  attached.
- Safety rule: **never publish a confident verdict from unverified fields.**
  If a notification was not confirmed against its official source, the result
  is forced to "Check notification" instead of "you qualify".

### 4. My Roadmap
- AI-generated week-by-week study plan (Groq) tailored to the exam and the
  candidate's profile.
- Results are cached and saved to the signed-in account so they survive
  across devices and refreshes.

### 5. Photo & Signature Resizer
- Client-side tool that resizes and compresses exam photos/signatures to the
  exact limits of specific boards. Files never leave the browser.

### 6. Accounts & sign-in
- Email/password accounts and Google sign-in (custom OIDC with PKCE).
- HttpOnly session cookies, per-user saved profiles and eligibility drafts.

### 7. Privacy
- Public privacy policy page describing data, cookies and account handling.

### 8. Advertising (clearly labelled)
- House-ad placeholders and explicitly labelled sponsored placements; no
  deceptive ads. See `docs/AD-MODEL.md`.

## Backend / pipeline features

- **Layer 1 — Discovery**: polls official portals with conditional GETs
  (ETag/Last-Modified), CSS-scoped content hashing, robots.txt compliance,
  exponential backoff and per-source failure isolation.
- **Layer 2 — Extraction**: downloads official PDFs (magic-byte check, 25 MB
  cap), extracts structured fields with per-field confidence and evidence via
  Groq, with an optional fallback model and a content-hash cache.
- **Publishing gate**: only `auto` rows with complete required fields become
  notifications; anything uncertain is held in a review queue with a
  machine-readable reason — nothing is invented at publish time.
- **Benchmark gate**: a 10-PDF benchmark scores the extractor; wrong or
  missing critical values must be flagged rather than auto-published.
- **Review & discovery admin queues**: official-evidence-only approval flows
  with append-only audit history.
- **Watchdogs**: deadline re-verification against official notices, admit-card
  link liveness, jobs coverage, and new-job discovery.
- **Telegram integration**: admin health alerts and optional user notifications.

## Infrastructure / SEO

- FastAPI backend on Render (Dockerfile + Blueprint, Alembic migrations on
  container start).
- Static Vite/React frontend on Vercel with prerendered HTML for every public
  route, generated sitemap and per-page meta tags.
- Cloudflare in front: DNS/CDN/WAF, Full (strict) TLS, API cache bypass, and
  crawler-friendly bot settings (AI crawlers and managed robots.txt disabled).
- Same-origin `/api/*` rewrite so session cookies stay first-party.

## Retired features

- **Closed Jobs archive** — the closed-jobs tab, route and prerendered page
  were removed. Old `/closed-jobs` links now redirect to the home page; closed
  notifications remain in the database and their detail pages are still
  prerendered for existing links.
