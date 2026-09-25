#!/usr/bin/env bash
# bloodbath.sh: road 1 of the bloodbath question (pharmacopoeia) — the four bank directions the
# lottery flagged dark on the storm girl, 158_f246 060_f6 046_f175 061_f20, on a seed with no
# blood in it. Cut corners on 2026-09-26: one seed (the asses), one dose (0.75, where they held
# in the lottery), three draws (RNG seeds 1–3), 170 tokens, the ladder's sampler, no sober — the sober pages are the seed's, already on the shelf (bekh, 2026-09-26).
# Usage: bloodbath.sh <seed-file> — pages go to night2/bloodbath/<seed-name>/; skipped if they exist.
# 2026-09-26: run on the asses (0 of 12 blood), then on scott.
set -uo pipefail
cd "$(dirname "$0")/../night2" || exit 1
N=$(basename "$1" .txt); N=${N#03-}; N=${N%-diary}
mkdir -p bloodbath/$N
M=$HOME/.cache/llama.cpp/Mistral-Nemo-Base-2407.Q5_K_M.gguf
SAMP="--temp 2.0 --min-p 0.08 --top-k 0 --top-p 1.0 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --repeat-penalty 1.05 --repeat-last-n 512"
S=$1
CV=../night1/cv-nemo
for v in 158_f246 060_f6 046_f175 061_f20; do for s in 1 2 3; do
  o=bloodbath/$N/${v}__x0.75__s$s.txt
  [ -s "$o" ] || llama-completion -m "$M" -ngl 99 -c 2048 -f "$S" -n 170 --seed $s -no-cnv --no-display-prompt $SAMP \
    --control-vector-scaled "$CV/$v.gguf:0.75" --control-vector-layer-range 9 9 > "$o" 2>/dev/null
done; done
echo done > bloodbath/$N/.done
