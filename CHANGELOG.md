# Changelog

## [Unreleased]

### Changed
- Collapsed the two separate AI-pipeline triggers into one. The Jobs list's
  "AI process" button is gone; the Candidates screen's action is now "Rank
  candidates" and runs both stages back to back — parse resumes, then rank
  them — with a spinner label that switches ("Parsing resumes…" ->
  "Ranking…") instead of two separate manual clicks on two separate screens.
  Both backend endpoints/tasks (`POST /jobs/{id}/process`,
  `POST /jobs/{id}/rank`) are unchanged; a `PARSE_ERROR` candidate is already
  skipped by the ranking query, so partial-failure handling needed no new
  code. `canProcessJob` (`frontend/src/lib/jobs.ts`) also now accepts a
  `PROCESSED` job, matching the backend guard — a repeat click on an
  already-ranked job stays a cheap re-rank (parsing is a no-op for
  already-`PARSED` candidates) rather than being wrongly blocked. See
  `docs/drift.md` row 72.

### Fixed
- Emails and Scheduling lists silently truncated at 100 rows with no way to
  see the rest — `useEmails`/`useInterviews` fetched a single fixed
  `size=100` page and never surfaced `total`, so a recruiter with more than
  100 emails or interviews just lost the overflow. Both hooks now page
  (`size=20`) and a new shared `Pagination` component (`src/components/ui`)
  renders Previous/Next controls plus an "X–Y of Z" count on the Emails and
  Scheduling screens; filter changes reset back to page 1.
- Candidate status actions, two direct UX fixes: (1) an `INVITED` candidate
  no longer shows a "Mark Rejected" button next to an invite that's already
  gone out — a same-card reject read as contradictory. Shows a
  non-actionable green "Invite sent for interview" confirmation instead.
  (2) "Undo rejection" now uses a distinct amber `warning` button variant
  (new on the shared `Button` component) with a dedicated undo icon
  (`RotateCcwIcon`), instead of looking identical to a generic "Mark X"
  primary-blue action.
- "Undo rejection" always landed on `PARSED`, hardcoded regardless of what
  the candidate's status actually was before rejection — a candidate
  rejected while the job was still `LIVE` (never closed or processed, so
  genuinely still `SUBMITTED`) came back showing `Parsed`, a parse that
  never ran. The same bug would have shown `Parsed` instead of `Ranked` for
  a candidate rejected *after* being ranked, silently losing their
  "Schedule interview" action on undo. `candidate_service` gains
  `compute_restorable_status(candidate, has_ranking)`, deriving the real
  prior status from data that already exists — an `ai_analysis_results` row
  means `RANKED`, a `parse_error` means `PARSE_ERROR`, a populated
  `resume_text` means `PARSED`, otherwise `SUBMITTED` — exposed as
  `restorable_status` on `CandidateOut` (batched via a new
  `ranking_exists_map`, one query for the whole page, never N+1).
  `_LEGAL_TRANSITIONS[REJECTED]` widened from `{PARSED}` to
  `{SUBMITTED, PARSED, PARSE_ERROR, RANKED}` to make the four real targets
  legal. Frontend: `nextStatusOptions`/`statusActionLabel` no longer
  hardcode `PARSED` for the undo edge — they use `restorable_status` from
  the API, still bordered as "Undo rejection" no matter which of the four
  it resolves to. See `docs/drift.md` row 71.
