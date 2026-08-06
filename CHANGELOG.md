# Changelog

## [Unreleased]

### Added
- Backend FastAPI app boots with a working `/api/v1/health` endpoint (TS-00)
- Database bootstrap: Alembic wired up, first migration enables the `pgcrypto` and `vector` Postgres extensions (TS-00)
- Playwright E2E scaffold in `e2e/`, ready for the smoke test once the frontend lands (TS-00)
