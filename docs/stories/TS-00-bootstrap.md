# TS-00: Bootstrap the repository

- **Status:** In Progress — Backend and E2E scaffold sections done; Frontend, UI
  primitives, and Wire-up remain (Frontend/UI primitives are in progress on a
  separate branch; Wire-up depends on that branch landing)
- **Owner:** Both, together, one sitting
- **Points:** 3

**Do this before any feature story.** Right now the repo is documentation and config
describing a project that doesn't exist. This story creates the actual project so that
`make up` works and CI goes green. Until it lands, every CI job fails — that is expected,
not a bug.

## Goal

`make up && make migrate && make seed` runs clean, http://localhost:8000/docs loads,
http://localhost:5173 renders, `make test` passes with a trivial test, and CI is green.

No features. No auth. No AI. Plumbing only.

## Backend

- [x] `backend/requirements.txt` — fastapi, uvicorn[standard], sqlalchemy>=2, alembic,
      psycopg[binary], pydantic>=2, pydantic-settings, celery, redis, python-multipart
- [x] `backend/requirements-dev.txt` — first line `-r requirements.txt` (CI installs
      only this file for the backend job, so it must pull the runtime deps in too),
      then pytest, pytest-cov, pytest-html, httpx, factory-boy, ruff, mypy,
      pyreverse (via pylint)
- [x] `backend/pyproject.toml` — ruff + mypy config. Without this the pre-commit
      mypy hook has nothing to configure and will start blocking commits the
      moment `app/main.py` imports FastAPI/Celery/pydantic-settings
- [x] `backend/Dockerfile` — python:3.12-slim, install requirements, workdir `/app`
- [x] `backend/app/main.py` — FastAPI app, `/api/v1` router prefix, `GET /api/v1/health`
- [x] `backend/app/core/config.py` — pydantic-settings reading every var in `.env.example`
- [x] `backend/app/core/db.py` — engine, session factory, `Base`
- [x] `backend/app/worker.py` — Celery app wired to `REDIS_URL`
- [x] `alembic init` inside `backend/`, `env.py` pointed at `Base.metadata` and
      `DATABASE_URL`; first migration enables `pgcrypto` and `vector` extensions
- [x] `backend/app/scripts/dump_openapi.py` — prints `app.openapi()` as JSON to stdout
- [x] `backend/app/scripts/dump_erd.py` — renders PlantUML from `Base.metadata`
- [x] `backend/app/scripts/seed.py` — empty stub for now, real seed data comes later
- [x] `backend/tests/test_health.py` — asserts `/api/v1/health` returns 200

## Frontend

- [x] `npm create vite@latest frontend -- --template react-ts`
- [x] Tailwind installed. **Check the major version** — the shipped
      `src/styles/tokens.css` uses v4 `@theme` syntax. If you end up on v3, convert
      those tokens into `tailwind.config.js` instead. Do not mix.
      → npm shipped Tailwind 4.3.3; wired via `@tailwindcss/vite`, no conversion needed.
- [x] `frontend/Dockerfile` — node:20-alpine, workdir `/app`
- [x] React Router with two shells: authenticated app, and bare public layout
- [x] TanStack Query provider
- [x] `src/lib/api.ts` — fetch wrapper reading `VITE_API_URL`
- [x] Vitest + React Testing Library, one trivial passing test
- [x] `/kitchen-sink` route (dev only) rendering every `components/ui` primitive —
      this is your Storybook replacement, ~20 lines, no maintenance burden

## UI primitives — build these now, before any screen

Ten components, from `docs/design.md` tokens only. Every later story reuses them, so
an hour here saves nineteen inconsistent screens later.

Button · Input · Select · Textarea · FileInput · DataTable · Modal · StatusBadge ·
MatchScore · Card · EmptyState · Toast

Each needs its loading/disabled/error states from the start (`docs/checklists/ux.md`).

## E2E

- [x] `e2e/` with Playwright config pointed at `http://localhost:5173`
- [x] One smoke test: app loads, health endpoint reachable (written; not yet run
      end-to-end — needs the frontend branch to land first)

## Wire-up

- [ ] `make api-client` runs and produces `frontend/src/lib/api.d.ts`; commit it
- [ ] `pre-commit install`, then `pre-commit run --all-files` passes
- [ ] Uncomment the `contract` and `e2e` jobs in `.github/workflows/ci.yml`
      (they're commented out until the scripts and `e2e/` folder they depend
      on exist — that's now)
- [ ] Push a branch, confirm all four CI jobs go green

## Acceptance

- [ ] `make up` → all six containers healthy
- [ ] `/api/v1/health` returns 200; Swagger renders at `/docs`
- [ ] Frontend renders; `/kitchen-sink` shows all primitives
- [ ] Mailhog reachable at :8025
- [ ] `make test` passes
- [ ] CI green on a real PR
