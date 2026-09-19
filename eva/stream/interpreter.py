#!/usr/bin/env -S uv run --python 3.12
"""interpreter.py — a second voice beside the stream: somebody reading it.

    uv run --python 3.12 eva/stream/interpreter.py --once

The stream is verbose — a passage every five minutes, all day, and nobody picking. bekh's
idea: anchor it with a reader who **takes the dreams seriously**, is keen on reflections and
symbols, is lucid and calm about the process and is in the game; who writes a short reading of
each small stretch and **underlines**, inside the passages, what touched him. A reading every
two passages for now, so he is more exposed to it while testing.

That reader is Claude Opus through the cli, headless, exactly the way `berserk.py` asks it a
question: `claude -p --model opus`, prompt on **stdin** (a prompt of this size carries quotes,
newlines and backslashes an argv would mangle), no tools, `cwd` in a temp dir and `CLAUDECODE`
out of the env so this repo's `CLAUDE.md` is not loaded into the head of somebody who was asked
to read a dream.

**The persona is not in this file.** It is `interpreter.txt` beside it, which bekh edits by
hand and this code never rewrites; everything appended after it here is plumbing he should not
have to see in his prompt — the output shape, his last four readings, and the material.

**No sameness checker** (bekh, 2026-09-19). The interpreter types the dream back with its own
`<mark>` tags in it, and what comes back is stored as its own copy, verbatim. If it alters a
word on the way, *that is another prophecy* and is kept, not corrected. The room on the shelf
is never written to by this process — not as a check, simply because the record is the record,
and the page shows the raw dream the moment the marks are switched off.

**His slips are shown, in red.** Not fixed: a word diff runs once here, at write time, between
the raw dream and his copy with the tags stripped, and the result is stored as render-ready
segments — what he added in red, what he dropped struck through where it was dropped, his
underlines on top. Words and not characters, because a character diff of prose is unreadable;
whitespace tokens compare equal to each other, so normalising a double space is not a slip.

Env: STREAM_DIR (default shelf/stream/), STREAM_READ_EVERY (how many passages a reading
covers, default 2), STREAM_READ_MEMORY (how many of its own readings it is shown, default 4),
STREAM_READ_TIMEOUT, STREAM_PERSONA (the persona file), plus loom's LOOM_SITTINGS.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.realpath(__file__))              # eva/stream
EVA = os.path.dirname(HERE)
for d in (os.path.join(EVA, "server"), os.path.join(EVA, "cli")):
    if d not in sys.path:
        sys.path.insert(0, d)
import loom  # noqa: E402   the shelf, the stream rooms: nothing else here reads a room

STREAM = os.environ.get("STREAM_DIR", os.path.join(loom.SHELF, "stream"))
READINGS = os.path.join(STREAM, "readings")
LEDGER = os.path.join(STREAM, "ledger.jsonl")
PERSONA = os.environ.get("STREAM_PERSONA", os.path.join(HERE, "interpreter.txt"))

# How many passages one reading covers. Two while bekh is testing — he wants to be more
# exposed to the reading than to the stream — and the dial is here because it is the one
# number that decides how much of an opus bill a day of dreaming costs.
EVERY = int(os.environ.get("STREAM_READ_EVERY", "2"))
# How many of its OWN past readings it is shown. Its memory, and the only continuity there is:
# nothing else carries from one call to the next. Four is what fits beside two passages
# without the material drowning in it.
MEMORY = int(os.environ.get("STREAM_READ_MEMORY", "4"))
TIMEOUT = int(os.environ.get("STREAM_READ_TIMEOUT", "300"))

# berserk's invocation, copied on purpose rather than imported: a reader with tools is a reader
# that will go and read the rest of the repo instead of the dream in front of it.
# `--setting-sources project` is what keeps bekh's GLOBAL ~/.claude/CLAUDE.md out of the
# reader's head (checked 2026-09-19: without it a headless call answers YES to "do you have a
# persona file loaded" and names that file; with it, nothing is loaded and the subscription
# login still works). That file is a knight, a horse, a swearing rule and a DBA's day job —
# take this flag out and every dream is read by someone who was just told all of that. The
# temp-dir cwd below only ever kept the PROJECT file out.
CLAUDE = ["claude", "-p", "--model", "opus", "--output-format", "text",
          "--tools", "", "--strict-mcp-config", "--setting-sources", "project"]
MODEL = "opus"


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", file=sys.stderr, flush=True)


def ledger(row: dict) -> None:
    os.makedirs(STREAM, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "kind": "reading", **row},
                           ensure_ascii=False) + "\n")


# ---- what has been read already -------------------------------------------------------------

def reading_files() -> list[str]:
    """Every reading on disk, oldest first by name — the names are timestamps, like the
    rooms', so this is a sort and not a parse."""
    out = []
    for dirpath, dirnames, filenames in os.walk(READINGS):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for fname in sorted(filenames):
            if fname.endswith(".json"):
                out.append(os.path.join(dirpath, fname))
    return sorted(out)


