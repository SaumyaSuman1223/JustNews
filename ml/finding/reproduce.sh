#!/usr/bin/env bash
# Stage 6 Part A: run the original FINDING code (Yu et al., CIKM '23) on a
# public dataset, with only the porting changes in porting.patch - so the
# numbers are the paper's code's numbers, not ours (ROADMAP §Stage 6).
#
#   ml/finding/reproduce.sh prepare adressa-1week     # once: preprocess
#   ml/finding/reproduce.sh train adressa-1week NRMS  # centralised baseline
#   ml/finding/reproduce.sh train adressa-1week FindingNRMS
#
# The upstream code is not vendored into this repository (it carries no
# licence); it is fetched at a pinned commit into ml/finding/.work, which
# is git-ignored, and patched there. Data lives in ml/data (git-ignored:
# MIND and Adressa are research-licensed and must not be redistributed).
set -euo pipefail

UPSTREAM=https://github.com/yusanshi/FINDING
COMMIT=be9bb78bdcd3273c065c1ab1e96140c3db731e4c

HERE="$(cd "$(dirname "$0")" && pwd)"
ML="$(dirname "$HERE")"
ROOT="$(dirname "$ML")"
WORK="$HERE/.work/FINDING"
DATA="$ML/data/finding"

fetch() {
  if [[ -d "$WORK/fednewsrec" ]]; then return; fi
  mkdir -p "$HERE/.work"
  local source="$ROOT/resources/FINDING"
  if [[ -d "$source/.git" ]] && [[ "$(git -C "$source" rev-parse HEAD)" == "$COMMIT" ]]; then
    rsync -a --exclude .git --exclude homomorphic-encryption "$source/" "$WORK/"
  else
    git clone --quiet "$UPSTREAM" "$HERE/.work/clone"
    git -C "$HERE/.work/clone" checkout --quiet "$COMMIT"
    rsync -a --exclude .git --exclude homomorphic-encryption "$HERE/.work/clone/" "$WORK/"
    rm -rf "$HERE/.work/clone"
  fi
  (cd "$WORK" && patch -p1 --quiet < "$HERE/porting.patch")
  mkdir -p "$DATA/raw"
  ln -sfn "$DATA" "$WORK/data"
}

prepare() {
  local dataset="$1"
  fetch
  case "$dataset" in
    adressa-1week)
      # The README moves one_week/* up a level; a link does the same.
      ln -sfn "$ML/data/raw/adressa-1week/one_week" "$DATA/raw/adressa-1week"
      (cd "$WORK" && uv run --project "$ML" python -m fednewsrec.data_preprocess.adressa \
        --source_dir=./data/raw/adressa-1week --target_dir=./data/adressa-1week)
      ;;
    mind-small)
      # Needs MINDsmall_{train,dev}.zip in ml/data/raw/mind-small and GloVe
      # 840B in ml/data/raw/glove - see PORTING-NOTES.md for where they are.
      local raw="$ML/data/raw/mind-small"
      [[ -d "$raw/train" ]] || unzip -q "$raw/MINDsmall_train.zip" -d "$raw/train"
      [[ -d "$raw/val" ]] || unzip -q "$raw/MINDsmall_dev.zip" -d "$raw/val"
      [[ -d "$raw/test" ]] || cp -r "$raw/val" "$raw/test"
      ln -sfn "$raw" "$DATA/raw/mind-small"
      (cd "$WORK" && uv run --project "$ML" python -m fednewsrec.data_preprocess.mind \
        --source_dir=./data/raw/mind-small --target_dir=./data/mind-small \
        --glove_path="$ML/data/raw/glove/glove.840B.300d.txt")
      ;;
    *) echo "unknown dataset: $dataset" >&2; exit 2 ;;
  esac
}

train() {
  local dataset="$1" model="$2"
  shift 2
  fetch
  mkdir -p "$HERE/results"
  # A run that crashed while writing its dataset cache leaves a lock the
  # next run would wait on forever.
  rm -f "$WORK"/cache/*.lock
  (cd "$WORK" && uv run --project "$ML" python -m fednewsrec.train \
    --dataset "$dataset" --model "$model" "$@") 2>&1 | tee "$HERE/results/$model-$dataset.log"
}

case "${1:-}" in
  prepare) prepare "${2:?dataset}" ;;
  train) train "${2:?dataset}" "${3:?model}" "${@:4}" ;;
  *) echo "usage: $0 prepare DATASET | train DATASET MODEL [args...]" >&2; exit 2 ;;
esac
