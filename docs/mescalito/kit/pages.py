"""pages.py: raw.jsonl -> pages.md, labelled. bekh reads the pages knowing which pile each one is
from (2026-09-24: "fuck that shit about blindness"), so the file is ordered for reading, not
shuffled: one section per seed, and in it the clean page first, then the owned vectors, then the
random ones, every page headed by its condition and its surface stats (distinct-2 low = loop,
rep4 high = mantra). `python pages.py [title]`, in the dir that holds raw.jsonl."""
import json, os, re, sys

rows = [json.loads(l) for l in open("raw.jsonl") if l.strip()]
title = sys.argv[1] if len(sys.argv) > 1 else os.path.basename(os.getcwd())


def stats(text):
    w = re.findall(r"\w+|[^\w\s]", text.lower())
    bi = list(zip(w, w[1:])); q4 = list(zip(w, w[1:], w[2:], w[3:]))
    seen, rep = set(), 0
    for g in q4:
        rep += g in seen; seen.add(g)
    return len(w), len(set(bi)) / max(1, len(bi)), rep / max(1, len(q4))


def pile(cond):
    return "clean" if cond == "clean" else "random" if cond.startswith("rand_") else "owned"


order = {"clean": 0, "owned": 1, "random": 2}
seeds = sorted({r["seed"] for r in rows})
with open("pages.md", "w") as f:
    f.write(f"# {title}\n\n")
    f.write("clean = no vector; owned = a direction the model learned (melbo bank, layer 10, 1.0×R); "
            "random = a gaussian direction of the same norm on the same layer. Same RNG seed for every page.\n\n")
    for seed in seeds:
        name = os.path.basename(seed)[:-4]
        f.write(f"## seed: {name}\n\n> {open(seed).read().strip()}\n\n")
        for r in sorted((r for r in rows if r["seed"] == seed), key=lambda r: (order[pile(r["cond"])], r["cond"])):
            n, d2, r4 = stats(r["text"])
            f.write(f"### {pile(r['cond'])} · {r['cond']} · {n} words · distinct-2 {d2:.2f} · rep4 {r4:.2f}\n\n")
            f.write(r["text"].strip() + "\n\n")
print(f"pages.md: {len(rows)} pages on {len(seeds)} seeds")
