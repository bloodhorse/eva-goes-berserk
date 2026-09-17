#!/usr/bin/env -S uv run --python 3.12 --script
"""census.py — one document, n continuations, unattended.

    uv run --python 3.12 census.py --name wide --doc seed.txt --n 50 --temps 0.8,1.2,1.6
    uv run --python 3.12 census.py --name long --empty --bare --n 1 --n-predict 4000
    uv run --python 3.12 census.py --name two --doc seed.txt --n 30 --tail 260 \
        --models nemo=http://127.0.0.1:8080,pythia=http://127.0.0.1:8081

The loom and eva are both a person picking. This is the other half of the instrument: hand
it a document and walk away, and come back to fifty continuations of it side by side, taken
across a set of temperatures. Nothing here chooses anything — the room is left standing on
its root with every branch hanging off it, which is exactly the shape the page's "choose an
answer" screen already reads.

With `--models` it is a *blind comparison* instead of a census: one document, several
llama-servers, the branches split evenly between them and the order they are written to the
room shuffled, so that nothing about a card's position says which model wrote it. Every
branch is stamped `meta.model`; that stamp is the key, and it is in the file rather than on
the screen, which is what lets bekh read the pile first and be told after.

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
import http.client
import json
import os
import random
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
import eva  # noqa: E402
from loom import name_ok, sitting_path, write_sitting  # noqa: E402


def temps_of(s: str) -> list[float]:
    out = []
    for piece in str(s).split(","):
        piece = piece.strip()
        if piece:
            out.append(float(piece))
    if not out:
        raise ValueError("no temperatures")
    return out


def models_of(spec: str) -> list[tuple[str, str]]:
    """`nemo=http://…:8080,pythia=http://…:8081` into pairs, in the order given.

    The order matters for one thing only: the first model's tokenizer is the one `--tail`
    measures the document with. Everything else about a model here is its name (which
    becomes `meta.model`, and is therefore what the key reads) and its url.
    """
    out: list[tuple[str, str]] = []
    for piece in str(spec).split(","):
        piece = piece.strip()
        if not piece:
            continue
        name, sep, url = piece.partition("=")
        name, url = name.strip(), url.strip()
        if not sep or not name or not url:
            raise ValueError(f"expected NAME=URL, got {piece!r}")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise ValueError(f"a model name is letters, digits, _ . and -: {name!r}")
        if urlparse(url).hostname is None:
            raise ValueError(f"not a url: {url!r}")
        if name in [n for n, _ in out]:
            raise ValueError(f"two models called {name!r}")
        out.append((name, url.rstrip("/")))
    if not out:
        raise ValueError("no models")
    return out


def plan(n: int, temps: list[float], names: list[str], seed: str,
         shuffle: bool = True) -> list[tuple[str, float]]:
    """Which model draws which branch, in the order they will be WRITTEN.

    Even shares (30 across three is 10/10/10; a remainder goes to the models named first),
    and inside each model's share the temperatures round-robin, so every model gets the same
    slice of the temperature range and a hot pile is not accidentally one model's.

    Then shuffled, and shuffled from the ROOM NAME: position in the fan must carry no
    information about who wrote a card, and a run repeated under the same name has to lay
    out the same way or the room could not be rebuilt. The seed is the string itself and not
    `hash()`, which is salted per process for str and would differ between two runs.

    `shuffle` is off for the plain one-model census, where the shuffle would buy nothing and
    would silently reorder the temperature round-robin every existing run reads back.
    """
    jobs: list[tuple[str, float]] = []
    base, extra = divmod(n, len(names))
    for i, name in enumerate(names):
        share = base + (1 if i < extra else 0)
        for j in range(share):
            jobs.append((name, temps[j % len(temps)]))
    if shuffle:
        random.Random(seed).shuffle(jobs)
    return jobs


def get_json(url: str, route: str, body: dict | None = None, timeout: int = 30):
    """One small request to one llama-server. None on anything that isn't a 200 of json.

    loom.py has `model_info` and `tokenize` already, and they are the same two reads — but
    both are wired to loom's single `LLAMA` constant. A census that talks to three servers
    in one run needs the endpoint as an argument; pointing a module constant at each server
    in turn would make the answer depend on the order the calls happened in.
    """
    u = urlparse(url)
    conn = http.client.HTTPConnection(u.hostname or "127.0.0.1", u.port or 80, timeout=timeout)
    prefix = (u.path or "").rstrip("/")
    try:
        if body is None:
            conn.request("GET", prefix + route)
        else:
            conn.request("POST", prefix + route,
                         body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                         headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        raw = resp.read()
        if resp.status != 200:
            return None
        return json.loads(raw)
    except (OSError, http.client.HTTPException, ValueError):
        return None
    finally:
        try:
            conn.close()
        except OSError:
            pass


def props(url: str) -> dict:
    """`{"file", "n_ctx"}` off /props — the same two fields loom's `model_info` reads for an
    artifact, per endpoint. Empty when the server is down or answers something else: a
    census with no name for its model is still a census, it just can't say what drew it."""
    d = get_json(url, "/props")
    if not isinstance(d, dict):
        return {}
    path = d.get("model_path") if isinstance(d.get("model_path"), str) else ""
    gen = d.get("default_generation_settings")
    n_ctx = gen.get("n_ctx") if isinstance(gen, dict) else None
    return {"file": os.path.basename(path) or None,
            "n_ctx": n_ctx if isinstance(n_ctx, int) and n_ctx > 0 else None}


