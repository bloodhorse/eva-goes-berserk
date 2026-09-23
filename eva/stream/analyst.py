#!/usr/bin/env -S uv run --python 3.12
"""analyst.py — the one who has read every dream, writing a portrait of the dreamer.

    uv run --python 3.12 eva/stream/analyst.py --once
    uv run --python 3.12 eva/stream/analyst.py --once --seat blind --start last:10
    uv run --python 3.12 eva/stream/analyst.py --show --seat blind

bekh's fourth voice (2026-09-23): opus reading ALL the dreams, oldest first, and rewriting a
psychological portrait of whoever dreams them — the themes, and just as much the verbal tics.

**His memory is a cli session, never a summary** (bekh's law, not negotiable). Each run hands
the next batch of dreams over as the next user turn of ONE resumed `claude` session, so every
dream he has ever been handed is still in his context word for word. A tic is a turn of phrase
coming back across forty dreams; a digest of the first thirty — his own or ours — keeps the
themes and drops exactly the phrasing he is hunting. So there is no memory block and no previous
portrait in the prompt: both are already in the session.

**Seats.** A seat is one session with one persona, everything under `portraits/<seat>/`. They
exist so bekh can run two persona lines over the same dreams side by side — `analyst.txt`
(told the dreamer is nemo; his pick on 2026-09-23) against `analyst-blind.txt`. The persona is
sent once, in the session's first turn, and never again.

**The ceiling.** A full session is compacted by the cli on its own, and compaction is precisely
the reduction bekh forbade — so the tool refuses before the cli gets the chance, at
`STREAM_ANALYST_CONTEXT_MAX` tokens, and the answer is a new seat.

Like every voice here he sees nemo's text only: no seed, no reader's note, no name, no story —
each dream under the date and minute it was written.

Env: STREAM_DIR (default shelf/stream/), STREAM_ANALYST_SEAT (analyst), STREAM_ANALYST_PERSONA
(eva/stream/analyst.txt), STREAM_ANALYST_EVERY (10), STREAM_ANALYST_CONTEXT_MAX (150000),
STREAM_ANALYST_TIMEOUT (600), plus loom's LOOM_SITTINGS.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))              # eva/stream
EVA = os.path.dirname(HERE)
for d in (os.path.join(EVA, "server"), os.path.join(EVA, "cli"), HERE):
    if d not in sys.path:
        sys.path.insert(0, d)
import loom  # noqa: E402
import opus  # noqa: E402   one call, one usage block, one place the budget is counted
import push  # noqa: E402   the mirror, tapped the moment a portrait lands

STREAM = os.environ.get("STREAM_DIR", os.path.join(loom.SHELF, "stream"))
PORTRAITS = os.path.join(STREAM, "portraits")
LEDGER = os.path.join(STREAM, "ledger.jsonl")
SEAT = os.environ.get("STREAM_ANALYST_SEAT", "analyst")
PERSONA = os.environ.get("STREAM_ANALYST_PERSONA", os.path.join(HERE, "analyst.txt"))
# Ten dreams a turn: fewer and a run is mostly the cli's overhead and a portrait rewritten for
# one new scrap; more and a backlog of a day is a handful of enormous turns.
EVERY = int(os.environ.get("STREAM_ANALYST_EVERY", "10"))
# Under the point where the cli would compact the session by itself — see the module doc. A
# dream is ~250 tokens, so this is roughly five hundred dreams in one seat.
CONTEXT_MAX = int(os.environ.get("STREAM_ANALYST_CONTEXT_MAX", "150000"))
# Longer than the other voices': a resumed turn re-reads the whole session, and at a hundred
# thousand tokens of dreams five minutes is not generous.
TIMEOUT = int(os.environ.get("STREAM_ANALYST_TIMEOUT", "600"))

PORTRAIT_RE = re.compile(r"<portrait>(.*?)</portrait>", re.S | re.I)
ROOM_RE = re.compile(r"(\d{4}-\d{2}-\d{2})/(\d{2})(\d{2})(?:-\d+)?$")
SEAT_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

SHAPE = """
Answer with the whole portrait, rewritten, and nothing else — no preamble, no code fences:

