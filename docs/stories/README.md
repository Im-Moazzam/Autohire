# Stories

One file per story. Each carries acceptance criteria (from RS §5.2) and test cases
(from SDS §9). A story file is the brief for a Claude Code session: `/story US-06`.

Status values: `Todo` | `In Progress` | `Done`. `/wrap` updates these.

## Scope declaration (2026-08-10)

**Phase 1 is the deliverable.** Phases 2 and 3 are documented as future work and will
not be implemented — single available developer, hard end-of-September deadline. See
`docs/drift.md` rows 10–11.

**Role split changed.** The original per-story Owner column assumed two full-stack
developers each taking whole vertical slices. Actual split: Moazzam builds **all
backend**, Saif builds **all frontend** against the generated TypeScript client.
Owner columns below now read backend-owner / frontend-owner.

Because this makes the backend a hard bottleneck, the working pattern is
**stub-first**: land route signatures and Pydantic response models for every Phase 1
endpoint early (returning fixture data), run `make api-client`, and let frontend work
proceed in parallel against real types while backend logic is filled in behind them.
This is `docs/workflow.md`'s contract-first parallelism, now mandatory rather than
optional.

## Phase 1 — Walking skeleton

Thinnest possible slice of the whole pipeline, end to end. Ugly UI, one recruiter,
minimal error handling. **When this runs start to finish, every integration risk in
the register is dead** and you always have something demoable.

| Story | Title | Backend | Frontend | Status |
|---|---|---|---|---|
| US-01 | Google OAuth sign-up with scope capture | Moazzam | Saif | Done |
| US-02 | Login, session, profile | Moazzam | Saif | Done |
| US-03 | Permission recovery / reconnect | Moazzam | Saif | Done |
| US-04 | Create application template | Moazzam | Saif | Done |
| US-06 | Launch job — JD, TTL, Drive folder, apply link | Moazzam | Saif | Done |
| US-11 | Candidate opens application link | Moazzam | Saif | Done |
| US-12 | Candidate submits application + resume | Moazzam | Saif | Done |
| US-13 | Recruiter views raw submissions | Moazzam | Saif | Done |
| US-15 | Trigger AI processing | Moazzam | Saif | Done |
| US-16 | Resume text extraction + parse errors | Moazzam | Saif | Done |
| US-18 | Embeddings + semantic scoring | Moazzam | Saif | Done |
| US-19 | Ranked shortlist | Moazzam | Saif | Done |
| US-24 | Availability windows | Moazzam | Saif | Done |
| US-26 | Auto-schedule interviews | Moazzam | Saif | Done (backend). Frontend not started |
| US-27 | Interview invitation email | Moazzam | Saif | Done (backend). Frontend not started |

Build US-03 in Phase 1 even though it feels like polish. Testing-mode tokens expire
weekly (ADR-002), so you will need it constantly from week two onward.

## Out of scope — documented as future work

**Phase 2:** US-05, US-07, US-08, US-09, US-10, US-14, US-17, US-20, US-21, US-22,
US-23, US-25, US-28, US-29, US-30, US-31

**Phase 3:** US-32, US-33, US-34, TS-03, TS-04, TS-05

## Cloud cutover (ADR-003)
Drive → Gmail → Calendar. **Pinecone dropped** — pgvector only, see `docs/drift.md`
row 10. One per sprint slice, each only after the feature works locally.