def count_tokens(url: str, text: str) -> int | None:
    """How many tokens THIS server makes of this text. None when it won't say.

    Its own tokenizer and not a ratio, because the whole point of asking is that the models
    being compared tokenize differently — gpt-2's window is 1024 of its tokens, not of
    nemo's, and a four-characters-to-a-token guess is exactly the kind of estimate that puts
    a truncated prompt in front of one model and nobody notices.
    """
    if not text:
        return 0
    d = get_json(url, "/tokenize", {"content": text, "add_special": False})
    toks = d.get("tokens") if isinstance(d, dict) else None
    return len(toks) if isinstance(toks, list) else None


def trim_tail(doc: str, want: int, count) -> str:
    """The document's last `want` tokens, moved FORWARD to a whole paragraph.

    A long seed is a style lesson: the model spends the fan imitating nine hundred words of
    somebody's prose instead of standing where the document stopped. So the tail is cut —
    and cut at a paragraph break, never at a token boundary, because a seed that opens
    mid-sentence makes the first fork "finish this clause" for every model at once.

    Forward, i.e. the longest run of trailing paragraphs that still fits: the end of the
    document is what must survive (the seam the fan is standing on), the beginning is what
    is spent. A last paragraph already longer than the budget falls back to sentence starts
    inside it, and a single sentence longer than the budget is kept whole — over the budget
    beats opening mid-clause.
    """
    if want <= 0:
        return doc
    n = count(doc)
    if n is None or n <= want:
        return doc
    # Split keeping the separators, so the pieces concatenate back to the document exactly:
    # what this returns is always a verbatim suffix of the seed, never a reflow of it.
    paras = re.split(r"(\n\s*\n)", doc)
    best = ""
    for i in range(len(paras) - 1, -1, -1):
        cand = "".join(paras[i:]).lstrip("\n")
        c = count(cand)
        if c is None:
            break
        if c > want:
            break
        best = cand
    if best.strip():
        return best
    # No paragraph break inside the budget: sentences of the last paragraph instead.
    tail = paras[-1] if paras else doc
    sents = re.split(r"(?<=[.!?…])(\s+)", tail)
    best = ""
    for i in range(len(sents) - 1, -1, -1):
        cand = "".join(sents[i:]).lstrip()
        c = count(cand)
        if c is None or c > want:
            if not best:
                best = cand          # one sentence over budget, kept whole
            break
        best = cand
    return best or doc


