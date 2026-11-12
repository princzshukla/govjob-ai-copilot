# Phase 0 preflight report (STEP 1 only — no code written)

Date: 2026-11-12
Author: AI pair (senior engineer role)
Plan source: `IMPLEMENTATION_PLAN.md` (untracked; added to `.gitignore` by you)

This file records the overlap check and open questions **before** any Phase 0
code is written. No source file was modified for Phase 0.

> **Status update:** Phase 0 has since been implemented on
> `chore/phase-0-alembic-ci`. Results, decisions and verification are in
> `docs/implementation/phase-0-completion.md`. The section below is kept as the
> pre-implementation record.

---

## 1. Repo snapshot

| Item | Value |
|---|---|
| Current checkout | `backend/login` |
| HEAD | `03c02c0` — `chore: finish local merge` |
| `origin/backend/login` | `03c02c0` (same commit) |
| `origin/main` | `03c02c0` (same commit) |
| Local `main` | `48eff30` — **15 commits behind `origin/main`** (stale local ref only) |
| Working tree | clean except `.gitignore` (your uncommitted edit adding `IMPLEMENTATION_PLAN.md`) |
| Tags | none |
| Postgres | running on 5432 |
| Backend | running from this repo on **port 8080** (`.env` says 8000) |

Conclusion: your branch is **already identical to `origin/main`**. There is no
divergence to reconcile before Phase 0.

---

## 2. Overlap check (STEP 1.2 / 1.3)

`git fetch origin --prune` ran first. Remote branches:

| Branch | Diff vs `origin/main` |
|---|---|
| `origin/backend/login` | **empty** (identical commit) |
| `origin/fix/bug-issue` | **empty** (already merged) |

`git branch -r --no-merged origin/main` → **no output** (nothing unmerged).

**So there is no parallel branch with outstanding changes to conflict with.**
Every file on the Phase 0 map has zero overlap risk from another branch right
now. The real overlap risk for later phases is the branch you push next, so the
conflict-avoidance rules still apply.

---

## 3. Phase 0 file map verification (STEP 1.4)

| File | State | Notes |
|---|---|---|
| `backend/alembic.ini` | **MISSING** | expected — NEW |
| `backend/alembic/env.py`, `script.py.mako`, `versions/` | **MISSING** | expected — NEW |
| `.github/workflows/ci.yml` | **MISSING** | expected — NEW (no `.github/` at all) |
| `backend/requirements.txt` | exists | `alembic==1.20.1` already pinned → **no edit needed** |
| `backend/tests/conftest.py` | exists | already forces `ENVIRONMENT=test` + `govjobs_test` DB → **no edit needed** |

No file on the map was renamed or moved. Nothing to stop for on this point.

---

## 4. Hardcoded demo identity search (STEP 1.4)

`git grep -n "usr_demo_001"`:

```
backend/app/api/v1/endpoints/adaptive.py:28   user_id Query default "usr_demo_001"
frontend/src/components/AdaptiveQuizPanel.tsx:53   userId = "usr_demo_001"
frontend/src/components/govjob/roadmap-step.tsx:35 userId = "usr_demo_001"
frontend/src/components/govjob/use-mastery.ts:10   userId = "usr_demo_001"
frontend/src/routes/quiz...tsx:39                  const userId = "usr_demo_001"
```

(Phase 2 fixes the backend one; Phase 6 fixes the four frontend ones. Not in
scope for Phase 0.)

Demo rows actually present in the dev DB (`govjobs_db`):

| Table | Total rows | `usr_demo_001` rows |
|---|---|---|
| `users` | 0 | — |
| `topic_mastery` | 1 | **1** |
| `quiz_attempts` | 2 | **2** |
| `candidate_profiles` | 0 | — |
| `saved_roadmaps` | 0 | — |

So the "delete demo data" decision has real data behind it: 3 rows.

---

## 5. Alembic heads (STEP 1.5)

`alembic` is installed in `backend/venv` (1.20.1) but there is **no Alembic
project yet**:

- `alembic.ini`: missing
- `backend/alembic/`: missing
- migrations: 0
- heads on `origin/main`: **0**
- heads on `origin/backend/login`: **0** (identical tree)
- heads on `origin/fix/bug-issue`: **0**

