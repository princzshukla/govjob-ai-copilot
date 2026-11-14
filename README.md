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
 │      │               every result — provenance) │
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
  confident verdict. Every result row links the official notification.
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

| PDF | Result |
|---|---|
| ibps-po-xvi (54pp, full ad) | extracted 20/30/01.07/2026-07-21/pay/relaxations; vacancies+qualification flagged `review` (not publishable) |
| upsc-advt-13-2026 (multi-post) | vacancy total 13 ✓, ages 35 ✓; flagged `review` |
| bhel-artisan-detailed-ad | ages 27 ✓, dates ✓, relaxations ✓, ITI ✓ |
| bhel-et-detailed-ad | **PASS** (all fields correct; `age_max_general` 27\|29 any-of) |
| bhel-ptmc-kolkata / corp-oct2026 | age 65 ✓, correct flag for ambiguous vacancy wording / PASS |
| bhel-ptmc-ivp-goindwal | **PASS** |
| bhel-atc-jhansi (retired-workmen ad) | full extraction except `age_cutoff_date` → `review` |
| bhel-fta-pssr-chennai (bilingual) | age/cutoff/dates ✓, vacancies+qualification → `review` |
| bhel-fta-cfp-rudrapur-hindi (Hindi doc) | age/date/pay ✓ (LLM 429 on quota that day) |

**Score: 3 PASS / 7 FLAGGED / 0 FAIL — every wrong-answer outcome was blocked
into `review`; zero hallucinated dates/ages were auto-publishable.**
Scanned image-only PDFs short-circuit to `is_scanned=True` + `review`
(never sent to the LLM). Gate: ≥ 9/10 "safe" (PASS or review-flagged);
held on the completed run (2026-11-13). A re-run after compression fixes was
blocked by the free-tier TPD ceiling (198k/200k) — see
`benchmarks/notification_extraction_report.md` for the honest numbers and
the addendum.

## Local development

```bash
# backend (Python 3.13)
cd backend && pip install -r requirements.txt
# disposable test DB (one command; wiped every run)
docker compose -f ../docker-compose.test.yml up -d
TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/govjobs_test" python -m pytest -q
# golden eligibility cases (51+ cases, no DB needed)
python -m pytest tests/eligibility -q

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
dedicated `pipeline` job, and a frontend typecheck/lint/test job.

## Pipeline status

Layer 1 (discovery) and the Layer 2 extractor are implemented, tested and
benchmarked. Layer 3 (publish extracted notifications into
`exam_notifications`) is the next milestone; extractor outputs persist to
`extraction_results` with per-field confidence and evidence snippets and a
`review` gate, so nothing untrusted reaches users as a verdict.

Key environment variables: `DATABASE_URL`, `GROQ_API_KEY`/`GROQ_MODEL`,
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID` (health alerts),
`LLM_FALLBACK_*` (optional OpenAI-compatible fallback LLM — escalated once
per document when the primary model yields missing/low-confidence fields).
Never commit `.env`; CI uses `test-key-not-used`.
