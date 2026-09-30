# FINDING: porting notes

This covers Stage 6 of `docs/ROADMAP.md`:
- **Part A:** the original code, run as it was written except for the changes below.
- **Part B:** the user tower over JustNews's frozen encoder.

The decision is ADR 0016.

## Source

- **Code:** https://github.com/yusanshi/FINDING at commit `be9bb78bdcd3273c065c1ab1e96140c3db731e4c`.
- **Not vendored.** The repository carries no licence, so `reproduce.sh` fetches it into `ml/finding/.work/`, which is git-ignored, and applies `porting.patch` there.
- **Environment:** `ml/pyproject.toml`, a separate `uv` project that isn't part of the app workspace. It pins torch 2.6 (CUDA 12.4) and Python 3.12.
- **Hardware:** an RTX 3050 6 GB laptop GPU and 16 CPU threads, with 7 GB of RAM under WSL2.

## Changes to the original code

Every change is in `porting.patch` and marked `PORTING` in the code. None changes what the model or training does.

| File | Change | Why |
|---|---|---|
| `parameters.py` | `strtobool` defined locally instead of imported from `distutils` | `distutils` was removed in Python 3.12 |
| `utils.py` | `np.Inf` becomes `np.inf` | `np.Inf` was removed in NumPy 2.0 |
| `dataset.py` | The evaluation split uses `iloc` over `np.array_split` of the row indexes | `np.array_split` on a DataFrame now returns plain arrays. The split is the same |
| `model/general/trainer/federated_group.py` | `KMeans(n_clusters, n_init=10)` | scikit-learn 1.4 changed the default `n_init` from 10 to `'auto'` (a single k-means++ run). Leaving it would quietly change FINDING's clustering |

## Changes to the environment only

- **`nltk.download('punkt_tab')`** as well as `punkt`: NLTK 3.9 tokenises from `punkt_tab`.
- **`phe` (python-paillier) installed:** `train.py` imports the optional homomorphic-encryption module even when encryption is off.
- **`swifter`, `coloredlogs` and `matplotlib` installed:** the original code imports them.
- **The homomorphic-encryption C++ tree is not built:** the paper's code makes it optional, it doesn't change the results, and serving here is centralised anyway.
- **Stale cache lock files are deleted before each run:** a run that crashes while writing its dataset cache leaves a `.lock` that the next run would wait on forever.

## Data

- **Adressa-1week** comes from https://reclab.idi.ntnu.no/dataset/one_week.tar.gz (1.4 GB compressed, 13 GB unpacked, 7 day files).
  - It was preprocessed by the original `data_preprocess/adressa.py` in 2 minutes 41 seconds, peaking at 1.4 GB of memory.
  - The result: 20,428 articles and 47,124 readers.
  - Splits: 44,094 reader-days for training, 21,257 for validation and 43,599 for test.
  - Evaluation negatives are sampled, 20 per click, by the original preprocessing.
- **MIND-small** was not run.
  - Its original Azure links now return 409 (public access disabled).
  - The official site (msnews.github.io) links to a Hugging Face mirror (`yjw1029/MIND`), which is gated and returns 401 without a signed-in account that has accepted MIND's licence.
  - To run it:
    1. Accept the terms on that page.
    2. Download `MINDsmall_train.zip` and `MINDsmall_dev.zip` into `ml/data/raw/mind-small/`, and GloVe 840B (2 GB, still at nlp.stanford.edu) into `ml/data/raw/glove/`.
    3. Run `reproduce.sh prepare mind-small`.
- **Licences:** both datasets are research-licensed. Nothing trained on them serves the public site (ADR 0016).

## Part B: what differs from the paper, and why

- **The news tower** is the frozen `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions) that JustNews embeds every article with, plus one trainable linear adapter. It replaces NRMS's news encoder over GloVe word vectors.
  - This is what makes the model multilingual.
  - It also means article vectors never need recomputing: the adapter folds into the served user vector, Wᵀu.
- **The user encoder** follows NRMS, with three changes:
  - The history is masked. FINDING attends over the zero-vector padding, which matters for short histories.
  - It uses torch's `MultiheadAttention`, which exports to ONNX.
  - It has 12 heads, because 384 isn't divisible by 15.
- **FINDING's procedure** is re-implemented from the paper and the reference trainer:
  - groups, per-round client sampling proportional to group size, and one batch per client group;
  - size-weighted gradient averaging into the global model;
  - interpolation every 10 rounds, of parameters and Adam moments;
  - re-clustering every 100 rounds, with a Hungarian relabel and a transfer-matrix remix;
  - validation every 600 rounds, with patience 3 on AUC.
  - All defaults are the paper's.
  - The layers for the depth coefficient are the adapter, the self-attention and the additive attention (n = 3).
- **The metrics** (`jnfinding/metrics.py`) are our own: AUC, MRR and nDCG@5/10 as MIND defines them, tested against hand calculations (`ml/tests/test_metrics.py`).

## Results

Filled in from `ml/finding/results/*.json` and the original code's logs; see `RESULTS.md`.
