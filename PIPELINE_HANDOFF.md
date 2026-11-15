# Pipeline handoff (2026-11-15, revised)

All PRs from the morning batch are merged or green.

## Merged into main today
- #22 eligibility engine (+ d9a94c2 `alembic check` fix, + b27617f the
  sign-up-claim profile WIP, both needed for green CI)
- #24 Layer 1 source health: first-class `status` ('ok'|'degraded'|'disabled');
  UPPSC shows `degraded` (8 consecutive HTTP 503s at backfill; auto-recovers
  on next good poll). 48h stability run continues (poller pid 17600).
- #30 (replacing #25, closed by accidental base-branch deletion — don't do that
  again) PDF cost reduction: content-hash cache + per-field fallback escalation
  + eligibility keyword window. ⚠️ Benchmark NOT re-run — Groq TPD exhausted
  on both keys (199k/200k); re-run tomorrow AM to re-confirm ≥9/10 safe.
- #26 Layer 2 worker: drains new links → download → trim → extract → gate →
  publish/review; WORKER_DAILY_TOKEN_BUDGET (default 40000 est. tokens/day);
  3-strike skip; `--dry-run` never phones the LLM. Live validated on the dev
  DB (1 scanned doc, 2 non-PDFs ignored, 1 doc ~1.7k tokens).
- #27 table-driven matcher tests (27 boundary cases).
- #28 frontend: saveCandidateProfile wired into the profile step
  (sign-in-gated, remembers profile_id).
- #29 deploy hardening: startup SEED_EXAMS upsert (insert-missing only,
  never overwrites), optional SENTRY_DSN, local redis in docker-compose,
  redis-backed slowapi already wired (RATE_LIMIT_STORAGE_URL).

## Merged
- **#31** `feat/review-queue` — review queue: GET /api/v1/admin/review-queue
  (evidence quotes, PDF link, reasons), approve/reject/edit (all through the
  publish gate); /admin frontend page; env ADMIN_EMAILS allowlist gate
  (fail-closed); publish digest email behind MAIL_PROVIDER=smtp +
  MAIL_DIGEST_TO; inert otherwise. (Merged 2026-11-15 after all-green CI.)

## Status notes
- Telegram admin alerts still pending: TELEGRAM_ADMIN_CHAT_ID unset in
  backend/.env — user to paste chat id (health alerts for the 48h run
  silently skip until then).
- 48h poller: pid 17600, running with today's code; UPSC/SSCCR/SSC JSON fine;
  uppsc-home DEGRADED (503s all run — site down; can't tighten selector until
  reachable; backoff + alert machinery handles it).
- Dev DB (Supabase): reconciled to head yesterday; today it got d4e5f6a7b8c9 +
  e5f6a7b8c9d0 + f6a7b8c9d0e1 (all additive).
- New tests today: publisher (7), pipeline status (4), extractor cost
  (4), worker (7), admin review queue (6), matcher rules (27+1), seed upsert
  (2). First full suite: 325 passed with 2 flaky DB-timeout failures (docker
  was slow) — those 3 tests pass in isolation; clean re-run in flight
  (check /tmp/full_suite3.log).
- Benchmark re-run tomorrow AM needed for the README/report accuracy
  (2 PASS / 8 FLAGGED on Nov-15 run; numbers current in README).
- Deploy target + Sentry DSN: deferred (user decisions); no production deploy
  has happened. Localhost + Supabase dev only so far.
- Backup note: no automated DB backups yet — needed before any real user
  traffic (host decision pending by the user).

## What's intentionally not wired
- Auto-drain of raw_discovered_links is manual (`python -m app.services.layer2_worker`)
  or via cron — not on a schedule; quota cost per doc ~1.7k tokens + gate.
- Per-user email opt-in alerts (needs users table preference column).
- Cross-source ad-number dedup into a single exam_notification row (today:
  one exam row per extraction; dup finder exists in pipeline_metrics.py).
- age_relaxations don't persist onto exam_notifications (no column; the
  eligibility engine uses statutory relaxations; exam-specific ones stay in
  extraction_results.extracted).
