# Pipeline handoff (2026-11-26, BCA-eligible networking / cyber roles)

Three more rows (157 → 160), all accepting BCA and checked against official
notifications. `mygov-network-administrator` (above) also accepts BCA and is
the only currently-open pure networking role in the set.

| id | Job | Window | Official source |
|---|---|---|---|
| `kerala-hc-system-assistant` | High Court of Kerala, System Assistant, 90 posts | **open until 2026-12-14** | Rec. No. 24/2026 notification PDF, dated 2026-11-10 |
| `nielit-delhi-cloud-administrator` | NIELIT Delhi Cloud Administrator | **open until 2026-12-06** | NIELIT Advt 07/354/2026/NDL/FM page |
| `duk-junior-forensics-analyst` | DUK Junior Forensics Analyst (KSAAC) | closed 2026-11-18 | DUK notification + 2026-11-13 extension notice |

- Kerala HC asks for BCA / B.Sc(CS) / computer-electronics diploma **plus 2 years
  of hardware troubleshooting with basic computer networking**; age is a lower
  bound only (born on/after 02.01.1985), encoded as 18–41 with a note.
- NIELIT is `check_required`: the main route is BE/B.Tech/M.Tech/MCA, and BCA is
  accepted **only with a cloud certification**, which the matcher cannot test.
  BCA stays in `allowed_degrees` but the verdict is forced to `check_manually`.
- DUK's Junior Forensics Analyst accepts BCA and **fresh graduates**; its
  image-only extension notice was rendered and read directly to confirm
  18.11.2026. NABARD's SOC Analyst post does **not** accept BCA (BE/B.Tech or
  MCA only), so it remains in the set as a BE-focused next-cycle reference.
- No BCA-eligible *government* SOC Analyst notification was found; the only
  BCA-friendly "SOC Analyst" hit was a private-sector Infosys listing, which is
  out of scope for this government-jobs app.

Validation: `py_compile` passes, 160 unique seed ids, all fields map to
`ExamNotification` columns. DB-backed pytest still requires CI (local Postgres
password auth fails).

---

# Pipeline handoff (2026-11-26, networking / SOC seed coverage)

Four new curated rows in `backend/app/core/seed.py` (153 → 157), each checked
against the recruiting body's own notification PDF on 2026-11-26:

| id | Job | Window | Official source |
|---|---|---|---|
| `mygov-network-administrator` | MyGov Network Administrator / Engineer, Delhi (1 post) | **open until 2026-12-09** | MyGov/Digital India Corporation PDF, published 2026-11-25 |
| `nabard-soc-analyst-2026` | NABARD SOC / Information Security Analyst (Advt 04) | closed 2026-11-02 | NABARD detailed ad + 2026-10-27 extension notice |
| `nabard-network-security-analyst-2026` | NABARD Network Security Analyst (Advt 04) | closed 2026-11-02 | same two NABARD PDFs |
| `cdac-cine-network-engineer-2026` | C-DAC CINE Consultant (IT & Network Engineer) | closed 2026-09-28 | C-DAC CINE/REC/2026/05 PDF, dated 2026-09-22 |

Safety notes:

- **MyGov is `check_required`.** Its official PDF states the post, qualification
  (B.Tech/BE CS/ECE/EEE or BCA), 2–5 years' experience and the application form
  URL, but prints **no closing date**. 2026-12-09 is an aggregator-reported
  placeholder (`verified_on=None`); the matcher forces a `check_manually`
  verdict. The apply link is the form URL printed in the PDF, not a guess.
- **NABARD deadline comes from an image-only PDF.** The detailed ad prints
  26.10.2026; the 27.10.2026 extension notification (rendered and read directly,
  no extractable text) extends it to 02.11.2026. Split into two rows with
  distinct age bands (SOC/InfoSec 24–35; Network Security Analyst 26–38) so the
  multi-post advertisement cannot produce an over-broad "eligible" verdict.
- **C-DAC has no `apply_url`:** applications go by email to
  `recruitment-cine@cdac.in`, so the UI correctly shows only the notification.

Validation: `py_compile` passes, 157 seed rows with unique ids, all new fields
map to `ExamNotification` columns. DB-backed pytest could not run locally
(local Postgres rejects password auth — see earlier handoffs); CI must run it.

---

# Pipeline handoff (2026-11-16, SR-parity seed)

