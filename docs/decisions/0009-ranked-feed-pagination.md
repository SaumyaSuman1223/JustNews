# 0009 — A frozen-window cursor for the ranked feed

- **Date:** 2026-09-03
- **Status:** accepted

## Context

CLAUDE.md is unambiguous: "cursor pagination only, never offset, on any
feed." The reason is specific to a *chronologically* ordered feed - `(x,y) <
(a,b)` keyset pagination works because the sort key is stable: an article's
`(published_at, id)` never changes, so "everything after the last row I saw"
is a well-defined, monotonically-consistent request no matter how many new
rows land in between.

Stage 5's heuristic ranker breaks that assumption on purpose. Its score
depends on `now` (recency decay) and on click counts that change every time
anyone clicks anything. There is no stable sort key to keyset against - two
requests scoring the same candidate pool five minutes apart can legitimately
disagree about the order, and there is no row-level cursor that expresses
"whatever came after position 7 last time," because *whatever came after
position 7* is itself a property of the whole ranked list, not of the row at
position 7.

## Options

1. **Re-run the full ranking query on every page** with a live, unbounded
   candidate window (`published_at <= now()`, evaluated fresh each request).
   This reintroduces exactly the bug offset pagination has: new articles
   published between page 1 and page 2 shift every candidate's relative
   rank, so a reader can see an article twice or miss one - not because of a
   raw `OFFSET`, but for the identical underlying reason.
2. **Materialise and persist the ranked list** for a reader's session (a
   cache row, keyed by user and a generated timestamp) and page through the
   stored order. Correct, but real new infrastructure - a cache with its own
   invalidation story - for a problem that does not need it yet at beta
   scale.
3. **Freeze the candidate window's upper bound in the cursor itself.** The
   first request captures `now`; every subsequent page for that same feed
   load re-queries `published_at <= that same now`, which can never include
   an article published after it. The candidate *set* is therefore
   reproducible on every page - re-running scoring and MMR over an identical
   input deterministically produces an identical order - so an integer
   offset into that reproduced list is safe. Nothing external is stored;
   the cursor (`window_upper_bound`, `offset`) carries everything needed to
   reproduce the exact same ranked list again.

## Decision

Option 3. `repositories.content.list_articles_window` is the one query this
depends on: bounded by `published_at <= upper_bound`, nothing else. As long
as the underlying rows in that window do not change between two requests -
true within one feed session in practice; an article being taken down
mid-scroll is the one real exception, and simply removes itself from a
future page rather than corrupting one already served -
`services.ranking.score_candidates` and `.diversify` are pure functions of
their input, so the same window reproduces the same order every time.
`services.cursor.encode_rank_cursor` / `decode_rank_cursor` are a distinct
cursor *version* from the chronological feed's keyset cursor
(`encode_cursor`), so the two can never be confused for one another even
though both currently arrive at the same `/v1/feed?cursor=` parameter.

This is still not literally the same thing CLAUDE.md's "cursor pagination
only" rule was written to forbid. That rule's failure mode is a table that
grows *underneath* a fixed position, silently skipping or repeating rows.
Freezing the window's upper bound is precisely what makes that failure mode
structurally impossible here: nothing published after the bound can ever
enter this query, at any page, ever.

## Consequences

**Easy:** no new infrastructure, no cache to invalidate. A reader's feed
session is internally consistent - scrolling through it never skips or
repeats an article - which was the actual property "cursor pagination only"
was protecting, achieved by a different mechanism than a literal keyset.

**Hard:** an article published *after* a reader's feed session started
cannot appear until they reload the page (a fresh, unbounded-window
request), even if it would have outranked everything already shown. For a
15-minute ingestion cadence this is a minor staleness, not an outage - the
same trade-off a paginated feed on any high-traffic site makes.

**Revisit if:** Stage 6's learned ranker needs to score against a
continuously moving candidate pool (a genuinely live "for you" feed) rather
than a bounded recent window - at that point option 2's persisted ranking
likely stops being premature and starts being necessary.
