#!/usr/bin/env -S uv run --python 3.12
"""monitor.py — is the stream still dreaming, and is it getting anywhere? Read-only.

    uv run --python 3.12 eva/stream/monitor.py          # a frame every two seconds
    uv run --python 3.12 eva/stream/monitor.py --once   # one frame and out

berserk's dashboard, same skin, for a worker with a very different shape: berserk is one
long run with a pid, this is one short run every five minutes with no pid to find between
them. So the three signals are read off different things, and they are still three:

  1. **the probe** — the spinner and the clock move, so you know THIS process is polling and
     is not itself frozen on a stale frame;
  2. **alive** — the heartbeat's age. The worker rewrites it on every run, success or not,
     so anything under one interval is fine, under two is one missed turn (a busy GPU), and
     past that something is wrong with the timer or the box;
  3. **progressing** — pages actually LANDING on the ledger. A heartbeat ticking every five
     minutes with nothing but error rows under it is the alive-but-stuck state, and it looks
     nothing like dead: llama is down, or every page is coming back empty.

Never writes. Reads ledger.jsonl and heartbeat.json in shelf/stream/, both of which may be
missing, half-written or from last week — every read here is allowed to fail.

Env: STREAM_DIR (default shelf/stream/), STREAM_INTERVAL (default 300).
"""

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))                     # eva/stream
ROOT = os.path.dirname(os.path.dirname(HERE))                          # the repo
STREAM = os.environ.get("STREAM_DIR", os.path.join(ROOT, "shelf", "stream"))
HEARTBEAT = os.path.join(STREAM, "heartbeat.json")
LEDGER = os.path.join(STREAM, "ledger.jsonl")

INTERVAL = int(os.environ.get("STREAM_INTERVAL", "300"))
# One interval is a turn taken; two is a turn missed, which happens when the GPU is busy with
# a census and is not news. Past that, somebody wants to know.
ALIVE_S, LAGGING_S = INTERVAL + 60, 2 * INTERVAL + 60

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
    """The tail, parsed leniently. A line being appended as we read it is normal and is
    simply skipped — the next frame gets it."""
    try:
        with open(LEDGER, encoding="utf-8") as f:
            lines = f.readlines()[-n:]
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def fmt_age(sec):
    if sec < 60:
        return f"{int(sec)}s"
    if sec < 3600:
        return f"{int(sec // 60)}m{int(sec % 60):02d}s"
    return f"{int(sec // 3600)}h{int((sec % 3600) // 60):02d}m"


def cut(s, n):
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[:n - 1] + "…"


