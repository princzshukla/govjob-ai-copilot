# GovJob Matcher & AI Roadmap — API Endpoints

This document lists every HTTP endpoint the application exposes (FastAPI backend), what data each
one serves, and which part of the frontend consumes it.

- **Backend:** FastAPI app `backend/app/main.py` ("GovJob Matcher & AI Roadmap API", v1.0.0)
- **Base URL (local dev):** `http://localhost:8000`
- **API prefix:** all application endpoints live under `/api/v1`
- **Frontend:** RozgarBoard SPA (Vite + React 19, `frontend/`) — no SSR; serve statically.
  The API client is `frontend/src/lib/api.ts`
  (`API_BASE` = `VITE_API_BASE_URL` / `VITE_GOVJOB_API_BASE`, default
  `http://localhost:8000/api/v1`). Top-level views are nav-state tabs
  (Latest Jobs / My Eligibility / My Roadmap / Photo & Signature); auth and account flows live in modals.
- **Auth model:** session cookie (`HttpOnly`, set on register/login). The cookie name comes from
  `COOKIE_NAME`. Tokens are stored hashed in the `sessions` table. There is no Bearer-token flow.
  - `current_user` → requires a valid session, else `401 Not authenticated`
  - `optional_current_user` → guests allowed; session used when present
  - `require_admin` → session **and** the user's email in the `ADMIN_EMAILS` allowlist (empty allowlist = nobody is admin)
- **Docs:** `/docs`, `/redoc`, `/openapi.json` are only served when `ENVIRONMENT != "production"`; in production they return 404.
- **Health check:** `GET /health` → `{"status": "ok"}` (outside `/api/v1`, unauthenticated, used by deploy/uptime probes).
- **Cross-cutting middleware:** security headers on every response (`no-store`, deny-all CSP, etc.), CORS restricted to `CORS_ORIGINS`, rate limiting via slowapi (429 on exceed), 422 bodies never echo submitted values back.
- **Discovery pipeline (Layer 1 scraper / Layer 2 worker) has NO HTTP endpoints.** It runs as a poller/worker process against the same database (see `PIPELINE_HANDOFF.md`, `backend/scripts/`). Only its *outputs* surface over HTTP: the admin review queue and the published exam notifications served by the eligibility endpoints.

---

## 1. Auth — `/api/v1/auth` (`endpoints/auth.py`, tag `Auth`)

Session lifecycle. Used by `frontend/src/hooks/use-auth.ts` and `use-me.ts` on every page (via `__root`).

| Method | Path | Auth | Serves / does | Frontend caller |
|---|---|---|---|---|
| POST | `/api/v1/auth/register` | public (5/min/IP) | Creates a user account (email + phone must be unique; generic conflict error to avoid enumeration). Sets the session cookie. Returns the user record. | `api.register` — sign-up flow in `use-auth.ts` |
| POST | `/api/v1/auth/login` | public (5/min/IP) | Verifies credentials (constant-work dummy hash for unknown emails), creates a fresh session (fixation-safe), sets the cookie. Returns the user record. | `api.login` — `signIn` in `use-auth.ts` |
| POST | `/api/v1/auth/logout` | cookie (idempotent) | Deletes the session row and clears the cookie. Always 200. | `api.logout` — `signOut` in `use-auth.ts` |
| GET | `/api/v1/auth/me` | session | Returns the currently logged-in user (`id`, `email`, `full_name`, `phone`, …). | `api.getMe` — `use-me.ts` (drives the whole signed-in UI state) |

`UserOut` shape: `id`, `email`, `full_name`, `phone`, created/updated timestamps. Passwords are Argon2-hashed; the hash never leaves the server.

## 2. Users (account) — `/api/v1/users` (`endpoints/users.py`, tag `Users`)

Account-level actions for the signed-in user. Frontend: `src/components/govjob/account-page.tsx` (route `/account`).

