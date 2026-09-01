# 0002 — Cold start by exploration, not just a topic picker

- **Date:** 2026-09-01
- **Status:** accepted — implemented in Stage 7

## Context
A new user has no interaction history. FINDING's cold-user problem is the
entire motivation for group-level personalisation: in MIND most users have
fewer than five training samples, so a per-user model is untrainable.

Asking users to tick topic boxes is cheap but weak evidence — people describe
themselves aspirationally ("world news, science") and read something else
("football, gadgets"). Stated preference ≠ revealed preference.

## Options
1. **Explicit topic picker only.** Cheap, one screen, users feel in control.
   Weak, biased signal. No dwell/skip data.
2. **Exploration deck only.** Show a stratified sample of popular articles
   across all categories; learn from clicks, dwell, and skips. Better signal,
   but costs the user 60–90 seconds before they see any value, and some will
   abandon.
3. **Both, in that order.** Picker seeds the initial distribution; a capped
   exploration deck (~15–20 cards) refines it; an ongoing epsilon-share of
   the live feed keeps exploring forever.

## Decision

Option 3, both in that order.

The picker alone is too weak a signal to bootstrap a user vector: stated
preference is aspirational and carries no dwell, skip, or position data, so
there is nothing for the user encoder to run over. The deck alone costs the user
60–90 seconds before they see any value, which is where new users leave.

Together they complement each other. The picker is one fast screen that seeds a
prior and makes the deck's stratified sample immediately relevant, so the deck
feels like browsing rather than like a form. The deck then produces the thing the
picker cannot: real engagement events on real articles, which the user encoder
turns into a vector and which assign the user to a FINDING group centroid. And
because the ongoing ε-share keeps a slice of every feed page exploratory, cold
start stops being a one-time event and becomes a permanent property of the
system — which is also the only defence against the feedback loop closing.

This lands in **Stage 7** of `docs/ROADMAP.md`, after the FINDING model exists
in Stage 6 — the handoff from deck to group assignment needs a trained user
tower to be worth anything. Until then, beta users get the Stage 5 heuristic:
language and edition selection, an IPTC top-two-level topic picker, then
popularity within picked topics.

The deck's arms are the **17 IPTC top-level concepts** (ADR 0006), and the deck
is filtered to the reader's chosen languages (ADR 0005) — so a Spanish-reading
user's exploration is genuinely exploratory rather than 60% unreadable.

## Consequences (design constraints this creates)
- **Stratify, don't sample uniformly.** Popularity is power-law distributed;
  uniform sampling over the corpus shows only sport and politics. Sample per
  category, then by popularity within category.
- **Log the propensity.** For every card shown, store the probability the
  policy had of showing it, plus its position in the deck. Without this you
  can never do unbiased offline evaluation later (IPS / doubly-robust
  estimators need it), and you will regret it in Stage 6.
- **Position bias is real.** Card 1 gets clicked more regardless of content.
  Log position; randomise order within the deck.
- **Skips are data.** A card scrolled past fast is a weak negative; a long
  dwell without a click is a weak positive; explicit "not interested" is a
  strong negative. Define the weights, and write them down here.
- **Feeds the group assignment.** After the deck, run the user encoder over
  the clicked articles to get a user vector and assign the nearest FINDING
  group — this is exactly how the paper handles evaluation-only users, done
  as a product feature.
- **Never stop exploring.** Reserve an epsilon share (start ~10%) of every
  feed page for exploration, or the feedback loop closes: the model only ever
  learns about what it already showed, and the filter bubble the survey warns
  about becomes structural.
- **Abandonment risk.** The deck must be skippable at any point, and must
  degrade to popularity-by-picked-topics if skipped.
