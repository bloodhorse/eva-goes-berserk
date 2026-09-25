#!/usr/bin/env bash
# god.sh: does the god direction (012_f232) fill a slot with god? bekh's asses seed, cut at
# "were created by": f232 at 0.25 / 0.4 / 0.5 / 0.6 / 0.7, sober, and 000_f37 at 0.5 as the
# any-drug control; three draws each (RNG seeds 1–3), 20 tokens, the ladder's sampler.
# Pages: night2/god/<cond>__s<seed>.txt. Skipped if they exist.
set -uo pipefail
cd "$(dirname "$0")/../night2" || exit 1
mkdir -p god
M=$HOME/.cache/llama.cpp/Mistral-Nemo-Base-2407.Q5_K_M.gguf
SAMP="--temp 2.0 --min-p 0.08 --top-k 0 --top-p 1.0 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --repeat-penalty 1.05 --repeat-last-n 512"
S=../../../shelf/seeds/asses.txt
CV=../night1/cv-nemo
run() { # cond vector dose
  local c=$1 v=$2 d=$3 s o
  for s in 1 2 3; do
    o=god/${c}__s$s.txt
    [ -s "$o" ] && continue
    if [ -z "$v" ]; then
      llama-completion -m "$M" -ngl 99 -c 2048 -f "$S" -n 20 --seed $s -no-cnv --no-display-prompt $SAMP > "$o" 2>/dev/null
    else
      llama-completion -m "$M" -ngl 99 -c 2048 -f "$S" -n 20 --seed $s -no-cnv --no-display-prompt $SAMP \
        --control-vector-scaled "$CV/$v.gguf:$d" --control-vector-layer-range 9 9 > "$o" 2>/dev/null
    fi
  done
}
run sober "" 0
for D in 0.25 0.4 0.5 0.6 0.7; do run f232_x$D 012_f232 $D; done
run f37_x0.5 000_f37 0.5
echo done > god/.done