def render(spin, now):
    try:
        width = os.get_terminal_size().columns
    except OSError:
        width = 80
    width = max(48, min(width, 100))

    hb = read_json(HEARTBEAT) or {}
    rows = read_ledger()
    # One ledger, two writers. A row with no `kind` is the worker's: every page written before
    # the interpreter existed has none, so absent means "page" and always will.
    pages = [r for r in rows if r.get("kind", "page") == "page"]
    reads = [r for r in rows if r.get("kind") == "reading"]
    landed = [r for r in pages if r.get("room")]
    failed = [r for r in pages if not r.get("room")]
    flagged = [r for r in landed if r.get("flag")]

    out = [CLEAR]
    clock = time.strftime("%H:%M:%S", time.localtime(now))
    out.append(f"{BOLD}{MINT}STREAM{R} {MINT}{spin}{R}  {LBLUE}{STREAM}{R}"
               f"{' ' * max(1, width - 23 - len(STREAM) - len(clock))}{clock}")
    out.append(LBLUE + "─" * width + R)

    # 1. alive — the heartbeat's age, and nothing else. It says nothing about whether the
    # runs it is counting actually wrote anything.
    if not hb:
        dot, label = LBLUE + "●" + R, LBLUE + "NO HEARTBEAT" + R
        sub = "never run here, or STREAM_DIR is wrong"
    else:
        age = now - (hb.get("ts") or 0)
        if age <= ALIVE_S:
            dot, label = MINT_HI + "●" + R, MINT_HI + "ALIVE" + R
        elif age <= LAGGING_S:
            dot, label = LBLUE + "●" + R, LBLUE + f"QUIET — one turn missed ({INTERVAL}s apart)" + R
        else:
            dot, label = PINK + "●" + R, BOLD + PINK + "STALE — the timer is not firing" + R
        sub = (f"heartbeat {fmt_age(age)} ago · last run "
               f"{'ok' if hb.get('ok') else 'failed'} · {hb.get('room') or '—'}")
    out.append(f"{dot} {label}   {LBLUE}{sub}{R}")

    # 2. progressing — a heartbeat every five minutes with no page under it is the state
    # this whole panel exists to make impossible to miss.
    ok_ts = hb.get("last_ok")
    if ok_ts:
        since = now - ok_ts
        mark = MINT_HI if since <= LAGGING_S else PINK
        out.append(f"  {mark}last page {fmt_age(since)} ago{R}")
    else:
        out.append(f"  {PINK}no page has ever landed{R}")
    if hb and not ok_ts:
        out.append(f"  {PINK}beating but writing nothing — llama down?{R}")
    elif hb.get("ts") and ok_ts and (hb["ts"] - ok_ts) > LAGGING_S:
        out.append(f"  {PINK}beating but writing nothing since {fmt_age(now - ok_ts)} ago{R}")
    out.append("")

    out.append(f"  {LBLUE}{len(landed)} pages on the ledger · {len(flagged)} flagged · "
               f"{len(failed)} runs wrote nothing{R}")

    # The second voice. Its own line and not mixed into the counts above: the interpreter can
    # be dead for a day while the stream is perfectly healthy, and the reverse.
    #
    # It has NO clock — stream.py kickstarts it when a dream lands — so a heartbeat age would
    # say nothing about it. The question that does is whether the last page that landed has a
    # row after it: a note, or a failure to write one.
    today = time.strftime("%Y-%m-%d", time.localtime(now))
    ok = [r for r in reads if not r.get("error")]
    mine = [r for r in ok if time.strftime("%Y-%m-%d", time.localtime(r.get("ts") or 0)) == today]
    bad = [r for r in reads if r.get("error")]
    if reads:
        age = fmt_age(now - (ok[-1].get("ts") or now)) + " ago" if ok else "never"
        marked = sum(r.get("marked") or 0 for r in mine)
        out.append(f"  {MINT_LO}{len(mine)} notes today · last {age} · "
                   f"{marked} passages marked up{R}")
        page_ts = (landed[-1].get("ts") or 0) if landed else 0
        read_ts = reads[-1].get("ts") or 0
        if page_ts and read_ts < page_ts:
            waited = now - page_ts
            # A kick, a cli call and an opus answer are tens of seconds; under two minutes is
            # the note still being written, not a reader that never woke up.
            mark = LBLUE if waited < 120 else PINK
            out.append(f"  {mark}the last dream has no note yet "
                       f"({fmt_age(waited)} since it landed){R}")
        if bad:
            out.append(f"  {PINK}last note failure: {cut(bad[-1].get('error'), width - 26)}"
                       f" ({fmt_age(now - (bad[-1].get('ts') or now))} ago){R}")
    else:
        out.append(f"  {LBLUE}no notes yet — the interpreter has not run here{R}")
    if landed:
        heats = [r.get("temperature") for r in landed[-40:] if r.get("temperature")]
        toks = [r.get("tokens") or 0 for r in landed[-40:]]
        if heats:
            out.append(f"  {LBLUE}last 40 · t {min(heats):g}–{max(heats):g} · "
                       f"{round(sum(toks) / max(1, len(toks)))} tok a page{R}")
    out.append("")

    out.append(f"  {LBLUE}last 8 runs:{R}")
    for r in rows[-8:]:
        when = time.strftime("%H:%M", time.localtime(r.get("ts") or 0))
        if not r.get("room"):
            out.append(f"    {PINK}{when} —  {cut(r.get('error'), width - 16)}{R}")
            continue
        mark = LBLUE if r.get("flag") else MINT_LO
        out.append(f"    {mark}{when} {cut(r.get('room'), 24):<24} t{r.get('temperature')} "
                   f"{r.get('tokens')} tok"
                   f"{'  flag ' + str(r.get('flag')) if r.get('flag') else ''}{R}"
                   f"  {LBLUE}{cut(r.get('seed'), 22)}{R}")
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
