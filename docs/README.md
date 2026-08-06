# Documentation model

## Source of truth

**The code is the source of truth. The documents are generated from it.**

The Phase I RS and Phase II SDS were written before implementation. Their ERD, class
diagram, API table, and use cases are a *design baseline* — directionally right, not
binding. Where reality and the baseline disagree, reality wins and we record the drift.

| Artifact | Source of truth | How the report version is produced |
|---|---|---|
| Database schema | Alembic migrations | `make docs-erd` — rendered from the live DB |
| API contract | FastAPI route definitions | `make docs-api` — OpenAPI dump |
| Class diagram | SQLAlchemy models + services | `make docs-uml` — pyreverse |
| Test evidence | the test suite | `make docs-tests` — HTML report + coverage |
| Requirements | `docs/stories/` | already narrative |
| Decisions | `docs/decisions/` | already narrative |

`make docs` runs all four. Do it before every advisor meeting and before submission.

Nobody hand-updates an ERD in this project. Hand-maintained diagrams go stale within
two sprints and then quietly lie to you — and to your examiner.

## Reference documents

`docs/schema.md`, `docs/api-contract.md` and `docs/architecture.md` are **working
notes**, not contracts. They exist so a Claude Code session starts with context instead
of guessing. Update them when they get badly wrong, but don't agonise — the generated
artifacts are what count.

`docs/design.md` is different: it *is* binding, because design tokens with no authority
produce nineteen inconsistent screens.

## Files with an expiry date

Two files here are scaffolding, useful now and misleading later:

- **`docs/schema.md`** — delete it once SQLAlchemy models exist. The models are then
  the schema, and `make docs-erd` is the diagram. A second hand-written copy will drift.
- **`docs/api-contract.md`** — keep only the *Conventions* section once real routes
  exist. The endpoint table is superseded by generated OpenAPI.

Delete them when the time comes. Stale documentation is worse than none, because
someone (or Claude Code) will believe it.

## Drift log

Every deviation from the submitted RS/SDS goes in `docs/drift.md`. At submission you
turn that file into the revision history and the "design evolution" section, instead of
trying to remember eight months later why the schema doesn't match the diagram.

Drift is expected and healthy. Undocumented drift is what loses marks.
