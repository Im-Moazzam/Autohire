# TS-08 summary — D-01, D-02, D-06 (partial)

**Status:** In progress. D-03/D-04/D-05 (SDS/RS reconciliation, `.docx` format check)
are blocked and out of scope for this session — see "Blocked" below.

## D-01 — `make docs-erd` fixed

`backend/app/scripts/dump_erd.py` imported only `app.core.db.Base`, never any model
module, so `Base.metadata` was empty and the script emitted `@startuml\n@enduml` for
its entire history.

Fix:
- Added `import app.models  # noqa: F401` so every model registers on `Base.metadata`
  before it's read.
- Added FK edge output (`table }o--|| other`), a `+` marker on FK columns, and a
  `NOT NULL` suffix on non-nullable columns — the script previously emitted a column
  list, not a relationship diagram.
- The Makefile's `docs-erd` comment claimed the ERD is rendered "from the live
  database." It isn't — it reads SQLAlchemy metadata, never queries Postgres. Corrected
  the comment rather than building live-DB introspection, which nothing else in this
  script needs.

**Proof:** `docker compose exec -T api python -m app.scripts.dump_erd` now emits **12
entities and 20 FK edges** (all confirmed against `app/models/__init__.py`'s 11 model
classes across 12 tables — `Candidate`/`CandidateFormResponse` both live in
`candidate.py`). Output committed at `docs/generated/erd.puml`.

Not rendered to PNG/SVG: no `plantuml` binary is available locally or in the API
container, and the project's own `docs-uml` target has never rendered its `.puml`
output either — the Makefile explicitly punts rendering to "plantuml.com or the
PlantUML CLI" as a manual step (`Makefile:53`). Committing `.puml` source matches
existing convention rather than inventing a new one for this target alone.

## D-02 — all four `make docs` targets verified

| Target | Result |
|---|---|
| `docs:api` | Confirmed matching — generated OpenAPI (`app.openapi()`) is byte-for-byte semantically equal to the committed `docs/openapi.json` |
| `docs:uml` | Confirmed working — `pyreverse` produces `classes_AutoHire.puml` / `packages_AutoHire.puml` in `docs/generated/` when the target directory pre-exists (the Makefile's `mkdir -p docs/generated` ahead of the call is load-bearing; `pyreverse -d` silently falls back to the cwd if the directory is missing) |
| `docs:erd` | Fixed under D-01 |
| `docs:tests` | Previously unverified — now run for real: **217 tests passed, 93% coverage**, HTML report + coverage HTML written to `docs/generated/` |

Nothing else was broken.

## D-06 — generated artifacts regenerated and committed

`docs/generated/` now contains, from the current `dev`-based build:
- `openapi.json`
- `erd.puml`
- `classes_AutoHire.puml`, `packages_AutoHire.puml`
- `test-report.html`, `coverage/` (HTML report)

Final numbers: **217 tests passing, 93% coverage.**

## Drift log

Added row 68: the ERD generator bug itself. A generated artifact silently emitting
`@startuml\n@enduml` for its entire history is the exact failure mode
`docs/README.md`'s "code is the source of truth" model exists to prevent, so it's
recorded as drift rather than folded silently into the fix.

## `.env` reset

Per session start: `RESUME_STORE` / `MAILER` / `CALENDAR_STORE` reset from
`drive`/`gmail`/`google` (TS-07 manual-verification state) back to `local` for
day-to-day dev. `api`/`worker` containers recreated to pick up the change.

## Blocked — D-03, D-04, D-05

The submitted SDS `.docx` and RS `.docx` are not present anywhere in this repository
or on this filesystem — searched the full working tree and a filesystem-wide glob for
`*SDS*`/`*RS*`/`*.docx`; the only `.docx` found is an unrelated test fixture
(`backend/tests/fixtures/resumes/word_doc_resume.docx`). `docs/README.md` confirms
the RS/SDS are external submitted documents, never tracked in this repo.

Per user direction, this session proceeds without them. Deferred:
- D-03: SDS deviations front-matter section, inline "superseded — see drift row N"
  markers, the four outright factual-error corrections (`api_name_enum` members,
  `is_accepting_responses` default, `pinecone_vector_id`→`vector_id`,
  `google_form_id` NOT NULL), and replacing the schema section with the fixed D-01
  generator output.
- D-04: same treatment for the RS.
- D-05: verifying whether the `.docx` files are genuine OOXML or (per the story's own
  suspicion) markdown mis-extracted by a Projects uploader.

**Before/after mention counts:** not established — the documents were never located,
so no counts exist to compare. The story's own figures (SDS: Pinecone 10, Google Forms
12, pgvector 0, fastembed 0, apply_slug 0; RS: Pinecone 9, Google Forms 21) come from a
prior review's plain-text extraction, not from a file this session could open or edit.

**Next step:** locate the actual submitted `.docx` files (an absolute path, or
confirmation they need to be re-exported from wherever the Projects extraction came
from), then resume D-03/D-04/D-05 in a follow-up session.

## Amendments applied (per session brief, not story text)

- **Amendment 1** (Google integration claims are now TRUE post-TS-07): not yet
  actionable — no SDS/RS access this session, so no passages were marked either way.
  Recorded here so a follow-up session doesn't mark Drive/Gmail/Calendar passages
  superseded by mistake.
- **Amendment 2** (`architecture.md`/ADR-003 already reconciled): verified. ADR-003's
  decision section already documents the four per-adapter settings (TS-07) and
  correctly attributes the Pinecone/OpenAI drops to drift rows 10 and 47/66-67. Left
  untouched, as directed.
- **Amendment 3** (drift rows 58-67 reflect new deviations): confirmed present —
  `.doc` rejection (row 59), `google_form_id`/`google_form_url` column drop (row 63),
  and the four-setting adapter split (row 65) are all recorded. No SDS/RS access this
  session to reflect them inline, but the drift rows themselves needed no fixing.
