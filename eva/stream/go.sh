#!/bin/bash
# go.sh — `eva go N`: dream N dreams with everything (note, retelling, picture each), then stop,
# nemo included — the one dreamer since gpt-2 came off the stream on 2026-09-28. A run is sized
# in dreams — N passages, N plates — not in hours. A dream here is one passage (one plate); the
# four-scene story is the sleeper's unit, not this one's.
#
# Every step is the runbook's own line (stream/CLAUDE.md, "Running it"); this only orders them.
# It runs IN THE FOREGROUND on purpose (bekh: so it's easy to kill): ctrl-c ends it, and the
# trap puts everything back — writer off, nemo off. Lost the terminal with a run half
# done? `eva go stop` does the same from anywhere.
set -u
cd "$(dirname "$0")/../.." || exit 1
U=$(id -u)
LOG=${EVA_GO_LOG:-/tmp/eva-go.log}
SETTLE=100   # STREAM_PLATE_SETTLE (90) and a breath: the reader's note must land before a plate

say() { printf '%s %s\n' "$(date +%T)" "$*" | tee -a "$LOG"; }
count_since() { ls shelf/sittings/stream/"$DAY"/ 2>/dev/null | awk -v s="$STAMP" '$0 >= s' | wc -l | tr -d ' '; }
run_rooms() { ls shelf/sittings/stream/"$DAY"/ 2>/dev/null | awk -v s="$STAMP" '$0 >= s' | sed 's/\.json$//'; }
unpainted() { for r in $(run_rooms); do [ -f shelf/stream/plates/"$DAY"/"$r".jpg ] || echo "$r"; done; }
plating_busy() { pgrep -f 'eva/stream/plating.py' >/dev/null; }
# who is at work right now: a launchd job's state flips to running while a voice is busy
running() { launchctl print gui/$U/com.bekh.$1 2>/dev/null | grep -q "state = running"; }
busy_lines() {  # printed on the rising edge only, so the terminal reads like a log, not a spinner
  local now="" j label
  for j in "eva-stream:writing a dream…" "eva-stream-interpreter:codex reading…" \
           "eva-stream-remembering:opus retelling the story…" "eva-stream-plating:codex painting…"; do
    label=${j#*:}; running "${j%%:*}" && now="$now$label|"
    case "$WAS" in *"$label|"*) ;; *) [[ "$now" == *"$label|"* ]] && say "$label" ;; esac
  done
  WAS=$now
}
NARR=""
narrate_on() {  # every ledger row as a plain line: who did what, how long it took
  tail -n0 -F shelf/stream/ledger.jsonl 2>/dev/null | uv run --python 3.12 eva/stream/narrate.py | tee -a "$LOG" &
  NARR=$!
}
narrate_off() { [ -n "$NARR" ] && { kill $NARR 2>/dev/null; pkill -P $NARR 2>/dev/null; }; NARR=""; }
writer_off() {
  launchctl bootout gui/$U/com.bekh.eva-stream 2>/dev/null
  launchctl bootout gui/$U/com.bekh.eva-llama 2>/dev/null
  say "writer off, nemo told to stop"
}
up() { curl -sf http://127.0.0.1:8080/health >/dev/null; }

case "${1:-}" in
  stop)   # from another terminal, or after a lost one: the same as ctrl-c would do
    say "== stopped by hand"; writer_off; exit 0 ;;
  ''|*[!0-9]*)
    echo "usage: eva go N   (N dreams = N passages, N pictures; ctrl-c stops it clean)   |   eva go stop"; exit 2 ;;
esac
N=$1
if launchctl print gui/$U/com.bekh.eva-stream >/dev/null 2>&1; then echo "the writer is already on — eva go stop first"; exit 1; fi

# ---- the run --------------------------------------------------------------------------------
DAY=$(date +%F); STAMP=$(date +%H%M)
: > "$LOG"
say "== eva go: $N dreams, ~$((N * 5)) min. ctrl-c stops it clean."
trap 'echo; say "== interrupted"; writer_off; narrate_off; exit 1' INT TERM HUP
WAS=""

# start: nemo first, wait for it, then the writer
if up; then say "nemo already answers on 8080; the mac's is not started"
else launchctl bootstrap gui/$U "$PWD/eva/stream/com.bekh.eva-llama.plist" 2>/dev/null; fi
for i in $(seq 1 90); do up && break; sleep 2; done
if ! up; then say "nemo never came up; stopping"; writer_off; exit 1; fi
say "nemo up"
launchctl bootstrap gui/$U "$PWD/eva/stream/com.bekh.eva-stream.plist"
launchctl kickstart gui/$U/com.bekh.eva-stream
say "writer on"
narrate_on

# wait for the dreams (one every 300s; the ceiling is twice that, in case nemo is slow)
seen=0
for i in $(seq 1 $((N * 120))); do
  c=$(count_since)
  if [ "$c" -ne "$seen" ]; then seen=$c; say "— dream $c of $N —"; fi
  [ "$c" -ge "$N" ] && break
  busy_lines
  sleep 5
done
writer_off

# pictures for the tail: the writer's kicks paint one per landing, so the last dreams are still
# bare when the writer stops. paint them by hand, one at a time, until none is left.
say "waiting ${SETTLE}s for the reader, then the last pictures"
for i in $(seq 1 $((SETTLE / 5))); do busy_lines; sleep 5; done
for i in $(seq 1 $((N + 2))); do
  left=$(unpainted | wc -l | tr -d ' ')
  [ "$left" -eq 0 ] && break
  say "unpainted: $left — painting"
  while plating_busy; do busy_lines; sleep 5; done
  say "codex painting…"
  uv run --python 3.12 eva/stream/plating.py --once >/dev/null 2>&1
  sleep 5
done

narrate_off
say "== done: $(count_since) dreams, $(( $(count_since) - $(unpainted | wc -l) )) pictures"
curl -s -H "Title: eva go: $N dreams done" -H "Tags: w00t" \
  -d "$(count_since) dreams, $(( $(count_since) - $(unpainted | wc -l) )) pictures; writer and nemo off" ntfy.sh/kk_alert >/dev/null
