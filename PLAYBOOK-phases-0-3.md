# Playbook — phases 0 to 3

One session ≈ one sitting (2–3 hours). Work them in order. Each session has:
**goal**, the **prompt** to open with, **what you do yourself** (non-negotiable
— this is where the learning is), and **done when**.

Rules that apply to every session:

- Start Claude Code in plan mode. Read the plan. Change it. *Then* say go.
- Review the diff with `git add -p` before committing. Never `git add .`.
- One commit per logical change, present-tense message: `feat(api): add cursor pagination to feed`.
- End the session with the **teach-back prompt** at the bottom of this file.
- If a session runs long, stop and split it. Half a slice reviewed beats a whole slice skimmed.

---

## Phase 0 — Foundations

### 0.1 · Repo and git hygiene
**Goal** Your existing clone is scaffolded, and your first change goes through a pull request rather than straight to `main`.

**You do yourself**
```bash
cd JustNews                      # your existing clone
# put bootstrap.sh, CLAUDE.md and this playbook here
bash bootstrap.sh                # additive; backs up your README/.gitignore as .bak

# merge anything worth keeping from the backups, then remove them
for f in *.bak; do echo "== $f"; diff "${f%.bak}" "$f" || true; done
rm -f *.bak

git switch -c chore/scaffold
git add -A
git commit -m "chore: scaffold monorepo"
git push -u origin chore/scaffold
```
Open the PR on GitHub, read your own diff in the PR view, merge it, then
`git switch main && git pull`. Do this even though you're alone on the repo —
you're building the muscle, and every commercial team works this way.

Then, in the repo settings, protect `main`: no direct pushes, require a pull
request. There's no required status check yet — session 0.4 adds one, and you
come back and turn it on.

**Prompt** (after the above)
```
Read CLAUDE.md and the repo tree. Don't write code. Tell me: what's missing
from this scaffold that a team would expect on day one, ranked by how much
pain its absence causes in month three. For each, say which phase it belongs
in — I don't want everything now.
```

**Done when** you can explain the difference between `git merge` and `git rebase`, what `git add -p` is for, and why protecting `main` matters on a solo repo — without looking any of it up.

---

### 0.2 · Local stack with Docker Compose
**Goal** `make up` gives you Postgres (with pgvector), Redis, a FastAPI `/health`, and a Next.js page.

**Prompt**
```
Plan only, no code yet. I want a docker-compose setup for local dev with:
postgres 16 + pgvector, redis, a FastAPI service, a Next.js app.

Walk me through the decisions I have to make, one at a time, and wait for my
answer before moving on:
- do the app services run in containers or on the host, and what does each
  choice cost me in dev-loop speed and prod parity?
- how do containers find each other, and why doesn't localhost work?
- named volumes vs bind mounts for postgres data
- healthchecks and depends_on: what does "depends_on" actually guarantee?

After I've answered all four, write the compose file and the two Dockerfiles.
```

**You do yourself** Type the FastAPI `/health` endpoint and the Next.js page by hand. They're ten lines each and they're your first lines in this repo.

**Then break it deliberately:** stop Postgres and hit `/health`. Does the API hang, or fail fast? Fix it so it fails fast with a clear message. That fix is worth more than the compose file.

**Done when** `docker compose down -v && make up` works from cold, and you can explain the layer cache order in your Dockerfile.

---

### 0.3 · Reproducibility
**Goal** A stranger with a fresh clone is running in five minutes.

**Prompt**
```
Set up dependency management: uv for the Python services, pnpm workspaces +
turborepo for the JS apps. Explain the lockfile strategy in a monorepo and
what breaks if I commit a lockfile from a different platform.

Then fill in the Makefile targets that are currently TODO stubs.
Keep them thin — make targets should call real tools, not hide them.
```

**You do yourself** Write the README Quickstart. Then actually test it: clone the repo into `/tmp` and follow your own instructions literally, doing nothing you didn't write down. Everything you had to improvise is a README bug. Fix and repeat.