def readings() -> list[dict]:
    out = []
    for path in reading_files():
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue          # a broken reading is one fewer memory, never a failed run
        if isinstance(d, dict) and isinstance(d.get("reading"), str):
            out.append(d)
    out.sort(key=lambda d: d.get("ts") or 0)
    return out


def covered(past: list[dict]) -> str:
    """The newest room any reading has covered. Room names sort chronologically, so this is a
    max over strings and the watermark the next block starts above."""
    top = ""
    for d in past:
        for room in (d.get("rooms") or []):
            if isinstance(room, str) and room > top:
                top = room
    return top


def block(past: list[dict]) -> list[dict]:
    """The passages this run should read: the newest EVERY unflagged ones above the watermark,
    or [] when there are not enough yet.

    A backlog is never chewed through. If the interpreter was down for an hour, the twelve
    passages it missed simply stay unread and it picks up at the newest — the stream is
    disposable and a reading of an hour-old stretch is not what the page is for.
    """
    top = covered(past)
    fresh = []
    for name in loom.stream_room_names():            # newest first
        if name <= top:
            break                                     # sorted, so everything below is covered
        page = loom.stream_page(name)
        if page is None or page.get("flag"):
            continue                                  # the filter's column, honoured here too
        fresh.append(page)
        if len(fresh) >= EVERY:
            break
    return fresh if len(fresh) >= EVERY else []


# ---- the prompt ------------------------------------------------------------------------------
# Persona first, verbatim, then the plumbing. The split is the point: bekh opens
# `interpreter.txt` and reads the whole of what he is saying to it, with no output format and
# no bookkeeping in the way.

SHAPE = """
Answer in exactly this shape and nothing else — no preamble, no code fences:

<reading>
your reading of this stretch
</reading>
<passage n="1">
the dream text of passage 1, typed back with your <mark>…</mark> tags in it
</passage>
<passage n="2">
…and so on, one per passage
</passage>
"""


def prompt_for(told: list[dict], past: list[dict], persona: str) -> str:
    """The persona file's text, then the shape, then its own last readings, then the stretch.

    `told` is oldest first — the stretch is read in the order it was dreamt — and the passage
    numbers follow it, which is the only thing that ties an answer back to a room.
    """
    parts = [persona.rstrip("\n"), SHAPE.strip()]
    mem = past[-MEMORY:] if MEMORY > 0 else []
    if mem:
        lines = ["--- your earlier readings, oldest first ---"]
        for d in mem:
            lines.append(f"({when(d.get('ts') or 0)})")
            lines.append((d.get("reading") or "").strip())
        parts.append("\n\n".join(lines))
    lines = ["--- the latest stretch ---"]
    for i, p in enumerate(told, 1):
        lines.append(f"passage {i}")
        lines.append("[seed] " + (p.get("seed") or "").strip())
        lines.append("[dream] " + (p.get("text") or ""))
    parts.append("\n\n".join(lines))
    return "\n\n".join(parts) + "\n"


def when(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts or 0))


def ask(prompt: str) -> str:
    """One `claude -p` call, prompt on stdin. Raises ValueError on anything that is not a
    clean answer — the caller turns that into a ledger row and exit 0.

    CLAUDECODE and CLAUDE_CODE_ENTRYPOINT come out of the env because a claude started from
    inside a claude session refuses to start, and this may be run by hand from one. The cwd is
    a temp dir so this repo's CLAUDE.md is not auto-loaded in front of the dream.
    """
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(CLAUDE, input=prompt, capture_output=True, text=True,
                           timeout=TIMEOUT, env=env, cwd=tempfile.gettempdir())
    except FileNotFoundError:
        raise ValueError("no `claude` on PATH")
    except subprocess.TimeoutExpired:
        raise ValueError(f"claude timed out after {TIMEOUT}s")
    if r.returncode != 0:
        raise ValueError(f"claude exited {r.returncode}: {(r.stderr or '')[-300:]}")
    return r.stdout or ""


