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

**One telling with seams in it** (bekh, 2026-09-22): the account is a single continuous
narrative, and a `|` marks the point where each later scene comes in, so the page can put the
part for scene n beside passage n and still have one story running down the left. The marks are
stored in `text` like every other character he writes, and `parts` beside it is that same string
split on the mark — derived, never corrected. He is shown his own marked text back as his
memory, so he can see where he put the seams last time.

The two voices do not share a vocabulary and do not have to: the reader's own prompt calls each
passage a dream, and its file is left alone.

**A story has a name and an address** (bekh, 2026-09-22). He named it: every four-scene story
gets a name of the sleeper's own — *what you would call it if someone asked you about it over
breakfast* — and every dream gets a psalm's number, `12:3` being the third scene of the twelfth
story. The chapter is taken when a story starts, stored on every version of it and never
computed from what is on the shelf, because forgetting will one day prune the shelf and an
address must not shift under him. `--number` backfills the stories written before this.

Env: STREAM_DIR (default shelf/stream/), STREAM_DREAM_TURNS (how many scenes a dream runs to,
default 4 — about twenty minutes), STREAM_DREAM_SEEDS (1 = hand him the seed as well, off by default),
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
import interpreter  # noqa: E402   only for `clean_name`: one rule for both names, not two
import loom  # noqa: E402
import opus  # noqa: E402   one call, one usage block, one place the budget is counted
import push  # noqa: E402   the mirror, tapped the moment a rewrite lands

STREAM = os.environ.get("STREAM_DIR", os.path.join(loom.SHELF, "stream"))
DREAMS = os.path.join(STREAM, "dreams")
LEDGER = os.path.join(STREAM, "ledger.jsonl")
PERSONA = os.environ.get("STREAM_DREAM_PERSONA", os.path.join(HERE, "remembering.txt"))

# How many scenes one dream runs to before he starts again. Two hours at a passage every five
# minutes. bekh: after a couple of hours he starts again.
TURNS = int(os.environ.get("STREAM_DREAM_TURNS", "4"))
# **No other way a dream ends** (bekh, 2026-09-23). There was a second one — half an hour of
# silence, "the mac slept, so he woke" — and in practice the silence was always bekh stopping
# the stream, which lands anywhere in the count: every evening that ran 4n+1 passages left a
# story of one scene stranded, and the next evening started over. Now a story waits across a
# stop for its four: one passage tonight, two tomorrow, one the day after is one story.
TIMEOUT = int(os.environ.get("STREAM_DREAM_TIMEOUT", "300"))
# Off by default: he is handed the scene and nothing else. See prompt_for for why the ragged
# edges are the point. `=1` puts the seed and the labels back, for going back in one env var.
SEEDS = os.environ.get("STREAM_DREAM_SEEDS") == "1"

DREAM_RE = re.compile(r"<dream>(.*?)</dream>", re.S | re.I)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)

SHAPE = """
Answer with the whole account, rewritten, and nothing else — no preamble, no code fences:

<dream>
what you remember of the dream, now that this scene is part of it
</dream>
<title>
what you would call this dream
</title>

Put a single | at the exact point in the telling where each later scene
comes in — one mark per scene after the first, in order, nowhere else.
It goes where the scene enters, and the middle of a sentence is the right
place for it when that is where it enters. Never start a new sentence,
a new line or a new paragraph for it.
"""

# **The seam mark** (bekh, 2026-09-22). The account stays ONE continuous telling and the page
# shows the part for scene n beside passage n — so the sleeper marks where each later scene
# comes in, and the page cuts there. The mark is allowed to fall mid-sentence, because that is
# where a scene usually enters; the sentence stays whole and the cut is a display decision.
SEAM = "|"


def split_parts(text: str) -> list[str]:
    """The telling cut at its seams. Whitespace around a cut goes, nothing else — `text` stays
    the source of truth and is stored exactly as it was written, marks and all.

    No mark is one part; the wrong number of marks is simply the wrong number of parts. Nothing
    here is an error: the page holds the mismatch (a missing part leaves a row bare, a surplus
    one is appended to the last), and correcting a voice's own words is not done in this
    project.
    """
    return [p.strip() for p in text.split(SEAM)]


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


