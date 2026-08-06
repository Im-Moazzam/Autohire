# ADR-003: Local-first development; cloud services behind adapters

- **Status:** Accepted
- **Date:** 2026-08-06
- **Affects:** all external integrations, TR-01, TR-03

## Context

The system depends on five external services (Drive, Gmail, Calendar, OpenAI, Pinecone).
Developing directly against them means: blocked on OAuth setup before any feature work,
burnt API quota during iteration, non-reproducible tests, cost exposure from runaway
loops, and a demo that fails when any one vendor has a bad day.

## Decision

Every external dependency sits behind a `Protocol` with two implementations, selected by
`APP_ENV`. See `docs/architecture.md` for the full table.

Development and CI run `APP_ENV=local` with zero external calls: local filesystem for
resumes, Mailhog for mail, an in-memory calendar fake, pgvector for vectors, a local
sentence-transformers model for embeddings, and canned LLM responses.

Cloud services are integrated in this order, each in its own sprint slice, only after
the corresponding feature works locally: **Drive -> Gmail -> Calendar -> Pinecone.**
Drive first because realistic resume files matter for parser quality. Pinecone last
because it is the cleanest swap and the least likely to surprise us.

## Consequences

- The full pipeline is buildable and testable before OAuth verification is resolved
- The test suite is fast, offline, deterministic, and free
- Pinecone outage mid-demo is a one-env-var fallback to pgvector (mitigates TR-03)
- Set a hard spend limit on the OpenAI key regardless — a loop in a Celery retry
  can cost real money
- **Embedding dimensions differ between local (384) and OpenAI (1536).** Dimension is
  config-driven everywhere. Re-embed the whole corpus when switching; never mix.
- Keeping pgvector working after Pinecone lands gives the report a genuine
  "we benchmarked managed vs self-hosted vector search" section
