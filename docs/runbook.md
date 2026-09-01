# Runbook

Fill a section in the moment something breaks, while you still remember.

## How to tell it's healthy

| Check | Healthy | Command |
|---|---|---|
| API process | `{"status":"ok"}` | `curl $API/health` |
| API + database | `{"status":"ready","database":"ok"}` | `curl $API/health/ready` |
| Corpus is fresh | newest article under ~30 min old | `make stats` |
| Ingestion is running | a row in the last 15 min with `feeds_failed` low | `select * from ingest_runs order by started_at desc limit 5;` |
| Storage headroom | `free_tier_fraction` below 0.7 | `make prune` |
| GNews budget | `gnews_calls_remaining_today` above 0 | `make stats` |

`/health` and `/health/ready` are deliberately different. Liveness probes must
hit `/health`, which never touches the database — otherwise a database
outage makes the orchestrator kill healthy containers and a degradation
becomes an outage.

## Common failures

### An `ingest_runs` row has `finished_at` NULL
The run was killed rather than finishing — the GitHub Actions job timeout, the
next cron lapping it, or the runner being reclaimed. Per-entry
transactions mean whatever it stored is intact and the next run picks up the
rest, so this is not data loss. It is a signal that the pass is too slow.
- Check `error` on that row: `run stopped at its deadline` means the run's own
  budget stopped it cleanly, which is working as designed. A NULL `finished_at`
  with no error means something external killed it, which is not.
- The usual cause is enrichment. `ingest_max_enrich_per_run` caps it and
  `ingest_run_deadline_seconds` bounds the whole pass; both must stay well
  under the `timeout-minutes` in `.github/workflows/ingest.yml`.

### The site loads but headlines are hours old
Ingestion has stopped. Check the most recent `ingest_runs` row.
- No recent row at all → the GitHub Actions cron is not firing. Check the
  workflow's run history; a repository with no activity for 60 days has its
  scheduled workflows disabled by GitHub.
- Recent row with a high `feeds_failed` → a publisher is blocking us, or DNS is
  failing. `select url, last_error, consecutive_failures from feeds where
  consecutive_failures > 0 order by consecutive_failures desc;`
- One bad feed is not an incident. Feeds back off exponentially to a six-hour
  ceiling and recover on their own.

### `/health/ready` returns 503 with `"database":"unreachable"`
Supabase has paused, or the credentials rotated.
- **Paused** is the common one on the free tier: seven days without database
  traffic pauses the project. Resume it in the Supabase dashboard, then check
  why the 15-minute ingestion cron — which exists partly to prevent this —
  stopped running.
- `"database":"timeout"` instead means it is reachable but slow. Look for a
  long-running query or an index that is not being used.

### The same story appears several times on the feed
Dedup is too loose for that case. Establish which layer *should* have caught it:
- Same story, different URLs, identical headline → layer 2. Check
  `dedup_simhash_max_distance`.
- Reworded headlines → layer 3. Check `dedup_embedding_min_cosine`, and check
  which embedder is live: `HashingEmbedder` is lexical and will not match a
  rewrite or a translation. Production must run `EMBEDDER=sentence-transformers`.

### Unrelated stories merged into one cluster
Worse than duplicates. Raise `dedup_embedding_min_cosine`, then look at the
offending pair — `select title, language from articles where story_cluster_id = N`.
Clusters are recomputed from the articles table, so correcting membership fixes
the counts.

### Database is over 70% of the free tier
`make prune` reports the fraction and applies the retention window. If it is
still high, shorten `article_retention_days`, then check for interaction rows
that should have been rolled up.

## How to restore a database backup
Supabase takes daily backups on the free tier and keeps them for seven days.
Restore from the dashboard into a **new** project, verify, then repoint
`DATABASE_URL`. Do not restore in place before you have looked at the data.

## How to roll back a deploy
Render keeps every deploy. In the service's Render dashboard, open the
Deploys tab and "Rollback" to the previous successful deploy (or redeploy an
older commit directly). Vercel works the same way from its Deployments tab —
"Promote to Production" on a prior deployment.
If the bad deploy included a migration, roll the migration back *first* —
`alembic downgrade -1` — or the old code meets a schema it does not understand.

## How to roll back a model version
Not applicable until Stage 6. When it is: model versions are registered and
promoted from the admin console, and article embeddings are unaffected because
the news encoder is frozen (ADR 0004, ADR 0005).

## Operating the private beta

### Making the first account an admin
No signup flow grants `admin` - it has to be set directly, once, before an
admin console session exists to do it any other way:
```sql
update user_profiles set role = 'admin' where id = '<supabase-auth-uuid>';
```
The row must already exist, which means that reader has signed in and hit any
authenticated endpoint at least once (profile creation is lazy - ADR 0007).
Every promotion after this first one goes through `/admin/users` and is
audit-logged; this one, by construction, cannot be.

### Inviting a beta reader
`/admin/invites` creates a code (`POST /v1/admin/invites`, `max_uses`,
optional `expires_at`). Send the code to the reader outside this system -
there is no invite-sending email flow yet, only redemption
(`POST /v1/invites/redeem`, or `/invite` in the web app). A reader who has
signed up but not redeemed sees `has_beta_access: false` on `/v1/me` and a
403 from `/v1/feed`, `/v1/saves`, `/v1/follows` and `/v1/history` - `/v1/me`
itself always stays reachable, since it is how they find out and fix it.

### A reader reports a problem you cannot reproduce
There is no session-replay yet (deferred - see Stage 4 status in README).
What you have: `/admin/audit-log` for anything an admin did, and direct SQL
against `interaction_events`/`impressions` filtered by `user_id` for what the
reader themselves did (position, surface, propensity, timestamp on every
row). Ask for their reader id from `/v1/me` rather than an email - this
system does not store one.

### Taking an article down
`/admin/articles`, or `POST /v1/admin/articles/{id}/takedown` with a reason.
This sets `removed_at`/`removed_reason` - the row survives (moderation
history, the audit log entry references it), but
`repositories.content._base_query()` is the one choke point every read path
shares, so it stops appearing anywhere on the site immediately. Restore from
`/admin/articles` or `POST /v1/admin/articles/{id}/restore`.

### A reader asks to be deleted
Point them at Settings → "Delete my account" (or `DELETE /v1/me` directly).
This removes their `user_profiles` row, cascading to saves and follows, and
sets `user_id` to `NULL` on their impressions and interaction events -
anonymised, not deleted, since those rows also represent aggregate product
measurement once identity is stripped. It does **not** delete their Supabase
auth account - no service-role key is wired up for that yet, so tell them
that step is separate and currently manual.

## Who to wake up
(you)