- Clicking anywhere on an "All submissions" table row now opens the
  candidate detail modal — previously only the name/email text itself was
  clickable, everything else in the row did nothing. `DataTable` gained a
  reusable `onRowClick` prop (Templates' non-clickable rows are unaffected,
  since it's optional); the resume-link cell stops propagation so it still
  opens independently instead of also triggering the row click.

### Added
- Recruiter dashboard (TS-10): a real-time overview screen replacing the
  placeholder stub. New `GET /api/v1/dashboard/stats` endpoint
  (`dashboard_service.get_dashboard_stats`) returns recruiter-scoped totals
  and a zero-filled per-status breakdown for jobs, candidates (joined
  through the recruiter's own job postings, since candidates carry no
  direct `recruiter_id`), interviews, and emails — tenant-isolated and
  covered by 6 new tests including a cross-recruiter isolation check.
  Frontend polls it every 30s. New `recharts` + `framer-motion` dependencies
  (React 19–compatible) power an animated KPI row (`AnimatedNumber`
  count-up, respecting `prefers-reduced-motion`), a donut chart per
  categorical breakdown (`DonutChart`/`DonutLegend`), and an ordered
  horizontal bar chart for the candidate pipeline (`FunnelBarChart`) — all
  colors sourced from design tokens (`var(--color-x)`), never raw hex.
  Covers all five UX states: skeleton loading, error with retry, an empty
  state with a "post your first job" CTA, and the populated view.
- Dev tooling: `mise run db:seed-demo` (`backend/app/scripts/seed_demo.py`) rebuilds a
  full demo world — recruiter, templates, jobs across every status, candidates across
  every submission status, rankings, interview slots, email logs — built from real resumes
  dropped in `backend/seed_resumes/` (gitignored; see its README), falling back to the
  bundled test fixture on a fresh clone. Idempotent (deterministic IDs), wipe-and-rebuild
  each run. Both this and the existing `seed.py` now refuse to run unless `APP_ENV=local`.
- `mise run db:test-create` provisions a dedicated `autohire_test` database; `mise run
  test` and `mise run docs:tests` now run pytest against it instead of the dev database.
  A session-scoped guard in `backend/tests/conftest.py` refuses to run the suite at all
  against anything but a `*_test` database, since teardown deletes every row in every
  table on every run — previously this silently wiped local dev/demo data (including the
  login session) on every `make test`/`make docs`.

### Fixed
- Post-merge review of PRs #37/#38/#39 (candidates screen, reopen-closed-job,
  icon polish): `Candidates.tsx` reimplemented five icons (`SparkleIcon`,
  `ArrowLeftIcon`, `FileIcon`, `CheckIcon`, `XIcon`) as local one-offs instead
  of using `components/ui/icons.tsx` — `SparkleIcon` was a byte-for-byte
  duplicate of that same PR's own `SparklesIcon`. Moved `ArrowLeftIcon`,
  `CheckIcon`, `XIcon` into the shared icon set; `Candidates.tsx` now imports
  all five from there (`FileIcon` usages replaced with the existing
  `FileTextIcon`).
- `useCandidates` (`frontend/src/lib/candidates.ts`) hardcodes `size=100`
  (the backend's hard max, `pagination_params`'s `le=100`) with no way to
  reach a job's submissions beyond that — a job with 100+ applicants
  silently truncated the "All submissions" table with no indication more
  existed. `Candidates.tsx` now reads the existing `total` field already
  returned by the `{items, total, page, size}` envelope and shows a "Showing
  N of total" note prompting a narrower search/status filter when truncated,
  rather than building a paging UI no other list in the app has yet.
- Reopen-a-closed-job (PR #38) was filed under story `US-06`, which was
  already `Done` and describes launching a job, not reopening one — no story
  file existed with acceptance criteria for the reopen behaviour. Backfilled
  as `docs/stories/TS-09.md`; `docs/drift.md` row 70's story column
  corrected to point at it.
- TS-08 (D-01): `make docs-erd` silently emitted `@startuml\n@enduml` for its entire
  history — `backend/app/scripts/dump_erd.py` imported only `app.core.db.Base`, never
  any model module, so `Base.metadata` was empty. Added `import app.models`; the
  script now emits all 12 entities with 20 FK edges, PK/FK markers, and nullability.
  Corrected the Makefile's `docs-erd` comment, which claimed the ERD is rendered "from
  the live database" — it reads SQLAlchemy metadata, never queries Postgres.
  `docs/drift.md` row 68.

### Changed
- `mise run db:seed-demo` now builds a minimal demo world instead of a full
  one: a single live job ("Backend Engineer") with every seed resume applied
  to it as a freshly `SUBMITTED` candidate — no other job statuses, no
  ranking/interview/email data. Matches the actual demo scenario needed
  (one live job, candidates at the applied stage) instead of exercising
  every status the UI can show.
- TS-08 (D-02, D-06): verified all four `make docs` targets — `docs:api` and
  `docs:uml` already correct, `docs:tests` (previously unverified) now confirmed
  passing: 217 tests, 93% coverage. Regenerated and committed `docs/generated/`
  (OpenAPI spec, ERD, class diagram, test report + coverage) against current `dev`.
  SDS/RS reconciliation (D-03/D-04/D-05) deferred — the submitted `.docx` files
  aren't present in this repo or filesystem; see `docs/stories/TS-08-summary.md`.
- TS-07 (Slice 1): replaced the single `APP_ENV=local|cloud` switch with four
  independent adapter settings — `RESUME_STORE`, `MAILER`, `CALENDAR_STORE`,
  `EMBEDDER` — each defaulting to today's local behaviour, so Drive/Gmail/Calendar
  can now be cut over one at a time per ADR-003's staged order instead of all at
  once. `APP_ENV` keeps exactly one job, the session cookie's `Secure` flag; zero
  `settings.app_env` references remain in `app/services/`. `candidate_service` and
  `job_service` branch on the returned `StoredFile` (`drive_file_id is None`) or on
  the relevant adapter setting instead of the environment. Hardened
  `DriveResumeStore.store_resume`'s multipart metadata to `json.dumps` instead of
  f-string interpolation. Deleted `fixtures.resume_url_for` (zero callers, verified
  by grep). Added a `REAUTH_REQUIRED` reconnect banner (`AppShell`, driven by
  `account_state`, already fetched on every authenticated page — not a new
  `http.ts` interceptor, since the failure can originate inside a Celery task with
  no request in flight) plus an error-message mapping in `apiErrorMessage` so an
  in-flight request's 409 points at the banner instead of reading like a generic
  failure. `api.d.ts`/`docs/openapi.json` unchanged — no route touched. Embedder
  decision: kept `fastembed` only (drift row 66); `sendUpdates` decision: left
  unset so AutoHire's own Gmail invite stays the single tracked email (drift row
  67). Slices 2-4 manually verified against real Google accounts — see below and
  `docs/stories/TS-07-summary.md`.
