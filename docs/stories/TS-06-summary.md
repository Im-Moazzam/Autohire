# TS-06 remediation summary

**Branch:** fix/TS-06-review-remediation
**Baseline:** 189 passed, ruff clean, mypy clean, 91% coverage (before any change)
**Final:**    207 passed, ruff clean, mypy clean, 93% coverage

## Per item

### R-01 — `canProcess` gate makes AI processing unreachable from the UI
- **Verified?** REPRODUCED
- **Evidence:** Read `Jobs.tsx:43` (`canProcess = job.status === "LIVE" && ...`)
  against `task_service.enqueue_resume_parse` (`backend/app/services/task_service.py:88`,
  requires `job.status == CLOSED`) — confirmed by inspection, not runtime repro
  (a frontend-only reasoning defect).
- **Changed:** `frontend/src/lib/jobs.ts` — new exported `canProcessJob()`.
  `frontend/src/pages/Jobs.tsx` — calls the helper, corrected tooltip.
- **Why:** Single source of truth matching the backend guard exactly, testable
  in isolation. Rejected re-deriving the rule inline in `Jobs.tsx` a second
  time — that's exactly how the two drifted apart originally.
- **Test:** `frontend/src/lib/jobs.test.ts` — LIVE+n → false, CLOSED+0 →
  false, CLOSED+n → true, DRAFT → false. All four written and green
  immediately (new pure function, no prior "before" state to be red against).
- **Commit:** abe622c fix(TS-06/R-01): fix canProcess gate mismatch with backend guard

### R-02 — Parse retry impossible once a job is `PROCESSED`
- **Verified?** REPRODUCED
- **Evidence:** `test_process_on_processed_job_retries_parse_error_ranked_untouched`
  before the fix: `POST /jobs/{id}/process` on a `PROCESSED` job → `409
  {"code":"INVALID_STATE_TRANSITION","message":"Job must be CLOSED with
  candidates to process."}` instead of `202`.
- **Changed:** `backend/app/services/task_service.py` — widened
  `enqueue_resume_parse`'s guard to `job.status not in (CLOSED, PROCESSED)`,
  updated `_INVALID_STATE`'s message. `docs/api-contract.md` updated to match.
- **Why:** Mirrors `enqueue_batch_ranking`'s existing `(CLOSED, PROCESSED)`
  guard. Safe because `_process_job_candidates` only ever touches
  `SUBMITTED`/`PARSE_ERROR` candidates and `PARSED -> PARSED` is a no-op in
  the legal transition graph — a `RANKED` candidate in the same run is inert.
- **Test:** `test_process_on_processed_job_retries_parse_error_ranked_untouched`
  (`backend/tests/test_process.py`) — failed red (409) before the fix,
  green (202, `PARSE_ERROR` → `PARSED`, `RANKED` untouched) after.
- **Commit:** a10ee3d fix(TS-06/R-02): allow parse retry on a PROCESSED job

### R-03 — `.doc` is advertised, accepted, and always fails parsing
- **Verified?** REPRODUCED
- **Evidence:** `test_ole2_doc_upload_is_415_nothing_written` before the fix:
  posting OLE2 magic bytes (`\xd0\xcf\x11\xe0...`) as `resume.doc` →
  `201 Created` (candidate row written), not `415`.
- **Changed:** `backend/app/services/resume_validation.py` — removed the
  `_OLE_MAGIC` accepting branch from `sniff_extension` (kept the constant,
  commented). `backend/app/adapters/resume_store.py` and
  `backend/app/api/routes/candidates.py` — dropped `"doc"` from
  `_MIME_BY_EXT`. `backend/app/services/candidate_service.py` — 415 message
  now says "PDF and DOCX". `frontend/src/pages/Apply.tsx` — `accept=".pdf,.docx"`
  (the one permitted edit to that file).
- **Why:** Reject where the candidate can still act, not silently after the
  fact. Rejected keeping `.doc` "accepted but always errors" — that's worse
  than an honest 415, it just delays the failure past the point of no return.
