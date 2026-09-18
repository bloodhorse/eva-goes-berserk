#!/usr/bin/env -S uv run --python 3.12 --script
"""wire.py — two base models taking turns on one line, and nobody picking.

    uv run --python 3.12 wire.py --name experiments/wire/hum-plain-nemofirst-01 \
        --doc shelf/seeds/short/08-what-is-that-hum.txt \
        --models a=nemo=http://127.0.0.1:8080,b=gpt2=http://127.0.0.1:8083 \
        --lines 24 --n-predict 40 --temp 1.4
    uv run --python 3.12 wire.py --name experiments/wire/hum-beats-nemocaller-01 \
        --doc shelf/seeds/short/08-what-is-that-hum.txt --beats <a beats file> --first a \
        --models a=nemo=http://127.0.0.1:8080,b=gpt2=http://127.0.0.1:8083

A document opens on a wire — a phone, a switch, a line going faint — and then the two models
write it a line at a time, turn and turn about: each one sees the whole document so far,
neither controls it, one sample per turn, no fan and no picker. What lands on the shelf is the
transcript of a channel between two minds that never read each other.

Bare, neither of them knows there are two of them: each is only continuing a text. `--beats`
is bekh's answer to that (2026-09-18) — a posed line between the turns, the way berserk's beats
work, saying whose turn it is now without ever saying what it is. Two groups of them, because
the seats are not symmetric: **a is the caller, the *i* of the seed; b is the voice on the
line**, and the line that introduces a voice is not the line that introduces a caller. Half
the run goes without beats, so the padding is a thing that can be read against its absence.

It is here because a picker can only ever return what a fan already holds, and everything that
ever moved a fan in this project was on the generating side. So the only hands on this are the
seed and the alternation — the cyborgism wiki's warning about many preferences pulling one way
(a multiverse magnetized into stasis) applies to a loop as much as to a fan, and this loop
chooses nothing.

The shape of the room is the simplest one the page already reads: a **bare** room standing on
the seed, and then a linear spine, each line one model node hanging off the line before it.
`current` walks to the newest node and the file is rewritten after every line, so a page open
on the room watches the transcript grow; the canvas draws a spine as one column of line-cards.

A line ends at the first newline, and wire.py is what ends it: the turn is drawn as a budget of
`--n-predict` tokens with no stop string, and `line_of` cuts the first line out of what came
back (llama's own `stop: ["\\n"]` cannot do it — see `line_of`). The newline that closes the
line is appended here, so every turn starts on a fresh line and the next model reads a clean
seam.

Env: LOOM_SITTINGS (the shelf), LOOM_LLAMA (only as eva's fallback; --models is explicit).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import time
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.realpath(__file__))              # eva/cli, where eva.py is
SERVER = os.path.join(os.path.dirname(HERE), "server")          # eva/server, where loom.py is
for d in (SERVER, HERE):
    if d not in sys.path:
        sys.path.insert(0, d)
import census  # noqa: E402   props / count_tokens / one_line: one set of small reads, not three
import eva  # noqa: E402
from loom import name_ok, prompt_to, sitting_path, write_sitting  # noqa: E402

ROLES = ("a", "b")
"""The two seats, and what they are: **a is the caller**, the *i* the seed already stands in;
**b is the voice on the line**. `--first` says which of them writes the opening line and the
turns alternate from there, so the letter — not the model's name — is what `--temps` and the
beats file talk about: a run with the two models swapped between the seats is the same score
read by different players."""


def read_beats(path: str) -> dict[str, list[str]]:
    """A beats file: two groups, blank-line separated — before the VOICE speaks, then before
    the CALLER speaks. `{"b": [...], "a": [...]}`, keyed by the seat the beat introduces.

    Two groups and not one because the seats are not symmetric: a line that hands the turn to
    something at the far end of a wire reads nothing like a line that hands it back to the
    person holding the receiver, and one pile of beats used for both would make the caller
    answer himself. A `#` line is a comment and is skipped — these lines are ours, the project
    marks posed text as posed, and the note saying who wrote them belongs in the file.
    """
    groups: list[list[str]] = [[]]
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line.startswith("#"):
                continue
            if not line:
                if groups[-1]:
                    groups.append([])       # a blank line ends a group, a run of them is one
                continue
            groups[-1].append(line)
    groups = [g for g in groups if g]
    if len(groups) != 2:
        raise ValueError(f"expected two groups of beats separated by a blank line, "
                         f"got {len(groups)}")
    return {"b": groups[0], "a": groups[1]}


def wires_of(spec: str) -> list[tuple[str, str, str]]:
    """`a=nemo=http://…:8080,b=gpt2=http://…:8083` into (role, name, url), a first.

    Two entries, roles exactly `a` and `b`. The role is separate from the name because the
    alternation is the whole experiment: which seat a model sits in has to be sayable without
    renaming the model, or a run with the models swapped could not be told from a rerun.
    """
    out: dict[str, tuple[str, str, str]] = {}
    for piece in str(spec).split(","):
        piece = piece.strip()
        if not piece:
            continue
        bits = piece.split("=", 2)
        if len(bits) != 3:
            raise ValueError(f"expected ROLE=NAME=URL, got {piece!r}")
        role, name, url = (b.strip() for b in bits)
        if role not in ROLES:
            raise ValueError(f"a role is 'a' or 'b': {role!r}")
        if role in out:
            raise ValueError(f"two models in seat {role!r}")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name or ""):
            raise ValueError(f"a model name is letters, digits, _ . and -: {name!r}")
        if urlparse(url).hostname is None:
            raise ValueError(f"not a url: {url!r}")
        out[role] = (role, name, url.rstrip("/"))
    if sorted(out) != list(ROLES):
        raise ValueError("--models needs exactly two: a=NAME=URL,b=NAME=URL")
    return [out[r] for r in ROLES]


def temps_of(spec: str, default: float) -> dict[str, float]:
    """`a=1.4,b=2.0` per seat, or the same heat for both. A bare number is also accepted, so
    --temps and --temp never disagree about which one won."""
    out = {r: float(default) for r in ROLES}
    spec = str(spec or "").strip()
    if not spec:
        return out
    for piece in spec.split(","):
        piece = piece.strip()
        if not piece:
            continue
        role, sep, val = piece.partition("=")
        role, val = role.strip(), val.strip()
        if not sep:
            out = {r: float(role) for r in ROLES}   # --temps 1.8 means both
            continue
        if role not in ROLES:
            raise ValueError(f"a role is 'a' or 'b': {role!r}")
        out[role] = float(val)
    return out


def line_of(text: str) -> str:
    """The first line the model actually wrote, and nothing after it.

    **Why this is not llama's `stop: ["\\n"]`** (measured against gpt-2 XL, 2026-09-18, and the
    reason the first chain came back with twenty-four empty turns): a base model handed a prompt
    that ends on a newline answers with ANOTHER newline — it is opening a paragraph, which is
    what the corpus does there. llama's stop string fires on that first token, hands back an
    empty string, and the seat looks mute when it had a whole line ready one token later. With
    gpt-2 that was 6 of 6. So the turn is drawn as a budget of `--n-predict` tokens with no stop
    at all, and the line is cut here: leading blank lines skipped, everything after the first
    line thrown away.

    Trailing whitespace goes — it is invisible and poisonous, a document ending on a space makes
    the next token a numeral (the register findings, 2026-09-16) — and a leading space stays,
    because after a seed that ends mid-clause the space belongs to the line. Where the document
    does end mid-clause the model's first token is essentially never a newline, so skipping
    blank lines cannot eat the continuation; where it ends on a newline, skipping them is the
    whole point. The newline that closes the line is ours, appended by the caller.
    """
    for piece in text.split("\n"):
        if piece.strip():
            return piece.rstrip()
    return ""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="wire.py", description=__doc__.splitlines()[0])
    ap.add_argument("--name", required=True,
                    help="the room to make; a path files it in a folder "
                         "(experiments/wire/fainter-ab-01)")
    ap.add_argument("--doc", required=True,
                    help="the seed document: the room's root, verbatim")
    ap.add_argument("--models", required=True, metavar="a=NAME=URL,b=NAME=URL",
                    help="the two seats: a is the caller, b is the voice on the line")
    ap.add_argument("--first", choices=ROLES, default="a",
                    help="who writes the opening line (default a, the caller). Where the seed "
                         "already ends on a line that hands the turn to the far end, say b")
    ap.add_argument("--beats", default="", metavar="FILE",
                    help="a posed line between the turns: two blank-line separated groups, "
                         "before the voice speaks then before the caller speaks, each rotated "
                         "in order. The opening line never gets one")
    ap.add_argument("--lines", type=int, default=24, help="how many lines in all (default 24)")
    ap.add_argument("--n-predict", type=int, default=40,
                    help="the cap on one line, if no newline comes first (default 40)")
    ap.add_argument("--temp", type=float, default=1.4, help="temperature for both (default 1.4)")
    ap.add_argument("--temps", default="", metavar="a=1.4,b=2.0",
                    help="a temperature per seat, if the two should run at different heats")
    a = ap.parse_args(argv[1:])

    if not name_ok(a.name):
        print("names are letters, digits, _ . - and / for a folder", file=sys.stderr)
        return 2
    # A no-op on a taken name, exactly as census and eva's /new are: this writes unattended and
    # the one thing it must never do is land on top of a real room.
    if os.path.exists(sitting_path(a.name)):
        print(f"{a.name} already exists, nothing changed", file=sys.stderr)
        return 1
    if a.lines < 1:
        print("--lines is at least 1", file=sys.stderr)
        return 2
    try:
        seats = wires_of(a.models)
        temps = temps_of(a.temps, a.temp)
    except ValueError as exc:
        print(f"bad --models/--temps: {exc}", file=sys.stderr)
        return 2
    beats: dict[str, list[str]] = {}
    if a.beats:
        try:
            beats = read_beats(a.beats)
        except (OSError, ValueError) as exc:
            print(f"bad --beats: {exc}", file=sys.stderr)
            return 2
    try:
        # newline="" so nothing python thinks about line endings reaches the model
        with open(a.doc, encoding="utf-8", newline="") as f:
            doc = f.read()
    except OSError as exc:
        print(f"can't read {a.doc}: {exc}", file=sys.stderr)
        return 1

    sitting = eva.blank(a.name, is_bare=True, root_text=doc)
    p = sitting["params"]
    # A budget, not a line length: the turn is drawn with NO stop string (see line_of — llama's
    # `stop: ["\n"]` catches the paragraph-opening newline a base model answers a newline with,
    # and every gpt-2 turn came back empty), and the line is cut out of what came back. So most
    # of these tokens are written and thrown away, which is the price of a legible seam.
    p["n_predict"] = a.n_predict
    p["stop"] = []
    # Everything else is the room's default on purpose: min_p 0.08, xtc off, and the brakes
    # (dry 0.8, repeat 1.05) ON — two voices answering each other echo, and with nothing
    # punishing repetition a wire turns into one line said twice for twenty turns.
    write_sitting(sitting)

    where = {role: url for role, _, url in seats}
    named = {role: name for role, name, _ in seats}
    # One /props per server per RUN, never per turn: it is the window the document has to keep
    # fitting inside, and gpt-2's is 1024 of its own tokens.
    windows = {role: census.props(url).get("n_ctx") for role, _, url in seats}

    print(f"wire · {a.name} · {a.lines} lines · {a.first} first · "
          + " ".join(f"{r}={named[r]}@t{temps[r]}" for r in ROLES)
          + f" · beats {os.path.basename(a.beats) if a.beats else 'none'}"
          + f" · n_predict {a.n_predict} · root {len(doc)} chars", flush=True)
    for role in ROLES:
        if not windows[role]:
            print(f"note · {named[role]} does not say its window; no context check on that seat",
                  file=sys.stderr, flush=True)

    at = sitting["current"]                    # the root, then the newest line
    last = None                                # the newest model node, for a stopped stamp
    stopped = ""
    empties = {r: 0 for r in ROLES}            # misses per seat, for the closing line
    tokens = {r: [0, 0] for r in ROLES}        # [tokens, lines] per seat
    spent = {r: 0 for r in ROLES}              # how far each group of beats has been rotated
    other = {"a": "b", "b": "a"}

    for turn in range(1, a.lines + 1):
        # Whose turn it is comes from the turn NUMBER and never from who wrote last, so one
        # miss (below) cannot shift the whole alternation off its parity. `--first` is the
        # seed's business: where the document already ends on a line handing the turn to the
        # far end, the voice speaks first and the opening beat would say it a second time.
        role = a.first if turn % 2 else other[a.first]

        # The beat introducing whoever is about to speak, rotated through that seat's own
        # group. Never before the opening line: the seed's last sentence is the only
        # introduction that turn is allowed to have, whichever seat it hands to.
        beat_line = ""
        if beats and turn > 1:
            group = beats[role]
            beat_line = group[spent[role] % len(group)]
        # `\n\n` before and `\n` after, exactly as berserk poses one: the line before ends
        # wherever it ended, the beat stands alone, and the model opens on the line after it.
        beat_text = "\n\n" + beat_line + "\n" if beat_line else ""
        prompt = prompt_to(sitting, at) + beat_text

        # Per turn, because the document grows: the check has to be against what this seat is
        # about to be handed — the beat included — on its own tokenizer, or a 1024-window model
        # gets a prompt llama silently cuts the FRONT off, and a model that read a different
        # document is not on this wire at all. Stop the chain instead; never truncate.
        n_ctx = windows[role]
        need = census.count_tokens(where[role], prompt) if n_ctx else None
        if n_ctx and need is not None and need + a.n_predict > n_ctx:
            stopped = "context"
            print(f"stop · context · {named[role]} · document is {need} tokens "
                  f"+ {a.n_predict} to write, window is {n_ctx}", flush=True)
            break

        # The beat becomes a node only once the turn is really going to happen, so a room that
        # stopped for context never ends on one of our lines nobody answered.
        if beat_text:
            bid = secrets.token_hex(4)
            # `kind: "human"` and `posed`, which is what the page and eva already mean by "not
            # the model's" — a beat written as a model node would put our words into the
            # record as something a base model said. `meta.beat` names what kind of posed line
            # it is, since a wire room has no other.
            sitting["nodes"][bid] = {"id": bid, "parent": at, "kind": "human",
                                     "text": beat_text, "ts": time.time(),
                                     "pruned": False, "posed": True, "meta": {"beat": True}}
            sitting["current"] = bid
            at = bid
            spent[role] += 1
            write_sitting(sitting)

        # One retry at the same seat, then the other model takes the turn. An empty line is
        # what a base model standing on a fresh newline does when it wants a paragraph break,
        # and a wire that wrote it down would spend the run on blank lines.
        wrote, tries, d = role, 0, None
        for wrote in (role, role, other[role]):
            try:
                d = eva.complete_stream(prompt, dict(p, temperature=temps[wrote]),
                                        lambda piece: None, where[wrote])
            except KeyboardInterrupt:
                # The socket is down, so llama has its slot back; everything before this line
                # is on disk. A half-streamed line is dropped: the dry-run law.
                stopped = "cut"
                break
            if d.get("error"):
                print(f"turn {turn} · {named[wrote]} · {d['error']}", file=sys.stderr, flush=True)
                return 1
            if line_of(d["text"]).strip():
                break
            tries += 1
            empties[role] += 1
        if stopped == "cut":
            break

        line = line_of(d["text"])
        node = {"id": secrets.token_hex(4), "parent": at, "kind": "model",
                # Ours, not llama's: the stop string was eaten, and every turn has to start on
                # a fresh line or the two voices run together mid-sentence.
                "text": line + "\n",
                "ts": time.time(), "pruned": False, "posed": False,
                "meta": {"stop_type": d["stop_type"], "stopping_word": d["stopping_word"],
                         "tokens_predicted": d["tokens_predicted"], "tps": d["tps"],
                         "probs": d.get("probs"),
                         "params": dict(p, temperature=temps[wrote]),
                         # Who wrote it, by NAME — the same stamp census leaves, so the canvas
                         # and the reveal tell these cards apart the way they do a census's.
                         "model": named[wrote], "turn": turn}}
        if tries:
            # The miss is part of the record: an empty reply says something about the seam, and
            # a swapped turn is the one place the alternation breaks.
            node["meta"]["empty_retries"] = tries
        if wrote != role:
            node["meta"]["swapped_from"] = named[role]
        sitting["nodes"][node["id"]] = node
        sitting["current"] = node["id"]
        at = node["id"]
        last = node
        tokens[wrote][0] += d["tokens_predicted"]
        tokens[wrote][1] += 1
        # After every line, not at the end: a page open on this room watches it grow, and a run
        # killed at line 19 keeps 18.
        write_sitting(sitting)
        print(f"turn {turn} · {named[wrote]} · {d['tokens_predicted']} tok"
              + (f" · {tries} empty" if tries else "")
              + f" · \"{census.one_line(line)}\"", flush=True)

    if stopped and last:
        # On the last node, because that is where the document ends: the room itself says why
        # it is 11 lines long and not 24, and nothing has to be read off a terminal that is gone.
        last["meta"]["stopped"] = stopped
        write_sitting(sitting)

    lines = sum(1 for n in sitting["nodes"].values() if n["kind"] == "model")
    per = " · ".join(f"{named[r]} {tokens[r][0]} tok in {tokens[r][1]}" for r in ROLES)
    miss = " · ".join(f"{named[r]} {empties[r]} empty" for r in ROLES if empties[r])
    print(f"{'stopped (' + stopped + '):' if stopped else 'done:'} {lines} lines · {per}"
          + (f" · {miss}" if miss else "")
          + f" · {sitting_path(a.name)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
