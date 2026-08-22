# ADR-005: Single app-wide scheduling timezone, stamped onto each row at write time

- **Status:** Accepted
- **Date:** 2026-08-23
- **Affects:** EP-05, US-24, US-26, `scheduling_preferences.timezone`

## Context

`scheduling_preferences.available_start_time`/`available_end_time` are `TIME`
columns — no date, no offset. Something has to say what wall clock they mean, or a
recruiter in Lahore and a UTC server silently disagree by five hours. The baseline
(`docs/schema.md`, the SDS ERD) never named a timezone at all; this was pure
ambiguity, not a documented gap.

Two shapes were considered:

1. **App-wide setting**, read live at request time. One config value, no schema
   change, no frontend field. But nothing records which zone a *saved* row was
   entered in — change the setting later (or deploy to a different default) and
   every existing row silently reinterprets. Interviews shift by hours with no
   error and no trace.
2. **Per-recruiter column**, accepted in the `PUT` body, validated against
   `zoneinfo.available_timezones()`. Correct for a multi-region product. Costs a
   migration, a validator, and a frontend input Saif hasn't scoped — and AutoHire
   has exactly one recruiter population (Lahore) for the life of this FYP.

## Decision

Single app-wide setting, `SCHEDULING_TIMEZONE` (`app/core/config.py`, default
`Asia/Karachi`), **but stamped onto `scheduling_preferences.timezone` at insert
time rather than read live**. `PUT` never updates it after creation.

This is the cheap option (1) with option (2)'s failure mode fixed: a saved row
keeps meaning what it meant when it was entered, even if `SCHEDULING_TIMEZONE`
changes later. The API still doesn't accept a `timezone` field — it isn't
per-recruiter configurable — but the data records the fact, not just displays a
setting.

## Consequences

- US-26 (slot generation) must read `ZoneInfo(row.timezone)` for any already-saved
  preference row, **never `settings.scheduling_timezone` directly** — the live
  setting is only correct for a row that doesn't exist yet (`GET`'s synthesized
  defaults).
- Changing `SCHEDULING_TIMEZONE` in `.env` only affects recruiters who save (or
  re-save) their preferences afterward. Existing rows are untouched — this is the
  point, not a bug to fix later.
- A future per-recruiter timezone becomes "expose the existing `timezone` column
  and accept it in `SchedulingPreferencesIn`" rather than a migration plus an
  unrecoverable backfill (there is no way to know, after the fact, what zone an
  untouched row's `TIME` values were meant in).
- `docs/drift.md` row 48 records this against the baseline's silence on the
  question.
