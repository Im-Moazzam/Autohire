# AutoHire Mobile

A read-mostly companion app for recruiters: check jobs, candidates, interviews, and
emails from your phone. Talks to the same FastAPI backend as `frontend/` — no backend
changes were made for this app.

## Scope (deliberate — see below before adding more)

**Screens:** Dashboard, Jobs (list + detail), Candidates (per job, list + detail),
Scheduling (view-only), Emails (view-only).

**Actions:** reject / undo-rejection on a candidate, copy a job's application link.
Everything else is read-only.

**Why Scheduling has no confirm/cancel action:** the backend's
`PATCH /interviews/{slot_id}` is a deliberate stub that always returns
`501 Not Implemented` (`backend/app/api/routes/interviews.py`, commented "Phase 2, not
implemented"). The web Scheduling screen doesn't expose this either. Mobile follows the
same constraint — do not add a confirm/cancel button here without first building the
real endpoint on the backend.

## Design

No mobile Figma file exists yet, so this reuses `docs/design.md`'s color palette and
type scale (see `tailwind.config.js` — keep it in sync with
`frontend/src/styles/tokens.css` by hand until there's a shared tokens package).
Layout is native-first, not a port of the web app shell: bottom tab bar instead of a
sidebar, stacked drill-down navigation for Jobs → Job → Candidates → Candidate, and a
smaller type scale (`page` is 28px here vs. 32px on web) since phone screens have far
less width than the web app's 1440px frame.

## Setup

1. `cd mobile && npm install`
2. Copy `.env.example` to `.env` and set `EXPO_PUBLIC_API_HOST` to your machine's LAN
   IP (run `ipconfig` on Windows, look for the Wi-Fi adapter's IPv4 address) — a
   physical phone can't resolve `localhost` to your dev machine. The backend's Docker
   container already binds `0.0.0.0:8000`, so it's reachable from any device on the
   same network once this is set correctly.
3. Make sure the backend is running (`docker compose up -d` from the repo root).
4. `npx expo start` — scan the QR code with the **Expo Go** app (Android/iOS) to run it
   on your phone, or press `w` to open the web-preview target in a browser.

## Auth

Reuses the exact same Google OAuth flow as the web app (`/auth/google/login` →
Google consent → `/auth/google/callback`, which sets an httponly session cookie) —
no separate mobile auth endpoint. `app/login.tsx` runs that flow in an in-app WebView.

The session cookie is httponly, so no JS can ever read its value — not even inside the
WebView's own page. The first version of this used a native cookie-manager package to
read it anyway, which crashed instantly on a real device: Expo Go's app binary only
ships the Expo SDK's own native modules, and a third-party native module like that
isn't in it (this only would have worked in a custom dev client, not Expo Go).

The actual fix needs no native code at all (`lib/webviewBridge.tsx`): a second,
invisible, persistent WebView stays loaded on the API's origin. Because it shares the
same app-level cookie jar as the visible login WebView, a `fetch()` run *inside* that
hidden WebView's own page carries the httponly cookie automatically — exactly like a
real browser tab does for the web app. `lib/http.ts` relays every API call's
request/response across that JS bridge on native, and just uses a normal
`credentials: "include"` fetch directly on web (no bridge needed there — a browser tab
already has its own cookie jar).

## Debugging note (react-native-web preview)

`react-native-web` crashes if NativeWind's `darkMode` is left at its default `"media"` —
throws the instant anything touches `Appearance` (`tailwind.config.js` sets
`darkMode: "class"` to avoid it; the app has no dark theme yet anyway). Also worth
knowing: `babel-preset-expo` and `react-native-worklets` (Reanimated 4's peer dep)
sometimes don't get hoisted to the top-level `node_modules` after certain install
orders, which Metro can't resolve — both are pinned as explicit dependencies here for
that reason.

## Regenerating API types

`mobile/lib/api.d.ts` is generated from the same OpenAPI spec as the web app's client.
Run `make api-client` from the repo root after any backend route change — it now
regenerates both `frontend/src/lib/api.d.ts` and `mobile/lib/api.d.ts` together.