- TS-07 (Slices 2-4): manually verified `RESUME_STORE=drive`, `MAILER=gmail`, and
  `CALENDAR_STORE=google` end-to-end against real Google accounts, one at a time.
  Drive: job folder created, resume uploaded into it with the fix below, link opens.
  Gmail: invitation delivered (`delivery_status: SENT`, real `gmail_message_id`),
  redelivery correctly no-ops via the `idempotency_key` UNIQUE constraint. Calendar:
  event created at the correct Asia/Karachi local time (`04:30Z` UTC displays as
  `9:30am` local — confirms `starts_at.isoformat()`'s embedded UTC offset is read
  correctly with no explicit `timeZone` field), real joinable Meet link matching the
  API's `google_meet_link`. Full evidence, including a testing near-miss (an
  undersized fixture PDF tripped the `MIN_CHARS` scanned-document guard) and a
  self-caught idempotency-check bug (wrong ID passed on the first attempt), in
  `docs/stories/TS-07-summary.md`.
- TS-07 (Slice 2 prep): `ResumeStore.store_resume` gained an optional
  `display_name` parameter so `DriveResumeStore` can set the uploaded file's
  Drive-visible name to the candidate's actual resume filename (sanitized),
  while the server-generated uuid4 name (TC-08's path-traversal/overwrite
  guard) stays the actual storage key everywhere — local disk path, Drive
  lookup by `drive_file_id`, and the download response's filename are all
  unchanged. `display_name` is metadata-only for Drive, never a lookup key.
  Follow-up not done here: `Candidate` has no column for the original
  filename, so it isn't shown anywhere in the recruiter UI yet — only in
  Drive. Revisit if the UI needs it too.