<portrait>
the portrait as it stands now
</portrait>
"""

AGAIN = "The portrait again, rewritten whole, inside <portrait></portrait>."


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", file=sys.stderr, flush=True)


def ledger(row: dict) -> None:
    os.makedirs(STREAM, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "kind": "portrait", **row},
                           ensure_ascii=False) + "\n")


def write_json(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


# ---- the seat ---------------------------------------------------------------------------------

def seat_dir(seat: str) -> str:
    return os.path.join(PORTRAITS, seat)


def load_session(seat: str) -> dict | None:
    try:
        with open(os.path.join(seat_dir(seat), "session.json"), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    return d if isinstance(d, dict) else None


def save_session(seat: str, state: dict) -> None:
    write_json(os.path.join(seat_dir(seat), "session.json"), state)


def live(state: dict | None) -> bool:
    """A seat is live once a session exists to resume. A state file with a watermark and no id
    is a start that has not landed yet — `--start` may still move it."""
    return bool(state and state.get("session_id"))


def version_files(seat: str) -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(seat_dir(seat)):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for fname in filenames:
            if fname.endswith(".json") and fname != "session.json":
                out.append(os.path.join(dirpath, fname))
    return sorted(out)


def latest(seat: str) -> dict | None:
    best = None
    for path in version_files(seat):
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(d, dict) and isinstance(d.get("text"), str):
            if best is None or (d.get("ts") or 0) >= (best.get("ts") or 0):
                best = d
    return best


def version_path(seat: str, when_ts: float) -> str:
    lt = time.localtime(when_ts)
    day = os.path.join(seat_dir(seat), time.strftime("%Y-%m-%d", lt))
    stem = time.strftime("%H%M", lt)
    # The sleeper's rule, no ceiling on the suffix: a backlog chewed by hand lands several
    # portraits inside one minute, and a ceiling is where the tenth overwrites the ninth.
    i = 1
    while True:
        path = os.path.join(day, stem + ("" if i == 1 else f"-{i}") + ".json")
        if not os.path.exists(path):
            return path
        i += 1


# ---- which dreams -------------------------------------------------------------------------------

def unflagged(names: list[str]) -> list[str]:
    """The dreams worth handing over, in the order given. The filter's column is honoured here
    as everywhere: a licence footer is not something the dreamer dreamt."""
    out = []
    for name in names:
        page = loom.stream_page(name)
        if page is not None and not page.get("flag"):
            out.append(name)
    return out


def start_mark(spec: str) -> str:
    """The watermark that makes `spec` the first dream read: the room just below it on the
    shelf, or "" when it is the oldest. Raises ValueError with the message for bekh."""
    names = sorted(loom.stream_room_names())                 # oldest first
    if spec.startswith("last:"):
        try:
            k = int(spec[5:])
        except ValueError:
            raise ValueError(f"--start {spec}: last:K wants a number")
        if k < 1:
            raise ValueError(f"--start {spec}: K is at least 1")
        # Walk from the newest and open only as many rooms as it takes to find K good ones.
        good = []
        for name in reversed(names):
            if unflagged([name]):
                good.append(name)
                if len(good) == k:
                    break
        if not good:
            raise ValueError("--start: no unflagged dream on the shelf")
        room = good[-1]                                       # fewer than K: start at the oldest
    else:
        room = spec
        if room not in names:
            raise ValueError(f"--start {spec}: no such stream room")
    i = names.index(room)
    return names[i - 1] if i else ""


def batch(covered: str, n: int, partial: bool) -> list[dict]:
    """The oldest unflagged dreams above the watermark, at most n; [] when there are fewer than
    n and `partial` is off. Oldest first, unlike the reader: the backlog is the point."""
    out = []
    for name in sorted(r for r in loom.stream_room_names() if r > covered):
        page = loom.stream_page(name)
        if page is None or page.get("flag"):
            continue
        out.append(page)
        if len(out) == n:
            return out
    return out if partial else []


# ---- the prompt ---------------------------------------------------------------------------------

def header(room: str) -> str:
    """`[2026-09-22 17:11]` off `stream/2026-09-22/1711` — the name IS when it was written, and
    a `-2` is a hand run inside the same minute, so it gets the same stamp."""
    m = ROOM_RE.search(room)
    if not m:
        return f"[{room}]"
    return f"[{m.group(1)} {m.group(2)}:{m.group(3)}]"


def material(pages: list[dict]) -> str:
    """Each dream under its stamp, the text exactly as nemo left it — ragged edges, stray
    brackets, all of it, because the tics are in exactly what a tidier would take out."""
    return "\n\n".join(header(p["room"]) + "\n" + (p.get("text") or "") for p in pages)


def first_prompt(persona: str, pages: list[dict]) -> str:
    return "\n\n".join([persona.rstrip("\n"), SHAPE.strip(),
                        "--- the dreams ---\n\n" + material(pages)]) + "\n"


def next_prompt(pages: list[dict]) -> str:
    return (f"--- {len(pages)} more dreams ---\n\n" + material(pages) + "\n\n" + AGAIN + "\n")


def parse(answer: str) -> str:
    m = PORTRAIT_RE.search(answer)
    if not m or not m.group(1).strip():
        raise ValueError("no <portrait> in the answer")
    return m.group(1).strip()


def context_of(usage: dict) -> int:
    """How big the session is now: everything that went in on this call. Output is left out —
    it becomes input on the next call and is counted there."""
    return (int(usage.get("input_tokens") or 0) + int(usage.get("cache_read_input_tokens") or 0)
            + int(usage.get("cache_creation_input_tokens") or 0))


# ---- one run -------------------------------------------------------------------------------------

def run_once(seat: str, persona_path: str, n: int, partial: bool, start: str | None,
             new: bool) -> int:
    state = load_session(seat)

    if new and os.path.isdir(seat_dir(seat)):
        # Binned, never deleted: an old seat's versions are the record of what he saw then.
        bin_ = os.path.join(PORTRAITS, ".trash", time.strftime("%Y%m%d-%H%M%S"), seat)
        os.makedirs(os.path.dirname(bin_), exist_ok=True)
        os.replace(seat_dir(seat), bin_)
        log(f"portrait · {seat} moved to {os.path.relpath(bin_, STREAM)}")
        state = None
    elif start is not None and live(state):
        print(f"seat {seat} already has a session ({state['session_id']}); --new bins it "
              f"and starts over", file=sys.stderr)
        return 2

    if start is not None:
        try:
            mark = start_mark(start)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        # Written before the call, so a first call that fails still leaves the start where bekh
        # put it and the next plain --once picks up from there.
        state = {"session_id": "", "persona": persona_path, "started": None, "covered": mark,
                 "dreams": 0, "context": 0, "model": None}
        save_session(seat, state)

    resuming = live(state)
    covered = (state or {}).get("covered") or ""
    pages = batch(covered, n, partial)
    if not pages:
        if start is not None:
            print(f"fewer than {n} dreams from there; the start is kept, --partial takes "
                  f"what is there", file=sys.stderr)
        # Otherwise quietly and with no row: too few new dreams is the ordinary state between
        # landings, and a row every time would bury the real ones.
        return 0

    # After the batch and not before it, so a full seat with nothing new stays as quiet as any
    # other; the refusal is for a call that would otherwise have been made.
    held = int((state or {}).get("context") or 0)
    if resuming and held >= CONTEXT_MAX:
        msg = f"session at {held} tokens, over the ceiling of {CONTEXT_MAX} — start a new seat"
        print(f"portrait · {seat} · {msg}", file=sys.stderr)
        ledger({"seat": seat, "error": msg, "context": held})
        return 0

    if resuming:
        prompt = next_prompt(pages)
    else:
        try:
            with open(persona_path, encoding="utf-8") as f:
                persona = f.read()
        except OSError as exc:
            log(f"no persona at {persona_path}: {exc}")
            ledger({"seat": seat, "error": f"no persona file: {exc}"})
            return 0
        prompt = first_prompt(persona, pages)

    rooms = [p["room"] for p in pages]
    started = time.time()
    try:
        answer, usage = opus.ask(prompt, TIMEOUT, resume=state["session_id"] if resuming else None)
    except ValueError as exc:
        log(f"portrait · {seat} · {exc}")
        ledger({"seat": seat, "rooms": len(rooms), "error": str(exc),
                "seconds": round(time.time() - started, 1)})
        return 0
    sid = opus.SESSION
    if not sid:
        # Without an id there is nothing to resume, and the next run would start him over with
        # no memory — the one outcome this voice exists to avoid. Nothing is stored.
        log(f"portrait · {seat} · the cli reported no session id")
        ledger({"seat": seat, "rooms": len(rooms), "error": "the cli reported no session id",
                "seconds": round(time.time() - started, 1)})
        return 0
    if resuming and sid != state["session_id"]:
        log(f"portrait · {seat} · the cli answered from session {sid}, "
            f"not {state['session_id']} — following it")

    now = time.time()
    total = int((state or {}).get("dreams") or 0) + len(pages)
    ctx = context_of(usage)
    # The session moves on whether or not the answer parses: the cli answered, so these dreams
    # ARE in his context now. Holding the watermark back would hand them over a second time and
    # he would read them twice — a garbage answer costs one portrait, never a duplicate.
    save_session(seat, {"session_id": sid,
                        "persona": (state or {}).get("persona") or persona_path,
                        "started": (state or {}).get("started") if resuming else now,
                        "covered": rooms[-1], "dreams": total, "context": ctx,
                        "model": opus.MODEL})
    try:
        text = parse(answer)
    except ValueError as exc:
        log(f"portrait · {seat} · {exc}")
        ledger({"seat": seat, "session_id": sid, "rooms": len(rooms), "dreams": total,
                "context": ctx, "error": str(exc), "seconds": round(now - started, 1),
                "usage": usage})
        return 0

    obj = {"ts": now, "seat": seat, "session_id": sid, "rooms": rooms, "dreams": total,
           "text": text, "model": opus.MODEL, "seconds": round(now - started, 1),
           "usage": usage, "context": ctx}
    path = version_path(seat, now)
    write_json(path, obj)
    ledger({"seat": seat, "session_id": sid, "rooms": len(rooms), "dreams": total,
            "context": ctx, "model": opus.MODEL, "seconds": obj["seconds"], "usage": usage})
    log(f"portrait · {os.path.relpath(path, STREAM)} · {seat} · {len(rooms)} dreams ({total}) · "
        f"{ctx} ctx · {obj['seconds']}s · " + opus.line(usage))
    print(text)
    push.now()
    return 0


def show(seat: str) -> int:
    v = latest(seat)
    if v is None:
        print(f"no portrait in seat {seat} yet", file=sys.stderr)
        return 1
    state = load_session(seat) or {}
    print(f"{seat} · {v.get('dreams')} dreams · {state.get('context', v.get('context'))} ctx",
          file=sys.stderr)
    print(v["text"])
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="analyst.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true",
                    help="hand over one batch and rewrite the portrait — the only run mode")
    ap.add_argument("--show", action="store_true",
                    help="print the seat's latest portrait and exit, no call")
    ap.add_argument("--seat", default=SEAT, help=f"the session to read in (default {SEAT})")
    ap.add_argument("--persona", default=PERSONA,
                    help="persona file, read only when a session starts")
    ap.add_argument("--n", type=int, default=EVERY, help=f"dreams per batch (default {EVERY})")
    ap.add_argument("--partial", action="store_true",
                    help="take whatever is there when fewer than --n are new")
    ap.add_argument("--start", metavar="ROOM|last:K",
                    help="start the seat at ROOM, or at the K-th newest unflagged dream")
    ap.add_argument("--new", action="store_true",
                    help="bin the seat's folder to portraits/.trash/ and start it over")
    a = ap.parse_args(argv[1:])
    if not SEAT_RE.match(a.seat):
        print(f"--seat {a.seat!r}: letters, digits, - and _ only", file=sys.stderr)
        return 2
    if a.n < 1:
        print("--n is at least 1", file=sys.stderr)
        return 2
    if a.show:
        return show(a.seat)
    if not a.once:
        ap.print_help(sys.stderr)
        return 2
    return run_once(a.seat, a.persona, a.n, a.partial, a.start, a.new)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
