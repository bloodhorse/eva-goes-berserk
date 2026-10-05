#!/usr/bin/env bash
cd ~/eva-olmo
export LD_LIBRARY_PATH=$PWD/build/bin:/usr/local/cuda-13.3/lib64
M=llama70/Meta-Llama-3.1-70B.Q4_K_M.gguf
V=$1; D=$2; shift 2; N=${N:-170}
SAMP=(--temp 2.2 --min-p 0.08 --top-k 0 --top-p 1.0 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --repeat-penalty 1.05 --repeat-last-n 512)
O="llama70/hits/$V-$D"; mkdir -p "$O"
for s in "$@"; do
  n=$(basename "$s" .txt); t0=$(date +%s)
  build/bin/llama-completion -m "$M" -ngl 44 -c 4096 -f "$s" -n "$N" --seed 1 --ignore-eos -no-cnv --no-display-prompt "${SAMP[@]}" --control-vector-scaled "cv-llama/$V.gguf:$D" --control-vector-layer-range 19 19 > "$O/$n.txt" 2> "$O/$n.err"
  echo "$n rc=$? $(( $(date +%s) - t0 ))s"
done
echo HITS-DONE