**Done when** the cold-clone test passes twice in a row.

---

### 0.4 · CI and your first ADR
**Goal** Every push runs lint + typecheck + tests. ADR 0001 written by you.

**Prompt**
```
Write the GitHub Actions workflow: set up uv and pnpm with caching, run ruff,
mypy, pytest, and the JS lint/typecheck. Explain the caching keys — what
makes a cache hit vs miss, and what a stale cache would do to me.
Keep the workflow under 60 lines.
```

**You do yourself** `docs/decisions/0001-stack.md`, handwritten, no AI. Context, three options you actually considered, the decision, the consequences. Five sentences per section. If you can't fill Options honestly, you didn't make a decision — you accepted a default, and that's what the ADR should say.

**PHASE 0 GATE** — delete `node_modules`, `.venv`, and all containers. Rebuild from a fresh clone in under five minutes using only your README.

---

## Phase 1 — Own the paper and the repo

### 1.1 · Get FINDING running
**Goal** The original repo trains, on your machine, on MIND-small.

**Prompt**
```
I'm cloning https://github.com/yusanshi/FINDING (CIKM '23 code, so expect
dependency rot). Plan only:
1. how to isolate this so it can't pollute my main environment
2. a strategy for pinning versions when the original pins are unbuildable —
   what do I pin exactly, and how do I record what I changed?
3. the smallest run that proves the pipeline works end to end

Then walk me through the repo like an onboarding buddy: the data flow for ONE
training round — which file, which function, what shape the tensors are, what
gets mutated. Use file:line references. Don't summarise the paper; I've read it.
```

**Done when** one short run completes and you have `ml/finding/PORTING-NOTES.md` listing every change you made and why.

---

### 1.2 · Own the metrics
**Goal** You can compute nDCG by hand. You will be asked this in an interview.

**You do yourself, first, on paper:** a ranked list of 5 items with relevance `[0,1,0,1,0]`. Compute DCG@5, IDCG@5, nDCG@5. Then MRR. Then write them in Python in `ml/finding/metrics.py` and unit-test against your hand calculation.

**Prompt** (only after your version passes)
```
Here's my metrics implementation and tests. Review it against how the FINDING
repo computes AUC/MRR/nDCG. Where do they differ, and does the difference
change the reported numbers? Also explain why nDCG@10 is higher than nDCG@5
in the paper's Table 1 — is that expected, and what would it mean if it weren't?
```

**Done when** your implementation and theirs agree to 4 decimal places on the same input.

---

### 1.3 · Find the equations in the code
**Goal** You can point at the two mechanisms that make this paper the paper.

**Prompt**
```
Show me exactly where these live in the FINDING codebase, with file:line:
- Eq. 7:  lambda(t,i) = (1 - alpha^-t) * ((i+1)/N)^beta
- Eq. 8:  the transition-matrix remix of group models after re-clustering
For each: what are the variable shapes, when is it called, and what would
visibly break if I set beta = 0? Then quiz me on my answers.
```

---

### 1.4 · The toy simulation
**Goal** Intuition, built by your own hands.

**You do yourself, no AI:** ~60 lines of pure Python/NumPy. 20 fake users, 2 latent interests, a global vector plus K group vectors, the interpolation rule from Eq. 7, K-means every T rounds. Print cluster membership each round. Watch the groups separate.

Only afterwards, ask: *"here's my toy simulation — where does it diverge from what the paper actually does, and does that divergence matter?"*

**PHASE 1 GATE** — whiteboard: what happens to one user's data during round *t*, and why the authors cluster on user vectors rather than gradients.

---

## Phase 2 — Model to service

