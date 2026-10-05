#!/usr/bin/env bash
cd ~/tower/forge/eva-goes-berserk/school
N=${1:-night1}; B=ubuntu@10.4.65.34
O=(-o BatchMode=yes -o ConnectTimeout=8)
mkdir -p "night/$N" "models/$N"
while true; do
  if ssh "${O[@]}" $B "cat ~/eva-olmo/school/runs/$N/status.json" </dev/null > "night/$N/status.new" 2>/dev/null && [ -s "night/$N/status.new" ]; then
    mv "night/$N/status.new" "night/$N/status.json"
    tr -d '\n' < "night/$N/status.json" >> "night/$N/ledger.jsonl"; echo >> "night/$N/ledger.jsonl"
  fi
  scp -q "${O[@]}" "${B}:eva-olmo/school/runs/$N/samples.jsonl" "night/$N/" 2>/dev/null
  scp -q "${O[@]}" "${B}:eva-olmo/school/runs/$N.guard.log" "night/$N/guard.log" 2>/dev/null
  scp -q "${O[@]}" "${B}:eva-olmo/school/runs/$N.temp" "night/$N/temp" 2>/dev/null
  /opt/homebrew/bin/uv run -q --python 3.12 python night/page.py "$N" > "night/$N/page.md" 2>> "night/$N/watch.err" \
    && /opt/homebrew/bin/pandoc -s "night/$N/page.md" -o "night/$N/school-$N.html" --metadata pagetitle="school $N" -V header-includes='<meta http-equiv="refresh" content="120">' \
    && scp -q -o BatchMode=yes -o ConnectTimeout=8 "night/$N/school-$N.html" bek@100.69.218.90:sheets/ 2>> "night/$N/watch.err"
  for f in $(ssh "${O[@]}" $B "ls ~/eva-olmo/school/runs/$N/ 2>/dev/null | grep '^model-.*gguf$'" </dev/null 2>/dev/null); do
    [ -f "models/$N/$f" ] || { scp -q "${O[@]}" "${B}:eva-olmo/school/runs/$N/$f" "models/$N/$f.part" 2>/dev/null && mv "models/$N/$f.part" "models/$N/$f"; }
  done
  if grep -q "guard down" "night/$N/guard.log" 2>/dev/null; then break; fi
  sleep 120
done
