import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import wb

JUNK = re.compile(r"sitemap|@|\.pdb|\.pdf|www\.|%|\+$|/art/|\.(gif|jpg|png|css|js)$", re.I)


def path(r):
    return re.sub(r"^https?://[^/]+", "", r["original"])


def wanted(rows, what):
    main, staging = [], []
    for r in rows:
        if r["timestamp"] >= "2010":
            continue
        p = path(r)
        if "?" in p or JUNK.search(p):
            continue
        if p.startswith("/stories/"):
            main.append(r)
        elif p.startswith("/private/nextissue/stories/"):
            staging.append(r)
    have = {path(r).lower() for r in main}
    extra = [r for r in staging if path(r)[len("/private/nextissue"):].lower() not in have]
    if what == "main":
        return main
    if what == "staging":
        return extra
    return main + extra


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    rows = [json.loads(l) for l in open(HERE / "cdx.jsonl")]
    extra = HERE / "refetch.jsonl"
    if extra.exists():
        rows += [json.loads(l) for l in open(extra)]
    sel = wanted(rows, what)
    if "--count" in sys.argv:
        print(len(sel))
        return
    wb.fetch_all(HERE, sel)


if __name__ == "__main__":
    main()
