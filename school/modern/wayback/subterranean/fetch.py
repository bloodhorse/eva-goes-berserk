import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import wb

JUNK = re.compile(r"\?|&&|/img/|\.(png|gif|jpg|css|js)$|undefined$|%22|%7C|/\*/|\._|\.fb$|\.form-plugin$|Microsoft\.|multipart|/n/a$|/contact$|http:/|#", re.I)
NOTFIC = re.compile(r"^(review|column|interview|audio|article|essay|memoir|appreciation|introduction|lansdale[-_]unchained|teleplay|bookreviews|birdistheword|non-?fiction|editorial)", re.I)
ISSUE = re.compile(r"^/(index\.php/)?magazine/?$|^/(index\.php/)?magazine/(spring|summer|fall|winter)[-_]?\d{2,4}/?$", re.I)


def path(r):
    return re.sub(r"^https?://[^/]+", "", r["original"])


def kind(r):
    p = path(r)
    if JUNK.search(p):
        return "junk"
    if ISSUE.match(p):
        return "issue"
    last = p.rstrip("/").split("/")[-1]
    if NOTFIC.match(last) or last.endswith("_review"):
        return "notfiction"
    return "candidate"


def wanted(rows, what):
    out = [r for r in rows if kind(r) in (("issue", "candidate") if what == "all" else (what,))]
    out.sort(key=lambda r: (kind(r) != "issue", r["urlkey"]))
    return out


def main():
    what = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "all"
    rows = [json.loads(l) for l in open(HERE / "cdx.jsonl")]
    extra = HERE / "refetch.jsonl"
    if extra.exists():
        rows += [json.loads(l) for l in open(extra)]
    sel = wanted(rows, what)
    if "--count" in sys.argv:
        from collections import Counter
        print(len(sel), Counter(kind(r) for r in rows))
        return
    wb.fetch_all(HERE, sel)


if __name__ == "__main__":
    main()
