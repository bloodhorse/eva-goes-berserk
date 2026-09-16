#!/bin/bash
# Follow-up rig: only the states the parallel run couldn't catch, shot ONE AT A TIME
# (four headless browsers at once starved virtual time and produced half-loaded frames),
# with every state set synchronously — notes load through a sync XHR so no fetch races
# the screenshot. Same seed, same iframe-and-crop trick as shoot.sh.
#   shoot2.sh <outdir>
set -u
REPO=/Users/bekh/tower/forge/eva-goes-berserk
M=${M:-/tmp/mobile-rig}   # scratch dir for rig, profiles, shots — set M to move it
OUT=$M/${1:-shots2}
RIG=$M/rig2
PORT=8186
rm -rf "$RIG" "$OUT" "$M/profiles2" "$M/wrap2"; mkdir -p "$RIG/sittings" "$RIG/storage" "$RIG/artifacts" "$OUT/logs" "$M/profiles2" "$M/wrap2"
cp "$REPO/eva/server/loom.py" "$RIG/"
{ cat "$REPO/eva/front/loom.html"
  cat <<'JS'
<script>
function loadNoteSync(name){
  const x = new XMLHttpRequest();
  x.open("GET", "/api/note?name=" + encodeURIComponent(name), false);
  x.send();
  const d = JSON.parse(x.responseText);
  note = {name: d.name, text: d.text};
  document.getElementById("notetitle").textContent = note.name;
  document.getElementById("noteview").textContent = note.text;
  noteMode(false);
  showNote();
}
(function(){
  const js = decodeURIComponent(location.hash.slice(1));
  const w = setInterval(() => {
    try{
      if(typeof sitting === "undefined" || !sitting) return;
      if(!document.querySelector("#blocks .blk")) return;
      clearInterval(w);
      try{ (0,eval)(js); console.log("DBG eval ok"); }
      catch(e){ console.log("DBG eval err " + e); }
      console.log("DBG docW=" + document.documentElement.scrollWidth + " vw=" + innerWidth +
                  " tools=" + !document.getElementById("tools").hidden +
                  " note=" + !document.getElementById("notepane").hidden);
    }catch(e){ console.log("DBG poll err " + e); }
  }, 50);
})()
</script>
JS
} > "$RIG/loom.html"
python3 "$(dirname "$0")/seed.py" "$RIG"

python3 "$REPO/eva/tests/stub_llama.py" 8197 >"$RIG/stub.log" 2>&1 & STUBPID=$!
# loom.py finds its page and shelf relative to the repo it was copied out of; point every one
# of them at the rig, or the scratch server serves the real page over the real sittings.
(cd "$RIG" && LOOM_PORT=$PORT LOOM_LLAMA=http://127.0.0.1:8197 LOOM_PAGE="$RIG/loom.html" \
  LOOM_SITTINGS="$RIG/sittings" LOOM_STORAGE="$RIG/storage" LOOM_ARTIFACTS="$RIG/artifacts" \
  exec python3 loom.py >"$RIG/loom.log" 2>&1) & LOOMPID=$!
sleep 2

H=/Applications/Helium.app/Contents/MacOS/Helium
shot(){ # name width height js
  local tag="$1-$2x$3" w=$2 h=$3
  local hash; hash=$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$4")
  local win=$(( w < 600 ? 600 : w ))
  printf '<!doctype html><style>html,body{margin:0;height:100%%;background:#000}body{display:flex;justify-content:center}iframe{border:0;width:%spx;height:%spx}</style><iframe src="http://127.0.0.1:%s/#%s"></iframe>' \
    "$w" "$h" "$PORT" "$hash" > "$M/wrap2/$tag.html"
  "$H" --headless=new --disable-gpu --hide-scrollbars --no-first-run \
    --user-data-dir="$M/profiles2/$tag" --enable-logging=stderr --v=0 \
    --window-size="$win,$h" --virtual-time-budget=5000 \
    --screenshot="$OUT/$tag.png" "file://$M/wrap2/$tag.html" >"$OUT/logs/$tag.log" 2>&1 &
  local pid=$!
  ( sleep 30; kill -9 "$pid" 2>/dev/null ) &
  local wd=$!
  # the screenshot lands long before a hung exit; stop waiting as soon as the file exists
  for _ in $(seq 1 60); do
    [ -s "$OUT/$tag.png" ] && sleep 1 && break
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.5
  done
  kill -9 "$pid" 2>/dev/null; kill "$wd" 2>/dev/null
  [ -f "$OUT/$tag.png" ] && sips -c "$h" "$w" "$OUT/$tag.png" >/dev/null 2>&1
  printf '%-22s %s\n' "$tag" "$(grep -oE 'DBG[^"]*' "$OUT/logs/$tag.log" | tr '\n' ' ')"
}

LONGJS="turnEl.value='a long line i am typing into the box to see how it grows\n'.repeat(7);turnEl.dispatchEvent(new Event('input'))"
shot menu      390 844 "menu(true)"
shot sampler   390 844 "menu(true);document.getElementById('samp').click()"
shot notice    390 844 "sys('the loom is not answering: TypeError: Failed to fetch, and a long tail of reasons after it',true)"
shot typing    390 844 "$LONGJS"
shot note      390 844 "loadNoteSync('a long finding')"
shot noteedit  390 844 "loadNoteSync('a long finding');editNote()"
shot newnote   390 844 "newNote()"
shot note      360 740 "loadNoteSync('a long finding')"
shot fan       390 844 "showChoices(alternativesFrom())"
shot doctop    844 390 "document.getElementById('blocks').scrollTop=0"

kill -9 $LOOMPID $STUBPID 2>/dev/null
rm -rf "$M/profiles2"
cd "$OUT"
magick menu-390x844.png sampler-390x844.png notice-390x844.png typing-390x844.png note-390x844.png -background '#000' -splice 8x0 +append "$M/$1-a.png" 2>/dev/null
magick noteedit-390x844.png newnote-390x844.png note-360x740.png fan-390x844.png -background '#000' -splice 8x0 +append "$M/$1-b.png" 2>/dev/null
cp doctop-844x390.png "$M/$1-c.png"
ls "$M/$1"-*.png
