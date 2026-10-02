#!/usr/bin/env bash
set -uo pipefail
if [ $# -lt 5 ]; then
  echo "usage: box_pages.sh <out-dir> <seed-file> <dose>[,<dose>...] <rng>[,<rng>...] <vector> [<vector>...]" >&2
  exit 2
fi
cd ~/eva-olmo
OUT=$1; SEED=$2; DOSES=$3; RNGS=$4; shift 4
N=${N:-170}
BANK=${BANK:-cv-olmo}
M=$(ls olmo-q4/*.gguf)
export LD_LIBRARY_PATH=$PWD/build/bin:/usr/local/cuda-13.3/lib64
SAMP=(--temp 3.0 --min-p 0.08 --top-k 0 --top-p 1.0 --xtc-probability 0.5 --xtc-threshold 0.1 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --repeat-penalty 1.05 --repeat-last-n 512)
[ -f "$SEED" ] || { echo "no seed: $SEED" >&2; exit 1; }
mkdir -p "$OUT"
IFS=, read -ra DS <<< "$DOSES"
IFS=, read -ra RS <<< "$RNGS"
total=$(( $# * ${#DS[@]} * ${#RS[@]} )); done_n=0
for V in "$@"; do
  f=$(ls "$BANK"/"$V"*.gguf 2>/dev/null | head -1)
  [ -n "$f" ] || { echo "no vector: $BANK/$V" >&2; exit 1; }
  name=$(basename "$f" .gguf)
  for D in "${DS[@]}"; do
    for s in "${RS[@]}"; do
      o=$OUT/${name}__x${D}__s$s.txt
      done_n=$((done_n + 1))
      if [ ! -s "$o" ]; then
        build/bin/llama-completion -m "$M" -ngl 99 -c 2048 -f "$SEED" -n "$N" --seed "$s" -no-cnv --no-display-prompt \
          "${SAMP[@]}" --control-vector-scaled "$f:$D" --control-vector-layer-range 9 9 > "$o" 2> "${o%.txt}.err" && rm -f "${o%.txt}.err"
      fi
      echo "$(date -u +%H:%M:%S) $done_n/$total $o"
    done
  done
done
echo "PAGES-DONE $OUT $total"
