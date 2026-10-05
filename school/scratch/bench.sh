#!/usr/bin/env bash
cd ~/eva-olmo/school
PY=~/eva-olmo/.venv-train/bin/python
SECS=${SECS:-60}
run() {
  local name=$1 layers=$2 width=$3 heads=$4 comp=$5; shift 5
  for b in "$@"; do
    echo "=== $name compile=$comp batch=$b"
    $PY train.py --data stand/gutenberg.bin --out bench/$name --bench --seconds $SECS --layers $layers --width $width --heads $heads --ctx 1024 --batch $b $comp > bench/$name-$b${comp:+-c}.log 2>&1
    if grep -q BENCH bench/$name-$b${comp:+-c}.log; then grep BENCH bench/$name-$b${comp:+-c}.log; break; fi
    grep -E "OutOfMemory|Error" bench/$name-$b${comp:+-c}.log | tail -1
  done
}
mkdir -p bench
for spec in "s30 6 384 6 64 32" "s125 12 768 12 32 16 8" "s350 24 1024 16 16 8 4"; do
  set -- $spec
  n=$1 l=$2 w=$3 h=$4; shift 4
  run $n $l $w $h "" "$@"
  run $n $l $w $h --compile "$@"
done
echo BENCH-DONE
