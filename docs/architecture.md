# Architecture

Layered architecture, per SDS Phase II §1. Four layers, one rule that matters more
than the rest: **the application layer never imports a vendor SDK.**

```
Presentation   React SPA (recruiter shell) + public apply page
     |
API            FastAPI routers under /api/v1   — validation, authz, pagination
     |
Services       business logic. Pure Python. Depends on Protocols, not vendors.
     |         |
Adapters       LocalDrive/GoogleDrive, LocalMail/GmailMail, LocalCal/GoogleCal,
     |         PgVectorStore/PineconeStore, LocalEmbedder/OpenAIEmbedder, LLM
     |
Data           PostgreSQL + pgvector (SQLAlchemy), Redis (Celery broker)
```

## The adapter rule

Every external dependency sits behind a Python `Protocol` in `backend/app/adapters/base.py`,
with two implementations: a local one and a real one. Each adapter reads its own setting —
`RESUME_STORE`, `MAILER`, `CALENDAR_STORE`, `EMBEDDER` — independently of the others
(TS-07; see ADR-003). `APP_ENV` no longer selects an adapter; it governs deployment
semantics only (e.g. the session cookie's `Secure` flag).

```python
class ResumeStore(Protocol):
    def create_job_folder(self, recruiter: Recruiter, job_id: UUID, name: str) -> str: ...
    def store_resume(
        self, recruiter: Recruiter, job: JobPosting, filename: str, content: bytes
    ) -> StoredFile: ...
```

`store_resume` (US-12) always receives a server-generated `filename`
(`{uuid4}.{validated-extension}`) — the candidate's raw filename never reaches an
adapter. `content` is already validated (magic bytes) and size-capped by the time an
adapter sees it; adapters are storage, not validation. `StoredFile` carries
`storage_key` (local path, or the Drive file id) plus, in cloud mode, `drive_file_id`
and `drive_url`.

| Concern | Setting | Local | Cloud |
|---|---|---|---|
| Resume storage | `RESUME_STORE=local\|drive` | `./storage/resumes/` | Google Drive |
| Email | `MAILER=local\|gmail` | Mailhog SMTP (`http://localhost:8025`) | Gmail API |
| Calendar | `CALENDAR_STORE=local\|google` | in-memory free/busy fake | Google Calendar |
| Vector store | — | pgvector | pgvector (Pinecone dropped, drift row 10) |
| Embeddings | `EMBEDDER=fastembed` (only value implemented) | `all-MiniLM-L6-v2` (384-dim, free) | not built — `NotImplementedError` (drift, TS-07) |
| LLM feedback | — (reserved `OPENAI_API_KEY`, not wired) | canned deterministic text | not built |

Each row above is switched independently — cutting Drive over does not require
Gmail, Calendar, or the embedder to move too. Integration order per ADR-003:
Drive -> Gmail -> Calendar -> embedder decision.

Why this earns its keep:
- Tests run with no network, no API keys, no quota burn, no flakiness.
- You develop the entire pipeline before Google verification is sorted.
- Cutting one Google service over doesn't force the others — a Drive-only
  demo, or a Drive+Gmail demo with Calendar still local, both just work.
- If an OpenAI embedder is ever built, `FastEmbedEmbedder` and it will have
  **different dimensions** (384 vs 1536). Read the dimension from config
  everywhere — hardcoding either will silently corrupt the vector index.

Adapters are also where `api_usage_logs` rows get written. One place, exact counts.

## Google token handling

Every Google call goes through `adapters/google/session.py`:

1. Decrypt the recruiter's refresh token
2. Refresh the access token if expired
3. Make the call
4. On `invalid_grant` → set `account_state = REAUTH_REQUIRED`, raise `ReauthRequired`
5. On 429/5xx → exponential backoff, max 3 attempts
6. Write the `api_usage_logs` row

The API layer turns `ReauthRequired` into HTTP 409 with `{"code": "REAUTH_REQUIRED"}`.
The frontend shows the "Reconnect Google" banner. This is US-03, and because of the
7-day testing-mode token expiry (ADR-002) you will exercise it constantly. Build it early.

## Background work

Celery + Redis. Task types are in `task_type_enum`. Rules:

- Write the `background_tasks` row when you **enqueue**, not when the worker starts.
- Every task takes an idempotency key and is safe to run twice.
- `acks_late=True`, `max_retries=3`, exponential backoff.
- A failed resume parse marks that one candidate `PARSE_ERROR` and **the batch continues**
  (US-16). Never let one bad PDF abort a 200-candidate run.
- `soft_time_limit` on every task so nothing hangs forever.

## The AI pipeline

```
trigger (recruiter clicks Process, job must be CLOSED)
  -> fan out one RESUME_PARSE task per candidate
       extract text (pypdf / python-docx; OCR fallback for scanned PDFs)
       failure -> status=PARSE_ERROR, parse_error=reason, continue
  -> BATCH_RANKING when parses settle
       clean + structure text (LLM, structured output)
       embed resume -> vector store
       cosine similarity vs jd_embedding
       LLM pass for matched/missing skills + feedback + evidence snippets
       write ai_analysis_results, assign rank_position, candidate -> RANKED
```

Keep scoring deterministic and separate from the LLM narrative. The score comes from
cosine similarity (reproducible, defensible in your viva); the LLM only *explains* it.
If you let the LLM produce the score you cannot defend the ranking, and re-runs will
disagree with each other.

## Frontend structure

```
src/
  components/ui/     Button, Input, Select, FileInput, DataTable, Modal,
                     StatusBadge, MatchScore, Card, EmptyState, Toast
  components/app/    AppShell, Sidebar, PageHeader
  features/          auth/ templates/ jobs/ candidates/ scheduling/ email/ admin/
  pages/             route components
  lib/               api client, query hooks, formatters
  styles/tokens.css  design tokens — single source of truth
```

Two shells: the recruiter app (sidebar 260px, header 72px) and the public apply page
(centered, no sidebar, no auth). They share `components/ui` and nothing else.

## Environments and seeding (future)

There is no staging/prod deployment yet — everything above describes local dev. Two
scripts exist for local-only test data: `app/scripts/seed.py` (one fake recruiter, for a
session cookie) and `app/scripts/seed_demo.py` (a minimal demo world: one template, a
single live job, and every resume dropped in `backend/seed_resumes/` applied to it as a
freshly submitted candidate — see that folder's README).
Both refuse to run unless `APP_ENV=local` — dev-only tooling, never safe to point at a
real deployment.

When a staging/prod environment exists:

- Seeding must target a database that is provably not prod (a separate `DATABASE_URL`,
  ideally a distinct host/instance, not just a different db name on the same server).
- A real recruiter's data already isn't at risk from sign-out — `upsert_recruiter`
  (`app/services/auth_service.py`) keys on `google_user_id`, and `/auth/logout`
  (`app/api/routes/auth.py`) only clears the session cookie, never a DB row. Keep it that
  way: no future "cleanup on logout" logic.
- If synthetic demo data is ever wanted in staging (e.g. a sales demo account), it should
  be a real recruiter row created through the normal OAuth flow, seeded by job/candidate
  ID under that recruiter — never a wipe-and-rebuild script sharing tenancy with real
  accounts.

Separately, local pytest runs against a dedicated `autohire_test` database
(`mise run db:test-create`, wired into `mise run test`) — never the dev database. A
session-scoped guard in `backend/tests/conftest.py` refuses to run pytest at all if
`DATABASE_URL` isn't a `*_test` database, because the suite's teardown deletes every row
in every table.
