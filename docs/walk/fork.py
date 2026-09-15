#!/usr/bin/env -S uv run --python 3.12
"""fork.py — copy a room whole and stand the copy on one branch, optionally cut.

    uv run --python 3.12 docs/walk/fork.py chrome-roll i-cant-make-you-believe \
        --phrase "i can't make you believe any of this is real" --title "i can't make you believe"
    uv run --python 3.12 docs/walk/fork.py chrome-roll i-wish-i-could \
        --phrase "i can't make you believe any of this is real. i wish i could." --cut

A whole copy, not a spin: the fork keeps every sibling of the branch, so the fan it came from
is still one ‹ › away. The branch is found by a phrase in its text, among the root's children
unless --anywhere. --cut trims the branch right after the phrase and marks it posed, because
a model line we edited is posed by the project's law. The source is hashed before and after,
and the fork refuses to overwrite an existing room.
"""
import argparse, copy, hashlib, json, os, sys, time

ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))
sys.path.insert(0, ROOT)
from loom import check, sitting_path, write_sitting  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--phrase", required=True)
    ap.add_argument("--title")
    ap.add_argument("--cut", action="store_true", help="trim the branch right after the phrase")
    ap.add_argument("--anywhere", action="store_true", help="search every node, not just the root's children")
    a = ap.parse_args()

    src_path = sitting_path(a.src)
    before = hashlib.sha256(open(src_path, "rb").read()).hexdigest()
    if os.path.exists(sitting_path(a.dst)):
        sys.exit(f"{a.dst} already exists, not overwriting")
    s = json.load(open(src_path, encoding="utf-8"))
    hits = [n for n in s["nodes"].values()
            if a.phrase in n["text"] and (a.anywhere or n["parent"] == s["root"])]
    if len(hits) != 1:
        sys.exit(f"expected one branch with that phrase, found {len(hits)}")

    f = copy.deepcopy(s)
    f["name"], f["created"] = a.dst, time.time()
    if a.title:
        f["title"] = a.title
    node = f["nodes"][hits[0]["id"]]
    if a.cut:
        orig = node["text"]
        node["text"] = orig[:orig.index(a.phrase) + len(a.phrase)]
        node["posed"] = True
        print("cut away:", repr(orig[len(node["text"]):]))
    f["current"] = node["id"]
    why = check(f)
    if why:
        sys.exit("check failed: " + why)
    write_sitting(f)
    after = hashlib.sha256(open(src_path, "rb").read()).hexdigest()
    print("source untouched:", before == after)
    print("standing on:", repr(node["text"][-80:]))


if __name__ == "__main__":
    main()
