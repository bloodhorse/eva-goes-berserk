#!/usr/bin/env -S uv run --python 3.12
"""stream.py — one short page every five minutes, with nobody picking.

    uv run --python 3.12 eva/stream/stream.py --once

The dream machine as the brief means it: nemo writes a page, it lands on the shelf, and
bekh reads whatever is newest whenever he picks up his phone. No fan, no reader, no
resolver — the only choices made here are made by lot, and the only hand that ever
touches a page is his mark on it afterwards.

**One page, one process.** There is no loop in this file: launchd's `StartInterval` is the
loop (`com.bekh.eva-stream.plist`). A worker that slept for five minutes in a `while True`
would have to be watched, restarted and reasoned about across a laptop lid closing; a
worker that writes one page and exits has none of those states. What breaks if this goes:
a crash becomes a dead stream instead of one missing page.

**A failed run is a ledger line and exit 0.** llama down, a seed unreadable, a page that
came back empty — all of them write a row and leave quietly, because launchd's throttling
treats a non-zero exit as a reason to back off, and a stream that punishes itself for the
five minutes the GPU was busy is a stream that stops.

**The other two voices are tapped from here.** With STREAM_KICK_INTERPRETER=1 a page that
landed ends by `launchctl kickstart`ing `com.bekh.eva-stream-interpreter` (the reader at the
bedside) and `com.bekh.eva-stream-remembering` (the sleeper remembering the night), neither of
which has an interval of its own. Best-effort: a failure is one log line and nothing else.

Env: STREAM_DIR (ledger + heartbeat, default shelf/stream/), STREAM_KICK_INTERPRETER, STREAM_SEEDS
(shelf/seeds/), STREAM_INTERVAL, STREAM_N_PREDICT, STREAM_TEMP_LO, STREAM_TEMP_HI, plus
loom's own LOOM_SITTINGS and LOOM_LLAMA.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import secrets
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))              # eva/stream
EVA = os.path.dirname(HERE)                                     # eva/
for d in (os.path.join(EVA, "server"), os.path.join(EVA, "cli")):
    if d not in sys.path:
        sys.path.insert(0, d)
import eva  # noqa: E402   the one place a blank room's shape is written down
import loom  # noqa: E402   rooms, names, llama: nothing else here knows how a sitting is written

# ---- the dials ----------------------------------------------------------------------------
# All of them here and overridable by env, because every one of them is a thing bekh will
# want to move after reading a morning's worth of pages, and hunting them through the file
# is how a dial stops being turned.

# What launchd is told, restated here for the status line: the page calls the stream asleep
# when the last success is older than twice this. Change one and change the plist.
INTERVAL = int(os.environ.get("STREAM_INTERVAL", "300"))
# A passage, not a page: ~170 tokens is about half a phone screen. It shipped at 350 and bekh
# cut it after reading the first live ones (2026-09-19): they felt long to him, and what he
# pictures is half a page, a separator, the next passage, on and on. A side effect, ours and
# not his reason: a genre locks in over length, so a shorter passage spends less of itself on
# furniture.
N_PREDICT = int(os.environ.get("STREAM_N_PREDICT", "170"))
# The hunting ground, not the baseline: 1.0 shows nemo's default and nothing else. min_p
# 0.08 cuts the absurd tail first because this build applies temperature LAST, which is why
# 2.5 is still a sentence here.
TEMP_LO = float(os.environ.get("STREAM_TEMP_LO", "1.8"))
TEMP_HI = float(os.environ.get("STREAM_TEMP_HI", "2.5"))
# How much of a starred page is fed back as the next seed. Enough to carry a situation, not
# enough to be a style lesson — a long seed spends the page imitating prose instead of
# standing on the seam (census's --tail exists for the same reason).
TAIL_CHARS = 600
# Conservative by a mile: nemo's window is 8k tokens, a page is 350 of them, and 12k
# characters is roughly 3k tokens. Measured in BYTES below, which for utf-8 can only
# over-count characters — the error is on the side of skipping a seed, never of handing
# llama a document it has to truncate the front off in silence.
SEED_MAX_CHARS = 12000

# The two other voices have no clock of their own: both are launchd jobs with no interval, and
# this is what starts them. bekh, 2026-09-19 — they should start when the dream is finished,
# not on timers of their own, which used to land a note a whole tick late.
KICK = os.environ.get("STREAM_KICK_INTERPRETER") == "1"
KICK_JOBS = ("com.bekh.eva-stream-interpreter",      # the reader at the bedside
             "com.bekh.eva-stream-remembering")      # the sleeper remembering the night
KICK_TIMEOUT = 15

FOLDER = "stream"                       # where the rooms are filed, under the sittings shelf
STREAM = os.environ.get("STREAM_DIR", os.path.join(loom.SHELF, FOLDER))
SEEDS = os.environ.get("STREAM_SEEDS", os.path.join(loom.SHELF, "seeds"))
LEDGER = os.path.join(STREAM, "ledger.jsonl")
HEARTBEAT = os.path.join(STREAM, "heartbeat.json")


# ---- the filter: a column, not a knife ------------------------------------------------------
# A base model's document drifts onto the web, because the web is most of what it ate. These
# rules say "this page went there", and that is ALL they do: a flagged page is written to the
# shelf exactly like any other and the reader simply hides it by default (`?all=1` shows it).
#
# **They are audited against bekh's marks later** — how many pages he marked did this flag? —
# so a false positive costs one page hidden behind a query string and nothing else, and the
# list is meant to be read, argued with and edited. Keep it here, one rule per line, first
# match wins: the name that lands in `meta.flag` is the name the reader prints.
FILTERS: list[tuple[str, re.Pattern]] = [
    ("url", re.compile(r"https?://|\bwww\.[a-z0-9-]+\.|\b[a-z0-9-]+\.(?:com|net|org|edu|gov|io|co\.uk)\b", re.I)),
    ("html", re.compile(r"</?(?:a|p|br|div|span|img|h[1-6]|ul|ol|li|table|tr|td|script|style|strong|em|blockquote)\b[^>]{0,200}>", re.I)),
    ("markdown header", re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+\S", re.M)),
    ("markdown link", re.compile(r"\[[^\]\n]{1,80}\]\([^)\n]{1,200}\)")),
    ("byline", re.compile(r"\b(?:photo|photos|photograph|image|illustration|written|posted|submitted|published|reviewed|edited|translated)\s+by\b", re.I)),
    ("blog chrome", re.compile(r"\b(?:leave a comment|no comments|\d+\s+comments?|post a comment|subscribe|share this|click here|read more|continue reading|author'?s note|filed under|related posts?|permalink|trackback|reply to this)\b", re.I)),
    ("chapter", re.compile(r"^[ \t]*chapter\s+\d", re.I | re.M)),
    ("copyright", re.compile(r"©|\(c\)\s*(?:19|20)\d{2}|all rights reserved|creative commons|unless otherwise stated, the content of this page", re.I)),
    ("bracket tag", re.compile(r"\[(?:wip|oc|edit|deleted|removed|spoilers?|nsfw|tw|cw|citation needed|author'?s note|update)\b[^\]\n]{0,30}\]", re.I)),
    ("handle", re.compile(r"(?:^|[\s(])@[A-Za-z0-9_]{2,30}\b")),
    ("hashtag", re.compile(r"(?:^|[\s(])#[A-Za-z][A-Za-z0-9_]{1,30}\b")),
]


def flag_of(text: str) -> str | None:
    """Which rule this page tripped, or None. First match wins — a footer that is also a url
    is one flag, because the column says "it went to the web", not how many ways."""
    for name, rx in FILTERS:
        if rx.search(text or ""):
            return name
    return None


# ---- the log, the ledger, the heartbeat -----------------------------------------------------
# Same three files berserk keeps, same shapes, because monitor.py is the same dashboard: the
# ledger is what happened, the heartbeat is whether anything is happening at all. Unlike
# berserk's, NEITHER is in git: the whole stream is disposable running state (bekh,
# 2026-09-19), and what survives is the artifact a star writes.

def log(msg: str) -> None:
    """Stderr, stamped. launchd redirects it and nobody tails it live; the stamp is the only
    way to tell a slow page from a hung one after the fact."""
    print(f"{time.strftime('%H:%M:%S')} {msg}", file=sys.stderr, flush=True)


def ledger(row: dict) -> None:
    # `kind` since the interpreter writes to this same file (2026-09-19). Rows from before it
    # existed have none, so everything that reads this treats a missing kind as a page.
    os.makedirs(STREAM, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "kind": "page", **row}, ensure_ascii=False) + "\n")


def read_heartbeat() -> dict:
    try:
        with open(HEARTBEAT, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def beat(ok: bool, room: str | None) -> None:
    """One json object, rewritten whole. Temp-then-replace because the monitor reads it on
    its own clock and half a json is a red dot on a healthy worker.

    `last_ok` is carried over from the file when this run failed: the whole question the
    status line answers is "when did a page last land", and a failed run that zeroed it
    would make one unreachable llama look like a stream that never ran.
    """
    os.makedirs(STREAM, exist_ok=True)
    now = time.time()
    was = read_heartbeat()
    out = {"ts": now,
           "last_ok": now if ok else was.get("last_ok"),
           "room": room or was.get("room"),
           "ok": ok}
    tmp = HEARTBEAT + f".{os.getpid()}.part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    os.replace(tmp, HEARTBEAT)


# ---- the seeds, by lot ----------------------------------------------------------------------
# Two pots and a weighted coin between them. Pot A is everything bekh has ever cut as a seed; pot
# B is the stream feeding on itself — the tail of a page he starred. B is what makes this a
# machine and not a shuffle: his mark is the only thing in the loop, it acts at the NEXT
# page's input and never at generation, which is the brief's whole rule about where his hand
# is allowed to be.

def pot_a() -> list[str]:
    """Every `.txt` under the seeds shelf, recursively, that leaves room for a page.

    Sorted, so `--once` twice in a row draws from the same list in the same order and a
    ledger row can be reproduced. A seed too big to sit under a page is skipped rather than
    trimmed: llama truncates the FRONT of an over-long prompt in silence, and a page grown
    from a document nobody can read back is not evidence of anything.
    """
    out = []
    for dirpath, dirnames, filenames in os.walk(SEEDS):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fname in filenames:
            if not fname.endswith(".txt"):
                continue
            path = os.path.join(dirpath, fname)
            try:
                if os.path.getsize(path) > SEED_MAX_CHARS:
                    continue
            except OSError:
                continue
            out.append(path)
    return sorted(out)


SENT_END = r"[.!?…][\"'”’»)\]]*"
"""The end of a sentence and whatever punctuation closes over it. Not a parser — a tail cut
mid-clause makes every page open on "finish this sentence", which is the one thing a seam is
supposed to avoid."""


def sentences_tail(text: str, chars: int = TAIL_CHARS) -> str:
    """The last `chars` characters of a document, moved forward to a sentence start and back
    to a sentence end. Falls back to the raw tail when the window holds no sentence break —
    a strange page with no full stops in it is still a seed."""
    tail = text[-chars:]
    start = re.search(SENT_END + r"\s+", tail)
    if start:
        tail = tail[start.end():]
    end = None
    for end in re.finditer(SENT_END, tail):
        pass
    if end:
        tail = tail[:end.end()]
    return tail.strip() or text[-chars:].strip()


def pot_b() -> list[tuple[str, str]]:
    """The tails of stream pages bekh starred, as (identity, text).

    `kept` and not `good`: the circle means "kind of nice, i wouldn't keep it" and feeding it
    back would make the stream drift toward the merely nice. Seed plus page, because the tail
    has to carry the situation and a 350-token page often is not a whole one on its own.
    """
    out = []
    try:
        rooms = loom.folder_rooms(FOLDER)
    except ValueError:
        return out
    for room in rooms:
        try:
            with open(loom.sitting_path(room), encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        nodes = d.get("nodes")
        if not isinstance(nodes, dict):
            continue
        root = nodes.get(d.get("root")) or {}
        for n in nodes.values():
            if not isinstance(n, dict) or n.get("kind") != "model" or not n.get("kept"):
                continue
            whole = (root.get("text") or "") + (n.get("text") or "")
            tail = sentences_tail(whole)
            if tail:
                out.append((f"tail:{room}", tail))
    return out


BAG = os.path.join(STREAM, "bag.json")


def from_bag(pot: list[str], rng: random.Random) -> str:
    """One seed out of a shuffle bag: no seed comes back until every other has had its turn.

    Still a lot and still nobody's preference — only drawn WITHOUT replacement. A fresh
    `rng.choice` every five minutes is the birthday problem: on the first day, 62 pages had
    already repeated 16 seeds while 32 of the 78 were never touched, and bekh saw it as "the
    switchboards returning" (2026-09-19). Take the bag out and that is what comes back.

    The bag is a file because the worker is one process per page and remembers nothing. It
    holds what is LEFT of the current shuffle plus everything it has ever been dealt from:
    a seed that appears on the shelf mid-bag is slipped into the remaining stack at a random
    depth instead of waiting out the whole round, and one that was deleted is simply skipped.
    A lost or broken bag file is a reshuffle, never an error.
    """
    try:
        with open(BAG, encoding="utf-8") as f:
            d = json.load(f)
        left, known = list(d.get("left") or []), set(d.get("known") or [])
    except (OSError, ValueError, AttributeError):
        left, known = [], set()
    have = set(pot)
    left = [x for x in left if x in have]
    for x in pot:
        if x not in known:
            left.insert(rng.randrange(len(left) + 1), x)
    if not left:
        left = list(pot)
        rng.shuffle(left)
    path = left.pop(0)
    os.makedirs(STREAM, exist_ok=True)
    tmp = BAG + f".{os.getpid()}.part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"left": left, "known": sorted(have)}, f)
    os.replace(tmp, BAG)
    return path


def draw_seed(rng: random.Random) -> tuple[str, str] | None:
    """(identity, text) by lot, or None when there is nothing to draw.

    A starred tail weighs what one seed weighs, until the stars are half the draws and then
    no more: p(pot B) = min(0.5, |B| / (|A| + |B|)); pot A is then dealt from a shuffle bag
    (`from_bag`), pot B is uniform. NOT a
    flat fair coin — with a fair coin bekh's FIRST star would seed half of all pages, 144 a
    day grown from the same 600 characters, which is the stasis the cyborgism wiki warns of
    (many preferences pulling one way magnetize the stream) arriving on day one. And not
    past a half either, or a month of stars would crowd the shelf's seeds out entirely and
    the stream would only ever eat itself.
    """
    a, b = pot_a(), pot_b()
    p_b = min(0.5, len(b) / (len(a) + len(b))) if b else 0.0
    if b and rng.random() < p_b:
        ident, text = rng.choice(b)
    elif a:
        path = from_bag(a, rng)
        try:
            # newline="" so nothing python thinks about line endings reaches the model
            with open(path, encoding="utf-8", newline="") as f:
                text = f.read()
        except OSError:
            return None
        # Spelled against the seeds folder and not against the shelf, so the identity on a
        # ledger row reads `seeds/short/x.txt` wherever STREAM_SEEDS happens to point.
        ident = "seeds/" + os.path.relpath(path, SEEDS).replace(os.sep, "/")
    elif b:
        ident, text = rng.choice(b)
    else:
        return None
    # The trailing-space trap, measured 2026-09-16: a document ending on a space makes the
    # next token a NUMERAL, every time. Spaces and tabs only, and only at the very end —
    # newlines are the document's own shape and a seed that ends on one means it.
    return ident, re.sub(r"[ \t]+\Z", "", text)


# ---- the page ---------------------------------------------------------------------------

def sampler(rng: random.Random) -> dict:
    """The room's sampler, its temperature drawn per page.

    Everything not named here is eva's room default on purpose — DRY and the repeat penalty
    above all. Base models loop; with nothing punishing repetition a hot page becomes one
    sentence said nine times, which reads as a machine and not as a dream.
    """
    p = json.loads(json.dumps(eva.PARAMS))
    p.update(n_predict=N_PREDICT, stop=[],
             temperature=round(rng.uniform(TEMP_LO, TEMP_HI), 3),
             min_p=0.08, top_k=0, top_p=1.0,
             repeat_penalty=1.05, repeat_last_n=512,
             # The minimum that makes llama answer with probabilities at all. One per token
             # is all that is kept (see `logprobs_of`): the full tables are ~300 KB a room,
             # and 288 rooms a day of them would be a gigabyte a week in git.
             n_probs=1)
    return p


def logprobs_of(probs) -> list[float]:
    """llama's per-token tables, reduced to the chosen token's logprob and nothing else.

    A flat list, one number per generated token — which is what a surprise curve is read off
    (the parked "entropy collapsing along a branch" move in BRIEF.md), and the only part of
    the tables anything here has ever wanted. Reduced BEFORE the room is written, so the
    weight never reaches the disk at all.
    """
    out = []
    for row in probs or []:
        if isinstance(row, dict) and isinstance(row.get("logprob"), (int, float)):
            out.append(row["logprob"])
    return out


def room_name(when: float) -> str:
    """`stream/<YYYY-MM-DD>/<HHMM>` — a day is a folder, so the whole day opens as one
    picture at `https://eva.x/#canvas=stream/<date>` and the names sort chronologically,
    which is what lets `/api/stream` page backwards without reading a single file.

    A name already taken gets a `-2`. Only a hand run inside the same minute can collide
    with the timer, and losing that page would be a lost page for no reason; two lines is
    cheaper than explaining it.
    """
    lt = time.localtime(when)
    stem = f"{FOLDER}/{time.strftime('%Y-%m-%d', lt)}/{time.strftime('%H%M', lt)}"
    name = stem
    for i in range(2, 10):
        if not os.path.exists(loom.sitting_path(name)):
            return name
        name = f"{stem}-{i}"
    return name


def write_page(rng: random.Random) -> int:
    """One page: draw a seed, draw a heat, ask nemo once, write the room. Exit code."""
    drawn = draw_seed(rng)
    if drawn is None:
        log(f"no seeds in {SEEDS} and nothing starred — nothing to dream on")
        ledger({"room": None, "seed": None, "error": "no seed"})
        beat(False, None)
        return 0
    ident, seed = drawn
    params = sampler(rng)

    started = time.time()
    name = room_name(started)
    sitting = eva.blank(name, is_bare=True, root_text=seed)
    sitting["title"] = "stream · " + time.strftime("%Y-%m-%d %H:%M", time.localtime(started))
    sitting["params"] = params

    # The prompt is the root's text and nothing else: a bare room, no header, no turn names,
    # no stop strings. The words "AI" and "assistant" never appear in a document here, and
    # neither does anything else of ours — the seed is the whole document the model sees.
    d = loom.complete(seed, params)
    if d.get("error"):
        log(f"llama · {d['error']}")
        ledger({"room": None, "seed": ident, "temperature": params["temperature"],
                "error": d["error"]})
        beat(False, None)
        return 0
    text = d.get("text") or ""
    if not text.strip():
        # Not an error worth a non-zero exit, and not a room either: an empty page is nothing
        # to read and nothing to mark.
        log("nemo answered nothing")
        ledger({"room": None, "seed": ident, "temperature": params["temperature"],
                "error": "empty page"})
        beat(False, None)
        return 0

    flag = flag_of(text)
    node = {"id": secrets.token_hex(4), "parent": sitting["root"], "kind": "model",
            "text": text, "ts": time.time(), "pruned": False, "posed": False,
            "meta": {"stop_type": d.get("stop_type") or "",
                     "stopping_word": d.get("stopping_word") or "",
                     "tokens_predicted": d.get("tokens_predicted") or 0,
                     "tps": d.get("tps") or 0,
                     # The flat list, never llama's `probs` tables — see logprobs_of.
                     "logprobs": logprobs_of(d.get("probs")),
                     "params": params,
                     "model": (loom.model_info() or {}).get("file"),
                     # Which seed, so a page can be traced back to what it grew on without
                     # the ledger open beside it.
                     "seed": ident,
                     "flag": flag}}
    sitting["nodes"][node["id"]] = node
    sitting["current"] = node["id"]
    loom.write_sitting(sitting)

    ledger({"room": name, "seed": ident, "temperature": params["temperature"],
            "tokens": d.get("tokens_predicted") or 0, "tps": d.get("tps") or 0,
            "flag": flag, "seconds": round(time.time() - started, 1)})
    beat(True, name)
    log(f"{name} · {ident} · t{params['temperature']} · {d.get('tokens_predicted')} tok"
        + (f" · flagged {flag}" if flag else ""))
    # Last, and only on a page that really landed: the reader is started by the dream being
    # finished and by nothing else.
    kick()
    return 0


def kick() -> None:
    """Tap the other two voices, best-effort. Never anything but a log line if one fails.

    Each job is tapped on its own and a failure on one does not touch the other: they are two
    unrelated voices, and a reader that cannot start is no reason for the night to go untold.

    **No `-k`.** launchd does not start a second instance of a job that is already running, so
    a kick that arrives while a reading is in flight is dropped and the two can never overlap —
    which is also why there is no lockfile here. Add `-k` and that becomes the opposite: it
    kills the running job first, so a note being written would be cut off mid-cli-call.

    A failed kick costs one dream its note. That is the dry-run law's acceptable loss, and the
    next dream's kick reads the newest one anyway — which is why nothing retries and why the
    page is never told.
    """
    if not KICK:
        return
    for job in KICK_JOBS:
        cmd = ["launchctl", "kickstart", f"gui/{os.getuid()}/{job}"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=KICK_TIMEOUT)
            if r.returncode != 0:
                log(f"kick · {job} · launchctl said {r.returncode}: "
                    f"{(r.stderr or '').strip()[:120]}")
        except (OSError, subprocess.SubprocessError) as exc:
            log(f"kick · {job} · {exc}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="stream.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true",
                    help="write one page and exit — which is the only thing this does; the "
                         "five-minute loop is launchd's StartInterval, not a sleep in here")
    a = ap.parse_args(argv[1:])
    del a                                   # --once is documentation; there is no other mode
    if TEMP_HI < TEMP_LO:
        print("STREAM_TEMP_HI is below STREAM_TEMP_LO", file=sys.stderr)
        return 2
    return write_page(random.Random())


if __name__ == "__main__":
    sys.exit(main(sys.argv))
