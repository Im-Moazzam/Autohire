# TS-07 summary

Same template as TS-06, plus a **Manual verification** section per slice (Drive,
Gmail, Calendar — what was run, what was observed against the real Google product).
This file is filled in slice by slice as work completes and is verified.

---

## Slice 1 — Split the switch

**Status:** Done. Commit `d82ff2d` on `feat/TS-07-cloud-cutover`, independently
mergeable — nothing in Slice 1 depends on Google credentials or the manual
verification still pending for Slices 2-4.

### Test counts, before and after

| | Before (TS-06, `docs/stories/TS-06-summary.md`) | After (this commit) |
|---|---|---|
| Backend tests | 207 passed | **217 passed** (+10, all in the new `test_adapter_selection.py`) |
| Coverage (`app/services`, gate is 70%) | 93% | **93.61%** — effectively unchanged, expected: the new tests target `app/adapters` and `candidate_service.resume_url_for`'s docstring/branch simplification, not new `app/services` line volume |
| Frontend tests | **16** (measured directly, not carried over from TS-06's summary text, which didn't state a number: `identityFields.test.ts` generates 10 cases at runtime from `docs/identity-fields-cases.json`, `jobs.test.ts` has 5, `Button.test.tsx` has 1) | **19** (+3, all in the new `http.test.ts`) |

Re-run just now, not carried over from an earlier pass:

```
$ docker compose exec api pytest -q
217 passed, 2 warnings in 60.41s

$ docker compose exec api pytest --cov=app/services --cov-report=term-missing --cov-fail-under=70 -q
TOTAL  735  47  94%
Required test coverage of 70% reached. Total coverage: 93.61%
217 passed, 2 warnings in 112.40s

$ docker compose exec api ruff check app
All checks passed!

$ docker compose exec api mypy --config-file pyproject.toml app
Success: no issues found in 77 source files

$ npx tsc -b        # frontend — the real gate, not --noEmit
(clean, no output)

$ npm run lint
2 pre-existing oxlint warnings (Button.tsx, Toast.tsx — only-export-components,
unrelated to this story, same ones TS-06 documented), 0 errors

$ npx vitest run
Test Files  4 passed (4)
Tests  19 passed (19)

$ npm run build
✓ built in 742ms
```

### AC: zero `settings.app_env` references in `app/services/`

```
$ grep -rn "app_env" backend/app/services/
backend/app/services/candidate_service.py:236:        # write doesn't — that distinguishes the store, not settings.app_env.
```

One hit, and it's a comment *naming* the thing that used to be read there, not a
read of `settings.app_env` itself — confirming the AC. The four real business-logic
branches that used to key off it (`candidate_service.py` lines ~93/231/325,
`job_service.py` line ~181) now read `settings.resume_store` or the returned
`StoredFile`, per the story's own instruction (see per-file section below).

`settings.app_env` itself still exists and is still read in exactly one place,
which the story explicitly keeps: `backend/app/api/routes/auth.py`'s
`_COOKIE_SECURE = settings.app_env != "local"`. That's a deployment concern, not
adapter selection, and the story's own rules of engagement list it as the one
site that must stay tied to `APP_ENV`.

### AC: `api.d.ts` / `docs/openapi.json` unchanged

```
$ git diff --stat HEAD~1 HEAD -- docs/openapi.json frontend/src/lib/api.d.ts
(no output)
```

No route was touched in this slice, so nothing to regenerate — confirmed by diff,
not assumed.

### `fixtures.resume_url_for` — real grep output, not an assertion

Per the story's instruction to check whether `fixtures.py` has any importers left
after TS-06/R-04 before touching it:

```
$ grep -rn "fixtures\." backend/ --include=*.py | grep -v __pycache__
backend/app/services/job_service.py:26:# of app/api/fixtures.py — jobs.py was its only caller.
backend/tests/conftest.py:125:    """Mirrors fixtures.JOBS (and the two fixture templates they reference) as
backend/tests/conftest.py:130:    for template_id, template in fixtures.TEMPLATES.items():
backend/tests/conftest.py:143:    for job_id, job in fixtures.JOBS.items():
backend/tests/test_stub_common.py:32:    assert body["total"] == len(fixtures.JOBS)
backend/tests/test_stub_common.py:47:        f"/api/v1/jobs/{fixtures.JOB_LIVE_ID}", json={"not_a_real_field": "x"}
backend/tests/test_stub_common.py:68:        f"/api/v1/jobs/{fixtures.JOB_DRAFT_ID}", json={"status": "PROCESSED"}
```

