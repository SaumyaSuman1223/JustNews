# JustNews

A personalised news reader whose ranking layer uses clustered, interpolated
personalisation derived from **FINDING** (Yu et al., CIKM '23).

> **Honesty statement (keep this accurate as you build).**
> Training implements FINDING's fine-grained interpolation and dynamic
> clustering over *simulated* clients replayed from production interaction
> logs. Serving is centralised. On-device computation is Phase 12 and is not
> done yet. Do not describe this as a federated production system until it is.

## Status
- [ ] Phase 0 — foundations
- [ ] Phase 1 — own the paper & repo
- [ ] Phase 2 — model → service
- [ ] Phase 3 — backend core

## Quickstart
TODO(session 0.3): a reader with a fresh clone must get the stack running
from this section alone, in under 5 minutes. If they can't, this section is
the bug.

## Layout
See `docs/architecture.md`.

## Docs
- `docs/architecture.md` — the system and why it's shaped this way
- `docs/runbook.md` — how to operate it when it breaks
- `docs/decisions/` — architecture decision records
- `CLAUDE.md` — how AI assistance is used in this repo

## Attribution
Based on ideas from *Federated News Recommendation with Fine-grained
Interpolation and Dynamic Clustering* (CIKM '23) — https://github.com/yusanshi/FINDING
Check that repository's licence before publishing derived code.
