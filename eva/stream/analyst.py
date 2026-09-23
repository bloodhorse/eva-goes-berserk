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

Like every voice here he sees the dreamer's text only: no seed, no reader's note, no name, no
story — each dream under the date and minute it was written and, since two models write the pages
in turn, the one that wrote it: `[2026-09-23 18:58 · gpt2]`.

**The remark** (bekh, 2026-09-23): beside the portrait, one sentence he would say out loud about
the dreamer right now. It is what the feed shows on the card every ten dreams — the portrait is
the manuscript behind it — so it is his own voice, never a summary of the portrait.

**The clock is the tap**: `com.bekh.eva-stream-analyst` has no interval, and stream.py kickstarts
it with the other voices when a page lands. Nine landings in ten that is a quiet no-op — fewer
than ten new dreams above the watermark — and the tenth is a portrait.

Env: STREAM_DIR (default shelf/stream/), STREAM_ANALYST_SEAT (analyst — the loom reads it too:
only this seat's portraits reach /api/stream), STREAM_ANALYST_PERSONA
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
import codex  # noqa: E402   the third door: GPT through codex, one thread resumed
import deepseek  # noqa: E402   the second door: v3.2 over openrouter, the transcript kept here
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
# **Two doors, one seat each** (bekh, 2026-09-23: fresh blood). `opus` is the claude cli in one
# resumed session; `deepseek` is v3.2 over openrouter with the transcript kept in the seat as
# `messages.json`, sent whole every call. A seat is born with a door and keeps it — a session
# can't move houses. The prompts are the same to the byte; only the door differs.
DOORS = ("opus", "fable", "deepseek", "codex")
# `fable` is the opus door with the model flipped: the same cli, the same resumed session, on
# bekh's fable limit instead — his ask the same night, unhappy with opus's prose.
DOOR = os.environ.get("STREAM_ANALYST_DOOR", "opus")
# The third door: GPT through codex, one recorded thread resumed every call (`codex exec
# resume <thread>`), the same countermanded seat folder the reader uses. bekh's pick for it
# (2026-09-23): `gpt-5.6-sol`. It draws on his codex window, which is the scarce thing here,
# and a resumed turn replays the whole thread plus the harness's ~18k every call.
CODEX_MODEL = os.environ.get("STREAM_ANALYST_CODEX_MODEL", "gpt-5.6-sol")
CODEX_EFFORT = os.environ.get("STREAM_ANALYST_CODEX_EFFORT", "low")
# Under the point where the seat's window runs out — for opus, where the cli would compact the
# session by itself (see the module doc); for deepseek, a 128k window. Measured 2026-09-23: a
# dream costs ~420 tokens of context with the portraits in the session, so this is ~350 dreams
# in an opus seat and ~280 in a deepseek one. One env var overrides either.
CONTEXT_MAX = {"opus": 150000, "fable": 150000, "deepseek": 120000, "codex": 180000}
if os.environ.get("STREAM_ANALYST_CONTEXT_MAX"):
    CONTEXT_MAX = dict.fromkeys(DOORS, int(os.environ["STREAM_ANALYST_CONTEXT_MAX"]))
# The transcript-kept door has no id; this stands in for one so `live()` and every reader of
# session.json see a seat that can be resumed.
LOCAL_SESSION = "messages"
# Longer than the other voices': a resumed turn re-reads the whole session, and at a hundred
# thousand tokens of dreams five minutes is not generous.
TIMEOUT = int(os.environ.get("STREAM_ANALYST_TIMEOUT", "600"))

PORTRAIT_RE = re.compile(r"<portrait>(.*?)</portrait>", re.S | re.I)
REMARK_RE = re.compile(r"<remark>(.*?)</remark>", re.S | re.I)
ROOM_RE = re.compile(r"(\d{4}-\d{2}-\d{2})/(\d{2})(\d{2})(?:-\d+)?$")
SEAT_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

SHAPE = """
Answer with the whole portrait, rewritten, then one remark, and nothing else — no preamble, no
code fences:

<portrait>
the portrait as it stands now
</portrait>
<remark>
one sentence, two at most, that you would say out loud about the dreamer right now — your own
words to somebody beside you, not a summary of the portrait
</remark>
"""

AGAIN = ("The portrait again, rewritten whole, inside <portrait></portrait>, "
         "then your remark inside <remark></remark>.")


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", file=sys.stderr, flush=True)


def ledger(row: dict) -> None:
    os.makedirs(STREAM, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "kind": "portrait", **row},
                           ensure_ascii=False) + "\n")


