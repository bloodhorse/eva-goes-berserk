#!/usr/bin/env bash
cd ~/eva-olmo
export LD_LIBRARY_PATH=$PWD/build/bin:/usr/local/cuda-13.3/lib64
M=llama70/Meta-Llama-3.1-70B.Q4_K_M.gguf
SEED=${SEED:-llama70/seeds/23-1330.txt}; N=${N:-80}
SAMP=(--temp 2.2 --min-p 0.08 --top-k 0 --top-p 1.0 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --repeat-penalty 1.05 --repeat-last-n 512)
V=$1; shift
mkdir -p "llama70/ladder/$V"
for d in "$@"; do
  CV=(); [ "$d" != 0 ] && CV=(--control-vector-scaled "cv-llama/$V.gguf:$d" --control-vector-layer-range 19 19)
  t0=$(date +%s)
  build/bin/llama-completion -m "$M" -ngl 44 -c 4096 -f "$SEED" -n "$N" --seed 1 --ignore-eos -no-cnv --no-display-prompt "${SAMP[@]}" "${CV[@]}" > "llama70/ladder/$V/$d.txt" 2> "llama70/ladder/$V/$d.err"
  echo "$V $d rc=$? $(( $(date +%s) - t0 ))s"
done
echo "LADDER-DONE $V"
