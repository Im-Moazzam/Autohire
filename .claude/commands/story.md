---
description: Implement a story from docs/stories
---

Implement the story I name (e.g. `/story US-06`).

**Before writing any code:**

1. Read `docs/stories/US-XX.md` in full.
2. Read `docs/schema.md` and `docs/api-contract.md`. For frontend work also read
   `docs/design.md`.
3. Skim `docs/decisions/` — do not re-open a settled question.
4. Check `CHANGELOG.md` to see what already exists. Do not rebuild it.

**Then plan.** Present, before implementing:
- Files you will create or change
- Schema changes, if any, and the migration
- New API endpoints with their request/response shapes
- Which tests will prove the acceptance criteria
- Anything in the story that is ambiguous or looks wrong

Wait for my approval on the plan.

**Then build**, in this order: migration -> models -> service -> route -> tests ->
frontend. Tests come from the story's test cases, not invented after the fact.

**Constraints** (from CLAUDE.md, repeated because they get violated most):
- No vendor SDK imports outside `app/adapters/`
- Every query scoped by `recruiter_id`
- Every list endpoint paginated
- Frontend uses only `components/ui` primitives and design tokens

Finish with `/wrap`.
