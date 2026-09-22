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

**And nothing is compared either** (bekh, 2026-09-19, after living with it for an hour): a word
diff of his copy against the dream used to light every tiny difference in red, and it was noise.
What is stored is his copy, verbatim, plus the same string cut into render-ready runs by his
`<mark>` tags alone. The page writes the marked words in colour and that is the whole of it.

**Two families, on purpose** (bekh, 2026-09-21: *we use opus on the left and opus on the
right… how about we use codex for the summarization of the dreams, so they are two different
families*). `STREAM_READER=codex` puts GPT in this seat through `codex.py`; the sleeper
remembering stays opus either way. Everything else is held identical so a note can be read
against a note: the same persona file, the same shape, the same parser, the same storage. Only
the `model` field says who wrote it. When codex is over its limit, or fails, or answers
something with no `<reading>` in it, **opus writes that one note** — every dream gets one — and
the ledger row says why.

Env: STREAM_DIR (default shelf/stream/), STREAM_READER (opus | codex), STREAM_READ_EVERY (how
many passages a note covers, default 1), STREAM_READ_MEMORY (how many of its own readings it is
shown, default 0 — see prompt_for), STREAM_READ_SEEDS (1 = show him the labelled seed again),
STREAM_READ_TIMEOUT, STREAM_READER_TIMEOUT (the codex call, 120s), STREAM_READER_WEEK_MAX (50),
STREAM_READER_SESSION_MAX (80), STREAM_PERSONA (the persona file), plus loom's LOOM_SITTINGS.
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
import codex  # noqa: E402   the other family's door, and the one place its limit is read
import loom  # noqa: E402   the shelf, the stream rooms: nothing else here reads a room
import opus  # noqa: E402   one call, one usage block, one place the budget is counted
import push  # noqa: E402   the mirror, tapped the moment a note lands

STREAM = os.environ.get("STREAM_DIR", os.path.join(loom.SHELF, "stream"))
READINGS = os.path.join(STREAM, "readings")
LEDGER = os.path.join(STREAM, "ledger.jsonl")
PERSONA = os.environ.get("STREAM_PERSONA", os.path.join(HERE, "interpreter.txt"))

# How many passages one note covers. One, since 2026-09-19: bekh wants a note for every
# generation. The dial is here because it is the one number that decides how much of an opus
# bill a day of dreaming costs.
EVERY = int(os.environ.get("STREAM_READ_EVERY", "1"))
# How many of its OWN past readings it is shown. Its memory, and the only continuity there is:
# nothing else carries from one call to the next. Four is what fits beside two passages
# without the material drowning in it.
MEMORY = int(os.environ.get("STREAM_READ_MEMORY", "0"))
# Whether he is shown the seed each dream grew from. Off since 2026-09-21, like the sleeper's:
# with the seed in sight he narrated the plumbing ("now it is handed Gogol's madman…") instead
# of reading the dream. `STREAM_READ_SEEDS=1` puts the labelled seed back.
SEEDS = os.environ.get("STREAM_READ_SEEDS") == "1"
TIMEOUT = int(os.environ.get("STREAM_READ_TIMEOUT", "300"))

