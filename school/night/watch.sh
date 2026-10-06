#!/usr/bin/env bash
cd ~/tower/forge/eva-goes-berserk/school
N=${1:-night1}; B=${BOX:-BekmemetevVO@ds-dev2.x340.org}; D=${BOXDIR:-/opt/llama/magdra}
O=(-o BatchMode=yes -o ConnectTimeout=8 ${KEY:+-i "$KEY"})
mkdir -p "night/$N" "models/$N"
while true; do
  if ssh "${O[@]}" $B "cat $D/runs/$N/status.json" </dev/null > "night/$N/status.new" 2>/dev/null && [ -s "night/$N/status.new" ]; then
    mv "night/$N/status.new" "night/$N/status.json"
    tr -d '\n' < "night/$N/status.json" >> "night/$N/ledger.jsonl"; echo >> "night/$N/ledger.jsonl"
  fi
  scp -q "${O[@]}" "${B}:$D/runs/$N/samples.jsonl" "night/$N/" 2>/dev/null
  scp -q "${O[@]}" "${B}:$D/runs/$N.guard.log" "night/$N/guard.log" 2>/dev/null
  scp -q "${O[@]}" "${B}:$D/runs/$N.temp" "night/$N/temp" 2>/dev/null
  /opt/homebrew/bin/uv run -q --python 3.12 python night/page.py "$N" > "night/$N/page.md" 2>> "night/$N/watch.err" \
    && /opt/homebrew/bin/pandoc -s "night/$N/page.md" -o "night/$N/school-$N.html" --metadata pagetitle="school $N" -V header-includes='<meta http-equiv="refresh" content="120">' \
    && scp -q -o BatchMode=yes -o ConnectTimeout=8 "night/$N/school-$N.html" bek@100.69.218.90:sheets/ 2>> "night/$N/watch.err"
  f=$(ssh "${O[@]}" $B "ls -t $D/runs/$N/ 2>/dev/null | grep '^model-.*gguf$' | head -1" </dev/null 2>/dev/null)
  if [ -n "$f" ] && [ "$f" != "$(cat "models/$N/latest" 2>/dev/null)" ]; then
    scp -q "${O[@]}" "${B}:$D/runs/$N/$f" "models/$N/model-latest-q8_0.gguf.part" 2>/dev/null \
      && mv "models/$N/model-latest-q8_0.gguf.part" "models/$N/model-latest-q8_0.gguf" && echo "$f" > "models/$N/latest"
  fi
  if grep -q "guard down" "night/$N/guard.log" 2>/dev/null; then break; fi
  sleep 120
done