def current(past: list[dict]) -> dict | None:
    """The version this run should rewrite, or None when the next scene starts a new dream.

    A dream is over when it has had its scenes — and only then, however long the stream was
    off in between. Read off the files and not off a state file: there is one record, the
    versions, and a second place to keep "which dream are we in" would be a second place for
    it to be wrong.
    """
    if not past:
        return None
    last = past[-1]
    if (last.get("turn") or 0) >= (last.get("of") or TURNS):
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


def parse(answer: str) -> tuple[str, str]:
    """(the account, its name). Raises ValueError when there is no account — and only then:
    the name is how a story is chosen off the page, not what it is."""
    m = DREAM_RE.search(answer)
    if not m or not m.group(1).strip():
        raise ValueError("no <dream> in the answer")
    t = TITLE_RE.search(answer)
    # **The title may change with every rewrite, and that is the point** (bekh, 2026-09-22): a
    # dream of four scenes is not the dream its first scene looked like. The latest version's
    # title is the story's name; the older ones stay on the shelf with their own.
    title = interpreter.clean_name(t.group(1)) if t else ""
    return m.group(1).strip(), title


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


# ---- chapter and verse -------------------------------------------------------------------------
# **Every dream gets a psalm's address** (bekh, 2026-09-22): `12:3` is the third scene of the
# twelfth story. A chapter is one story of the sleeper's, a verse is a scene's place in it.
#
# **Chapters count up forever and never reset**, and the number is STORED on every version and
# never computed at read time. Forgetting is coming (BRIEF.md, parked): old files will be pruned
# one day, and an address computed by counting what is left would shift under him — the twelfth
# story would become the fourth and every number he remembers would be a lie.

def next_chapter(past: list[dict]) -> int:
    """One more than the highest chapter anybody has ever been given. Not a count of stories:
    pruning must never hand out a number twice."""
    top = 0
    for d in past:
        c = d.get("chapter")
        if isinstance(c, int) and c > top:
            top = c
    return top + 1


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
    tell(page, past, persona)
    return 0


def tell(page: dict, past: list[dict], persona: str) -> dict | None:
    """One scene told: the version it becomes, written and ledgered, or None when he gave no
    account. The live run and the retell both come through here, so a retold story is made
    exactly the way a live one is."""
    held = current(past)

    started = time.time()
    prompt = prompt_for(page, held, persona)
    try:
        answer, usage = opus.ask(prompt, TIMEOUT)
        text, title = parse(answer)
    except ValueError as exc:
        log(f"sleeper · {exc}")
        ledger({"room": page["room"], "error": str(exc),
                "seconds": round(time.time() - started, 1)})
        return None

    now = time.time()
    obj = {"ts": now,
           "dream": held.get("dream") if held else dream_id(now),
           # The chapter is taken once, when the story STARTS, and then carried by every
           # version of it — a story that has begun keeps its address however it is rewritten.
           "chapter": (held.get("chapter") if held else None) or next_chapter(past),
           "turn": ((held.get("turn") or 0) + 1) if held else 1,
           "of": TURNS,
           "room": page["room"],
           "text": text,
           # Derived, never a second source: `text` is what he wrote, `parts` is that same
           # string cut at its seams, so nothing downstream re-implements the split.
           "parts": split_parts(text),
           # What he would call it over breakfast. Rewritten with the account, so the newest
           # version's title is the story's name.
           "title": title,
           "model": opus.MODEL,
           "seconds": round(now - started, 1),
           "usage": usage}
    path = write_version(obj)
    ledger({"room": obj["room"], "dream": obj["dream"], "chapter": obj["chapter"],
            "turn": obj["turn"], "of": obj["of"], "title": title,
            "chars": len(text), "model": obj["model"], "seconds": obj["seconds"],
            "usage": usage})
    log(f"dream · {os.path.relpath(path, STREAM)} · {obj['chapter']}:{obj['turn']} · "
        f"“{title or '—'}” · {len(text)} chars · {obj['seconds']}s · " + opus.line(usage))
    # The trickle beside a whole pack of dreams just changed, and so may the story's name.
    push.now()
    return obj


# ---- the retell --------------------------------------------------------------------------------

