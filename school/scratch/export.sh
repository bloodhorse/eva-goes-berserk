#!/usr/bin/env bash
set -e
RUN=${1:?usage: export.sh RUN_DIR [f16|q8_0|bf16|f32]}
TYPE=${2:-f16}
SCHOOL=$(cd "$(dirname "$0")" && pwd)
PY=${PY:-$SCHOOL/.venv/bin/python}
export PYTHONDONTWRITEBYTECODE=1
HF=$($PY "$SCHOOL/export_hf.py" "$RUN/ckpt.pt" "$RUN" | tail -1)
STEP=${HF##*hf-}
$PY /opt/llama/src/llama.cpp/convert_hf_to_gguf.py "$HF" --outtype "$TYPE" --outfile "$RUN/model-$STEP-$TYPE.gguf"
ls -la "$RUN/model-$STEP-$TYPE.gguf"
