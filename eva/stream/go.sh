#!/bin/bash
# go.sh — `eva go N`: dream N dreams with everything (note, retelling, picture each), then stop,
# nemo included. bekh's ration (2026-09-22): codex is the scarce thing, so a run is sized in
# dreams — N passages, N plates — not in hours. A dream here is one passage (one plate); the
# four-scene story is the sleeper's unit, not this one's.
#
# Every step is the runbook's own line (stream/CLAUDE.md, "Running it"); this only orders them.
# It runs IN THE FOREGROUND on purpose (bekh: so it's easy to kill): ctrl-c ends it, and the
# trap puts everything back — writer off, nemo off, the painter's cap restored. Lost the
# terminal with a run half done? `eva go stop` does the same from anywhere.
#
# The painter's cap: its launchd job holds under STREAM_PLATE_WEEK_MAX (20 in its plist, a guard
# against an unattended painter eating a week). A run that asks for pictures needs headroom, so
# for the run the cap becomes $CAP — bekh's own number for the week (43 on 2026-09-22: "my real
# expected usage"), not a formula — and goes back when the run ends, however it ends. A week
# already past it refuses to run.
set -u
cd "$(dirname "$0")/../.." || exit 1
U=$(id -u)
PL=~/Library/LaunchAgents/com.bekh.eva-stream-plating.plist
LOG=${EVA_GO_LOG:-/tmp/eva-go.log}
CAP=${EVA_GO_CAP:-43}
SETTLE=100   # STREAM_PLATE_SETTLE (90) and a breath: the reader's note must land before a plate

say() { printf '%s %s\n' "$(date +%T)" "$*" | tee -a "$LOG"; }
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
cap_restore() { [ -f "$PL.cap-was" ] && { cap_set "$(cat "$PL.cap-was")"; rm -f "$PL.cap-was"; }; }
writer_off() {
  launchctl bootout gui/$U/com.bekh.eva-stream 2>/dev/null
  launchctl kill SIGTERM gui/$U/com.bekh.eva-llama 2>/dev/null
  say "writer off, nemo told to stop"
}

case "${1:-}" in
  stop)   # from another terminal, or after a lost one: the same as ctrl-c would do
    say "== stopped by hand"; writer_off; cap_restore; exit 0 ;;
  ''|*[!0-9]*)
    echo "usage: eva go N [CAP]   (N dreams = N passages, N pictures; CAP = the painter's week cap for the run, $CAP; ctrl-c stops it clean)   |   eva go stop"; exit 2 ;;
esac
N=$1; CAP=${2:-$CAP}
if launchctl print gui/$U/com.bekh.eva-stream >/dev/null 2>&1; then echo "the writer is already on — eva go stop first"; exit 1; fi
week=$(week_now); [ -n "$week" ] || { echo "no codex usage cache (~/.cache/claude-usage/codex.json) — run cu first"; exit 1; }
if [ "$week" -ge "$CAP" ]; then echo "codex week at $week%, the cap is $CAP% — nothing would get painted, not running"; exit 1; fi

# ---- the run --------------------------------------------------------------------------------
DAY=$(date +%F); STAMP=$(date +%H%M)
: > "$LOG"
say "== eva go: $N dreams, ~$((N * 5)) min; codex week $week%, painter cap $CAP% for the run. ctrl-c stops it clean."
cap_get > "$PL.cap-was"
cap_set "$CAP"
trap 'echo; say "== interrupted"; writer_off; cap_restore; exit 1' INT TERM

# start: nemo first, wait for it, then the writer
launchctl kickstart gui/$U/com.bekh.eva-llama
for i in $(seq 1 90); do curl -sf http://127.0.0.1:8080/health >/dev/null && break; sleep 2; done
if ! curl -sf http://127.0.0.1:8080/health >/dev/null; then say "nemo never came up; stopping"; cap_restore; exit 1; fi
say "nemo up"
launchctl bootstrap gui/$U ~/Library/LaunchAgents/com.bekh.eva-stream.plist
launchctl kickstart gui/$U/com.bekh.eva-stream
say "writer on"

# wait for the dreams (one every 300s; the ceiling is twice that, in case nemo is slow)
seen=0
for i in $(seq 1 $((N * 40))); do
  c=$(count_since)
  if [ "$c" -ne "$seen" ]; then seen=$c; say "dream $c of $N landed"; fi
  [ "$c" -ge "$N" ] && break
  sleep 15
done
writer_off

# pictures for the tail: the writer's kicks paint one per landing, so the last dreams are still
# bare when the writer stops. paint them by hand, one at a time, until none is left or codex holds.
say "waiting ${SETTLE}s for the reader, then the last pictures"
sleep $SETTLE
for i in $(seq 1 $((N + 2))); do
  left=$(unpainted | wc -l | tr -d ' ')
  [ "$left" -eq 0 ] && break
  say "unpainted: $left — painting"
  while plating_busy; do sleep 10; done
  out=$(STREAM_PLATE_WEEK_MAX=$CAP uv run --python 3.12 eva/stream/plating.py --once 2>&1 | tail -1)
  say "  $out"
  echo "$out" | grep -qi held && break
  sleep 15
done

cap_restore
say "== done: $(count_since) dreams, $(( $(count_since) - $(unpainted | wc -l) )) pictures; codex week now $(week_now)%"
curl -s -H "Title: eva go: $N dreams done" -H "Tags: w00t" \
  -d "$(count_since) dreams, $(( $(count_since) - $(unpainted | wc -l) )) pictures; writer + nemo off; codex week $(week_now)%" ntfy.sh/kk_alert >/dev/null
