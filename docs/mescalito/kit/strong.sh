#!/usr/bin/env bash
# strong.sh: the strong end of the bank at low dose. ranks 000–039 on the storm-girl, one draw
# (RNG seed 1), at the dose given ($1, default 0.25). Skips pages that exist. Pulse: status.json.
set -uo pipefail
cd "$(dirname "$0")/../night1" || exit 1
D=${1:-0.25}
M=$HOME/.cache/llama.cpp/Mistral-Nemo-Base-2407.Q5_K_M.gguf
SAMP="--temp 2.0 --min-p 0.08 --top-k 0 --top-p 1.0 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --repeat-penalty 1.05 --repeat-last-n 512"
S=../../olmo-seeds/2026-09-21-1650.txt
mkdir -p strong; n=0; START=$(date +%s)
for f in $(ls cv-nemo/0[0-3][0-9]_*.gguf); do v=$(basename $f .gguf); n=$((n+1))
  printf '{"stage":"strong x%s","seed":"storm-girl","vector":"%s","done":%d,"total":40,"elapsed":%d}\n' "$D" "$v" "$n" "$(( $(date +%s) - START ))" > status.json
  o=strong/2026-09-21-1650__${v}__x$D.txt
  [ -s "$o" ] || llama-completion -m "$M" -ngl 99 -c 2048 -f "$S" -n 170 --seed 1 -no-cnv --no-display-prompt $SAMP \
    --control-vector-scaled "$f:$D" --control-vector-layer-range 9 9 > "$o" 2>/dev/null
done
curl -s -H "Title: mescalito" -d "strong end at x$D done (40)" ntfy.sh/kk_alert >/dev/null
