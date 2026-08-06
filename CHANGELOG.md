# Changelog

All notable changes to AutoHire. Format based on [Keep a Changelog](https://keepachangelog.com).
Every entry ends with its story ID. Updated by `/wrap` at the end of each session —
an entry here is the difference between work that counts and work that vanishes.

Tag a release at each sprint demo (`v0.3-sprint7`) and move `[Unreleased]` down.

## [Unreleased]

### Added
- Repository scaffold: CLAUDE.md, docs, ADR-001/002/003, Docker stack, design tokens
- `backend/pyproject.toml` — ruff/mypy config, ahead of TS-00 so pre-commit has
  something to run against from the first commit of app code
- `docs/drift.md`: three undocumented rows (`apply_slug`, `email_logs.idempotency_key`,
  `PARSE_ERROR`) that `docs/schema.md` already flagged as ERD additions but that
  hadn't been logged

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
