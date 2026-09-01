# 0006 — IPTC Media Topics as the topic taxonomy

- **Date:** 2026-09-01
- **Status:** accepted

## Context

Every article needs topics. Topics drive navigation, the onboarding picker, the
exploration deck's stratification, topic-affinity scoring in the heuristic
ranker, and every analytics slice. Getting the taxonomy wrong is expensive to
undo, because it is baked into the interaction log the moment logging starts.

The choice became easier once the audience became global.

## Options

**1. A custom set of ~16 topics.** Simple, tuned to our sources, no mapping
layer. But every source's own categories still need mapping to it, the labels
need translating into every launch language by hand, the hierarchy has to be
invented and defended, and none of it is interoperable with anything.

**2. IPTC Media Topics.** 17 top-level concepts, 1,200+ terms across 5
hierarchical levels, official translations in 13 languages, and the taxonomy
most publishers and wire services already tag against. Chosen.

**3. Source categories as-is, no canonical taxonomy.** Zero work, and it makes
the whole product incoherent: "Tech" from one source and "Technology" from
another become different topics, and cross-source comparison dies.

## Decision

IPTC Media Topics, with three implementation rules that matter more than the
choice itself.

**Store the concept ID, not the label.** The canonical key is the IPTC concept
ID (`medtop:20000170`). Labels are a presentation-layer lookup. This is what makes
the multilingual story work: one topic, thirteen official display names, and our
own translations where IPTC has none.

**Store the full hierarchical path, browse at any depth.** An article tagged with
a level-4 concept is reachable from its level-1 ancestor. Navigation exposes the
17 top-level concepts; the onboarding picker exposes levels 1–2 (a picker with
1,200 options is not a picker); analytics roll up to whatever level answers the
question.

**Map, then classify.** Many sources already emit categories that map cleanly to
IPTC. Use the mapping where it exists; classify only what is left over. This is
much cheaper and more accurate than classifying everything from scratch, and the
mapping table is editable from the admin console in Stage 4.

## Consequences

- **A mapping layer is real work.** Source categories → IPTC concept IDs, with an
  admin-editable table and a review queue for unmapped values. Built in Stage 1,
  maintained forever.
- **IPTC covers 13 languages: Arabic, English (GB and US), Chinese, Danish,
  French, German, Norwegian (Bokmål and Nynorsk), Portuguese (and Brazilian),
  Spanish, Swedish.** There is **no Hindi or other Indian-language** coverage.
  Because we key on concept IDs, supplying our own display translations for
  uncovered languages is additive and does not fork the taxonomy.
- The 17 top-level concepts give the exploration deck (Stage 7) a natural,
  defensible set of arms for Thompson sampling — a taxonomy someone else
  justified, rather than 16 topics we invented and would have to defend.
- Interoperability we get for free: structured data, syndication, and any future
  publisher partnership already speak this vocabulary.
- Classification into a 1,200-term hierarchy is harder than into 16 buckets.
  Mitigated by classifying to level 2 by default and only going deeper where the
  source's own metadata supports it. Precision at level 1 matters far more than
  recall at level 4.
