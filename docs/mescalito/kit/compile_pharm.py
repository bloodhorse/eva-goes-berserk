import collections, glob, os, re, sys

if len(sys.argv) < 4:
    sys.exit("usage: compile_pharm.py <pharm-dir> <out.md> <title> <bank> <direction> [<direction>…]")
root, out_path, title, bank = sys.argv[1:5]
wanted = sys.argv[5:]

def stats(t):
    w = re.findall(r"\w+", t.lower())
    bi = list(zip(w, w[1:])); four = list(zip(w, w[1:], w[2:], w[3:]))
    d2 = len(set(bi)) / len(bi) if bi else 0
    seen, rep = set(), 0
    for g in four:
        rep += g in seen; seen.add(g)
    return len(w), d2, (rep / len(four) if four else 0)

seeds = {}
pages = collections.defaultdict(list)
for p in sorted(glob.glob(f"{root}/{bank}/*/*.txt")):
    seed = p.split("/")[-2]
    vec, dose, rng = os.path.basename(p)[:-4].split("__")
    if vec[:3] not in wanted:
        continue
    seeds[seed] = f"{root}/../../../shelf/seeds"
    pages[vec].append((seed, dose[1:], rng[1:], open(p, errors="replace").read()))

seed_files = {"cold": "kept/11-2201", "bread": "kept/05-1443", "house": "kept/02-1044", "note": "kept/23-1330",
              "horla": "pot2/31-the-horla", "blizzard": "pot2/03-home-of-the-blizzard", "sinner": "pot2/14-justified-sinner",
              "silk": "pot2/26-an-adventure", "wallpaper": "short/00-yellow-wallpaper", "opium": "short/09b-opium-dreams"}
out = [f"# {title}", "",
       "Every page is a 170-token continuation of the seed named in its header; the ten seeds are printed first. "
       "`words / distinct-2 / rep4` are surface stats: distinct-2 low means a loop, rep4 high means a mantra.", "", "## the seeds", ""]
for name in seed_files:
    if name in seeds:
        out += [f"### seed: {name}", "", "```", open(f"shelf/seeds/{seed_files[name]}.txt").read().rstrip(), "```", ""]
for vec in sorted(pages):
    out += [f"## direction {vec}", ""]
    for seed, dose, rng, text in sorted(pages[vec], key=lambda x: (list(seed_files).index(x[0]), float(x[1]))):
        n, d2, r4 = stats(text)
        out += [f"### {vec} · {seed} · dose {dose} · draw {rng}  ({n} words / d2 {d2:.2f} / rep4 {r4:.2f})", "",
                "```", text.strip("\n"), "```", ""]
open(out_path, "w").write("\n".join(out))
print(out_path, "|", len(pages), "directions,", sum(len(v) for v in pages.values()), "pages")
