#!/bin/bash
set -u
cd "$(dirname "$0")/../.." || exit 1
U=$(id -u)
BOX=ubuntu@10.4.65.34
box() { ssh -o BatchMode=yes -o ConnectTimeout=8 "$BOX" "$@"; }
up() { curl -sf -m 3 http://127.0.0.1:8080/health >/dev/null; }
loaded() { launchctl print gui/$U/com.bekh.$1 >/dev/null 2>&1; }
off() { loaded "$1" && launchctl bootout gui/$U/com.bekh.$1; while loaded "$1"; do sleep 1; done; }
wait_up() { for _ in $(seq 1 90); do up && return 0; sleep 2; done; return 1; }
where() {
  local p
  p=$(curl -sf -m 3 http://127.0.0.1:8080/props | sed -n 's/.*"model_path":"\([^"]*\)".*/\1/p')
  case "$p" in
    "") echo "nemo: nothing answers on 8080" ;;
    /Users/*) echo "nemo: the mac ($p)" ;;
    *) echo "nemo: the box ($p)" ;;
  esac
}

case "${1:-status}" in
  box)
    off eva-llama
    box '~/eva-olmo/kit/box_serve.sh up nemo' || exit 1
    loaded eva-nemo-box || launchctl bootstrap gui/$U "$PWD/eva/stream/com.bekh.eva-nemo-box.plist"
    wait_up || { echo "the tunnel never answered; see /tmp/eva-nemo-box.log"; exit 1; }
    where ;;
  mac)
    off eva-nemo-box
    box '~/eva-olmo/kit/box_serve.sh down' || echo "the box did not answer; its server was left as it is"
    loaded eva-llama || launchctl bootstrap gui/$U "$PWD/eva/stream/com.bekh.eva-llama.plist"
    wait_up || { echo "nemo never came up; see /tmp/eva-llama.log"; exit 1; }
    where ;;
  off)
    off eva-nemo-box; off eva-llama
    box '~/eva-olmo/kit/box_serve.sh down' || echo "the box did not answer; its server was left as it is"
    where ;;
  status)
    where
    loaded eva-nemo-box && echo "tunnel job loaded"
    loaded eva-llama && echo "mac job loaded"
    box '~/eva-olmo/kit/box_serve.sh status' 2>/dev/null || echo "the box does not answer" ;;
  *) echo "usage: nemo.sh box | mac | off | status"; exit 2 ;;
esac
