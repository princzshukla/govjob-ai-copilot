# Cloudflare Free Plan — DNS, DDoS, Edge CDN & WAF for RozgarBoard

How to put **Cloudflare's Free plan** in front of `rozgarboard.in` with zero
monthly spend: authoritative DNS, unmetered DDoS protection, a global edge CDN
with data centers in Mumbai / New Delhi / Chennai, free SSL/TLS, and a basic
WAF + one rate-limiting rule.

Researched from Cloudflare/Render/Vercel official docs on **2026-11-21**.
Feature limits on the Free plan change over time — re-check the
[Sources](#sources) if you are reading this much later.

## Applied configuration (2026-11-21)

The steps below were applied to `rozgarboard.in` on the Free plan and verified:

- **DNS**: `A @` → `216.198.79.1` (Vercel apex) and `CNAME www` →
  `cfdd1e6dfcf459f9.vercel-dns-017.com` — both **Proxied**; `_domainconnect`
  and `_dmarc` left **DNS only**. Cloudflare reports "All set".
- **SSL/TLS**: encryption mode **Full (strict)**; **Always Use HTTPS** and
  **Automatic HTTPS Rewrites** on; Universal SSL active.
- **Caching**: Cache Rule `Bypass cache - API` — `URI Path contains /api/` →
  **Bypass cache**. Tiered Cache already Active with Smart topology.
- **WAF**: Cloudflare Managed Ruleset enabled; custom rule `Block scanner paths`
  (`.env`, `wp-login.php`, `phpmyadmin`, `xmlrpc.php`) → **Block**; the single
  free rate-limit rule `Auth brute-force cap` — `URI Path contains
  /api/v1/auth/`, IP, 10 requests / 10 s → **Block** for 10 s.
- **Live verification**: site returns 200 via Cloudflare; `/api/v1/auth/me`
  returns 401 with `cf-cache-status: DYNAMIC` (through the Vercel → Render
  rewrite); a hashed `/assets/*` file returns `HIT`/`REVALIDATED`; `/.env`
  returns 403 from Cloudflare.

---

## 1. What the Free plan actually gives you

| Capability | What you get on Free | Relevant limit | Used here for |
|---|---|---|---|
| **DNS** | Anycast authoritative DNS, CNAME flattening, `Auto` TTL (300 s) on proxied records | — | `rozgarboard.in` apex + `www` |
| **DDoS** | Network-wide, always-on L3/4 + L7 mitigation | Unmetered (no attack-sized bill) | Protecting the site automatically — no toggle to enable |
| **Edge CDN** | Static-content caching at 300+ cities; **Mumbai, New Delhi, Chennai** (plus Bengaluru, Hyderabad, Kolkata, Pune, Ahmedabad, Kochi, …) | Cache Rules: **10 rules**; Tiered Cache + Smart Topology available | Vite's hashed `/assets/*` served from the nearest Indian PoP |
| **Bandwidth** | No bandwidth cap on the Free plan ("no limit on the amount of bandwidth your visitors use") | Subject to Cloudflare ToS (no abuse / CDN-as-storage) | Serving the SPA and API responses |
| **SSL/TLS** | Universal SSL (free edge certificate, apex + first-level subdomains), HTTPS rewrites, HSTS | — | HTTPS for `rozgarboard.in` and `www` |
| **WAF** | Cloudflare **Free Managed Ruleset**, **5 custom rules**, 3 response custom rules, IP access rules, hotlink protection, email obfuscation | Managed Rules = *Free Managed Ruleset only*; no regex in custom rules | Blocking scanner noise, protecting the app |
| **Rate limiting** | **1 rate limiting rule** | Counting characteristic **IP only**; counting period **10 s**; mitigation timeout **10 s**; expression fields **Path** and **Verified Bot** only | Blunt-force protection on `/api/v1/auth/login` and `/register` |
| **Observability** | Security Events (**sampled logs only**), zone Security Analytics | No alerting, no payload logging | Incident triage, not a full audit log |

> **Important expectation setting:** "unlimited bandwidth" means no *bandwidth
> charge or cap*, not unlimited compute. Free also enforces proxy connection /
> request-size limits and a 100 s-ish origin timeout (524 if exceeded). The
> app's existing 25 MB upload cap and 25 s client timeout sit comfortably inside
> these.

---

## 2. Target architecture for this repository

```
   User (India)
        │  HTTPS
        ▼
  Cloudflare edge  ── Mumbai / New Delhi / Chennai PoP
   • Anycast DNS (orange-clouded records)
   • Universal SSL, Full (strict) to origin
   • DDoS mitigation (automatic)
   • WAF: Free Managed Ruleset + 5 custom rules + 1 rate limit rule
   • CDN: cache static assets; BYPASS cache for /api/*
        │  (proxied HTTPS)
        ▼
  Vercel  ── RozgarBoard SPA (frontend/)
   • serves / and /assets/*
   • rewrites /api/* → Render  (already in frontend/vercel.json)
        │  server-side rewrite (not visible to the browser)
        ▼
  Render  ── backend API (render.yaml, govjob-ai-copilot)
```

**Key consequence of the existing rewrite:** `frontend/vercel.json` maps
`/api/:path*` to `https://govjob-ai-copilot.onrender.com/api/:path*`, and
`frontend/src/lib/api.ts` defaults `API_BASE` to `/api/v1`. So the browser
calls **same-origin** `https://rozgarboard.in/api/v1/...`. The HttpOnly session
cookie stays first-party, and **no CORS changes and no `api.` subdomain are
needed**. Do not add one unless you deliberately want cross-origin cookies
(which would require `SameSite=None`, `Secure`, and widening `CORS_ORIGINS`).

---

## 3. Setup steps

### Step 1 — Add the site to Cloudflare

1. Sign up / log in at <https://dash.cloudflare.com> → **Add a site** → `rozgarboard.in`.
2. Pick the **Free** plan.
3. Cloudflare scans existing DNS records. Review them — keep `MX`, `TXT`, DKIM/SPF,
   and any verification records exactly as they are.
4. Change the **nameservers at your registrar** to the two Cloudflare assigns
   (e.g. `xxx.ns.cloudflare.com` / `yyy.ns.cloudflare.com`). Activation can take
   up to 24 h; Cloudflare emails you when active.
   - If you bought the domain elsewhere and don't want to move nameservers, you
     can use **CNAME setup** for a subdomain only — but for apex + CDN + WAF you
     want full (nameserver) setup.

### Step 2 — DNS records (`DNS → Records`)

Use the **exact values Vercel shows in Project → Domains**; the hashes below are
placeholders.

| Type | Name | Target | Proxy | Purpose |
|---|---|---|---|---|
| `A` | `@` | Vercel apex value (e.g. `76.76.21.21` — confirm in Vercel) | **Proxied** (orange) | `https://rozgarboard.in` |
| `CNAME` | `www` | Vercel's project CNAME (e.g. `<hash>.vercel-dns-017.com`) | **Proxied** (orange) | `https://www.rozgarboard.in` |
| `MX`, `TXT`, CAA | as-is | as-is | **DNS only** (grey) | Email + domain verification — never proxy these |

Notes:

- Only `A`, `AAAA` and `CNAME` records can be proxied. A DNS-only web record
  exposes your origin IP (no DDoS protection, no CDN, no WAF).
- Proxied records are flattened by Cloudflare; `Auto` TTL is fixed at 300 s.
- Add both hostnames in **Vercel → Project → Domains** first, then add the
  matching records here. Vercel issues the certificate once DNS points at it.
- Don't add `AAAA` records unless Vercel explicitly gives you one, and don't
  invent an `api.rozgarboard.in` CNAME (see §2).
- Redirection `www → apex` (or the reverse) can be done with a Cloudflare
  **Redirect Rule** (free) or in Vercel — pick one place only, to avoid loops.

### Step 3 — SSL/TLS (`SSL/TLS → Overview`)

- Set encryption mode to **Full (strict)**. Cloudflare strongly recommends
  Full / Full (strict); Vercel and Render both terminate TLS with valid public
  certificates, so strict validation works.
  - Render's own Cloudflare guide says **Full** — if you ever see **526 (invalid
    SSL certificate)** on API calls, switch from Full (strict) to Full.
  - **Never use Flexible**: Vercel forces HTTPS, so Flexible produces an
    infinite redirect loop.
