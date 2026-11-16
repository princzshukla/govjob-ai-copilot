# GovJob Matcher & AI Study Copilot

Government-exam discovery pipeline and eligibility engine for Indian
recruitment notifications (SSC, UPSC, IBPS, PSU & state boards). Paste a
resume or fill a profile → see every job you're eligible for, why, and the
official PDF that proves it.

## Architecture (pipeline)

```
                    Layer 1 — Discovery                     Layer 2 — Extraction          Layer 3 — Matching
 ┌──────────────────────────────────────────────┐
 │  Government portals (SSC JSON API, UPSC,     │
 │  SSCR, uppsc, BHEL …)  +  local fixture      │
 │           │                                  │
 │           ▼  poll (tiered, ETag/Last-Mod)    │
 │  layer1_poller ──► scrape_logs (audit trail) │
 │           │  css-scoped sha256 of notice     │
 │           │  list → changed? else skip       │
 │           ▼                                  ▼
 │  raw_discovered_links ──► notification_      │
 │  (dedup: source+url unique,                  │
 │   dedup_key = ad no. for                      │
  │   cross-source) ──────────► extraction_results│
 │      │   │                   (per-field       │
 │      │   │                    confidence +      │
 │      │   │                    evidence,         │
 │      │   │                    status: auto /    │
 │      │   │                    review / rejected)│
 │      │   └────────► exam_notifications        │
 │      │              (official_pdf_url kept for  │
 │      │               provenance; apply_url =    │
 │      │               official apply portal)      │
 └───────┼───────────────────────────────┼────────┘
         ▼                               ▼
  candidate profiles              eligibility engine
  (resume upload +                (matcher.py)
   manual completion)             age/degree/stream/
                                 sharing + relaxation
                                 → verdict + rule-by-rule
                                 explanations + source PDF
```

**Design rules**

* **Never show a wrong eligibility result.** Low confidence, missing critical
  fields, scanned/image-only PDFs or ambiguous documents are flagged
  `review` — the UI shows "Check notification" with the official PDF, not a
  confident verdict. Every result row links the official notification, plus a distinct Apply button only when a known official application portal URL is on file (`apply_url`) — the PDF and the apply link are never conflated.
* **Good citizen to government servers.** Conditional GETs (ETag/
  Last-Modified → 304), css-scoped content hashing so counters/clocks/
  session tokens don't flap the hash, robots.txt honoured (source gets
  disabled + admin alerted), exponential backoff and per-source failure
  isolation, tiered poll frequencies.
* **Measure, don't trust the LLM.** A 10-PDF benchmark gate scores the
  extractor against sources' real advertisements.

## Benchmark — LLM PDF→JSON extraction (`scripts/benchmark_notification_extraction.py`)

Model: `openai/gpt-oss-120b` (Groq). 10 real, already-published notification
PDFs (IBPS, UPSC, BHEL ×7, bilingual Hindi BHEL ad) graded field-by-field on
vacancies, ages (+per-category relaxation), cutoff/last dates, qualification,
pay:

| PDF | Result (2026-11-15) |
|---|---|
| ibps-po-xvi (54pp, full ad) | ages 20/30, cutoff, last date, qualification, pay ✓; `total_vacancies` not extracted → `review` (not publishable) |
| upsc-advt-13-2026 (multi-post) | vacancies 13 ✓, ages 35 ✓, degree ✓, 7th CPC ✓; `age_cutoff_date` not extracted → `review` |
| bhel-artisan-detailed-ad | ages 27 ✓, dates ✓, relaxations ✓, ITI ✓; `total_vacancies` not extracted → `review` |
| bhel-et-detailed-ad | Groq `json_validate_failed` 400 (primary + fallback) → `LLM unavailable` → `review` |
| bhel-ptmc-kolkata | age 65 ✓, dates ✓, MBBS ✓; `total_vacancies` not extracted → `review` |
| bhel-ptmc-corp-oct2026 | **PASS** (2 vacancies, 65, dates ✓) |
| bhel-ptmc-ivp-goindwal | **PASS** |
| bhel-atc-jhansi (retired-workmen ad) | full extraction except `age_cutoff_date` → `review` |
| bhel-fta-pssr-chennai (bilingual) | age/dates ✓, pay ✓; vacancies+qualification → `review` |
| bhel-fta-cfp-rudrapur-hindi (Hindi doc) | age/date/pay ✓; vacancies+qualification → `review` |

