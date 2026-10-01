# FINDING on Adressa-1week: results

Test-set metrics, in percent. The split is the original preprocessing's:
- **Test:** 43,599 reader-days.
- **Negatives:** 20 sampled per click.

Each model is selected on validation AUC (patience 3), then tested once. How the runs were made is in `PORTING-NOTES.md`. The raw outputs are in `results/`:
- `original-*.json` for the original code, with its validation curve, extracted from its git-ignored logs by `summarise.py`;
- `tower-*.json` for our runs.

## The table

| Model | Runs | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|---|
| **Paper**, NRMS centralised | mean of 5 | 72.67 | 29.39 | 35.66 | 41.16 |
| **Paper**, NRMS + FINDING | mean of 5 | 72.51 | 28.89 | 35.81 | 41.28 |
| **Original code**, NRMS centralised (Part A) | 1 | 68.73 | 29.50 | 36.85 | 41.02 |
| **Original code**, NRMS + FINDING (Part A) | 1 | 70.46 | 28.65 | 35.67 | 40.33 |
| **Our tower**, centralised (Part B) | seeds 0-2 | 73.61 ± 0.80 | 26.91 ± 0.39 | 32.82 ± 0.59 | 38.77 ± 0.65 |
| **Our tower**, FINDING, group models (Part B) | seeds 0-2 | 74.14 ± 0.94 | 27.01 ± 1.03 | 32.99 ± 1.60 | 39.10 ± 1.44 |
| **Our tower**, FINDING, global model only | seeds 0-2 | 74.14 ± 1.05 | 26.90 ± 1.15 | 32.85 ± 1.80 | 38.93 ± 1.60 |

**Notes on the table:**
- **Spread.** "±" is the sample standard deviation across seeds.
- **Paper numbers.** Table 1 of Yu et al., CIKM '23; the paper reports no spread.
- **Test models.** FINDING is tested the way the original code tests it: each reader is assigned a group by the clusterer over the global model's user vectors, then scored with that group's model.

**Per-seed test AUC, our tower:**

| Seed | Centralised | FINDING groups |
|---|---|---|
| 0 | 73.79 | 74.51 |
| 1 | 74.31 | 73.07 |
| 2 | 72.74 | 74.84 |

## What it says

1. **FINDING's procedure costs nothing, but buys nothing measurable either.** The paper's claim is that FINDING trains on simulated clients and matches centralised training (72.51 against 72.67 AUC). Our tower reproduces that claim.
   - FINDING scored 74.14 ± 0.94 AUC; centralised training scored 73.61 ± 0.80.
   - The gap is smaller than the seed-to-seed spread on both sides.
   - Group models and the global model alone score the same.
   - With three seeds, the honest reading is "no worse", not "better".
2. **The original code reproduces the paper's ranking metrics to within about a point, and lands lower on AUC.**

   | Original code vs the paper | AUC | MRR | nDCG@5 | nDCG@10 |
   |---|---|---|---|---|
   | FINDING | 70.46 vs 72.51 | 28.65 vs 28.89 | 35.67 vs 35.81 | 40.33 vs 41.28 |
   | Centralised | 68.73 vs 72.67 | 29.50 vs 29.39 | 36.85 vs 35.66 | 41.02 vs 41.16 |

   - **Run count.** The paper averages five runs; these are one each.
   - **Early peaks.** Both validation curves peaked early and then fell steadily, and early stopping kept the peak:
     - NRMS after its first epoch (68.49);
     - FINDING at round 1,200 of 12,000 (70.11).
     A run like that can easily sit a few AUC points from a five-run mean.
   - **The paper's comparison holds.** Between the two original runs, FINDING is +1.7 AUC and −0.9 MRR against centralised training. That is the paper's own "comparable to centralised", within noise.
   - **Closing the AUC gap.** Running four more of each takes about 35 minutes per run here.
3. **The frozen multilingual encoder trades top-of-list sharpness for breadth.**
   - Breadth: our tower separates clicked from unclicked articles better than NRMS (AUC 73.6, against 68.7-70.5 for the original code and the paper's 72.5-72.7).
   - Sharpness: it puts the clicked article first less often (MRR 26.9 against 28.7-29.5; nDCG@10 38.8 against 40.3-41.3).
   - Why that is plausible: NRMS learns its title encoder end to end on Adressa's Norwegian titles, while ours is MiniLM, frozen, plus one linear adapter. The frozen encoder knows what articles are *about*; the trained one learns what this newspaper's readers click.
   - What we keep in exchange is what the site needs. One vector space serves every language JustNews carries. Article vectors never need recomputing. Serving is a stored vector and a dot product (ADR 0004, ADR 0016).

## What this means for the site

Nothing here changes the gate in ADR 0016.
- **No public weights.** These weights were trained on research-licensed data and are never served.
- **Readiness.** The numbers say the tower and the training procedure work. They do not say `finding_v1` beats ranker v2 on JustNews's own readers.
- **What decides that.** `jnfinding.replay`, on JustNews's own logs, once there are enough of them.

## Not run

- **MIND-small.** The dataset is gated behind a signed-in Hugging Face account (`PORTING-NOTES.md` has the steps).
- **NAML.** It needs article bodies and categories in the paper's form, and NRMS is the only model the paper and Part B share.
- **More seeds or runs.** Four more runs of each original model would make those rows comparable to the paper's mean of five.
