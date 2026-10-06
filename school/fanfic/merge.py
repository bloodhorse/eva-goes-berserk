import collections
import hashlib
import json
import os
import re
import shutil
import sys

from common import ROOT

OUT = ROOT / "out"


def fingerprint(text):
    t = re.sub(r"\s+", " ", text[:3000].lower())
    return hashlib.sha1(t.encode("utf-8", "ignore")).digest()


def merge(shelf):
    parts = sorted((OUT / shelf).glob("*.jsonl"))
    dst = ROOT / f"{shelf}.jsonl"
    tmp = ROOT / f"{shelf}.jsonl.part"
    seen = set()
    fand = collections.defaultdict(lambda: [0, 0])
    tiers = collections.defaultdict(lambda: [0, 0])
    ratings = collections.Counter()
    explicit = [0, 0]
    works = words = dups = 0
    with open(tmp, "w", encoding="utf-8") as out:
        for f in parts:
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    r = json.loads(line)
                    fp = fingerprint(r["text"])
                    if fp in seen:
                        dups += 1
                        continue
                    seen.add(fp)
                    out.write(line)
                    works += 1
                    words += r["words"]
                    fand[r["fandom"]][0] += 1
                    fand[r["fandom"]][1] += r["words"]
                    tiers[r["tier"]][0] += 1
                    tiers[r["tier"]][1] += r["words"]
                    ratings[r["rating"]] += 1
                    if r["explicit"]:
                        explicit[0] += 1
                        explicit[1] += r["words"]
        out.flush()
        os.fsync(out.fileno())
    tmp.rename(dst)
    summary = {
        "shelf": shelf,
        "path": str(dst),
        "bytes": dst.stat().st_size,
        "works": works,
        "words": words,
        "duplicates_removed": dups,
        "explicit_works": explicit[0],
        "explicit_words": explicit[1],
        "ratings": dict(ratings),
        "tiers": {str(k): {"works": v[0], "words": v[1]} for k, v in sorted(tiers.items())},
        "fandoms": {k: {"works": v[0], "words": v[1]} for k, v in sorted(fand.items(), key=lambda kv: -kv[1][1])},
    }
    (ROOT / f"{shelf}.summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    shutil.rmtree(OUT / shelf)
    print(shelf, works, words, dups, summary["bytes"], flush=True)


def main():
    for shelf in sys.argv[1:] or ["souls", "wired", "anime"]:
        merge(shelf)


if __name__ == "__main__":
    main()
