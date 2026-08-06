# Stories

One file per story. Each carries acceptance criteria (from RS §5.2) and test cases
(from SDS §9). A story file is the brief for a Claude Code session: `/story US-06`.

Status values: `Todo` | `In Progress` | `Done`. `/wrap` updates these.

## Phase 1 — Walking skeleton

Thinnest possible slice of the whole pipeline, end to end. Ugly UI, one recruiter,
minimal error handling. **When this runs start to finish, every integration risk in
the register is dead** and you always have something demoable.

| Story | Title | Owner | Status |
|---|---|---|---|
| US-01 | Google OAuth sign-up with scope capture | Moazzam | Todo |
| US-02 | Login, session, profile | Moazzam | Todo |
| US-03 | Permission recovery / reconnect | Moazzam | Todo |
| US-04 | Create application template | Moazzam | Todo |
| US-06 | Launch job — JD, TTL, Drive folder, apply link | Moazzam | Todo |
| US-11 | Candidate opens application link | Saif | Todo |
| US-12 | Candidate submits application + resume | Saif | Todo |
| US-13 | Recruiter views raw submissions | Saif | Todo |
| US-15 | Trigger AI processing | Saif | Todo |
| US-16 | Resume text extraction + parse errors | Saif | Todo |
| US-18 | Embeddings + semantic scoring | Saif | Todo |
| US-19 | Ranked shortlist | Saif | Todo |
| US-24 | Availability windows | Moazzam | Todo |
| US-26 | Auto-schedule interviews | Moazzam | Todo |
| US-27 | Interview invitation email | Saif | Todo |

Build US-03 in Phase 1 even though it feels like polish. Testing-mode tokens expire
weekly (ADR-002), so you will need it constantly from week two onward.

## Phase 2 — Depth
US-05, US-07, US-08, US-09, US-10, US-14, US-17, US-20, US-21, US-22, US-23, US-25,
US-28, US-29, US-30, US-31

## Phase 3 — Hardening
US-32, US-33, US-34, TS-03, TS-04, TS-05

## Cloud cutover (ADR-003)
Drive → Gmail → Calendar → Pinecone. One per sprint slice, each only after the
feature works locally.
