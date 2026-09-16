#!/usr/bin/env -S uv run --python 3.12
"""berserk_monitor.py — is berserk.py alive, and how far has it walked? Read-only.

    uv run --python 3.12 berserk_monitor.py          # a frame every two seconds
    uv run --python 3.12 berserk_monitor.py --once   # one frame and out

Three signals, kept apart on purpose, because conflating them is how a dead run looks busy:

  1. **the probe** — the spinner and the clock move, so you know THIS process is polling and
     not itself frozen on a stale frame;
  2. **alive** — the heartbeat's age. berserk rewrites it on every branch, so a fan of 15 at
     ~11 tok/s is a beat every few seconds; the only long silence a healthy run has is one
     picker call, which can be minutes. Hence mint under 3 minutes, light blue under 10;
  3. **progressing** — the ledger's last fork line. Alive-but-stuck is a heartbeat ticking
     with `fork` frozen, and it looks nothing like dead.

Plus the pid from state.json: state.json present with a pid nobody answers to means the run
died mid-walk, which is the one state that needs a human.

Never writes. Reads berserk/heartbeat, berserk/ledger.jsonl and berserk/state.json, all of
which may be missing, half-written or from last week — every read here is allowed to fail.

Env: BERSERK_DIR (default berserk/ next to this file).
"""

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BERSERK = os.environ.get("BERSERK_DIR", os.path.join(HERE, "berserk"))
HEARTBEAT = os.path.join(BERSERK, "heartbeat")
LEDGER = os.path.join(BERSERK, "ledger.jsonl")
STATE = os.path.join(BERSERK, "state.json")

# A branch is seconds, a picker call is minutes. Anything past ten minutes is not a slow
# reader any more — it is a hung subprocess or a model that went away.
ALIVE_S, LAGGING_S = 180, 600

R, BOLD = "\033[0m", "\033[1m"
# House palette: mint good/active, pink fail, light blue context.
MINT, MINT_HI, MINT_LO = "\033[36m", "\033[1;36m", "\033[2;36m"
PINK = "\033[95m"
LBLUE = "\033[94m"
CLEAR, HIDE, SHOW = "\033[H\033[J", "\033[?25l", "\033[?25h"
SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def read_ledger(n=400):
    """The tail, parsed leniently. A line being written as we read it is normal and is
    simply skipped — the next frame gets it."""
    try:
        with open(LEDGER, encoding="utf-8") as f:
            lines = f.readlines()[-n:]
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def fmt_age(sec):
    if sec < 60:
        return f"{int(sec)}s"
    if sec < 3600:
        return f"{int(sec // 60)}m{int(sec % 60):02d}s"
    return f"{int(sec // 3600)}h{int((sec % 3600) // 60):02d}m"


def cut(s, n):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n - 1] + "…"


