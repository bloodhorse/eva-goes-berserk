#!/usr/bin/env bash
cd "${SCHOOL:-/opt/llama/magdra}" || exit 1
N=${1:-}; INIT=${2:-${INIT:-}}; HOURS=${3:-${HOURS:-}}
die() { echo "run4: $*" >&2; exit 1; }
[ -n "$N" ] || die "usage: run4.sh <run> [init.pt] [hours]   (env: MIX or MIXFILE, INIT, HOURS or STEPS, BATCH ACCUM LR WARMUP LOG_EVERY EVAL_EVERY EVAL_ITERS CKPT_MINUTES PROMPTS COMPILE TRIES PAUSE NTFY DRY)"
R=runs/$N
PY=${PY:-$PWD/.venv/bin/python}
if [ -z "${MIX:-}" ]; then
  F=${MIXFILE:-night/$N/mix.txt}; [ -f "$F" ] || F=runs/$N/mix.txt
  [ -f "$F" ] || die "no mix: set MIX, or write one bin:weight per line into ${MIXFILE:-night/$N/mix.txt}"
  MIX=$(sed -e 's/#.*//' "$F" | tr -s ' \t\r\n' ' ')
fi
read -r -a PARTS <<< "$MIX"
[ "${#PARTS[@]}" -gt 0 ] || die "the mix is empty"
for p in "${PARTS[@]}"; do
  [[ "$p" =~ ^[^:]+:[0-9]+(\.[0-9]+)?$ ]] || die "mix entry '$p' is not bin:weight"
  [ -f "${p%:*}" ] || die "mix entry '$p': no such file ${p%:*}"
done
if [ ! -f "$R/ckpt.pt" ]; then
  [ -n "$INIT" ] || die "no init checkpoint: run4.sh <run> <init.pt>, or INIT="
  [ -f "$INIT" ] || die "init checkpoint $INIT: no such file"
  [ -n "$HOURS" ] || [ -n "${STEPS:-}" ] || die "no budget: run4.sh <run> <init.pt> <hours>, or HOURS= or STEPS="
fi
if [ -n "${STEPS:-}" ]; then BUDGET=(--steps "$STEPS"); SAY="$STEPS steps"; else BUDGET=(--hours "$HOURS"); SAY="$HOURS h"; fi
DATA=(--data "${PARTS[@]}" --out "$R")
SHAPE=(--init "$INIT" --batch "${BATCH:-6}" --accum "${ACCUM:-4}" --lr "${LR:-8e-5}" --warmup "${WARMUP:-300}" "${BUDGET[@]}" --log-every "${LOG_EVERY:-50}" --eval-every "${EVAL_EVERY:-1000}" --eval-iters "${EVAL_ITERS:-20}" --ckpt-minutes "${CKPT_MINUTES:-20}")
PROMPTS=${PROMPTS-prompts.txt}; [ -z "$PROMPTS" ] || SHAPE+=(--prompts "$PROMPTS")
[ "${COMPILE-1}" = 1 ] && SHAPE+=(--compile)
NTFY=${NTFY-ntfy.sh/kk_alert}
push() { [ -z "$NTFY" ] || curl -s -m 10 -H "Title: $1" -H "Priority: low" -H "Tags: $2" -d "$3" "$NTFY" > /dev/null; }
if [ -n "${DRY:-}" ]; then
  echo "start:  $PY train.py ${DATA[*]} ${SHAPE[*]} >> $R.log"
  echo "resume: $PY train.py ${DATA[*]} >> $R.log"
  exit 0
fi
mkdir -p "$R"
push "school: $N started" hatching_chick "magdra, warm start from $INIT, $SAY"
for try in $(seq 1 "${TRIES:-30}"); do
  if [ -f "$R/ckpt.pt" ]; then $PY train.py "${DATA[@]}" >> "$R.log" 2>&1; else $PY train.py "${DATA[@]}" "${SHAPE[@]}" >> "$R.log" 2>&1; fi
  if tail -n 5 "$R.log" | grep -q -E 'DONE step=|STOPPED step='; then break; fi
  echo "$(date -u +%FT%TZ) trainer exited without DONE, restart $try" >> "$R.guard.log"
  sleep "${PAUSE:-30}"
done
E=$(tail -n 3 "$R.log" | grep -o -E '(DONE|STOPPED) step=[0-9]+ tokens=[0-9,]+ eval_loss=[0-9.]+' | tail -1)
push "school: $N ended" checkered_flag "${E:-gave up after ${TRIES:-30} restarts}"
echo "$(date -u +%FT%TZ) wrapper exit: ${E:-gave up}" >> "$R.guard.log"
