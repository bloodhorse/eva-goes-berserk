#!/usr/bin/env -S uv run --python 3.12
"""fan_under.py — a wide fan under one branch of an existing room, unattended.

    uv run --python 3.12 docs/walk/fan_under.py i-wish-i-could \
        --phrase "i wish i could." --n 40 --predict 160 --temps 1.8,2.2,2.6,3.0

census.py makes a new room from a document; this adds to a room that already has a tree.
The fan point is found by a phrase among the root's children (or is wherever the room
stands, without --phrase), so bekh clicking around in the page doesn't move the target.
Each branch is written as it lands, re-reading the file first; token probabilities are kept,
so the lock-in of a genre can be read off later. The page must not have the room open.
"""
import argparse, json, secrets, sys, time, os

ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))
sys.path.insert(0, ROOT)
from loom import check, complete, sitting_path, write_sitting  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("room")
    ap.add_argument("--phrase")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--predict", type=int, default=160)
    ap.add_argument("--temps", default="1.8,2.2,2.6,3.0")
    a = ap.parse_args()
    temps = [float(t) for t in a.temps.split(",")]

    s = json.load(open(sitting_path(a.room), encoding="utf-8"))
    if a.phrase:
        hits = [n["id"] for n in s["nodes"].values() if n["parent"] == s["root"] and a.phrase in n["text"]]
        if len(hits) != 1:
            sys.exit(f"expected one branch with that phrase, found {len(hits)}")
        at = hits[0]
    else:
        at = s["current"]
    chain, n = [], s["nodes"][at]
    while n:
        chain.insert(0, n["text"])
        n = s["nodes"][n["parent"]] if n["parent"] else None
    prompt = "".join(chain)

    for i in range(a.n):
        params = dict(s["params"], temperature=temps[i % len(temps)], n_predict=a.predict)
        r = complete(prompt, params)
        if "error" in r:
            print(f"{i+1}/{a.n} error: {r['error']}", flush=True)
            continue
        cur = json.load(open(sitting_path(a.room), encoding="utf-8"))
        nid = secrets.token_hex(4)
        cur["nodes"][nid] = {"id": nid, "parent": at, "kind": "model", "text": r["text"],
                             "ts": time.time(), "pruned": False, "posed": False,
                             "meta": {k: v for k, v in r.items() if k != "text"} | {"params": params}}
        why = check(cur)
        if why:
            sys.exit("check failed: " + why)
        write_sitting(cur)
        print(f"{i+1}/{a.n} t={params['temperature']} {r['tokens_predicted']} tok", flush=True)
    print("done")


if __name__ == "__main__":
    main()
