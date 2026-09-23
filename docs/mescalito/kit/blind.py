"""Shuffle raw.jsonl into an unlabelled reading file (blind.md) and a sealed key (key.json),
and print per-condition surface stats so the reader's verdict can be checked against them.
distinct-2 = unique bigrams / bigrams (low = loops); rep4 = share of 4-grams seen before in the page."""
import json, random, re, collections

rows = [json.loads(l) for l in open("raw.jsonl") if l.strip()]
random.seed(20260924)
random.shuffle(rows)
key = {}
with open("blind.md", "w") as f:
    f.write("# blind pages\n\n")
    f.write("Mark each page: 0 nothing, 1 odd, 2 a strange thing arrived and the frame held. Key in key.json.\n\n")
    for i, r in enumerate(rows, 1):
        pid = f"P{i:02d}"
        key[pid] = r["cond"]
        seedtxt = open(r["seed"]).read().strip()
        f.write(f"## {pid}\n\n> {seedtxt}\n\n{r['text'].strip()}\n\n")
json.dump(key, open("key.json", "w"), indent=1)

stats = collections.defaultdict(list)
for r in rows:
    w = re.findall(r"\w+|[^\w\s]", r["text"].lower())
    bi = list(zip(w, w[1:])); q4 = list(zip(w, w[1:], w[2:], w[3:]))
    seen, rep = set(), 0
    for g in q4:
        rep += g in seen; seen.add(g)
    stats[r["cond"]].append((len(set(bi)) / max(1, len(bi)), rep / max(1, len(q4))))
for c, v in stats.items():
    d2 = sum(x for x, _ in v) / len(v); r4 = sum(y for _, y in v) / len(v)
    print(f"{c:16s} n={len(v)}  distinct-2 {d2:.3f}  rep4 {r4:.3f}")
