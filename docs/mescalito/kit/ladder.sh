#!/usr/bin/env bash
# ladder.sh: five strong directions up the dose ladder on the storm-girl, one draw each.
# waits for the 0.4 pass (tmux 'strong4') to finish first. pages skipped if they exist.
set -uo pipefail
cd "$(dirname "$0")/../night1" || exit 1
while tmux has-session -t strong4 2>/dev/null; do sleep 15; done
M=$HOME/.cache/llama.cpp/Mistral-Nemo-Base-2407.Q5_K_M.gguf
SAMP="--temp 2.0 --min-p 0.08 --top-k 0 --top-p 1.0 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --repeat-penalty 1.05 --repeat-last-n 512"
S=../../olmo-seeds/2026-09-21-1650.txt
n=0; START=$(date +%s)
for D in 0.5 0.6; do for v in 016_f201 036_f23 027_f66 015_f230 023_f26; do n=$((n+1))
  printf '{"stage":"ladder x%s","seed":"storm-girl","vector":"%s","done":%d,"total":10,"elapsed":%d}\n' "$D" "$v" "$n" "$(( $(date +%s) - START ))" > status.json
  o=strong/2026-09-21-1650__${v}__x$D.txt
  [ -s "$o" ] || llama-completion -m "$M" -ngl 99 -c 2048 -f "$S" -n 170 --seed 1 -no-cnv --no-display-prompt $SAMP \
    --control-vector-scaled "cv-nemo/$v.gguf:$D" --control-vector-layer-range 9 9 > "$o" 2>/dev/null
done; done
curl -s -H "Title: mescalito" -d "ladder done: five directions at 0.5 / 0.6" ntfy.sh/kk_alert >/dev/null