def render(spin, now):
    try:
        width = os.get_terminal_size().columns
    except OSError:
        width = 80
    width = max(48, min(width, 100))

    hb = read_json(HEARTBEAT)
    st = read_json(STATE)
    rows = read_ledger()
    forks = [r for r in rows if r.get("event") is None]
    pages = [r for r in rows if r.get("event") == "page"]
    cycles = [r for r in rows if r.get("event") == "cycle"]

    out = [CLEAR]
    clock = time.strftime("%H:%M:%S", time.localtime(now))
    out.append(f"{BOLD}{MINT}BERSERK{R} {MINT}{spin}{R}  {LBLUE}{BERSERK}{R}"
               f"{' ' * max(1, width - 24 - len(BERSERK) - len(clock))}{clock}")
    out.append(LBLUE + "─" * width + R)

    # 1. alive — the heartbeat's age, and nothing else. It says nothing about progress.
    if hb is None:
        dot, label = LBLUE + "●" + R, LBLUE + "NO HEARTBEAT" + R
        sub = "never run here, or the dir is wrong"
    else:
        age = now - (hb.get("ts") or 0)
        if age <= ALIVE_S:
            dot, label = MINT_HI + "●" + R, MINT_HI + "ALIVE" + R
        elif age <= LAGGING_S:
            dot, label = LBLUE + "●" + R, LBLUE + "QUIET — a picker call runs for minutes" + R
        else:
            dot, label = PINK + "●" + R, BOLD + PINK + "STALE — maybe dead" + R
        sub = (f"heartbeat {fmt_age(age)} ago · {hb.get('phase') or '—'}"
               f" · branch {hb.get('branch') or '—'}")
    out.append(f"{dot} {label}   {LBLUE}{sub}{R}")

    # The one state that needs a human: a run that left its state file behind.
    if st is None:
        out.append(f"  {LBLUE}no run in flight (state.json gone — clean exit){R}")
    elif pid_alive(st.get("pid")):
        out.append(f"  {MINT}pid {st.get('pid')} running{R}"
                   f"   {LBLUE}up {fmt_age(now - (st.get('started') or now))}{R}")
    else:
        out.append(f"  {PINK}pid {st.get('pid')} is GONE — the run died mid-walk{R}")
    out.append("")

    # 2. progressing — where the walk actually is, off the ledger and state, not the beat.
    if st or hb:
        at = st or hb
        page, fork = at.get("page"), at.get("fork")
        room = at.get("room") or "—"
        here = [r for r in forks if r.get("room") == room]
        bits = round(sum(r.get("bits") or 0 for r in here), 1)
        fails = sum(1 for r in here if r.get("picker_failed"))
        out.append(f"  {MINT_HI}cycle {at.get('cycle')}{R}  "
                   f"{MINT}page {page}{R}  {MINT}fork {fork}{R}   {LBLUE}{room}{R}")
        out.append(f"  {LBLUE}{len(here)} forks on this page · {bits} bits · "
                   f"{fails} picker failure{'' if fails == 1 else 's'}{R}")
        if here:
            last = here[-1]
            out.append(f"  {MINT_LO}genre{R} {cut(last.get('genre'), width - 10)}")
            out.append(f"  {MINT_LO}note {R} {cut(last.get('note'), width - 10)}")
    out.append("")

    out.append(f"  {LBLUE}pages landed {len(pages)} · cycles closed {len(cycles)}{R}")
    out.append("")
    out.append(f"  {LBLUE}last 8 ledger lines:{R}")
    for r in rows[-8:]:
        if r.get("event") == "page":
            mark = PINK if r.get("error") else MINT_HI
            out.append(f"    {mark}page {r.get('room')} · {r.get('bits')} bits · "
                       f"{'posted' if r.get('posted') else 'not posted'}"
                       f"{' · ' + str(r.get('error')) if r.get('error') else ''}{R}")
        elif r.get("event") == "cycle":
            out.append(f"    {MINT_HI}cycle {r.get('cycle')} done · "
                       f"{r.get('notable')} of {r.get('pages')} notable{R}")
        else:
            mark = PINK if r.get("picker_failed") else MINT_LO
            out.append(f"    {mark}p{r.get('page')} f{r.get('fork')}"
                       f"{' close' if r.get('closing') else '     '} "
                       f"{r.get('fan_size')}→{r.get('pick')} keep {r.get('keep')} "
                       f"{r.get('seconds')}s{R}  {LBLUE}{cut(r.get('genre'), 28)}{R}")
    out.append("")
    out.append(f"{LBLUE}  ctrl-c to quit · read-only{R}")
    sys.stdout.write("\n".join(out) + "\n")
    sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    i = 0
    sys.stdout.write("" if a.once else HIDE)
    try:
        while True:
            render(SPIN[i % len(SPIN)], time.time())
            if a.once:
                break
            i += 1
            time.sleep(a.interval)
    except KeyboardInterrupt:
        pass
    finally:
        if not a.once:
            sys.stdout.write(SHOW + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
