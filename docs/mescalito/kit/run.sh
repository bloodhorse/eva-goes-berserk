#!/usr/bin/env bash
# Flags live in an array: the harness shell is zsh, which does not word-split an unquoted $VAR the way bash does, so a string of flags in a variable arrives as one argument and llama-completion writes an empty page.
set -uo pipefail
if [ $# -lt 5 ]; then
  echo "usage: run.sh <out-dir> <seed-file> <vector|sober> <dose> <rng>[,<rng>...] [<tokens>]" >&2
  exit 2
fi
OUT=$1
SEED=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
V=$3
D=$4
RNGS=$5
N=${6:-170}
[ -f "$SEED" ] || { echo "no seed: $SEED" >&2; exit 1; }
cd "$(dirname "$0")/../night2" || exit 1
M=$HOME/.cache/llama.cpp/Mistral-Nemo-Base-2407.Q5_K_M.gguf
CV=../night1/cv-nemo
SAMP=(--temp 2.0 --min-p 0.08 --top-k 0 --top-p 1.0 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --repeat-penalty 1.05 --repeat-last-n 512)
if [ "$V" = sober ]; then
  CVF=()
else
  [ -f "$CV/$V.gguf" ] || { echo "no vector: $CV/$V.gguf" >&2; exit 1; }
  CVF=(--control-vector-scaled "$CV/$V.gguf:$D" --control-vector-layer-range 9 9)
fi
mkdir -p "$OUT"
IFS=, read -ra SEEDS <<< "$RNGS"
for s in "${SEEDS[@]}"; do
  if [ "$V" = sober ]; then o=$OUT/sober__s$s.txt; else o=$OUT/${V}__x${D}__s$s.txt; fi
  [ -s "$o" ] && continue
  llama-completion -m "$M" -ngl 99 -c 2048 -f "$SEED" -n "$N" --seed "$s" -no-cnv --no-display-prompt \
    "${SAMP[@]}" ${CVF[@]+"${CVF[@]}"} > "$o" 2>/dev/null
  echo "$o"
done
