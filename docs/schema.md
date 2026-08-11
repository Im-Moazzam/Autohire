# AutoHire Database Schema

PostgreSQL 16 + pgvector. 14 entities. Transcribed from `autohire_erd_final.puml`
(the submitted SDS Phase II ERD) as a starting point. **These are working notes, not
a contract** — the Alembic migrations are the schema (see `docs/README.md`). Update
this file when it gets badly wrong, but don't agonise over sync; `make docs-erd`
renders the real diagram from the live database, and this file gets deleted once
SQLAlchemy models exist.

Conventions: all PKs are `UUID DEFAULT gen_random_uuid()`. All timestamps are
`TIMESTAMPTZ`. Soft-deletable tables carry `deleted_at TIMESTAMPTZ NULL`.

---

## Enums

```
field_type_enum        : SHORT_TEXT | PARAGRAPH | MULTIPLE_CHOICE | DROPDOWN
                         | FILE_UPLOAD | DATE | NUMBER
job_status_enum        : DRAFT | LIVE | CLOSED | PROCESSED
submission_status_enum : SUBMITTED | PARSED | RANKED | INVITED | CONFIRMED
                         | DECLINED | REJECTED | RESCHEDULED | PARSE_ERROR
slot_status_enum       : PENDING | CONFIRMED | DECLINED | RESCHEDULED | CANCELLED
intent_enum            : CONFIRM | DECLINE | RESCHEDULE | AMBIGUOUS
email_type_enum        : APPLICATION_CONFIRMATION | INTERVIEW_INVITE
                         | INTERVIEW_RESCHEDULE | CANCELLATION | REJECTION | CUSTOM
delivery_status_enum   : SENT | FAILED | PENDING
task_type_enum         : RESUME_PARSE | BATCH_RANKING | EMAIL_DISPATCH
                         | CALENDAR_SYNC | JD_EMBEDDING
task_status_enum       : PENDING | RUNNING | SUCCESS | FAILED | RETRIED
admin_action_enum      : ACTIVATE_RECRUITER | SUSPEND_RECRUITER | VIEW_QUOTA_ALERT
                         | RETRY_TASK
api_name_enum          : GOOGLE_DRIVE | GOOGLE_GMAIL | GOOGLE_CALENDAR | OPENAI
recruiter_state_enum   : ACTIVE | SUSPENDED | REAUTH_REQUIRED
```

`PARSE_ERROR` and `recruiter_state_enum` are additions to the submitted ERD —
see ADR-002. Note them in the SDS revision history.

---

## Core tables

### recruiters
| Column | Type | Notes |
|---|---|---|
| recruiter_id | UUID | PK |
| google_user_id | VARCHAR(255) | UNIQUE, NOT NULL |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| full_name | VARCHAR(150) | NOT NULL |
| profile_picture_url | TEXT | NULL |
| google_access_token | TEXT | NOT NULL, **encrypted at rest** |
| google_refresh_token | TEXT | **NULL**, encrypted at rest when present |
| google_token_expires_at | TIMESTAMPTZ | NOT NULL |
| granted_scopes | JSONB | NOT NULL |
| account_state | recruiter_state_enum | NOT NULL, DEFAULT 'ACTIVE' |
| created_at | TIMESTAMPTZ | NOT NULL |
| last_login_at | TIMESTAMPTZ | NULL |

Tokens encrypted with a Fernet key from `TOKEN_ENCRYPTION_KEY`. Never log them.
`google_refresh_token` is nullable because Google only reissues a refresh token on
some re-consents — on update, a missing one means "keep the existing token," not
"the recruiter has none." `google_token_expires_at` is an addition to the submitted
ERD (US-01); see `docs/drift.md`.

### scheduling_preferences (1:1 -> recruiters)
| Column | Type | Notes |
|---|---|---|
| preference_id | UUID | PK |
| recruiter_id | UUID | FK, UNIQUE, NOT NULL |
| available_days | TEXT[] | NOT NULL |
| available_start_time | TIME | NOT NULL |
| available_end_time | TIME | NOT NULL |
| slot_duration_minutes | INTEGER | NOT NULL, DEFAULT 30 |
| last_synced_at | TIMESTAMPTZ | NULL |

CHECK: `available_start_time < available_end_time`.