# The opus seat's name is NOT snapshotted here: `opus.MODEL` is the id the cli says answered,
# and it is read after the call (see opus.py).
#
# Which family sits at the bedside. `opus` in code, `codex` in the plist (bekh, 2026-09-21):
# the default stays opus so a hand run, a test and a fresh clone behave the way this file has
# always behaved, and production says what it wants out loud.
READER = (os.environ.get("STREAM_READER") or "opus").strip().lower()
# The codex call's own clock. Two minutes, not the opus five: this is a short note at low
# reasoning effort, and a codex that is thinking for longer than that is stuck — every second
# spent waiting is a second the next dream's note is late.
CODEX_TIMEOUT = int(os.environ.get("STREAM_READER_TIMEOUT", "120"))
# The reader's own thresholds on the shared codex ceiling, kept apart from the painter's
# (STREAM_PLATE_*) because the two spend very differently: a plate is minutes and ~19k tokens,
# a note is seconds. The session window is the one that actually trips.
WEEK_MAX = float(os.environ.get("STREAM_READER_WEEK_MAX", "50"))
SESSION_MAX = float(os.environ.get("STREAM_READER_SESSION_MAX", "80"))


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
the dream text of passage 1, typed back with your two tags in it
</passage>
<passage n="2">
…and so on, one per passage
</passage>
<name>
what comes after "a dream about"
</name>
"""


def prompt_for(told: list[dict], past: list[dict], persona: str) -> str:
    """The persona file's text, then the shape, then its own last readings, then the stretch.

    `told` is oldest first — the stretch is read in the order it was dreamt — and the passage
    numbers follow it, which is the only thing that ties an answer back to a room.
    """
    parts = [persona.rstrip("\n"), SHAPE.strip()]
    # His memory is OFF by default (2026-09-21). Shown his own last four notes, he stopped
    # remembering the dreams and started copying his own format: one note opened "Last time
    # it…", the next call had that note in front of it, and from 16:42 on the first day 81 of
    # 97 notes open with those two words and end on "plainly" — a genre lock, the same disease
    # nemo has, built by us. bekh saw it as four dreams summarized the same way. If a memory
    # comes back it must be something he cannot imitate (a bare list of recurring images, not
    # his own sentences); turning this number up again brings the formula back within an hour.
    mem = past[-MEMORY:] if MEMORY > 0 else []
    if mem:
        lines = ["--- your own earlier readings, oldest first; you remember them ---"]
        for d in mem:
            lines.append(f"({when(d.get('ts') or 0)})")
            lines.append((d.get("reading") or "").strip())
        parts.append("\n\n".join(lines))
    lines = ["--- the latest stretch ---"]
    if SEEDS:
        # No "machine" here either (bekh, 2026-09-21): the word is out of everything a voice is
        # shown, because it is what made the reader see an AI's self-portrait in every dream.
        lines.append("(each passage grew from a seed, text that was handed over and is not the "
                     "dreamer's own, marked [seed]; the dream is what comes after, marked [dream])")
    for i, p in enumerate(told, 1):
        if len(told) > 1 or SEEDS:
            lines.append(f"passage {i}")
        if SEEDS:
            lines.append("[seed] " + (p.get("seed") or "").strip())
            lines.append("[dream] " + (p.get("text") or ""))
        else:
            # The dream exactly as nemo wrote it, ragged first and last words included.
            lines.append(p.get("text") or "")
    parts.append("\n\n".join(lines))
    return "\n\n".join(parts) + "\n"


def when(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts or 0))


# ---- reading the answer ----------------------------------------------------------------------
# Tags and not json, because the answer is full of `<mark>` and a tag inside a json string is
# an escaping question nobody needs to get right at 3am. Parsed leniently: a reading with no
# passages is still a reading, and a passage whose number names nothing is dropped.

READING_RE = re.compile(r"<reading>(.*?)</reading>", re.S | re.I)
PASSAGE_RE = re.compile(r"<passage[^>]*\bn\s*=\s*[\"']?(\d+)[\"']?[^>]*>(.*?)</passage>", re.S | re.I)
NAME_RE = re.compile(r"<name(?:[^>]*\bn\s*=\s*[\"']?(\d+)[\"']?)?[^>]*>(.*?)</name>", re.S | re.I)

# **Every dream gets a name, and the name is a menu** (bekh, 2026-09-22): the page has very
# little separation between dreams and he does not read them all, so he picks by name. His
# prompt asks the reader to finish *"a dream about …"* and to write only the part that comes
# after it — the page says the first part, once, in how it is laid out. So anything the reader
# says anyway gets cut here: it would be a name that reads *a dream about a dream about*.
NAME_PREFIX_RE = re.compile(r"^\s*(?:a\s+)?dream\s+about\s*[:,]?\s*", re.I)
NAME_MAX = 200


def clean_name(raw: str) -> str:
    """One line, ready to print, or "". Never raises: a missing or silly name costs the note
    nothing, and a note without a name is a dream that is simply harder to choose."""
    name = NAME_PREFIX_RE.sub("", (raw or "").strip())
    name = " ".join(name.split())                     # a name that wrapped in the answer is one line
    name = name.strip("\"'“”‘’`*").strip()
    name = name.rstrip(".").strip()                   # a full stop at the end of a title is noise
    # Lowercase, always (bekh, 2026-09-22): the page is lowercase and a name is part of the
    # page. Done here and not asked for in the prompt, so it holds whoever wrote the name and
    # however they felt about capitals that day — "Sandy Hook" and "I" included, by decision.
    name = name.lower()
    if len(name) > NAME_MAX:
        # Cut at a word, not mid-syllable; an over-long name is the reader explaining instead
        # of naming, and what is lost past 120 characters was never going to be read in a list.
        name = name[:NAME_MAX].rsplit(" ", 1)[0].rstrip(",;:—-") + "…"
    return name


# ---- his copy, as he typed it -----------------------------------------------------------------
# The page shows HIS copy of the dream and nothing is compared against the raw text (bekh,
# 2026-09-19: the retype marks were too much noise). All that is read out of it is where he put
# his two marks; everything else he may have typed, angle brackets and all, is characters and
# stays characters, and a stray closing tag closes nothing rather than throwing.
#
# **Two marks and no more** (bekh, 2026-09-21), and now they MEAN the two things his own prompt
# already asks for: `touched` is what impressed and touched him most, `strange` is what felt
# most mysterious and meaningful. The page gives them the magenta and the cyan it already had,
# so a colour stops being a coin toss and starts being a reading.
MARKS = ("touched", "strange")
MARK_TAG_RE = re.compile(r"</?(touched|strange|mark)>", re.I)


def segments_of(copy: str) -> tuple[list[dict], int]:
    """(his copy as render-ready runs, how many marks were dropped).

    A run is `{t, mark}` with `mark` one of `"touched"`, `"strange"`, `True` (a legacy
    `<mark>`) or `False`. Adjacent runs of one state join.

    **The first of each kind wins.** If he marks two things touched, the second becomes plain
    text and is counted — the rule is his and enforcing it here is cheaper than a second rule
    in the page, which would then have to agree with this one forever.
    """
    segs: list[dict] = []
    open_kinds: list[str] = []
    used: set[str] = set()
    dropped, i = 0, 0

    def state():
        # The innermost open tag that is still allowed to paint. Nesting is not a thing he is
        # asked for, but an answer is text and may do anything.
        for kind in reversed(open_kinds):
            if kind is not None:
                return True if kind == "mark" else kind
        return False

    def add(text: str, mark) -> None:
        if not text:
            return
        if segs and segs[-1]["mark"] == mark:
            segs[-1]["t"] += text
        else:
            segs.append({"t": text, "mark": mark})

    for m in MARK_TAG_RE.finditer(copy):
        add(copy[i:m.start()], state())
        kind = m.group(1).lower()
        if m.group(0)[1] == "/":
            for at in range(len(open_kinds) - 1, -1, -1):
                if open_kinds[at] in (kind, None) and (open_kinds[at] == kind or kind == "mark"):
                    open_kinds.pop(at)
                    break
            else:
                if open_kinds:
                    open_kinds.pop()
        else:
            if kind in MARKS and kind in used:
                dropped += 1
                open_kinds.append(None)      # opened, and painting nothing
            else:
                used.add(kind)
                open_kinds.append(kind)
        i = m.end()
    add(copy[i:], state())
    return segs, dropped


def parse(answer: str, told: list[dict]) -> tuple[str, dict, dict]:
    """(the reading, {room: the marked copy}, {room: the dream's name}).

    Raises ValueError when there is no reading — and only then. A name is a convenience for
    choosing what to read; a missing one is a name-less dream and never a failed note.
    """
    m = READING_RE.search(answer)
    if not m or not m.group(1).strip():
        raise ValueError("no <reading> in the answer")
    names, loose = {}, 0
    for num, body in NAME_RE.findall(answer):
        # A block of one is the rule, so the usual answer is one bare <name>. A numbered one
        # names that passage; unnumbered ones are taken in order, which is the same thing when
        # there is one of each.
        i = (int(num) - 1) if num else loose
        if not num:
            loose += 1
        name = clean_name(body)
        if name and 0 <= i < len(told):
            names[told[i]["room"]] = name
    marked = {}
    for num, body in PASSAGE_RE.findall(answer):
        i = int(num) - 1
        if not (0 <= i < len(told)):
            continue
        text = body.strip("\n")
        # He sometimes types the material back whole, labels and all. His slips are kept by
        # decision; our `[seed] … [dream]` plumbing turning up inside a dream is not one of his.
        if "[dream]" in text:
            text = text.rsplit("[dream]", 1)[1].lstrip(" \t").strip("\n")
        if text.strip():
            marked[told[i]["room"]] = text
    return m.group(1).strip(), marked, names


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


def read(prompt: str, told: list[dict]) -> tuple[str, dict, dict, str, dict, str]:
    """Ask the seat's family, and fall back to opus for this one note if it cannot answer.

    `(the reading, the marked copies, the names, who wrote it, its usage block, why it fell
    back)`.
    Raises ValueError only when opus fails too — which is the old behaviour: a ledger row and
    exit 0.

    **The fallback is per-note, not per-session.** A dream with no note is a hole in the page
    that nothing later fills in (the reader never chews a backlog), so a codex that is held, a
    codex that times out and a codex that answers a paragraph of apology all cost the same
    thing: one note written by the other family, and one line on the ledger saying so.
    """
    if READER == "codex":
        held = codex.held_for(*codex.usage(), WEEK_MAX, SESSION_MAX)
        why = f"codex held · {held}" if held else ""
        if not why:
            try:
                answer, usage = codex.ask(prompt, CODEX_TIMEOUT)
                reading, marked, names = parse(answer, told)
                return reading, marked, names, "codex:" + codex.MODEL, usage, ""
            except ValueError as exc:
                why = f"codex · {exc}"
        log(f"falling back to opus · {why}")
        answer, usage = opus.ask(prompt, TIMEOUT)
        return (*parse(answer, told), opus.MODEL, usage, why)
    answer, usage = opus.ask(prompt, TIMEOUT)
    return (*parse(answer, told), opus.MODEL, usage, "")


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
        reading, marked, names, model, usage, fell_back = read(prompt, told)
    except ValueError as exc:
        log(f"reader · {exc}")
        ledger({"rooms": [p["room"] for p in reversed(told)], "error": str(exc),
                "seconds": round(time.time() - started, 1)})
        return 0

    # Cut once, here, and never in the page or the server: the same string will not change
    # again, and the page should be drawing, not parsing.
    segments, dropped = {}, 0
    for room, copy in marked.items():
        segments[room], n = segments_of(copy)
        dropped += n

    obj = {"ts": time.time(),
           # Newest first, so the head of the block — the passage the page hangs the reading
           # off — is `rooms[0]` and nothing has to sort it again.
           "rooms": [p["room"] for p in reversed(told)],
           "reading": reading,
           "marked": marked,
           "segments": segments,
           # **The name is the menu** (bekh, 2026-09-22). A dict keyed by room, so a block of
           # several passages still names each of them; an empty one is a nameless dream and
           # the page simply shows its number.
           "names": names,
           # Who wrote this note: `opus`, or `codex:<model id>`. The page never shows it, and
           # a pile of notes read blind later is worth nothing without it.
           "model": model,
           "seconds": round(time.time() - started, 1),
           "usage": usage}
    path = write_reading(obj)
    row = {"rooms": obj["rooms"], "marked": len(marked), "chars": len(reading),
           # Two marks is the rule; how often he reaches for a third is worth knowing.
           "dropped": dropped,
           # The newest dream's name on the row, so the ledger reads as a table of contents.
           "name": names.get(obj["rooms"][0]),
           "model": model, "seconds": obj["seconds"], "usage": usage}
    if fell_back:
        row["fell_back"] = fell_back
    ledger(row)
    counted = codex.line(usage) if model.startswith("codex:") else opus.line(usage)
    named = names.get(obj["rooms"][0]) or "—"
    log(f"reading · {os.path.relpath(path, STREAM)} · {len(told)} passages · "
        f"{len(marked)} marked up · “{named}” · {model} · {obj['seconds']}s · " + counted)
    # A note changes what a reader sees — the margin and the dream's name — so the mirror is
    # told now rather than at the next minute. Whichever family wrote it: the file is ours.
    push.now()
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
    if READER not in ("opus", "codex"):
        # Loud, like EVERY: a typo in the plist would otherwise be a silent demotion back to
        # opus, and the whole point of the switch is knowing which family wrote a note.
        print(f"STREAM_READER is opus or codex, not {READER!r}", file=sys.stderr)
        return 2
    return run_once()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
