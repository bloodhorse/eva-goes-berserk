import json
import sys
from pathlib import Path

import wb

HERE = Path(__file__).resolve().parent

SOURCES = {
    "scifiction": ["scifi.com/robots.txt", "www.scifi.com/robots.txt", "scifi.com/scifiction/robots.txt"],
    "infinitematrix": ["infinitematrix.net/robots.txt", "www.infinitematrix.net/robots.txt"],
    "subterranean": ["subterraneanpress.com/robots.txt", "www.subterraneanpress.com/robots.txt"],
}


def main():
    names = sys.argv[1:] or list(SOURCES)
    for name in names:
        out = HERE / name / "word"
        out.mkdir(parents=True, exist_ok=True)
        notes = []
        for u in SOURCES[name]:
            rows = wb.cdx(u, html_only=False, ok_only=False, collapse=None, extra=[("limit", "-8")])
            notes.append({"url": u, "last_captures": rows})
            good = [r for r in rows if r["statuscode"] == "200"]
            if good:
                r = good[-1]
                status, body, _ = wb.get(wb.snap_url(r["timestamp"], r["original"]))
                (out / f"robots_{wb.safe_name(r['timestamp'], r['original'])}.txt").write_bytes(body)
                print(name, u, r["timestamp"], status, len(body))
            else:
                print(name, u, "no 200 capture among last", len(rows), [x["statuscode"] for x in rows])
        (out / "robots_captures.json").write_text(json.dumps(notes, indent=1))


if __name__ == "__main__":
    main()
