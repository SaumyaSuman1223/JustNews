# 0013 — Perspectives are grounded in who published, not inferred from text

- **Date:** 2026-09-04
- **Status:** accepted

## Context

"Perspectives" is the differentiator in
`docs/JustNews_Design_and_Product_Direction.md`: My Desk should not only answer
*what happened* but *how different groups are reading what happened* — an
industry view, a government view, an academic view, a public view.

This is the single most dangerous feature in the product. Every other surface
either shows a headline someone else wrote or ranks headlines by observable
behaviour. Perspectives is the first place JustNews would make an **assertion
of its own**: that a given piece of coverage represents a particular group's
interpretation. Get it wrong and the product is confidently mislabelling
journalism — which is worse than not shipping the feature.

Two constraints narrow the field before taste enters. ADR 0004 forbids model
inference in a request path, so whatever this is, it is computed offline. And
the free-tier budget rules out per-article LLM calls at ingestion volume.

## Options

**1. LLM labels each article's stance.** Send title and snippet to a model, ask
which stakeholder lens it represents. Most expressive, and unusable: it costs
real money per article at ingest volume, it is unverifiable (the label is the
model's opinion with no citation), it will confidently mislabel, and a reader
who disagrees has nothing to inspect. It also puts a paid dependency in the
ingestion path, which the free-tier constraint (ADR 0003) exists to prevent.

**2. Zero-shot classification against perspective prototypes** using the
frozen multilingual encoder already in the pipeline. Free, offline, fits the
existing architecture. Still fundamentally a guess presented as a fact:
cosine similarity to a prototype sentence is not evidence that an article
represents the government's view, and the reader still cannot check it.

**3. Ground the claim in source role.** A perspective group is defined by *who
published the article* — a fact the system already knows and the reader can
verify by clicking through. Chosen.

## Decision

**A perspective is a fact about the publisher, not a guess about the text.**

Sources gain an editorially-assigned `source_role`: `wire`, `industry`,
`government`, `academic`, `investor`, `consumer`, `public`. Nullable, seeded
for the existing catalogue, and editable from the admin console — the same
shape as the source-category mapping ADR 0006 already established, and for the
same reason: a small curated table beats a classifier on both accuracy and
explainability.

A story cluster's Perspectives view is then its articles **grouped by the role
of the source that published them**. "Industry press — 4 sources" is a
statement that can be checked in one click. Topic-level Perspectives aggregate
the same grouping across the topic's recent clusters.

**Labels must describe what the grouping actually is.** The UI says
"Industry press" and "Government sources", not "The Industry View" — the first
is true, the second claims to summarise what an entire sector thinks. A
publisher's category is evidence about perspective; it is not identical to it,
and the copy must not pretend otherwise.

Roles are unassigned by default. An unroled source appears in the story's
coverage like any other and simply does not contribute to a perspective group —
silence is correct, invention is not.

## Consequences

- **Every perspective on screen is traceable** to named sources the reader can
  open. This is the property that makes the feature defensible, and it is the
  one an inference-based approach cannot provide at any price.
- **Curation is ongoing work.** Roles must be assigned for new sources, which
  means a real admin surface and an unroled-source queue. This is the cost, and
  it is the same cost ADR 0006 already accepted for category mapping.
- **Coverage is uneven and will look it.** Many topics will have wire and
  industry coverage and nothing else. The UI must show three groups honestly
  rather than padding to a decorative four.
- **A wire service is not a perspective**, and `wire` exists to keep Reuters and
  AP out of the perspective groups rather than to create a "wire view".
- **The hard case stays hard.** A single outlet can publish both an industry
  puff piece and an investigative critique. Source role cannot distinguish them,
  and this decision does not claim to. A later intra-role framing layer
  (option 2, applied *within* a role rather than to assign one) is a reasonable
  extension precisely because it would be refining a grounded grouping rather
  than inventing one.
- Revisit if role assignment cannot keep up with the source catalogue, or once
  there is enough labelled data that a classifier could be evaluated against
  something real instead of against intuition.
