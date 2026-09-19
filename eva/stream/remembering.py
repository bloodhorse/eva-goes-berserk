#!/usr/bin/env -S uv run --python 3.12
"""remembering.py — the sleeper remembering the dream he is in.

    uv run --python 3.12 eva/stream/remembering.py --once

bekh's idea: a second opus that writes a **through-line** through the passages. After the first
one a couple of sentences; with each new one he **rewrites** the account so the new passage
belongs to it — *three sentences, then three different ones, maybe one more* — and after a
couple of hours he starts again.

He is not an outside narrator. He is **the sleeper remembering**: first person, past tense,
half awake while it is still going on. And what he is handed are not separate dreams but
**scenes of one dream he is dreaming** (bekh, 2026-09-19) — so that he has to find connective
tissue instead of listing. With him the page has three voices: the sleeper dreaming (nemo,
`stream.py`), the sleeper remembering (here), and the reader at the bedside
(`interpreter.py`). They do not read each other: this one is shown scenes and its own last
words, and **never** the reader's notes or underlines, or the account would start answering
the reader instead of remembering the dream.

**He is handed the scene alone** (2026-09-19): no seed, and the passage's ragged first and last
words left as they are, because consecutive ragged edges are what he makes the dream's joints
out of. `STREAM_DREAM_SEEDS=1` puts the seed back.

**Rewriting, not appending, is the whole thing.** Each call hands over one version and one new
scene and gets a whole new version back, so the account stays index-card sized and the older
scenes fade as newer ones arrive — an appender would just grow a list. Every version is kept on
the shelf, because the *sequence of rewrites* is itself the object: what survived four rewrites
is what the dream was about.

The two voices do not share a vocabulary and do not have to: the reader's own prompt calls each
passage a dream, and its file is left alone.

Env: STREAM_DIR (default shelf/stream/), STREAM_DREAM_TURNS (how many scenes a dream runs to,
default 4 — about twenty minutes), STREAM_DREAM_GAP (seconds of silence that end a dream,
default 1800), STREAM_DREAM_SEEDS (1 = hand him the seed as well, off by default),
STREAM_DREAM_TIMEOUT, STREAM_DREAM_PERSONA, plus loom's LOOM_SITTINGS.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))              # eva/stream
EVA = os.path.dirname(HERE)
for d in (os.path.join(EVA, "server"), os.path.join(EVA, "cli"), HERE):
    if d not in sys.path:
        sys.path.insert(0, d)
import loom  # noqa: E402
import opus  # noqa: E402   one call, one usage block, one place the budget is counted

STREAM = os.environ.get("STREAM_DIR", os.path.join(loom.SHELF, "stream"))
DREAMS = os.path.join(STREAM, "dreams")
LEDGER = os.path.join(STREAM, "ledger.jsonl")
PERSONA = os.environ.get("STREAM_DREAM_PERSONA", os.path.join(HERE, "remembering.txt"))

# How many scenes one dream runs to before he starts again. Two hours at a passage every five
# minutes. bekh: after a couple of hours he starts again.
TURNS = int(os.environ.get("STREAM_DREAM_TURNS", "4"))
# The other way a dream ends: a silence. Half an hour with no passage means the mac slept or
# llama went away, and the sleeper woke — carrying that gap across as if it were one dream
# would make an account of two evenings pretending to be one.
GAP = int(os.environ.get("STREAM_DREAM_GAP", "1800"))
TIMEOUT = int(os.environ.get("STREAM_DREAM_TIMEOUT", "300"))
# Off by default: he is handed the scene and nothing else. See prompt_for for why the ragged
# edges are the point. `=1` puts the seed and the labels back, for going back in one env var.
SEEDS = os.environ.get("STREAM_DREAM_SEEDS") == "1"

DREAM_RE = re.compile(r"<dream>(.*?)</dream>", re.S | re.I)

SHAPE = """
Answer with the whole account, rewritten, and nothing else — no preamble, no code fences:

<dream>
what you remember of the dream, now that this scene is part of it
</dream>
"""


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", file=sys.stderr, flush=True)


def ledger(row: dict) -> None:
    os.makedirs(STREAM, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "kind": "dream", **row},
                           ensure_ascii=False) + "\n")


# ---- the dream so far ---------------------------------------------------------------------

def version_files() -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(DREAMS):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for fname in sorted(filenames):
            if fname.endswith(".json"):
                out.append(os.path.join(dirpath, fname))
    return sorted(out)


def versions() -> list[dict]:
    """Every version ever written, oldest first. Small files; the whole history of an evening
    is a few dozen of them."""
    out = []
    for path in version_files():
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue          # a broken version is one fewer memory, never a failed run
        if isinstance(d, dict) and isinstance(d.get("text"), str):
            out.append(d)
    out.sort(key=lambda d: d.get("ts") or 0)
    return out


def current(past: list[dict], now: float | None = None) -> dict | None:
    """The version this run should rewrite, or None when the next scene starts a new dream.

    A dream is over when it has had its scenes, or when the silence since its last version is
    longer than the gap. Both are read off the files and not off a state file: there is one
    record, the versions, and a second place to keep "which dream are we in" would be a second
    place for it to be wrong.
    """
    if not past:
        return None
    last = past[-1]
    if (last.get("turn") or 0) >= (last.get("of") or TURNS):
        return None
    if (now or time.time()) - (last.get("ts") or 0) > GAP:
        return None
    return last


def covered(past: list[dict]) -> str:
    """The newest room any version has been told. His own watermark, kept apart from the
    reader's: the two voices run on their own clocks and neither waits for the other."""
    top = ""
    for d in past:
        room = d.get("room")
        if isinstance(room, str) and room > top:
            top = room
    return top


