import collections, glob, os, re, sys

if len(sys.argv) < 4:
    sys.exit("usage: compile_pages.py <pages-dir> <out.md> <title> <seed-name>=<seed-file> [...]")
root, out_path, title = sys.argv[1:4]
seeds = dict(a.split("=", 1) for a in sys.argv[4:])

def stats(t):
    w = re.findall(r"\w+", t.lower())
    bi = list(zip(w, w[1:])); four = list(zip(w, w[1:], w[2:], w[3:]))
    d2 = len(set(bi)) / len(bi) if bi else 0
    seen, rep = set(), 0
    for g in four:
        rep += g in seen; seen.add(g)
    return len(w), d2, (rep / len(four) if four else 0)

pages = collections.defaultdict(list)
for p in sorted(glob.glob(f"{root}/*/*.txt")):
    seed = p.split("/")[-2]
    vec, dose, rng = os.path.basename(p)[:-4].split("__")
    pages[vec].append((seed, dose[1:], rng[1:], open(p, errors="replace").read()))

out = [f"# {title}", "",
       "Every page is the seed's continuation, 170 tokens. `words / distinct-2 / rep4` are surface stats: "
       "distinct-2 low means a loop, rep4 high means a mantra.", "", "## the seeds", ""]
for name, path in seeds.items():
    out += [f"### seed: {name}", "", "```", open(path).read().rstrip(), "```", ""]
for vec in sorted(pages):
    out += [f"## direction {vec}", ""]
    for seed, dose, rng, text in sorted(pages[vec]):
        n, d2, r4 = stats(text)
        out += [f"### {vec} · {seed} · dose {dose} · draw {rng}  ({n} words / d2 {d2:.2f} / rep4 {r4:.2f})", "",
                "```", text.strip("\n"), "```", ""]
open(out_path, "w").write("\n".join(out))
print(len(pages), "directions,", sum(len(v) for v in pages.values()), "pages")
