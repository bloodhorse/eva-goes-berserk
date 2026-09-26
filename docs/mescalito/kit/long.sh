#!/usr/bin/env bash
# long.sh: one direction at one dose over many seeds, unattended. bekh, 2026-09-26: the power
# 061_f20 at 0.75, "100 pages, get more seeds like scott and the green book" — the pot as cut
# tonight plus pot2. Runs run.sh per seed under caffeinate; writes status.json after every seed
# (the heartbeat) and pushes to the phone at start, at the half and at the end.
#
#     long.sh <out-dir> <vector> <dose> <rng-list> <seed-file>...
#
# out-dir relative to night2/, one folder per seed under it, named by the seed file's stem.
set -uo pipefail
[ $# -ge 5 ] || { echo "usage: long.sh <out-dir> <vector> <dose> <rng-list> <seed-file>..." >&2; exit 2; }
OUT=$1; V=$2; D=$3; RNGS=$4; shift 4
KIT=$(cd "$(dirname "$0")" && pwd)
NIGHT=$KIT/../night2
mkdir -p "$NIGHT/$OUT"
STATUS=$NIGHT/$OUT/status.json
TOTAL=$#; n=0; START=$(date +%s); HALF=$(( TOTAL / 2 ))
ping() { curl -s -H "Title: mescalito long" -d "$1" ntfy.sh/kk_alert >/dev/null 2>&1 || true; }
ping "start: $V x$D, $TOTAL seeds, rng $RNGS"
for SEEDF in "$@"; do
  n=$((n+1)); name=$(basename "$SEEDF" .txt)
  printf '{"stage":"%s %s x%s","seed":"%s","done":%d,"total":%d,"elapsed":%d,"ts":%d}\n' \
    "$OUT" "$V" "$D" "$name" "$n" "$TOTAL" "$(( $(date +%s) - START ))" "$(date +%s)" > "$STATUS"
  caffeinate -i "$KIT/run.sh" "$OUT/$name" "$SEEDF" "$V" "$D" "$RNGS" 170 >/dev/null
  [ "$n" -eq "$HALF" ] && ping "half: $n of $TOTAL seeds, $(( ($(date +%s) - START) / 60 )) min"
done
printf '{"stage":"done","done":%d,"total":%d,"elapsed":%d,"ts":%d}\n' "$n" "$TOTAL" "$(( $(date +%s) - START ))" "$(date +%s)" > "$STATUS"
ping "done: $n seeds, $(( ($(date +%s) - START) / 60 )) min"
