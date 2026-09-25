#!/usr/bin/env bash
# baseline.sh: the sober baseline for the ladder — the storm-girl seed, the ladder's sampler
# and length (170 tokens), no vector, forty draws (RNG seeds 1–40). A model reads them with the
# instructions in docs/mescalito/stars.md and stars-fable.md; bekh reads none. Pages:
# night2/baseline/s<seed>.txt, skipped if they exist.
set -uo pipefail
cd "$(dirname "$0")/../night2" || exit 1
mkdir -p baseline
M=$HOME/.cache/llama.cpp/Mistral-Nemo-Base-2407.Q5_K_M.gguf
SAMP="--temp 2.0 --min-p 0.08 --top-k 0 --top-p 1.0 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --repeat-penalty 1.05 --repeat-last-n 512"
S=../../olmo-seeds/2026-09-21-1650.txt
for s in $(seq 1 40); do
  o=baseline/s$s.txt
  [ -s "$o" ] || llama-completion -m "$M" -ngl 99 -c 2048 -f "$S" -n 170 --seed $s -no-cnv --no-display-prompt $SAMP > "$o" 2>/dev/null
done
echo done > baseline/.done
