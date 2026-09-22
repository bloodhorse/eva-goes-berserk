#!/bin/bash
# go.sh — `eva go N`: dream N whole stories with everything (notes, retellings, pictures), then
# stop, nemo included. bekh's ration (2026-09-22): codex is the scarce thing, so a run is sized in
# stories, not in hours — N stories of STREAM_DREAM_TURNS scenes each, one plate per scene.
#
# Every step is the runbook's own line (stream/CLAUDE.md, "Running it"); this only orders them and
# runs them with nobody at the desk. It detaches: `eva go 5` returns at once, the run lives on
# under nohup, `eva go status` reads its log, `eva go stop` ends it early (writer off, nemo off,
# the painter's cap put back). The runner's own pid is in $PIDFILE.
#
# The painter's cap: its launchd job holds under STREAM_PLATE_WEEK_MAX (20 in its plist, a guard
# against an unattended painter eating a week). A run that asks for pictures needs headroom, so
# the cap is raised for the run — to the week's current number plus what the run costs (about
# 0.7 points a plate) plus a little — and put back the moment the run ends, however it ends.
# Never above $CEILING: past that the run refuses instead of painting.
set -u
cd "$(dirname "$0")/../.." || exit 1
U=$(id -u)
PL=~/Library/LaunchAgents/com.bekh.eva-stream-plating.plist
LOG=${EVA_GO_LOG:-/tmp/eva-go.log}
PIDFILE=/tmp/eva-go.pid
CEILING=${EVA_GO_CEILING:-60}
POINTS_PER_PLATE=0.7
TURNS=$(/usr/libexec/PlistBuddy -c "Print :EnvironmentVariables:STREAM_DREAM_TURNS" \
        ~/Library/LaunchAgents/com.bekh.eva-stream-remembering.plist 2>/dev/null || echo 4)
SETTLE=100   # STREAM_PLATE_SETTLE (90) and a breath: the reader's note must land before a plate

say() { printf '%s %s\n' "$(date +%T)" "$*" >> "$LOG"; }
count_since() { ls shelf/sittings/stream/"$DAY"/ 2>/dev/null | awk -v s="$STAMP" '$0 >= s' | wc -l | tr -d ' '; }
run_rooms() { ls shelf/sittings/stream/"$DAY"/ 2>/dev/null | awk -v s="$STAMP" '$0 >= s' | sed 's/\.json$//'; }
unpainted() { for r in $(run_rooms); do [ -f shelf/stream/plates/"$DAY"/"$r".jpg ] || echo "$r"; done; }
plating_busy() { pgrep -f 'eva/stream/plating.py' >/dev/null; }
week_now() { python3 -c "import json;print(int(json.load(open('$HOME/.cache/claude-usage/codex.json'))['week']['utilization']))" 2>/dev/null; }
cap_get() { /usr/libexec/PlistBuddy -c "Print :EnvironmentVariables:STREAM_PLATE_WEEK_MAX" "$PL"; }
cap_set() {
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:STREAM_PLATE_WEEK_MAX $1" "$PL"
  launchctl bootout gui/$U/com.bekh.eva-stream-plating 2>/dev/null
  launchctl bootstrap gui/$U ~/Library/LaunchAgents/com.bekh.eva-stream-plating.plist
  say "painter cap -> $1"
}
writer_off() {
  launchctl bootout gui/$U/com.bekh.eva-stream 2>/dev/null
  launchctl kill SIGTERM gui/$U/com.bekh.eva-llama 2>/dev/null
  say "writer off, nemo told to stop"
}

