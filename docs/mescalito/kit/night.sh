#!/usr/bin/env bash
# night.sh: one mescalito night on the pod, stage by stage. A stage is skipped once done/<stage>
# exists, so a crash is a rerun of one stage, never a restart of the night. Runs from ~ on the
# pod: the kit is ~/kit, the bank learns on ~/seeds/train and is judged on ~/seeds/read (never the
# same files). Every stage logs to log/<stage>.log; `ls done` is the progress.
#
#   night.sh setup nemo-dl olmo-dl nemo-gguf nemo-bank nemo-kill nemo-verdict olmo-bank olmo-kill olmo-verdict ship
#   night.sh all        # the lot in order, olmo's downloads in the background from the start
#
# Shape of a model's half: learn a bank of 256 directions the model owns (melbo_bank), export
# each as a control vector plus sixteen random ones of the same norm, write one 60-token page per
# vector on the willows seed (the kill screen), let screen.py declare the dead by surface stats and
# draw 12 living owned + 12 living random by lot, then write the verdict pages: those 24 on both
# read seeds at 170 tokens, plus one clean page per seed, shuffled blind by blind.py.
set -euo pipefail
export LD_LIBRARY_PATH=/app PATH=/app:$HOME/.local/bin:$PATH
cd ~
PY=$HOME/.venv/bin/python
mkdir -p done log
export SAMP_NEMO="--temp 2.0 --min-p 0.08 --top-k 0 --top-p 1.0 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --repeat-penalty 1.05 --repeat-last-n 512"
export SAMP_OLMO="--temp 3.0 --min-p 0.08 --top-k 0 --top-p 1.0 --xtc-probability 0.5 --xtc-threshold 0.1 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --repeat-penalty 1.05 --repeat-last-n 512"

ntfy() { curl -s -H "Title: mescalito" -H "Tags: test_tube" -d "$1" ntfy.sh/kk_alert >/dev/null || true; }

# page MODEL SEED NTOK VECTOR|"" SAMPLER OUT — one llama-completion page, the vector on layer 9
page() {
  local m=$1 seed=$2 n=$3 vec=$4 samp=$5 out=$6 cv=()
  [ -n "$vec" ] && cv=(--control-vector-scaled "$vec:1.0" --control-vector-layer-range 9 9)
  llama-completion -m "$m" -ngl 99 -c 2048 -f "$seed" -n "$n" --seed 1 -no-cnv --no-display-prompt \
    $samp "${cv[@]}" > "$out" 2> "${out%.txt}.err" && rm -f "${out%.txt}.err"
}
export -f page

stage() {
  local s=$1
  if [ -e "done/$s" ]; then echo "== $s: done already"; return; fi
  echo "== $s: start $(date -u +%H:%M:%S)"
  if "st_$s" 2>&1 | tee "log/$s.log"; then
    touch "done/$s"; echo "== $s: finished $(date -u +%H:%M:%S)"
  else
    ntfy "$s FAILED — see log/$s.log"; echo "== $s: FAILED"; exit 1
  fi
}

