# AutoHire

AI-powered recruitment automation. Resume parsing, semantic ranking, and agentic
interview scheduling over Google Workspace.

FYP — Group S26SE012, University of Central Punjab.
Moazzam (Scrum Master / Dev) · Saif-ur-Rehman (Full Stack / QA) · Nimra Yousaf (Docs)
Advisor / Product Owner: Mohsin Sami

## Quick start

Requires [mise](https://mise.jdx.dev/) to manage the Python and Node versions
(`.mise.toml` pins them). Postgres, Redis, and Mailhog stay in Docker — mise
doesn't touch those.

```bash
mise trust                    # one-time, per clone
cp .env.example .env          # fill TOKEN_ENCRYPTION_KEY, leave Google blank for now
make setup                    # mise install + pre-commit hooks + npm install
make up
make migrate
make seed
```

- App: http://localhost:5173
- API docs: http://localhost:8000/docs
- Mail catcher: http://localhost:8025

Runs fully offline with `APP_ENV=local` — no Google account, no API keys, no cost.
See `docs/decisions/ADR-003`.

## Docs

**Code is the source of truth; report artifacts are generated (`make docs`).**
See `docs/README.md` for the documentation model.

| File | What it is |
|---|---|
| `CLAUDE.md` | Working agreement — read this first |
| `docs/README.md` | How docs work here, and what's generated |
| `docs/drift.md` | Deviations from the RS/SDS baseline |
| `docs/checklists/` | UX, testing, and PR checklists |
| `docs/schema.md` | Current entity shape (working notes) |
| `docs/architecture.md` | Layers, adapters, AI pipeline |
| `docs/api-contract.md` | Endpoint conventions |
| `docs/design.md` | Design system and tokens |
| `docs/decisions/` | ADRs — settled questions |
| `docs/stories/` | Story briefs with acceptance criteria |
| `CHANGELOG.md` | What has actually been built |

## Workflow

`main` (protected) ← `dev` ← `feat/US-XX-slug`. PR into `dev`, reviewed by the other
developer, squash merge. Tag at each sprint demo.

Claude Code: `/story US-06` to build, `/review` before the PR, `/wrap` to close out.
One story per session, `/clear` in between.