def next_scene(past: list[dict]) -> dict | None:
    """The newest unflagged passage he has not been told. Never a backlog: if he was down for
    an hour the twelve scenes he missed stay untold, and the dream simply picks up at the
    newest one — the stream is disposable and so is an account of it."""
    top = covered(past)
    for name in loom.stream_room_names():            # newest first
        if name <= top:
            return None
        page = loom.stream_page(name)
        if page is None or page.get("flag"):
            continue                                  # the filter's column, honoured here too
        return page
    return None


# ---- the prompt -----------------------------------------------------------------------------

NOTHING_YET = "Nothing yet — this is the first scene of the dream."


SEEDED_NOTE = ("A scene is given as the seed it grew from, marked [seed] — text that was "
               "handed to you, not yours — and then the scene itself, marked [scene].")


def prompt_for(page: dict, held: dict | None, persona: str) -> str:
    """Persona (bekh's file, verbatim), the shape, what he remembers, the new scene.

    **Seedless by default** (bekh, 2026-09-19, after reading four scenes each way): the scene
    goes over as nemo wrote it and nothing else — no seed, no `[scene]` label, and **its ragged
    first and last words left exactly as they are**. A passage stops at 170 tokens mid-sentence
    and starts mid-one too, and those ragged edges turn into the dream's JOINTS: *the car
    stopped just before* followed by *killed.* came back as *stopped just before something was
    killed*. Trim or tidy them and that is gone — the account goes back to a list of scenes with
    nothing between them, which is exactly what this voice exists not to be.

    `STREAM_DREAM_SEEDS=1` puts the old material back, labels and all, with one line of
    plumbing explaining the labels — which lives here and not in bekh's persona file, because
    with no seeds in the material there is nothing for his file to explain.

    What is NOT here either way: no reader's note, no underlines, no other scene, no earlier
    version than the latest. His only memory is his own current text.
    """
    remembered = (held or {}).get("text") or NOTHING_YET
    parts = [persona.rstrip("\n"), SHAPE.strip()]
    if SEEDS:
        parts.append(SEEDED_NOTE)
    parts.append("--- what you remember of the dream so far ---\n\n" + remembered.strip())
    if SEEDS:
        parts.append("--- the new scene ---\n\n[seed] " + (page.get("seed") or "").strip()
                     + "\n\n[scene] " + (page.get("text") or ""))
    else:
        parts.append("--- the new scene ---\n\n" + (page.get("text") or ""))
    return "\n\n".join(parts) + "\n"


def parse(answer: str) -> str:
    m = DREAM_RE.search(answer)
    if not m or not m.group(1).strip():
        raise ValueError("no <dream> in the answer")
    return m.group(1).strip()


# ---- writing it down -------------------------------------------------------------------------

def version_path(when_ts: float) -> str:
    lt = time.localtime(when_ts)
    day = os.path.join(DREAMS, time.strftime("%Y-%m-%d", lt))
    stem = time.strftime("%H%M", lt)
    for i in range(1, 10):
        path = os.path.join(day, stem + ("" if i == 1 else f"-{i}") + ".json")
        if not os.path.exists(path):
            return path
    return os.path.join(day, stem + "-9.json")


def write_version(obj: dict) -> str:
    path = version_path(obj["ts"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return path


def dream_id(when_ts: float) -> str:
    """A dream is named for when it began, plus two bytes. The clock alone is not enough: two
    dreams inside one second is only a hand run or a very short cap, but two dreams under one
    name would be ONE dream on the page and in every count, silently."""
    return time.strftime("%Y-%m-%d-%H%M", time.localtime(when_ts)) + "-" + secrets.token_hex(2)


def run_once() -> int:
    try:
        with open(PERSONA, encoding="utf-8") as f:
            persona = f.read()
    except OSError as exc:
        log(f"no persona at {PERSONA}: {exc}")
        ledger({"room": None, "error": f"no persona file: {exc}"})
        return 0

    past = versions()
    page = next_scene(past)
    if page is None:
        # Quietly and with no row: nothing new is the ordinary answer between passages, and a
        # row every time would bury the real ones.
        return 0
    held = current(past)

    started = time.time()
    prompt = prompt_for(page, held, persona)
    try:
        answer, usage = opus.ask(prompt, TIMEOUT)
        text = parse(answer)
    except ValueError as exc:
        log(f"sleeper · {exc}")
        ledger({"room": page["room"], "error": str(exc),
                "seconds": round(time.time() - started, 1)})
        return 0

    now = time.time()
    obj = {"ts": now,
           "dream": held.get("dream") if held else dream_id(now),
           "turn": ((held.get("turn") or 0) + 1) if held else 1,
           "of": TURNS,
           "room": page["room"],
           "text": text,
           "model": opus.MODEL,
           "seconds": round(now - started, 1),
           "usage": usage}
    path = write_version(obj)
    ledger({"room": obj["room"], "dream": obj["dream"], "turn": obj["turn"], "of": obj["of"],
            "chars": len(text), "model": obj["model"], "seconds": obj["seconds"],
            "usage": usage})
    log(f"dream · {os.path.relpath(path, STREAM)} · {obj['dream']} · "
        f"turn {obj['turn']}/{obj['of']} · {len(text)} chars · {obj['seconds']}s · "
        + opus.line(usage))
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="remembering.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true",
                    help="rewrite the dream once and exit — the only mode; stream.py taps "
                         "this job when a passage lands and it has no clock of its own")
    ap.parse_args(argv[1:])
    if TURNS < 1:
        print("STREAM_DREAM_TURNS is at least 1", file=sys.stderr)
        return 2
    return run_once()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
