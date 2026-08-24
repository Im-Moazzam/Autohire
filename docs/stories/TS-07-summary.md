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

## Slices 2-5 — pending manual verification

Not started against real Google. Code-only fixes already landed in the Slice 1
commit where they were low-risk and testable without live credentials:

- **Slice 2:** `DriveResumeStore.store_resume`'s `json.dumps` hardening (see
  above). The "Prove it" manual run (job folder created, resume uploaded into
  it, `webViewLink` opens) has not been run.
- **Slice 3:** no code changes — both open questions (`From` header behavior,
  `gmail_message_id`/`gmail_thread_id` populated) are verify-only against a real
  send, not implicated by anything Slice 1 touched.
- **Slice 4:** `sendUpdates` decision recorded (above); the `starts_at`
  timezone claim is unverified.
- **Slice 5:** embedder decision recorded (above); no code to verify further.

This section will be filled in with real observed evidence — what was run, what
was seen in the actual Google product, anything that behaved differently from
the story's description — once that verification happens.