- **Test:** `test_ole2_doc_upload_is_415_nothing_written` (candidate_submission),
  `test_doc_ole_header_is_unsupported` (resume_validation, updated from
  asserting `"doc"` to asserting `None`) — both red-then-green.
- **Commit:** 6a33e83 fix(TS-06/R-03): reject .doc uploads at the point of acceptance

### R-04 — `PATCH /interviews/{slot_id}` 404s on real slots; `POST /emails/send` returns a stale fixture
- **Verified?** REPRODUCED
- **Evidence:** `test_patch_real_slot_is_501_not_implemented` before the fix:
  scheduling a real interview then `PATCH`ing its real `slot_id` → `404
  SLOT_NOT_FOUND` (fixture lookup miss). `test_send_email_is_501_not_implemented`
  before the fix: `POST /emails/send` → `202` with a fixture `TaskOut`
  (`task_type: BATCH_RANKING`, `status: RUNNING`) whose `task_id` doesn't
  exist in `background_tasks`.
- **Changed:** `backend/app/api/routes/interviews.py` and `.../emails.py` —
  both now raise `501 NOT_IMPLEMENTED`, keeping the declared `response_model`/
  status. Removed `fixtures` import and `_to_slot_out` from both modules.
  Regenerated `docs/openapi.json` + `frontend/src/lib/api.d.ts`.
- **Why:** Both are genuinely Phase 2 (reschedule/cancel; manual ad hoc
  send). An honest 501 beats a fixture that either 404s downstream or lies
  about task state. Rejected implementing either for real — explicitly out
  of scope per the story.
- **Test:** `test_patch_real_slot_is_501_not_implemented` (test_interviews.py),
  `test_send_email_is_501_not_implemented` (test_emails.py), plus
  `test_stub_scheduling.py`/`test_stub_emails.py` rewritten to assert 501.
- **Dead-code check:** `app/api/fixtures.py` is **not** fully dead —
  `conftest.py` and `test_stub_common.py` still import it for an unrelated
  fixture-mirroring helper (`seeded_stub_jobs`) and TC-01/02 list-endpoint
  tests. Reported per the story's instruction rather than deleted.
- **Commit:** c059947 fix(TS-06/R-04): honest 501 for PATCH /interviews/{id} and POST /emails/send

### R-05 — Two authenticated routes do not declare 401
- **Verified?** REPRODUCED
- **Evidence:** `test_auth_me_declares_401`/`test_recruiters_me_patch_declares_401`
  before the fix: `GET /openapi.json`'s `responses` for both operations was
  `{"200", "422"}`, no `"401"`.
- **Changed:** `backend/app/api/routes/auth.py` and `.../recruiters.py` —
  added `responses=error_responses(401)`.
- **Why:** Both depend on `get_current_recruiter` and are 401-reachable at
  runtime (`test_tc05_me_without_cookie_is_401`,
  `test_tc05_patch_without_session_cookie_is_401` already existed and pass);
  the declaration was simply missing.
- **Test:** New `backend/tests/test_openapi_declared_responses.py`.
- **Commit:** af3a9ff fix(TS-06/R-05): declare 401 on GET /auth/me and PATCH /recruiters/me

### R-06 — Job routes declare 502 but not the 500 they raise locally
- **Verified?** REPRODUCED
- **Evidence:** `test_jobs_post_declares_500`/`test_jobs_patch_declares_500`
  before the fix: declared responses were `{"401","404","422","502"}` (POST)
  / `{"401","404","409","422","502"}` (PATCH) — no `"500"`, while
  `job_service.finalize_launch` demonstrably raises 500 when
  `settings.app_env == "local"`.
- **Changed:** `backend/app/api/routes/jobs.py` — added `500` to both
  routes' `error_responses(...)`.
- **Why:** `POST /public/apply/{slug}` already declares both 500 and 502 for
  the same underlying failure — matched the existing precedent.
- **Test:** `test_jobs_post_declares_500`, `test_jobs_patch_declares_500`.
- **Commit:** 0848ef8 fix(TS-06/R-06): declare 500 on POST/PATCH /jobs alongside 502

