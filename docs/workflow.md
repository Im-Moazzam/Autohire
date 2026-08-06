# How we actually build

Two questions this answers: which document gets used when, and what a feature cycle
looks like end to end.

## Which doc does what

Only **`CLAUDE.md`** is read automatically at the start of every Claude Code session.
Everything else is pulled in deliberately — that's why CLAUDE.md is short and tells
Claude what to open next.

| File | Who reads it | When |
|---|---|---|
| `CLAUDE.md` | Claude Code | automatic, every session |
| `docs/stories/US-XX.md` | Claude Code | the story being built — the unit of work |
| `docs/architecture.md` | Claude Code | any backend work |
| `docs/design.md` + `checklists/ux.md` | Claude Code | any frontend work |
| `docs/decisions/` | Claude Code | scanned so settled questions stay settled |
| `docs/schema.md`, `api-contract.md` | Claude Code | orientation only, until real code replaces them |
| `docs/checklists/pr.md` | you | pasted into every PR |
| `docs/checklists/testing.md` | you | when deciding what to test |
| `docs/drift.md` | you + the report | whenever you depart from the RS/SDS |
| `CHANGELOG.md` | written by `/wrap` | never read by Claude, read by your advisor |
| `docs/README.md`, `workflow.md` | you | onboarding, once |

If a file isn't being read by anyone, delete it. That is a real rule, not a slogan.

## Order of work

**TS-00 first.** Bootstrap the repo so `make up` works. No features.

**Then a stubbed auth boundary, not real OAuth.** Session 2 should add the `Recruiter`
model, a seeded demo recruiter, and `GET /api/v1/auth/me` returning it from a fake
session. Two reasons this matters:

- Your first coding session should prove the stack wires together, not fight Google
  Cloud Console. If OAuth is session one you can burn two days and have nothing to show.
- It unblocks parallel work immediately. Saif can build candidate intake against a
  known recruiter while Moazzam builds real OAuth behind the same interface.

Replace the stub in US-01/US-02. Nothing downstream changes, because everything
downstream only ever knew `get_current_recruiter()`.

**Then vertical slices,** in the Phase 1 order from `docs/stories/README.md`.

## The cycle for one feature

Never "all the backend, then all the frontend". One story = one thin vertical slice
through every layer. You should be able to demo something after each one.

```
1.  Pick the story. Make sure docs/stories/US-XX.md has real acceptance
    criteria — sharpen it before the session, not during.
2.  git checkout -b feat/US-XX-slug
3.  /clear          ← stale context is the main cause of drift
4.  /story US-XX
5.  Read the plan. Push back if it's wrong. This is the cheapest
    place to correct course — much cheaper than reviewing 600 lines.
6.  Approve. It builds in order:
        migration → model → service (+unit tests) → route (+integration
        test) → make api-client → UI → component test
7.  Check it yourself in the browser. All five UX states, not just
    the happy path.
8.  /review        ← catches tenant isolation, adapter leaks, raw hex
9.  Fix what it finds.
10. /wrap          ← changelog, story status, PR body
11. Open the PR with docs/checklists/pr.md. Other person reviews.
12. Merge. Update the Notion Work item: Status + PR link.
```

Steps 5 and 8 are the two that keep quality up. Skipping the plan review is how you
end up with 600 lines going the wrong direction; skipping `/review` is how tenant
isolation bugs reach `dev`.

## Session hygiene

- **One story per session.** Two stories in one context and it starts conflating them.
- **`/clear` between stories.** Always.
- **If a session goes sideways, stop and restart it.** Arguing with a session that has
  built on a wrong assumption costs more than starting clean with a better brief.
  The story file is the brief — improve it and re-run.
- **If Claude asks to change the schema mid-story**, stop. Decide separately, write it
  in `drift.md` if it departs from the baseline, then continue.
- **Never let it disable a CI gate to go green.** Fix the code or change the gate on purpose.

## Splitting work

Once TS-00 and the stubbed auth boundary are in, you can work genuinely in parallel:

- **Moazzam** — auth, templates, jobs, dashboard, scheduling, admin
- **Saif** — apply page, candidate intake, parsing, AI pipeline, ranking UI, email

You'll collide in `components/ui` and `docs/schema` only. Agree migrations verbally
before either of you writes one — two Alembic heads is an annoying half hour.
