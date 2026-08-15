# TS-02: Phase 1 stub-route contract

- **Status:** Done
- **Backend:** Moazzam · **Frontend consumer:** Saif
- **Points:** 5
- **Depends on:** US-02 (done), ADR-004 (API conventions)
- **Target: committed by 2026-08-23**

## Why this exists

Saif is unavailable and all backend is on one developer. If the frontend can only be
started once each backend story is finished, the two halves are fully serialized
against a fixed end-of-September deadline — and every integration bug surfaces in the
last two weeks.

This story lands the **route signature and Pydantic response model for every remaining
Phase 1 endpoint**, returning hardcoded fixture data. `make api-client` then produces a
complete `api.d.ts`, and all 15 screens become buildable immediately, in any order,
against real TypeScript types. Real logic fills in behind these signatures story by
story without the frontend changing.

This is `docs/workflow.md`'s contract-first parallelism. It is now mandatory.

## Decided before the session (don't reopen)

All eight are recorded in **ADR-004**; they are restated here so the session does not
have to infer them. Where this file and `docs/api-contract.md` ever disagree,
`api-contract.md` wins and the difference is a `drift.md` row.

1. **`/api/v1` on everything.** The only unauthenticated routes live under
   `/api/v1/public/*`, on their own `APIRouter`.
2. **Top-level resources, filters not nesting.** Nest only where the child cannot
   exist outside the parent *and* is never queried across parents. Candidates nest
   under jobs; interview slots and email logs do not.
3. **State changes are `PATCH`.** No `/close`, no `/activate`. Action endpoints only
   for batch/async work. Illegal transitions → 409 `INVALID_STATE_TRANSITION`.
4. **Batch/async → `TaskOut` 202, polled at `GET /tasks/{task_id}`.** Job processing,
   interview scheduling, and email dispatch all use this one pattern.
5. **Persisted collections are `Page[T]`.** Computed/bounded results
   (`/scheduling/available-slots`) return a bare list — this exception is deliberate,
   not drift.
6. **Singletons aren't paginated.** `PATCH` for flat partial updates; `PUT` for
   aggregate roots owning an ordered child collection (templates).
7. **Errors are `ErrorOut {code, message, details}`,** declared in OpenAPI on every
   route via `responses={}` so they reach `api.d.ts`.
8. **Cross-tenant access returns 404, not 403.**

## Rules for this story

- **Signatures and response shapes only.** No business logic, no migrations, no Google
  calls, no Celery. Every handler returns a fixture from `app/api/fixtures.py`.
- **Every route carries its real `get_current_recruiter` dependency** except the two
  public apply endpoints. Auth behaviour must be real from day one — it's the thing
  Saif's routing depends on.
- **Response models must be exact.** Field names come from `docs/schema.md`. A wrong
  field name here costs Saif a rewrite later; that's the whole risk of this story.
- Every handler body gets `# STUB: US-XX` so the story that replaces it is greppable.
- Enum values come from `docs/schema.md` §Enums and must be **real Python enums**, not
  `str` — Saif needs the union types for exhaustive switch handling. This includes
  `available_days`, which uses the new weekday enum, not bare strings.
- Fixtures must be *realistic*: 2–3 items in lists, at least one row in a failure
  state, never an empty array. Empty or all-green fixtures let the frontend skip its
  empty and partial-failure states, which is exactly what `docs/checklists/ux.md`
  cares most about.

## Build these four primitives first, before any route

Twelve stories will each need these. Building them once here is the point of doing
TS-02 before US-04.

### 1. `Page[T]` — `app/schemas/common.py`
Generic Pydantic model `{items: list[T], total: int, page: int, size: int}` plus a
reusable `PaginationParams` dependency (`page` ≥ 1 default 1, `size` 1–100 default 20).
Every list endpoint below uses it.

### 2. `ErrorOut` + global handler — `app/schemas/common.py`, `app/main.py`
`{code: str, message: str, details: dict | None}`. Add an
`@app.exception_handler(HTTPException)` that reshapes FastAPI's default
`{"detail": ...}` into it, and give `deps.py`'s 401 a real code
(`NOT_AUTHENTICATED`). Align the existing `ReauthRequired` handler to the same model.
Attach `responses={401: ..., 404: ..., 409: ...}` to routes so the shapes reach
`api.d.ts` — today Saif has no typed errors at all.

