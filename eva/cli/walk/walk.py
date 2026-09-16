#!/usr/bin/env -S uv run --python 3.12
"""walk.py — one hand on the loom from the terminal: seed, short fan, pick, repeat.

    uv run --python 3.12 docs/walk/walk.py new carrier --seed-file seed.txt --title "the carrier"
    uv run --python 3.12 docs/walk/walk.py fan carrier            # 15 short branches, numbered
    uv run --python 3.12 docs/walk/walk.py pick carrier 8         # step onto branch 8
    uv run --python 3.12 docs/walk/walk.py doc carrier            # the document so far

Every fan and every pick is saved into the room, refused branches included, so the page at
eva.x shows each fork that was passed over. Talks to llama through loom.complete directly,
not through the live loom: the page must not have this room open while a fan runs, or its
next save wipes the new branches (last writer wins).
"""
import argparse, json, os, secrets, sys, time

EVA = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))  # eva/cli/walk -> eva/
for _d in ("cli", "server"):  # eva.py and loom.py
    sys.path.insert(0, os.path.join(EVA, _d))
import eva  # noqa: E402
from loom import check, complete, sitting_path, write_sitting  # noqa: E402

# Short branches and xtc are the anti-template levers: a genre locks in over length, so a
# pick every ~30-40 tokens steers at the forks, and xtc cuts the most obvious token when
# several are plausible. Temperatures step across a range instead of one value per fan.
TEMPS = [1.4, 1.7, 2.0, 2.2, 2.4]


def load(room):
    return json.load(open(sitting_path(room), encoding="utf-8"))


def save(s):
    why = check(s)
    if why:
        sys.exit("check failed: " + why)
    write_sitting(s)


def prompt_to(s, nid):
    out, n = [], s["nodes"][nid]
    while n:
        out.insert(0, n["text"])
        n = s["nodes"][n["parent"]] if n["parent"] else None
    return "".join(out)


def kids(s, nid):
    return sorted((n for n in s["nodes"].values() if n["parent"] == nid), key=lambda n: n["ts"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new"); p.add_argument("room"); p.add_argument("--seed-file", required=True)
    p.add_argument("--title"); p.add_argument("--predict", type=int, default=40)
    p = sub.add_parser("fan"); p.add_argument("room"); p.add_argument("--n", type=int, default=15)
    p = sub.add_parser("pick"); p.add_argument("room"); p.add_argument("k", type=int)
    p = sub.add_parser("doc"); p.add_argument("room")
    a = ap.parse_args()

    if a.cmd == "new":
        if os.path.exists(sitting_path(a.room)):
            sys.exit(f"{a.room} exists, not overwriting")
        seed = open(a.seed_file, encoding="utf-8").read()
        s = eva.blank(a.room, is_bare=True, root_text=seed)
        if a.title:
            s["title"] = a.title
        s["params"].update(n_predict=a.predict, xtc_probability=0.5, xtc_threshold=0.1)
        save(s)
        print("seeded", a.room)
    elif a.cmd == "fan":
        s = load(a.room)
        at, prompt = s["current"], prompt_to(s, s["current"])
        for i in range(a.n):
            params = dict(s["params"], temperature=TEMPS[i % len(TEMPS)])
            r = complete(prompt, params)
            if "error" in r:
                print("error", r["error"]); continue
            s = load(a.room)  # re-read: append to what is on disk now, not to a stale copy
            nid = secrets.token_hex(4)
            s["nodes"][nid] = {"id": nid, "parent": at, "kind": "model", "text": r["text"],
                               "ts": time.time(), "pruned": False, "posed": False,
                               "meta": {k: v for k, v in r.items() if k not in ("text", "probs")}
                               | {"params": params}}
            save(s)
        for i, n in enumerate(kids(load(a.room), at), 1):
            print(f'--- {i} t={n["meta"]["params"]["temperature"]}\n{n["text"]!r}')
    elif a.cmd == "pick":
        s = load(a.room)
        s["current"] = kids(s, s["current"])[a.k - 1]["id"]
        save(s)
        print("now at:", repr(s["nodes"][s["current"]]["text"]))
    elif a.cmd == "doc":
        s = load(a.room)
        print(prompt_to(s, s["current"]))


if __name__ == "__main__":
    main()