Every real importer touches `fixtures.JOBS`/`fixtures.TEMPLATES`/the two job-ID
constants (seed data for `conftest.py` and `test_stub_common.py`). None reference
`resume_url_for`. The file itself stays — it's still imported for that seed
data — only the dead `resume_url_for` function was deleted.

### What the four new factory tests actually assert

`backend/tests/test_adapter_selection.py`, no `APP_ENV` set in any of them
(that's the point — proving the split actually decoupled the four settings from
each other and from `app_env`):

- `test_resume_store_defaults_local` / `test_resume_store_switches_to_drive` —
  `get_resume_store()` returns `LocalResumeStore` when `RESUME_STORE=local`,
  `DriveResumeStore` when `RESUME_STORE=drive`.
- `test_mailer_defaults_local` / `test_mailer_switches_to_gmail` — same shape for
  `get_mailer()` / `MAILER`.
- `test_calendar_store_defaults_local` / `test_calendar_store_switches_to_google`
  — same shape for `get_calendar_store()` / `CALENDAR_STORE`.
- `test_embedder_defaults_fastembed` — `get_embedder()` returns
  `FastEmbedEmbedder` when `EMBEDDER=fastembed`.
- `test_embedder_openai_is_not_implemented` — `EMBEDDER=openai` raises
  `NotImplementedError` whose message names `fastembed` as the supported value
  (asserted via `pytest.raises(..., match="fastembed")`), not a bare exception.
- `test_resume_url_for_local_candidate_ignores_app_env` /
  `test_resume_url_for_drive_candidate_ignores_app_env` — `resume_url_for`
  returns the download route for a `Candidate` with `resume_storage_key` set,
  the Drive link for one with `resume_drive_url` set — constructed directly with
  each field, no `APP_ENV` touched, no DB write.

`frontend/src/lib/http.test.ts` (3 new tests): `apiErrorMessage` maps a 409 body
with `code: "REAUTH_REQUIRED"` to a message mentioning "reconnect" (case-
insensitive) rather than the raw backend string; any other error code still
surfaces the backend's own message unchanged; a non-`ApiError` still falls back
to the caller-supplied fallback text.

### Files changed and what each change does

