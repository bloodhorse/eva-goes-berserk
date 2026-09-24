#!/usr/bin/env bash
# mac_night.sh: the mac's night of generation, nobody reading. Runs from docs/mescalito/night1
# on nemo's Q5 gguf (llama-completion, ~27 s a page). Every page is skipped if its file already
# exists, so a crash is a rerun. A status file is written before every page and `pulse` reads
# it; ntfy at start, at each stage's end, at the finish, and on failure.
#
#   mac_night.sh            # the whole night, in order
#   mac_night.sh pulse      # one line: where it is, how old the last page is, the eta
#
# Stages, in order (bekh, 2026-09-24: generation only at night, he reads):
#   1. small: ender forced fanned — 224 at 0.75 + ignore-eos, five draws, beck / storm / tower (15)
#   2. small: negation — ender, kin, voices at -0.75 on beck and the storm-girl (6)
#   3. baseline: the tower seed sober, five draws (5) — beck and the storm-girl have theirs in fan/
#   4. the lottery: all 256 owned directions at 0.75, one draw, on the storm-girl, the tower, beck (768)
#   5. stats: one row per vector per seed — words, ended early, distinct-2, rep4, first word — lottery/stats.tsv
set -uo pipefail
cd "$(dirname "$0")/../night1" || exit 1
M=$HOME/.cache/llama.cpp/Mistral-Nemo-Base-2407.Q5_K_M.gguf
SAMP="--temp 2.0 --min-p 0.08 --top-k 0 --top-p 1.0 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --repeat-penalty 1.05 --repeat-last-n 512"
SEEDS=../../olmo-seeds
BECK=$SEEDS/2026-09-21-1645.txt; STORM=$SEEDS/2026-09-21-1650.txt; TOWER=$SEEDS/2026-09-23-0033.txt
START=$(date +%s); DONE=0; TOTAL=794

ntfy() { curl -s -H "Title: mescalito night" -H "Tags: crescent_moon" -d "$1" ntfy.sh/kk_alert >/dev/null || true; }

if [ "${1:-}" = pulse ]; then
  [ -f status.json ] || { echo "no status yet"; exit 0; }
  python3 - <<'EOF'
import json, time, os
s = json.load(open("status.json")); age = int(time.time() - os.path.getmtime("status.json"))
rate = s["elapsed"] / max(1, s["done"]); left = (s["total"] - s["done"]) * rate
eta = time.strftime("%H:%M", time.localtime(time.time() + left)) if s["done"] < s["total"] else "done"
state = "alive" if age < 120 else "STALE"
print(f"{s['stage']}: {s['done']}/{s['total']} pages · last page {age}s ago ({state}) · {s['seed']} · {s['vector']} · eta {eta}")
EOF
  exit 0
fi

# page STAGE SEEDFILE OUT VECTORFLAGS... — one page, status first, skipped if it exists
page() {
  local stage=$1 seed=$2 out=$3; shift 3
  DONE=$((DONE + 1))
  printf '{"stage":"%s","seed":"%s","vector":"%s","done":%d,"total":%d,"elapsed":%d}\n' \
    "$stage" "$(basename "$seed" .txt)" "$(basename "$out" .txt)" "$DONE" "$TOTAL" "$(( $(date +%s) - START ))" > status.json
  [ -s "$out" ] && return 0
  llama-completion -m "$M" -ngl 99 -c 2048 -f "$seed" -n 170 -no-cnv --no-display-prompt $SAMP "$@" > "$out" 2>/dev/null \
    || { ntfy "FAILED at $out"; echo "FAILED $out"; exit 1; }
}
cv() { echo --control-vector-scaled "cv-nemo/$1.gguf:$2" --control-vector-layer-range 9 9; }

ntfy "night started: 794 pages, ~6 h"

# 1. ender forced, fanned
mkdir -p forced-fan
for s in $BECK $STORM $TOWER; do n=$(basename $s .txt); for r in 1 2 3 4 5; do
  page ender-forced $s forced-fan/${n}__x0.75__r$r.txt --seed $r --ignore-eos $(cv 224_f112 0.75)
done; done
ntfy "ender forced fan done (15)"

# 2. negation
mkdir -p negation
for s in $BECK $STORM; do n=$(basename $s .txt); for v in 224_f112 125_f146 169_f199; do
  page negation $s negation/${n}__${v}__x-0.75.txt --seed 1 $(cv $v -0.75)
done; done
ntfy "negation done (6)"

# 3. the tower seed sober
mkdir -p fan
for r in 1 2 3 4 5; do page tower-sober $TOWER fan/2026-09-23-0033__sober__r$r.txt --seed $r; done

# 4. the lottery
mkdir -p lottery
for s in $STORM $TOWER $BECK; do n=$(basename $s .txt)
  for f in cv-nemo/[0-9]*.gguf; do v=$(basename $f .gguf)
    page lottery $s lottery/${n}__${v}__x0.75.txt --seed 1 $(cv $v 0.75)
  done
  ntfy "lottery: $n done (256)"
done

# 5. stats
python3 - <<'EOF'
import glob, os, re
rows = []
for p in sorted(glob.glob("lottery/*.txt")):
    s, v, _ = os.path.basename(p)[:-4].split("__")
    t = open(p, errors="replace").read()
    w = re.findall(r"\w+|[^\w\s]", t.lower())
    bi = list(zip(w, w[1:])); q4 = list(zip(w, w[1:], w[2:], w[3:]))
    seen, rep = set(), 0
    for g in q4:
        rep += g in seen; seen.add(g)
    first = (t.strip().split() or [""])[0]
    rows.append((v, s, len(t.split()), int("[end of text]" in t), round(len(set(bi)) / max(1, len(bi)), 3), round(rep / max(1, len(q4)), 3), first))
with open("lottery/stats.tsv", "w") as f:
    f.write("vector\tseed\twords\tended_early\tdistinct2\trep4\tfirst_word\n")
    for r in rows: f.write("\t".join(map(str, r)) + "\n")
print(len(rows), "rows")
EOF
printf '{"stage":"finished","seed":"","vector":"","done":%d,"total":%d,"elapsed":%d}\n' "$TOTAL" "$TOTAL" "$(( $(date +%s) - START ))" > status.json
ntfy "night finished: $(ls lottery/*.txt | wc -l | tr -d ' ') lottery pages, stats.tsv written"
