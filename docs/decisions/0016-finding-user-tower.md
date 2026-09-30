# 0016 — FINDING's user tower: trained offline, served as stored vectors, live only after it wins offline

- **Date:** 2026-09-30
- **Status:** accepted. Built end to end; not in the live split.

## Context

ROADMAP Stage 6 is FINDING (Yu et al., CIKM '23): a news recommender trained with fine-grained interpolation between a global model and group models, and dynamic re-clustering of users. The recommendation audit (`docs/RECOMMENDATION_AUDIT_2026-09-30.md`) found four things standing in the way:
- **The site's constraints.**
  - FINDING's news encoder is NRMS over English GloVe, and JustNews is multilingual (ADR 0005).
  - There can be no model inference in a request (ADR 0004).
- **No data.** There are no reading logs to train on, which ADR 0015's logging now starts to fix.
- **The paper's own data is hard to get.**
  - MIND's download links are dead.
  - MIND's Hugging Face mirror needs a signed-in account that has accepted the licence.
  - Adressa, the paper's other dataset, is openly downloadable.

## Options

1. **Import the reference code into the app.**
   - `apps/` never imports `ml/`.
   - The code is unlicensed, depends on GloVe, and runs a forward pass per request.
2. **Retrain NRMS with a multilingual word model.** This means re-embedding the corpus for every model, and the news tower would still run at ingest per model version.
3. **Keep the frozen multilingual vectors as the news tower. Train FINDING's user tower and training procedure over them offline, export to ONNX, and serve precomputed vectors.**

## Decision

Option 3, in these parts:
- **Part A, reproduction** (`ml/finding/reproduce.sh`).
  - It runs the original code at its pinned commit.
  - The only changes are the porting fixes in `ml/finding/porting.patch`, recorded in `ml/finding/PORTING-NOTES.md`.
  - The code is fetched, not vendored.
- **Part B, the tower** (`ml/finding/jnfinding`).
  - The model is NRMS's user encoder (masked) plus one linear news adapter, over the frozen MiniLM vectors.
  - FINDING's procedure is re-implemented from the paper:
    - simulated clients sampled per group, and size-weighted gradient averaging into the global model;
    - interpolation p(r, i) = (1 − α^−r)·((i+1)/n)^β for parameters and Adam moments;
    - KMeans re-clustering, with a Hungarian relabel and a transfer-matrix remix of the group models.
  - The metrics are our own, tested against hand calculations.
- **Serving without inference.**
  - A click score is u·(Wc + b). For one reader, u·b is constant, so ranking by (Wᵀu)·c is identical.
  - `justnews-ingest user-vectors` runs the exported ONNX files offline for every reader with at least 5 reads, and stores Wᵀu in `user_vectors` (migration 0021).
  - The `finding_v1` policy is ranker v2 with that vector as the reader's profile, compared to candidates by cosine in Postgres.
  - Article vectors never change.
- **Jobs across readers.**
  - `user-vectors` and `export-behaviours` declare themselves with `app.job`.
  - Read-only RLS policies let exactly those jobs read the tables they need; only `user-vectors` may write vectors.
- **The gate.** `finding_v1` is registered but not in `EXPERIMENT_SPLIT`. It joins the split only after `jnfinding.replay` shows it ranking JustNews's own logged pages better than the policy that served them.

## Consequences

**What this makes possible:**
- FINDING's contribution can be measured on public data now, and on JustNews logs as they accumulate, without touching the request path.
- A model upgrade is new ONNX files and a job run; no article is re-embedded.

**What stands in the way of going live:**
- **Licences.** MIND and Adressa are research-licensed, so weights trained on them are not deployed to the public site.
- **Groups.** FINDING's groups are meaningful only with hundreds of active readers. Until then, one group is the honest configuration.

**What's still manual:**
- **Serving.** There is no GitHub Actions step yet. It needs a model trained on data it may serve, stored somewhere the workflow can fetch.
- **Signed-out readers.** They are never ranked by FINDING, because it needs a history tied to an account. They keep ranker v2's device-history profile.
- **Honesty.** Training replays simulated clients, and serving is centralised. Nothing here may be described as federated.
