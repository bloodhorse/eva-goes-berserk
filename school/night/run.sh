#!/usr/bin/env bash
cd ~/eva-olmo/school
N=${1:-night1}; R=runs/$N
mkdir -p "$R"
PY=~/eva-olmo/.venv-train/bin/python
DATA=(--data bins/fantasy.bin:350 bins/scifi.bin:250 bins/anime.bin:400 bins/picks.bin:6 --out "$R")
SHAPE=(--layers 24 --width 1024 --heads 16 --ctx 1024 --batch 12 --accum 2 --lr 3e-4 --warmup 1000 --hours "${HOURS:-10}" --log-every 50 --eval-every 1000 --ckpt-minutes 20 --prompts prompts.txt --compile)
curl -s -m 10 -H "Title: school: $N started" -H "Priority: low" -H "Tags: hatching_chick" -d "355M from scratch, ${HOURS:-10} h" ntfy.sh/kk_alert > /dev/null
for try in $(seq 1 30); do
  if [ -f "$R/ckpt.pt" ]; then $PY train.py "${DATA[@]}" >> "$R.log" 2>&1; else $PY train.py "${DATA[@]}" "${SHAPE[@]}" >> "$R.log" 2>&1; fi
  if tail -n 5 "$R.log" | grep -q -E 'DONE step=|STOPPED step='; then break; fi
  echo "$(date -u +%FT%TZ) trainer exited without DONE, restart $try" >> "$R.guard.log"
  sleep 30
done
E=$(tail -n 3 "$R.log" | grep -o -E '(DONE|STOPPED) step=[0-9]+ tokens=[0-9,]+ eval_loss=[0-9.]+' | tail -1)
curl -s -m 10 -H "Title: school: $N ended" -H "Priority: low" -H "Tags: checkered_flag" -d "${E:-gave up after 30 restarts}" ntfy.sh/kk_alert > /dev/null
echo "$(date -u +%FT%TZ) wrapper exit: ${E:-gave up}" >> "$R.guard.log"
