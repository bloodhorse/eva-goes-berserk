import collections
import json
import sys
from pathlib import Path

ROOT = Path.home() / "eva-olmo" / "school" / "fanfic"


def load():
    shelves = collections.defaultdict(collections.Counter)
    fandoms = collections.defaultdict(collections.Counter)
    allc = collections.Counter()
    n = 0
    for f in sorted((ROOT / "stats").glob("*.json")):
        n += 1
        st = json.loads(f.read_text())
        for k, c in st.items():
            if k == "all":
                allc.update(c)
                continue
            shelf, label = k.split("|", 1)
            shelves[shelf].update(c)
            fandoms[k].update(c)
    return n, allc, shelves, fandoms


def main():
    n, allc, shelves, fandoms = load()
    print("shards", n, dict(allc))
    for shelf, c in sorted(shelves.items()):
        print(shelf, {k: v for k, v in sorted(c.items())})
        top = sorted(((k.split("|", 1)[1], v["words"], v["kept"]) for k, v in fandoms.items() if k.startswith(shelf + "|")), key=lambda x: -x[1])
        for lab, w, k in top[: int(sys.argv[1]) if len(sys.argv) > 1 else 8]:
            print("   ", lab, w, k)
    for shelf in ("souls", "wired", "anime"):
        d = ROOT / "out" / shelf
        b = sum(f.stat().st_size for f in d.glob("*.jsonl")) if d.exists() else 0
        print(shelf, "bytes", b)


if __name__ == "__main__":
    main()
