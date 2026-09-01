# 0005 — A global audience, and what it does to the model

- **Date:** 2026-09-01
- **Status:** accepted

## Context

The audience is global and multilingual, not English-only. That decision looks
like a product choice and is mostly a modelling one.

FINDING's news encoder is NRMS over **GloVe 840B 300d English word vectors**. It
tokenises with an English tokeniser and looks up English word embeddings. Fed a
Hindi or Arabic headline it produces noise, not a bad vector — noise. Every
downstream mechanism in the paper (user vectors, clustering, interpolation)
inherits that noise. A global corpus does not degrade this architecture
gracefully; it breaks it.

## Options

**1. One model per language.** Faithful to the paper, and each language gets a
properly trained encoder. But it multiplies the training cost by the language
count, splits an already-thin interaction dataset N ways, gives every new
language a cold start from zero, and makes cross-lingual story clustering
impossible. For a project whose entire difficulty is data sparsity, splitting
the data N ways is the wrong direction.

**2. English only, other languages later.** Honest and simple, and it keeps the
paper reproducible. But "later" for i18n means a retrofit, and retrofitting RTL
and locale routing into a finished Next.js app costs several times what building
with logical properties costs from the start. It also contradicts the stated
product goal.

**3. Replace the news tower with a frozen multilingual sentence encoder; keep
FINDING's user tower and training loop.** Chosen.

**4. Fine-tune a multilingual transformer as the news tower.** Best quality, and
out of reach: it needs GPU hours per retrain, and re-embedding the whole corpus
on every model upgrade, on a 500 MB database with no compute budget.

## Decision

Option 3.

The key observation is *where FINDING's contribution actually lives*. The paper's
novelty is the fine-grained interpolation coefficient
`λ(t,i) = (1 − α^−t)·((i+1)/N)^β` and the dynamic re-clustering of user models
with a transition-matrix remix. Both are properties of the **training procedure
and the user tower**. The news tower is ordinary NRMS, inherited from prior work,
and is replaceable without touching the contribution.

So the news tower becomes a **frozen multilingual sentence encoder producing
384-dimensional vectors** over 50+ languages, run once per article at ingest.
FINDING's trainable user tower and training loop sit on top, unchanged.

**This is validated, not assumed.** Stage 6 Part A reproduces the paper on
MIND-small with the *original* GloVe news tower first. That is the proof the port
is correct. Only then does Part B swap the tower and retrain for production.
Both sets of numbers are recorded, including the gap between them.

## Consequences

**Good, and load-bearing.**

- One shared vector space across all languages. Cross-lingual recommendation
  works for free: a user vector built from English reading surfaces a relevant
  Spanish article.
- **Cross-lingual story clustering.** The same event reported in English, Spanish
  and Arabic clusters into one story. Monolingual aggregators cannot do this, and
  it is one of the more distinctive things the product will do.
- **Article vectors never need recomputing when the ranker is retrained**, because
  the news encoder is frozen. Against a 500 MB database with no compute budget,
  removing the batch re-embed job from every model upgrade is a large operational
  win — and it makes ADR 0004's precompute-everything design strictly cheaper.
- 384 dims as `halfvec` is 768 bytes per article, half of a 1536-dim embedding.

**Costs, accepted.**

- We no longer reproduce FINDING's exact production numbers, because the news
  encoder differs. Mitigated by Part A above, and by never claiming otherwise.
- A frozen encoder cannot learn news-domain-specific representations the way a
  trained NRMS tower can. Some quality is left on the table. Measured in Stage 6,
  not guessed at.
- Encoder quality varies by language. Low-resource languages will rank worse, and
  the analytics must be sliced by language or that will stay invisible.
- Changing the sentence encoder later means re-embedding the entire corpus. The
  encoder identity is therefore pinned in the model registry alongside the ranker
  version.

**Product consequences beyond the model.**

- **i18n is structural, in Stage 3, not a Stage 11 retrofit:** locale-segmented
  routing, RTL via logical CSS properties throughout, locale-aware dates and
  numbers, per-script font stacks, `hreflang`.
- **Language is a first-class filter**, stored per article and per user. Readers
  see only the languages they chose.
- **Compliance targets the strictest applicable regime** — GDPR, UK GDPR, CCPA
  and India's DPDP — because a global audience means all of them apply.
- **The API's US free-tier region becomes the sharpest constraint in the
  system.** A reader in Delhi is ~230 ms away before the API does anything. The
  answer is to edge-render everything cacheable and reduce the personalised path
  to one round trip per session, then measure by region in Stage 8. See ADR 0003.