### 2.1 · Export to ONNX
**Prompt**
```
Plan only. I need the trained NRMS news encoder and user encoder exported to
ONNX so I can serve them on CPU.
- which parts of this model should be exported as separate graphs, and why
  does the news/user split matter for my serving architecture?
- what are the dynamic axes, and what breaks if I get them wrong?
- how do I verify the ONNX output matches PyTorch, and what tolerance is
  acceptable?
Then implement in ml/export/. I'll write the parity test myself.
```

**You do yourself** The parity test: same input to both, assert allclose. Pick the tolerance and justify it in a comment.

---

### 2.2 · Embed the corpus, add pgvector
**Prompt**
```
One slice: embed every article with the news encoder at ingest time and store
the vector in Postgres via pgvector.
Before code, answer: HNSW vs IVFFlat for ~10^5 articles with heavy recency
filtering — which index, what parameters, and what recall am I trading away?
What happens to the index when I re-embed everything after a model upgrade?
```

**Done when** you can run an ANN query and explain, from `EXPLAIN ANALYZE`, whether the index was actually used. It often isn't — find out why.

---

### 2.3 · The `/rank` endpoint
**Prompt**
```
Build POST /rank {user_id, candidate_ids} -> ranked list with scores, in the
inference service. Load the model once at startup, not per request.
Important: this is CPU-bound work inside an async framework. Explain what
happens to concurrent requests if I run inference directly in the coroutine,
then implement it correctly.
Instrument it so I can see time spent in: candidate fetch, embedding lookup,
user-vector compute, scoring, serialisation.
```

**You do yourself** Measure it under load (`hey`, `wrk`, or k6). Write the numbers down. Predict the bottleneck *before* you look.

---

### 2.4 · Make it 2× faster
No prompt. You profile, you form a hypothesis, you test it, and you only ask AI once you have a specific question. Batching, quantisation, caching user vectors, cutting serialisation — pick based on the measurement, not on vibes.

**PHASE 2 GATE** — show the timing breakdown of one `/rank` call, explain where every millisecond goes, and what you traded for the speedup.

---

## Phase 3 — Backend core

### 3.1 · Schema design
**You do yourself, first:** draw the ER diagram on paper. Users, articles, sources, categories, interactions, saves, sessions, groups, model versions. Decide keys, nullability, and what's a foreign key vs a soft reference.

**Prompt**
```
Here's my ER diagram (described below). Critique it as a DBA who will have to
run this at 10 million interaction rows. Specifically:
- which queries will be slow and what indexes do they need?
- where have I over-normalised, and where will I regret denormalising?
- what should be an enum vs a lookup table, and why?
- what's my partitioning story for the interactions table?
Don't write the schema. Give me the critique and I'll revise.
```
Then, second round: *"here's my revision — now write the SQLAlchemy models and the Alembic migration."*

---

### 3.2 · Auth, part 1
**Prompt**
```
One slice: registration + login. argon2id hashing, email verification token,
access token + refresh token.
Before code: explain the threat model. What does each of these defend against
— argon2 over bcrypt over sha256, httpOnly+SameSite cookies over localStorage,
short access TTL with rotating refresh tokens? For each, name the attack it
stops and the attack it doesn't.
```

---

### 3.3 · Auth, part 2
**Prompt**
```
Now: refresh-token rotation with reuse detection, logout, logout-everywhere.
Walk me through the exact sequence when a user's refresh token is stolen and
both the attacker and the real user try to refresh. What does my system do?
Then implement. I'll write the concurrency test.
```

**You do yourself** The test where two clients refresh simultaneously with the same token. Watch it fail. Fix it. This is the single most instructive bug in the whole phase.

---

### 3.4 · Ingestion worker
**Prompt**
```
One slice: a Celery worker that pulls a list of RSS feeds on a schedule,
normalises entries, dedupes, embeds, and stores.
Design questions first:
- dedupe strategy: URL canonicalisation vs title similarity vs content hash —
  which combination, and what's the false-merge risk?
- what makes this job idempotent if it runs twice on the same feed?
- backoff and failure isolation: one dead feed must not stall the others
Store title, snippet, image URL, source, canonical link only. Never full text.
```