### 3. `get_owned_job(job_id, recruiter)` — `app/api/deps.py`
The tenancy dependency every job-scoped route uses. In stub form it validates the UUID
and 404s on an unknown fixture id; the real query lands in US-06. Add
`get_owned_candidate` and `get_owned_template` alongside it. Twelve stories hand-rolling
their own ownership check is twelve chances to forget one.

### 4. `app/api/fixtures.py`
All fixture data in one module, imported by routes. Not inline constants scattered
across route files — this makes stub removal mechanical and makes one grep prove it's
complete.

---

## Endpoints

### Templates — US-04

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/templates` | — | `Page[TemplateOut]` |
| POST | `/templates` | `TemplateCreate` | `TemplateOut` 201 |
| GET | `/templates/{template_id}` | — | `TemplateOut` |
| PUT | `/templates/{template_id}` | `TemplateReplace` | `TemplateOut` |
| DELETE | `/templates/{template_id}` | — | 204 |

- `TemplateOut`: `template_id`, `template_name`, `fields: list[TemplateFieldOut]`,
  `created_at`, `updated_at`.
- `TemplateFieldOut`: `field_id`, `field_label`, `field_type` (`FieldType` enum),
  `is_required`, `field_order`, `options: list[str] | None`.
- `TemplateFieldIn`: same minus timestamps, **with `field_id: UUID | None`** — present
  means keep that existing field row, absent means create a new one. This is
  load-bearing: `candidate_form_responses.field_id` is an FK, so delete-and-recreate on
  every save would cascade away submitted responses.
- `PUT` replaces the field set wholesale; at least one field required.
- `DELETE` is a soft delete → 409 `TEMPLATE_IN_USE` if referenced by a LIVE job.
  Give the fixture path for both outcomes.

### Jobs — US-06

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/jobs?status=&q=` | — | `Page[JobOut]` |
| POST | `/jobs` | `JobCreate` | `JobDetailOut` 201 |
| GET | `/jobs/{job_id}` | — | `JobDetailOut` |
| PATCH | `/jobs/{job_id}` | `JobUpdate` | `JobDetailOut` |

- `JobOut` (list row): `job_id`, `job_title`, `status` (`JobStatus`),
  `is_accepting_responses`, `expires_at`, `submission_count`, `created_at`.
- `JobDetailOut` adds: `job_description`, `template_id`, `apply_slug`, `apply_url`,
  `google_drive_folder_id: str | None`, `updated_at`, and
  `submission_counts: dict[SubmissionStatus, int]` — the counts that let Saif render
  "18 ranked, 3 failed to parse" without a second request.
- `apply_url` is **computed** as `f"{PUBLIC_APPLY_BASE_URL}/{apply_slug}"` — the
  **SPA** route a candidate opens in a browser, not the API path. `PUBLIC_APPLY_BASE_URL`
  already embeds the `/apply` segment (`http://localhost:5173/apply`); do not append
  it again (ADR-004 P10). Saif never builds this string.
- `JobUpdate` (`extra="forbid"`): `job_title`, `job_description`, `expires_at`,
  `is_accepting_responses`, `status`. Closing a job is `{"status": "CLOSED"}`.
  Legal transitions: `DRAFT → LIVE → CLOSED → PROCESSED`. Anything else is 409
  `INVALID_STATE_TRANSITION` — give that a fixture path.