# ---- reading the answer ----------------------------------------------------------------------
# Tags and not json, because the answer is full of `<mark>` and a tag inside a json string is
# an escaping question nobody needs to get right at 3am. Parsed leniently: a reading with no
# passages is still a reading, and a passage whose number names nothing is dropped.

READING_RE = re.compile(r"<reading>(.*?)</reading>", re.S | re.I)
PASSAGE_RE = re.compile(r"<passage[^>]*\bn\s*=\s*[\"']?(\d+)[\"']?[^>]*>(.*?)</passage>", re.S | re.I)


# ---- his copy against the dream ---------------------------------------------------------------
# The page shows his copy, so whatever he changed while re-typing is what bekh would read as the
# dream. Rather than correct it — a slip is another prophecy — the difference is made visible:
# `new` for words that are his and not the machine's, `gone` for the machine's words he dropped,
# shown where they were dropped, and his `<mark>` underlines riding on top of either.
#
# WORDS, not characters: a character diff of prose is a rash of red inside words and unreadable.
# Whitespace tokens all normalise to one space before the comparison, so reflowing a paragraph or
# closing up a double space is not a slip — the whitespace SHOWN is still his.

TOKEN_RE = re.compile(r"\s+|\S+")
MARK_TAG_RE = re.compile(r"</?mark>", re.I)


def unmark(copy: str) -> tuple[str, list[bool]]:
    """His copy with the `<mark>` tags taken out, plus a flag per remaining character saying
    whether it stood inside a pair. Only `<mark>`/`</mark>` are read as tags — everything else
    he may have typed, angle brackets and all, is text and stays text. A stray `</mark>` closes
    nothing rather than throwing."""
    out, flags, depth, i = [], [], 0, 0
    for m in MARK_TAG_RE.finditer(copy):
        chunk = copy[i:m.start()]
        out.append(chunk)
        flags.extend([depth > 0] * len(chunk))
        depth = max(0, depth + (-1 if m.group(0)[1] == "/" else 1))
        i = m.end()
    chunk = copy[i:]
    out.append(chunk)
    flags.extend([depth > 0] * len(chunk))
    return "".join(out), flags


def tokens_of(text: str, flags: list[bool] | None = None) -> list[tuple[str, bool]]:
    """Word and whitespace tokens, each with whether any of it was underlined. A mark that
    opens mid-word underlines the whole word: the token stays whole, which is what keeps the
    diff from seeing `swi` and `tch` where the dream said `switch`."""
    out = []
    for m in TOKEN_RE.finditer(text):
        out.append((m.group(0),
                    bool(flags and any(flags[m.start():m.end()]))))
    return out


def _norm(tok: str) -> str:
    return " " if tok.isspace() else tok


def diff_segments(raw: str, copy: str) -> tuple[list[dict], int, int]:
    """(segments, words he added, words he dropped). A segment is `{t, mark, kind}` with kind
    one of same / new / gone, adjacent tokens of one kind and one mark run together."""
    import difflib
    plain, flags = unmark(copy)
    a, b = tokens_of(raw), tokens_of(plain, flags)
    sm = difflib.SequenceMatcher(a=[_norm(t) for t, _ in a], b=[_norm(t) for t, _ in b],
                                 autojunk=False)
    rows: list[tuple[str, bool, str]] = []
    added = dropped = 0

    def push(toks, kind, keep_mark):
        nonlocal added, dropped
        # A run that is nothing but whitespace is a break he added or dropped: invisible
        # either way, and a struck-through space is a smudge. Inside a run that has words in
        # it the spaces stay with their kind, or a dropped sentence would be struck through
        # as one long word.
        if kind in ("new", "gone") and all(t.strip() == "" for t, _ in toks):
            if kind == "gone":
                return
            kind = "same"
        for t, mk in toks:
            if t.strip():
                if kind == "new":
                    added += 1
                elif kind == "gone":
                    dropped += 1
            rows.append((t, mk if keep_mark else False, kind))

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            push(b[j1:j2], "same", True)
        elif op == "insert":
            push(b[j1:j2], "new", True)
        elif op == "delete":
            push(a[i1:i2], "gone", False)
        else:
            # The machine's words first, then his: the strike-through stands where the
            # replacement happened instead of after it.
            push(a[i1:i2], "gone", False)
            push(b[j1:j2], "new", True)

    segs: list[dict] = []
    for t, mk, kind in rows:
        if segs and segs[-1]["mark"] == mk and segs[-1]["kind"] == kind:
            segs[-1]["t"] += t
        else:
            segs.append({"t": t, "mark": mk, "kind": kind})
    return segs, added, dropped