**Score (2026-11-15 re-run — see addendum in `benchmarks/notification_extraction_report.md`): 2 PASS / 8 FLAGGED / 0 FAIL — every wrong-answer outcome was blocked
into `review`; zero hallucinated dates/ages were auto-publishable.**
Scanned image-only PDFs short-circuit to `is_scanned=True` + `review`
(never sent to the LLM). Gate: ≥ 9/10 "safe" (PASS or review-flagged);
held on both completed runs (2026-11-13: 3 PASS / 7 FLAGGED / 0 FAIL;
2026-11-15: 2 PASS / 8 FLAGGED / 0 FAIL, 10/10 safe).
On the re-run, `bhel-et-detailed-ad` never reached the LLM: Groq rejects the
model's output with `json_validate_failed` (400) on both the primary and the
fallback key — quota was healthy, so that PDF stays in `review` unscoreable
rather than ever publishable. `total_vacancies` also regressed to null on
`ibps-po-xvi`, `bhel-artisan-detailed-ad` and `bhel-ptmc-kolkata` — all
flagged `review`. Full per-field detail and both runs' history: see
`benchmarks/notification_extraction_report.md`.

## Local development

```bash
# backend (Python 3.13; uses backend/venv)
cd backend && pip install -r requirements.txt
# disposable test DB (one command; wiped every run)
docker compose -f ../docker-compose.test.yml up -d
TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/govjobs_test" python -m pytest -q
# golden eligibility cases (51+ cases, no DB needed)
python -m pytest tests/eligibility -q

# frontend — RozgarBoard SPA (static, no SSR)
cd frontend && npm install
npm run dev       # http://localhost:5173
npm test          # vitest (lib unit tests)
npm run build     # tsc -b + vite build
```

# scrape smoke-test against the local fixture (Test B harness)
cd backend/scripts/fixtures && python -m http.server 8001 &
cd backend && python -m app.services.scrape_source_seed
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/govjobs_migcheck" \
  alembic upgrade head && \
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/govjobs_migcheck" \
  python -m app.services.layer1_poller --once
```

CI (`.github/workflows/ci.yml`): Postgres service → `alembic upgrade head`
from scratch → full pytest (incl. Layer 1 + extractor + e2e suites) → plus a
dedicated `pipeline` job, and a frontend typecheck + test + build job.

## Frontend (RozgarBoard SPA)

Since the frontend rewrite, `frontend/` is a plain Vite + React 19 SPA with no
SSR (6 runtime dependencies; no router/query/state frameworks). Views are
top-level tabs (Latest Jobs / My Eligibility / My Roadmap); auth and account
flows are modals. Both the feed and the eligibility verdicts come from the live
backend; the vacancy/salary fields seen in the prototype were never stored on
`exam_notifications` and are not shown. Ads slots stay clearly labelled house
placeholders (see `docs/AD-MODEL.md`).

## Pipeline status

Layer 1 (discovery) and the Layer 2 extractor are implemented, tested and
benchmarked (twice — see above). `app/services/exam_publisher.py` promotes
`extraction_results` rows with `status='auto'` into `exam_notifications`
with official-PDF provenance (`official_pdf_url`, `source_url`,
`last_checked_at`) and — when the notification explicitly prints one — an
`apply_url` pointing at the official online application portal (never
guessed; absent otherwise), wiring `exam_notification_id` forward and marking the
discovered link `processed`. Nothing is invented at publish time — a row
missing any required value (e.g. `min_age`, `application_deadline`) is
*held*: flipped to `review` with an explicit machine-readable
`review_note`, never published. Qualification wording is mapped onto known
degrees/streams (`Any Graduate` fallback); unmappable wording is held too.
`app/services/layer2_worker.py` drains `raw_discovered_links` end to end:
download (magic-byte check, 25 MB cap) → extract (content-hash cache) →
`auto` rows get promoted into `exam_notifications`, `review` rows wait in
the review queue. It stops cleanly at `WORKER_DAILY_TOKEN_BUDGET` (default
40000 estimated tokens/day, env-tunable) and skips links that fail 3 times.
`python -m app.services.layer2_worker [--dry-run] [--source upsc-whats-new,ssc-notice-board] [--max-docs N]`.

Run it with `python -m app.services.exam_publisher [--dry-run]`. Known
limits: per-exam `age_relaxations` have no `exam_notifications` column yet
(they stay in `extraction_results.extracted`), and one exam row is created
per extraction (cross-source ad-number dedup is a follow-up).

Key environment variables: `DATABASE_URL`, `GROQ_API_KEY`/`GROQ_MODEL`,
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID` (health alerts),
`LLM_FALLBACK_*` (optional OpenAI-compatible fallback LLM — escalated once
per document when the primary model yields missing/low-confidence fields;
can also point at a second Groq key's OpenAI-compatible endpoint as TPD
overflow). Never commit `.env`; CI uses `test-key-not-used`.
