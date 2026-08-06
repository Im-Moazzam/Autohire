# Spec drift log

Deviations from the submitted Phase I (RS) and Phase II (SDS) documents.

Not a list of mistakes — it is evidence of iterative design, which is the thing Agile
FYPs are supposed to demonstrate. Add a row whenever implementation departs from the
baseline. At submission this becomes the SDS revision history and §8 design evolution.

| # | Baseline said | Implementation does | Why | Story / ADR | Date |
|---|---|---|---|---|---|
| 1 | Job launch creates a Google Form with resume upload | App renders `/apply/{slug}`; resume posts to our API then to Drive | Forms API cannot create file-upload questions, and they force candidate Google sign-in | ADR-001 / US-06 | 2026-08-06 |
| 2 | `is_active BOOLEAN` on Recruiter | `account_state` enum incl. `REAUTH_REQUIRED` | Testing-mode tokens expire weekly; re-auth needs a real state | ADR-002 / US-03 | 2026-08-06 |
| 3 | `pinecone_vector_id` | `vector_id` + local `embedding` column | Vector backend is swappable; local-first development | ADR-003 | 2026-08-06 |
| 4 | Four email endpoints by type | One `POST /emails/send` with a `type` field | Same handler, same logging; four routes was duplication | — | 2026-08-06 |
| 5 | TemplateField has no options storage | Added `options JSONB` | MULTIPLE_CHOICE and DROPDOWN are unimplementable without it | — | 2026-08-06 |
| 6 | AIAnalysisResult has no evidence field | Added `evidence_snippets JSONB` | US-23 explainability had nowhere to store data | — | 2026-08-06 |
