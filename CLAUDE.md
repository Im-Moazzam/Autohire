# AutoHire — Claude Code Working Agreement

AI-powered recruitment automation platform. FYP project, Group S26SE012, University of Central Punjab.
Two developers: Moazzam (Scrum Master / Dev), Saif (Full Stack Dev / QA).

## Source of truth

**The code is the source of truth. Documents are generated from it.** See `docs/README.md`.

The academic RS/SDS documents — ERD, class diagram, API table, use cases — are a design
*baseline*, written before implementation. They are directionally right and worth reading,
but they are not binding. Where the baseline and a sensible implementation disagree,
implement the sensible thing and add a row to `docs/drift.md`.

Two exceptions that ARE binding:
- `docs/design.md` — design tokens. Inconsistent UI is not a judgement call.
- `docs/decisions/` — settled questions. Reopen via a new ADR, never silently.

## Read before you write

1. `docs/stories/US-XX.md` — the story you're building. Acceptance criteria are the DoD.
2. `docs/schema.md` and `docs/api-contract.md` — working notes on current shape.
   Treat as orientation, not contract. If they're wrong, fix them and note it.
3. `docs/architecture.md` — layer boundaries and the adapter rule. This one matters.
4. `docs/design.md` + `docs/checklists/ux.md` — for any frontend work.
5. `docs/decisions/` — do not relitigate.

If a requirement is ambiguous, say so and propose the resolution. Do not silently pick
one and build on it — that is how a wrong assumption gets buried under three sprints.

## Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2
- Worker: Celery + Redis
- DB: PostgreSQL 16 + pgvector
- Frontend: React 18, Vite, TypeScript, TailwindCSS, React Router, TanStack Query
- Tests: pytest (backend), Vitest + React Testing Library (frontend)

## Hard rules

**Database**
- Every schema change is an Alembic migration. Never edit a migration that is already merged.
- Never `DROP` a column in the same migration that stops using it. Two-step it.
- Every recruiter-owned table is filtered by `recruiter_id` in the query layer, always.
  Tenant isolation is a security requirement (NFR-06/07), not a nice-to-have.
- Soft-delete jobs and candidates (`deleted_at`), never hard-delete.

**External services**
- Never import `googleapiclient`, `openai`, or `pinecone` outside `backend/app/adapters/`.
  Routes and services depend on the Protocol, never the vendor SDK.
- Every adapter has a `Local*` implementation used when `APP_ENV=local`.
  If you add a method to an adapter Protocol, you add it to both implementations.
- Every Google API call goes through the token-refresh wrapper. On `invalid_grant`,
  set the recruiter to `REAUTH_REQUIRED` and raise `ReauthRequired`. Do not retry blindly.

**API**
- All routes under `/api/v1`.
- Every list endpoint takes `page` and `size` and returns `{items, total, page, size}`.
  No exceptions — unbounded list queries are a known defect class in this project.
- Pydantic response models on every route. No returning ORM objects directly.

**Frontend**
- Use only components from `src/components/ui`. If you need a primitive that doesn't
  exist, build it there first, then use it. Never inline a one-off styled button.
- Use design tokens (`text-primary`, `bg-surface`, `rounded-lg`) — never raw hex or
  arbitrary values like `text-[#2563EB]`.
- Component names follow `docs/design.md` § Component Naming Conventions.

**Secrets**
- Never write a real key into any file. `.env` is gitignored; `.env.example` holds
  placeholder names only. Never print token values in logs or error messages.

## Commits

Conventional commits, always with the story ID:

```
feat(US-06): create Drive folder on job launch
fix(US-12): reject resume uploads over 5MB
test(US-16): add malformed PDF parse cases
docs(ADR-004): record pgvector to Pinecone cutover
```

`git log --oneline` is our audit trail and our sprint evidence. Keep it clean.

See `docs/workflow.md` for the full feature cycle.

## Session discipline

- One story per session. Start fresh (`/clear`) between stories.
- Plan before coding on anything touching the DB, Google APIs, or the AI pipeline.
- End every session with `/wrap`. If you skip it, the work is invisible to the report.

## Definition of Done

1. Acceptance criteria in the story file all pass
2. Tests written and green — asserting the criteria, not merely that code executed
3. Migration reviewed and reversible (if schema changed)
4. UI meets `docs/checklists/ux.md` — all five states, tokens only
5. `make api-client` run and committed if any route changed
6. `CHANGELOG.md` updated; `docs/drift.md` updated if the baseline was departed from
7. Story file status set to Done
8. PR opened against `dev` using `docs/checklists/pr.md`, reviewed by the other developer

## Quality gates

Pre-commit runs ruff, mypy, prettier and gitleaks on every commit. CI runs lint, types,
unit + integration tests, a coverage floor, the frontend build, an API-client staleness
check, and Playwright E2E on every PR. Do not disable a gate to get a PR green — fix the
code, or raise it and change the gate deliberately.

The API-client check exists because frontend/backend contract drift is the most common
way a two-person full-stack team ships broken software. Change a route, run
`make api-client`, commit both. TypeScript then catches the mismatch at compile time
instead of a user finding it.

## Do not

- Do not call the Google Forms API. See `docs/decisions/ADR-001`.
- Do not add a dependency without saying why in the PR description.
- Do not generate placeholder/mock data inside application code. Use fixtures and seeds.
- Do not "improve" the schema mid-story. Raise it, write an ADR, then change it.