### R-07 — `JobUpdate` accepts a past `expires_at`; `JobCreate` does not
- **Verified?** REPRODUCED
- **Evidence:** `test_patch_expires_at_in_past_is_422` before the fix:
  `PATCH /jobs/{id}` with `expires_at` one day in the past → `200`, not `422`.
- **Changed:** `backend/app/schemas/job.py` — factored
  `_validate_expires_in_future`, applied via `field_validator` to both
  `JobCreate` and `JobUpdate` (the latter skips `None`).
- **Why:** One implementation instead of duplicating the validator body.
  Left `assert_job_accepting` untouched — leaving an expired-but-`LIVE` job
  reachable is a deliberate US-06 decision the story explicitly said not to
  touch.
- **Test:** `test_patch_expires_at_in_past_is_422` (test_jobs.py).
- **Commit:** f8487ec fix(TS-06/R-07): apply the future-date validator to JobUpdate too

### R-08 — `expiresAtToDateInput` mixes UTC and local dates
- **Verified?** REPRODUCED (a reasoning defect, confirmed live under
  `TZ=America/New_York` rather than at the dev machine's own UTC+5 offset,
  per the story's own repro note)
- **Evidence:** Round-trip test under `TZ=America/New_York` before the fix:
  `expiresAtToDateInput(dateToExpiresAt("2026-03-15"))` returned
  `"2026-03-16"`, not `"2026-03-15"`.
- **Changed:** `frontend/src/lib/jobs.ts` — `expiresAtToDateInput` now uses
  `new Date(iso).toLocaleDateString("en-CA")` instead of `iso.slice(0, 10)`.
  Both helpers moved from `JobBuilder.tsx` into `lib/jobs.ts` (importable,
  testable). Follow-up commit added a local `declare const process` so the
  test's `process.env.TZ` usage doesn't require `@types/node` project-wide.
- **Why:** `toLocaleDateString("en-CA")` reads the *local* calendar date of
  the parsed instant, matching what `dateToExpiresAt` wrote from. Rejected
  parsing the ISO string by hand — the built-in local-date API is one line
  and correct on the DST-transition edge cases a hand-rolled version would
  need to special-case.
- **Test:** `frontend/src/lib/jobs.test.ts` — round trip under
  `TZ=America/New_York`.
- **Commit:** 5cb4243 fix(TS-06/R-08): expiresAtToDateInput now reads the local calendar date;
  fe48313 fix(TS-06/R-08): declare process locally instead of pulling in @types/node

### R-09 — Dead configuration and dead columns
- **Verified?** REPRODUCED (confirmed via grep: zero readers outside each
  item's own definition, before removing anything)
- **Evidence:** `grep` for `paginate(`, `allowed_resume_types`,
  `pinecone_api_key`/`pinecone_index`, `google_form_id`/`google_form_url`,
  `retry_count` — every hit was the definition itself, a migration, or docs.
  `last_synced_at` had one real hit (`scheduling_service.py`, always sets
  `None`) — confirmed "always NULL" as the story claimed, kept per instruction.
- **Changed:** Deleted `paginate()` (`schemas/common.py`),
  `ALLOWED_RESUME_TYPES`, `PINECONE_API_KEY`/`PINECONE_INDEX`
  (`config.py`, `.env.example`). Commented `OPENAI_API_KEY` and
  `scheduling_preferences.last_synced_at` as reserved. New migration
  `98295cf48076` drops `job_postings.google_form_id`/`.google_form_url` and
  `background_tasks.retry_count`, with a real `downgrade()` re-adding all
  three nullable.
- **Why:** Dead code and dead schema left in place invite confusion about
  what's actually load-bearing. Kept `OPENAI_API_KEY`/`last_synced_at`
  rather than delete-and-re-add-later per the story's explicit instruction.
- **Test:** Migration round-trip (see below). No regression test needed for
  deletions with zero call sites — nothing exercises them to regress.
- **Commit:** 4ec2154 fix(TS-06/R-09): remove dead config, dead paginate(), drop two dead columns

### R-10 — `calendar_sync` fetches candidates without job or soft-delete scoping
- **Verified?** REPRODUCED
- **Evidence:** `test_soft_deleted_candidate_between_enqueue_and_run_is_not_scheduled`
  before the fix: a candidate soft-deleted after enqueue was still scheduled
  (`InterviewSlot` count == 1, not 0) and `email_dispatch_job.delay` was
  called. `test_recruiter_time_collision_reports_slot_time_taken` before the
  fix: a `uq_interview_slots_recruiter_time` collision (two different
  candidates, same recruiter+instant) reported `"ALREADY_SCHEDULED"`, not
  `"SLOT_TIME_TAKEN"`.
- **Changed:** `backend/app/tasks/calendar_sync.py` — added
  `Candidate.job_id == job.job_id` and `Candidate.deleted_at.is_(None)` to
  the candidate query. New `_unique_violation_reason()` inspects
  `exc.orig.diag.constraint_name` to distinguish the two partial-unique
  indexes, falling back to `"ALREADY_SCHEDULED"` if unrecoverable.
  Documented both reasons in `docs/api-contract.md` and `docs/schema.md`.
- **Why:** An excluded candidate now falls into the pre-existing
  `CANDIDATE_NOT_FOUND` branch rather than a new one — no new failure mode
  to test/document. Verified against the real psycopg3 driver (not mocked)
  that `diag.constraint_name` actually contains the index name.
- **Test:** `test_soft_deleted_candidate_between_enqueue_and_run_is_not_scheduled`,
  `test_recruiter_time_collision_reports_slot_time_taken` (test_interviews.py).
- **Commit:** 339b7f7 fix(TS-06/R-10): scope calendar_sync's candidate query, distinguish collision reasons

### R-11 — Untested failure branches in the newest tasks
- **Verified?** REPRODUCED
- **Evidence:** `pytest --cov=app --cov-report=term-missing` before any
  test added: `calendar_sync.py` 88%, `batch_ranking.py` 85%,
  `interview_service.py` 66% (missing 96, 142, 155, 167-189, 199-210,
  221-229 — the *entire* `enqueue_scheduling` happy path, `list_slots`, and
  `available_slots_for_recruiter`, none of which the story's item text named
  explicitly but which the item's own coverage target requires).
- **Changed:** Tests only, no production change.
- **Why:** The story's target line ("interview_service.py >= 85%") demanded
  more than the two branches its prose called out — every existing schedule
  test drives `calendar_sync_job.run()` directly, so the actual HTTP routes
  (`POST`/`GET /interviews`, `GET /scheduling/available-slots`) had never
  been exercised. Added route-level tests rather than more unit calls to
  `interview_service` functions directly, since the untested code *is* the
  route-to-service wiring.
- **Test:** `test_not_ranked_candidate_between_enqueue_and_run_is_unscheduled`,
  `test_calendar_sync_exception_outside_loop_marks_task_failed`,
  `test_schedule_interviews_route_returns_202_with_real_task_id`,
  `test_schedule_interviews_route_unknown_candidate_is_404`,
  `test_list_interviews_route_returns_scheduled_slot`,
  `test_available_slots_route_returns_windows` (test_interviews.py);
  `test_batch_ranking_exception_outside_loop_marks_task_failed` (test_ranking.py).
  Result: `calendar_sync.py` 97%, `batch_ranking.py` 93%,
  `interview_service.py` 93%, total 93%.
- **Commit:** 18d8c99 test(TS-06/R-11): cover exception/failure branches in the newest tasks

### R-12 — Generated docs artifacts
- **Verified?** REPRODUCED
- **Evidence:** `docs/stories/README.md` table: all 15 rows `Todo`. Every
  individual story file's own `Status:` header: `Done` (US-26/27: `Done
  (backend)`). `docs/drift.md` row sequence after row 40: 43,44,45,46,47,
  41,42,48... — confirmed exactly as the story described.
- **Changed:** `docs/stories/README.md` table synced from story files.
  `docs/drift.md` rows 41-47 resorted into numeric order (content
  unchanged). Added rows 58-64 for this story's behaviour changes.
- **Why:** Update from the story files, never invent a status. No row's
  content changed in the resort — only position.
- **Test:** N/A (docs-only).
- **Commit:** 26ccaeb docs(TS-06/R-12): sync story statuses, sort drift.md, record TS-06 rows

### R-13 — The e2e suite tests almost nothing
- **Verified?** REPRODUCED
- **Evidence:** `e2e/tests/smoke.spec.ts` — one test, page title + `/health`
  200. `.github/workflows/ci.yml`'s `e2e` job — full `docker compose up
  --build`, 25s sleep, migrations, seed, Chromium install, for that one test.
- **Changed:** `e2e/global-setup.ts` — runs `docker compose exec api python
  -m app.scripts.seed`, captures the printed session cookie to
  `e2e/.auth/session.json` (gitignored). New `e2e/tests/apply.spec.ts` —
  creates a template + job via the API as the seeded recruiter, drives
  `/apply/{slug}` in the browser: fills the form, uploads a fixture PDF,
  submits, asserts "Application received"; submits the same email again,
  asserts the duplicate-submission error surfaces. Kept `smoke.spec.ts`.
- **Why:** The public apply flow is the only fully-built vertical slice
  with no auth to fake — matches the story's explicit suggestion.
- **Test:** `e2e/tests/apply.spec.ts` itself, verified passing locally
  (`npx playwright test` — 2 passed) alongside the existing smoke test.
- **Commit:** 00affda test(TS-06/R-13): add a real apply-flow journey to the e2e suite

## Contract change
`GET /auth/me`, `PATCH /recruiters/me` (R-05): added `401`.
`POST /jobs`, `PATCH /jobs/{job_id}` (R-06): added `500`.
`PATCH /interviews/{slot_id}`, `POST /emails/send` (R-04): added `501`.
`JobUpdate.expires_at`'s new validator (R-07) produces **no** contract change
— a Pydantic `field_validator` isn't reflected in the generated JSON schema
(confirmed: `docs/openapi.json` byte-identical before/after that commit).
`docs/openapi.json` and `frontend/src/lib/api.d.ts` regenerated via `make
api-client` in the R-04, R-05, and R-06 commits. `npx tsc -b` (the real
project build, not the no-op bare `tsc --noEmit` — see Gates below) passes
with zero errors; no frontend call site broke.

## Migration
`98295cf48076` (R-09), run on a genuinely fresh scratch database
(`CREATE DATABASE autohire_fresh_check`, full history from `112c34b8ee71`
through `98295cf48076`):
```
alembic upgrade head    -> 14 migrations apply cleanly, ends at 98295cf48076
alembic downgrade base  -> all 14 unwind cleanly, back to empty schema
alembic upgrade head    -> reapplies cleanly, ends at 98295cf48076 again
```
No errors in either direction. Scratch database dropped afterward.

## Cold end-to-end run
Driven via curl against the real dev stack (docker compose), using the
seeded recruiter's session cookie:

| Step | Call | Status |
|---|---|---|
| Create template | `POST /templates` | 201 |
| Create job | `POST /jobs` | 201, `status: LIVE` |
| Apply as candidate | `POST /public/apply/{slug}` (real PDF) | 201 |
| Close job | `PATCH /jobs/{id}` `{"status":"CLOSED"}` | 200, `status: CLOSED` |
| Process (parse) | `POST /jobs/{id}/process` | 202 -> task `SUCCESS`, 1 processed |
| Rank | `POST /jobs/{id}/rank` | 202 -> candidate `RANKED`, score computed |
| Set preferences | `PUT /scheduling/preferences` | 200 |
| Schedule interview | `POST /interviews` | 202 -> task `SUCCESS`, `scheduled: 1` |
| Poll task | `GET /tasks/{id}` | `SUCCESS`, `result_summary.scheduled: 1` |
| List interviews | `GET /interviews` | 1 slot, `status: PENDING`, Meet link present |
| List emails | `GET /emails` | 1 `INTERVIEW_INVITE`, `delivery_status: SENT` |
| Mailhog | `GET :8025/api/v2/messages` | 1 message, correct `To`/`Subject` |

**Operational note (not a code defect):** the long-running dev `worker`
container was still running pre-R-09 code when the first `process` call in
this run was issued, so the very first `RESUME_PARSE` task hit
`UndefinedColumn: background_tasks.retry_count` (the column R-09 legitimately
dropped). `docker compose restart worker` picked up the current code and
migration state; re-dispatching that one task then succeeded. The migration
and application code were both already correct — this was a stale
long-running process, the same class of thing a real deploy's rolling
restart handles automatically.

**AI-process flow is completable from the UI (R-01):** confirmed by
contract, not a browser click-through — `canProcessJob()` in
`lib/jobs.ts` now returns `allowed: true` iff `status === "CLOSED" &&
submission_count > 0`, exactly the condition this cold run's `POST
/jobs/{id}/process` step required for its `202`. `JobBuilder.tsx` already
has a working Close action (verified by reading it, not rebuilt).

## Gates
- `ruff check backend` — clean (77 source files).
- `mypy --config-file backend/pyproject.toml backend/app` — clean.
- `pytest` — 207 passed, 93% coverage (baseline: 189 passed, 91%).
- `npx tsc -b` (frontend, full checkout on host — the bare `npx tsc --noEmit`
  invocation is a no-op on this project's solution-style `tsconfig.json`
  with `files: []`+`references` and only `-b` mode actually type-checks) —
  clean.
- `npm run lint` (oxlint) — 2 pre-existing warnings (`only-export-components`
  in `Button.tsx`/`Toast.tsx`, unrelated to this story), 0 errors.
- `npx vitest run` — all real tests green; one pre-existing failure
  (`identityFields.test.ts`, see New findings) is a Docker volume-mount
  artifact specific to this sandbox's `web` container, not a real failure —
  confirmed clean when run on the host with the full repo checked out.
- `npm run build` (`tsc -b && vite build`) — clean on host with full repo.
- `alembic upgrade head -> downgrade base -> upgrade head` — clean on a
  fresh database (see Migration above).
- Playwright (`npx playwright test`) — 2 passed (smoke + new apply journey).

## New findings
- **Flaky test ordering** (not fixed, out of scope — no unrequested
  refactors): `test_auth.py::test_last_login_at_set_on_callback` and
  `test_process.py::test_retrigger_while_pending_is_409_still_one_task` each
  failed once across several full-suite runs but passed every time in
  isolation — looks like cross-test state/timing coupling, not a real defect
  in either test's own assertion. Matches a prior session's memory note
  about the same class of flakiness in this suite.
- **`e2e/tests/apply.spec.ts` relies on `docker` being on `PATH`** for its
  `global-setup.ts` (`docker compose exec ...`) — matches how CI's `e2e` job
  already runs (`docker compose up -d --build` in the same job), but is
  worth naming since it's a new implicit dependency of the e2e suite beyond
  Playwright/Node.
- **`e2e/tests/smoke.spec.ts`'s existing `/health` check now also
  transitively exercises `global-setup.ts`'s seed step** even though it
  doesn't use the seeded session — harmless (seed is idempotent) but adds
  ~2-3s to every e2e run, including the smoke-only one.
- The bare `npx tsc --noEmit` command named in this story's own AC checklist
  and in CI (`.github/workflows/ci.yml` frontend job, line 53) is a no-op on
  this project's solution-style root `tsconfig.json` (`"files": []` with
  only `references`, no direct `include`) — it reports zero errors whether
  or not the code actually type-checks. `npm run build`'s `tsc -b` (and a
  direct `npx tsc -b`) is the command that actually performs the build-mode
  check. Not fixed here (touches CI config, out of this story's scope) but
  worth flagging: R-08's `process.env.TZ` typing bug (see below) would have
  shipped past CI's frontend job undetected.

## Not done, and why
Every item (R-01 through R-13) reproduced as described in the story — none
were NOT REPRODUCED, and none reproduced differently than described.
