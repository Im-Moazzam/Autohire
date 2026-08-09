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
| 7 | `job_postings` has no public URL field, form access assumed via Google Form | Added `apply_slug VARCHAR(64) UNIQUE` — random 16-char token, not the job UUID | Public apply link needed a non-enumerable identifier once forms were self-hosted (ADR-001) | ADR-001 / US-06 | 2026-08-06 |
| 8 | `email_logs` has no uniqueness constraint on sends | Added `idempotency_key VARCHAR(255) UNIQUE` | Structurally prevents duplicate sends (defect #6) instead of relying on application logic | — | 2026-08-06 |
| 9 | `submission_status_enum` had no failure state | Added `PARSE_ERROR` | A batch must continue past one bad resume (US-16); needed a status to land on | — | 2026-08-06 |
| 10 | Vector store has a Pinecone cloud implementation (ADR-003 adapter table) | pgvector only; `PineconeStore` not implemented | Dataset size (single-recruiter FYP demo, hundreds of vectors) does not justify an external dependency. The `VectorStore` Protocol stays, so Pinecone remains a drop-in addition — the abstraction is demonstrated without the integration cost. Removed under Aug–Sep schedule constraints. | ADR-003 | 2026-08-10 |
| 11 | Phase 2 (16 stories) and Phase 3 (6 stories) planned for implementation | Phase 1's 15 stories only | Single available developer, hard end-of-September deadline. Phase 1 is the complete end-to-end pipeline and constitutes the deliverable; Phases 2–3 documented as future work. | — | 2026-08-10 |
| 12 | `recruiters` has no token-expiry column | Added `google_token_expires_at TIMESTAMPTZ NOT NULL` | AC requires "token expiry timestamp stored alongside"; nothing in the baseline schema captured it | US-01 | 2026-08-10 |
| 13 | `google_refresh_token` NOT NULL | Made nullable | Google omits the refresh token on some re-consents; a missing value must mean "keep the stored one," which requires the column to tolerate a transient null, and it's simplest to make the column itself nullable rather than fake a sentinel | US-01 | 2026-08-10 |
| 14 | Scopes requested: `drive.file`, `gmail.send`, `calendar` only (US-01, ADR-002) | Also requests `openid`, `email`, `profile` | The three functional scopes carry no identity info; Google sign-in is impossible without an identity scope. These three are unrestricted and don't trigger the CASA/verification burden ADR-002 protects against, so this doesn't reopen that decision | US-01 / ADR-002 | 2026-08-10 |
| 15 | `recruiters.account_state` enum: `ACTIVE`, `REAUTH_REQUIRED`, `DISABLED` (US-01 draft) | Enum is `ACTIVE`, `SUSPENDED`, `REAUTH_REQUIRED` | Matches `docs/schema.md` and `admin_action_enum` (`ACTIVATE_RECRUITER`/`SUSPEND_RECRUITER`), which already assumed `SUSPENDED`; `DISABLED` had no corresponding admin action and was a story-drafting slip | US-01 | 2026-08-10 |
