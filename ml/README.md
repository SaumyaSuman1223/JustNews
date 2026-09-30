# ml/

Research code lives here and is **never imported by anything under `apps/`**. The only things that cross into the app are the ONNX files `finding/jnfinding/export.py` writes and the vectors the `user-vectors` job computes from them (CLAUDE.md).

| Path | What |
|---|---|
| `pyproject.toml` | Its own `uv` project (torch, research dependencies), outside the app workspace |
| `finding/reproduce.sh` | Stage 6 Part A: the original FINDING code at a pinned commit, plus `porting.patch` |
| `finding/PORTING-NOTES.md` | Every change made to run it, and where the data comes from |
| `finding/jnfinding/` | Part B: the user tower over the frozen encoder, FINDING's training procedure, our metrics, the ONNX export and the offline replay |
| `finding/results/` | What each run produced |
| `tests/` | Metrics against hand calculations; FINDING's mechanisms; export parity; the replay |
| `data/` | Git-ignored. MIND and Adressa are research-licensed; do not redistribute |
| `export/` | Exported models (`*.onnx` is git-ignored) |

```bash
cd ml && uv sync && uv run pytest -q
./finding/reproduce.sh prepare adressa-1week
./finding/reproduce.sh train adressa-1week NRMS
./finding/reproduce.sh train adressa-1week FindingNRMS
cd finding && uv run --project .. python -m jnfinding.train embed adressa-1week
uv run --project .. python -m jnfinding.train finding adressa-1week
```

Training here replays **simulated** clients. Serving is centralised. Nothing in this directory is, or may be described as, a federated production system.