### form_templates (N:1 -> recruiters)
| Column | Type | Notes |
|---|---|---|
| template_id | UUID | PK |
| recruiter_id | UUID | FK, NOT NULL |
| template_name | VARCHAR(150) | NOT NULL |
| created_at / updated_at | TIMESTAMPTZ | |
| deleted_at | TIMESTAMPTZ | NULL |

UNIQUE (recruiter_id, template_name) WHERE deleted_at IS NULL.

### template_fields (weak, N:1 -> form_templates)
| Column | Type | Notes |
|---|---|---|
| field_id | UUID | PK |
| template_id | UUID | FK, NOT NULL, ON DELETE CASCADE |
| field_label | VARCHAR(200) | NOT NULL |
| field_type | field_type_enum | NOT NULL |
| is_required | BOOLEAN | NOT NULL, DEFAULT false |
| field_order | INTEGER | NOT NULL |
| options | JSONB | NULL — choices for MULTIPLE_CHOICE / DROPDOWN |

`options` is an addition to the ERD; MULTIPLE_CHOICE/DROPDOWN are unusable without it.
UNIQUE (template_id, field_order).

### job_postings
| Column | Type | Notes |
|---|---|---|
| job_id | UUID | PK |
| recruiter_id | UUID | FK, NOT NULL |
| template_id | UUID | FK, NOT NULL |
| job_title | VARCHAR(200) | NOT NULL |
| job_description | TEXT | NOT NULL |
| jd_embedding_id | VARCHAR(255) | NULL — soft ref to vector store |
| google_form_id | VARCHAR(255) | **NULL** — retained, unused (ADR-001) |
| google_form_url | TEXT | **NULL** — retained, unused (ADR-001) |
| google_drive_folder_id | VARCHAR(255) | NULL until Drive adapter goes live |
| apply_slug | VARCHAR(64) | UNIQUE, NOT NULL — public URL segment |
| status | job_status_enum | NOT NULL, DEFAULT 'DRAFT' |
| is_accepting_responses | BOOLEAN | NOT NULL, DEFAULT true |
| expires_at | TIMESTAMPTZ | NOT NULL |
| created_at / updated_at | TIMESTAMPTZ | |
| deleted_at | TIMESTAMPTZ | NULL |

`apply_slug` is new — it is the public application URL (`/apply/{apply_slug}`) that
replaces `google_form_url`. Use a random 16-char token, not the UUID, so job IDs
are not enumerable by candidates.

INDEX on (recruiter_id, status), and (expires_at) WHERE status = 'LIVE'.

### candidates (N:1 -> job_postings)
| Column | Type | Notes |
|---|---|---|
| candidate_id | UUID | PK |
| job_id | UUID | FK, NOT NULL |
| full_name | VARCHAR(150) | NOT NULL |
| email | VARCHAR(255) | NOT NULL |
| phone_number | VARCHAR(30) | NULL |
| resume_drive_file_id | VARCHAR(255) | NULL until upload completes |
| resume_drive_url | TEXT | NULL |
| resume_storage_key | VARCHAR(500) | NULL — local path when APP_ENV=local |
| submission_status | submission_status_enum | NOT NULL, DEFAULT 'SUBMITTED' |
| submitted_at | TIMESTAMPTZ | NOT NULL |
| parse_error | TEXT | NULL |
| deleted_at | TIMESTAMPTZ | NULL |

A candidate is scoped to one job. Same person, two jobs = two rows.
UNIQUE (job_id, email) — prevents double submission to the same posting.

### candidate_form_responses (weak)
| Column | Type | Notes |
|---|---|---|
| response_id | UUID | PK |
| candidate_id | UUID | FK, NOT NULL, ON DELETE CASCADE |
| field_id | UUID | FK, NOT NULL |
| response_value | TEXT | NULL |

UNIQUE (candidate_id, field_id).

