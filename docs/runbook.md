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
Cloud Run keeps every revision. `gcloud run services update-traffic
justnews-api-production --region us-east1 --to-revisions <REVISION>=100`.
If the bad deploy included a migration, roll the migration back *first* —
`alembic downgrade -1` — or the old code meets a schema it does not understand.

## How to roll back a model version
Not applicable until Stage 6. When it is: model versions are registered and
promoted from the admin console, and article embeddings are unaffected because
the news encoder is frozen (ADR 0004, ADR 0005).

## Who to wake up
(you)
