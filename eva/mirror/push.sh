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
