# Changelog

## [Unreleased]

### Added
- US-11/US-12 (frontend): built the candidate-facing application form
  (`frontend/src/pages/Apply.tsx`) — was a placeholder stub, so a shared
  job link had nowhere to go. Renders the template's fields by type, submits
  a real multipart application (resume + answers) against the existing
  backend, and covers all five UX states (loading, invalid/closed link,
  form, inline validation errors, success). Added `forwardRef` to
  `Textarea`, `Select`, and `FileInput` (matching the existing `Input`
  pattern) so first-invalid-field focus works across all field types.
  Required fields are marked with a trailing `*` (with a "* fields are
  required" note) instead of labelling optional ones; the job description
  clamps to 4 lines with a "Show more" toggle; the field the backend
  resolves as the email identity field renders as a real `type="email"`
  input with client-side format validation; and a rejected submission now
  highlights the specific field(s) the backend complained about (mapping
  `MISSING_REQUIRED_FIELD` / `UNKNOWN_FIELD` / oversized-response /
  duplicate-email / invalid-email-or-name errors back onto the responsible
  field and focusing it) instead of a generic "invalid submission data"
  banner.
- US-04 (frontend): a new template now starts with "Full Name" and "Email"
  pre-filled as required `SHORT_TEXT` fields instead of one blank field —
  every template needs both to pass identity-field validation, and
  recruiters were hitting that 422 on their first save with no idea why.
- US-06 (frontend): "Copy link" action on the job card (`Jobs.tsx`) and job
  edit screen (`JobBuilder.tsx`) — `apply_url` was returned by the API but
  never surfaced anywhere, so a launched job had no way to actually be
  shared. Added `apply_url` to `JobOut` (previously only on
  `JobDetailOut`) so the list view doesn't need a second fetch per job.
- Shared golden-file contract test for identity-field matching
  (`docs/identity-fields-cases.json`), checked by both
  `backend/tests/test_identity_fields_contract.py` and
  `frontend/src/lib/identityFields.test.ts` — closes GitHub issue #23.
  The matching logic itself moved out of `TemplateBuilder.tsx` into a
  shared `frontend/src/lib/identityFields.ts`, now also used by `Apply.tsx`
  to detect the email field and to map backend validation errors back to
  the right field — one canonical frontend implementation instead of two.

### Changed
- Removed two of the three redundant "Post new job" entry points (sidebar
  button shown on every page, and the Jobs page's empty-state action) —
  the page-header button is now the only one.

### Fixed
- `frontend/vite.config.ts`: enabled polling-based file watching
  (`server.watch.usePolling`). Docker Desktop on Windows doesn't propagate
  inotify events through a bind mount, so the dev server's default watcher
  was silently missing host-side file edits — the file changed on disk but
  HMR never fired, requiring a manual container restart to see anything.
- `backend/app/core/db.py`: added `pool_pre_ping=True` to the SQLAlchemy
  engine — hardening against stale pooled connections in long-lived local
  dev sessions, suspected cause of the intermittent 401 in GitHub issue #24
  (not reproduced after 9 consecutive full-suite runs on fresh containers).
- US-15/16: `resume_parser.extract_text` glued icon-font glyphs directly onto
  adjacent words (e.g. a phone number rendered as an unrenderable codepoint
  immediately followed by the digits, no whitespace) — found on a real resume
  during the manual live-worker smoke test that `task_always_eager` unit tests
  can't reach. Icon fonts (phone/email/location pictograms, common in resume
  templates) map their glyphs into the Unicode Private Use Areas; `pypdf`
  faithfully returns whatever codepoint the font's cmap gives it, but there is
  no real character behind it. Now stripped to a space (not deleted outright,
  so words don't glue together) before the `MIN_CHARS` check. Left in, this
  would have quietly degraded US-18's embeddings on every resume built from a
  template using an icon font.

### Added
- US-06 (frontend): Jobs screens — listing (search + status filter, real
  `submission_count`/`expires_at`-derived "days left") and a launch/edit
  builder — against the real backend from US-06. Template picker binds to
  real data from US-04's Templates screen. `AI process` on each job card
  calls the real `POST /jobs/{id}/process` (US-15/16), disabled when the
  job isn't `LIVE` or has zero applications — no per-row status polling in
  the list, that felt like N+1 territory for a first pass.

  Two deliberate departures from the Figma design, both because the
  backend doesn't support what it shows: no "Save draft" button — `POST
  /jobs` always attempts to go live immediately (`job_service.create_job`
  calls `finalize_launch` unconditionally), there's no API path that
  creates-and-leaves-DRAFT; and no delete/trash action on job cards —
  `DELETE /jobs/{id}` doesn't exist, the real lifecycle action is closing
  (`PATCH {"status": "CLOSED"}`), wired up as "Close job" on the edit
  screen instead. Also skipped the Figma "Active/Expired" tab pair —
  `JobStatus` has no `EXPIRED` value (`assert_job_accepting` derives
  expiry from `expires_at` at request time, never stored as a status) — a
  real `All/Draft/Live/Closed/Processed` filter replaces it, with expiry
  shown per-card instead. Template name isn't shown on job cards either:
  `JobOut` doesn't carry `template_id` or a name, only `JobDetailOut`
  does, and resolving it per row would mean N+1 calls.

  `StatusBadge` (`components/ui`) gained `Live`/`Closed`/`Processed` —
  the job lifecycle isn't representable with its existing values (`Draft`
  was there, the rest weren't). `http.ts`'s `api` client gained `.patch`,
  needed for the first time here.

  The "application deadline" field is a native date input, not Figma's
  preset-days dropdown ("30 Days") — a preset can't round-trip an
  existing job's exact `expires_at` when editing, an exact date can.

  Verified end-to-end against the real backend in the browser: launch,
  edit, status filtering, and the DRAFT->LIVE close transition, all
  against a real Google-authenticated session.
- US-04 (frontend): Templates screen — list, create, edit, delete — built
  against the real CRUD backend from US-04. Also lands the recruiter app
  shell (`Sidebar`, `Header`) that every future authenticated screen hangs
  off: nav items without a route yet (Jobs, Candidates, Scheduling, Emails,
  Settings, Admin Monitoring) render disabled rather than as dead links.
  `AppShell` now gates the whole subtree on a real session (loading/error/
  redirect), so `Dashboard` no longer duplicates that check itself.

  All five UX states covered: loading and error skeletons come from
  `DataTable`'s existing states; empty state on zero templates; a "some
  templates loaded, one action failed" partial case via toast on a failed
  delete without dropping the rest of the list; success via toast + list
  refresh. The builder validates inline — template name on blur, everything
  else (empty field labels, `DROPDOWN`/`MULTIPLE_CHOICE` fields missing
  options, and the identity-fields check mirroring
  `identity_fields.resolve_identity_fields`) on submit — and focuses the
  first invalid field per `docs/checklists/ux.md`'s interaction floor.
  `DUPLICATE_TEMPLATE_NAME` (409) lands on the name field specifically;
  everything else is a form-level banner.

  `Input` (`components/ui`) now forwards its ref — needed to focus the
  first invalid field on a failed submit, and the kind of primitive gap
  `CLAUDE.md` says to fix in the shared component, not work around per-page.

  Verified end-to-end against the real backend: full create/edit
  (`field_id` reconciliation)/delete cycle via a real Google-authenticated
  session, plus every error path (`DUPLICATE_TEMPLATE_NAME`,
  `TEMPLATE_MISSING_IDENTITY_FIELD`, options-required) via `curl` against
  the seeded local recruiter.
- US-01 (frontend): homepage built from the Stitch Figma design (hero,
  features, how-it-works, footer) as a public route outside `AppShell`.
  Login/Sign up/Get started now navigate to the real
  `GET /api/v1/auth/google/login` instead of a stub route. `Dashboard` and
  `AuthError` now check the real session via a new `useCurrentRecruiter()`
  hook against `/auth/me`, resolving a 401 to `null` (logged out) rather
  than throwing, since that's an expected state on these pages, not a fetch
  failure. Fixed a real bug in the fetch wrapper along the way: it was
  missing `credentials: "include"`, so the session cookie set by the API's
  origin (`:8000`) was never sent back from the frontend's origin (`:5173`)
  — every authenticated call would have silently looked logged-out.
  Renamed `frontend/src/lib/api.ts` -> `http.ts` since it collided with the
  generated `api.d.ts` module under TypeScript's module resolution, which
  is what surfaced the bug. `--color-primary` / `--color-primary-soft`
  updated to match the Figma design (`#0058be` / `#d8e2ff`) in both
  `tokens.css` and `docs/design.md`, replacing `#2563eb` / `#eff6ff`.
- US-15/16 (commit 2 — extraction): the `RESUME_PARSE` task's per-candidate body is
  real. `app/services/resume_parser.py` — `extract_text(content, ext) -> str`,
  `pypdf` for PDF, `python-docx` for DOCX (including table-laid-out resumes, not just
  top-level paragraphs — the real DOCX fixture is table-based and top-level-only
  extraction silently returned empty text against it). Fewer than ~50 extracted
  characters (a scanned/image-only PDF) is `ExtractionFailed` with a message distinct
  from a corrupt-file failure — never a silent empty-string `PARSED` row that would
  rank bottom in US-18 (`docs/drift.md` #41, OCR out of scope). A password-protected
  PDF gets its own distinct message too.

  `ResumeStore` gains `fetch_resume(recruiter, candidate) -> bytes` on the Protocol
  and both implementations — extraction never opens a path directly.
  `LocalResumeStore` reuses the same path-containment guard as `store_resume`;
  `DriveResumeStore` is one `google_call` (`GET .../files/{id}?alt=media`).

  Per candidate, in a loop that commits after each one so a single failure can never
  roll back or abort the rest of the batch (**TC-05, the story's headline AC**): fetch
  the resume, sniff its extension from magic bytes (`resume_validation.sniff_extension`
  — never a filename, which doesn't survive in cloud mode either), extract text. Success
  → `resume_text` set, `parse_error` cleared, `SUBMITTED`/`PARSE_ERROR` → `PARSED`.
  Failure → `PARSE_ERROR` with the human-readable message, batch continues. Only
  `SUBMITTED`/`PARSE_ERROR` candidates are selected — a re-trigger after a partial
  failure only retries the failures, never re-parses an already-`PARSED` row.

  Closes `docs/drift.md` row 38: `candidate_service._LEGAL_TRANSITIONS` (mirroring
  `job_service`'s graph) gives `submission_status` a real legality graph for the first
  time — `PATCH /candidates/{id}` now 409s `INVALID_STATE_TRANSITION` on an illegal
  move (e.g. `PARSED` backwards to `SUBMITTED`). The retry AC is itself expressed as a
  graph rule (`PARSED` has no path back to `PARSED`), not just a query filter.

  `candidates.resume_text` migration — `ai_analysis_results` (schema.md's designated
  home) doesn't exist until US-18, so extracted text lives on `candidates` for now
  (`docs/drift.md` #40). One `RESUME_PARSE` task **per job**, not per candidate,
  departs from `architecture.md`'s literal fan-out description (`docs/drift.md` #39) —
  every AC/TC in the story describes a single `background_tasks` row per job.
- US-15/16 (commit 1 — task plumbing): `POST /jobs/{job_id}/process` and
  `GET /jobs/{job_id}/process/status` swap their TS-02 fixture stubs for a real Celery
  task. `background_tasks` migration (`task_type_enum`/`task_status_enum` per
  `docs/schema.md`) plus a partial UNIQUE index on
  `job_id WHERE task_type='RESUME_PARSE' AND status IN ('PENDING','RUNNING')` — the
  actual concurrency guard behind 409 `PROCESSING_IN_PROGRESS`; the enqueue path's
  pre-check (`task_service.active_task_for_job`) is only the fast path, same
  precedent as US-12's `uq_candidates_job_email`. The row is written **on enqueue,
  not on worker start** — committed before `.delay()` is ever called, so a
  worker/broker that never picks up the job still leaves a trace (verified directly:
  a test that makes `.delay()` raise still finds the row `PENDING`).

  `app/tasks/resume_parse.py` — one `RESUME_PARSE` Celery task **per job**, not per
  candidate, departing from `architecture.md`'s literal fan-out description
  (`docs/drift.md`): every AC and test case in the story describes a single
  `background_tasks` row per job. Opens its **own** `SessionLocal()`, never a
  session passed in from a request — same rule `adapters/google/session.py`
  follows. `acks_late=True`, `max_retries=3`, `soft_time_limit`, exponential
  backoff; `autoretry_for` is scoped to transient infrastructure failures only
  (`OperationalError` for now — commit 2 adds the Google-call transient case), never
  broad exceptions, since per-candidate failures are handled in-loop and retrying on
  them would redo already-completed work. Idempotency key is the task's own
  `task_id`: re-running an already-terminal (`SUCCESS`/`FAILED`) task is a no-op.
  Commit 1's per-candidate body is a placeholder (`_process_job_candidates` does
  nothing yet) — real extraction lands in commit 2.

  `GET /process/status` counts are computed from `candidates.submission_status`
  rows, never from task state (AC) — `processed` sums every status downstream of a
  successful parse, `failed` is `PARSE_ERROR`.

  Tests run Celery eagerly (`celery_app.conf.task_always_eager`, opt-in per test via
  a `celery_eager` fixture) — no live worker needed in CI.
- US-13: `GET /jobs/{job_id}/candidates`, `GET /candidates/{id}`, and
  `PATCH /candidates/{id}` swap their TS-02 fixture stubs for real queries — the
  first time a recruiter can see what's actually been submitted. Closes a live
  tenant-isolation gap along the way: `deps.get_owned_candidate` previously
  resolved a candidate from an in-memory dict with **no `recruiter_id` scoping at
  all**; it's now one query joined through the owning job, the only ownership path
  for candidates.

  List and detail are both bounded regardless of page size or answer count — the
  list response carries no `form_responses`, so it never touches
  `candidate_form_responses` or `template_fields`; the detail route joins both in
  one query rather than resolving each response's `field_label` individually.
  `?submission_status=` hits `ix_candidates_job_status`; `?q=` does an
  `ILIKE` over name/email, consistent with `list_jobs`.

  New route, not in the TS-02 contract (`docs/drift.md` row 37):
  `GET /candidates/{id}/resume` — authenticated, ownership-scoped, streams the
  file from `LOCAL_STORAGE_ROOT` after asserting the resolved path is inside the
  job's folder (defence in depth, same precedent as US-12). **Local mode only** —
  `resume_storage_key` is always NULL in cloud mode, so the route inertly 404s
  there and `resume_url` resolves to the Drive `webViewLink` instead; no redirect
  variant was built. `resume_url` is opaque to the client in either mode.
  `Content-Disposition` uses the server-generated stored filename, never anything
  candidate-supplied, and defaults to `attachment` — a malicious PDF can't execute
  in the recruiter's browser origin.

  `PATCH /candidates/{id}` accepts any valid `submission_status` with no legality
  graph (drift row 38) — candidates have no defined transition rules, unlike jobs.

- US-12: `POST /public/apply/{apply_slug}` is real — the biggest attack surface in
  the system, unauthenticated and accepting a file upload. `candidates` and
  `candidate_form_responses` migration per `docs/schema.md`, with a **partial**
  UNIQUE `(job_id, email) WHERE deleted_at IS NULL` (a soft-deleted candidate frees
  its email for re-application, same precedent as US-04's template-name index).
  Closes `docs/drift.md` row 29: `job_service.submission_counts_by_job` /
  `submission_counts_by_status` replace the hardcoded placeholder with real
  `GROUP BY` queries, each scoped to a page or a single job.

  File acceptance (`app/services/resume_validation.py`) never trusts the client:
  type is decided purely from magic bytes (`%PDF-`, the OLE2 header, or a ZIP whose
  entries include `[Content_Types].xml` + `word/*` for `.docx` — a bare ZIP header
  isn't enough, since `.zip`/`.jar` share it), and the 5MB cap is enforced by
  counting bytes as `read_capped` streams them, never by trusting `Content-Length`.
  A best-effort `Content-Length` pre-gate on the route rejects the common
  grossly-oversized case before the body is parsed at all; `read_capped` is what
  actually enforces the cap either way. The stored filename is always
  `{uuid4}.{validated-extension}` — the candidate's raw filename never reaches the
  filesystem or Drive.

  `ResumeStore` gains `store_resume(recruiter, job, filename, content) -> StoredFile`.
  `LocalResumeStore` writes under `LOCAL_STORAGE_ROOT/resumes/{job_id}/`, with a
  resolved-path check as defence in depth against path traversal. `DriveResumeStore`
  does one `multipart/related` upload via `google_call` (not a create-then-patch-media
  two-call sequence, which would double-log `api_usage_logs` for a single upload).
  Ordering matches US-06: the resume is stored *first*, then the candidate row
  commits with the resulting key — a DB failure never leaves a row pointing at a
  file that doesn't exist, and a storage failure leaves no row at all.

  `app/services/identity_fields.py` resolves which template field answers a
  candidate's email/full name by a normalised label match — the single place both
  `template_service` (reject a template missing either at save time, 422
  `TEMPLATE_MISSING_IDENTITY_FIELD`) and `candidate_service` (read the answer at
  submission time) agree on what counts as "the email field". Validating at template
  save time, not just submission time, means a misconfigured template is the
  recruiter's error to fix, not a candidate-facing 500 mid-application.

  `candidate_service.submit_application` calls `job_service.assert_job_accepting`
  (the same US-11 function, not a second copy) before writing anything. An
  unrecognized `field_id` — whether it isn't a UUID at all or belongs to another
  template — is 422 `UNKNOWN_FIELD`, not silently dropped. Free-text responses are
  capped at 5000 characters in Pydantic (`response_value` is unbounded `TEXT`).
  `POST /public/apply/{slug}` is the one `async def` route in the codebase, solely so
  it can `await request.form()` for the `field_id`-keyed parts FastAPI already parsed
  to resolve `resume: UploadFile`; all blocking work (DB, and in cloud mode
  `google_call`'s sleep-based retry) runs via `run_in_threadpool`, since `google_call`
  must never block the event loop.

  Amends two AC numbers from the story text against `docs/api-contract.md`, which
  predates it: the size cap is 5MB, not 10MB, and file-shape rejections are
  413/415, not 422 (`docs/drift.md`).

- US-11: `GET /public/apply/{apply_slug}` — the first unauthenticated, no-session
  endpoint in the system — is real. `job_service.get_job_by_slug` looks up by
  `apply_slug` only (never `job_id`), scoped to non-deleted rows, and
  `assert_job_accepting` holds the single three-condition check
  (`LIVE AND is_accepting_responses AND now < expires_at`) that US-12 will call
  before writing a submission. Unknown slug, soft-deleted, and DRAFT jobs all
  404 identically — a draft is unlaunched, not closed, and a distinguishable
  response would leak that a posting exists before the recruiter shares it.
  CLOSED/paused/expired jobs 410 with a new `JOB_CLOSED` code carrying
  `details: {job_title, reason}` (`reason` ∈ `CLOSED | EXPIRED | PAUSED`),
  replacing the earlier `JOB_EXPIRED`/`JOB_NOT_ACCEPTING` split (`docs/drift.md`
  rows 30–31). Raised as a new `JobNotAccepting` domain exception
  (`app/core/exceptions.py`), mapped to 410 by one handler in `main.py` —
  same pattern as `ReauthRequired` — so the check stays callable outside a
  FastAPI route. `PublicJobOut` exposes only `job_title`, `job_description`,
  `fields`, `is_accepting_responses`, `expires_at`; `TemplateFieldOut.field_id`
  is the one UUID that survives, deliberately, as the FK key US-12's submission
  payload needs.
- US-06: Job launch gets real persistence, the first `google_call`-backed route,
  and the first resource adapter. `job_postings` migration (`job_status_enum`,
  UNIQUE `apply_slug`, `(recruiter_id, status)` index, partial index on
  `expires_at WHERE status = 'LIVE'`). `app/services/job_service.py` holds the
  launch logic: `POST /jobs` commits the row as `DRAFT` first, then calls
  `ResumeStore.create_job_folder` outside any open transaction, then flips the
  row to `LIVE` — no DB transaction is ever held open across the network call.
  A failed folder creation leaves the row `DRAFT` and returns `RESUME_FOLDER_FAILED`
  (502 in cloud mode, 500 in local — an upstream failure and our own failure aren't
  the same thing); retrying is `PATCH /jobs/{id} {"status": "LIVE"}`, which runs the
  same launch function and never mints a second `apply_slug` for the same job.
  Closing a job is `PATCH {"status": "CLOSED"}`, not a `/close` action endpoint
  (ADR-004 P3). New `ResumeStore` Protocol (`app/adapters/base.py`) with
  `LocalResumeStore` (`{LOCAL_STORAGE_ROOT}/resumes/{job_id}/`, new setting —
  defaults to `/storage`, the docker-compose mount; overridable for CI/host runs
  that aren't in that container) and `DriveResumeStore` (via
  `google_call`, never `googleapiclient` or raw `httpx`), selected by `APP_ENV`.
  `get_owned_job` and `candidates.py` now return/consume a real `JobPosting` ORM
  row instead of a fixture dict. `TEMPLATE_IN_USE` (409) on `DELETE /templates/{id}`
  is now enforced against `job_postings` (closes `docs/drift.md` row 27).
  `submission_count`/`submission_counts` are a placeholder constant, not a query —
  `candidates` doesn't exist until US-12/US-13 (`docs/drift.md` row 29). JD
  embedding deferred to US-18 (`docs/drift.md` row 28).
- US-04: Application templates get real persistence. `form_templates` and
  `template_fields` migration (partial UNIQUE `(recruiter_id, template_name)
  WHERE deleted_at IS NULL`; UNIQUE `(template_id, field_order)`; `field_type_enum`).
  `app/services/template_service.py` holds all logic — routes are thin. `POST`
  creates the template and its fields in one transaction (any DB-level failure,
  unique violation or otherwise, rolls back the whole insert and the session
  cleanly, so a bad field never leaves an orphaned template row — TC-10). `PUT`
  (not `PATCH` — ADR-004 P6) reconciles the full field set by `field_id` rather
  than delete-and-recreate, since `candidate_form_responses.field_id` is an FK.
  `field_order` is normalized server-side to a dense 0-based sequence on every
  write; reordering existing rows on `PUT` bumps them out of range first since
  the order constraint isn't deferrable. `DELETE` soft-deletes (`deleted_at`),
  freeing the name for reuse. Cross-tenant access is 404, not 403 (ADR-004 P8).
  Added `DUPLICATE_TEMPLATE_NAME` (409) to the error-code list — additive, not a
  shape change; TS-02's `TemplateOut` shape was checked against `docs/schema.md`
  and needed no changes. `TEMPLATE_IN_USE` (409) stays declared on `DELETE` but is
  not enforced yet — `job_postings` doesn't exist until US-06 (`docs/drift.md`
  row 27).
- TS-02: Phase 1 stub-route contract. All 24 remaining Phase 1 endpoints now exist
  with real route signatures, exact Pydantic response models, and fixture data —
  Saif can build all 15 screens against real generated types before any backend
  logic lands. Four shared primitives every route uses:
  `app/schemas/common.py` (`Page[T]`/`PaginationParams`/`ErrorOut`/`error_responses()`),
  three global exception handlers in `main.py` (`HTTPException` — registered on
  `starlette.exceptions.HTTPException` so routing-level 404/405s are covered too,
  not just `fastapi.HTTPException` — `RequestValidationError`, and `ReauthRequired`,
  all emitting `ErrorOut`; `extra="forbid"` violations get `code="VALIDATION_ERROR"`
  with per-field Pydantic errors preserved under `details`, not flattened),
  `get_owned_job`/`get_owned_candidate`/`get_owned_template` in `app/api/deps.py`
  (stub bodies validate against fixtures; real `recruiter_id` scoping lands with
  each owning story — the `recruiter` dependency is already in the signature so
  that story doesn't change it), and `app/api/fixtures.py` (all stub data in one
  module, including every documented failure state: a `PARSE_ERROR` candidate, an
  expired apply slug, a paused apply slug, an illegal job transition, a `FAILED`
  email, a `CANCELLED` interview slot, and a slot with a null `google_meet_link`).
  `deps.py`'s 401 now carries `code="NOT_AUTHENTICATED"`; the existing
  `ReauthRequired` handler moved onto the same `ErrorOut` model (its body gains a
  `"details": null` key — `test_google_session.py`'s TC-03 assertion updated to
  match, per ADR-004). All enums (`FieldType`, `JobStatus`, `SubmissionStatus`,
  `SlotStatus`, `EmailType`, `DeliveryStatus`, `TaskType`, `TaskStatus`, `Weekday`)
  are real `StrEnum`s in `app/schemas/enums.py`, surfacing to `api.d.ts` as TS union
  types. `resume_url` and `apply_url` are computed, never columns — `apply_url` is
  `f"{PUBLIC_APPLY_BASE_URL}/{apply_slug}"` (ADR-004 P10; the env var already ends
  in `/apply`, so no second segment is appended). Public apply routes
  (`GET`/`POST /api/v1/public/apply/{apply_slug}`) live on their own `APIRouter`
  with zero `get_current_recruiter` anywhere in the module — asserted structurally
  in `test_stub_common.py`, not just by convention. `Page[T]` uses legacy
  `TypeVar`/`Generic` syntax, not PEP 695 — the pinned `mypy==1.11.2` pre-commit
  hook rejects PEP 695 generics, so ruff's UP046/UP047 autofix is suppressed with
  `noqa` and a comment naming the pin. It still serializes to OpenAPI as
  `Page_JobOut_`-style names (Pydantic v2's default generic-schema naming) —
  expected, not accidental. Every handler carries `# STUB: US-XX`. Not stubbed, by
  design: `DELETE /jobs/{id}` (Phase 2, US-09/10 — excluded from Phase 1 by US-06
  itself) and the Phase 2/3 endpoints TS-02 already named out of scope
  (`/templates/{id}/duplicate`, `/candidates/{id}/evidence`,
  `/jobs/{id}/candidates/export`, `/emails/replies*`, `/admin/*`,
  `/scheduling/sync-calendar`). 73 tests total (up from 30): one file per contract
  section plus `test_stub_common.py` for the cross-cutting rules (pagination shape,
  401/404/409/422 all matching `ErrorOut`, cross-tenant 404-not-403, public router
  has no auth dependency). `mise run db:seed` now seeds one fake recruiter through
  the real `upsert_recruiter` path — the same fake-token/userinfo shape
  `tests/conftest.py`'s `authed_client` uses, so the seeded row matches what
  production login produces rather than being a parallel mock — and prints a ready
  session cookie, so the stub routes can be exercised manually without real Google
  OAuth credentials.
- US-02: Logout and profile update. `POST /api/v1/auth/logout` clears the
  session cookie unconditionally (no `get_current_recruiter` dependency, so
  it's idempotent with or without a session) with the same `httponly`/
  `samesite=lax`/`path=/` attributes it was set with — a mismatch there is the
  classic way a "logout" silently fails to clear the cookie. Safe without CSRF
  protection because `SameSite=Lax` already stops a cross-site POST from
  carrying the cookie. `PATCH /api/v1/recruiters/me` updates `full_name` only;
  `RecruiterUpdate` uses `extra="forbid"` so attempting `email` or
  `account_state` 422s loudly instead of being silently dropped. `RecruiterOut`
  (`/auth/me`) now includes `granted_scopes`, closing a gap between it and
  `docs/api-contract.md` — needed for the reconnect banner to name which
  permission is missing. Confirmed `last_login_at` (written since US-01) is
  actually covered by a test, since it wasn't. 7 new tests (TC-01 through
  TC-05 plus the `last_login_at` gap-closer).
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
  `make api-client` for all 24 TS-02 endpoints; `docs/api-contract.md` corrected to
  match what was actually built: ranked-candidates has no `?sort=` param (sort is
  implicit by `rank_position`), and email send/list use `email_type`, not `type`
  (TS-02)
- `docs/openapi.json` and `frontend/src/lib/api.d.ts` regenerated via
  `make api-client` for `/auth/logout`, `PATCH /recruiters/me`, and the
  `granted_scopes` field on `RecruiterOut` (US-02)
- `docs/api-contract.md`: dropped `POST /auth/refresh`, its own note already
  said "not needed with cookie sessions; drop or repurpose in US-02" and
  nothing repurposed it; added the `## Recruiters` section (US-02)
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
