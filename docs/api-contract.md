# API Contract

**The generated OpenAPI spec is the source of truth, not this file.** Two Makefile
targets dump it, for two different purposes — don't merge them:

- `make api-client` — dumps `docs/openapi.json`, regenerates
  `frontend/src/lib/api.d.ts` from it. Run this after every route change; it's what
  the CI `contract` job checks for staleness.
- `make docs-api` (part of `make docs`) — dumps `docs/generated/openapi.json`, a
  point-in-time snapshot for the report. Run before advisor meetings and submission.

This file exists to fix conventions before the first route is written.

The endpoint list below is derived from SDS Phase II §6, with four corrections applied:
a version prefix, pagination on all list endpoints, one consistent verb convention,
and explicit error codes.

## Conventions

- Base path `/api/v1`. Everything.
- **List endpoints**: `?page=1&size=20` -> `{"items": [...], "total": n, "page": 1, "size": 20}`.
  No unbounded lists. Ever. (Defect #7 in your log was exactly this.)
- **State changes**: `PATCH` on the resource with the new state in the body.
  Sub-resource action endpoints only where a state change isn't the point (e.g. `/retry`).
- Auth: signed, HTTP-only, SameSite=Lax session cookie (`itsdangerous`, keyed on
  `SECRET_KEY`) — not a Bearer JWT. Single server, single frontend origin, no
  third-party API consumers, so a JWT bought nothing but refresh/revocation
  complexity. Decided in US-01; Google tokens never reach the client either way.
- Errors: `{"code": "MACHINE_CODE", "message": "human readable", "details": {...}}`
- Timestamps: ISO 8601 UTC.

Key error codes: `REAUTH_REQUIRED` (409), `JOB_EXPIRED` (410), `JOB_NOT_ACCEPTING` (409),
`DUPLICATE_SUBMISSION` (409), `UNSUPPORTED_FILE_TYPE` (415), `FILE_TOO_LARGE` (413),
`QUOTA_EXCEEDED` (503), `TENANT_FORBIDDEN` (403).

## Auth
| Method | Path | Notes |
|---|---|---|
| GET | `/auth/google/login` | -> redirect to Google consent |
| GET | `/auth/google/callback` | code exchange, upsert recruiter, set session cookie |
| POST | `/auth/logout` | clears the session cookie unconditionally; 204 with or without a session (idempotent) |
| GET | `/auth/me` | profile + `granted_scopes` + `account_state` |
| GET | `/auth/google/reconnect` | US-03 — restarts consent (must redirect the browser, so GET not POST); callback replaces stored tokens |

## Recruiters
| Method | Path | Notes |
|---|---|---|
| PATCH | `/recruiters/me` | `{full_name}` only — `extra="forbid"`, any other field 422s rather than being silently dropped |

## Templates
| Method | Path | Notes |
|---|---|---|
| GET | `/templates` | paginated |
| POST | `/templates` | name + ordered fields; >=1 field required |
| GET | `/templates/{id}` | with fields |
| PUT | `/templates/{id}` | replaces field set wholesale |
| POST | `/templates/{id}/duplicate` | US-05 |
| DELETE | `/templates/{id}` | soft delete; 409 if used by a LIVE job |

## Jobs
| Method | Path | Notes |
|---|---|---|
| GET | `/jobs` | paginated; `?status=LIVE&q=` |
| POST | `/jobs` | JD + template + TTL -> creates Drive folder, `apply_slug`, JD embedding |
| GET | `/jobs/{id}` | detail + counts |
| PATCH | `/jobs/{id}` | JD edit, TTL extend/revoke, `is_accepting_responses` |
| DELETE | `/jobs/{id}` | soft delete, requires confirm flag |
| POST | `/jobs/{id}/process` | 409 unless status=CLOSED and candidates exist |

## Public — no auth
| Method | Path | Notes |
|---|---|---|
| GET | `/public/apply/{slug}` | job title, JD, field definitions. 410 if expired |
| POST | `/public/apply/{slug}` | multipart. Rate-limited by IP |

The only two unauthenticated endpoints in the system. Rate limit them, validate
file type by magic bytes not extension, cap size at 5MB.

## Candidates
| Method | Path | Notes |
|---|---|---|
| GET | `/jobs/{id}/candidates` | raw submissions, paginated, dynamic columns |
| GET | `/jobs/{id}/candidates/ranked` | `?sort=score&min_score=&skill=` |
| GET | `/candidates/{id}` | profile + responses + AI result + resume URL |
| GET | `/candidates/{id}/evidence` | US-23 |
| GET | `/jobs/{id}/candidates/export` | `?format=csv\|xlsx`, UTF-8 BOM (defect #8) |
| PATCH | `/candidates/{id}` | status changes |

## Scheduling
| Method | Path | Notes |
|---|---|---|
| GET / PUT | `/scheduling/preferences` | availability windows |
| POST | `/scheduling/sync-calendar` | free/busy pull; 409 REAUTH_REQUIRED if scope lost |
| GET | `/scheduling/available-slots` | `?job_id=&count=` computed, fresh |
| POST | `/interviews/schedule` | candidate_ids -> slots + Calendar events + Meet links |
| GET | `/interviews` | master schedule, paginated |
| PATCH | `/interviews/{id}` | cancel / reschedule via status |

Re-fetch free/busy immediately before allocation, and conflict-check at event-creation
time. That is TR-05 and defect #4 in one line of policy.

## Email
| Method | Path | Notes |
|---|---|---|
| POST | `/emails/send` | `{type, candidate_ids[], subject?, body?}` — one endpoint |
| GET | `/emails` | history, paginated, `?candidate_id=&type=` |
| GET | `/emails/replies` | classified replies, `?needs_review=true` |
| POST | `/emails/replies/{id}/resolve` | manual intent override |

Collapsed from four endpoints to one typed endpoint. Every send carries an
`idempotency_key`; duplicate keys return 200 with the original log row rather than
sending twice.

## Admin
| Method | Path | Notes |
|---|---|---|
| GET | `/admin/recruiters` | paginated |
| PATCH | `/admin/recruiters/{id}` | `{account_state}` |
| GET | `/admin/api-usage` | `?from=&to=&api_name=` with threshold flags |
| GET | `/admin/tasks` | `?status=FAILED`, paginated |
| POST | `/admin/tasks/{id}/retry` | re-enqueue |
