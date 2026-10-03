#!/usr/bin/env bash
set -euo pipefail
cd ~/eva-olmo
PY=.venv/bin/python
NAME=${1:-olmo}
BUDGET=${BUDGET:-512}
S=${S:-10}; T=${T:-20}; SLICE=${SLICE:-0}; L=$((S - 1))
if [ -e "${NAME}_s${S}.pt" ]; then echo "bank exists: ${NAME}_s${S}.pt" >&2; exit 1; fi
used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
if [ "$used" -gt 500 ]; then echo "card busy: ${used} MiB in use" >&2; exit 1; fi

stamp() { while IFS= read -r l; do printf '%s %s\n' "$(date -u +%H:%M:%S)" "$l"; done; }
{
  echo "bank $NAME: start, budget $BUDGET"
  $PY kit/melbo_bank.py --model olmo-hf --seeds seeds/train/*.txt --s "$S" --t "$T" --slice "$SLICE" --m 256 --budget "$BUDGET" --out "${NAME}_s${S}.pt" 2>&1 \
    | tr '\r' '\n' | grep --line-buffered -E '^R=|^iter |rror'
  rm -rf "cv-$NAME"; mkdir -p "cv-$NAME"
  $PY kit/export_cvec.py "${NAME}_s${S}.pt" olmo2 "cv-$NAME"
  R=$($PY -c "import json; print(json.load(open('${NAME}_s${S}.pt.json'))['R'])")
  A=$($PY -c "print($R/5120**0.5)")
  for s in $(seq 0 15); do
    $PY kit/rand_cvec.py "cv-$NAME/rand_$s.gguf" --n-embd 5120 --n-layer 64 --layers "$L-$L" --alpha "$A" --seed "$s"
  done
  echo "BANK-DONE $NAME: R=$R  $(ls "cv-$NAME" | wc -l) vectors"
} 2>&1 | stamp
