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
and explicit error codes. Conventions below are settled in `docs/decisions/ADR-004`
— reopen there, not here.

## Conventions

See `docs/decisions/ADR-004-api-conventions.md` for the reasoning behind each of
these. Summary:

- Base path `/api/v1`. Everything. Unauthenticated routes live under
  `/api/v1/public/*` as a separate router (P1).
- **Resources are top-level; relationships are query filters**, except where a child
  cannot exist outside its parent and is never queried across parents (P2).
- **List endpoints** (persisted collections): `?page=1&size=20` ->
  `{"items": [...], "total": n, "page": 1, "size": 20}`. No unbounded lists. Ever.
  (Defect #7 in your log was exactly this.) **Exception**: computed or inherently
  bounded results (e.g. available interview slots) return a bare list — pagination is
  a property of storage, not of every array (P5). Singleton resources are never
  paginated (P6).
- **State changes**: `PATCH` on the resource with the new state in the body. Illegal
  transitions return 409 `INVALID_STATE_TRANSITION`. Sub-resource action endpoints
  exist only for batch/async operations that aren't a state change on one addressable
  resource (P3).
- **Batch/async operations** (job processing, interview scheduling, email dispatch)
  return `TaskOut` with 202 and are polled at `GET /tasks/{task_id}` (P4).
- **Singletons** (`/auth/me`, `/recruiters/me`, `/scheduling/preferences`): `PATCH`
  for partial updates of flat resources, `PUT` for aggregate roots owning an ordered
  child collection (P6).
- Auth: signed, HTTP-only, SameSite=Lax session cookie (`itsdangerous`, keyed on
  `SECRET_KEY`) — not a Bearer JWT. Single server, single frontend origin, no
  third-party API consumers, so a JWT bought nothing but refresh/revocation
  complexity. Decided in US-01; Google tokens never reach the client either way.
- Errors: `{"code": "MACHINE_CODE", "message": "human readable", "details": {...}}`,
  declared in OpenAPI via `responses={}` so it reaches the generated client. A global
  `HTTPException` handler reshapes FastAPI's default `{"detail": ...}` into this (P7).
- **Cross-tenant access**: a resource belonging to another recruiter returns 404, not
  403 — a 403 confirms the resource exists (P8). `TENANT_FORBIDDEN` is retained only
  for cases where ownership is already established but the action isn't permitted.
- Timestamps: ISO 8601 UTC.

Key error codes: `REAUTH_REQUIRED` (409), `JOB_CLOSED` (410), `DUPLICATE_SUBMISSION` (409),
`UNSUPPORTED_FILE_TYPE` (415), `FILE_TOO_LARGE` (413), `QUOTA_EXCEEDED` (503),
`TENANT_FORBIDDEN` (403), `INVALID_STATE_TRANSITION` (409), `TEMPLATE_IN_USE` (409),
`DUPLICATE_TEMPLATE_NAME` (409), `NOT_AUTHENTICATED` (401), `VALIDATION_ERROR` (422, ADR-004 P9).
`JOB_CLOSED` (US-11) replaces the earlier `JOB_EXPIRED`/`JOB_NOT_ACCEPTING` split — one
code, `details: {job_title, reason}` where `reason` is `CLOSED | EXPIRED | PAUSED`, so
the frontend still knows which of the three gating conditions failed without three codes.
Per-resource `{RESOURCE}_NOT_FOUND` codes (`JOB_NOT_FOUND`, `CANDIDATE_NOT_FOUND`, etc.)
follow the obvious pattern and aren't enumerated individually.

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
| PUT | `/templates/{id}` | aggregate root owning an ordered field collection (P6) |
| POST | `/templates/{id}/duplicate` | Phase 2 (US-05) — out of scope |
| DELETE | `/templates/{id}` | soft delete; 409 if used by a LIVE job |

`TemplateFieldIn.field_id` is optional: present means keep the existing field row,
absent means create a new one. This matters because `candidate_form_responses.field_id`
is a foreign key — deleting and recreating fields on every save would cascade away
already-submitted responses. `PUT` reconciles the field set by `field_id` rather than
replacing rows wholesale.

`field_order` is normalized server-side to a 0-based dense sequence on every write
(create and `PUT`), so the client can send any ascending sequence (e.g. `[5, 10, 20]`)
without hitting the `(template_id, field_order)` UNIQUE constraint.

`DELETE /templates/{id}` returns 409 `TEMPLATE_IN_USE` when a non-deleted job posting
references the template (US-06 wired the real check against `job_postings`; drift
row 27 closed).

## Jobs
| Method | Path | Notes |
|---|---|---|
| GET | `/jobs` | paginated; `?status=LIVE&q=` |
| POST | `/jobs` | JD + template + TTL -> creates DRAFT row, then a resume folder, then flips to LIVE. `jd_embedding_id` stays NULL (US-18) |
| GET | `/jobs/{id}` | detail + counts |
| PATCH | `/jobs/{id}` | JD edit, TTL extend/revoke, `is_accepting_responses`, `status` |
| DELETE | `/jobs/{id}` | Phase 2 (US-09/US-10) — out of scope; US-06 explicitly excludes edit/TTL-extend/delete from Phase 1 |
| POST | `/jobs/{id}/process` | async (P4) — 202 `TaskOut`; 409 unless status=CLOSED and candidates exist |

**No close action endpoint.** Closing a job is `PATCH /jobs/{id}` with
`{"status": "CLOSED"}` (P3) — it is a state change on one addressable resource, not a
batch/async operation. Legal transition graph: `DRAFT -> LIVE -> CLOSED -> PROCESSED`.
Any other transition, including skipping a state, is 409 `INVALID_STATE_TRANSITION`.

**Retrying a failed launch is also `PATCH`.** `POST /jobs` commits the row as `DRAFT`
before the resume-folder call; if that call fails, the row stays `DRAFT` and the
response is `RESUME_FOLDER_FAILED` — 502 in cloud mode (an upstream/Drive failure),
500 in local mode (our own filesystem failed). Retry with
`PATCH /jobs/{id} {"status": "LIVE"}`, which runs the same launch logic — one DRAFT
row per attempt, and the original `apply_slug` survives every retry.

`status` is lifecycle; `is_accepting_responses` is a pause/resume toggle *within*
`LIVE` — a recruiter can pause and resume intake without leaving the LIVE state or
losing the `expires_at` countdown. Applications are accepted iff
`status == LIVE AND is_accepting_responses AND now < expires_at`. All three
conditions gate `POST /public/apply/{slug}`; `docs/schema.md` previously left this
ambiguous.

## Public — no auth
| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/public/apply/{apply_slug}` | job title, JD, field definitions. Unknown slug, soft-deleted, or DRAFT → 404. CLOSED/paused/expired → 410 `JOB_CLOSED` |
| POST | `/api/v1/public/apply/{apply_slug}` | multipart. Rate-limited by IP |

The only two unauthenticated endpoints in the system, mounted as a separate
`APIRouter` under `/api/v1/public/*` (P1) so rate limiting and "no auth dependency
here" are enforced at the router level. Rate limit them, validate file type by magic
bytes not extension, cap size at 5MB.

**Not the same URL as the SPA route.** Candidates visit `/apply/{slug}` in the
browser — that's the React app route (ADR-001), not an API endpoint. `JobOut.apply_url`
is the SPA URL (`/apply/{slug}`), never the API path above. Don't conflate the two
when wiring frontend links.

## Candidates
| Method | Path | Notes |
|---|---|---|
| GET | `/jobs/{id}/candidates` | raw submissions, `Page[CandidateOut]`, dynamic columns; `?submission_status=` |
| GET | `/jobs/{id}/candidates/ranked` | `Page[RankedCandidateOut]`, sorted by `rank_position`; `?min_score=&skill=` |
| GET | `/candidates/{id}` | profile + responses + AI result + resume URL |
| GET | `/candidates/{id}/evidence` | Phase 2 (US-23) — out of scope |
| GET | `/jobs/{id}/candidates/export` | `?format=csv\|xlsx`, UTF-8 BOM (defect #8) |
| PATCH | `/candidates/{id}` | status changes |

Candidates that failed parsing are **not** a second list embedded in the ranked
response. They're retrieved from `GET /jobs/{id}/candidates?submission_status=PARSE_ERROR`
— one collection, filtered, per P2/P5. Aggregate counts (total, parsed, ranked,
parse-error) live on `GET /jobs/{id}` detail and on process task status, not on the
ranked endpoint.

## Scheduling
| Method | Path | Notes |
|---|---|---|
| GET / PUT | `/scheduling/preferences` | availability windows; singleton, `PUT` (P6) — see schema note on `available_days` |
| POST | `/scheduling/sync-calendar` | free/busy pull; 409 REAUTH_REQUIRED if scope lost |
| GET | `/scheduling/available-slots` | `?job_id=&count=` — bare list, computed and fresh, not `Page[T]` (P5) |
| POST | `/interviews` | `{job_id, candidate_ids}` -> async (P4), 202 `TaskOut`; slots + Calendar events + Meet links |
| GET | `/interviews` | `Page[InterviewSlotOut]`, cross-job master schedule; `?job_id=&status=` (P2) |
| PATCH | `/interviews/{id}` | cancel / reschedule via status |

Re-fetch free/busy immediately before allocation, and conflict-check at event-creation
time. That is TR-05 and defect #4 in one line of policy.

## Email
| Method | Path | Notes |
|---|---|---|
| POST | `/emails/send` | `{email_type, candidate_ids[], subject?, body?}` — async (P4), 202 `TaskOut` |
| GET | `/emails` | `Page[EmailLogOut]`, cross-job history; `?job_id=&candidate_id=&email_type=` (P2) |
| GET | `/emails/replies` | Phase 2 — out of scope |
| POST | `/emails/replies/{id}/resolve` | Phase 2 — out of scope |

Collapsed from four endpoints to one typed endpoint. Every send carries an
`idempotency_key`; duplicate keys return 200 with the original log row rather than
sending twice.

## Tasks
| Method | Path | Notes |
|---|---|---|
| GET | `/tasks/{task_id}` | `TaskOut` — poll target for every 202 response (P4) |

## Admin
| Method | Path | Notes |
|---|---|---|
| GET | `/admin/recruiters` | paginated |
| PATCH | `/admin/recruiters/{id}` | `{account_state}` |
| GET | `/admin/api-usage` | `?from=&to=&api_name=` with threshold flags |
| GET | `/admin/tasks` | `?status=FAILED`, paginated |
| POST | `/admin/tasks/{id}/retry` | re-enqueue |