- Leave **Universal SSL** enabled (free certificate). Wait for status *Active*.
- Turn on **Always Use HTTPS** and **Automatic HTTPS Rewrites**.
- Add HSTS only after you are confident every subdomain is HTTPS-correct:
  `SSL/TLS → HSTS → Enable` (start with a short `max-age`, e.g. 1 hour).

### Step 4 — DDoS protection

Nothing to configure — this is the part that is genuinely automatic. Cloudflare
absorbs volumetric attacks at the edge *before* traffic reaches Vercel/Render,
with no bill for the attack traffic. The only action item: **keep the web
records orange-clouded** (§2). A grey-clouded record bypasses it entirely.

### Step 5 — Edge CDN / caching (`Caching → Cache Rules`)

Default behaviour is already safe: Cloudflare honours origin `Cache-Control`,
so Vite's fingerprinted `/assets/*` (long `immutable` TTL) are cached at the
edge in Mumbai / Delhi / Chennai, while HTML and API responses are not.

Add two Cache Rules (10 available on Free; both require proxied records):

1. **Never cache the API** (most important)
   - Name: `Bypass cache — API`
   - Expression: `(http.request.uri.path contains "/api/")`
   - Then: **Cache eligibility → Bypass cache**
   - Reason: an auth/profile response must never be served from an edge cache
     to another user. This also protects the `/api/*` rewrite path.