**Seed expanded to 75 notifications** (19 new, all verified against official
sources; 56 → 75; open now: 32 / total 75). New rows: BPSC Auditor Mains
(Mains-qualified only), UPSSSC Inter Level (1,784), Assam Rifles Tradesman
2026, RRC NR Apprentice (4,651), UPESSC TGT (17,735), UPESSC Principal
(1,475), UPESSC Headmaster (1,172), ISRO URSC 2026, Exim Bank MT & Manager
(120), UPSSSC JE Mechanical (1,156), RRC NWR Apprentice (2,008), AFMS Medical
Officer (SSC, 120), RRC CR Apprentice (3,809), Bihar Vidhan Sabha Office
Attendant (5), Bihar Vidhan Sabha JSA (15), UP Anganwadi (district-wise),
RRB Isolated Categories (CEN 09/2026, 191), UPSSSC JE Electrical (380),
ISRO SDSC SHAR Apprentice (400). Rationale: Sarkariresult-list parity was
requested — coverage of every currently-open recruitment on the list.
Domain/professional-qualification rows (e.g. MBBS for AFMS Medical Officer)
use degrees the matcher cannot rule out (`Specialist / See Notification`,
`ITI`, `MBBS` etc.) → matcher returns `needs_check` / "Check notification" —
never a wrong confident verdict. Two rows (UPSSSC JE 05, Anganwadi) are
`check_required` (deadline opens on multiple phased windows). RRB Isolated
Categories 2026 initially excluded for Prince's qualifications — re-added on
user request for SR parity. Dev DB `/api/v1/eligibility/exams?status=all`
returns all 75 with `window_state` (32 open / 43 closed). Frontend `Latest
Jobs` tab renders both sections.

---

# Pipeline handoff (2026-11-16, apply links)

**`apply_url` is now wired end to end.** Goal: jobs carry an "Apply" link to the
official online application portal, not the official-PDF notification link.

- New nullable column `exam_notifications.apply_url` (migration
  `1a2b3c4d5e6f`, additive, no backfill needed for correctness — seed ships values).
- Seed: 50 of 56 rows carry a verified `apply_url` (researched against official
  sources 2026-11-16 — SSC→ssc.gov.in/home/apply, UPSC→upsconline.nic.in,
  RRB→rrbapply.gov.in, IBPS→ibpsreg.ibps.in, SBI→sbi.bank.in/web/careers/current-openings,
  DSSSB→dsssbonline.nic.in, AFCAT→afcat.edcil.co.in, RBI→opportunities.rbi.org.in,
  NABARD→nabard.org/career, LIC→licindia.in/careers, RMLIMS→drrmlims.ac.in,
  BHU→bhu.ac.in/rac, Indian Bank→ibpsreg.ibps.in/inbraoct26/, NICL→nats.education.gov.in/index.php,
  HCL(MCP)→hindustancopper.com/ITIApplicationmcp/Login/145, armed forces/Agniveer
  portals, BSNL externalexam.bsnl.co.in, NIC recruitment.nic.in, DRDO rac.gov.in).
  Deliberately blank (never guessed): delhi-police-constable-12th, ib-acio-grade-ii,
  isro-scientist-b, iocl-officer, ntpc-executive, kvs-tgt. `_REFRESHABLE_FIELDS`
  refreshes apply_url but never nulls a stored one the file doesn't define.
  Apply URLs are cycle/portal entry points and must be re-verified each season,
  exactly like the deadline verification pass.
- Layer 2: `apply_url` is an optional, non-critical extraction field — only kept
  when the printed notice explicitly gives the URL (http/https, ≤500 chars); LLM
  never constructs it. Never affects the review/publish gate or token budget.
- Publisher carries it onto `exam_notifications`; publish digest email includes it;
  admin review-queue edit can set/correct it pre-publish.
- API: `ExamMatchResult.apply_url` (null when unknown). UI: primary "Apply" intent
  = `apply_url` (Apply Now / Apply on Official Portal); the official notification
  PDF stays as a separate "Official notification" link. Rows without apply_url show
  no Apply button, just the PDF link.
- Latest Jobs feed (`GET /api/v1/eligibility/exams?status=all`; default stays
  `open`): open windows first ("Open Now — Apply Directly", Apply Online per row),
  then closed cycles ("Closed Cycles — Next Cycle Reference", apply disabled, PDF
  kept) for next-cycle reference. Search filter, verified-deadline badges,
  `window_state` computed server-side (open/closed/unknown). NOTE: the TanStack
  `latest-jobs.tsx` implementation was superseded by the RozgarBoard SPA rewrite
  (upstream #33); the SPA feed renders the same data — apply_url wiring for it
  ships separately (see feat/apply-url-graft). Currently 75 verified rows (32 open) —
  the set only grows when the Layer-1 pipeline finds new official notices
  (sync-live-jobs does SSC/UPSC only today; broader portals = one-at-a-time
  follow-up per SEED_VERIFICATION scope note). DB-backed test:
  `tests/eligibility/test_exams.py` (CI runs it).
- Tests added (publisher ×3, extractor ×3, matcher ×2). DB-backed suite NOT run
  locally (no Docker daemon; local PG on :5432 rejects password auth; Supabase
  dev DB must not be pointed at by the test harness — it drops/creates
  `govjobs_test`). CI must run the suite; migration `1a2b3c4d5e6f` must be applied
  to the dev DB (`alembic upgrade head`) before deploy.

---

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
- 2026-11-16: LLM fallback rotated to the new second Groq key (same
  OpenAI-compatible endpoint, openai/gpt-oss-120b) for TPD overflow —
  fallback verified loading and live-tested (HTTP 200). Effective daily
  LLM headroom ≈ 2 × key TPD. Benchmark re-run unblocked.
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
