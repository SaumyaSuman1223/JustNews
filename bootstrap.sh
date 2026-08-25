#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# bootstrap.sh — scaffolds the JustNews monorepo.
#
# Usage (repo already created on GitHub and cloned locally):
#   cd JustNews                      # your clone
#   bash bootstrap.sh
#   # then copy CLAUDE.md and PLAYBOOK-phases-0-3.md into the repo root
#   git add -A && git commit -m "chore: scaffold monorepo" && git push
#
# Safe to run inside an existing repo: any file it would overwrite is moved
# to <file>.bak first, and it tells you which. Your existing README and
# .gitignore are preserved as .bak so you can merge them by hand.
#
# This script creates STRUCTURE and DOCS only. It deliberately does NOT write
# your docker-compose, Dockerfiles, or application code — those are Phase 0
# sessions you work through with Claude Code so you understand them. Every
# stub below has a TODO telling you which playbook session fills it in.
# ---------------------------------------------------------------------------
set -euo pipefail

if [ ! -d .git ]; then
  echo "! No .git here. Run this inside your cloned JustNews repo." >&2
  echo "  (git rev-parse --show-toplevel will tell you where the root is.)" >&2
  exit 1
fi

BACKED_UP=0
bak() {
  if [ -f "$1" ]; then
    mv "$1" "$1.bak"
    echo "  ! existing $1 saved as $1.bak"
    BACKED_UP=1
  fi
}
# write a file, preserving anything already there
w() { bak "$1"; cat > "$1"; }

echo "→ creating directory tree"

dirs=(
  apps/api/src/routers apps/api/src/services apps/api/src/repositories
  apps/api/src/models apps/api/src/core apps/api/migrations apps/api/tests
  apps/inference/src apps/inference/tests
  apps/orchestrator/src apps/orchestrator/tests
  apps/ingestion/src apps/ingestion/tests
  apps/web apps/mobile
  packages/api-client packages/schemas packages/ui
  ml/finding ml/notebooks ml/export ml/data
  infra/docker infra/terraform/modules infra/terraform/envs/azure infra/terraform/envs/aws
  docs/decisions
  scripts
  .github/workflows
)
for d in "${dirs[@]}"; do
  mkdir -p "$d"
  touch "$d/.gitkeep"
done

