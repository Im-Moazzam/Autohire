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
with two implementations: a local one and a real one. `APP_ENV` picks which.

```python
class ResumeStore(Protocol):
    def save(self, job_id: UUID, filename: str, data: bytes) -> StoredFile: ...
    def url_for(self, file_ref: str) -> str: ...
    def fetch(self, file_ref: str) -> bytes: ...
```

| Concern | `APP_ENV=local` | `APP_ENV=cloud` |
|---|---|---|
| Resume storage | `./storage/resumes/` | Google Drive |
| Email | Mailhog SMTP (`http://localhost:8025`) | Gmail API |
| Calendar | in-memory free/busy fake | Google Calendar |
| Vector store | pgvector | Pinecone |
| Embeddings | `all-MiniLM-L6-v2` (384-dim, free) | `text-embedding-3-small` (1536-dim) |
| LLM feedback | canned deterministic text | OpenAI chat completions |

Why this earns its keep:
- Tests run with no network, no API keys, no quota burn, no flakiness.
- You develop the entire pipeline before Google verification is sorted.
- When Pinecone is down mid-demo, you flip one env var (your own risk TR-03).
- `LocalEmbedder` and `OpenAIEmbedder` have **different dimensions**. Read the
  dimension from config everywhere. Hardcoding 1536 will silently corrupt your index.

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
