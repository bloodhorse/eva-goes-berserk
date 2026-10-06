#!/usr/bin/env bash
cd ~/tower/forge/eva-goes-berserk/school
N=${1:-night1}; B=${BOX:-BekmemetevVO@ds-dev2.x340.org}; D=${BOXDIR:-/opt/llama/magdra}
M=bek@100.69.218.90; A=/srv/music/school-archive/models/$N
O=(-o BatchMode=yes -o ConnectTimeout=8 ${KEY:+-i "$KEY"})
mkdir -p "night/$N"
ssh -o BatchMode=yes -o ConnectTimeout=8 $M "mkdir -p $A" </dev/null
while true; do
  t0=$(date +%s)
  want=$(ssh "${O[@]}" $B "stat -c%s $D/runs/$N/ckpt.pt" </dev/null 2>/dev/null)
  if [ -n "$want" ] && ssh "${O[@]}" $B "cat $D/runs/$N/ckpt.pt" </dev/null 2>> "night/$N/watch.err" | ssh -o BatchMode=yes -o ConnectTimeout=8 $M "cat > $A/ckpt.pt.part" 2>> "night/$N/watch.err"; then
    got=$(ssh -o BatchMode=yes -o ConnectTimeout=8 $M "stat -c%s $A/ckpt.pt.part" </dev/null 2>/dev/null)
    if [ "$got" = "$want" ]; then
      ssh -o BatchMode=yes -o ConnectTimeout=8 $M "mv $A/ckpt.pt.part $A/ckpt.pt" </dev/null
      echo "$(date -u +%FT%TZ) MATCH trainable copy on the mini: $(( got / 1048576 )) MB in $(( $(date +%s) - t0 )) s" >> "night/$N/pull.log"
    else
      echo "$(date -u +%FT%TZ) MISMATCH got ${got:-0} of $want bytes, old copy kept" >> "night/$N/pull.log"
    fi
  else
    echo "$(date -u +%FT%TZ) pull failed" >> "night/$N/pull.log"
  fi
  if grep -q "guard down" "night/$N/guard.log" 2>/dev/null && [ -n "$last" ]; then break; fi
  grep -q "guard down" "night/$N/guard.log" 2>/dev/null && last=1
  sleep "${EVERY:-21600}"
done