| Method | Path | Auth | Serves / does | Frontend caller |
|---|---|---|---|---|
| PATCH | `/api/v1/users/me` | session | Updates the display name only (`full_name`). `email`/`phone` are not updatable here by design. Returns the updated user. | `api.updateMyFullName` — account page |
| POST | `/api/v1/users/me/change-password` | session (5/min) | Verifies current password, re-hashes with Argon2, **revokes every other session** (current session survives). Returns `{message}`. | `api.changePassword` — account page |
| DELETE | `/api/v1/users/me` | session (5/min) | Verifies password, deletes the account and cascades owned rows, clears the cookie. `204 No Content`. | `api.deleteAccount` — `use-auth.ts` (`removeAccount`), account page |

## 3. User-owned data — `/api/v1/users/me` (`endpoints/user_data.py`, tag `Users`)

Owned profile, saved roadmaps and per-week progress. The session cookie — never a URL parameter — identifies the owner. Frontend: main app (`govjob-app.tsx`), `use-roadmap.ts`, `use-auth.ts`.

| Method | Path | Auth | Serves / does | Frontend caller |
|---|---|---|---|---|
| GET | `/api/v1/users/me/profile` | session | Returns the caller's saved `CandidateProfile` (statutory details: DOB, gender, category, PwD, domicile, degree, stream, CGPA, passing year, skills). `404` if none saved yet. | `api.getMyProfile` — defined in client; not currently rendered (profile is re-fetched via claim/save flows) |
| PUT | `/api/v1/users/me/profile` | session (30/min) | Merge-update of the profile: only fields present in the payload change; explicit `null` clears one field; defaulted columns (`gender`, `category`, `is_pwd`) never become NULL. Creates the row if missing (one profile per account). | `api.putMyProfile` — defined in client |
| GET | `/api/v1/users/me/roadmaps/{exam_id}` | session | Returns the caller's saved AI roadmap for an exam (`roadmap_json`) plus completion progress (`completed_weeks`, `total_weeks`, ids). `404` if none. | `api.getMyRoadmap` — `use-roadmap.ts` (roadmap step) |
| GET | `/api/v1/users/me/roadmaps/{roadmap_id}/progress` | session | Returns `{roadmap_id, target_weeks, completed_weeks, …}` for one owned roadmap. | `api.getRoadmapProgress` — defined in client |
| PUT | `/api/v1/users/me/roadmaps/{roadmap_id}/progress` | session (120/min) | Marks a week done/undone (`{week_no, done}`). Idempotent insert/delete in `roadmap_progress`; `week_no` out of range → 422. | `api.toggleRoadmapWeek` — `use-roadmap.ts` (week checkboxes, optimistic update) |
| POST | `/api/v1/users/me/claim-draft` | session (10/min) | Attaches a guest's parsed/completed draft profile to the account **once**. If the account already has a profile, returns it with `already_claimed` (never overwrites). Raw resume text is never stored. | `api.claimMyDraft` — `use-auth.ts` (runs automatically after register/login when a guest draft exists) |

## 4. Candidate (resume & eligibility profile) — `/api/v1/candidate` (`endpoints/candidate.py`, tag `Candidate`)

Resume parsing and the persisted "candidate" record used by the eligibility engine. Frontend: main app upload flow (`govjob-app.tsx` → `resume-profile-step.tsx`).

| Method | Path | Auth | Serves / does | Frontend caller |
|---|---|---|---|---|
| POST | `/api/v1/candidate/parse-resume` | optional (guests: 3/day/IP; signed-in: 20/day) | Accepts a PDF resume (≤ 5 MB, `%PDF-` magic checked), extracts text, and parses it with Groq into a structured profile (name, DOB, degree, marks, skills, …). Returns `ResumeParseResponse` (the parsed fields + raw text). Nothing is persisted by this endpoint. | `api.parseResume` — `govjob-app.tsx` upload flow |
| POST | `/api/v1/candidate/profile` | session | Persists/updates a `CandidateProfile` owned by the caller (one per account; `?profile_id=` re-points/updates a specific owned profile). 404 (not 403) if the id belongs to someone else. | `api.saveCandidateProfile` — `govjob-app.tsx` (after parsing or manual entry) |
| GET | `/api/v1/candidate/profile/{profile_id}` | optional | Fetches a persisted profile by id. Owned profiles are invisible to everyone but their owner (404). Returns `CandidateProfileResponse`. | `api.fetchCandidateProfile` — defined in client; not currently rendered |
| GET | `/api/v1/candidate/profile/{profile_id}/eligibility` | optional | Loads a saved profile and runs the full eligibility matcher against all active exams. Query param `primary_exam_id` tunes Plan-B syllabus-overlap %. Returns `EligibilityCheckResponse`. | `api.checkSavedProfileEligibility` — defined in client; not currently rendered |

