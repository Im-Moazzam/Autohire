# ADR-002: Stay in OAuth Testing mode; treat re-auth as a first-class flow

- **Status:** Accepted
- **Date:** 2026-08-06
- **Affects:** EP-01, US-01, US-02, US-03, `recruiters.account_state`

## Context

AutoHire requests Drive, Gmail, and Calendar scopes. Gmail read scopes are *restricted*
under Google's classification. Publishing an External app with restricted scopes requires
full OAuth verification plus a CASA Tier 2 security assessment by an approved third-party
assessor — a process measured in weeks and requiring payment. That is not compatible with
an academic project timeline or budget.

Remaining in Testing status has two documented consequences: a hard cap of 100 test users,
and **refresh tokens that expire after 7 days**. Test users also see an "unverified app"
warning they must click through, but they can authorize successfully.

## Decision

Remain in Testing status for the life of the project. Do not attempt verification.

Because tokens will expire roughly weekly, re-authorization is not an edge case — it is
normal operation. Therefore:

- `recruiters.account_state` carries `REAUTH_REQUIRED`
- The Google session wrapper catches `invalid_grant`, flips the state, and raises
  `ReauthRequired`; the API returns 409 `REAUTH_REQUIRED`
- The frontend renders a persistent "Reconnect Google" banner in that state
- `POST /auth/google/reconnect` re-runs consent and replaces the stored tokens

This is US-03 (permission recovery), which was already in the backlog. The constraint
turns it from a rarely-exercised edge case into a demonstrable feature.

## Consequences

- Build and test the reconnect flow in Phase 1, not late. You will use it constantly.
- **Demo checklist item: re-authorize the demo account the morning of every advisor
  demo or presentation.** An expired token mid-demo is an avoidable disaster.
- Add all developer and demo Google accounts as test users up front (limit 100).
- Request the minimum scope set. Adding a restricted scope later restarts verification
  if you ever do pursue it.
- If the university has Google Workspace and can host the Cloud project internally,
  an **Internal** user type removes both the 7-day expiry and the 100-user cap. Worth
  one conversation with the advisor or IT; it is the only clean escape from this constraint.