def retell(chapter: int) -> int:
    """Tell every scene again from `chapter` on, oldest first, as if he had been dreaming them
    one after another all along.

    Born of the gap rule (2026-09-23): it stranded stories of one scene every time the stream
    was stopped, and giving an orphan its four means taking the next story's scenes, which
    moves every story after it — so the only honest repair is to retell the lot from the first
    orphan. This is the one place the "an address never shifts" rule is broken on purpose, by
    hand, with bekh's say-so: the old versions of those chapters go to `dreams/.trash/<stamp>/`
    (the loom and `versions()` both skip dot folders), and the chapters are handed out again
    from `chapter` up.

    Unload the sleeper's job first, or a live tap can tell the newest scene in the middle of
    the retell and jump the watermark past everything still waiting.
    """
    try:
        with open(PERSONA, encoding="utf-8") as f:
            persona = f.read()
    except OSError as exc:
        print(f"no persona at {PERSONA}: {exc}", file=sys.stderr)
        return 1
    gone, kept = [], []
    for path in version_files():
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        c = d.get("chapter") if isinstance(d, dict) else None
        (gone if isinstance(c, int) and c >= chapter else kept).append((path, d))
    if not gone:
        print(f"nothing from chapter {chapter} on", file=sys.stderr)
        return 1
    # The scenes to tell: every unflagged passage past what the kept chapters covered, oldest
    # first — the old versions' rooms are NOT the list, a scene they skipped is told too.
    top = covered([d for _, d in kept])
    rooms = sorted(n for n in loom.stream_room_names() if n > top)

    bin_ = os.path.join(DREAMS, ".trash", time.strftime("%Y%m%d-%H%M%S"))
    for path, _ in gone:
        dest = os.path.join(bin_, os.path.relpath(path, DREAMS))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        os.replace(path, dest)
    print(f"{len(gone)} versions of chapters {chapter}+ moved to "
          f"{os.path.relpath(bin_, STREAM)} · {len(rooms)} scenes to tell", file=sys.stderr)

    told = 0
    for name in rooms:
        page = loom.stream_page(name)
        if page is None or page.get("flag"):
            continue
        obj = tell(page, versions(), persona)
        if obj is None:
            # A missed scene is simply not in the story, as it would not be live; the next one
            # carries on, and the ledger has the row.
            continue
        told += 1
    print(f"{told} scenes told", file=sys.stderr)
    return 0


# ---- the backfill ------------------------------------------------------------------------------

def number(quiet: bool = False) -> int:
    """Give every story already on the shelf a chapter, oldest first. Idempotent by design.

    A hand flag and not a migration that runs at start-up: this is one pass over ~11 stories
    written before the numbering existed, and a numbering that ran by itself would be a second
    place chapters are handed out. It only ADDS the field — a story that has one keeps it, and
    the next new story starts above the highest number here.
    """
    past = versions()
    order: list[str] = []
    for d in past:                                   # versions() is sorted by ts
        if d["dream"] not in order:
            order.append(d["dream"])
    taken = {d["dream"]: d["chapter"] for d in past
             if isinstance(d.get("chapter"), int)}
    at = max(taken.values()) if taken else 0
    chapters = dict(taken)
    for dream in order:
        if dream not in chapters:
            at += 1
            chapters[dream] = at
    written, already = 0, 0
    for path in version_files():
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict) or not isinstance(d.get("dream"), str):
            continue
        if isinstance(d.get("chapter"), int):
            already += 1
            continue
        d["chapter"] = chapters[d["dream"]]
        tmp = f"{path}.{os.getpid()}.part"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        written += 1
        if not quiet:
            print(f"{os.path.relpath(path, STREAM)} · chapter {d['chapter']} · {d['dream']}")
    if not quiet:
        print(f"{len(order)} stories · {written} versions numbered · {already} already had one")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="remembering.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true",
                    help="rewrite the dream once and exit — the only mode; stream.py taps "
                         "this job when a passage lands and it has no clock of its own")
    ap.add_argument("--number", action="store_true",
                    help="give every story on the shelf a chapter, oldest first, and exit. "
                         "A one-off for the stories written before the numbering; idempotent")
    ap.add_argument("--retell", type=int, metavar="CHAPTER",
                    help="bin every version from CHAPTER on and tell those scenes again, "
                         "oldest first, chapters handed out from CHAPTER. Unload the "
                         "sleeper's job first")
    a = ap.parse_args(argv[1:])
    if a.number:
        return number()
    if a.retell is not None:
        return retell(a.retell)
    if TURNS < 1:
        print("STREAM_DREAM_TURNS is at least 1", file=sys.stderr)
        return 2
    return run_once()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
