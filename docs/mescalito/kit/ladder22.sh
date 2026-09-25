#!/usr/bin/env bash
# ladder22.sh: the 22 strong directions that cooked at 0.75 (ranks 000–015, 017–021, 034), up
# the ladder on the storm-girl at 0.2 / 0.3 / 0.5 / 0.6 / 0.7 (0.25 and 0.4 already exist), one
# draw (RNG seed 1). Pages skipped if they exist. Pulse: status.json.
set -uo pipefail
cd "$(dirname "$0")/../night1" || exit 1
M=$HOME/.cache/llama.cpp/Mistral-Nemo-Base-2407.Q5_K_M.gguf
SAMP="--temp 2.0 --min-p 0.08 --top-k 0 --top-p 1.0 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --repeat-penalty 1.05 --repeat-last-n 512"
S=../../olmo-seeds/2026-09-21-1650.txt
V=$(ls cv-nemo/*.gguf | grep -E '^cv-nemo/(00[0-9]|01[0-5]|01[7-9]|02[01]|034)_' )
n=0; START=$(date +%s)
for D in 0.2 0.3 0.5 0.6 0.7; do for f in $V; do v=$(basename $f .gguf); n=$((n+1))
  printf '{"stage":"ladder22 x%s","seed":"storm-girl","vector":"%s","done":%d,"total":110,"elapsed":%d}\n' "$D" "$v" "$n" "$(( $(date +%s) - START ))" > status.json
  o=strong/2026-09-21-1650__${v}__x$D.txt
  [ -s "$o" ] || llama-completion -m "$M" -ngl 99 -c 2048 -f "$S" -n 170 --seed 1 -no-cnv --no-display-prompt $SAMP \
    --control-vector-scaled "$f:$D" --control-vector-layer-range 9 9 > "$o" 2>/dev/null
done; done
curl -s -H "Title: mescalito" -d "ladder22 done: 22 directions x 5 rungs" ntfy.sh/kk_alert >/dev/null