2. **Pin static assets to the edge** (optional; default caching usually suffices)
   - Expression: `(http.request.uri.path contains "/assets/")`
   - Cache eligibility: **Eligible for cache**; Edge TTL: **Respect origin**
   - Browser TTL: **Respect origin**

Also enable **Caching → Tiered Cache → Smart Topology** (available on Free). It
improves hit ratio and reduces origin fetches; you do not need paid Argo.

Purge after a deploy if you ever override TTLs: `Caching → Purge → Purge
Everything` (or by prefix `/assets`).

### Step 6 — WAF and the one free rate-limit rule

`Security → WAF`. On Free you get the **Free Managed Ruleset**, **5 custom
rules**, and **1 rate-limiting rule**.

**6a. Managed Ruleset** — enable it. It gives zero-day/OWASP-style protection
out of the box. Keep action defaults; watch *Security Events* (sampled on Free)
for false positives.

**6b. Custom rules** (no regex on Free — use `contains` / `eq`):

- Block common scanner paths:
  - Expression:
    `(http.request.uri.path contains "/.env") or (http.request.uri.path contains "/wp-login.php") or (http.request.uri.path contains "/phpmyadmin") or (http.request.uri.path contains "/xmlrpc.php")`
  - Action: **Block**
- Let the Telegram webhook through unchallenged (if you enable any challenge /
  bot rule):
  - Expression: `(http.request.uri.path eq "/api/v1/notifications/telegram/webhook")`
  - Action: **Skip** → select the Cloudflare security components to skip.
  - The app still validates the `X-Telegram-Bot-Api-Secret-Token` header in
    `backend/app/api/v1/endpoints/notifications.py`, so skipping Cloudflare
    challenges does not remove authentication.

**6c. Rate limiting rule** — Free allows exactly one rule (IP-based, 10 s
counting period, 10 s mitigation timeout):

- Name: `Auth brute-force cap`
- Expression (only `Path` and `Verified Bot` fields are available on Free):
  `(http.request.uri.path eq "/api/v1/auth/login") or (http.request.uri.path eq "/api/v1/auth/register")`
- Characteristics: **IP**; Period: **10 seconds**; Requests per period: **10**
- Action: **Block**; Duration: **10 seconds**

This is a coarse edge layer on top of the existing SlowAPI limits in the
backend (`5/minute` on login/register, `backend/app/api/v1/endpoints/auth.py`).
Keep `RATE_LIMIT_STORAGE_URL` pointing at shared Redis in production
(`render.yaml`) so the backend limit is consistent across instances.

> Rate counters are per-data-center and can lag by a few seconds; some excess
> requests may still reach the origin. Treat this as abuse dampening, not a
> precise quota. Verify-bot rules can affect SEO — don't rate-limit crawlers.

### Step 7 — Verify

