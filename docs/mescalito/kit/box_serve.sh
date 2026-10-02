#!/usr/bin/env bash
set -uo pipefail
cd ~/eva-olmo
PORT=${PORT:-8081}
PIDF=log/serve.pid
alive() { [ -s "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; }
health() { curl -s -m 3 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/health"; }

case "${1:-status}" in
  up)
    if alive; then echo "already up: pid $(cat "$PIDF"), health $(health)"; exit 0; fi
    sudo bash /opt/llama/scripts/set-model.sh stop >/dev/null 2>&1
    used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
    if [ "$used" -gt 500 ]; then echo "card busy: ${used} MiB in use" >&2; exit 1; fi
    LD_LIBRARY_PATH=/opt/llama/lib:/usr/local/cuda-13.3/lib64 nohup /opt/llama/bin/llama-server \
      -m "$(ls olmo-q4/*.gguf)" -c 8192 -ngl 99 -fa on --no-jinja --host 0.0.0.0 --port "$PORT" \
      > log/serve.log 2>&1 < /dev/null &
    echo $! > "$PIDF"
    for _ in $(seq 60); do
      [ "$(health)" = 200 ] && { echo "UP pid $(cat "$PIDF") port $PORT"; exit 0; }
      alive || { echo "DIED:"; tail -5 log/serve.log; exit 1; }
      sleep 2
    done
    echo "not healthy after 120 s:"; tail -5 log/serve.log; exit 1 ;;
  down)
    if alive; then kill "$(cat "$PIDF")"; echo "DOWN"; else echo "not running"; fi
    rm -f "$PIDF" ;;
  status)
    if alive; then echo "UP pid $(cat "$PIDF") port $PORT health $(health)"; else echo "DOWN"; fi
    nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader ;;
  *) echo "usage: box_serve.sh up|down|status" >&2; exit 2 ;;
esac
