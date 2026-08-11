# ADR-004: Lock API conventions before the Phase 1 stub-route pass

- **Status:** Accepted
- **Date:** 2026-08-12
- **Affects:** all Phase 1 routes, `docs/api-contract.md`, `frontend/src/lib/api.d.ts`

## Context

Phase 1 is 25+ endpoints across 12 remaining stories, built by one backend developer
and consumed by a frontend developer who is currently unavailable and will build
against the generated TypeScript client without being able to ask questions in real
time (see `docs/drift.md` row on the solo review policy). `docs/api-contract.md` and
the draft TS-02 architecture-validation notes disagree with each other in six places.
On a co-located team an inconsistent shape costs a five-minute Slack message. Here it
costs a silent wrong assumption baked into generated types that nobody catches until
the frontend is built.

This ADR settles the shape questions once, before the stub-route pass, so every route
written from here on follows the same rules instead of each being a local judgement
call.

## Decisions

**P1. Base path `/api/v1` for everything.** The only unauthenticated routes live under
`/api/v1/public/*`, mounted as a separate `APIRouter`. Rate limiting and "no auth
dependency in this module" are then enforceable at the router level rather than
per-route vigilance.

**P2. Resources are top-level collections; relationships are query filters.** Nest a
child under a parent only when it cannot exist outside that parent *and* is never
queried across parents. Candidates are nested under jobs (`docs/schema.md`: "a
candidate is scoped to one job"). Interview slots and email logs are top-level with
`?job_id=` filters, because a recruiter has a cross-job master schedule and cross-job
email history.

**P3. State changes are `PATCH` on the resource with the new state in the body.**
Action sub-resource endpoints exist only for batch or asynchronous operations that
are not a state change on one addressable resource. Illegal transitions return 409
`INVALID_STATE_TRANSITION`.

**P4. Every batch or asynchronous operation returns `TaskOut` with 202 and is polled
at `GET /tasks/{task_id}`.** Applies to job processing, interview scheduling, and
email dispatch. One pattern, one polling client on the frontend.

**P5. Persisted collections are paginated with a generic `Page[T]` envelope**
`{items, total, page, size}` and `?page=&size=` query params. Computed or inherently
bounded results (e.g. available interview slots) return a bare list — pagination is a
property of storage, not of every array. Stated explicitly here so it does not read as
drift later.

**P6. Singleton resources** (`/auth/me`, `/recruiters/me`, `/scheduling/preferences`)
are not paginated. `PATCH` for partial updates of flat resources; `PUT` for aggregate
roots that own an ordered child collection, because `PATCH` on an ordered weak entity
has no defined semantics for reorder-and-delete.

**P7. Every error response is `ErrorOut {code, message, details}`**, declared in
OpenAPI via `responses={}` so it reaches the generated TypeScript client. A global
`HTTPException` handler reshapes FastAPI's default `{"detail": ...}` into this shape.
This fixes a current inconsistency: `deps.py` raises `HTTPException(detail=...)` and
`main.py`'s `ReauthRequired` handler returns `{code, message}` — two shapes, neither
declared in the schema.

**P8. A resource belonging to another recruiter returns 404, not 403.** A 403 confirms
the resource exists, which leaks the existence of other recruiters' jobs to an
enumeration attempt. This overrides the `TENANT_FORBIDDEN` 403 entry in
`api-contract.md`; `TENANT_FORBIDDEN` is retained only for cases where ownership is
already established but the action itself is not permitted.

## Consequences

- `docs/api-contract.md` is rewritten to match (see accompanying commit).
- `GET /tasks/{task_id}` is added to the contract — it was missing from every current
  document and P4 makes it load-bearing.
- `INVALID_STATE_TRANSITION` (409) is added to the error code list.
- Any Phase 1 route written before this ADR that doesn't match (job close as an action
  endpoint, ranked/failed candidates as two lists, etc.) is corrected in the same pass.
- Phase 2/3 endpoints already sketched in the contract are marked out of scope rather
  than deleted — they are documented future work per `docs/stories/README.md`.
