# 0007 — Application-verified JWTs, and RLS keyed off a session GUC

- **Date:** 2026-09-01
- **Status:** accepted

## Context

CLAUDE.md commits to two things that pull in different directions: "the API
verifies JWTs against Supabase JWKS" and "RLS on every user-owned table as
defence in depth." Supabase's own documentation assumes a different shape —
the browser holds the Supabase client library, talks to PostgREST directly
with the user's JWT, and `auth.uid()` (`current_setting('request.jwt.claims',
true)::json->>'sub'`, cast to a UUID) is what RLS policies compare against.
That function only means something when PostgREST is the thing evaluating the
JWT on every request.

This system's browser never talks to Postgres. It talks to FastAPI, which
verifies the JWT itself and always connects to Postgres as itself — one
application role, not a per-user one. `auth.uid()` would be permanently NULL
here; policies written against it would silently deny everything, or
(worse, if written carelessly) silently allow everything.

## Options

1. **Skip RLS, rely entirely on the service layer.** Least engineering, and
   correctness rests entirely on every repository query remembering its
   `WHERE user_id = ...`. One missed filter in one function is a
   cross-account data leak with no second layer to catch it — which is
   exactly the failure mode "defence in depth" exists to cover.
2. **Depend on `auth.uid()` anyway**, by having the API forward the user's
   JWT to Postgres somehow (e.g. `SET request.jwt.claims`). Reproduces
   Supabase's own convention, but ties every environment — local dev, CI, a
   future non-Supabase Postgres — to a Supabase-specific mechanism, for a
   value the API has already verified and decoded a moment earlier.
3. **A plain session-local Postgres setting the API writes itself,
   `app.user_id`**, set once per authenticated request's transaction via
   `set_config('app.user_id', :user_id, true)`. Policies compare against
   `NULLIF(current_setting('app.user_id', true), '')::uuid`. Works
   identically against Supabase, local pgserver, and CI's Postgres service
   container — it is just a Postgres session variable, nothing
   Supabase-specific about it.

## Decision

Option 3, with two things that make it actually protective rather than
decorative:

- **`FORCE ROW LEVEL SECURITY`, not just `ENABLE`.** The API's role owns
  these tables (it ran the migrations), and Postgres exempts an owning role
  from RLS by default. `ENABLE` alone would make this defence in depth a
  no-op for the one role that ever queries these tables.
- **`justnews_api.core.db.get_user_session`** is the only sanctioned way an
  authenticated route touches the database. It verifies the JWT, sets
  `app.user_id` before anything else runs on that session, lazily creates
  the reader's `user_profiles` row (a JWT is valid the moment Supabase
  issues it — before this system has ever seen that user), and commits or
  rolls back the same way `justnews_core.db.session_scope` already does. A
  route that used a raw session instead would simply see no rows on any
  RLS-protected table, which fails loud and immediately rather than leaking
  quietly.

JWT verification itself (`justnews_api/services/auth.py`) fetches Supabase's
JWKS over HTTPS, caches it with a TTL, and refreshes early on an unrecognised
`kid` so real key rotation doesn't wait out the cache. RS256 and ES256 only —
Supabase's current asymmetric-key signing, not the legacy HS256 shared-secret
mode, which cannot be verified from a public JWKS at all.

## Consequences

**Easy:** local dev, CI and Supabase all enforce the same RLS policies with
no environment-specific auth wiring. Tests sign real, verifiable tokens
against a self-signed key (`justnews_testing.auth.FakeJWKSProvider`) with no
network access and no live Supabase project. A repository bug that forgets a
user filter fails as an empty result set instead of another user's data.

**Hard:** if a future surface needs the browser talking to Postgres directly
(Supabase Realtime, a client-side query) it cannot reuse these policies as
written — that would need genuine `auth.uid()` policies alongside these, not
instead of them. `app.user_id` also does nothing on its own to stop a
compromised application role from setting an arbitrary user id — the
boundary that matters is still "only `require_user`'s verified JWT decides
what value gets set," not the GUC itself.

**Revisit if:** Stage 8's launch requires direct browser-to-Supabase reads
for latency reasons, or the admin console (Stage 4) needs a service-role
path that must bypass these policies by design rather than by accident.