echo "→ writing .gitignore"
w .gitignore <<'EOF'
# python
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.ruff_cache/
# node
node_modules/
.next/
dist/
.turbo/
.expo/
# env & secrets  (NEVER commit real secrets)
.env
.env.*
!.env.example
*.pem
# data & models — too big for git, and licensed
ml/data/*
!ml/data/.gitkeep
ml/export/*.onnx
*.ckpt
*.pt
# scaffold backups (delete once merged)
*.bak
# os / editor
.DS_Store
.idea/
.vscode/
EOF

echo "→ writing .env.example"
w .env.example <<'EOF'
# Copy to .env for local dev. Real secrets never live in git.
# TODO(session 0.3): fill these in as you build each service.

APP_ENV=local
LOG_LEVEL=debug

# --- database ---
POSTGRES_USER=justnews
POSTGRES_PASSWORD=change_me_locally
POSTGRES_DB=justnews
DATABASE_URL=postgresql+asyncpg://justnews:change_me_locally@localhost:5432/justnews

# --- cache / queue ---
REDIS_URL=redis://localhost:6379/0

# --- auth ---
# generate with: openssl rand -hex 32
JWT_SECRET=
ACCESS_TOKEN_TTL_SECONDS=900
REFRESH_TOKEN_TTL_SECONDS=2592000

# --- services ---
INFERENCE_URL=http://localhost:8001
API_URL=http://localhost:8000
EOF

echo "→ writing README skeleton"
w README.md <<'EOF'
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
EOF

echo "→ writing Makefile"
w Makefile <<'EOF'
.DEFAULT_GOAL := help

help: ## show this help
;;@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## start local stack
;;@echo "TODO(session 0.2): docker compose up -d"

down: ## stop local stack
;;@echo "TODO(session 0.2): docker compose down"

logs: ## tail service logs
;;@echo "TODO(session 0.2)"

test: ## run all tests
;;@echo "TODO(session 0.4): uv run pytest -q && pnpm test"

lint: ## lint + typecheck everything
;;@echo "TODO(session 0.4): uv run ruff check . && pnpm lint"

migrate: ## apply database migrations
;;@echo "TODO(session 3.1): uv run alembic upgrade head"

seed: ## load development fixtures
;;@echo "TODO(session 3.4)"

.PHONY: help up down logs test lint migrate seed
EOF
sed -i 's/^;;/\t/' Makefile

echo "→ writing docs"
w docs/architecture.md <<'EOF'
# Architecture

> Write this yourself. Do not paste a generated version — the value of this
> file is that you can reproduce the diagram on a whiteboard from memory.

## Context
What the product is, who it's for, what it must not do.

## Services
| Service | Responsibility | Scales on | Fails how |
|---|---|---|---|
| api | | | |
| inference | | | |
| ingestion | | | |
| orchestrator | | | |

## Data flow
1. Article enters the system →
2. A user opens the feed →
3. A click is recorded →
4. A training round runs →

## Why it is split this way
One paragraph per boundary. Each paragraph must answer: what would break if
these two services were one?

## Degraded modes
What still works when each service is down?
EOF

w docs/runbook.md <<'EOF'
# Runbook

Fill a section in the moment something breaks, while you still remember.

## How to tell it's healthy
## Common failures
### Symptom → likely cause → fix
## How to restore a database backup
## How to roll back a model version
## How to roll back a deploy
## Who to wake up
(you)
EOF

w docs/decisions/TEMPLATE.md <<'EOF'
# NNN — <short title>

- **Date:** YYYY-MM-DD
- **Status:** proposed | accepted | superseded by NNN

## Context
What forced a decision? Constraints, deadlines, what we knew at the time.

## Options
1. **<option>** — how it works, cost, failure mode.
2. **<option>** —
3. **<option>** —

## Decision
What we chose, in one sentence.

## Consequences
What this makes easy, what it makes hard, what would make us revisit it.
EOF

w docs/decisions/0001-stack.md <<'EOF'
# 0001 — Initial stack

- **Date:** TODO
- **Status:** proposed

## Context
TODO(session 0.4): write this yourself, in your own words, before you write
any application code. If you can't justify a choice here, you don't own it.

## Options
TODO

## Decision
TODO

## Consequences
TODO
EOF

w docs/decisions/0002-cold-start-exploration.md <<'EOF'
# 0002 — Cold start by exploration, not just a topic picker

- **Date:** TODO
- **Status:** proposed

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
TODO — but option 3 is the intended one. Record why once you've built it.

## Consequences (design constraints this creates)
- **Stratify, don't sample uniformly.** Popularity is power-law distributed;
  uniform sampling over the corpus shows only sport and politics. Sample per
  category, then by popularity within category.
- **Log the propensity.** For every card shown, store the probability the
  policy had of showing it, plus its position in the deck. Without this you
  can never do unbiased offline evaluation later (IPS / doubly-robust
  estimators need it), and you will regret it in Phase 11.
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
EOF

echo "→ writing placeholder service notes"
w apps/api/README.md <<'EOF'
FastAPI service: auth, users, feed, saves, search, admin, transparency.
Layering rule: routers → services → repositories. Business logic must not
know it is on HTTP. TODO(session 3.x).
EOF
w apps/inference/README.md <<'EOF'
ONNX serving: candidate generation (ANN over pgvector) + ranking with the
global/group interpolated model. TODO(session 2.x).
EOF
w apps/orchestrator/README.md <<'EOF'
FINDING rounds: client sampling, per-group updates, lambda(t,i) interpolation,
periodic K-means re-clustering, model registry publication. TODO(phase 6).
EOF
w apps/ingestion/README.md <<'EOF'
RSS pull, dedupe, embed, store. Never store full article text — title,
snippet, image URL, source, link only. TODO(session 3.4).
EOF
w ml/README.md <<'EOF'
Research code lives here and is NEVER imported by anything under apps/.
- finding/  adapted research code
- notebooks/ exploration only
- export/   torch -> onnx, quantisation
- data/     gitignored; MIND/Adressa are research-licensed, do not redistribute
EOF

echo "→ writing CI stub"
w .github/workflows/ci.yml <<'EOF'
name: ci
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # TODO(session 0.4): set up uv + pnpm, cache them, run lint and tests.
      # Build this with Claude Code, then explain every line before merging.
      - run: echo "no checks yet"
EOF

w scripts/README.md <<'EOF'
One-off and operational scripts. Anything you run twice belongs here with a
comment saying why.
EOF

echo
echo "✓ scaffold created."
echo
if [ "$BACKED_UP" = "1" ]; then
  echo "  Some files were replaced. Diff them before committing:"
  echo '    for f in *.bak; do echo "== $f"; diff "${f%.bak}" "$f" || true; done'
  echo "  Merge anything you want to keep, then delete the .bak files."
  echo
fi
echo "Next:"
echo "  1. copy CLAUDE.md and PLAYBOOK-phases-0-3.md into this folder"
echo "  2. git switch -c chore/scaffold"
echo "  3. git add -A && git commit -m 'chore: scaffold monorepo' && git push -u origin chore/scaffold"
echo "  4. open the PR, merge it, then start at playbook session 0.1"
