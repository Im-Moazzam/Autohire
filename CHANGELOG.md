# Changelog

## [Unreleased]

### Added
- Repository scaffold: CLAUDE.md, docs, ADR-001/002/003, Docker stack, design tokens
- `backend/pyproject.toml` — ruff/mypy config, ahead of TS-00 so pre-commit has
  something to run against from the first commit of app code
- `docs/drift.md`: three undocumented rows (`apply_slug`, `email_logs.idempotency_key`,
  `PARSE_ERROR`) that `docs/schema.md` already flagged as ERD additions but that
  hadn't been logged
- Frontend scaffold: Vite + React 19 + TypeScript, Tailwind v4 wired to the existing
  `tokens.css` (npm shipped v4 already, no v3-to-config conversion needed), React
  Router with `AppShell` (authenticated) and `PublicLayout` (bare candidate-facing)
  route trees, TanStack Query provider, `src/lib/api.ts` fetch wrapper reading
  `VITE_API_URL` (TS-00)
- 12 UI primitives in `src/components/ui`: Button, Input, Select, Textarea, FileInput,
  DataTable, Modal, StatusBadge, MatchScore, Card, EmptyState, Toast — each stubbing
  loading/disabled/error states per `docs/checklists/ux.md`, tokens only, Modal built
  on the native `<dialog>` element (TS-00)
- `/kitchen-sink` dev-only route rendering every primitive and its states (TS-00)
- Vitest + React Testing Library wired up with one passing test (TS-00)
- `frontend/Dockerfile` (node:20-alpine) (TS-00)

### Changed

### Fixed
- CI: `contract`/`e2e` jobs were live despite a comment saying they were disabled
  pending TS-00; actually commented out, with their two latent env bugs fixed so
  they work once uncommented (TS-00)
- CI: backend coverage gate now matches the documented `app/services`-only policy
  (was `app`, unreachable at TS-00 with no service layer yet)
- docker-compose: `docs-uml`/`docs-tests` output was written to an unmounted
  container path and lost; `./docs` now mounted on `api`
- docker-compose: `web` had no `env_file`, so `VITE_API_URL` never reached Vite
- `.env.example`: added missing `VITE_API_URL`
- `docs/api-contract.md`: referenced a nonexistent `make openapi` target; pointed
  at the two real ones (`api-client`, `docs-api`) and clarified their purposes
- `docs/schema.md`: opening line told sessions to hand-sync this file with the
  ERD, contradicting the code-is-truth model everywhere else in the repo

### Removed
- Google Forms API from the runtime path — see ADR-001
- Backend FastAPI app boots with a working `/api/v1/health` endpoint (TS-00)
- Database bootstrap: Alembic wired up, first migration enables the `pgcrypto` and `vector` Postgres extensions (TS-00)
- Playwright E2E scaffold in `e2e/`, ready for the smoke test once the frontend lands (TS-00)