### Fixed
- TS-06: post-review remediation — 13 items from an external review
  (2026-08-23) that ran the migrations on a virgin database, executed the
  suite, regenerated the API contract, and drove a cold end-to-end pipeline
  run. Every item was reproduced before fixing (none were NOT REPRODUCED),
  one commit per item with a regression test that failed before the fix.
  - **R-01**: `Jobs.tsx`'s AI-process button was enabled exactly when the
    backend refused (`LIVE`) and disabled exactly when it would accept
    (`CLOSED`+candidates). Extracted `canProcessJob()` to `lib/jobs.ts` as
    the single source of truth, matching `task_service.enqueue_resume_parse`.
  - **R-02**: a `PARSE_ERROR` candidate left over after a rank run could
    never be retried once the job flipped to `PROCESSED` — widened
    `enqueue_resume_parse`'s guard to `(CLOSED, PROCESSED)`, mirroring
    `enqueue_batch_ranking`.
  - **R-03**: `.doc` (OLE2) was sniffed and accepted at upload, but
    `extract_text` has no handler for it — every `.doc` candidate silently
    became `PARSE_ERROR`. Rejected at upload (415) instead; `Apply.tsx`
    advertises `.pdf,.docx` only.
  - **R-04**: `PATCH /interviews/{id}` and `POST /emails/send` still read
    `app/api/fixtures.py` — the former 404'd on every real slot, the latter
    always returned a stale fixture `TaskOut` whose `task_id` 404'd at
    `GET /tasks/{id}`. Both are genuinely Phase 2; replaced with an honest
    `501 NOT_IMPLEMENTED`.
  - **R-05/R-06**: `GET /auth/me`/`PATCH /recruiters/me` didn't declare
    `401`; `POST`/`PATCH /jobs` declared `502` but not the `500`
    `finalize_launch` raises in local mode. Declared both — first
    intentional `api.d.ts` regeneration since TS-02.
  - **R-07**: `JobUpdate` had no future-date validator (`JobCreate` did) — a
    `PATCH` with a past `expires_at` left a job `LIVE` while the public
    endpoint immediately 410'd. Factored one shared validator.
  - **R-08**: `JobBuilder.tsx`'s `expiresAtToDateInput` read the UTC date
    from an ISO string while `dateToExpiresAt` wrote local `23:59:59` — at a
    negative UTC offset, re-saving the edit form walked the deadline forward
    a day per save. Now derives the local calendar date via
    `toLocaleDateString("en-CA")`; both helpers moved to `lib/jobs.ts`.
  - **R-09**: removed confirmed-dead code — `paginate()`, `ALLOWED_RESUME_TYPES`,
    `PINECONE_API_KEY`/`PINECONE_INDEX` — and dropped
    `job_postings.google_form_id`/`.google_form_url` and
    `background_tasks.retry_count` via a reversible migration. Kept
    `OPENAI_API_KEY` and `scheduling_preferences.last_synced_at`, both
    reserved for TS-07.
  - **R-10**: `calendar_sync`'s candidate query had no `job_id`/`deleted_at`
    scoping (a soft-deleted candidate could still be scheduled and emailed),
    and its `IntegrityError` handler always reported `"ALREADY_SCHEDULED"`
    regardless of which partial-unique index fired. Fixed both; added
    `"SLOT_TIME_TAKEN"` as a distinct reason.
  - **R-11**: tests only. Covered the `except Exception -> FAILED` path in
    both `calendar_sync` and `batch_ranking`, `calendar_sync`'s `NOT_RANKED`
    race branch, and — the larger gap — `interview_service.py`'s
    `enqueue_scheduling` happy path, `list_slots`, and
    `available_slots_for_recruiter`, none of which had ever actually been
    exercised through their HTTP routes.
  - **R-12**: synced `docs/stories/README.md` statuses from the story files
    (all Todo -> actual Done/Done-backend), sorted `docs/drift.md`'s
    out-of-order rows, added drift rows 58-64 for this story's behaviour
    changes.
  - **R-13**: added a real apply-flow journey to the e2e suite (create
    template + job via API as the seeded recruiter, submit through
    `/apply/{slug}` in the browser, assert success then duplicate-email
    rejection) — `smoke.spec.ts` alone was one trivial assertion for the
    cost of a full Docker build.

### Added
- US-24/US-26/US-27: Scheduling and Emails screens (frontend) — the last
  two backend-ready screens with no UI. New `/scheduling` route: an
  availability form (`GET`/`PUT /scheduling/preferences` — days, hours,
  slot length) plus a real interview list (`GET /interviews`, filterable by
  job/status, with a working Meet link per row). New `/emails` route: a
  read-only delivery log (`GET /emails`, filterable by job/type) for
  automated candidate emails. Both wired into the sidebar, which previously
  had them permanently disabled ("Coming soon").
- The Candidates screen's "Mark Interview Invited" button was a bare status
  PATCH — no calendar event, no email, nothing real, despite Moazzam's
  US-26/US-27 backend already existing to do exactly that. Replaced it with
  a real **"Schedule interview"** action (on both the ranked card and the
  candidate detail modal) that calls `POST /interviews`, polls the returned
  `CALENDAR_SYNC` task the same way "Run AI ranking" does, and reports the
  outcome from the task's `result_summary` (`scheduled`/`unscheduled` with a
  reason, e.g. "no available slot in the next 14 days — check your
  availability"). `nextStatusOptions` no longer offers a direct
  `RANKED -> INVITED` PATCH — scheduling a real interview is the only path
  now, so the UI can't imply one happened when it didn't. Verified against
  the real backend end-to-end: a scheduled candidate produces a real
  Calendar event (Meet link), a real Gmail invite logged in `email_logs`,
  and shows up in both new screens.
