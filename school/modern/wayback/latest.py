import json
import sys
from pathlib import Path

import wb

HERE = Path(__file__).resolve().parent


def main():
    name = sys.argv[1]
    sub = sys.argv[2]
    urls = sys.argv[3:]
    out = HERE / name / sub
    out.mkdir(parents=True, exist_ok=True)
    for u in urls:
        fr = to = None
        if "@" in u:
            u, span = u.split("@")
            fr, to = span.split("-")
        extra = [("limit", "-5")]
        if fr:
            extra += [("from", fr), ("to", to)]
        rows = wb.cdx(u, html_only=False, ok_only=True, collapse=None, extra=extra)
        if not rows:
            print(u, "no 200 capture")
            continue
        r = rows[-1]
        status, body, _ = wb.get(wb.snap_url(r["timestamp"], r["original"]))
        p = out / (wb.safe_name(r["timestamp"], r["original"]) + ".html")
        p.write_bytes(body)
        print(u, r["timestamp"], status, len(body), p.name)


if __name__ == "__main__":
    main()