### Public apply — US-11, US-12 (own router, **no auth dependency**)

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/public/apply/{apply_slug}` | — | `PublicJobOut` |
| POST | `/public/apply/{apply_slug}` | multipart: `resume` + field responses | `ApplySuccessOut` 201 |

- `PublicJobOut` exposes **only** `job_title`, `job_description`,
  `fields: list[TemplateFieldOut]`, `is_accepting_responses`, `expires_at`. No
  recruiter identity, no job id, no counts.
- `ApplySuccessOut`: `submitted_at`, `message`. **No `candidate_id`** — an internal
  UUID has no business reaching an unauthenticated caller, and the same reasoning
  already governs `PublicJobOut`.
- Accepting applications requires `status == LIVE AND is_accepting_responses AND
  now < expires_at`. Unknown slug → 404 `JOB_NOT_FOUND`. Expired → 410 `JOB_EXPIRED`.
  Paused or closed → 410 `JOB_NOT_ACCEPTING`. Fixture path for each — a closed job is
  a state Saif renders, not an error toast.
- Declare `413 FILE_TOO_LARGE` and `415 UNSUPPORTED_FILE_TYPE` in `responses={}` even
  though the stub does not enforce them, so the client is typed for US-12.

### Candidates — US-13, US-19

| Method | Path | Response |
|---|---|---|
| GET | `/jobs/{job_id}/candidates?submission_status=&q=` | `Page[CandidateOut]` |
| GET | `/jobs/{job_id}/candidates/ranked?min_score=&skill=` | `Page[RankedCandidateOut]` |
| GET | `/candidates/{candidate_id}` | `CandidateDetailOut` |
| PATCH | `/candidates/{candidate_id}` | `CandidateDetailOut` |

- `CandidateOut`: `candidate_id`, `full_name`, `email`, `phone_number`,
  `submission_status` (`SubmissionStatus`), `submitted_at`, `parse_error: str | None`,
  `resume_url: str | None`.
- `RankedCandidateOut` extends it with `rank_position`, `semantic_score: float`,
  `matched_skills: list[str]`, `missing_skills: list[str]`,
  `ai_feedback_summary: str | None`.
- `CandidateDetailOut` extends `CandidateOut` with
  `form_responses: list[FormResponseOut]` where `FormResponseOut` is
  `field_id`, `field_label`, `field_type`, `response_value: str | None`. **`field_id`
  and `field_type` are required** — labels aren't unique or stable, and Saif can't pick
  a renderer without the type.
- `CandidateUpdate` (`extra="forbid"`): `submission_status` only.
- `resume_url` is **computed** from `resume_drive_url` or `resume_storage_key`
  depending on `APP_ENV`.
- **Fixtures must include at least one `PARSE_ERROR` candidate with a populated
  `parse_error`**, reachable via the `?submission_status=PARSE_ERROR` filter. Failed
  candidates are a filter over this one collection — not a second list bolted onto the
  ranked response.

### AI processing — US-15, US-16

| Method | Path | Response |
|---|---|---|
| POST | `/jobs/{job_id}/process` | `TaskOut` 202 |
| GET | `/jobs/{job_id}/process/status` | `ProcessStatusOut` |

- `TaskOut`: `task_id`, `task_type` (`TaskType`), `status` (`TaskStatus`),
  `started_at`, `completed_at: datetime | None`, `error_message: str | None`.
- `ProcessStatusOut`: `status` (`TaskStatus`), `total: int`, `processed: int`,
  `failed: int`, `error_message: str | None`. These three counts are **computed** over
  `candidates.submission_status` — there are no such columns. `failed` is separate from
  `processed` deliberately; it's what lets Saif show "18 ranked, 3 failed" instead of
  silently dropping rows.
- 409 `INVALID_STATE_TRANSITION` unless the job is CLOSED and has candidates.

### Tasks — shared

| Method | Path | Response |
|---|---|---|
| GET | `/tasks/{task_id}` | `TaskOut` |

The single polling endpoint behind every 202. Missing from every prior document;
ADR-004 P4 makes it load-bearing.

### Scheduling — US-24, US-26

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/scheduling/preferences` | — | `SchedulingPreferencesOut` |
| PUT | `/scheduling/preferences` | `SchedulingPreferencesIn` | `SchedulingPreferencesOut` |
| GET | `/scheduling/available-slots?job_id=&count=` | — | `list[AvailableSlotOut]` |
| POST | `/interviews` | `{job_id, candidate_ids: list[UUID]}` | `TaskOut` 202 |
| GET | `/interviews?job_id=&status=` | — | `Page[InterviewSlotOut]` |
| PATCH | `/interviews/{slot_id}` | `InterviewSlotUpdate` | `InterviewSlotOut` |

- `SchedulingPreferencesOut`: `preference_id`, `available_days: list[Weekday]`,
  `available_start_time: time`, `available_end_time: time`,
  `slot_duration_minutes: int`, `last_synced_at: datetime | None`.
  `SchedulingPreferencesIn` is the same minus `preference_id` and `last_synced_at`.
  Reject `available_start_time >= available_end_time` with 422.
- `AvailableSlotOut`: `starts_at`, `ends_at`. Computed and bounded by `count` —
  **not paginated**, per ADR-004 P5.
- `InterviewSlotOut`: `slot_id`, `candidate_id`, `candidate_name`, `job_id`,
  `scheduled_at`, `duration_minutes`, `status` (`SlotStatus`),
  `google_meet_link: str | None`.
- `InterviewSlotUpdate` (`extra="forbid"`): `status`, `scheduled_at`,
  `reschedule_reason`. Cancel and reschedule are both PATCH.
- Fixture must include one `CANCELLED` or `DECLINED` slot and one with a null
  `google_meet_link`.