st_setup() {
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
  ls /app/llama-completion /app/llama-quantize /app/convert_hf_to_gguf.py
  command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; }
  [ -x "$PY" ] || uv venv --python 3.12 ~/.venv
  uv pip install -q --python "$PY" torch transformers accelerate gguf numpy "huggingface_hub[cli]"
  "$PY" -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
  # the converter needs torch too; the image's python may or may not have it
  if python3 -c "import torch, gguf" 2>/dev/null; then echo "converter: image python"; else echo "converter: venv python"; fi
  ls seeds/train/*.txt seeds/read/*.txt
}

st_nemo-dl() {
  ~/.venv/bin/hf download mistralai/Mistral-Nemo-Base-2407 --exclude "consolidated*" --local-dir nemo-hf
  du -sh nemo-hf
}

st_olmo-dl() {
  ~/.venv/bin/hf download Tricit/Olmo-3-1125-32B-stage1-step656000-Q4_K_M-GGUF --local-dir olmo-q4
  ~/.venv/bin/hf download allenai/Olmo-3-1125-32B --revision stage1-step656000 --local-dir olmo-hf
  du -sh olmo-q4 olmo-hf
}

st_nemo-gguf() {
  local conv=python3; python3 -c "import torch, gguf" 2>/dev/null || conv=$PY
  [ -s nemo-q4km.gguf ] || {
    $conv /app/convert_hf_to_gguf.py nemo-hf --outtype bf16 --outfile nemo-bf16.gguf
    llama-quantize nemo-bf16.gguf nemo-q4km.gguf Q4_K_M
    rm -f nemo-bf16.gguf
  }
  ls -la nemo-q4km.gguf
}

# bank NAME MODELDIR HINT NLAYER — learn, export, and cut the sixteen random controls of the same norm
bank() {
  local name=$1 model=$2 hint=$3 nlayer=$4
  "$PY" kit/melbo_bank.py --model "$model" --seeds seeds/train/*.txt --s 10 --t 20 --m 256 --out "${name}_s10.pt"
  rm -rf "cv-$name"; mkdir -p "cv-$name"
  "$PY" kit/export_cvec.py "${name}_s10.pt" "$hint" "cv-$name"
  local R A; R=$("$PY" -c "import json; print(json.load(open('${name}_s10.pt.json'))['R'])")
  A=$("$PY" -c "print($R/5120**0.5)")
  for s in $(seq 0 15); do
    "$PY" kit/rand_cvec.py "cv-$name/rand_$s.gguf" --n-embd 5120 --n-layer "$nlayer" --layers 9-9 --alpha "$A" --seed "$s"
  done
  echo "bank $name: R=$R  $(ls cv-$name | wc -l) vectors"
}
st_nemo-bank() { bank nemo nemo-hf llama 40; }
st_olmo-bank() {
  while [ ! -e done/olmo-dl ]; do echo "waiting for olmo-dl…"; sleep 60; done
  bank olmo olmo-hf olmo2 64
}

# kill NAME GGUF PAR SAMPLER — one 60-token page per vector on the willows seed, PAR at a time, then the lot
kill_screen() {
  local name=$1 gguf=$2 par=$3 samp=$4
  mkdir -p "kill/$name"
  ls "cv-$name"/*.gguf | xargs -P "$par" -I{} bash -c \
    'v=$1; o=kill/'"$name"'/$(basename "$v" .gguf).txt; [ -s "$o" ] || page '"$gguf"' seeds/read/willows-last.txt 60 "$v" "$SAMP" "$o"' _ {}
  "$PY" kit/screen.py "kill/$name" --n 12 --out "picks-$name.json"
}
st_nemo-kill() { SAMP=$SAMP_NEMO kill_screen nemo nemo-q4km.gguf 4 "$SAMP_NEMO"; }
st_olmo-kill() { SAMP=$SAMP_OLMO kill_screen olmo "$(ls olmo-q4/*.gguf)" 2 "$SAMP_OLMO"; }

# verdict NAME GGUF PAR — the 24 picked vectors on both read seeds at 170 tokens, plus a clean page per seed
verdict() {
  local name=$1 gguf=$2 par=$3
  mkdir -p "out/$name"
  "$PY" - "$name" > "out/$name/jobs.txt" <<'EOF'
import json, sys, glob
name = sys.argv[1]
picks = json.load(open(f"picks-{name}.json"))["picks"]
vecs = [(v, f"cv-{name}/{v}.gguf") for pile in picks.values() for v in pile] + [("clean", "-")]   # "-": no vector (xargs drops an empty field)
for seed in sorted(glob.glob("seeds/read/*.txt")):
    s = seed.split("/")[-1][:-4]
    for v, path in vecs:
        print(f"{seed}\t{path}\tout/{name}/{v}__{s}.txt")
EOF
  xargs -P "$par" -L1 bash -c 'seed=$1; v=$2; o=$3; [ "$v" = - ] && v=""; [ -s "$o" ] || page '"$gguf"' "$seed" 170 "$v" "$SAMP" "$o"' _ < "out/$name/jobs.txt"
  "$PY" - "$name" <<'EOF'
import json, sys, glob, os
name = sys.argv[1]
with open(f"out/{name}/raw.jsonl", "w") as f:
    for p in sorted(glob.glob(f"out/{name}/*__*.txt")):
        cond, s = os.path.basename(p)[:-4].split("__")
        f.write(json.dumps({"cond": cond, "seed": os.path.abspath(f"seeds/read/{s}.txt"), "text": open(p, errors="replace").read()}) + "\n")
EOF
  (cd "out/$name" && "$PY" ../../kit/pages.py "mescalito · $name · $(date -u +%Y-%m-%d)")
  ntfy "$name: pages ready ($(wc -l < out/$name/raw.jsonl))"
}
st_nemo-verdict() { SAMP=$SAMP_NEMO verdict nemo nemo-q4km.gguf 4; }
st_olmo-verdict() { SAMP=$SAMP_OLMO verdict olmo "$(ls olmo-q4/*.gguf)" 2; }

st_ship() {
  tar czf night.tgz ./*_s10.pt ./*_s10.pt.json cv-nemo cv-olmo kill picks-*.json out log done
  ls -la night.tgz
  ntfy "night shipped: night.tgz ready to pull"
}

if [ "${1:-}" = all ]; then
  stage setup
  ( stage olmo-dl ) > log/olmo-dl.bg 2>&1 &
  for s in nemo-dl nemo-gguf nemo-bank nemo-kill nemo-verdict olmo-bank olmo-kill olmo-verdict ship; do stage "$s"; done
else
  for s in "$@"; do stage "$s"; done
fi
