# Changelog

## [Unreleased]

### Added
- US-03: Google token refresh + reconnect. `app/adapters/google/session.py` —
  `google_call()`, the wrapper every future Google-calling route goes through:
  decrypts + refreshes the access token (60s skew), retries 429/5xx with
  exponential backoff and 401 with a forced refresh sharing one 3-attempt
  budget (not a bonus retry on top of it), raises `ReauthRequired` on
  `invalid_grant` after flipping `account_state`, and writes exactly one
  `api_usage_logs` row per call with `call_count` = attempts made. Token
  persistence and usage logging each use their own short-lived DB session,
  never the caller's, so a route mid-transaction can't have this partial work
  rolled back with it. `app/core/exceptions.py` (`ReauthRequired`) and one
  `@app.exception_handler` in `main.py` convert it to 409
  `{"code": "REAUTH_REQUIRED"}` — no per-route try/except. `api_usage_logs`
  table + `api_name_enum` migration (`GOOGLE_DRIVE`/`GOOGLE_GMAIL`/
  `GOOGLE_CALENDAR`/`OPENAI` — `PINECONE` omitted, see `docs/drift.md` #16).
  `GET /api/v1/auth/google/reconnect` restarts consent for the logged-in
  recruiter, reusing US-01's browser-bound CSRF state cookie; the existing
  `/google/callback` + `upsert_recruiter` already replace tokens and retain
  the existing refresh token when Google omits a new one. 18 new tests
  (TC-01 through TC-09, the unified-retry-budget and pre-check cases, plus
  two covering caller-supplied headers and refresh-avoidance on reuse).
  Also verified end-to-end against real Google on 2026-08-11 (forced token
  expiry, forced `invalid_grant` via revoking access at
  myaccount.google.com/permissions, and a live reconnect) via a throwaway
  scratch script, deleted after use — see `docs/stories/US-03.md`.
- US-01: `frontend/src/pages/Dashboard.tsx` and `AuthError.tsx` — placeholder
  redirect targets for the OAuth callback's success/failure paths, wired into
  `router.tsx`. Added to unblock manual end-to-end verification against real
  Google OAuth; Saif replaces both with real screens.
- `.mise.toml`: task set mirroring the Makefile (`up`, `down`, `db:migrate`,
  `db:revision`, `db:seed`, `test`, `lint`, `api-client`, `docs`, `reset`, etc.)
  so the team isn't dependent on `make`, which isn't available by default on
  Windows/PowerShell
- US-01: Google OAuth sign-up. `recruiters` table + migration (`account_state`
  enum `ACTIVE`/`SUSPENDED`/`REAUTH_REQUIRED`, `google_token_expires_at`,
  nullable `google_refresh_token`); `app/adapters/google/oauth.py` (httpx-only,
  no vendor SDK) for the authorize URL, code exchange, and userinfo lookup;
  `app/services/auth_service.py` for browser-bound state (signed nonce + cookie,
  not signed-state-alone, to close a login-CSRF hole), the signed session
  cookie, and recruiter upsert with a granted-vs-required scope check that sets
  `REAUTH_REQUIRED` on partial consent; `GET /api/v1/auth/google/login`,
  `GET /api/v1/auth/google/callback`, `GET /api/v1/auth/me`; Fernet
  encrypt/decrypt helper in `app/core/crypto.py`; CORS middleware in `main.py`
  (cookie auth needs `allow_credentials` + an explicit frontend origin, which
  didn't exist yet); 9 tests covering all 5 story test cases plus the
  partial-scope case and a token-leak assertion
- `backend/requirements.txt`: `httpx` (Google OAuth HTTP calls), `cryptography`
  (Fernet), `itsdangerous` (signed state + session cookie)
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
- Wire-up: `docs/openapi.json` and `frontend/src/lib/api.d.ts` generated via
  `make api-client` (first real run of this target) and committed; empty
  `backend/app/services/` package added ahead of the first service (TS-00)

### Changed
- `docs/openapi.json` and `frontend/src/lib/api.d.ts` regenerated via
  `make api-client` for `/auth/google/reconnect` (US-03)
- `docs/openapi.json` and `frontend/src/lib/api.d.ts` regenerated via
  `make api-client` for the three new auth routes (US-01)
- `docs/schema.md`: `api_name_enum` drops `PINECONE` (US-03, drift #16)
- `docs/api-contract.md`: `/auth/google/reconnect` corrected to GET — it has
  to redirect a browser into Google's consent screen (US-03, drift #17)
- `backend/pyproject.toml`: ruff ignores `B008` — FastAPI's `Depends()`/`Query()`/
  `Cookie()`-in-default-argument pattern is documented and correct, not the bug
  the rule assumes
- `backend/Dockerfile` installs `requirements-dev.txt` (which pulls in
  `requirements.txt`) instead of runtime-only deps, so `make test`'s
  `docker compose exec api pytest` has pytest/ruff/mypy available in the
  image (TS-00)
- CI: `contract` and `e2e` jobs uncommented in `.github/workflows/ci.yml`,
  now that the scripts and `e2e/` folder they depend on exist (TS-00)

### Fixed
- Backend coverage gate (`--cov=app/services --cov-fail-under=70`) had no
  `app/services` package to measure, so it always failed 0% regardless of
  test count; added the (currently empty) package so the gate has a valid
  target ahead of the first real service (TS-00)
- `.prettierignore` added for `frontend/src/lib/api.d.ts` — prettier was
  reformatting the openapi-typescript output on every commit, which would
  have made the `contract` CI job's raw diff fail on every future
  `make api-client` regenerate (TS-00)
- CI: `backend` job's `TOKEN_ENCRYPTION_KEY: ${{ steps.fernet.outputs.key }}`
  was set in job-level `env:`, which GitHub Actions evaluates before any
  step runs — `steps.*` isn't valid there, so every push touching this repo
  has failed CI instantly regardless of code correctness, since before
  TS-00. Fixed by writing the key to `$GITHUB_ENV` from the fernet step
  instead; same bug fixed in the newly-uncommented `contract` job (TS-00)
- `backend/requirements-dev.txt` pins `mypy==2.3.0` for reproducible CI runs
- `backend/pyproject.toml` mypy config: added a `celery.*` override for
  `ignore_missing_imports` — global `ignore_missing_imports` doesn't cover
  the "installed but no py.typed marker" case celery hits (TS-00)
- CI's `mypy backend/app` ran from the repo root, where mypy's config
  discovery never finds `backend/pyproject.toml` (it only searches cwd, not
  the target path) — so the `pydantic.mypy` plugin, the `celery.*` override,
  and every other mypy setting were silently not applied, surfacing a
  spurious `call-arg` error on `Settings()` and an unsuppressed celery
  import-untyped warning. Fixed by passing
  `--config-file backend/pyproject.toml` explicitly; same fix applied to the
  pre-commit mypy hook, which had the identical blind spot (TS-00)
- CI: `e2e` job never ran `npm ci` in `e2e/` before `npx playwright test`,
  so every run failed immediately with `Cannot find module '@playwright/test'`
  regardless of the smoke test itself (TS-00)
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