def coerce(current, val: str):
    """A typed value for --set, read from what the param already holds — except for numbers,
    which are read from what was TYPED: the page's json writes `temperature: 1` as an int,
    and following the stored type would refuse 0.9 on a room the browser made. (eva's /set
    has the same rule, for the same reason.)"""
    if isinstance(current, bool):
        return val.lower() in ("1", "true", "yes", "on")
    if isinstance(current, (int, float)):
        return int(val) if val.lstrip("-").isdigit() else float(val)
    if isinstance(current, list):
        out = json.loads(val)
        if not isinstance(out, list):
            raise ValueError("expected a json list")
        return out
    return val


def one_line(text: str, width: int = 60) -> str:
    """The branch's opening, flattened. Newlines are collapsed on purpose: this line is a
    receipt in a column of receipts, and a continuation that opens with three blank lines
    would push the next ten off the screen."""
    flat = " ".join(text.split())
    return flat[:width]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="census.py", description=__doc__.splitlines()[0])
    ap.add_argument("--name", required=True,
                    help="the room to make; a path files it in a folder "
                         "(experiments/basin/smoke-01)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--doc", help="a file whose contents become the root, verbatim")
    src.add_argument("--empty", action="store_true", help="an empty root: the model starts it")
    ap.add_argument("--n", type=int, default=10, help="how many continuations (default 10)")
    ap.add_argument("--temps", default="1.0",
                    help="comma-separated temperatures, used round-robin (default 1.0)")
    ap.add_argument("--n-predict", type=int, default=None, help="tokens per branch")
    ap.add_argument("--bare", action="store_true",
                    help="no turn names and no stop strings: pure continuation")
    # One escape hatch instead of a flag per sampler field: everything in PARAMS is
    # reachable, and a field llama grows next month needs no change here.
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="any sampler field, e.g. --set xtc_probability=0.5 "
                         "--set ignore_eos=true (repeatable)")
    ap.add_argument("--models", default="", metavar="NAME=URL[,NAME=URL…]",
                    help="split the branches evenly between several llama-servers, shuffle "
                         "the order they are written in, and stamp each with meta.model")
    ap.add_argument("--tail", type=int, default=0, metavar="N",
                    help="cut the document to its last N tokens, forward to a paragraph "
                         "break; the room's root IS the cut text")
    a = ap.parse_args(argv[1:])

    if not name_ok(a.name):
        print("names are letters, digits, _ . - and / for a folder", file=sys.stderr)
        return 2
    # A no-op on a name that is taken, exactly as eva's /new is: this writes for hours
    # unattended, and the one thing it must never do is land on top of a real room.
    if os.path.exists(sitting_path(a.name)):
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

    # Named models, or the one endpoint this project has always talked to. `eva.LLAMA` and
    # not the env var directly, because that is the name the tests move to point at a stub.
    if a.models:
        try:
            models = models_of(a.models)
        except ValueError as exc:
            print(f"bad --models: {exc}", file=sys.stderr)
            return 2
    else:
        models = [("", eva.LLAMA)]

    doc = ""
    if a.doc:
        try:
            # newline="" so nothing python thinks about line endings reaches the model
            with open(a.doc, encoding="utf-8", newline="") as f:
                doc = f.read()
        except OSError as exc:
            print(f"can't read {a.doc}: {exc}", file=sys.stderr)
            return 1

    if a.tail and doc:
        # Before the room is made, so the ROOT is the cut text: what bekh reads as the seed
        # has to be the exact string every model was handed, or the seed on the page and
        # the seed on the wire are two different documents.
        ruler = models[0][1]
        was = len(doc)
        doc = trim_tail(doc, a.tail, lambda t: count_tokens(ruler, t))
        if len(doc) != was:
            print(f"tail · {a.tail} tokens by {models[0][0] or 'llama'} · "
                  f"{was} chars → {len(doc)}", flush=True)

    sitting = eva.blank(a.name, a.bare, doc)
    if a.n_predict:
        sitting["params"]["n_predict"] = a.n_predict
    for pair in a.set:
        key, _, val = str(pair).partition("=")
        key = key.strip()
        # `grammar` is llama's, not the page's: a GBNF string that pins the SHAPE of a branch
        # (`[a-z]+ "-witch"`) while the sampler keeps the letters free. The one field allowed in
        # from outside PARAMS, because the page has no drawer for it and the walks want it.
        if key == "grammar":
            sitting["params"]["grammar"] = val.strip()
            continue
        if key not in sitting["params"]:
            print(f"no such param: {key}", file=sys.stderr)
            return 2
        try:
            sitting["params"][key] = coerce(sitting["params"][key], val.strip())
        except ValueError as exc:
            print(f"bad value for {key}: {exc}", file=sys.stderr)
            return 2
    root = sitting["nodes"][sitting["root"]]
    write_sitting(sitting)

    where = dict(models)
    n_predict = sitting["params"]["n_predict"]
    # One /props per model per RUN, never per branch: it is the model's name for the stamp
    # and, where the server says so, the window the prompt has to fit inside.
    seen_props = {name: props(url) for name, url in models}
    if not a.models:
        # Unchanged behaviour, one thing added: the branches say what drew them. The file
        # name llama reports is the honest best available — the same string an artifact is
        # saved with, so the two records name a model the same way.
        stamp = {"": (seen_props[""].get("file") or "")}
    else:
        stamp = {name: name for name, _ in models}
        for name, url in list(models):
            n_ctx = seen_props[name].get("n_ctx")
            need = count_tokens(url, root["text"])
            if n_ctx and need is not None and need + n_predict > n_ctx:
                # Skipped, not truncated: llama would silently drop the FRONT of the
                # document, and a model that read a different seed is not in the comparison
                # at all — a missing pile is legible, a secretly shortened one is not.
                print(f"skip · {name} · seed is {need} tokens + {n_predict} to write, "
                      f"window is {n_ctx}", file=sys.stderr, flush=True)
                models = [(m, u) for m, u in models if m != name]
        if not models:
            print("no model can hold this seed, nothing drawn", file=sys.stderr)
            return 1

    # Planned over every model NAMED, then the skipped ones struck out — so the branches a
    # skipped model would have drawn are simply missing, and the survivors keep the exact
    # positions they would have had. Handing its share to the others would make one pile
    # bigger than the other and put the reading budget out of true.
    alive = dict(models)
    jobs = [j for j in plan(a.n, temps, list(seen_props), a.name, shuffle=bool(a.models))
            if j[0] in alive]

    live = sys.stdout.isatty()
    told = ", ".join(f"{n}×{sum(1 for m, _ in jobs if m == n)}" for n, _ in models) \
        if a.models else (seen_props[""].get("file") or "llama")
    print(f"census · {a.name} · {len(jobs)} branches · {told}"
          f" · temps {', '.join(str(t) for t in temps)}"
          f" · n_predict {n_predict} · root {len(doc)} chars", flush=True)

    cut = False
    for i, (model, temp) in enumerate(jobs, 1):
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
            d = eva.complete_stream(root["text"], params, on_chunk, where[model])
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
                         "probs": d.get("probs"), "params": params,
                         # The key. In the file and nowhere on the choose screen: the cards
                         # are read first and told apart after.
                         "model": stamp[model]}}
        sitting["nodes"][node["id"]] = node
        # After every branch, not at the end: a page open on this room shows the pile
        # growing, and a run killed at branch 38 keeps 37.
        write_sitting(sitting)
        print(f"{i:>4}  t {temp:<5} {(model or '·'):<8} {d['tokens_predicted']:>5} tok  "
              f"{(d['stop_type'] or '?'):<5}  {one_line(d['text'])}", flush=True)

    live_nodes = sum(1 for n in sitting["nodes"].values() if n["kind"] == "model")
    print(f"{'cut at' if cut else 'done:'} {live_nodes} branches · "
          f"{sitting_path(a.name)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
