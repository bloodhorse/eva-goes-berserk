#!/usr/bin/env bash
# scott.sh: the good directions on a new seed — Scott's last diary (shelf/seeds/short/03), the
# real March 1912 entry, cut at "foot went and I didn't". god 012_f232, 005_f53, 013_f60 (bekh's
# stars on the ladder) and ender 224_f112, kin 125_f146, voices 169_f199 (night 1's compounds),
# at 0.25 and 0.4, three draws each (RNG seeds 1–3), 170 tokens, the ladder's sampler; three
# sober. The question: does each direction bring its subject onto a seed that has nothing for it.
# Pages: night2/scott/<vector>__x<dose>__s<seed>.txt and sober__s<seed>.txt; skipped if they exist.
set -uo pipefail
cd "$(dirname "$0")/../night2" || exit 1
mkdir -p scott
M=$HOME/.cache/llama.cpp/Mistral-Nemo-Base-2407.Q5_K_M.gguf
SAMP="--temp 2.0 --min-p 0.08 --top-k 0 --top-p 1.0 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --repeat-penalty 1.05 --repeat-last-n 512"
S=../../../shelf/seeds/short/03-scotts-diary.txt
CV=../night1/cv-nemo
for s in 1 2 3; do
  o=scott/sober__s$s.txt
  [ -s "$o" ] || llama-completion -m "$M" -ngl 99 -c 2048 -f "$S" -n 170 --seed $s -no-cnv --no-display-prompt $SAMP > "$o" 2>/dev/null
done
for v in 012_f232 005_f53 013_f60 224_f112 125_f146 169_f199; do for D in 0.25 0.4; do for s in 1 2 3; do
  o=scott/${v}__x${D}__s$s.txt
  [ -s "$o" ] || llama-completion -m "$M" -ngl 99 -c 2048 -f "$S" -n 170 --seed $s -no-cnv --no-display-prompt $SAMP \
    --control-vector-scaled "$CV/$v.gguf:$D" --control-vector-layer-range 9 9 > "$o" 2>/dev/null
done; done; done
echo done > scott/.done
curl -s -H "Title: mescalito" -d "scott done: 6 directions x 2 doses x 3 draws + 3 sober" ntfy.sh/kk_alert >/dev/null
