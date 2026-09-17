#!/bin/bash
# The mac → mini push: the page, the server and the shelf, copied to ~/eva-mirror on the mini,
# where eva-mirror.service serves them read-only while the mac is off. Run every minute by
# launchd (com.bekh.eva-mirror). Quiet when nothing changed; one line when something did.
#
# One direction only, --delete on: the mirror is a copy, never a place anything is written, so
# whatever is there and not here is stale by definition.
set -u
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
HOST=${EVA_MIRROR_HOST:-bek@miniarch}
DEST=eva-mirror
SSH="ssh -o BatchMode=yes -o ConnectTimeout=15"
stamp(){ date '+%F %T'; }

cd "$REPO" || exit 1

# Marks made on the mirror come home FIRST, through the mac's own loom — the same /api/mark the
# canvas uses, so a keep builds its artifact here like any other keep. Only then is the copy
# pushed over, and by then it carries those marks. mv, not cat+rm: a mark landing on the mirror
# mid-take goes into a fresh journal instead of being deleted unread. The taken lines stay in
# `.taking` until every one has landed, and a replay is safe to repeat: a mark is set, not toggled.
LOOM=${EVA_MIRROR_LOOM:-http://100.91.166.121:8082}
J=eva-marks.jsonl
marks=$($SSH "$HOST" "if [ -s $J ]; then mv $J $J.new && cat $J.new >> $J.taking && rm $J.new; fi; cat $J.taking 2>/dev/null; true") \
  || { echo "$(stamp) can't read the mirror's marks"; exit 1; }
if [ -n "$marks" ]; then
  n=0
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 90 -H 'Content-Type: application/json' \
      -d "$line" "$LOOM/api/mark")
    case "$code" in
      # 400/404: that room or branch is gone on the mac — there is nothing to land the mark on
      200|400|404) n=$((n + 1)) ;;
      # the loom is down: stop here and push nothing, or the copy would lose the marks it shows
      *) echo "$(stamp) replay stopped at mark $((n + 1)): the loom said $code"; exit 1 ;;
    esac
  done <<<"$marks"
  $SSH "$HOST" "rm -f $J.taking" || { echo "$(stamp) replayed $n marks, couldn't clear the journal"; exit 1; }
  echo "$(stamp) replayed $n marks from the mirror"
fi

# --relative keeps the repo layout (eva/server, eva/front, shelf) because loom.py finds the
# page and the shelf relative to its own file. Running state and the trash stay home.
out=$(rsync -az --delete --relative --itemize-changes -e "$SSH" \
  --exclude '__pycache__/' --exclude '.trash/' --exclude '.DS_Store' --exclude '*.part' \
  --exclude 'shelf/berserk/heartbeat' --exclude 'shelf/berserk/state.json' \
  eva/server eva/front shelf "$HOST:$DEST/" 2>&1) || { echo "$(stamp) push failed: $out"; exit 1; }

# A new loom.py on disk is not a new loom.py running: python read it at start.
restart=""
if grep -q 'eva/server/loom.py' <<<"$out"; then restart="sudo systemctl restart eva-mirror"; fi
# The stamp is "the copy is current as of now", so it moves on every successful push, changes
# or not — that is what the page prints as "synced".
$SSH "$HOST" "touch $DEST/.synced${restart:+; $restart}" || { echo "$(stamp) stamp failed"; exit 1; }
[ -n "$out" ] && echo "$(stamp) pushed $(grep -c . <<<"$out") changes${restart:+, mirror restarted}"
exit 0
