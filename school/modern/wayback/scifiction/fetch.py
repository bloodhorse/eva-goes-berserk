import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import wb


SIDE = re.compile(r"_(bio|biblio)\d*\.html?$", re.I)


def wanted(rows, what):
    out = []
    for r in rows:
        u = r["original"]
        if "?" in u or SIDE.search(u):
            continue
        kind = "classics" if "/classics/" in u else "originals" if "/originals/" in u else "elements" if "/elements/" in u or "periodictable" in u else "front"
        if what == "all" or kind == what:
            out.append(r)
    return out


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    rows = [json.loads(l) for l in open(HERE / "cdx.jsonl")]
    extra = HERE / "refetch.jsonl"
    if extra.exists():
        rows += [json.loads(l) for l in open(extra)]
    wb.fetch_all(HERE, wanted(rows, what))


if __name__ == "__main__":
    main()
