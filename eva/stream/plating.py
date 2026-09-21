#!/usr/bin/env -S uv run --python 3.12
"""plating.py — a picture for every dream while the stream is running, with a hand on the limit.

    uv run --python 3.12 eva/stream/plating.py --once

bekh, 2026-09-21: *draw a picture to every dream that's going right now… and keep your hand on
the limit of codex.* Both halves are the job. The painting is `plate.py`'s — this only decides
**which** dream gets one and **whether** the machine may spend anything on it right now.

The fourth job the writer taps when a dream lands (`stream.py`'s `KICK_JOBS`), with no clock of
its own. **One plate per run, at most.** A run is 60–90 seconds and a dream lands every 300, and
launchd will not start a second instance of a job that is already running — so there is no lock
here and no queue: whatever is unpainted when the next dream lands is picked up then.

**The guard is the point.** Every plate spends real money on bekh's codex limit, unattended, at
three in the morning. Nine plates measured about two points of the week — so a plate per dream
is roughly 65–70 points of a week per day: affordable for a half-day experiment, not a way of
life. So this reads the same usage cache his `cu` command shows and refuses to paint over a
ceiling, and refuses just as hard when it cannot see the numbers at all. No numbers is not a
green light; it is the one state where an unattended painter could eat a week.

Env: STREAM_PLATE_SETTLE (90s — how old a dream must be before it is painted, so the reader's
note has landed and the `pieces` prompt has words to work from), STREAM_PLATE_WINDOW (6h — how
far back it will reach, so a job that was off for a day does not wake up and paint three hundred
pictures), STREAM_PLATE_WEEK_MAX (50), STREAM_PLATE_SESSION_MAX (80), STREAM_CODEX_USAGE (the
cache path), plus everything `plate.py` reads.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))              # eva/stream
EVA = os.path.dirname(HERE)
for d in (os.path.join(EVA, "server"), os.path.join(EVA, "cli"), HERE):
    if d not in sys.path:
        sys.path.insert(0, d)
import loom  # noqa: E402
import plate  # noqa: E402   the painting itself, its prompts, its files: all of it is there

SETTLE = int(os.environ.get("STREAM_PLATE_SETTLE", "90"))
WINDOW = int(os.environ.get("STREAM_PLATE_WINDOW", str(6 * 3600)))
WEEK_MAX = int(os.environ.get("STREAM_PLATE_WEEK_MAX", "50"))
SESSION_MAX = int(os.environ.get("STREAM_PLATE_SESSION_MAX", "80"))
# The cache the `cu` command reads, refreshed by its own daemon every few minutes. Read here and
# never written: this process is a consumer of that number, not a second source of it.
USAGE = os.environ.get("STREAM_CODEX_USAGE",
                       os.path.expanduser("~/.cache/claude-usage/codex.json"))
# Past this the cache is not a reading of anything. Six of its refresh intervals.
USAGE_STALE = 1800


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", file=sys.stderr, flush=True)


def ledger(row: dict) -> None:
    os.makedirs(plate.STREAM, exist_ok=True)
    with open(plate.LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "kind": "plating", **row},
                           ensure_ascii=False) + "\n")


def rows() -> list[dict]:
    out = []
    try:
        with open(plate.LEDGER, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if isinstance(d, dict):
                    out.append(d)
    except OSError:
        pass
    return out


# ---- the guard --------------------------------------------------------------------------------

def usage() -> tuple[dict | None, str]:
    """(the numbers, why they cannot be used). One of the two is always empty."""
    try:
        st = os.stat(USAGE)
    except OSError:
        return None, "no usage cache"
    if time.time() - st.st_mtime > USAGE_STALE:
        return None, f"usage cache {int((time.time() - st.st_mtime) // 60)} min stale"
    try:
        with open(USAGE, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None, "usage cache unreadable"
    if not isinstance(d, dict):
        return None, "usage cache is not an object"
    out = {}
    for k in ("week", "session"):
        v = (d.get(k) or {}).get("utilization") if isinstance(d.get(k), dict) else None
        if not isinstance(v, (int, float)):
            return None, f"usage cache has no {k} utilization"
        out[k] = float(v)
    return out, ""


def held_for(u: dict | None, why: str) -> str:
    """Why this run must not paint, or "" to go ahead."""
    if u is None:
        return why
    if u["week"] >= WEEK_MAX:
        return f"week at {u['week']:g}%"
    if u["session"] >= SESSION_MAX:
        return f"session at {u['session']:g}%"
    return ""


def say_held(why: str, u: dict | None) -> None:
    """One row per *state*, not one per run. At a dream every five minutes an unchanged hold
    would write 288 identical lines a day and bury the rows that mean something; the tens digit
    is enough to see the numbers moving without writing down every percent."""
    last = None
    for r in rows():
        if r.get("kind") == "plating":
            last = r
    tens = lambda x: None if x is None else int(x) // 10           # noqa: E731
    now = (why, tens(u and u["week"]), tens(u and u["session"]))
    if last and last.get("held"):
        was = (last["held"], tens(last.get("week")), tens(last.get("session")))
        if was == now:
            return
    ledger({"held": why, "week": u and u["week"], "session": u and u["session"]})


# ---- which dream ------------------------------------------------------------------------------

def when_of(room: str) -> float | None:
    """The room's own clock, off its NAME — `stream/<YYYY-MM-DD>/<HHMM>` is a timestamp, so
    the window can be applied to three hundred rooms without opening one of them."""
    parts = room.split("/")
    if len(parts) != 3:
        return None
    stem = parts[2].split("-")[0]              # a `-2` suffix is the same minute
    try:
        return time.mktime(time.strptime(parts[1] + " " + stem, "%Y-%m-%d %H%M"))
    except ValueError:
        return None


def next_room() -> str | None:
    """The oldest dream that still wants a plate, inside the window and past the settle.

    Oldest first, so a backlog is worked through in the order it was dreamt rather than newest
    first — a picture arriving for a dream he read an hour ago is still the picture for it.
    """
    now = time.time()
    out = []
    for name in loom.stream_room_names():                 # newest first
        at = when_of(name)
        if at is None:
            continue
        age = now - at
        if age > WINDOW:
            break                                          # sorted: everything older is older
        if age < SETTLE:
            continue                                       # the reader has not been past yet
        if os.path.isfile(plate.plate_paths(name)[0]):
            continue
        out.append(name)
    for name in reversed(out):                             # oldest of the eligible ones
        page = loom.stream_page(name)
        if page is None or page.get("flag"):
            continue
        # A stub is a dream like any other — the reader notes it and the sleeper has to fit it
        # into the story, and a lone full stop once gave the best sentence of its hour (bekh,
        # 2026-09-21: "full stop is kinda awesome… it was great not having [a minimum]"). The
        # painter is the one voice that skips it: a picture of fifteen words or fewer is the one
        # expensive thing here, about two thirds of a point of the codex week.
        if len((page.get("text") or "").split()) < MIN_WORDS:
            continue
        return name
    return None


# Dreams shorter than this many words get no plate (and everything else). 0 = paint them too.
MIN_WORDS = int(os.environ.get("STREAM_PLATE_MIN_WORDS", "15"))


def run_once() -> int:
    u, why = usage()
    held = held_for(u, why)
    if held:
        say_held(held, u)
        log(f"holding · {held}")
        return 0

    room = next_room()
    if room is None:
        return 0                                           # nothing to paint is the usual state

    log(f"plating · {room} · week {u['week']:g}% · session {u['session']:g}%")
    # plate.py's own entry point, argv and all: the prompts, the alternation, the hand, the
    # conversion and the `kind: "plate"` row all live there and must have exactly one
    # implementation. This process decides only which room and whether at all.
    code = plate.main(["plate.py", "--room", room])
    ledger({"room": room, "painted": code == 0, "code": code,
            "week": u["week"], "session": u["session"]})
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="plating.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true",
                    help="paint at most one plate and exit — the only mode; stream.py taps "
                         "this job when a dream lands and it has no clock of its own")
    ap.parse_args(argv[1:])
    return run_once()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
