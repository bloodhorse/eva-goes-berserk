#!/usr/bin/env -S uv run --python 3.12
"""naming.py — names for the dreams that were dreamt before names existed.

    uv run --python 3.12 eva/stream/naming.py --unnamed --limit 5
    uv run --python 3.12 eva/stream/naming.py --unnamed --day 2026-09-19

**Opus, never codex** (bekh, 2026-09-22: *i have basically infinite tokens for this… leave
codex alone*). The reader's seat is codex's and codex's limit is the scarce thing here; a
hundred and fifty names off the back catalogue is exactly the job to spend the other family's
tokens on. There is no fallback in either direction: this tool asks opus and nobody else.

**It never writes a note.** Those dreams already have one — opus's from the first day, five of
codex's — and a reading file is the whole reading: the note, the verbatim copy and the marks.
The newest note for a room is the one the page shows, so a naming pass that wrote reading files
would quietly replace every marked copy on the shelf with an empty one. So names go in their
own small store and the api prefers a note's name when there is one.

**The prompt is the reader's own paragraph, read out of `interpreter.txt` at run time** — one
source for what a name is, never a second copy that drifts. If bekh edits that paragraph, this
tool follows him the next time it runs.

A hand tool: one-shot, no launchd, no kick. A failed call is a line on the log and the next
room; a ledger row per name, so what it costs is counted like everything else here.

Env: STREAM_DIR, STREAM_PERSONA, STREAM_NAME_TIMEOUT (120), plus loom's LOOM_SITTINGS.
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
import interpreter  # noqa: E402   the persona file, the name cleaning, the storage paths
import loom  # noqa: E402
import opus  # noqa: E402
import push  # noqa: E402   the mirror, tapped once at the end of a pass

TIMEOUT = int(os.environ.get("STREAM_NAME_TIMEOUT", "120"))

# The one framing line. It says *someone's dreams* and not a machine's, like the persona does
# now: the word "machine" in front of a reader is what turned every note into a portrait of an
# AI (2026-09-21), and this prompt is shorter than the persona and would show it faster.
FRAMING = "You are reading someone's dreams."

SHAPE = """
Answer with the name and nothing else — no preamble, no explanation:

<name>
what comes after "a dream about"
</name>
"""

# The paragraph in bekh's file that says what a name is. Found by its first words, which are
# his: a marker string is a worse contract than the sentence itself, and this way the file
# stays a file he reads rather than one he has to maintain.
NAME_PARA_OPENS = "Last, name the dream."


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def naming_paragraph() -> str:
    """bekh's own naming paragraph, verbatim. Raises ValueError if it is not in his file —
    better a clear stop than a hundred dreams named by a prompt nobody wrote."""
    with open(interpreter.PERSONA, encoding="utf-8") as f:
        persona = f.read()
    for para in persona.split("\n\n"):
        if para.strip().startswith(NAME_PARA_OPENS):
            return para.strip()
    raise ValueError(f"no paragraph starting “{NAME_PARA_OPENS}” in {interpreter.PERSONA}")


def prompt_for(page: dict, paragraph: str) -> str:
    """Framing, his paragraph, the shape, the dream. **No seed and no labels** — the same rule
    the reader lives by: with the seed in sight the voice narrates the plumbing instead of
    reading the dream."""
    return "\n\n".join([FRAMING, paragraph, SHAPE.strip(),
                        "--- the dream ---\n\n" + (page.get("text") or "")]) + "\n"


# ---- the store ---------------------------------------------------------------------------------
# `names/<YYYY-MM-DD>.json` = {room: name}, a day of rooms to a file, next to the readings and
# gitignored with them. Its own store and not a field on a reading file, because a reading is a
# whole reading and this tool has no business rewriting one.

def store_path(room: str) -> str:
    """By the ROOM's date and not today's, so a run in the small hours files yesterday's dreams
    under yesterday and the store reads like the shelf."""
    return os.path.join(interpreter.STREAM, "names", room.split("/")[1] + ".json")


def load_store(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def save_store(path: str, names: dict) -> None:
    """Rewritten after every single name, atomically: a run of a hundred that is killed at
    ninety has ninety names on the shelf and nothing half-written."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(names, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)


