#!/usr/bin/env bash
set -uo pipefail
cd ~/eva-olmo
PIDF=log/serve.pid
WHOF=log/serve.who
alive() { [ -s "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; }
who() { cat "$WHOF" 2>/dev/null || echo olmo; }
port_of() { case "$1" in nemo) echo 8082 ;; *) echo 8081 ;; esac; }
gguf_of() { case "$1" in nemo) ls nemo/*.gguf ;; *) ls olmo-q4/*.gguf ;; esac; }
health() { curl -s -m 3 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$(port_of "$1")/health"; }
down() { if alive; then kill "$(cat "$PIDF")"; echo "DOWN $(who)"; else echo "not running"; fi; rm -f "$PIDF" "$WHOF"; }

case "${1:-status}" in
  up)
    M=${2:-olmo}
    case "$M" in olmo|nemo) ;; *) echo "no such model: $M (olmo|nemo)" >&2; exit 2 ;; esac
    if alive; then
      if [ "$(who)" = "$M" ]; then echo "already up: $M pid $(cat "$PIDF"), health $(health "$M")"; exit 0; fi
      down; sleep 2
    fi
    sudo bash /opt/llama/scripts/set-model.sh stop >/dev/null 2>&1
    used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
    if [ "$used" -gt 500 ]; then echo "card busy: ${used} MiB in use" >&2; exit 1; fi
    LD_LIBRARY_PATH=/opt/llama/lib:/usr/local/cuda-13.3/lib64 nohup /opt/llama/bin/llama-server \
      -m "$(gguf_of "$M")" -c 8192 -ngl 99 -fa on --no-jinja --host "${HOST:-127.0.0.1}" --port "$(port_of "$M")" \
      > log/serve.log 2>&1 < /dev/null &
    echo $! > "$PIDF"; echo "$M" > "$WHOF"
    for _ in $(seq 60); do
      [ "$(health "$M")" = 200 ] && { echo "UP $M pid $(cat "$PIDF") port $(port_of "$M")"; exit 0; }
      alive || { echo "DIED:"; tail -5 log/serve.log; exit 1; }
      sleep 2
    done
    echo "not healthy after 120 s:"; tail -5 log/serve.log; exit 1 ;;
  down)
    down ;;
  status)
    if alive; then echo "UP $(who) pid $(cat "$PIDF") port $(port_of "$(who)") health $(health "$(who)")"; else echo "DOWN"; fi
    nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader ;;
  *) echo "usage: box_serve.sh up [olmo|nemo] | down | status" >&2; exit 2 ;;
esac
