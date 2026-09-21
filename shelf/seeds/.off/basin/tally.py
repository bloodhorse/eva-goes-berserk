#!/usr/bin/env python3
"""tally.py — read the basin census back: which `-witch` names came up, under which seeds.

    python3 tally.py <room-prefix>         # e.g. basin-smoke-  or  basin-

A name is a HIT when it comes under two or more different seeds; under one seed twenty times
is that seed's pull, not nemo's. Wiki seeds and control seeds are counted apart: a name under
wiki and control both is nemo's general basin; under two wiki seeds and never control is the
one this census is for. Nothing is dropped for being rare — the full list is printed after the
hits, so a one-off can still be read.
"""
import collections
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "sittings")
NAME = re.compile(r"^\s*([a-z]+-witch)")
prefix = sys.argv[1] if len(sys.argv) > 1 else "basin-"

by_name = collections.defaultdict(lambda: collections.defaultdict(list))   # name -> seed -> [line]
per_seed = collections.Counter()
for fn in sorted(os.listdir(ROOT)):
    if not fn.startswith(prefix) or not fn.endswith(".json"):
        continue
    seed = fn[len(prefix):-5]
    with open(os.path.join(ROOT, fn), encoding="utf-8") as f:
        s = json.load(f)
    for n in s["nodes"].values():
        if n.get("kind") != "model":
            continue
        m = NAME.match(n["text"])
        if not m:
            continue
        t = (n.get("meta") or {}).get("params", {}).get("temperature")
        by_name[m.group(1)][seed].append((t, n["text"].strip().replace("\n", " / ")[:110]))
        per_seed[seed] += 1

def kind(seed):
    return "control" if seed.startswith(("12", "13", "14", "15")) else "wiki"

rows = []
for name, seeds in by_name.items():
    wiki = sorted(s for s in seeds if kind(s) == "wiki")
    ctrl = sorted(s for s in seeds if kind(s) == "control")
    total = sum(len(v) for v in seeds.values())
    rows.append((len(seeds), total, name, wiki, ctrl, seeds))
rows.sort(key=lambda r: (-r[0], -r[1], r[2]))

print(f"{sum(per_seed.values())} named branches across {len(per_seed)} seeds\n")
print("HITS — under two or more seeds")
for nseeds, total, name, wiki, ctrl, seeds in rows:
    if nseeds < 2:
        break
    tag = "wiki only" if not ctrl else ("control only" if not wiki else "both")
    print(f"\n{name}  ·  {nseeds} seeds · {total} draws · {tag}")
    for seed, lines in sorted(seeds.items()):
        t, line = lines[0]
        print(f"    {seed:<22} ×{len(lines):<3} t{t}  {line}")

print("\nONE-OFFS — under a single seed")
for nseeds, total, name, wiki, ctrl, seeds in rows:
    if nseeds >= 2:
        continue
    seed = next(iter(seeds))
    t, line = seeds[seed][0]
    print(f"  {name:<28} {seed:<22} ×{total:<3} t{t}  {line}")
