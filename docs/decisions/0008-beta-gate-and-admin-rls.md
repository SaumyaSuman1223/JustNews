# 0008 — A separate beta gate from sign-in, and an RLS bypass for admin

- **Date:** 2026-09-02
- **Status:** accepted

## Context

Stage 4 ends with an invite-only private beta: "invited users read a real
site" is the literal exit criterion. Two things fell out of taking that
seriously rather than treating it as a launch-week checkbox.

First, *signed in* and *allowed to use the product* turned out not to be the
same fact. Supabase account creation is self-serve and needs no invite - any
reader can sign up. If having a Supabase session were treated as sufficient,
"invite-only" would only ever be a website copy claim, not something the API
enforced.

Second, ADR 0007's RLS design (a session-local `app.user_id` GUC, checked
against `user_id = ...` on every user-owned table) has no path for an
administrator to see anyone's rows but their own. That is correct for a
reader-facing endpoint. It is exactly wrong for the admin console this stage
also builds: source health is fine without RLS (nothing user-owned in it),
but analytics (impressions, interaction events) and user administration
(`user_profiles`) are RLS-protected tables an admin must be able to read
across every row, and `user_profiles.role` must be writable by an admin
acting on someone else's row.

## Options

**Beta gate**

1. **Gate at sign-up**, by refusing to create a Supabase account without a
   valid code. Requires either a Postgres trigger on `auth.users` (which
   this system does not own or migrate) or the Supabase Admin API with the
   service-role key (not configured in any environment this project has
   access to). Both add a hard dependency on Supabase-specific machinery for
   a rule the application already needs to enforce for other reasons.
2. **Gate at first use**, application-side: any verified reader may hold a
   Supabase session, but every beta-only route checks whether that reader's
   `user_profiles` row has redeemed an invite, independent of whether an
   account exists at all.

**Admin RLS access**

1. **A second, privileged database role** the admin console connects as,
   bypassing RLS by Postgres role membership rather than policy logic.
   Requires two connection pools, two sets of credentials, and a decision
   about which requests get which - real infrastructure for a beta-scale
   admin surface.
2. **A `SECURITY DEFINER` function**, `is_current_user_admin()`, referenced
   as an `OR` clause in the existing owner-only policies. One role, one
   connection pool; the widening lives in the policy definition, which is
   exactly where ADR 0007 already put the owner check.

## Decision

Gate at first use (option 2), and widen policies with a `SECURITY DEFINER`
admin-check function (option 2). Concretely:

- `user_profiles.invite_redeemed_at` is `NULL` until a reader redeems a code
  through `/v1/invites/redeem`. `core.db.get_beta_session` - not
  `get_user_session` - is what `/v1/feed`, `/v1/saves`, `/v1/follows` and
  `/v1/history` depend on, and it 403s a signed-in reader who has not
  redeemed. `/v1/me` deliberately stays on the unrestricted dependency: it is
  how a reader discovers they need a code and how they redeem one, so gating
  it too would be a lock with no door.
- An admin (`user_profiles.role = 'admin'`) always passes the beta check,
  invited or not - operating the product requires being able to see it.
- `is_current_user_admin()` runs as the table owner (`SECURITY DEFINER`,
  `SET search_path` pinned against hijacking), so its own lookup against
  `user_profiles` does not recurse through the very policy it is evaluating.
  Every RLS policy touched by Stage 4 - `user_profiles`, `user_saves`,
  `user_follows`, `impressions`, `interaction_events` - now reads
  `USING (owner_check OR is_current_user_admin())`; only `user_profiles`
  also widens `WITH CHECK`, since promoting another reader's role is the one
  write an admin legitimately makes on someone else's row.
- `invite_codes` and `admin_audit_log` get RLS from birth, admin-only in both
  directions - there is no reader-facing reason either table is ever queried
  outside `/v1/admin/*`, so the database enforces that rather than only
  routing convention.

## Consequences

**Easy:** one connection pool, one role, identical behaviour in local dev, CI
and Supabase - the same property ADR 0007 already established, extended
rather than reworked. A repository bug that forgets a beta-access check on a
new route still 403s instead of leaking a personalised feed to an
un-invited reader.

**Hard:** `is_current_user_admin()` is invoked on every RLS check against
these five tables, including from ordinary reader requests where it always
evaluates false - one extra indexed lookup per request. Not measured against
the free-tier Postgres budget yet; revisit if it shows up in query latency
once there is real traffic to look at.

**Revisit if:** a future admin surface needs to act *as* a specific user
(impersonation for support) rather than merely *see* their data - the current
design only ever widens read (and the one `user_profiles` write) access, and
was not built to answer "act on behalf of."
