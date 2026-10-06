import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path.home() / "eva-olmo" / "school" / "fanfic"
GENRES = {
    "Adventure", "Angst", "Crime", "Drama", "Family", "Fantasy", "Friendship", "General", "Horror",
    "Humor", "Hurt-Comfort", "Mystery", "Parody", "Poetry", "Romance", "Sci-Fi", "Spiritual",
    "Supernatural", "Suspense", "Tragedy", "Western",
}


def split_category(c):
    parts = [p.strip() for p in (c or "").split(",")]
    genres = []
    while len(parts) > 1 and parts[-1] in GENRES:
        genres.insert(0, parts.pop())
    return ", ".join(parts), genres


def main():
    src = collections.Counter()
    lang = collections.Counter()
    rows_total = 0
    fand = collections.defaultdict(lambda: [0, 0, 0])
    seen = collections.defaultdict(set)
    genres = collections.Counter()
    for f in sorted((ROOT / "survey").glob("*.json")):
        for c, s, l, n, chars, ppl, lens in json.loads(f.read_text()):
            rows_total += n
            src[s] += n
            lang[l] += n
            if l != "en":
                continue
            fd, g = split_category(c)
            for x in g:
                genres[x] += n
            a = fand[fd]
            a[0] += n
            a[1] += chars
            for ln in lens:
                k = (c, ln)
                if k in seen[fd]:
                    a[2] += 1
                else:
                    seen[fd].add(k)
    print("rows", rows_total)
    print("sources", src.most_common())
    print("langs", lang.most_common(12))
    print("genres", genres.most_common())
    en_works = sum(a[0] for a in fand.values())
    en_chars = sum(a[1] for a in fand.values())
    dups = sum(a[2] for a in fand.values())
    print("en works", en_works, "en chars", en_chars, "dup-looking", dups, "fandoms", len(fand))
    out = [{"fandom": k, "works": a[0], "chars": a[1], "dups": a[2]} for k, a in fand.items()]
    out.sort(key=lambda r: -r["chars"])
    (ROOT / "fandoms.json").write_text(json.dumps(out, ensure_ascii=False, indent=0))
    crosses = [r for r in out if re.search(r"crossover| \+ |&", r["fandom"], re.I)]
    print("crossover-looking", len(crosses), crosses[:10])


if __name__ == "__main__":
    main()
