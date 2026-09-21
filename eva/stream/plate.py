#!/usr/bin/env -S uv run --python 3.12
"""plate.py — a painting for one dream, made by hand.

    uv run --python 3.12 eva/stream/plate.py --room stream/2026-09-19/1647
    uv run --python 3.12 eva/stream/plate.py --room stream/2026-09-19/1437 \\
        --prompt bekh --from /path/to/an-existing.png

**A hand tool, not a daemon.** No launchd job, no kick, no clock: every plate costs one
generation off bekh's ChatGPT allowance and about two minutes, so it is run on purpose, one
room at a time, and a failure is a message and a non-zero exit rather than a ledger row and a
shrug. That is the opposite of every other stance here and it is deliberate.

The picture is drawn by GPT through `codex exec`, which is the only image generator on this mac
with a hand worth using (`~/.claude/docs/codex.md`). The prompt is `plates/prompt-pieces.txt` or
`plates/prompt-bekh.txt` — bekh's files, filled here and never rewritten — plus one paragraph of
delivery plumbing appended after them, which is his rule everywhere: the file he reads is the
prompt, and nothing about saving a png belongs in it.

**Pieces, not the whole dream.** The default prompt is built from what the interpreter
underlined in that room: a drawing model is not a reading model, and the full text came back as
an inventory. With no reading, or nothing marked, it falls back to `bekh` over the dream
verbatim and says so.

Env: STREAM_DIR (default shelf/stream/), STREAM_PLATE_TIMEOUT (600), CODEX (the cli's name, for
the tests' stub).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.realpath(__file__))              # eva/stream
EVA = os.path.dirname(HERE)
for d in (os.path.join(EVA, "server"), os.path.join(EVA, "cli"), HERE):
    if d not in sys.path:
        sys.path.insert(0, d)
import loom  # noqa: E402

STREAM = os.environ.get("STREAM_DIR", os.path.join(loom.SHELF, "stream"))
PLATES = os.path.join(STREAM, "plates")
LEDGER = os.path.join(STREAM, "ledger.jsonl")
PROMPTS = os.path.join(HERE, "plates")
TIMEOUT = int(os.environ.get("STREAM_PLATE_TIMEOUT", "600"))
CODEX = os.environ.get("CODEX", "codex")

# Web-sized. Codex hands back a ~3 MB png; the page loads one of these per passage behind the
# text, so the jpg is what is served and the png is kept beside it as the original.
LONG_SIDE = 1400
QUALITY = 82

# Appended after bekh's prompt file, never inside it. Everything here is about delivery and
# nothing about the painting: keep it that way, or the next person editing the prompt is
# editing plumbing without knowing it.
PLUMBING = """

---