def write_json(path: str, obj: dict | list) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


write_json_list = write_json


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

def header(room: str, model: str | None = None) -> str:
    """`[2026-09-22 17:11]` off `stream/2026-09-22/1711` — the name IS when it was written, and
    a `-2` is a hand run inside the same minute, so it gets the same stamp.

    With the dreamer after it when the page says who wrote it — `[2026-09-23 18:58 · gpt2]` —
    because since 2026-09-23 two models write the pages in turn, and a tic he pins on the one
    dreamer that turns out to be only the other one's is a wrong portrait. `model` is
    `loom.stream_model`'s short name, so a page from before the seats (nemo's file name on it)
    reads `nemo` like tonight's. No stamp at all and the header is what it always was."""
    m = ROOM_RE.search(room)
    stamp = f"{m.group(1)} {m.group(2)}:{m.group(3)}" if m else room
    return f"[{stamp} · {model}]" if model else f"[{stamp}]"


def material(pages: list[dict]) -> str:
    """Each dream under its stamp, the text exactly as the dreamer left it — ragged edges, stray
    brackets, all of it, because the tics are in exactly what a tidier would take out."""
    return "\n\n".join(header(p["room"], p.get("model")) + "\n" + (p.get("text") or "")
                        for p in pages)


def first_prompt(persona: str, pages: list[dict]) -> str:
    return "\n\n".join([persona.rstrip("\n"), SHAPE.strip(),
                        "--- the dreams ---\n\n" + material(pages)]) + "\n"


def next_prompt(pages: list[dict]) -> str:
    return (f"--- {len(pages)} more dreams ---\n\n" + material(pages) + "\n\n" + AGAIN + "\n")


def parse(answer: str) -> tuple[str, str]:
    """(the portrait, the remark). The portrait is the run: without it there is nothing to
    store. The remark is lenient — missing, empty or unclosed it is "", never a failed run, since
    a portrait that landed with no line is still the portrait, and the card simply has no words."""
    m = PORTRAIT_RE.search(answer)
    if not m or not m.group(1).strip():
        raise ValueError("no <portrait> in the answer")
    return m.group(1).strip(), remark(answer)


def remark(answer: str) -> str:
    """One line for the card: wrapped lines joined, and quotes round the whole of it taken off,
    because the card and the narration put their own round it."""
    m = REMARK_RE.search(answer)
    if not m:
        return ""
    line = " ".join(m.group(1).split())
    if len(line) >= 2 and line[0] + line[-1] in ('""', "“”", "''", "‘’"):
        line = line[1:-1].strip()
    return line


def context_of(usage: dict) -> int:
    """How big the session is now: everything that went in on this call. Output is left out —
    it becomes input on the next call and is counted there. Opus's door reports three counters,
    deepseek's one; a usage block has one shape or the other."""
    if "prompt_tokens" in usage:
        return int(usage.get("prompt_tokens") or 0)
    return (int(usage.get("input_tokens") or 0) + int(usage.get("cache_read_input_tokens") or 0)
            + int(usage.get("cache_creation_input_tokens") or 0))


# ---- the transcript-kept session (the deepseek door) ------------------------------------------

def messages_path(seat: str) -> str:
    return os.path.join(seat_dir(seat), "messages.json")


