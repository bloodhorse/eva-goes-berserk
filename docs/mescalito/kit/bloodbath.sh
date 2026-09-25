#!/usr/bin/env bash
# bloodbath.sh: road 1 of the bloodbath question (pharmacopoeia) — the four bank directions the
# lottery flagged dark on the storm girl, 158_f246 060_f6 046_f175 061_f20, on a seed with no
# blood in it. Cut corners on 2026-09-26: one seed (the asses), one dose (0.75, where they held
# in the lottery), three draws (RNG seeds 1–3), 170 tokens, the ladder's sampler, three sober.
# Pages: night2/bloodbath/<vector>__x0.75__s<seed>.txt and sober__s<seed>.txt; skipped if they exist.
set -uo pipefail
cd "$(dirname "$0")/../night2" || exit 1
mkdir -p bloodbath
M=$HOME/.cache/llama.cpp/Mistral-Nemo-Base-2407.Q5_K_M.gguf
SAMP="--temp 2.0 --min-p 0.08 --top-k 0 --top-p 1.0 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --repeat-penalty 1.05 --repeat-last-n 512"
S=../../../shelf/seeds/asses.txt
CV=../night1/cv-nemo
for s in 1 2 3; do
  o=bloodbath/sober__s$s.txt
  [ -s "$o" ] || llama-completion -m "$M" -ngl 99 -c 2048 -f "$S" -n 170 --seed $s -no-cnv --no-display-prompt $SAMP > "$o" 2>/dev/null
done
for v in 158_f246 060_f6 046_f175 061_f20; do for s in 1 2 3; do
  o=bloodbath/${v}__x0.75__s$s.txt
  [ -s "$o" ] || llama-completion -m "$M" -ngl 99 -c 2048 -f "$S" -n 170 --seed $s -no-cnv --no-display-prompt $SAMP \
    --control-vector-scaled "$CV/$v.gguf:0.75" --control-vector-layer-range 9 9 > "$o" 2>/dev/null
done; done
echo done > bloodbath/.done