No merge-heads work needed. Phase 0 creates the first revision, which becomes
the single root head.

---

## 6. Baseline checks (current tree, before any Phase 0 change)

| Check | Command | Result |
|---|---|---|
| Backend tests | `cd backend; .\venv\Scripts\python.exe -m pytest -q` | **8 passed in 6.75s** |
| Backend import | `from app.main import app` | OK |
| Frontend type-check | `cd frontend; npx tsc --noEmit` | **clean** |
| Frontend tests | `cd frontend; npm test` (vitest) | **2 files, 7 tests passed** |
| Frontend lint | `cd frontend; npm run lint` | **FAILS — no ESLint config file** |

### Blocker found: ESLint is not configured

`npm run lint` → `ESLint couldn't find an eslint.config.(js|mjs|cjs) file`.
There is no `eslint.config.js` and no `.eslintrc*` in `frontend/`. ESLint 9
does not accept the old format without migration.

That means the Phase 0 checkbox "CI job that runs backend tests and the
frontend type-check and lint" cannot be completed as written **without**
adding an ESLint config, which is not on the Phase 0 file map. See question 2.

---

## 7. Proposed commit sequence (for approval)

Branch: `chore/phase-0-alembic-ci` cut from `origin/main` (`03c02c0`), not from
the stale local `main`.

Tag before any change: `pre-phase-0` (annotated, on `03c02c0`).

| # | Commit | Files | Notes |
|---|---|---|---|
| 1 | `chore: add alembic async scaffolding` | `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/README` | New files only. `env.py` reads `DATABASE_URL` from `app.core.config.settings` and runs migrations with the async engine. |
| 2 | `chore: add initial schema migration` | `backend/alembic/versions/0001_initial_schema.py` | Autogenerated against an **empty scratch DB** (`govjobs_migrate_check`), then reviewed by hand. Includes `DELETE` of `usr_demo_001` rows from `topic_mastery` + `quiz_attempts` (no-op on a fresh DB). Never touches an existing migration. |
| 3 | `ci: add backend + frontend pipeline` | `.github/workflows/ci.yml` | Postgres 16 service, `pip install -r requirements.txt`, `pytest`, `npm ci`, `npx tsc --noEmit`, `npm test`. Lint step only if approved (see question 2). |
| 4 | `chore: document migration workflow` | `docs/implementation/phase-0-preflight.md` (this file) + a short "how to run migrations" section | Optional; keeps the report in-repo. |

Deliberately **not** in Phase 0 (would touch files outside the map):

- removing `Base.metadata.create_all` from `init_db()` (`backend/app/core/database.py`)
- changing the test fixture to run migrations (`backend/tests/conftest.py`)
- `.gitignore` edits beyond what you already have

Those belong to Phase 1, where the first schema change lands.

---

## 8. Open questions — please answer before "go ahead"

1. **Branch name**: use `chore/phase-0-alembic-ci` from `origin/main`? Your
   current `backend/login` is the same commit as `main`, so I will not branch
   from the stale local `main` unless you say so.
2. **Lint blocker**: Phase 0 asks for frontend lint in CI, but ESLint has no
   config. Choose one:
   - (a) CI runs type-check + vitest + backend pytest only, add ESLint in a
     later phase (recommended: zero new conflict surface), or
   - (b) I add a minimal `frontend/eslint.config.js` (outside the Phase 0 map)
     and make lint pass — needs your approval and may require small code fixes.
3. **Tag**: `pre-phase-0` local only, or push it to origin?
4. **Demo rows**: include `DELETE` for the 3 `usr_demo_001` rows in the initial
   migration (recommended), or leave the dev DB as is?
5. **Existing dev DB**: after generating the initial revision, stamp the
   existing `govjobs_db` with `alembic stamp head` so future migrations apply
   cleanly. OK to do that locally (no code change)?
6. **Commit this report?** It is a new file outside the phase map, created at
   your request. Commit it with Phase 0, or keep it untracked?

**STOPPING HERE.** No Phase 0 code, branch, tag, or commit has been created.
Waiting for your "go ahead" plus answers to the six questions.
