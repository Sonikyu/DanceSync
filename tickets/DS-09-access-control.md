# DS-09 — Shared-passphrase access control

**Track:** Ship (MVP) · **Size:** S · **Depends on:** [DS-07](DS-07-serve-web-dist.md) · **Blocks:** exposing [DS-30…32](DS-30-youtube-url-validation.md) on the internet

## Context

The audience is the owner and friends, so this needs one shared secret, not accounts. It has to land before the server is reachable from the internet, and before YouTube import is exposed at all.

## Scope

- A passphrase in server config. Unset means no auth, so local dev is unchanged.
- Middleware that rejects unauthenticated requests to `/api/*` and to the static app with 401.
- A session cookie set by a small sign-in endpoint, so the passphrase isn't sent on every media range request.
- A minimal sign-in screen in the web app, shown when the API answers 401.

## Out of scope

Accounts, per-user storage, password reset, rate limiting.

## Acceptance criteria

- With a passphrase set, no endpoint serves media before sign-in
- With none set, behaviour is exactly as it is today
- Signing in once lasts the session, including for range requests from `<video>`
