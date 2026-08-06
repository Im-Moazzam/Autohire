---
description: Close out a work session — changelog, story status, PR draft
---

Wrap up the work in this session. Do all of the following, in order.

1. **Verify.** Run the test suite. If anything fails, stop and report — do not
   record work as done when it isn't.

2. **Changelog.** Add an entry to `CHANGELOG.md` under `## [Unreleased]`, in the
   right subsection (Added / Changed / Fixed / Removed). One line, written for a
   human reader, ending with the story ID:

   `- Recruiters can now duplicate an existing template (US-05)`

   Describe the user-visible change, not the implementation. "Added a service class"
   is not a changelog entry.

3. **Story status.** In `docs/stories/US-XX.md`, set the status line to `Done`,
   or to `In Progress` with a short note on exactly what remains. Tick the
   acceptance criteria that now pass.

4. **Decisions.** If this session involved a non-obvious choice — a workaround, a
   library pick, a schema change, a deviation from the SDS — write
   `docs/decisions/ADR-NNN-short-name.md` using the existing ADRs as the format.
   Skip this if nothing notable happened. Do not manufacture an ADR.

5. **Commit.** Conventional commit with the story ID.

6. **PR body.** Print a PR description for me to paste:
   - What changed and why (2-3 sentences)
   - Acceptance criteria covered
   - Migrations included (yes/no — if yes, name them explicitly)
   - Anything the reviewer should look at closely
   - Anything deliberately left out

7. **Handoff.** Print 2-4 bullets: where this leaves the codebase, and the obvious
   next step. This is what the next session reads first.

Keep it factual. If something is half-finished, say so plainly.
