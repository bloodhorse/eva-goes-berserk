#!/usr/bin/env -S uv run --python 3.12
"""reread.py — have codex read dreams that already have a note, by hand.

    uv run --python 3.12 eva/stream/reread.py --last 5
    uv run --python 3.12 eva/stream/reread.py --room stream/2026-09-21/1711 --wait-below 50

The reader (`interpreter.py`) never goes back: it reads the newest dream above its watermark
and nothing else, because the stream is disposable. This is the hand tool for the one case
that wants the opposite — the seat changed family (opus → codex, 2026-09-21) and bekh wanted
the last few dreams on the page read by the new reader too.

It writes an ordinary reading file through `interpreter.py`'s own functions, so nothing else
has to know about it: the server reads the readings in name order and a later file simply
replaces an earlier one for the same room, on the page and nowhere else — the older note stays
on the shelf. **Codex only, no fallback**: a re-read that quietly fell back to opus would put
the old family's note where the new one was asked for, which is the opposite of the job; a room
codex cannot read is skipped and said so.

`--wait-below N` polls the same usage cache the guard reads and starts only when the
five-hour codex window is under N percent — the window, not the week, is the ceiling that
bites (22 plates in 90 minutes tripped it at 80% while the week stood at 19%).
"""

from __future__ import annotations

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
EVA = os.path.dirname(HERE)
for d in (os.path.join(EVA, "server"), os.path.join(EVA, "cli"), HERE):
    if d not in sys.path:
        sys.path.insert(0, d)
import codex  # noqa: E402
import interpreter  # noqa: E402
import loom  # noqa: E402


def say(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def wait_below(pct: float, hours: float) -> bool:
    """True once the session window reads under `pct`. No numbers is not a green light."""
    deadline = time.time() + hours * 3600
    while time.time() < deadline:
        u, why = codex.usage()
        if u is not None and u["session"] < pct:
            say(f"codex window at {u['session']:g}% — going")
            return True
        say(f"waiting · {why or 'codex window at %g%%' % u['session']}")
        time.sleep(120)
    return False


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="reread.py", description=__doc__.splitlines()[0])
    ap.add_argument("--room", action="append", default=[], help="stream/<date>/<HHMM>; repeatable")
    ap.add_argument("--last", type=int, default=0, help="the newest N unflagged dreams")
    ap.add_argument("--wait-below", type=float, default=0.0,
                    help="start only when the five-hour codex window is under this percent")
    ap.add_argument("--max-wait-hours", type=float, default=6.0)
    a = ap.parse_args(argv[1:])

    rooms = list(a.room)
    if a.last:
        newest = [n for n in loom.stream_room_names()
                  if (loom.stream_page(n) or {}).get("flag") is None
                  and loom.stream_page(n) is not None][: a.last]
        rooms += [n for n in reversed(newest) if n not in rooms]      # oldest first
    if not rooms:
        say("nothing to read: give --room or --last")
        return 2
    if a.wait_below and not wait_below(a.wait_below, a.max_wait_hours):
        say("gave up waiting for the codex window")
        return 1

    with open(interpreter.PERSONA, encoding="utf-8") as f:
        persona = f.read()
    done = 0
    for name in rooms:
        page = loom.stream_page(name)
        if page is None:
            say(f"{name} · no such dream")
            continue
        started = time.time()
        try:
            answer, usage = codex.ask(interpreter.prompt_for([page], [], persona),
                                      interpreter.CODEX_TIMEOUT)
            reading, marked, names = interpreter.parse(answer, [page])
        except ValueError as exc:
            say(f"{name} · skipped · {exc}")
            continue
        segments, dropped = {}, 0
        for room, copy in marked.items():
            segments[room], n = interpreter.segments_of(copy)
            dropped += n
        model = "codex:" + codex.MODEL
        obj = {"ts": time.time(), "rooms": [name], "reading": reading, "marked": marked,
               "segments": segments, "names": names, "model": model,
               "seconds": round(time.time() - started, 1), "usage": usage,
               # so a pile of notes read later can tell a second reading from a first
               "reread": True}
        path = interpreter.write_reading(obj)
        interpreter.ledger({"rooms": [name], "marked": len(marked), "chars": len(reading),
                            "dropped": dropped, "name": names.get(name), "model": model,
                            "seconds": obj["seconds"], "usage": usage, "reread": True})
        done += 1
        say(f"{name} · {os.path.relpath(path, interpreter.STREAM)} · "
            f"“{names.get(name) or '—'}” · {obj['seconds']}s · " + codex.line(usage))
    say(f"{done} of {len(rooms)} re-read")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
