"""screen.py: the kill and the lot. Reads one short page per vector from a kill-screen dir,
declares the dead by surface stats only (never by taste), reports the death rate per pile, and
draws the verdict set by lot from the living: n owned + n random. Nothing here ranks a page.

    screen.py kill/nemo --n 12 --out picks-nemo.json [--seed 1]

A page is dead when it has fewer than --min-words words (the newline page), or its distinct-2
(unique bigrams / bigrams) is under --d2 (the loop), or its rep4 (share of 4-grams already seen
on the page) is over --rep4 (the mantra). The thresholds are loose on purpose: the kill removes
what nobody could have marked a 2, not what looks weak."""
import argparse, collections, glob, json, os, random, re

p = argparse.ArgumentParser()
p.add_argument("dir"); p.add_argument("--n", type=int, default=12); p.add_argument("--out", required=True)
p.add_argument("--seed", type=int, default=1)
p.add_argument("--min-words", type=int, default=20); p.add_argument("--d2", type=float, default=0.5)
p.add_argument("--rep4", type=float, default=0.3)
a = p.parse_args()


def stats(text):
    w = re.findall(r"\w+|[^\w\s]", text.lower())
    bi = list(zip(w, w[1:])); q4 = list(zip(w, w[1:], w[2:], w[3:]))
    seen, rep = set(), 0
    for g in q4:
        rep += g in seen; seen.add(g)
    return len(w), len(set(bi)) / max(1, len(bi)), rep / max(1, len(q4))


rows = {}
for path in sorted(glob.glob(os.path.join(a.dir, "*.txt"))):
    name = os.path.basename(path)[:-4]
    words, d2, r4 = stats(open(path).read())
    dead = words < a.min_words or d2 < a.d2 or r4 > a.rep4
    rows[name] = dict(words=words, d2=round(d2, 3), rep4=round(r4, 3), dead=dead,
                      pile="random" if name.startswith("rand_") else "owned")

piles = collections.defaultdict(list)
for name, r in rows.items():
    piles[r["pile"]].append(name)
for pile, names in sorted(piles.items()):
    dead = sum(rows[n]["dead"] for n in names)
    print(f"{pile:7s} {len(names):4d} vectors  {dead:4d} dead  ({100 * dead / max(1, len(names)):.0f}%)")

rng = random.Random(a.seed)
picks = {}
for pile, names in piles.items():
    alive = [n for n in names if not rows[n]["dead"]]
    picks[pile] = sorted(rng.sample(alive, min(a.n, len(alive))))
    if len(alive) < a.n:
        print(f"only {len(alive)} living {pile} vectors: the verdict set is short")
json.dump(dict(picks=picks, rows=rows, thresholds=dict(min_words=a.min_words, d2=a.d2, rep4=a.rep4),
               seed=a.seed), open(a.out, "w"), indent=1)
print("picks:", json.dumps(picks))