- Templates and Apply pick up the shared icon set introduced alongside the
  Candidates screen: Templates' table Edit/Delete actions are now icon-only
  buttons (pencil, trash) with hover tooltips instead of plain text links,
  Templates' empty state gets a contextual `FileTextIcon`, and Apply's
  "Application received" confirmation gets a `CheckCircleIcon`. Templates
  page also no longer shows a duplicate "+ Create template" button — the
  top-right one and the empty state's own action button were both present
  at once.
- Template delete confirmation: the "referenced by a job posting" error was
  rendering behind the modal's own backdrop and effectively invisible — an
  open `<dialog>` renders in the browser's top layer, above everything else
  in the document including a `position: fixed` toast, so the toast was
  dimmed underneath it. Fixed by using `Modal`'s existing `errorText` prop
  (rendered inside the top-layer dialog itself) instead of a toast for this
  case.
- TS-09: reopen a closed job (filed under `US-06` at merge time; that story
  was already `Done` and unrelated — see `docs/stories/TS-09.md`).
  `job_service._LEGAL_TRANSITIONS` gains
  `CLOSED -> LIVE` (previously the job lifecycle was strictly one-way,
  `DRAFT -> LIVE -> CLOSED -> PROCESSED` — see `docs/drift.md` row 70).
  Reopening requires a future `expires_at` (the payload's if provided, else
  the job's existing one) or 409s `REOPEN_REQUIRES_FUTURE_EXPIRY`, so a job
  can never come back `LIVE` already expired, and auto-sets
  `is_accepting_responses = True`. Deliberately scoped to `CLOSED` only —
  `PROCESSED -> LIVE` stays illegal, since a processed job already has
  ranked/invited/scheduled candidates that a fresh applicant pool would need
  a re-ranking story to reconcile with. Frontend: `JobBuilder.tsx`'s existing
  "Application deadline" field (already editable while editing a job)
  doubles as the new deadline; a "Reopen job" action appears when editing a
  `CLOSED` job, submits `{status: "LIVE", expires_at}` in one call, and
  shows the specific "must be in the future" validation client-side before
  ever hitting the API. Four new backend tests in `test_jobs.py` cover
  reopen-with-future-expiry, reopen-keeping-an-already-future expiry, the
  409 case, and confirming `PROCESSED -> LIVE` is still rejected. Its
  "you need a template first" empty state also picked up a contextual icon
  (`FileTextIcon`) from the shared icon set introduced alongside the
  Candidates screen.
- "Run AI ranking" now explains itself when disabled instead of just fading
  out: a distinct amber/warning-styled button reading "Can't rank until job
  is closed" with a lock icon, replacing the generic greyed-out primary
  button (which only explained why via a hover tooltip a recruiter had to
  find).
- Undo a candidate rejection. `candidate_service._LEGAL_TRANSITIONS` gains
  `REJECTED -> {PARSED}` (see `docs/drift.md` row 69). Undo lands on
  `PARSED`, not `RANKED`: `ranking_service.list_ranked_candidates` INNER
  JOINs `ai_analysis_results`, so setting `RANKED` directly (the first
  version of this fix) produced a candidate whose status claimed it was
  ranked while the AI-ranked list could never actually show it — caught via
  manual testing before merge. `PARSED` accurately means "eligible for the
  next ranking run," and a re-run of "Run AI ranking" picks it up for real
  (`_RANKABLE_STATUSES` already includes `PARSED`). Deliberately no direct
  `REJECTED -> INVITED` "schedule interview" shortcut either (a second
  version had one, also dropped after manual QA) — a recruiter undoes the
  rejection first and invites from `PARSED` like any other candidate, one
  obvious way back into the pipeline instead of two overlapping buttons on
  the same screen. `DECLINED` deliberately stays terminal — it records the
  candidate's own answer, not a recruiter judgement call, so there's nothing
  to undo there. Backend tests cover the undo edge, confirming
  `REJECTED -> INVITED` still 409s, and confirming `DECLINED` still 409s.
  Frontend: the existing `StatusActions` component (shared by the candidate
  detail modal and the AI-ranked cards) now renders the extra action
  automatically since it's driven by the same `nextStatusOptions` map, with
  the `REJECTED -> PARSED` button reading "Undo rejection" instead of the
  generic "Mark Parsed".
- Clicking a card in the AI-ranked tab now opens the same candidate detail
  modal the All-submissions table uses, instead of doing nothing —
  `RankedCard` gained an `onOpen` handler wired to the same `selectedId`
  state, with `stopPropagation` on its nested resume link and status-action
  buttons so they don't also trigger the card's own click.
- Fixed a stuck toast: triggering AI ranking's "AI ranking started." toast
  used the `loading` variant, which by design never auto-dismisses (there's
  no fixed duration for "still running") — but nothing ever dismissed it, so
  it sat pinned at the bottom-right of the screen indefinitely even after
  ranking finished. `Toast`'s `showToast` now returns the toast's id and the
  provider exposes `dismissToast(id)`; `Candidates.tsx` captures the loading
  toast's id and dismisses it the moment the polled task reaches a terminal
  status, right before showing the success/failure toast.
- Jobs list: clicking anywhere on a job card now opens its Candidates page
  (previously only a separate "Candidates" text link did, which is now
  removed as redundant). "Copy link" and "View / Edit" are now icon-only
  buttons (a chain-link icon, a pencil) with hover tooltips, consistent with
  the Templates table's icon-only actions from the same pass. Card clicks
  from the icon buttons and the "AI process" button call `stopPropagation`
  so they don't also navigate the card.
- Icon pass across empty/success states and list actions, per direct UX
  feedback that the generic dot/text-only UI "looks bad": new shared
  `components/ui/icons.tsx` (`BriefcaseIcon`, `UsersIcon`, `FileTextIcon`,
  `SparklesIcon`, `InboxIcon`, `AlertTriangleIcon`, `CheckCircleIcon`,
  `LinkIcon`, `PencilIcon`, `TrashIcon`, `LockIcon`). `EmptyState`'s default
  icon is now a real inbox/alert-triangle glyph instead of a "·"/"!"
  placeholder character, and `DataTable` gained an `emptyIcon` passthrough.
  Wired a contextual icon into Jobs' and Candidates' empty states (both
  tabs) as the first usages — Templates, JobBuilder, and Apply pick up the
  same icon set in follow-up commits.
- Candidate-status-update errors triggered from inside the candidate detail
  modal now render via `Modal`'s existing `errorText` prop instead of a
  toast: an open `<dialog>` renders in the browser's top layer, above
  everything else in the document including a `position: fixed` toast, so
  an error toast raised from inside one renders dimmed and effectively
  invisible underneath the modal's own backdrop. New optional `onError`
  prop on `StatusActions` carries the message up to the modal (defaults to
  a toast for the non-modal AI-ranked-card usage, which doesn't have this
  problem).
- Modal component (`components/ui/Modal.tsx`) redesign — the native `<dialog>` was
  rendering pinned to the top-left instead of centered: Tailwind's preflight resets
  `margin` globally, which silently breaks the browser's default dialog-centering
  algorithm. Fixed with explicit `fixed inset-0 m-auto`. Also, per direct UX
  feedback (a sketch marked up over a screenshot): added a proper header with an X
  close button (replacing the always-present "Cancel" text button, which now only
  renders for the two-button confirm variant, e.g. Templates' delete confirmation —
  content-only modals like the candidate profile no longer show a redundant Cancel
  below their own action buttons), a `size="lg"` variant for content-heavy modals,
  backdrop-click-to-close, and an entrance animation. Candidates' detail modal now
  shows an avatar-initials header and equal-width/equal-height action buttons with
  icons, replacing mismatched auto-width text buttons. This is a standing
  expectation for every future screen, not a one-off — see memory
  `feedback_ux_polish_beyond_figma`. Two follow-up fixes on the same
  component: (1) a long body no longer grows the whole dialog past the
  viewport and scrolls the header/close-button and footer/action-buttons out
  of view — the header and footer are now `shrink-0` and only the body
  (`min-h-0 flex-1 overflow-y-auto`) scrolls, plus a new `footer` prop so a
  dynamic action set (like the candidate profile's status buttons) can live
  in that fixed footer instead of inside the scrolling body; (2) the page
  behind the modal no longer stays scrollable while it's open —
  `showModal()` doesn't lock body scroll on its own, so `Modal` now sets
  `document.body.style.overflow = "hidden"` for as long as it's open.
- US-13/US-18-19: Candidates screen (frontend) — the submissions table and
  AI-ranked shortlist Moazzam's backend already exposed had no UI. New
  `/jobs/:jobId/candidates` route with two tabs: **All submissions**
  (`GET /jobs/{id}/candidates`, search + status filter, click a row for a detail
  modal with form responses and a resume link) and **AI ranked**
  (`GET /jobs/{id}/candidates/ranked`, reusing the existing `MatchScore` component
  for the semantic score bar plus matched/missing skill chips and the keyword-match
  feedback text). "Run AI ranking" triggers `POST /jobs/{id}/rank` and polls the
  returned task via a new shared `useTask` hook (`GET /tasks/{id}`, stops polling on
  a terminal status) — the same pattern `useTriggerProcess` will want next time it's
  touched. Status changes (`PATCH /candidates/{id}`) are gated client-side by a
  `nextStatusOptions` map mirroring `candidate_service._LEGAL_TRANSITIONS`, so only
  legal actions (e.g. "Mark Rejected", "Mark Interview Invited") render — the server
  stays the actual authority, a stale client copy just means a 409 to retry against.
  `resume_url` is either an absolute Drive link or a backend-relative local download
  path; added `resumeHref()` since the frontend runs on a different port than the
  API in dev and a relative path would resolve against the wrong origin.
  `matched_skills`/`missing_skills`/`ai_feedback_summary` come from a deterministic
  keyword-overlap heuristic (`LocalAnalyzer`, ADR-003), not an LLM — worth knowing
  before writing UI copy that implies otherwise. Extended `StatusBadge`'s `Status`
  union with the submission statuses (`Submitted`, `Parsed`, `Ranked`, `Declined`,
  `Parse Error`) rather than duplicating the badge component. Added `Jobs.tsx` a
  "Candidates" link (with a live submission count) alongside the existing
  "View / Edit" link. Added two small reusable motion tokens (`animate-fade-in`,
  `animate-slide-up`) to `tokens.css` — respects the existing
  `prefers-reduced-motion` override — used on the detail modal, ranked cards, and
  toast entrance; applying UX polish beyond the static Figma prototype is now a
  standing expectation for every future screen, not just this one.
- US-26/US-27: auto-scheduled interviews and invitation email — the last story
  in Phase 1; the pipeline now runs end to end (sign in -> template -> launch
  job -> apply -> parse -> rank -> schedule -> email in Mailhog). Two commits:
  - **Scheduling.** `interview_slots` (partial UNIQUE
    `uq_interview_slots_candidate_live` on `candidate_id` — one live slot per
    candidate, history retained on reschedule; partial UNIQUE
    `uq_interview_slots_recruiter_time` as a concurrency backstop for
    exact-timestamp double-booking). `POST /interviews` validates job/candidate
    ownership, that every candidate is `RANKED` (422 otherwise), a
    `scheduling_preferences` row exists (409 `NO_SCHEDULING_PREFERENCES`), and
    no other active task is running for the job, then enqueues `CALENDAR_SYNC`
    — same plumbing as `RESUME_PARSE`/`BATCH_RANKING` (row committed before
    `.delay()`, `uq_background_tasks_job_active` widened to include
    `CALENDAR_SYNC`). `interview_service.generate_slots` reads
    `ZoneInfo(scheduling_preferences.timezone)` for the row being scheduled
    against, never the live `SCHEDULING_TIMEZONE` setting (ADR-005), and
    rejects any candidate slot overlapping an existing live slot's own
    `[scheduled_at, scheduled_at + duration_minutes)` interval — not merely an
    exact-timestamp match, so a changed `slot_duration_minutes` between runs
    can't produce an undetected overlap. `CalendarStore` is the third resource
    adapter (`LocalCalendarStore` / `GoogleCalendarStore` through
    `google_call`, `ResumeStore`'s shape exactly). Ordering as in US-06: the
    slot row commits, then the Calendar event is created, then the row updates
    with the event id — no DB transaction held across the Google call; a
    Calendar failure leaves the slot present and retryable, and the candidate
    stays `RANKED`, never `INVITED` with nothing. A candidate with no slot
    available in the 14-day horizon, an already-live slot, or a Calendar
    failure is recorded — never silently dropped — in a new
    `background_tasks.result_summary JSONB` column
    (`{scheduled, unscheduled: [...], horizon_days}`), polled at
    `GET /tasks/{task_id}` (now wired to real data — see below).
  - **Email.** `email_logs` (`idempotency_key = "{candidate_id}:{email_type}:
    {slot_id or 'none'}"`, UNIQUE — the entire dedupe mechanism; no
    application-level check on top of it). `EMAIL_DISPATCH` is enqueued once a
    slot's Calendar event exists, claims its idempotency key (insert + commit)
    *before* attempting the send, then renders one fixed `INTERVIEW_INVITE`
    template (candidate name, job title, date/time in the recruiter's saved
    timezone, duration, Meet link — one template, not a template system) and
    sends via `Mailer` (`LocalMailer` — stdlib `smtplib` against the existing
    Mailhog service, 10s timeout to fail fast into the retryable path rather
    than hang the worker; `GmailMailer` through `google_call`). A send failure
    never rolls back the slot — `delivery_status` records `FAILED`, the
    interview stays booked. `email_logs.sent_at` is set at claim time (attempt
    started), not delivery time, so a `PENDING` row's age distinguishes a
    stalled attempt from a genuinely in-flight one. `GET /jobs/{id}/emails` and
    `GET /jobs/{id}/slots` retire the last of `fixtures.CANDIDATES`
    (`candidate_name()`), wired instead at the existing top-level
    `GET /interviews`/`GET /emails` paths per ADR-004 P2 (docs/drift.md row 52).
  - `GET /tasks/{task_id}` is real for the first time — it was left a TS-02
    stub through three prior stories that each built their own job-scoped
    status endpoint instead of ever wiring the generic poll target ADR-004 P4
    promises (docs/drift.md row 56).
- US-24: recruiter availability windows. `scheduling_preferences`
  (`UNIQUE(recruiter_id)` — one row per recruiter, ever), real
  `GET`/`PUT /scheduling/preferences` replacing the TS-02 stub. `PUT` upserts,
  never 409; `available_days` normalized (case-folded, deduped, sorted
  Monday-first) and rejected if empty or containing an unrecognized day;
  `slot_duration_minutes` bounded 15–120 and must fit inside the
  `[available_start_time, available_end_time)` window. `GET` before any `PUT`
  returns synthesized Mon–Fri/09:00–17:00/30min defaults with
  `preference_id: null` rather than 404 — nothing is persisted by a read.
  Times are wall-clock, not UTC: interpreted in a new app-wide
  `SCHEDULING_TIMEZONE` setting (default `Asia/Karachi`), copied onto each row
  at insert time via a new `timezone` column and never rewritten by a later
  update, so a saved row keeps its original meaning even if the setting
  changes. Four CHECK constraints (`ck_scheduling_preferences_window`,
  `_days_valid`, `_slot_duration`, plus the `UNIQUE`) mirror the Pydantic
  validation as invariants-of-last-resort, unreachable through the validated
  API. `scheduling_service.py` follows `template_service.py` conventions
  (explicit `recruiter_id` scoping, rollback-and-500 on unexpected
  `IntegrityError`).
- US-18/US-19: semantic scoring and the ranked shortlist. `ai_analysis_results`
  (pgvector `embedding` column, dimension read from `EMBEDDING_DIM`, never a
  literal), `Embedder`/`VectorStore`/`ResumeAnalyzer` Protocols behind
  `app/adapters/` (`FastEmbedEmbedder` — `all-MiniLM-L6-v2` via ONNX/fastembed
  instead of sentence-transformers, same model and 384 dims without pulling
  PyTorch; `PgVectorStore`'s cosine similarity is the whole of
  `semantic_score`, no LLM-produced number ever reaches it; `LocalAnalyzer` is
  deterministic and offline per ADR-003). A `BATCH_RANKING` background task
  mirrors `RESUME_PARSE`'s shape exactly, triggered by a new
  `POST /jobs/{id}/rank` (202 `TaskOut`, same pattern as `/process`). Only
  `PARSED`/`RANKED` candidates are scored — `PARSE_ERROR` and `SUBMITTED` are
  skipped, never ranked zero. `GET /jobs/{id}/candidates/ranked` is wired to
  real data, closing the last `fixtures.CANDIDATES` read path with a real
  counterpart. `jd_embedding_id` is populated as a
  `{model}:{dim}:{sha256(jd)[:16]}` provenance ref, closing drift row 28.
  `JobDetailOut.processed_at` is null until a job's first successful rank.
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