---

### 3.5 · Feed endpoint
**Prompt**
```
GET /feed with cursor pagination, calling the inference service for ranking.
- design the cursor: what's encoded in it, and why is it not an offset?
- what does the feed return when the inference service is down or slow?
  I want an explicit degraded mode, not a 500.
- what's the caching story for a personalised feed — what can be cached and
  for how long?
```

---

### 3.6 · The interaction log (do this carefully)
**Goal** The table that makes Phases 6 and 11 possible. Getting the schema wrong here is unrecoverable — you cannot backfill data you never captured.

**Prompt**
```
Design the interaction event schema. It has to serve four consumers:
1. the feed (don't re-show what was seen)
2. FINDING training replay (needs impressions with negatives, per session)
3. online experiment analysis (needs variant assignment)
4. unbiased offline evaluation (needs propensity + position)

Explain what propensity logging is, why it must be written at serve time by
the policy that made the decision, and what specifically I lose forever if I
skip it. Then propose the schema and the write path.
```

**You do yourself** Write out, in `docs/decisions/0003-interaction-log.md`, exactly what each column means and who consumes it. This ADR will save you later.

---

### 3.7 · Exploration deck (cold start)
**Goal** New users discover interests by exploring, not just by ticking boxes.

**Prompt**
```
Implement GET /explore/deck for cold-start users, per docs/decisions/0002.

Design first, no code:
- Sampling: stratified across categories, then by popularity within category.
  Show me the maths — with 20 cards and 14 categories, what's the allocation,
  and how do I avoid showing 14 near-identical mainstream stories?
- Epsilon-greedy vs Thompson sampling for this: I have no priors on a new
  user, ~20 interactions to learn from, and 14 arms. Which one, honestly, and
  is a bandit even the right frame for 20 pulls?
- What do I record per card: shown, position, propensity, dwell, click, skip,
  explicit "not interested". What weights do I give each signal, and how do I
  avoid treating "scrolled past fast" as a strong negative?
- Exit condition: how many interactions before I have enough signal, and what
  do I do for the user who skips the whole deck?

Then implement the endpoint and the event writes. I'll build the UI.
```

**Then the tie-in — this is the good part:**
```
Now the handoff to personalisation: after the deck, run the user encoder over
the articles the user engaged with to produce a user vector, and assign them
to the nearest FINDING group centroid.
Explain how this maps onto the paper's evaluation-time handling of users who
exist only in the evaluation set (Alg. 1, Evaluation, lines 4-7). Where does
my product flow match it and where does it differ?
```

**Done when** a brand-new account gets a visibly different feed after going through the deck than after skipping it — and you can show, from the interaction log, why.

---

### 3.8 · Saves, history, "not interested", and the OpenAPI contract
**Prompt**
```
Last slice of this phase: saves, reading history, and a "not interested"
signal that actually affects ranking. Then publish the OpenAPI spec and
generate a typed TS client into packages/api-client.
Explain how the generated client stays in sync — what breaks the contract
silently, and how CI can catch it.
```

**PHASE 3 GATE** — draw your ER diagram from memory. Then answer: what happens if the same user logs in on two devices and both refresh their token at the same instant?

---

## The two prompts to reuse constantly

**End of every session — teach-back:**
```
Quiz me on what we just built. 8 questions, hardest last, about why-decisions
not syntax. One at a time, wait for my answer, don't reveal the answer until
I've tried. Mark each answer and name the exact concept to go read if I miss it.
```

**Before every merge — adversarial review:**
```
Review this diff as a hostile staff engineer at a company that has been burned
before. Find: race conditions, unbounded queries, missing indexes, unhandled
failure modes, auth/authz holes, anything that breaks at 100x data. Rank by
blast radius. Don't fix anything — just give me the list.
```
