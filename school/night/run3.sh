#!/usr/bin/env bash
cd "${SCHOOL:-/opt/llama/magdra}"
N=${1:-day3}; R=runs/$N
mkdir -p "$R"
PY=${PY:-$PWD/.venv/bin/python}
MIX=${MIX:-"bins2/fantasy.bin:2000 bins2/scifi.bin:1500 bins/anime.bin:2100 bins/fanfic.bin:1400 bins2/base.bin:1550 bins/wired-core.bin:160 bins/wired-bulk.bin:400 bins2/literary.bin:620 bins2/horizons.bin:135 bins2/released.bin:80 bins2/library.bin:72 bins/lain.bin:20 bins/cyborg.bin:4 bins2/horizons-verse.bin:12"}
HOURS=${HOURS:-50}
DATA=(--data $MIX --out "$R")
SHAPE=(--init "${INIT:-ckpt-7896.pt}" --batch 6 --accum 4 --lr 8e-5 --warmup 300 --hours "$HOURS" --log-every 50 --eval-every 1000 --ckpt-minutes 20 --prompts prompts.txt --compile)
curl -s -m 10 -H "Title: school: $N started" -H "Priority: low" -H "Tags: hatching_chick" -d "magdra, warm start from ${INIT:-ckpt-7896.pt}, ${HOURS} h" ntfy.sh/kk_alert > /dev/null
for try in $(seq 1 30); do
  if [ -f "$R/ckpt.pt" ]; then $PY train.py "${DATA[@]}" >> "$R.log" 2>&1; else $PY train.py "${DATA[@]}" "${SHAPE[@]}" >> "$R.log" 2>&1; fi
  if tail -n 5 "$R.log" | grep -q -E 'DONE step=|STOPPED step='; then break; fi
  echo "$(date -u +%FT%TZ) trainer exited without DONE, restart $try" >> "$R.guard.log"
  sleep 30
done
E=$(tail -n 3 "$R.log" | grep -o -E '(DONE|STOPPED) step=[0-9]+ tokens=[0-9,]+ eval_loss=[0-9.]+' | tail -1)
curl -s -m 10 -H "Title: school: $N ended" -H "Priority: low" -H "Tags: checkered_flag" -d "${E:-gave up after 30 restarts}" ntfy.sh/kk_alert > /dev/null
echo "$(date -u +%FT%TZ) wrapper exit: ${E:-gave up}" >> "$R.guard.log"