```bash
# 1. DNS resolves to Cloudflare anycast, not Vercel directly
dig +short rozgarboard.in
dig +short www.rozgarboard.in

# 2. HTTPS + Cloudflare headers
curl -sSI https://rozgarboard.in | grep -iE 'HTTP/|server:|cf-ray|cf-cache-status|strict-transport-security'
# expect: HTTP/2 200, server: cloudflare, cf-ray: <hex>-<IATA> (e.g. -BOM/-DEL/-MAA)

# 3. A static asset is cached at the edge
curl -sSI https://rozgarboard.in/assets/<hashed-file>.js | grep -i cf-cache-status
# expect: HIT (after the first request)

# 4. The API must NOT be cached and must still work through the Vercel rewrite
curl -sSI https://rozgarboard.in/api/v1/auth/me | grep -iE 'HTTP/|cf-cache-status'
# expect: 401 when logged out, and NO cf-cache-status: HIT
```

In the Cloudflare dashboard check: **Analytics → Traffic** (edge traffic
served), **Caching → Analytics** (hit ratio), **Security → Events** (blocked
requests), and **SSL/TLS → certificates** (Universal SSL active).

---

## 4. Project-specific gotchas

- **Don't duplicate the API at `api.rozgarboard.in`.** The Vercel rewrite already
  makes API calls same-origin. Adding a second host would require CORS +
  `SameSite=None` changes and breaks first-party cookies (the reason
  `frontend/vercel.json` exists — see commit `1755461`).
- **`CORS_ORIGINS`** in `backend/app/core/config.py` still defaults to the Vercel
  preview URL. With the same-origin rewrite you don't *need* to add
  `https://rozgarboard.in`, but adding both apex and `www` is harmless and
  simplifies direct API testing:
  `CORS_ORIGINS=https://rozgarboard.in,https://www.rozgarboard.in` in Render.
- **Health check:** Render checks `/health` directly on the service, which is
  unaffected. From the public domain, `/health` would hit Vercel (404) because
  the rewrite only covers `/api/*`. Use `/api/v1/auth/me` (401 expected) for an
  end-to-end check, or add a Vercel rewrite `/health → <render>/health` if you
  want a public probe.
- **Outbound government-site polling** (`layer1_poller`, `layer2_worker`) runs
  *inside the Render backend* and is not affected by Cloudflare's WAF. Leave its
  ETag/robots.txt/backoff behaviour alone.
- **If you later point a hostname directly at Render** (not via Vercel),
  Render's Cloudflare guide says: set SSL mode **Full**, remove all `AAAA`
  records, add the CNAME to `<service>.onrender.com` with proxy **DNS only**
  first, verify the certificate in Render, then optionally switch to Proxied.
- **Rollback:** flip any record to **DNS only (grey cloud)** to bypass Cloudflare
  entirely while debugging. SSL mode changes and Cache Rules can be reverted
  independently in the dashboard. Keep the Registrar nameservers handy.

---

## Sources (official, retrieved 2026-11-21)

- Free plan overview & "no bandwidth limit": <https://www.cloudflare.com/plans/free/>
- Global network / India data centers (Mumbai, New Delhi, Chennai, …): <https://www.cloudflare.com/network/>
- WAF availability (Free Managed Ruleset, 5 custom rules, 1 rate-limit rule, sampled events): <https://developers.cloudflare.com/waf/>, <https://developers.cloudflare.com/waf/custom-rules/>, <https://developers.cloudflare.com/waf/rate-limiting-rules/>
- SSL/TLS encryption modes (Full / Full strict; avoid Flexible): <https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/>, <https://developers.cloudflare.com/ssl/>
- Cache Rules (10 on Free) and Tiered Cache (Free + Smart Topology): <https://developers.cloudflare.com/cache/how-to/cache-rules/>, <https://developers.cloudflare.com/cache/how-to/tiered-cache/>
- Proxied records, CNAME flattening, 524 timeouts: <https://developers.cloudflare.com/dns/manage-dns-records/reference/proxied-dns-records/>
- Render + Cloudflare DNS procedure: <https://render.com/docs/configure-cloudflare-dns>, <https://render.com/docs/custom-domains>
- Vercel custom-domain DNS records: <https://vercel.com/docs/domains/working-with-domains/add-a-domain>
