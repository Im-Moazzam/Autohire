# Testing strategy

Proportionate to a two-person team. The goal is confidence to refactor, not a coverage
number. Coverage gate is 70% on `app/services/` only — the layer where the logic lives.

## Layers

**Unit (pytest)** — services, validators, parsers, scoring, slot allocation. No DB, no
network. Fast. This is the bulk of the suite.

**Integration (pytest + real Postgres)** — routes through to the database, using the
`Local*` adapters. Covers tenant isolation, pagination, transactions, constraint
behaviour. Runs against a real pgvector container in CI, never SQLite — SQLite will
happily accept things Postgres rejects and you will find out in production.

**Component (Vitest + React Testing Library)** — UI primitives and the states above.
Assert what a user sees, never implementation detail. No `getByTestId` where a role or
label works.

**E2E (Playwright)** — three journeys only, kept green:
1. Recruiter signs in → creates template → launches job → copies apply link
2. Candidate opens link → submits application + resume → sees confirmation
3. Recruiter triggers processing → ranked list appears → opens candidate evidence

These three are your demo script. If they pass, you can demo. Add a fourth for
scheduling once US-26 lands.

## Non-negotiable test cases

Regardless of coverage, these exist by name — each maps to a real risk in the register:

- A recruiter cannot read another recruiter's jobs, candidates, templates, or emails
- A malformed PDF marks one candidate `PARSE_ERROR` and the batch completes
- Sending the same email twice produces one `email_logs` row and one delivery
- An expired job rejects submissions
- A file with a `.pdf` extension but a non-PDF magic number is rejected
- `invalid_grant` sets `REAUTH_REQUIRED` and returns 409, and does not retry
- Two candidates cannot be scheduled into the same slot

## Fixtures

`factory_boy` for model factories. One `seed` script producing a demo recruiter, two
templates, one closed job, and ~15 sample resumes of varying quality including two
deliberately corrupt. Commit the sample resumes — reproducible AI testing needs a fixed
corpus, and it doubles as your validation set for TR-02.

## Evidence

`make docs-tests` produces an HTML report and coverage summary. Run before each sprint
review; the output is your IV&V appendix.
