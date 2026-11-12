# Phase 0 completion report — Alembic, tests, CI

Branch: `chore/phase-0-alembic-ci` (cut from `origin/main` @ `03c02c0`)
Baseline tag: `pre-phase-0` (points at `03c02c0`)
Status: **Phase 0 complete, verified locally. Not pushed.**

---

## 1. What changed

| File | Commit intent | Notes |
|---|---|---|
| `backend/alembic.ini` | scaffolding | No URL stored; `script_location` is `%(here)s/alembic` |
| `backend/alembic/env.py` | scaffolding | Async engine with `NullPool`; URL from `app.core.config.settings`; `compare_type` + `compare_server_default` enabled |
| `backend/alembic/script.py.mako` | scaffolding | Alembic default template |
| `backend/alembic/README` | scaffolding | Project-specific migration instructions |
| `backend/alembic/versions/98d8dddbecd4_initial_schema.py` | initial migration | All 8 current tables, indexes and the `sessions → users` cascade FK; downgrade reverses it |
| `backend/tests/conftest.py` | test bootstrap | Drops/recreates `govjobs_test` then runs `alembic upgrade head`; no more `create_all` in tests |
| `frontend/eslint.config.js` | lint | Flat config (ESLint 9) using the already-installed `typescript-eslint`, `react-hooks`, `react-refresh`, `prettier` packages. Generated files/build output ignored |
| `frontend/src/components/govjob/roadmap-step.tsx` | bug fix | `useTopicMastery` was called **after** an early `return`; hooks now run unconditionally |
| `.github/workflows/ci.yml` | CI | Postgres 16 service, migration-from-empty + drift check, pytest; Node 24, `npm ci`, `tsc`, lint, vitest |

Not touched (by design, outside the Phase 0 map):

- `backend/app/core/database.py` — `init_db()`/`create_all` still runs at app startup.
  Alembic is now the source of truth for schema changes; removing `create_all`
  belongs to Phase 1 (the first real schema change).
- `backend/requirements.txt` — `alembic==1.20.1` was already pinned, so no edit.
- `frontend/package.json` / lockfile — no new dependencies were required.

---

## 2. Decisions

| Question | Decision |
|---|---|
| Demo data | Deleted the 3 existing `usr_demo_001` rows locally (1 `topic_mastery`, 2 `quiz_attempts`) before anything else. No `DELETE` is embedded in the initial migration because it is a no-op on a fresh database; **Phase 1** deletes any remaining demo rows *before* converting `user_id` to an integer FK (the conversion would fail otherwise) |
| Existing dev DB | Stamped with `alembic stamp head` after verifying `alembic check` reports zero drift, so future migrations apply cleanly |
| `create_all` | Kept for now (see above); tests no longer use it, so drift is caught in CI |
| ESLint | Added a real flat config instead of skipping lint in CI. `npm run lint` now exits 0 (10 pre-existing warnings, 0 errors) |
| Lint error found | `rules-of-hooks` violation in `roadmap-step.tsx` was a genuine bug, fixed rather than silenced |
| Tag | `pre-phase-0` created locally only (not pushed) |

---

## 3. Verification (commands and results)

| Check | Result |
|---|---|
| `alembic upgrade head` on empty `govjobs_migrate_check` | `Running upgrade -> 98d8dddbecd4` |
| `alembic check` (empty scratch DB) | `No new upgrade operations detected.` |
| `alembic downgrade base` then `upgrade head` | round-trip OK |
| `alembic heads` | exactly one head: `98d8dddbecd4` |
| `alembic current` on dev DB after stamp | `98d8dddbecd4 (head)` |
| `alembic check` on dev DB | `No new upgrade operations detected.` |
| `pytest -q` (schema built from migrations) | **8 passed** |
| `govjobs_test` schema after tests | 8 app tables + `alembic_version = 98d8dddbecd4` |
| `npx tsc --noEmit` | clean |
| `npm run lint` | 0 errors, 10 warnings |
| `npm test` | 2 files, 7 tests passed |
| `npm run build` | built successfully |
| `npm ci --dry-run` | lockfile accepted (no `EUSAGE` mismatch) |

Phase 0 acceptance from `IMPLEMENTATION_PLAN.md`:

- [x] Working branch + tag of the current state
- [x] Alembic configured (async, autogenerate) and used by tests
- [x] Separate test database (`govjobs_test`) rebuilt from migrations
- [x] Existing 8 auth tests pass as baseline
- [x] CI job: backend tests + migration check, frontend typecheck + lint + tests
- [x] Demo-data decision made and executed

---

## 4. Notes and follow-ups

1. **CI is unproven until pushed.** The workflow is validated for YAML syntax and
   every step was run locally, but the first real run happens on GitHub.
2. `init_db()` still calls `create_all` at app startup. Harmless today, but
   Phase 1 should remove it so the app never silently diverges from Alembic.
3. `npm run lint` currently succeeds with 10 warnings (`no-explicit-any` in
   `govjob-app.tsx` and the unused `quiz...tsx` route; `react-refresh` in the
   shadcn `ui/*` files). Warnings do not fail CI; tighten with
   `--max-warnings` once the pre-existing warnings are addressed.
4. `frontend/.wrangler/deploy/config.json` is still tracked from an earlier
   commit. Consider ignoring/removing it separately (not part of Phase 0).
5. `frontend/src/routes/quiz...tsx` is still the broken `main` route (invalid
   filename, params that the path does not define). Out of scope here.

**Do not start Phase 1 until this branch is merged.**
