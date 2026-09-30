# 0015 — Ranker v2: one ranker for every reader, and logs a model can learn from

- **Date:** 2026-09-30
- **Status:** accepted

## Context

The recommendation audit (`docs/RECOMMENDATION_AUDIT_2026-09-30.md`) found:
- **Ranking:**
  - The personal ranker (`heuristic_v1`) reached only invited readers on For You, and half of them sat in a chronological control.
  - It ranked the newest 200 articles, about four hours of English, whose publisher mix was each source's posting rate.
  - It learned nothing from reading. It ignored the article vectors every row already has, never demoted a card shown and ignored, and ranked Top for one page only.
- **Logs**, which are what FINDING (ROADMAP Stage 6) would train on:
  - Impressions counted cards nobody scrolled to.
  - Positions restarted on every page, while clicks numbered across pages.
  - The ranked head was logged at propensity 1.0, so offline evaluation of any other ranker has no support there.
  - Only one surface logged anything at all.

The readers chose, on 2026-09-30:
1. **Signed-out readers are personalised from on-device history**, and their reading is logged by browsing session under the existing analytics consent.
2. **The chronological control is a 10% holdout**, with new rankers compared offline over logged propensities.
3. **Order of work:** logging first, then v2, then FINDING.

## Options

1. **Tune v1.** A bigger pool and a heavier follow boost. This is cheap. But it leaves the pool set by posting rate, the logs unlearnable, and every non-invited reader unranked.
2. **Train a model now.** There is nothing to train it on: the local database has no clicks, and production logs only invited, consenting readers on one surface.
3. **One arithmetic ranker over stored vectors, with sampled, logged serving.**
   - It personalises from what the reader opened, saved and shared.
   - It works for every reader and every Discover view.
   - It records what a later model needs.
   - There is still no forward pass in the request path (ADR 0004).

## Decision

Option 3: `services/recommend.py` and `services/scoring.py`, served by `GET /v1/discover` for every reader and by `/v1/feed` as the 90% arm of the experiment.

**Candidates** come from four places:
- a time window (36 hours; 7 days for a topic) with at most 40 per source;
- the 150 articles nearest the reader's profile vector over 72 hours;
- new reports on followed stories;
- one article per story, whichever scores best.

**Score.** One log-linear function, with weights per surface:
- recency with a per-surface half-life;
- breadth and reach, as in v1;
- source trust;
- language rank;
- the cosine to the profile, which is the decayed, weighted mean of the vectors of opened, shared and saved articles, pushed away from "not interested";
- smoothed topic and source lifts;
- follows (topics, sources, stories);
- fatigue (shown and not opened in 72 hours);
- already opened;
- click-through lift across readers (clicks per view, not raw clicks).

**Order.**
- Greedy MMR on vector cosine and same-source.
- At most 5 cards per source in any 24, and never three in a row.
- For You gets an exploration slot every 12 positions. It draws uniformly from important stories outside what the reader reads.
- A logged page samples each step: a softmax at T=0.05 over the top 20 by MMR value, with 5% of uniform mixed in. Each placement logs its conditional probability; the product over a prefix is that prefix's probability.
- An unlogged page is the deterministic argmax, and can be cached.

**Pagination without state.**
- The cursor carries the moment the feed was ranked, the seed and, when signed out, the device history.
- Every reader signal is read as of that moment. Impressions are stamped with the app's clock after it.
- Page 2 is therefore the same ranking page 1 was cut from, recomputed. An article marked not interesting since then is dropped from the page without re-ranking.

**Logging** (migration 0020):
- **Views:** `impression_views` records which served cards were at least half on screen for a second, where they were drawn, and in what shape.
- **Positions:** feed-wide.
- **Clicks:** `POST /v1/clicks` for every reader. Signed out, a click counts only against an impression that browsing session was served.
- **Surfaces and locale:** `top` becomes a surface, and clicks carry the interface locale.

**Experiment:** `EXPERIMENT_SPLIT` gives `heuristic_v2` 90% and `chronological` 10%. `heuristic_v1` stays registered as the rollback.

## Consequences

**What this makes possible:**
- Every Discover view, for every reader, is ranked by one library with stated weights. A card's reason names only a term that was applied.
- With consent, the logs now hold what an impression-level learner needs:
  - served position, rendered position and slot;
  - seen or not, and opened or not;
  - the probability the policy had of placing each card.
  - A FINDING user tower (Stage 6) can train on these as replayed clients, and be compared offline against v2 before any reader sees it.

**What it costs:**
- **Per request:** about ten small queries, and numpy over at most 300 unit vectors. Candidate rows are fetched light: ids and the profile cosine computed in Postgres. Full rows are fetched only for served cards, and vectors are cached per process. Free-tier egress is the constraint this shape answers.
- **The feed ends:** after the 300 best stories of its window.

**What it doesn't do:**
- **Signed-out readers** are personalised only from ids their device sends. Nothing about them is stored without consent.
- **Weights** are hand-set, not learned. The 10% holdout and offline replay are how they get tested.

**Revisit when:**
- Consented logs reach a few hundred readers with histories: train the FINDING user tower on them, and compare offline.
- The pool's 300-story end is reached often: extend the window.
- Render's CPU shows the per-request arithmetic: precompute the shared, non-personal stage per minute.
