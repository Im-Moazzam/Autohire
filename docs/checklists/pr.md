# PR checklist

Paste into the PR description. Reviewer works top to bottom.

```
## What and why


## Story
US-XX — acceptance criteria covered:

## Checks
- [ ] Tests written, and they assert the story's criteria (not just that code ran)
- [ ] Migration reviewed and reversible (or: no schema change)
- [ ] Every new query scoped by recruiter_id
- [ ] Every new list endpoint paginated
- [ ] No vendor SDK imported outside app/adapters/
- [ ] No secrets, tokens, or keys in code, logs, or fixtures
- [ ] UI: five states present (docs/checklists/ux.md)
- [ ] UI: design tokens only — no raw hex, no arbitrary values
- [ ] CHANGELOG.md updated
- [ ] docs/drift.md updated if this departs from the RS/SDS baseline

## Reviewer should look closely at


## Deliberately not done
```
