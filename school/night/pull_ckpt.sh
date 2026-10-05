#!/usr/bin/env bash
cd ~/tower/forge/eva-goes-berserk/school
N=${1:-night1}; B=ubuntu@10.4.65.34
mkdir -p "models/$N"
while true; do
  t0=$(date +%s)
  if scp -q -o BatchMode=yes -o ConnectTimeout=8 "${B}:eva-olmo/school/runs/$N/ckpt.pt" "models/$N/ckpt.pt.part" 2>> "night/$N/watch.err"; then
    mv "models/$N/ckpt.pt.part" "models/$N/ckpt.pt"
    echo "$(date -u +%FT%TZ) trainable copy on the mac: $(( $(stat -f%z "models/$N/ckpt.pt") / 1048576 )) MB in $(( $(date +%s) - t0 )) s" >> "night/$N/pull.log"
  else
    echo "$(date -u +%FT%TZ) pull failed" >> "night/$N/pull.log"
  fi
  if grep -q "guard down" "night/$N/guard.log" 2>/dev/null && [ -n "$last" ]; then break; fi
  grep -q "guard down" "night/$N/guard.log" 2>/dev/null && last=1
  sleep 3600
done
