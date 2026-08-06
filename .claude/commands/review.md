---
description: Review a diff before opening a PR
---

Review the current changes as if you were the other developer on a two-person team
who has to maintain this code and defend it in a viva.

Check, in priority order:

1. **Tenant isolation** — can any query return another recruiter's rows? This is the
   one class of bug that is both a security failure and a graded requirement (NFR-06/07).
2. **Adapter boundary** — any vendor SDK imported outside `app/adapters/`?
3. **Migrations** — reversible? Any destructive change in the same step as the code
   that stopped using the column?
4. **Pagination** — any list endpoint without `page`/`size`?
5. **Secrets** — any key, token, or credential in code, logs, or error messages?
6. **Error handling** — do Google calls handle `invalid_grant` and rate limits? Does
   a single failure abort a batch that should continue?
7. **Tests** — do they actually assert the story's acceptance criteria, or just that
   the code ran?
8. **Design tokens** — any raw hex or arbitrary Tailwind values in the frontend?

Report as: **Blocking** / **Should fix** / **Nitpick**. Be specific with file and line.
If it's clean, say so — don't invent problems to look thorough.
