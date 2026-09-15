#!/usr/bin/env -S uv run --python 3.12 --script
"""census.py — one document, n continuations, unattended.

    uv run --python 3.12 census.py --name wide --doc seed.txt --n 50 --temps 0.8,1.2,1.6
    uv run --python 3.12 census.py --name long --empty --bare --n 1 --n-predict 4000

The loom and eva are both a person picking. This is the other half of the instrument: hand
it a document and walk away, and come back to fifty continuations of it side by side, taken
across a set of temperatures. Nothing here chooses anything — the room is left standing on
its root with every branch hanging off it, which is exactly the shape the page's "choose an
answer" screen already reads.

It writes through loom.py's `write_sitting` after EVERY branch, so the page opened on that
room shows the pile growing on a reload; and it talks to llama through eva's own streaming
client, so there is one transport in this project and not three.

Its liveness ledger is the sitting file itself, plus one line per finished branch on stdout.
A branch in flight redraws a byte count on the same line when stdout is a terminal, which is
the difference between "the 4000-token run is working" and "the 4000-token run is hung".

Env: LOOM_LLAMA (llama-server directly, default http://127.0.0.1:8080), LOOM_SITTINGS.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import eva  # noqa: E402
from loom import NAME_RE, SITTINGS, write_sitting  # noqa: E402


def temps_of(s: str) -> list[float]:
    out = []
    for piece in str(s).split(","):
        piece = piece.strip()
        if piece:
            out.append(float(piece))
    if not out:
        raise ValueError("no temperatures")
    return out


def one_line(text: str, width: int = 60) -> str:
    """The branch's opening, flattened. Newlines are collapsed on purpose: this line is a
    receipt in a column of receipts, and a continuation that opens with three blank lines
    would push the next ten off the screen."""
    flat = " ".join(text.split())
    return flat[:width]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="census.py", description=__doc__.splitlines()[0])
    ap.add_argument("--name", required=True, help="the room to make (letters, digits, _ . -)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--doc", help="a file whose contents become the root, verbatim")
    src.add_argument("--empty", action="store_true", help="an empty root: the model starts it")
    ap.add_argument("--n", type=int, default=10, help="how many continuations (default 10)")
    ap.add_argument("--temps", default="1.0",
                    help="comma-separated temperatures, used round-robin (default 1.0)")
    ap.add_argument("--n-predict", type=int, default=None, help="tokens per branch")
    ap.add_argument("--bare", action="store_true",
                    help="no turn names and no stop strings: pure continuation")
    a = ap.parse_args(argv[1:])

    if not NAME_RE.match(a.name or ""):
        print("names are letters, digits, _ . - and up to 64 of them", file=sys.stderr)
        return 2
    # A no-op on a name that is taken, exactly as eva's /new is: this writes for hours
    # unattended, and the one thing it must never do is land on top of a real room.
    if os.path.exists(os.path.join(SITTINGS, a.name + ".json")):
        print(f"{a.name} already exists, nothing changed", file=sys.stderr)
        return 1
    if a.n < 1:
        print("--n is at least 1", file=sys.stderr)
        return 2
    try:
        temps = temps_of(a.temps)
    except ValueError as exc:
        print(f"bad --temps: {exc}", file=sys.stderr)
        return 2

    doc = ""
    if a.doc:
        try:
            # newline="" so nothing python thinks about line endings reaches the model
            with open(a.doc, encoding="utf-8", newline="") as f:
                doc = f.read()
        except OSError as exc:
            print(f"can't read {a.doc}: {exc}", file=sys.stderr)
            return 1

    sitting = eva.blank(a.name, a.bare, doc)
    if a.n_predict:
        sitting["params"]["n_predict"] = a.n_predict
    root = sitting["nodes"][sitting["root"]]
    write_sitting(sitting)

    live = sys.stdout.isatty()
    print(f"census · {a.name} · {a.n} branches · temps {', '.join(str(t) for t in temps)}"
          f" · n_predict {sitting['params']['n_predict']} · root {len(doc)} chars", flush=True)

    cut = False
    for i in range(1, a.n + 1):
        temp = temps[(i - 1) % len(temps)]
        params = json.loads(json.dumps(sitting["params"]))
        params["temperature"] = temp
        got = {"n": 0}

        def on_chunk(piece: str, got=got, i=i, temp=temp) -> None:
            if not live:
                return
            got["n"] += len(piece)
            sys.stdout.write(f"\r{i:>4}  t {temp:<5} … {got['n']} chars")
            sys.stdout.flush()

        try:
            # The prompt is the root's text and nothing else — every branch is a child of
            # the root, so the concatenation along root→node IS the document, verbatim.
            d = eva.complete_stream(root["text"], params, on_chunk)
        except KeyboardInterrupt:
            # The socket is already down, so llama has its slot back. Everything that
            # finished is on disk; the half-written branch is dropped, because a truncated
            # continuation nobody asked for is indistinguishable later from one the model
            # actually ended there.
            cut = True
            break
        if live:
            sys.stdout.write("\r" + " " * 46 + "\r")
        if d.get("error"):
            print(f"{i:>4}  {d['error']}", file=sys.stderr, flush=True)
            return 1

        node = {"id": secrets.token_hex(4), "parent": root["id"], "kind": "model",
                "text": d["text"], "ts": time.time(), "pruned": False, "posed": False,
                "meta": {"stop_type": d["stop_type"], "stopping_word": d["stopping_word"],
                         "tokens_predicted": d["tokens_predicted"], "tps": d["tps"],
                         "probs": d.get("probs"), "params": params}}
        sitting["nodes"][node["id"]] = node
        # After every branch, not at the end: a page open on this room shows the pile
        # growing, and a run killed at branch 38 keeps 37.
        write_sitting(sitting)
        print(f"{i:>4}  t {temp:<5} {d['tokens_predicted']:>5} tok  "
              f"{(d['stop_type'] or '?'):<5}  {one_line(d['text'])}", flush=True)

    live_nodes = sum(1 for n in sitting["nodes"].values() if n["kind"] == "model")
    print(f"{'cut at' if cut else 'done:'} {live_nodes} branches · "
          f"{os.path.join(SITTINGS, a.name + '.json')}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
