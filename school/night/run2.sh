#!/usr/bin/env bash
cd ~/eva-olmo/school
N=${1:-night1}; R=runs/$N
mkdir -p "$R"
PY=~/eva-olmo/.venv-train/bin/python
DATA=(--data bins/fantasy.bin:2000 bins/scifi.bin:1500 bins/anime.bin:2100 bins/fanfic.bin:1400 bins/base.bin:2200 bins/wired-core.bin:200 bins/wired-bulk.bin:400 bins/picks.bin:50 bins/cyborg.bin:10 bins/lain.bin:25 --out "$R")
SHAPE=(--init runs/day2/ckpt-from-lr2e-4.pt --batch 12 --accum 2 --lr 8e-5 --warmup 300 --hours "${HOURS:-12}" --log-every 50 --eval-every 1000 --ckpt-minutes 20 --prompts prompts.txt --compile)
curl -s -m 10 -H "Title: school: $N started" -H "Priority: low" -H "Tags: hatching_chick" -d "magdra, warm start from night1, ${HOURS:-12} h" ntfy.sh/kk_alert > /dev/null
for try in $(seq 1 30); do
  if [ -f "$R/ckpt.pt" ]; then $PY train.py "${DATA[@]}" >> "$R.log" 2>&1; else $PY train.py "${DATA[@]}" "${SHAPE[@]}" >> "$R.log" 2>&1; fi
  if tail -n 5 "$R.log" | grep -q -E 'DONE step=|STOPPED step='; then break; fi
  echo "$(date -u +%FT%TZ) trainer exited without DONE, restart $try" >> "$R.guard.log"
  sleep 30
done
E=$(tail -n 3 "$R.log" | grep -o -E '(DONE|STOPPED) step=[0-9]+ tokens=[0-9,]+ eval_loss=[0-9.]+' | tail -1)
curl -s -m 10 -H "Title: school: $N ended" -H "Priority: low" -H "Tags: checkered_flag" -d "${E:-gave up after 30 restarts}" ntfy.sh/kk_alert > /dev/null
echo "$(date -u +%FT%TZ) wrapper exit: ${E:-gave up}" >> "$R.guard.log"
