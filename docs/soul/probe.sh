#!/usr/bin/env bash
cd ~/eva-olmo
port() { case "$1" in nemo) echo 8082 ;; llama8) echo 8086 ;; mini8) echo 8087 ;; mini14) echo 8088 ;; olmo7-e) echo 8089 ;; olmo7-m) echo 8090 ;; olmo7-l) echo 8091 ;; esac; }
P=$1; TAG=$2; N=$3; shift 3
for m in "$@"; do
  kit/box_serve.sh up "$m" || { echo "SKIP $m"; continue; }
  python3 soul/probe.py "http://127.0.0.1:$(port "$m")" "soul/$m-$TAG" "$P" "$N"
  kit/box_serve.sh down
  sleep 3
done
echo PROBE-DONE
