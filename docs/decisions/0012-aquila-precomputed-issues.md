# 0012 — The Aquila Tribune is a published issue, not a feed

- **Date:** 2026-09-04
- **Status:** accepted

## Context

Aquila is the product's signature surface: a digital newspaper published three
times a day (06:00 Morning, 14:00 Midday, 22:00 Evening), read page by page
rather than scrolled. It is the thing that makes JustNews a *publication*
rather than another ranked list.

That framing only holds if an issue is a **fixed artifact**. A newspaper you
can re-read, cite, and come back to tomorrow behaves nothing like a feed that
reshuffles under you. The question is whether to honour that literally in the
data model or to fake it at the presentation layer.

There is also a hard constraint: the API runs on Render's free tier and scales
to zero, the database is a 500 MB Supabase instance, and ADR 0004 forbids model
inference inside a request path. Whatever Aquila does, it cannot do it
per-reader per-request.

## Options

**1. Compute the issue on read.** No new tables. `GET /v1/issues/latest` runs
the composition query — pick a lead, fill each page from the corpus — every
time someone opens Aquila. Cheapest to build. Fails on everything else: the
issue mutates between page 1 and page 4 as ingestion writes new rows, two
readers on the same "issue" see different papers, an archive is impossible by
construction, and the most expensive query in the product runs on the hottest
path on a free tier that scales to zero.

**2. Compute on read, cache the result.** Mitigates the cost but not the
correctness. A cache key is not an identity: the issue still has no primary
key, cannot be linked to, cannot be archived, and the cache expiring mid-read
resurfaces exactly the mutation problem it was meant to hide.

**3. Compose and freeze at publish time.** Chosen. A scheduled job composes the
issue at each of the three publish times, writes the article selection into
real tables, and marks it published. Serving is then a primary-key read.

## Decision

An issue is **composed once, offline, at its publish time, and never changes
afterwards.**

Three tables: `issues` (edition slot, published_at, volume, number, locale),
`issue_pages` (page number, section, topic), `issue_slots` (position, article,
role — lead / secondary / brief / quote). The composer is a new command in
`apps/ingestion`, run by its own GitHub Actions schedule at the three publish
times — the same pattern as the 15-minute ingest cron, and for the same reason
(ADR 0010: there is no free-tier worker to run it on, and none is needed).

The word **"edition" is deliberately not reused.** `editions` already exists in
the schema and means a *regional* edition — a language/country pairing. Aquila's
morning/midday/evening is an `edition_slot` on an `issue`. Two different
concepts sharing a name in one schema is a bug waiting to be written.

Aquila logs impressions through the existing interaction pipeline under its own
`surface`, with a real propensity. A composed page is still a selection the
system made on the reader's behalf, and Stage 6 must be able to replay it.

## Consequences

- **Serving Aquila is trivially cheap** — a keyed read of frozen rows, fully
  cacheable, identical for every reader in a locale. On a free tier that is the
  difference between a feature that works and one that times out.
- **The archive is free.** Yesterday's Evening Edition still renders, because
  nothing about it was computed at read time. This is a real product surface
  later ("read the issue from the day X happened") at no additional cost.
- **A missed publish window is visible.** If the composer does not run, there is
  no issue — the failure is loud rather than silently serving a stale feed.
  Aquila needs an explicit "no issue yet" state, and the runbook needs a manual
  compose command.
- **Composition quality is now a batch problem**, which is the good version of
  this problem: it can be reviewed, re-run, and eventually hand-corrected from
  the admin console without touching serving code.
- Storage cost is bounded and small — an issue is a few hundred foreign keys,
  not copies of articles. Retention on issues can follow the existing article
  retention window.
- **Personalisation stops at Aquila's door**, by design. Every reader in a
  locale gets the same paper. That is the point of a publication, and it is why
  Home exists as the personal surface.