| File | Change |
|---|---|
| `backend/app/core/config.py` | Added `resume_store`, `mailer`, `calendar_store`, `embedder` settings, each defaulting to local/fastembed. `app_env` kept, re-labeled as deployment-only in a comment. Re-scoped the `openai_api_key` comment — reserved for a future LLM-feedback adapter, not the embedder (see Slice 5 decision below). |
| `backend/app/adapters/resume_store.py` | `get_resume_store()` reads `settings.resume_store`. `DriveResumeStore.store_resume`'s multipart metadata now built with `json.dumps` instead of f-string interpolation (Slice 2 hardening — `filename` is server-generated so this wasn't currently exploitable, but was fragile). |
| `backend/app/adapters/mailer.py` | `get_mailer()` reads `settings.mailer`. |
| `backend/app/adapters/calendar_store.py` | `get_calendar_store()` reads `settings.calendar_store` (renamed from the story's `CALENDAR` to `CALENDAR_STORE` for symmetry with `RESUME_STORE`, per review). |
| `backend/app/adapters/embedder.py` | `get_embedder()` reads `settings.embedder`. `NotImplementedError` message now names `EMBEDDER=fastembed` as the only supported value, instead of a generic "cloud embedder is not implemented" string. |
| `backend/app/services/candidate_service.py` | `_storage_failure_status_code()` keys off `settings.resume_store != "local"` instead of `settings.app_env`. `submit_application`'s `resume_storage_key` assignment now checks `stored.drive_file_id is None` (the returned `StoredFile`) instead of `settings.app_env == "local"`. `resume_url_for` branches on `candidate.resume_storage_key` being set, not on the environment. Docstrings on `resume_url_for`/`resolve_resume_path` updated to describe the new branching. |
| `backend/app/services/job_service.py` | `finalize_launch`'s 500-vs-502 status code keyed off `settings.resume_store != "local"` instead of `settings.app_env`. |
| `backend/app/api/fixtures.py` | Deleted the dead `resume_url_for` function (zero callers, see grep above). |
| `backend/app/api/routes/candidates.py` | Comment referencing `APP_ENV=local` corrected to describe the actual current branch (`resume_storage_key` only set for a local write). |
| `backend/tests/test_adapter_selection.py` | New — the 10 tests described above. |
| `backend/tests/test_candidate_submission.py` | Removed the now-unnecessary `settings.app_env = "cloud"` monkeypatch from the Drive-upload test — overriding the `get_resume_store` dependency is sufficient on its own now that the branch follows the returned `StoredFile`. |
| `backend/tests/test_jobs.py`, `test_openapi_declared_responses.py` | Comments referencing `APP_ENV=local` corrected to `RESUME_STORE=local` (test behavior unchanged). |
| `frontend/src/components/app/AppShell.tsx` | Added a persistent banner when `recruiter.account_state === "REAUTH_REQUIRED"`, linking to `googleReconnectUrl`. Driven by `useCurrentRecruiter()`, already fetched on every authenticated page — not a new fetch or interceptor. |
| `frontend/src/lib/auth.ts` | Added `googleReconnectUrl` export, same full-page-navigation pattern as the existing `googleLoginUrl`. |
| `frontend/src/lib/http.ts` | `apiErrorMessage` maps a `REAUTH_REQUIRED` error code to a message pointing at the banner, before falling back to the raw backend message. |
| `frontend/src/lib/http.test.ts` | New — the 3 tests described above. |
| `.env.example` | Documents `RESUME_STORE`, `MAILER`, `CALENDAR_STORE`, `EMBEDDER` with defaults; corrected comments that referenced `APP_ENV=local` for adapter selection. |
| `docs/architecture.md` | Adapter table rewritten: one row per concern with its own setting column, instead of a single `APP_ENV=local`/`APP_ENV=cloud` pair of columns. Corrected the Pinecone/OpenAI-embedder bullets, which were already stale before this story (Pinecone dropped, drift row 10; OpenAI embedder never built, drift row 47) — left uncorrected they'd have contradicted this story's own drift rows. |
| `docs/decisions/ADR-003-local-first-external-services.md` | Decision section rewritten to describe the four independent settings actually built, replacing the binary-switch description. Consequences section corrected for the same stale Pinecone/OpenAI claims. |
| `docs/drift.md` | Rows 65 (the switch split itself), 66 (embedder decision), 67 (`sendUpdates` decision). |
| `docs/stories/TS-07.md` | Story file itself — status updated, Slice 1's AC boxes checked with evidence notes, branch renamed from `feat/TS-07` to match the story's specified `feat/TS-07-cloud-cutover`. |
| `CHANGELOG.md` | New `### Changed` entry under `[Unreleased]` summarizing all of the above. |

### Decisions recorded, not defaulted from the story text

- **Embedder (Slice 5):** kept `fastembed` only. Explicitly decided, not the
  story's silently-accepted suggestion — embeddings (scoring vectors) are a
  different adapter from any future LLM-feedback narrative adapter; OpenAI use
  for feedback text, if it happens, doesn't require an OpenAI embedder. No
  migration, no re-embed, no dimension-mismatch risk. Recorded in drift row 66.
- **`sendUpdates` (Slice 4):** left unset (`events.insert` defaults to `none`).
  AutoHire's own Gmail `INTERVIEW_INVITE` stays the single tracked email the
  candidate receives. Recorded in drift row 67. No code change was needed —
  `GoogleCalendarStore.create_event` already didn't set it; this just makes the
  omission a recorded decision instead of an unexamined default.
- **`_COOKIE_SECURE`:** left on `settings.app_env`, unchanged, with the browser
  verification step skipped — after this split nobody needs to flip `APP_ENV` to
  reach a Google service, so the question of whether a `Secure` cookie survives
  `http://localhost` never arises in practice.

### Known gaps in this slice, not fixed here

- Nothing found. All four Slice 1 sub-items (config split, `candidate_service`
  storage-key branch, `resume_url_for`, `fixtures.py`) reproduced and closed
  exactly as the story described.

---

## Slice 2 — Drive for real

**Status:** Done. Verified manually against a real Google Drive, `RESUME_STORE=drive`.

### A second bug found and fixed mid-verification: real filename lost in Drive

Manual testing surfaced a UX gap the story didn't call out: `DriveResumeStore.store_resume`
used the same server-generated `uuid4` name (TC-08's path-traversal guard) as both the
storage key *and* Drive's visible file name, so every resume showed up in the recruiter's
Drive as e.g. `f01eec61-895e-4aa6-9a11-f07e0d95dc69.pdf` — unreadable, no way to tell
candidates apart by filename.

**Fix:** `ResumeStore.store_resume` gained an optional `display_name` parameter
(`backend/app/adapters/base.py`). `DriveResumeStore` uses it as Drive's `name` metadata
field — cosmetic only, never a lookup key (Drive files are addressed by `drive_file_id`,
never by name). `LocalResumeStore` accepts and ignores it — the local disk path must stay
the server-generated uuid (TC-08 is a real filesystem containment guard there, not just
display). `candidate_service.submit_application` computes the display name from
`resume.filename` (the original upload), sanitized (`_drive_display_name`: strips control
chars and path separators, caps at 150 chars, falls back to `resume` if empty) and
re-suffixed with the *sniffed* extension, never the candidate-supplied one. The
uuid4-based storage key — local path, Drive lookup, download response filename — is
unchanged everywhere. Commit `70cf09e`.

### Manual run

Job `TS-07 Display Name Verification` (`job_id 1da05855-b3fe-4c5e-962c-07341eaea821`),
`RESUME_STORE=drive`. Applied through the actual `/apply/{slug}` form in a real browser
(not a direct API call) with a PDF named `Moazzam_Aleem_Resume.pdf`.

- **Folder created:** `TS-07 Display Name Verification` appeared at Drive root
  (`folder_id 1cfKEFsySKesLzJF51mkW_MTyACFN36nQ`), immediately on job launch — confirmed
  by opening Drive directly, not inferred from the API.
- **File landed inside that folder**, not at Drive root — confirmed by navigating into
  the folder and seeing exactly one file.
- **Display name fix confirmed live:** the file is named `Moazzam_Aleem_Resume.pdf` in
  Drive — the candidate's real filename, not a uuid.
- **`GET /jobs/{id}/candidates`:** `resume_url` populated with a real, working
  `drive.google.com/file/d/…/view` link; nothing candidate-supplied leaks into it.
- **`resume_url` opens correctly:** clicked through from the API response, the PDF
  rendered in Google's viewer, tab title confirmed `Moazzam_Aleem_Resume.pdf`.

### AC status

- [x] Job folder created, resume uploaded into it, link opens — evidence above
- [x] `webViewLink` (`resume_url`) openable by the owning recruiter

---

## Slice 3 — Gmail for real

**Status:** Done. Verified manually against real Gmail, `MAILER=gmail` (`RESUME_STORE`
stayed `drive`; `CALENDAR_STORE` stayed `local` for this slice — one variable at a time,
per the story's own rule).

### A testing near-miss worth recording: an undersized fixture PDF

Applying with a synthetic test PDF hit `PARSE_ERROR: no selectable text found` —
looked like an app bug at first. Root cause: `resume_parser.py`'s `MIN_CHARS = 50` floor
(the scanned/image-only guard) rejected the extracted text because it was exactly 49
characters — a bug in the throwaway fixture, not the app. Fixed by patching the same
Drive file's content in place (`files.update?uploadType=media`) with longer text and
re-running `/process`, which correctly picked the `PARSE_ERROR` candidate back up and
re-parsed it clean. This incidentally proved the story's SUBMITTED/PARSE_ERROR retry
behavior against live Drive + `pypdf`, not just against local fixtures.

### Manual run

Reused the already-Drive-backed `TS-07 Drive Verification` job
(`job_id 50d92739-4da8-4506-b1f0-dbb7aec000d2`) rather than launching a new one — the
story's "use a brand-new job" caution is about jobs whose `google_drive_folder_id` is a
stale filesystem path from before `RESUME_STORE=drive`; this job's folder was already a
real Drive folder, so reuse was safe. Applied as `moazzamaleem786@gmail.com` (a second,
real Gmail account the user controls). Closed the job, ran `/process` → `PARSED`,
`/rank` → `RANKED`.

**Scheduling preferences set for real**, not defaulted: `PUT /scheduling/preferences`
with `available_days: [MON..FRI]`, `09:00–17:00`, `slot_duration_minutes: 30` — 200,
persisted (`preference_id` returned). Confirms the recruiter-configurable-hours AC
(US-24) is real and working end-to-end even though the frontend has no Scheduling page
yet to drive it from (see *Known gaps*, below) — this was called via the API directly.

`POST /interviews` → `CALENDAR_SYNC` task (still `CALENDAR_STORE=local` here, so
`google_meet_link` correctly came back as a `meet.local.test` stub — expected, Slice 4
not yet flipped).

**Email:**
```
GET /emails
  delivery_status: "SENT"
  gmail_message_id: "1a035593aacde2e3"   (confirmed directly on the EmailLog row,
                                           not just the summary list response)
```
Worker log confirms a real API call, not a mock: `POST
https://gmail.googleapis.com/gmail/v1/users/me/messages/send "HTTP/1.1 200 OK"`.
The user independently confirmed the invitation actually arrived in
`moazzamaleem786@gmail.com`'s inbox "as expected."

**Idempotency — first attempt was itself a bug, corrected:** `email_dispatch_job.run()`
takes a `slot_id`, not an `email_id`; the first idempotency check accidentally passed the
email log's id, which made `db.get(InterviewSlot, slot_id)` return `None` and the task
no-op silently — "no error" was not evidence of dedupe working, it was evidence of
nothing running. Caught before writing it up, re-ran with the correct `slot_id`
(`0faf399c-fc47-4058-91d6-ba8f54da93ad`): `email_logs` row count stayed at exactly 1,
same `email_id`/`sent_at` before and after — the `idempotency_key` UNIQUE constraint's
`IntegrityError` → rollback → no-op path (documented in `email_dispatch.py`'s own
docstring) is confirmed working against the real send, not just against a mock.

### Open question resolved

- **`From` header:** not independently inspected (would need the raw message headers in
  the recipient's client); the user's own inbox check confirms delivery and sender
  identity read as expected. Gmail's API sends as the authenticated user regardless of
  the `message["From"]` value set in code, per Google's documented behavior — consistent
  with what arrived.

### AC status

- [x] Invitation delivered, `gmail_message_id` non-null — evidence above
- [x] Redelivery deduplicated by `idempotency_key` — evidence above (corrected re-run)

---

## Slice 4 — Calendar for real

**Status:** Done. Verified manually against a real Google Calendar,
`CALENDAR_STORE=google` (`RESUME_STORE` stayed `drive`, `MAILER` stayed `gmail`).

### Manual run

New job `TS-07 Calendar Verification` (`job_id b94751dc-53c8-4ba5-8b97-2e903c51c5f5`).
Applied with the real fixture resume `backend/tests/fixtures/resumes/Moazzam_Resume.pdf`
(269 KB, real content — no `MIN_CHARS` surprises this time) as `moazzamaleem786@gmail.com`.
Closed → `/process` → `PARSED` on the first attempt → `/rank` → `RANKED`.
`POST /interviews` → `CALENDAR_SYNC` task:

```
GET /interviews
  scheduled_at:      "2026-08-25T04:30:00Z"
  google_meet_link:  "https://meet.google.com/dyz-vbhv-gnw"
```

Worker log: real API call, not a mock — `POST
https://www.googleapis.com/calendar/v3/calendars/primary/events?conferenceDataVersion=1
"HTTP/1.1 200 OK"`.

**Verified directly in Google Calendar**, not inferred from the API response. With the
user's explicit go-ahead, the recruiter's Google Calendar primary time zone was changed
from UTC to `(GMT+05:00) Pakistan Standard Time` (matching `SCHEDULING_TIMEZONE=Asia/Karachi`)
to make the comparison meaningful. The event appeared as:

> **Interview: Moazzam Aleem — TS-07 Calendar Verification**
> Tuesday, August 25 · **9:30 – 10:00am**
> Join with Google Meet: `meet.google.com/dyz-vbhv-gnw`
> 1 guest · 1 awaiting

`04:30Z + 5h = 09:30` local — exact match. This resolves the story's open question about
`starts_at.isoformat()` being passed without an explicit `timeZone` field: the UTC offset
embedded in the ISO string is read correctly by Google, no timezone bug. The Meet link in
the calendar event matches the API's `google_meet_link` exactly, and is real and clickable
(not a `meet.local.test` stub). "1 guest, 1 awaiting" confirms the candidate was actually
added as an attendee on the real event, not just referenced in a log row.

**`sendUpdates` decision (drift row 67) confirmed consistent in practice:** Google did not
send its own calendar-invite email for this event (`sendUpdates` still unset/`none`) —
AutoHire's own Gmail `INTERVIEW_INVITE` (Slice 3) remains the single tracked invitation
channel, as decided.

### AC status

- [x] Event on the recruiter's calendar at the correct Asia/Karachi local time — evidence
      above
- [x] Real, joinable Meet link — evidence above

---

## Slice 5 — Embedder

**Status:** Decision recorded in Slice 1 (kept `fastembed` only, drift row 66); no
further verification needed — no code path changed.

---

## Known gaps, not fixed here

- **No frontend UI for Scheduling, Candidates, or Emails yet** (`frontend/src/router.tsx`
  only has Dashboard, Templates, Jobs, and the public Apply page). All of Slices 3-4's
  scheduling-preferences, ranking, and interview calls were driven directly against the
  API from an authenticated browser session, not through a recruiter-facing page — because
  that page doesn't exist. This is a pre-existing scope gap (that UI belongs to
  US-13/US-24/US-26), not something TS-07 introduced or was supposed to close; called out
  here so the "manual verification" evidence above is understood as API-level, not
  UI-level, proof.
- **`Candidate` has no column for the original resume filename** — Slice 2's fix shows
  the real filename in Drive, but the recruiter UI (once built) has nowhere to display it
  either, since it isn't persisted anywhere in the DB. Revisit if/when the UI needs it.
- **`web` (frontend) docker-compose service doesn't mount `./docs`**, unlike `api`/
  `worker` — `identityFields.test.ts`'s import of `../../../docs/identity-fields-cases.json`
  fails inside that container (works fine run from the host, which is how it must have
  been run for Slice 1's reported "19 frontend tests"). Not touched this session; noted
  since it will bite the next person who tries `docker compose exec web npx vitest run`.

## Full-suite evidence (re-run after Slice 2's fix and all manual verification)

Run with `RESUME_STORE=local MAILER=local CALENDAR_STORE=local` overrides on top of the
live `.env` (which stayed on `drive`/`gmail`/`google` — the config used for the manual
verification above) so the suite exercises local adapters and makes no real network call,
per the story's rule 3:

```
$ docker compose exec -e RESUME_STORE=local -e MAILER=local -e CALENDAR_STORE=local \
    api pytest -q
217 passed, 2 warnings in 46.22s

$ docker compose exec -e RESUME_STORE=local -e MAILER=local -e CALENDAR_STORE=local \
    api pytest --cov=app/services --cov-report=term-missing --cov-fail-under=70 -q
TOTAL  741  47  94%
Required test coverage of 70% reached. Total coverage: 93.66%
217 passed, 2 warnings in 79.59s

$ docker compose exec api ruff check app
All checks passed!

$ docker compose exec api mypy --config-file pyproject.toml app
Success: no issues found in 77 source files
```

Same 217/217 as Slice 1's commit — the `display_name` addition (Slice 2's fix) changed
nothing structurally, only added an optional parameter. Frontend untouched this session,
not re-run (see *Known gaps* above for why `docker compose exec web` specifically would
have failed regardless).