## 5. Eligibility & roadmaps — `/api/v1/eligibility` (`endpoints/eligibility.py`, tag `Eligibility & Roadmaps`)

The core matching engine and AI roadmap generation. Frontend: main app (`govjob-app.tsx`, `use-eligibility.ts`, `eligibility-results.tsx`).

| Method | Path | Auth | Serves / does | Frontend caller |
|---|---|---|---|---|
| GET | `/api/v1/eligibility/exams` | public | Lists stored government exam notifications (`{total, exams}`), seeding `SEED_EXAMS` on first run. `?status=open` (default) = only open windows (`is_active` + deadline not past, IST). `?status=all` = **every** stored notification (open and closed cycles), each row annotated with computed `window_state` (`open`/`closed`/`unknown`), ordered open-by-deadline first then closed most-recent-first. Rows carry provenance (`source_url`, `official_pdf_url`, `last_checked_at`, `apply_url` — the official online application portal, NULL when unknown) and deadline-verification state (`verified_on`, `verification_status`; NULL = unverified → UI shows "check official notification"). | `src/views/directions/Rozgar.tsx` (`GET /api/v1/eligibility/exams` for the Latest Jobs feed) |
| POST | `/api/v1/eligibility/check` | public, per-IP 30/hour | Evaluates a profile in the request body against every open exam (active + deadline not past, IST): age at cutoff, category/relaxation, degree/stream, attempts, etc. Returns `EligibilityCheckResponse` = `{candidate_name, eligible_now[], borderline_last_chance[], check_manually[], ineligible[]}` where each item is an `ExamMatchResult` (verdict, per-rule explanations, syllabus-overlap %, deadline, verified_on/verification_status, provenance, and `apply_url` — official online application portal, NULL when unknown). | `api.checkEligibility` — `use-eligibility.ts` mutation → renders `eligibility-results.tsx` |
| POST | `/api/v1/eligibility/generate-roadmap/{exam_id}` | session (10/hour) | Generates an AI week-by-week study roadmap for the exam via Groq (cached per `exam_id + target_weeks`, `?target_weeks=4..52`, default 12). Also **saves/upserts** the roadmap for the session user so it survives across devices. Returns `StudyRoadmapResponse` (`exam_name`, `total_duration_weeks`, `weekly_breakdown[]`, `revision_strategy`). | `api.generateRoadmap` — `govjob-app.tsx` (roadmap step) |
| POST | `/api/v1/eligibility/report` | public | Stores a "this eligibility result is wrong" report (`exam_id` + verdict mismatch + a PII-stripped candidate snapshot — name and raw resume text are dropped). Returns `{report_id, status:"received"}`. | Not wired to a frontend button yet |
| POST | `/api/v1/eligibility/sync-live-jobs` | session (4/hour) + global 15-min cooldown | Discovers new notifications from the **official pipeline sources** (Layer 1 pass over UPSC What's New + SSC Notice Board), then drains Layer 2: PDF download → Groq extraction → publish gate. Published rows carry official government links (`source_url`/`official_pdf_url`). Requires login and is globally throttled, because one call costs scrape + LLM work for everybody. Returns `{new_jobs_discovered, skipped_jobs, total_active_jobs}`. | `api.syncLiveJobs` — `govjob-app.tsx` ("Sync Live Jobs" action) |

## 6. Adaptive preparation ("Sathi AI") — `/api/v1/adaptive` (`endpoints/adaptive.py`, tag `Sathi AI`)

Question bank + adaptive quizzes + mastery tracking. No frontend UI since the SPA swap
(`/quiz` removed); `GET /adaptive/mastery/{exam_id}` is still consumed by My Roadmap's
mastery badges.

| Method | Path | Auth | Serves / does | Frontend caller |
|---|---|---|---|---|
| GET | `/api/v1/adaptive/quiz` | session (30/hour) | Serves `count` questions (default 3, max 10) for `exam_id` / `subject` / `topic` from `question_bank`, generating via Groq on cache miss. Returns `QuizGenerateResponse` (`quiz_id`, questions with options/expected times). Owner is always the session user. | No UI caller (removed in the SPA swap) |
| POST | `/api/v1/adaptive/submit-quiz` | session (60/hour) | Grades submitted answers against stored question rows (client scores are never trusted). Computes accuracy, net marks (per-exam marking scheme), per-question diagnostics (Rush / Time-Sink / Conceptual Gap), logs a `QuizAttempt`, updates `TopicMastery` with an EMA (α=0.35) and upserts per `(user, exam, topic)`. Returns `QuizEvaluationResponse` (score, diagnostics, micro-revision suggestions, per-question review). | No UI caller (removed in the SPA swap) |
| POST | `/api/v1/adaptive/report-question/{question_id}` | session (30/hour) | Flags a flawed question (`{reason}`). Auto-retires it at ≥3 reports or >15% report rate; decrements its quality score. | `api.reportAdaptiveQuestion` — defined in client; no UI caller yet |
| POST | `/api/v1/adaptive/import-real-pyq` | session (20/hour) | Imports a verified "real" Previous-Year Question (`exam_id`, `subject`, `topic`, `pyq_year`, full question payload) marked `origin_type=REAL_PYQ`. Note: any signed-in user may call this — it is **not** admin-gated. | No frontend caller (operator/tooling use) |
| GET | `/api/v1/adaptive/mastery/{exam_id}` | session (120/hour) | Returns all topic-mastery rows for the caller on one exam: per topic — `accuracy_ema`, `attempts_count`, `status` (`Mastered` / `Moderate` / `Needs Revision`), `last_reviewed_at`. | `api.fetchUserMastery` - RoadmapPage mastery badges |

## 7. Notifications (Telegram) — `/api/v1/notifications` (`endpoints/notifications.py`, tag `Notifications`)

Telegram account linking and deadline reminders. Frontend: `govjob-app.tsx` (Telegram settings card).

| Method | Path | Auth | Serves / does | Frontend caller |
|---|---|---|---|---|
| POST | `/api/v1/notifications/telegram/link` | session (10/hour) | Creates a short-lived (default ~10 min) one-time code; only the SHA-256 digest is stored. Returns `{code, expires_at, bot_username}` — the user sends the code to the bot. | `api.createTelegramLink` — `govjob-app.tsx` |
| GET | `/api/v1/notifications/telegram/status` | session (120/hour) | Returns `{linked: bool, chat_id?, verified_at?}` (chat id is masked) for the caller. | `api.getTelegramStatus` — `govjob-app.tsx` |
| DELETE | `/api/v1/notifications/telegram/link` | session (10/hour) | Removes the caller's Telegram link and pending codes. | `api.unlinkTelegram` — `govjob-app.tsx` |
| POST | `/api/v1/notifications/telegram/webhook` | Telegram shared-secret header (`X-Telegram-Bot-Api-Secret-Token`); **not** a session endpoint | Telegram's callback: turns a valid one-time code into a verified `TelegramLink` (idempotent re-link; chat↔account is 1:1). Fail-closed without the secret; unknown/expired codes are silently ignored. | n/a (called by Telegram servers) |
| POST | `/api/v1/notifications/send-deadline-alert` | session (20/hour) | Sends a deadline reminder (`exam_title`, `application_deadline`, `days_left`) to the **caller's own** verified chat only. `409` if not linked. | `api.sendTelegramAlert` — `govjob-app.tsx` |

## 8. Admin (review queue) — `/api/v1/admin` (`endpoints/admin.py`, tag `Admin`)

Operator-only queue for scraped exam extractions held back by the publish gate. Frontend: route `/admin` → `src/components/govjob/admin-review-page.tsx`. Auth: `require_admin` (session + `ADMIN_EMAILS` allowlist, fail-closed).

| Method | Path | Auth | Serves / does | Frontend caller |
|---|---|---|---|---|
| GET | `/api/v1/admin/review-queue` | admin | Lists up to 100 held extractions (`status='review'`) joined with their raw link and source: `id`, `source_name`, `url`, `title`, `missing_fields[]`, `review_note`, `extracted{}`, evidence quotes, per-field confidence, `exam_notification_id?`. | `api.fetchAdminReviewQueue` — admin page |
| POST | `/api/v1/admin/review-queue/{result_id}/approve` | admin | Marks the row trusted and promotes it through the publish gate (re-validates completeness/plausibility). On gate failure it stays in review and returns the reasons (`422`). Returns `{status:"promoted", exam_id, title}`. | `api.adminApproveExtraction` — admin page |
| POST | `/api/v1/admin/review-queue/{result_id}/reject` | admin | Permanently rejects the extraction (`status='rejected'`, never published). | `api.adminRejectExtraction` — admin page |
| POST | `/api/v1/admin/review-queue/{result_id}/edit` | admin | Patches specific fields (`total_vacancies`, `min_age`, `age_max_general`, `age_cutoff_date`, `required_qualification`, `application_last_date`, `pay_level`, `age_relaxations`, `apply_url`), then re-runs the publish gate. Returns `{status:"promoted", exam_id, title}` or `422`. | `api.adminEditExtraction` — admin page |

---

## Frontend → endpoint map (quick view)

| Frontend location | Endpoints used |
|---|---|
| `src/views/directions/Rozgar.tsx` (Latest Jobs feed + nav) | `GET /api/v1/eligibility/exams`; free verdict chips come from the cached `POST /api/v1/eligibility/check` response (no new calls) |
| `src/views/directions/rozgar-pages.tsx` → `EligibilityPage` | `POST /api/v1/candidate/parse-resume`, `POST /api/v1/eligibility/check`, `POST /api/v1/candidate/profile` (Save), `POST /api/v1/users/me/claim-draft` (on sign-in) |
| `src/views/directions/rozgar-pages.tsx` → `RoadmapPage` | `POST /api/v1/eligibility/generate-roadmap/{exam_id}`, `GET /api/v1/users/me/roadmaps/{exam_id}`, `PUT /api/v1/users/me/roadmaps/{id}/progress`, `GET /api/v1/adaptive/mastery/{exam_id}` |
| `src/lib/auth.tsx` + `src/components/rozgar/AuthModal.tsx` | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| `src/components/rozgar/AccountModal.tsx` | `PATCH /users/me`, `POST /users/me/change-password`, `DELETE /users/me`, Telegram: `POST /notifications/telegram/link`, `GET /notifications/telegram/status`, `DELETE /notifications/telegram/link` |
| Admin review queue (`/admin`) and `/quiz` route | **removed in the SPA swap** — no UI callers; the backend endpoints remain live |

## Misc

| Method | Path | Auth | Serves / does |
|---|---|---|---|
| GET | `/health` | public | Liveness probe → `{"status": "ok"}` (not under `/api/v1`) |
| GET | `/docs`, `/redoc`, `/openapi.json` | public, **non-production only** | Interactive API schema; 404 in production |

## Notes & gotchas

- **Rate limits** are per-account for signed-in users (`user:<id>`) and per-IP for guests, via slowapi; the global Telegram webhook and sync endpoint have their own ceilings. Exceeding → `429`.
- **Ownership is always the session user.** No endpoint accepts a `user_id` from the client; roadmap/profile/mastery queries are scoped to the cookie.
- **404 vs 403**: owned resources are hidden with 404 so ids cannot be probed.
- **Discovery pipeline** (scrape → extract → publish gate) exposes no HTTP routes; its review output surfaces only through `/api/v1/admin/review-queue*`, and its published output only through the exam data served by `/api/v1/eligibility/*`. Published rows carry an optional `apply_url` (official online application portal, extracted only when the notification explicitly prints one — never guessed); the seed file ships verified values for the major recurring exams (75 seeded rows as of 2026-11-16).
- `POST /api/v1/adaptive/import-real-pyq` lets any signed-in user add questions to the bank — it is intentionally unlisted in the UI but is **not** admin-only.
