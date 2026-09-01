# 0004 — No model inference inside a user request

- **Date:** 2026-09-01
- **Status:** accepted

## Context

The obvious design is a `/rank` endpoint: take a user and a candidate set, run
the model, return scores. It is how the research code thinks, and it is how
most tutorials build it.

On our infrastructure it is the wrong shape. ONNX Runtime on a cold instance
of a free-tier host adds container start plus model load to the first
request. Every subsequent request spends real CPU on forward passes, drawn
from a fixed monthly compute budget. And a news feed is exactly the workload where
the model's inputs barely change between requests — the same articles are
scored for many users, and the same user is scored against overlapping
candidates all day.

## Options

**1. ONNX in the request path.** Faithful to the paper's framing, simple to
reason about, and it means a fresh user vector on every request. But it puts a
neural forward pass between the reader and their front page, on a platform that
bills CPU by the second and scales to zero.

**2. Precompute everything; serve from vectors.** NRMS is a two-tower model, so
the news encoder and the user encoder never need to run at the same time as each
other. Run both offline, store the outputs, and let the request path do the one
thing the towers were always going to do anyway — a dot product.

**3. A separate always-on inference service.** Best latency under sustained
load, and the right answer with a budget. There is no free tier that keeps a
PyTorch container warm.

## Decision

Option 2.

```
ingest        → news encoder → article vector      → pgvector (halfvec)
nightly + async → user encoder → user vector, group → users table
request       → ANN candidates → dot product → rerank → feed
```

Article vectors are computed once, at ingest, in the ingestion job. User vectors
are recomputed nightly for everyone and on demand for users whose behaviour has
moved materially — after the exploration deck, or after N new interactions.
Group centroids from FINDING's dynamic clustering are stored and versioned
alongside the model.

A feed request therefore costs: one indexed candidate query, one vector
similarity operation, a rerank in Python over ~200 candidates, and the
impression writes. No model, no ONNX, no cold start.

## Consequences

**Good.**
- p95 under 200 ms is achievable on a free tier. With option 1 it is not.
- The free vCPU budget stops being the binding constraint on traffic.
- Models can be upgraded, promoted and rolled back without an API deploy.
- Degradation is graceful: missing or stale vectors fall back to the heuristic
  ranker, and the feed is still good.

**Costs, accepted.**
- A user's vector lags their most recent behaviour by up to one refresh cycle.
  For news consumption, where interests move over days rather than seconds, this
  is a small loss — and the exploration slice keeps fresh signal flowing in.
- Re-embedding the corpus after a model upgrade is a batch job that must be run
  and monitored, and the pgvector index has to be rebuilt with it.
- Vector storage is a real line item against the 500 MB budget, which is why
  embeddings are `halfvec` and the retention window is enforced.
- The paper's per-user personalisation becomes per-user-vector plus per-group
  interpolation, evaluated offline. That is what FINDING does anyway, but the
  distinction must stay clear in how the system is described.