def parse(answer: str, told: list[dict]) -> tuple[str, dict]:
    """(the reading, {room: the marked copy}). Raises ValueError when there is no reading."""
    m = READING_RE.search(answer)
    if not m or not m.group(1).strip():
        raise ValueError("no <reading> in the answer")
    marked = {}
    for num, body in PASSAGE_RE.findall(answer):
        i = int(num) - 1
        if not (0 <= i < len(told)):
            continue
        text = body.strip("\n")
        if text.strip():
            marked[told[i]["room"]] = text
    return m.group(1).strip(), marked


# ---- writing it down ---------------------------------------------------------------------------

def reading_path(when_ts: float) -> str:
    """`readings/<YYYY-MM-DD>/<HHMM>.json`, a day to a folder like the rooms. A taken name
    gets a `-2`: only a hand run inside the timer's minute can collide, and losing the reading
    for that would be losing it for nothing."""
    lt = time.localtime(when_ts)
    day = os.path.join(READINGS, time.strftime("%Y-%m-%d", lt))
    stem = time.strftime("%H%M", lt)
    for i in range(1, 10):
        path = os.path.join(day, stem + ("" if i == 1 else f"-{i}") + ".json")
        if not os.path.exists(path):
            return path
    return os.path.join(day, stem + "-9.json")


def write_reading(obj: dict) -> str:
    path = reading_path(obj["ts"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return path


def run_once() -> int:
    try:
        with open(PERSONA, encoding="utf-8") as f:
            persona = f.read()
    except OSError as exc:
        log(f"no persona at {PERSONA}: {exc}")
        ledger({"rooms": [], "error": f"no persona file: {exc}"})
        return 0
    past = readings()
    told = list(reversed(block(past)))               # oldest first, as it was dreamt
    if not told:
        # Quietly, and with no ledger row: this is the ordinary state four runs out of five at
        # EVERY 2, and a row every five minutes saying "nothing yet" would bury the real ones.
        return 0

    started = time.time()
    prompt = prompt_for(told, past, persona)
    try:
        answer = ask(prompt)
        reading, marked = parse(answer, told)
    except ValueError as exc:
        log(f"reader · {exc}")
        ledger({"rooms": [p["room"] for p in reversed(told)], "error": str(exc),
                "seconds": round(time.time() - started, 1)})
        return 0

    # The diff runs once, here, and never in the page or the server: it is a fact about two
    # strings that will not change again, and the page should be drawing, not comparing.
    segments, added, dropped = {}, 0, 0
    for p in told:
        copy = marked.get(p["room"])
        if copy is None:
            continue
        segs, a, d = diff_segments(p.get("text") or "", copy)
        segments[p["room"]] = segs
        added += a
        dropped += d

    obj = {"ts": time.time(),
           # Newest first, so the head of the block — the passage the page hangs the reading
           # off — is `rooms[0]` and nothing has to sort it again.
           "rooms": [p["room"] for p in reversed(told)],
           "reading": reading,
           "marked": marked,
           "segments": segments,
           "model": MODEL,
           "seconds": round(time.time() - started, 1)}
    path = write_reading(obj)
    # `new`/`gone` on the row so a month of these says how faithfully he re-types, without
    # anybody opening a reading file.
    ledger({"rooms": obj["rooms"], "marked": len(marked), "chars": len(reading),
            "new": added, "gone": dropped,
            "model": MODEL, "seconds": obj["seconds"]})
    log(f"reading · {os.path.relpath(path, STREAM)} · {len(told)} passages · "
        f"{len(marked)} marked up · +{added}/-{dropped} words · {obj['seconds']}s")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="interpreter.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true",
                    help="write at most one reading and exit — the only mode; the loop is "
                         "launchd's StartInterval, as it is for the worker")
    ap.parse_args(argv[1:])
    if EVERY < 1:
        print("STREAM_READ_EVERY is at least 1", file=sys.stderr)
        return 2
    return run_once()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