Use your image generation tool to make this painting. Landscape.
Save it as `plate.png` in the current directory — the image must come from the tool, never
drawn by code or downloaded. Then reply with one line saying it is saved. Do not write any
other file, and do not ask any question.
"""


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def ledger(row: dict) -> None:
    os.makedirs(STREAM, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "kind": "plate", **row},
                           ensure_ascii=False) + "\n")


def pieces_for(room: str) -> list[str]:
    """What the interpreter underlined in this room, in the order it wrote them.

    Off the newest reading that covers the room — a room can be in more than one if a block of
    two was read before the blocks became one. Adjacent marked runs are joined: the segments
    are split wherever a tag opened or closed, and two of them touching are one phrase.
    """
    by_room, _ = loom.stream_readings()
    segs = (by_room.get(room) or {}).get("segments")
    if not isinstance(segs, list):
        return []
    out: list[str] = []
    run = ""
    for s in segs:
        if not isinstance(s, dict) or s.get("kind") == "gone":
            continue
        if s.get("mark"):
            run += s.get("t") or ""
        elif run:
            out.append(run.strip())
            run = ""
    if run.strip():
        out.append(run.strip())
    return [p for p in out if p]


def hands() -> list[str]:
    with open(os.path.join(PROMPTS, "hands.txt"), encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]


def brief_for(page: dict, which: str, hand: str, pieces: list[str]) -> str:
    with open(os.path.join(PROMPTS, f"prompt-{which}.txt"), encoding="utf-8") as f:
        body = f.read()
    if which == "pieces":
        body = body.replace("{pieces}", "\n".join(pieces))
    else:
        body = body.replace("{text}", page.get("text") or "")
    body = body.replace("{hand}", hand)
    return body.rstrip("\n") + PLUMBING


def draw(brief: str) -> tuple[str, str, float]:
    """(the png's path, the tail of codex's log, seconds). Raises RuntimeError.

    A fresh scratch dir per run under the system temp, because codex's workdir is its sandbox
    and `plate.png` must be the only thing in it worth finding. `--skip-git-repo-check` because
    that dir is not a repo.
    """
    started = time.time()
    work = tempfile.mkdtemp(prefix="plate-")
    with open(os.path.join(work, "brief.md"), "w", encoding="utf-8") as f:
        f.write(brief)
    cmd = [CODEX, "exec", "--skip-git-repo-check", "-s", "workspace-write", "-"]
    try:
        with open(os.path.join(work, "brief.md"), encoding="utf-8") as f:
            r = subprocess.run(cmd, stdin=f, capture_output=True, text=True,
                               timeout=TIMEOUT, cwd=work)
    except FileNotFoundError:
        raise RuntimeError(f"no `{CODEX}` on PATH")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"codex timed out after {TIMEOUT}s")
    tail = ((r.stdout or "") + (r.stderr or ""))[-1200:]
    if r.returncode != 0:
        raise RuntimeError(f"codex exited {r.returncode}\n{tail}")
    png = os.path.join(work, "plate.png")
    if not os.path.isfile(png):
        raise RuntimeError("codex wrote no plate.png\n" + tail)
    return png, tail, round(time.time() - started, 1)


def web_size(png: str, jpg: str) -> None:
    """The served copy: longest side 1400, quality 82. `sips` because it is on every mac and
    needs nothing installed; magick would do the same."""
    r = subprocess.run(["sips", "-Z", str(LONG_SIDE), "-s", "format", "jpeg",
                        "-s", "formatOptions", str(QUALITY), png, "--out", jpg],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not os.path.isfile(jpg):
        raise RuntimeError(f"sips could not convert it: {(r.stderr or '').strip()[:200]}")


def plate_paths(room: str) -> tuple[str, str, str]:
    """`plates/<date>/<HHMM>.{jpg,png,json}` — named after the room, so one room has one plate
    and re-running replaces it rather than piling up."""
    parts = room.split("/")
    day, stem = parts[-2], parts[-1]
    base = os.path.join(PLATES, day, stem)
    return base + ".jpg", base + ".png", base + ".json"


def prompt_text(which: str) -> str:
    try:
        with open(os.path.join(PROMPTS, f"prompt-{which}.txt"), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def newest_prompt() -> str:
    """Which prompt the newest plate on the shelf was made with, or "" when there is none."""
    best, which = 0.0, ""
    for dirpath, _dirs, files in os.walk(os.path.join(STREAM, "plates")):
        for name in files:
            if not name.endswith(".json"):
                continue
            try:
                with open(os.path.join(dirpath, name), encoding="utf-8") as f:
                    d = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(d, dict) and (d.get("ts") or 0) > best:
                best, which = d.get("ts") or 0, d.get("prompt") or ""
    return which


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="plate.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--room", required=True, help="stream/<YYYY-MM-DD>/<HHMM>")
    # bekh, 2026-09-21: every plate is made from the whole dream. `pieces` is parked, not gone —
    # it hands the painter only the reader's two marked phrases, and the reader marks what
    # touched it, never what the dream is about: the bread dream's pieces were a heel and a
    # feeling, and it came back a high-heeled shoe on a seashore. `pieces` and `alternate` still
    # run when asked for by name.
    ap.add_argument("--prompt", choices=("alternate", "pieces", "bekh"), default="bekh",
                    help="bekh = the whole dream (the default); pieces = only the reader's "
                         "marked phrases (parked); alternate = whichever the newest plate did "
                         "NOT use")
    ap.add_argument("--hand", default="", help="a line from plates/hands.txt; by lot if absent")
    ap.add_argument("--from", dest="src", default="",
                    help="file an existing png instead of drawing one (no codex call)")
    a = ap.parse_args(argv[1:])

    if not loom.name_ok(a.room) or len(a.room.split("/")) != 3:
        log("a room is stream/<YYYY-MM-DD>/<HHMM>")
        return 2
    page = loom.stream_page(a.room)
    if page is None:
        log(f"no such room on the shelf: {a.room}")
        return 1
    if page.get("flag"):
        log(f"{a.room} is flagged ({page['flag']}) — not plating it")
        return 1

    which, pieces = a.prompt, pieces_for(a.room)
    if which == "alternate":
        # bekh, 2026-09-20, after fourteen plates with almost no duds: both prompts stay and
        # they take turns — he won't pick a winner until we understand why both work. The turn
        # is read off the newest plate on the shelf, so a batch and a single hand run agree.
        which = "bekh" if newest_prompt() == "pieces" else "pieces"
    fell_back = False
    if which == "pieces" and not pieces:
        # Said out loud and written into the json: a plate made from the whole text is a
        # different experiment from one made from the underlines, and the file has to say which.
        which, fell_back = "bekh", True
        log(f"no underlined pieces for {a.room} — falling back to the `bekh` prompt")
    # A hand is only drawn for a prompt that has a slot for one. `prompt-bekh.txt` has none, and
    # the first batch recorded a hand on five plates that never saw it — a record that lies is
    # worse than no record, because the hands are exactly what gets compared later.
    hand = (a.hand or random.choice(hands())) if "{hand}" in prompt_text(which) else ""

    jpg, png, meta = plate_paths(a.room)
    os.makedirs(os.path.dirname(jpg), exist_ok=True)
    seconds, tail = 0.0, ""
    if a.src:
        if not os.path.isfile(a.src):
            log(f"no such png: {a.src}")
            return 1
        shutil.copy2(a.src, png)
    else:
        brief = brief_for(page, which, hand, pieces)
        print(f"plate · {a.room} · prompt {which} · {len(pieces)} pieces · hand: {hand or '—'}",
              flush=True)
        try:
            made, tail, seconds = draw(brief)
        except RuntimeError as exc:
            log(str(exc))
            return 1
        shutil.move(made, png)
    try:
        web_size(png, jpg)
    except RuntimeError as exc:
        log(str(exc))
        return 1

    obj = {"ts": time.time(), "room": a.room, "prompt": which, "hand": hand,
           "pieces": pieces, "seconds": seconds, "source_png": a.src or "codex",
           "fell_back": fell_back}
    with open(meta, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    ledger({"room": a.room, "prompt": which, "hand": hand, "pieces": len(pieces),
            "seconds": seconds, "bytes": os.path.getsize(jpg)})
    print(f"plate · {os.path.relpath(jpg, STREAM)} · "
          f"{os.path.getsize(jpg) // 1024} KB · {seconds}s", flush=True)
    used = tokens_used(tail)
    if used:
        print(f"codex tokens used: {used}", flush=True)
    return 0


def tokens_used(tail: str) -> str:
    """The token count out of codex's plain log, or "".

    The number is on the line AFTER the words — the cli prints a `tokens used` label and its
    value on the next line — which is why this used to print a bare label and no number at all.
    A same-line shape is still read, because an older cli and the tests' stub both write it
    that way and a count that silently disappears is worse than one that is ugly.
    """
    lines = tail.splitlines()
    out = ""
    for i, ln in enumerate(lines):
        if "tokens used" not in ln.lower():
            continue
        rest = ln[ln.lower().index("tokens used") + len("tokens used"):].strip(" \t:·-")
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        out = rest or nxt
    return out


if __name__ == "__main__":
    sys.exit(main(sys.argv))