case "${1:-}" in
  status)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then echo "running (pid $(cat "$PIDFILE"))"; else echo "not running"; fi
    tail -n 12 "$LOG" 2>/dev/null; exit 0 ;;
  stop)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then kill "$(cat "$PIDFILE")"; sleep 1; fi
    rm -f "$PIDFILE"
    say "== stopped by hand"
    writer_off
    [ -f "$PL.cap-was" ] && { cap_set "$(cat "$PL.cap-was")"; rm -f "$PL.cap-was"; }
    echo "stopped; writer and nemo off"; exit 0 ;;
  run) ;;   # the detached body, below
  ''|*[!0-9]*)
    echo "usage: eva go N | eva go status | eva go stop   (N = whole stories of $TURNS scenes)"; exit 2 ;;
  *)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then echo "a run is already going: eva go status"; exit 1; fi
    N=$1
    week=$(week_now); [ -n "$week" ] || { echo "no codex usage cache (~/.cache/claude-usage/codex.json) — run cu first"; exit 1; }
    need=$(python3 -c "import math;print(math.ceil($N*$TURNS*$POINTS_PER_PLATE)+3)")
    cap=$((week + need))
    if [ "$cap" -gt "$CEILING" ]; then echo "$N stories ≈ $need points on top of a week at $week% — past the $CEILING% ceiling, not running"; exit 1; fi
    echo "$N stories = $((N*TURNS)) scenes, ~$(( (N*TURNS)*5 )) min; codex week $week% → cap $cap% for the run; log $LOG"
    N=$N CAP=$cap nohup "$0" run >/dev/null 2>&1 &
    exit 0 ;;
esac

# ---- the run --------------------------------------------------------------------------------
echo $$ > "$PIDFILE"
DAY=$(date +%F); STAMP=$(date +%H%M)
: > "$LOG"
say "== eva go: $N stories × $TURNS scenes, day $DAY from $STAMP"
cap_get > "$PL.cap-was"
cap_set "$CAP"
trap 'say "== interrupted"; writer_off; cap_set "$(cat "$PL.cap-was")"; rm -f "$PL.cap-was" "$PIDFILE"; exit 1' INT TERM

# start: nemo first, wait for it, then the writer
launchctl kickstart gui/$U/com.bekh.eva-llama
for i in $(seq 1 90); do curl -sf http://127.0.0.1:8080/health >/dev/null && break; sleep 2; done
if ! curl -sf http://127.0.0.1:8080/health >/dev/null; then
  say "nemo never came up; stopping"; cap_set "$(cat "$PL.cap-was")"; rm -f "$PL.cap-was" "$PIDFILE"; exit 1
fi
say "nemo up"
launchctl bootstrap gui/$U ~/Library/LaunchAgents/com.bekh.eva-stream.plist
launchctl kickstart gui/$U/com.bekh.eva-stream
say "writer on"

# wait for the scenes (one every 300s; the ceiling is twice that, in case nemo is slow)
WANT=$((N * TURNS))
for i in $(seq 1 $((WANT * 40))); do
  [ "$(count_since)" -ge "$WANT" ] && break
  sleep 15
done
say "scenes since $STAMP: $(count_since) of $WANT wanted"
writer_off

# pictures for the tail: the writer's kicks paint one per landing, so the last scenes are still
# bare when the writer stops. paint them by hand, one at a time, until none is left or codex holds.
sleep $SETTLE
for i in $(seq 1 $((TURNS + 2))); do
  left=$(unpainted | wc -l | tr -d ' ')
  say "unpainted in this run: $left"
  [ "$left" -eq 0 ] && break
  while plating_busy; do sleep 10; done
  out=$(uv run --python 3.12 eva/stream/plating.py --once 2>&1 | tail -1)
  say "plating --once: $out"
  echo "$out" | grep -qi held && break
  sleep 15
done

cap_set "$(cat "$PL.cap-was")"; rm -f "$PL.cap-was" "$PIDFILE"
say "== done: $(count_since) scenes, $(( $(count_since) - $(unpainted | wc -l) )) plates, codex week now $(week_now)%"
curl -s -H "Title: eva go: $N stories done" -H "Tags: w00t" \
  -d "$(count_since) scenes, $(( $(count_since) - $(unpainted | wc -l) )) plates; writer + nemo off; codex week $(week_now)%" ntfy.sh/kk_alert >/dev/null
