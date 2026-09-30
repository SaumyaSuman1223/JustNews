# Recommendations: diagnosis and overhaul (2026-09-30)

**Scope:** every place JustNews decides what a reader sees, the data it learns
from, and whether FINDING (Yu et al., CIKM '23; `resources/FINDING`) can run on
the site now.

**Method:**
- Read the serving code:
  - backend: `services/feed.py`, `ranking.py`, `content.py`, `exploration_deck.py`, `issues.py`
  - web: `lib/discover.ts`, `components/discover/storyLayout.ts`, `app/api/click/route.ts`
- Read the logging path end to end, and the FINDING reference code.
- Measured the local corpus: 3,490 articles after the 27–29 September ingests.

**Caveats:**
- Production interaction counts can't be read from this checkout, which has no production credentials. The admin analytics overview shows them.
- Local development uses the hashing embedder, so local story clustering says nothing about production, which uses MiniLM.

## Bottom line

1. **What readers get today is mostly a clock.**
   - The personal ranker only ever sees the newest 200 articles in the reader's languages: about 4 hours of English, or 2½ hours for an English and Hindi reader.
   - Inside that window it knows nothing about what the reader reads, beyond explicit topic follows.
   - Most readers never reach it at all.
2. **The logs can't train anything yet.**
   - Impressions are logged for cards nobody scrolled to.
   - Positions are numbered differently on the two sides of the click–impression join.
   - The ranked head is logged at propensity 1.0, so no new ranker can be evaluated offline against it.
   - Only one surface logs impressions.
   - Every day this stays as it is loses training data that can't be backfilled.
3. **FINDING can be built now, but can't yet be trained on JustNews readers.**
   - What can be done today, on this machine:
     - the port
     - the MIND-small reproduction
     - a frozen-MiniLM variant whose user tower reads the article vectors JustNews already stores
     - a serving path that keeps ADR 0004 intact
   - What's missing is readers. FINDING's groups need hundreds of active readers with histories, and the beta has dozens at most.
   - Shipped honestly now, it is a user tower pretrained on MIND serving signed-in readers, with groups off until the data justifies them.

**Recommended order:**
1. Fix logging (days).
2. Build heuristic v2 for everyone; this is the biggest visible win.
3. Build FINDING offline, in parallel.
4. Run FINDING as a shadow policy.
5. Go live only after it beats v2 offline.

## 1. What decides each surface today

| Surface | Who | Ordering | Impressions logged |
|---|---|---|---|
| For You | signed in with an invite | 50%: `heuristic_v1` over the newest 200. 50%: newest first | yes, every card on each page |
| For You | everyone else | chosen-topic filter: 12 ranked, then newest first | no |
| Top | everyone | `score_for_everyone` over the newest 300 for 24 cards, then newest first | no |
| Topic | everyone | 12 ranked, then newest first | no |
| Aquila | everyone | composer (age, breadth, reach, trust) at publish time | yes, but clicks are never reported |
| Article "read next" | everyone | newest in the same topic; newest from the same source | no |
| Onboarding deck | invited | stratified topic sample, with real propensities | yes |

There are six orderings with overlapping formulas (recency half-life, breadth, trust), implemented in four places.

## 2. Diagnosis: ranking

**R1. Personalisation reaches almost no one.**
- `heuristic_v1` runs only for signed-in readers with an invite, on For You.
- Everyone else, including signed-in readers without an invite, gets a topic filter over a chronological list.
- Signed-out clicks are dropped (`app/api/click/route.ts:21`), so nothing a signed-out reader does ever shapes anything.

**R2. Half of those it reaches get chronology.**
- `assign_policy` (`services/feed.py:102`) splits invited readers 50/50 between the ranker and a chronological control, and each reader stays in their arm.
- With a few dozen readers, that comparison has almost no statistical power, while half the beta gets the weaker feed the whole time.

**R3. The candidate pool is "the newest 200", so the ranker is ranking a clock.**
- The pool is `CANDIDATE_POOL_SIZE = 200` (`services/feed.py:61`), newest first.
- How far back that reaches, on the 28–29 September ingest:

  | Languages | Newest 200 (For You) | Newest 300 (Top) |
  |---|---|---|
  | English | 4h 12m | 8h 10m |
  | English and Hindi | 2h 23m | 3h 56m |

- Nothing older can appear, however relevant. The 18-hour recency half-life barely matters inside a 4-hour window.
- The pool's source mix is simply each publisher's posting rate:
  - The Hindu is 64 of the newest 200 English articles.
  - Nature, NASA and Ars Technica have 0 between them, and NPR has 1. Yet over 36 hours those four filed 62 English articles.
  - A reader who follows Science almost never sees the science publishers.

**R4. It learns nothing from reading.**
- The score is recency × topic-follow boost × popularity × trust × language (`services/ranking.py:74`).
- The only personal terms:
  - ×1.6 when the article shares a top-level topic the reader follows.
  - ×0.15 when they have already clicked the article.
- Source follows and story follows are stored but not used.
- Clicks, saves and shares only feed global popularity.
- Every article has a 384-dimension multilingual embedding, used for dedup and clustering, but the ranker never reads it.
- So someone who has opened 50 cricket stories and followed nothing gets the same feed as a brand-new reader.

**R5. No fatigue.**
- A card that is shown and ignored is never demoted: `seen_article_ids` counts clicks only.
- Deterministic ranking over a slowly changing pool shows the same first screen on every visit, until newer articles push it off.

**R6. Top is ranked for one page only.**
- `stream()` (`lib/discover.ts:125`) puts 24 importance-ordered cards first; from page 2 it is newest first.
- The last audit's "firehose" problem moved to page 2 rather than going away.

**R7. Diversity is by label, not meaning.**
- The MMR similarity (`services/ranking.py:149`) is 1.0, 0.6 or 0.3, from "same source" and "shared top-level topic" alone.
- Two outlets reporting the same event count as unrelated whenever clustering missed the match.
- The stored embeddings would measure the similarity directly.

**R8. Popularity is raw clicks.**
- It is `log1p(clicks in the last 7 days)`, from invited readers only.
- It isn't normalised by impressions or position. Whatever is shown first gets clicked more and then ranks higher, a rich-get-richer loop.

**R9. Topics are coarse and incomplete.**
- Every tag is one of the 17 top-level IPTC concepts.
- 24% of articles (820 of 3,490) have no tag at all, so the follow boost can't reach them.
- Tagged share by source: BBC Mundo 12 of 75, BBC Hindi 22 of 75, Aaj Tak 36 of 105.

**R10. Minor: language detection strays.**
- 14 of 3,490 articles are detected wrongly: Hindi headlines as Marathi, and one Hindu headline as French.
- Those articles drop out of their real language's filter.

## 3. Diagnosis: the data FINDING, or any learned ranker, needs

**D1. Impressions include cards nobody saw.**
- `get_feed_page` logs all 24 cards on a page when it is served.
- A reader who reads the lead and leaves has "rejected" the other 23.
- Discover also prefetches the next page before the reader reaches the end of the current one, and that page's impressions are logged too.
- In bulk, the negatives are wrong.

**D2. Positions don't join.**
- Impressions are numbered from 0 on every page (`services/feed.py:243`).
- Clicks report the card's index in the whole accumulated list.
- The layout (`arrange` in `storyLayout.ts`) moves cards up to four slots and gives them different sizes (lead, wide, card).
- Position bias can't be corrected on this data, and it can't be repaired afterwards.

**D3. The ranked head is logged at propensity 1.0.**
- That is correct for a deterministic policy.
- But it means inverse-propensity and doubly-robust evaluation, which is Stage 6's plan, can only score a new ranker where it agrees with the old one.
- The only randomness is the last 10% of each page (positions about 22–23), where clicks are rarest.

**D4. Only one surface logs impressions.**
- Top, topic, story and read-next log none, and neither does any signed-out traffic.
- Signed-in clicks on those surfaces arrive without an impression, so they have no negatives to pair with.
- Signed-out clicks are dropped.

**D5. Aquila is half-logged.**
- Its impressions are logged, but its clicks aren't: its links are plain `Link`s that report nothing.
- `aquila` isn't in `VALID_SURFACES` (`services/interactions.py:31`), so a click report from it would be rejected anyway.

**D6. Only clicks count.**
- Saves, shares, follows and "not interested" are logged but unused as labels.
- `dwell` is in the schema but never reported.
- Most cards open at the publisher, so the only after-click signal JustNews can see is on its own story and article pages.

**D7. Admin CTR by language mixes two meanings.**
- Impressions are filtered on the interface language.
- Clicks are filtered on the article's language, because `report_click` stores `locale=article.language`.
- The per-language A/B numbers are wrong whenever someone reads outside their interface language.

## 4. FINDING: what it is, and whether it can run here

### What the code does

- **NRMS:** a news encoder (GloVe 300d, then multi-head self-attention, then additive attention) and a user encoder that runs the same layers over the reader's last 50 clicked news vectors. The click score is their dot product.
- **Around NRMS, FINDING adds a simulated federated trainer** (`federated_group.py`):
  - one global model plus `num_groups = 8` group models;
  - each round samples about 50 users, and each group model trains on its own users;
  - the global model then takes a step on the size-weighted average gradient.
- **Every 10 rounds, interpolation.** Each group model is pulled toward the global one, layer by layer, with `p = (1 − 1.0003^−r) · ((i+1)/n)^0.5`: deeper layers and later rounds stay more personal.
- **Every 100 rounds, re-clustering.**
  - Users are re-clustered by KMeans on the global model's user vectors.
  - The group models are remixed through the old-to-new transition matrix.
  - A Hungarian matching keeps group ids stable across re-clusterings.
- **Evaluation:** AUC, MRR and nDCG@5/10 per impression, with each user scored by their own group's model.
- **Homomorphic encryption:** optional C++, and irrelevant here because serving is centralised.

### Porting reality

- **It doesn't run on Python 3.12 as it stands:** `from distutils.util import strtobool` fails because `distutils` was removed in 3.12.
- **Rewrite it, don't import it.** Its argparse arguments are `eval`'d into lambdas, it monkey-patches `torch.optim.Optimizer.parameters`, and it relies on a global `args`. `apps/` never imports `ml/` anyway.
- **Fixes needed for our vectors and histories:**
  - 384-dimension vectors need a head count that divides 384: 12 or 16, not 15.
  - The user attention has no padding mask. With JustNews-sized histories of a handful of clicks, padding would dominate, so it needs a mask.
  - Softmax is a raw `exp` with no max-subtraction. That is fine at GloVe scales but worth fixing.
- **Data:**
  - MIND-small (50,000 users) plus GloVe 840B (a 2 GB download).
  - MIND is licensed for research, non-commercial use. Check the licence before MIND-trained weights serve a public site.
- **Hardware:** an RTX 3050 6 GB and 16 cores here. That is enough for NRMS and FINDING on MIND-small (the code has a `save_gpu_memory` switch for small GPUs). The frozen-encoder variant is tiny, around 0.5M parameters.

### How it fits the site without breaking ADR 0004

- **News tower:** the frozen `paraphrase-multilingual-MiniLM-L12-v2` vectors already stored on every article. Production ingest uses this model.
- **User tower:**
  - trained offline;
  - run in a scheduled job for each reader with at least 5 positive events (the ingest workflow already installs torch for sentence-transformers);
  - its output is one 384-dimension user vector per reader, stored with its model version and group.
- **Request path:** `score += w · (user_vector · article.embedding)`. That is a dot product on stored vectors, the same kind of arithmetic as today's ranker, with no forward pass.
- **Article vectors never change.** A linear news-side adapter can be folded into the stored user vector, since uᵀWn = (Wᵀu)ᵀn, so a new model never means re-embedding articles.
- **Readers with no history:** the nearest group centroid, or the heuristic. That is how FINDING itself handles unseen users.
- **Rollout:** `finding_v1` is registered in `POLICIES` and kept out of `EXPERIMENT_POLICIES` until offline evaluation passes. That seam already exists.

### The data gap, plainly

- FINDING trains on (reader, click history, impression with clicked and unclicked items).
- The local database has 0 clicks. Production logs impressions only for invited, consenting readers on For You; the admin overview shows how many.
- Group structure needs hundreds of readers with real histories. Eight groups over a few dozen readers is noise; ROADMAP §2 says the same.
- A tower trained on MIND (US news from 2019, in English) faces a shift in domain and in language on JustNews. MiniLM's shared vector space makes the transfer to Hindi and Spanish plausible, but not proven.

### Verdict

- **Now:**
  - Part A: a faithful port and a MIND-small reproduction, with the metrics unit-tested.
  - Part B pretraining: the same trainer over frozen MiniLM vectors of MIND titles.
  - The export, and the nightly user-vector job.
  - `finding_v1` as a shadow policy: scored alongside v2 and logged for offline replay.
- **Not now:**
  - fine-tuning on JustNews readers (there is no data);
  - groups in production (too few readers);
  - any claim that it's federated. It isn't, and CLAUDE.md's honesty rule forbids saying so.
- **It won't help signed-out readers.** The user tower needs a history tied to a person, so they get heuristic v2.

## 5. The overhaul

```
candidates ─► reader profile ─► one scorer ─► one per story ─► diversify ─► sample ─► log
(by time,      (content vector,  (surface      (reader's        (embedding   (real      (served slot,
 by profile,    topic/source      weights)      language first)  MMR, source  propensity) viewed or not,
 follows, big   affinity,                                        cap)                     outcome)
 stories)       fatigue)
```

**Candidates.** One generator serves every surface. It unions these sources, then dedupes by story:
- a recent window bounded by time (36 hours), not by count, with a per-source quota so posting rate doesn't set the mix;
- the top ~200 by embedding similarity to the reader's profile, over 72 hours;
- followed topics, sources and stories, including new reports on a followed story;
- big stories carried by many sources and languages in the last 36 hours.

MMR runs only over the top ~300 scored candidates, so it stays inside the request budget.

**Reader profile.** Updated when events are written, and nightly. Arithmetic only.
- **Content vector:** a time-decayed mean of the embeddings of clicked, saved and shared articles. "Not interested" subtracts.
- **Topic and source affinity:** learned from impressions and clicks, with a prior so that one click isn't a preference. Follows act as strong priors.
- **Fatigue:** how many times an article was shown without a click in the last 72 hours.

**Score.** One log-linear function with weights per surface: Top leans on importance, For You on the profile. The six orderings become one library.

**Diversity.** MMR on embedding cosine plus same-source, a hard per-source cap, and a topic quota.

**Randomisation with real propensities.**
- Sample each page from the scored list, by Plackett–Luce at a set temperature or by random swaps of neighbours, and log each item's probability.
- Spread the exploration slots through the page instead of parking them at the end.

**Signed-out readers:** see decision 1.

**Logging:** fix D1 to D7.

**Evaluation.**
- Every candidate ranker gets an offline replay (SNIPS, doubly robust) over the logged propensities, shown in the admin console.
- Online tests come only after an offline win.

## 6. Plan

| Phase | What | Size | Why this order |
|---|---|---|---|
| 1 | Logging:<br>• viewability events<br>• one position system, plus the rendered slot<br>• impressions on Top and topic views<br>• Aquila clicks<br>• save, share, follow and "not interested" as labels<br>• the CTR language fix | 1–2 slices (migration, API, web) | Lost data can't be backfilled |
| 2 | Heuristic v2:<br>• candidate generator<br>• reader profile and one scorer<br>• embedding MMR and fatigue<br>• randomised ranking with propensities<br>• nearest-neighbour topic tags at ingest for untagged articles<br>• ADR 0015 | 3–4 slices | Biggest visible win, for every reader |
| 3 | FINDING Part A: port into `ml/finding`, MIND-small reproduction, `PORTING-NOTES.md`, metric tests | offline, hours of GPU time | Proves the port before anything depends on it |
| 4 | FINDING Part B:<br>• frozen-MiniLM training<br>• export with a parity test<br>• nightly user vectors<br>• `finding_v1` shadow policy<br>• offline replay against v2 | 2–3 slices | Needs phase 1's logs and phase 2's policy seam |
| 5 | Live test, then groups | when there are enough readers | Recorded honestly either way |

## 7. What's good and stays

- The policy registry: a new ranker is one function and one entry.
- Impression ids handed back to the client, and the propensity column.
- The consent gate at the click route.
- Story clustering on multilingual embeddings.
- `cap_per_source` and `spreadRuns`.
- The onboarding deck's real propensities.

## 8. Decisions needed

1. **Signed-out readers.** Options:
   - Personalise from on-device history: the browser keeps its last reads, and the server uses them per request and stores nothing.
   - Log anonymous reading by session under the existing analytics consent. That is also the only way the beta produces enough data for FINDING.
   - Both, or neither.
2. **The A/B split.** Keep 50/50, or move to a small chronological holdout (about 10%) and rely on offline replay over the new propensities.
3. **Where to start.**