### ai_analysis_results (1:1 -> candidates)
| Column | Type | Notes |
|---|---|---|
| analysis_id | UUID | PK |
| candidate_id | UUID | FK, UNIQUE, NOT NULL |
| job_id | UUID | FK, NOT NULL — denormalized, intentional |
| semantic_score | FLOAT | NOT NULL |
| rank_position | INTEGER | NOT NULL |
| matched_skills | JSONB | NULL |
| missing_skills | JSONB | NULL |
| ai_feedback_summary | TEXT | NULL |
| resume_text_extracted | TEXT | NULL |
| evidence_snippets | JSONB | NULL — US-23 explainability |
| vector_id | VARCHAR(255) | NULL — soft ref, named vendor-neutrally |
| embedding | vector(N) | NULL — pgvector, local mode only |
| processed_at | TIMESTAMPTZ | NOT NULL |

Two changes from the ERD: `pinecone_vector_id` -> `vector_id` (we swap backends,
see ADR-003), and `evidence_snippets` added because US-23 has no home otherwise.
Embedding dimension is config-driven — 384 local, 1536 OpenAI. Never hardcode it.

### interview_slots
| Column | Type | Notes |
|---|---|---|
| slot_id | UUID | PK |
| candidate_id / job_id / recruiter_id | UUID | FK, NOT NULL |
| scheduled_at | TIMESTAMPTZ | NOT NULL |
| duration_minutes | INTEGER | NOT NULL |
| google_calendar_event_id | VARCHAR(255) | NULL |
| google_meet_link | TEXT | NULL |
| status | slot_status_enum | NOT NULL, DEFAULT 'PENDING' |
| candidate_reply_text | TEXT | NULL |
| intent_detected | intent_enum | NULL |
| reschedule_reason | TEXT | NULL |
| created_at / updated_at | TIMESTAMPTZ | |

Multiple rows per candidate model reschedule history. Only one may be live:
partial UNIQUE (candidate_id) WHERE status IN ('PENDING','CONFIRMED').
INDEX (recruiter_id, scheduled_at) for conflict checks.

### email_logs
| Column | Type | Notes |
|---|---|---|
| email_id | UUID | PK |
| recruiter_id / candidate_id | UUID | FK, NOT NULL |
| slot_id | UUID | FK, NULL |
| email_type | email_type_enum | NOT NULL |
| subject | VARCHAR(255) | NOT NULL |
| body_preview | TEXT | NULL |
| gmail_message_id / gmail_thread_id | VARCHAR(255) | NULL |
| idempotency_key | VARCHAR(255) | UNIQUE, NOT NULL |
| sent_at | TIMESTAMPTZ | NOT NULL |
| delivery_status | delivery_status_enum | NOT NULL |
| is_automated | BOOLEAN | NOT NULL |

`idempotency_key` is new and it directly kills defect #6 in your log (duplicate
confirmation emails). Build it as `{candidate_id}:{email_type}:{slot_id or 'none'}`
and let the UNIQUE constraint do the work — retries become harmless no-ops.

### background_tasks
| Column | Type | Notes |
|---|---|---|
| task_id | UUID | PK |
| recruiter_id | UUID | FK, NOT NULL |
| job_id / candidate_id | UUID | FK, NULL |
| celery_task_id | VARCHAR(255) | NULL |
| task_type | task_type_enum | NOT NULL |
| status | task_status_enum | NOT NULL, DEFAULT 'PENDING' |
| error_message | TEXT | NULL |
| started_at | TIMESTAMPTZ | NOT NULL |
| completed_at | TIMESTAMPTZ | NULL |
| retry_count | INTEGER | NOT NULL, DEFAULT 0 |

Every Celery task writes a row here **on enqueue**, not on start. Otherwise a worker
that dies before picking the job up leaves no trace, and US-34 has nothing to show.

---

## Admin tables

**admins** — `admin_id UUID PK`, `email VARCHAR(255) UNIQUE`, `full_name VARCHAR(150)`, `created_at`.

**admin_action_logs** — `admin_action_id UUID PK`, `admin_id UUID FK`,
`recruiter_id UUID FK NULL`, `action_type admin_action_enum`,
`entity_name VARCHAR(100)`, `entity_id UUID`, `description TEXT NULL`, `created_at`.
Append-only. Never UPDATE or DELETE a row here.

**api_usage_logs** — `log_id UUID PK`, `recruiter_id UUID FK NULL`,
`api_name api_name_enum`, `call_count INTEGER`, `tokens_used INTEGER NULL`, `recorded_at`.
Written by the adapter layer, never by routes — that way every call is counted exactly once.
