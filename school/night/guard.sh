#!/usr/bin/env bash
cd ~/eva-olmo/school
N=${1:-night1}; R=runs/$N
HOT=${HOT:-88}; COOL=${COOL:-75}; FLOOR=${FLOOR:-20}
hot=0; paused=0; last=$(date +%s)
say() { echo "$(date -u +%FT%TZ) $*" >> "$R.guard.log"; }
snap() {
  free=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
  if [ "$free" -lt "$FLOOR" ]; then say "disk ${free}G under ${FLOOR}G, snapshot skipped"; return; fi
  [ -f "$R/ckpt.pt" ] || return
  if nice -n 10 ./export.sh "$R" q8_0 >> "$R.export.log" 2>&1; then say "snapshot $(ls -t "$R"/model-*.gguf | head -1 | xargs basename)"; else say "snapshot failed"; fi
  rm -rf "$R"/hf-*
}
say "guard up: pause at ${HOT}C, resume at ${COOL}C, disk floor ${FLOOR}G"
while true; do
  t=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | head -1)
  pid=$(grep -o "\"pid\": [0-9]*" "$R/status.json" 2>/dev/null | grep -o "[0-9]*$")
  echo "$(date +%s) $t" > "$R.temp"
  if [ "${t:-0}" -ge "$HOT" ]; then hot=$((hot + 1)); else hot=0; fi
  if [ "$paused" = 0 ] && [ "$hot" -ge 3 ] && [ -n "$pid" ]; then kill -STOP "$pid" && paused=1 && say "paused at ${t}C"; fi
  if [ "$paused" = 1 ] && [ "${t:-99}" -le "$COOL" ] && [ -n "$pid" ]; then kill -CONT "$pid" && paused=0 && hot=0 && say "resumed at ${t}C"; fi
  now=$(date +%s)
  if [ $((now - last)) -ge 3600 ]; then last=$now; snap; fi
  if [ -f "$R.guard.log" ] && grep -q "wrapper exit" "$R.guard.log"; then snap; say "guard down"; break; fi
  sleep 60
done
