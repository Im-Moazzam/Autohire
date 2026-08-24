# ADR-003: Local-first development; cloud services behind adapters

- **Status:** Accepted
- **Date:** 2026-08-06
- **Affects:** all external integrations, TR-01, TR-03

## Context

The system depends on external services (Drive, Gmail, Calendar; optionally OpenAI).
Developing directly against them means: blocked on OAuth setup before any feature work,
burnt API quota during iteration, non-reproducible tests, cost exposure from runaway
loops, and a demo that fails when any one vendor has a bad day.

## Decision

Every external dependency sits behind a `Protocol` with two implementations. See
`docs/architecture.md` for the full table.

Development and CI run everything local by default, zero external calls: local
filesystem for resumes, Mailhog for mail, an in-memory calendar fake, pgvector for
vectors, a local fastembed model for embeddings, and canned LLM responses.

Cloud services are integrated in this order, each in its own sprint slice, only after
the corresponding feature works locally: **Drive -> Gmail -> Calendar -> embedder
decision.** Drive first because realistic resume files matter for parser quality.

**Selection mechanism, revised by TS-07.** The original design used one binary switch,
`APP_ENV=local|cloud`, driving every adapter factory at once — but that makes the
staged cutover above impossible: there is no configuration where Drive is cloud and
Calendar is still local. TS-07 replaced it with four independent settings, each
defaulting to local behaviour:

```
RESUME_STORE=local|drive        # default local
MAILER=local|gmail              # default local
CALENDAR_STORE=local|google     # default local
EMBEDDER=fastembed|openai       # default fastembed (openai not implemented)
```

`APP_ENV` still exists, but governs deployment semantics only (the session cookie's
`Secure` flag) — it is never read by an adapter factory or by business logic. Pinecone
was dropped before this story (drift row 10); pgvector is the only vector store, so
there is no fifth "vector store" setting to add.

## Consequences

- The full pipeline is buildable and testable before OAuth verification is resolved
- The test suite is fast, offline, deterministic, and free
- Each Google service cuts over independently — a Drive-only demo, or Drive+Gmail
  with Calendar still local, both just work (TS-07)
- Set a hard spend limit on any OpenAI key regardless — a loop in a Celery retry
  can cost real money
- **If an OpenAI embedder is ever built, dimensions differ (local 384 vs OpenAI
  1536).** Dimension is config-driven everywhere. Re-embed the whole corpus when
  switching; never mix. Not built as of TS-07 (drift.md) — scoring stays on
  fastembed only; OpenAI, if used, is reserved for a separate LLM-feedback adapter
