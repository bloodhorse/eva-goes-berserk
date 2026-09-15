#!/usr/bin/env -S uv run --python 3.12
"""names.py — read a naming fan: what came before a word, and the reason after it.

    uv run --python 3.12 docs/walk/names.py chrome-roll --word witch

Built for the "the parish called her the ___" documents: each root child is cut at the first
occurrence of --word, so "Answer-witch, and now she's gone…" reads as name + reason. Sorted
by how often a name came up, so the default pile sits on top and the one-offs below it.
"""
import argparse, collections, json, os, re, sys

ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))
sys.path.insert(0, ROOT)
from loom import sitting_path  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("room")
    ap.add_argument("--word", default="witch")
    a = ap.parse_args()

    s = json.load(open(sitting_path(a.room), encoding="utf-8"))
    rows = []
    for n in s["nodes"].values():
        if n["parent"] != s["root"]:
            continue
        t = n["text"]
        m = re.search(re.escape(a.word), t, re.I)
        name = t[:m.end()].strip() if m else "(no " + a.word + ") " + t.split("\n")[0].strip()[:60]
        reason = t[m.end():].split("\n\n")[0].replace("\n", " ").strip()[:110] if m else ""
        rows.append((name, reason))
    count = collections.Counter(r[0].lower() for r in rows)
    for name, reason in sorted(rows, key=lambda r: (-count[r[0].lower()], r[0].lower())):
        print(f"{name:<30} {reason}")
    print(f"\ndistinct: {len(count)} of {len(rows)}")


if __name__ == "__main__":
    main()