### Email — US-27

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/emails/send` | `{email_type, candidate_ids: list[UUID], subject?, body?}` | `TaskOut` 202 |
| GET | `/emails?job_id=&candidate_id=&email_type=` | — | `Page[EmailLogOut]` |

- `EmailLogOut`: `email_id`, `candidate_id`, `candidate_name`, `email_type`
  (`EmailType`), `subject`, `body_preview: str | None`,
  `delivery_status` (`DeliveryStatus`), `sent_at`, `is_automated`.
- Fixture must include one `FAILED` delivery.

---

## Acceptance criteria

- [x] `Page[T]`, `ErrorOut` + global handler, the three ownership dependencies, and
      `app/api/fixtures.py` exist and are used by every route below
- [x] Every endpoint above exists, returns its fixture, and appears in `/docs` with the
      correct response model
- [x] Every list endpoint returns `Page[T]` with working `?page=&size=`; the two
      documented exceptions (`/scheduling/available-slots`, singletons) return bare shapes
- [x] Authenticated routes 401 with an `ErrorOut` body; the two public apply routes do not
- [x] Cross-tenant / unknown ids return 404, never 403
- [x] All enums are real Python enums surfacing as TS union types, not bare strings —
      including `Weekday`
- [x] Failure fixtures exist and are reachable: `PARSE_ERROR` candidate, expired job,
      paused job, `INVALID_STATE_TRANSITION`, `FAILED` email, cancelled slot
- [x] `make api-client` regenerated; `docs/openapi.json` and
      `frontend/src/lib/api.d.ts` committed
- [x] `docs/api-contract.md` matches the built routes exactly (two corrections found
      and applied: no `?sort=` on ranked candidates, `email_type` not `type`)
- [x] One smoke test per route asserting status code and response shape, plus one test
      proving auth is enforced on private routes and absent on public ones
- [x] Every stub handler is greppable via `# STUB: US-XX`

## Test cases

| ID | Scenario | Expected |
|---|---|---|
| TC-01 | Any list endpoint without params | 200, `{items, total, page, size}`, non-empty items |
| TC-02 | Any list endpoint with `?size=1` | 200, exactly one item, `total` unchanged |
| TC-03 | Any private route without a session cookie | 401, body matches `ErrorOut` |
| TC-04 | `GET /public/apply/{slug}` without a cookie | 200 |
| TC-05 | `GET /public/apply/{unknown}` | 404 `JOB_NOT_FOUND` |
| TC-06 | `GET /public/apply/{expired-slug}` | 410 `JOB_EXPIRED` |
| TC-07 | `GET /public/apply/{paused-slug}` | 410 `JOB_NOT_ACCEPTING` |
| TC-08 | `GET /jobs/{job_id}/candidates?submission_status=PARSE_ERROR` | 200, ≥1 item with non-null `parse_error` |
| TC-09 | `PATCH /jobs/{id}` with an illegal transition | 409 `INVALID_STATE_TRANSITION` |
| TC-10 | Any `*Update` schema with an unknown field | 422 (`extra="forbid"`) |
| TC-11 | `GET /jobs/{unknown_id}` | 404, not 403 |
| TC-12 | `POST /jobs/{id}/process`, `POST /interviews`, `POST /emails/send` | all 202, all `TaskOut`, all pollable at `GET /tasks/{id}` |
| TC-13 | `PublicJobOut` response body | contains no `job_id`, `recruiter_id`, `template_id`, or counts |

## Out of scope

All real logic, migrations, Google calls, Celery tasks, vector operations, rate
limiting, file validation, and every frontend screen. This story produces a typed,
callable, entirely fake API.

Phase 2/3 endpoints (`/templates/{id}/duplicate`, `/candidates/{id}/evidence`,
`/jobs/{id}/candidates/export`, `/emails/replies*`, `/admin/*`,
`/scheduling/sync-calendar`) are **not** stubbed — they are declared future work in
`docs/stories/README.md` and stubbing them would put dead routes in Saif's client.

`DELETE /jobs/{id}` is also **not** stubbed here: US-06's own "Out of scope" section
excludes edit/TTL-extend/delete from Phase 1 (delete belongs to US-09/US-10, Phase 2).
It was listed as Phase 1 in an earlier draft of `docs/api-contract.md`; that's now
corrected there to match.

## Note for the story that replaces each stub

When US-04/06/11/12/13/15/16/18/19/24/26/27 land for real, they **must not change these
response shapes** without regenerating the client and telling Saif. If a shape turns
out to be wrong, that's a `docs/drift.md` row and an `api-contract.md` edit, not a
silent change.
