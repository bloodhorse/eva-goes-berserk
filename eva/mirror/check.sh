#!/bin/bash
# Verdicts only, one per line: is each piece of the mirror doing its job. Run from the mac.
set -u
HOST=bek@miniarch
SSH="ssh -o BatchMode=yes -o ConnectTimeout=15"
v(){ printf '%-34s %s\n' "$1" "$2"; }

curl -s --max-time 5 http://100.91.166.121:8082/api/health >/dev/null \
  && v "mac loom" UP || v "mac loom" DOWN
launchctl list 2>/dev/null | grep -q com.bekh.eva-mirror \
  && v "push agent (launchd)" LOADED || v "push agent (launchd)" NOT-LOADED

remote=$($SSH "$HOST" 'systemctl is-active eva-mirror;
  curl -s --max-time 5 http://127.0.0.1:8083/api/health;
  echo; echo $(( $(date +%s) - $(stat -c %Y eva-mirror/.synced 2>/dev/null || echo 0) ))' 2>/dev/null)
if [ -z "$remote" ]; then v "mini" UNREACHABLE; else
  [ "$(sed -n 1p <<<"$remote")" = active ] && v "mirror service" ACTIVE || v "mirror service" INACTIVE
  grep -q '"readonly": true' <<<"$(sed -n 2p <<<"$remote")" \
    && v "mirror answers read-only" MATCH || v "mirror answers read-only" MISMATCH
  age=$(sed -n 3p <<<"$remote")
  [ "${age:-99999}" -lt 180 ] && v "mirror synced" "FRESH (${age}s ago)" || v "mirror synced" "STALE (${age}s ago)"
fi

route=$(curl -s --max-time 10 https://eva.x/api/health)
case "$route" in
  *'"readonly": false'*) v "eva.x served by" MAC ;;
  *'"readonly": true'*)  v "eva.x served by" MIRROR ;;
  *)                     v "eva.x served by" NOTHING ;;
esac