def load_messages(seat: str) -> list[dict]:
    try:
        with open(messages_path(seat), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return []
    return d if isinstance(d, list) else []


def whole_answer(text: str) -> bool:
    """A complete answer ends on the remark's closing tag; one cut short gets a rethrow."""
    return text.rstrip().endswith("</remark>")


# ---- one run -------------------------------------------------------------------------------------

def run_once(seat: str, persona_path: str, n: int, partial: bool, start: str | None,
             new: bool, door: str = DOOR) -> int:
    state = load_session(seat)

    if live(state) and not new and (state.get("door") or "opus") != door:
        # A session is one door's: the cli's id means nothing to the router and the transcript
        # means nothing to the cli. --new is the only way across.
        print(f"seat {seat} is a {state.get('door') or 'opus'} seat; --door {door} needs --new",
              file=sys.stderr)
        return 2

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
        state = {"session_id": "", "door": door, "persona": persona_path, "started": None,
                 "covered": mark, "dreams": 0, "context": 0, "model": None}
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
    if resuming and held >= CONTEXT_MAX[door]:
        msg = f"session at {held} tokens, over the ceiling of {CONTEXT_MAX[door]} — start a new seat"
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
        if door == "deepseek":
            # The whole conversation goes over every time; the answer is appended to the
            # transcript before anything is parsed, for the same reason the watermark moves
            # below: what was sent is in the session now, parse or no parse.
            msgs = (load_messages(seat) if resuming else []) + [{"role": "user", "content": prompt}]
            answer, usage = deepseek.ask(msgs, TIMEOUT, whole=whole_answer)
            os.makedirs(seat_dir(seat), exist_ok=True)
            write_json_list(messages_path(seat), msgs + [{"role": "assistant", "content": answer}])
            sid, model = LOCAL_SESSION, deepseek.MODEL
        elif door == "codex":
            answer, usage = codex.ask(prompt, TIMEOUT, resume=state["session_id"] if resuming else "",
                                      model=CODEX_MODEL, effort=CODEX_EFFORT)
            sid, model = codex.SESSION, "codex:" + CODEX_MODEL
        else:
            answer, usage = opus.ask(prompt, TIMEOUT,
                                     resume=state["session_id"] if resuming else None,
                                     model="fable" if door == "fable" else "")
            sid, model = opus.SESSION, opus.MODEL
    except ValueError as exc:
        log(f"portrait · {seat} · {exc}")
        ledger({"seat": seat, "door": door, "rooms": len(rooms), "error": str(exc),
                "seconds": round(time.time() - started, 1)})
        return 0
    if not sid:
        # Without an id there is nothing to resume, and the next run would start him over with
        # no memory — the one outcome this voice exists to avoid. Nothing is stored.
        log(f"portrait · {seat} · the cli reported no session id")
        ledger({"seat": seat, "door": door, "rooms": len(rooms),
                "error": "the cli reported no session id",
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
    save_session(seat, {"session_id": sid, "door": door,
                        "persona": (state or {}).get("persona") or persona_path,
                        "started": (state or {}).get("started") if resuming else now,
                        "covered": rooms[-1], "dreams": total, "context": ctx,
                        "model": model})
    try:
        text, line = parse(answer)
    except ValueError as exc:
        log(f"portrait · {seat} · {exc}")
        ledger({"seat": seat, "door": door, "session_id": sid, "rooms": len(rooms),
                "dreams": total, "context": ctx, "error": str(exc),
                "seconds": round(now - started, 1), "usage": usage})
        return 0

    obj = {"ts": now, "seat": seat, "door": door, "session_id": sid, "rooms": rooms,
           "dreams": total, "text": text, "line": line, "model": model,
           "seconds": round(now - started, 1), "usage": usage, "context": ctx}
    path = version_path(seat, now)
    write_json(path, obj)
    # `line` on the row too, so the ledger reads as the remarks in order and `eva go` can say
    # one out loud as it lands.
    ledger({"seat": seat, "door": door, "session_id": sid, "rooms": len(rooms), "dreams": total,
            "line": line, "context": ctx, "model": model, "seconds": obj["seconds"],
            "usage": usage})
    told = {"deepseek": deepseek.line, "codex": codex.line}.get(door, opus.line)(usage)
    log(f"portrait · {os.path.relpath(path, STREAM)} · {seat} · {len(rooms)} dreams ({total}) · "
        f"{ctx} ctx · {obj['seconds']}s · {model} · " + told)
    print(text)
    if line:
        print("\n" + line)
    # The mirror, the moment it lands: the portrait rides on a page in /api/stream, and the
    # mini serves that page to dreamshit. Without this the card waits up to a minute.
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
    if v.get("line"):
        print("\n" + v["line"])
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
    ap.add_argument("--door", choices=DOORS, default=DOOR,
                    help=f"who sits in the seat: opus (the cli, one resumed session) or "
                         f"deepseek (v3.2 over openrouter, the transcript kept here); "
                         f"default {DOOR}")
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
    return run_once(a.seat, a.persona, a.n, a.partial, a.start, a.new, a.door)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