def named_already() -> set[str]:
    """Every room that already has a name from either source — a note's, or this store's."""
    have = set()
    for d in interpreter.readings():
        names = d.get("names")
        if isinstance(names, dict):
            have |= {room for room, name in names.items() if isinstance(name, str) and name}
    root = os.path.join(interpreter.STREAM, "names")
    try:
        days = sorted(os.listdir(root))
    except OSError:
        days = []
    for fname in days:
        if fname.endswith(".json"):
            have |= {room for room, name in load_store(os.path.join(root, fname)).items()
                     if isinstance(name, str) and name}
    return have


def wanted(day: str, limit: int) -> list[str]:
    """The unflagged, unnamed stream rooms, OLDEST first — the back catalogue is read forward,
    and a run that is cut short has done the oldest end of it."""
    have = named_already()
    out = []
    for name in reversed(loom.stream_room_names()):          # oldest first
        if day and not name.startswith(f"stream/{day}/"):
            continue
        if name in have:
            continue
        page = loom.stream_page(name)
        if page is None or page.get("flag"):
            continue
        out.append(name)
        if limit and len(out) >= limit:
            break
    return out


def run(rooms: list[str], paragraph: str) -> int:
    done = 0
    for room in rooms:
        page = loom.stream_page(room)
        if page is None:
            log(f"{room} · no such dream")
            continue
        started = time.time()
        try:
            answer, usage = opus.ask(prompt_for(page, paragraph), TIMEOUT)
        except ValueError as exc:
            log(f"{room} · skipped · {exc}")
            continue
        m = interpreter.NAME_RE.search(answer)
        # The tag or nothing. Taking a bare answer as the name looks generous and files
        # sentences like "i would rather not name it" as the name of a dream — and a name is
        # the one thing here that gets read out of context, in a list, with nothing to correct
        # it. Everything on this page is asked for in tags for the same reason.
        name = interpreter.clean_name(m.group(2)) if m else ""
        if not name:
            log(f"{room} · no <name> in the answer")
            continue
        path = store_path(room)
        names = load_store(path)
        names[room] = name
        save_store(path, names)
        seconds = round(time.time() - started, 1)
        # `kind: "name"`, on the shared ledger. The reader's own writer is reused and the kind
        # overridden — one place opens that file for appending, whoever is writing to it.
        interpreter.ledger({"kind": "name", "rooms": [room], "name": name,
                            "model": opus.MODEL, "seconds": seconds, "usage": usage})
        done += 1
        log(f"{room} · “{name}” · {seconds}s · " + opus.line(usage))
    log(f"{done} of {len(rooms)} named")
    # Once for the pass, not once per name: this is a hand tool that can run a hundred and
    # fifty dreams deep, and a push per name would be a hundred and fifty rsyncs of one file.
    if done:
        push.now()
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="naming.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--unnamed", action="store_true",
                    help="every unflagged dream with no name yet, oldest first")
    ap.add_argument("--room", action="append", default=[], help="one room; repeatable")
    ap.add_argument("--day", default="", help="only this YYYY-MM-DD")
    ap.add_argument("--limit", type=int, default=0, help="stop after this many")
    a = ap.parse_args(argv[1:])

    try:
        paragraph = naming_paragraph()
    except (OSError, ValueError) as exc:
        log(str(exc))
        return 2
    rooms = list(a.room)
    if a.unnamed:
        rooms += [r for r in wanted(a.day, a.limit) if r not in rooms]
        if not rooms:
            # The end state of the back catalogue, and not an error: a pass that has nothing
            # left to do should be runnable again for free.
            log("every dream has a name")
            return 0
    if not rooms:
        log("nothing to name: give --unnamed or --room")
        return 2
    return run(rooms, paragraph)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
