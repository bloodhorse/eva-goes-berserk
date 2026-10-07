import json
import sys
from pathlib import Path

import wb

HERE = Path(__file__).resolve().parent

PREFIXES = {
    "scifiction": ["scifi.com/scifiction*"],
    "infinitematrix": ["infinitematrix.net*"],
    "subterranean": ["subterraneanpress.com/magazine*", "subterraneanpress.com/index.php/magazine*"],
}


def main():
    for name in sys.argv[1:] or list(PREFIXES):
        out = HERE / name / "cdx.jsonl"
        if out.exists():
            print(name, "cdx.jsonl exists, skipping")
            continue
        seen = {}
        for p in PREFIXES[name]:
            rows = wb.cdx(p, html_only=True, ok_only=True, collapse="urlkey", extra=[("fl", "urlkey,timestamp,original,mimetype,statuscode,digest,length")])
            print(name, p, len(rows), flush=True)
            for r in rows:
                seen.setdefault(r["urlkey"], r)
        if not seen:
            print(name, "nothing enumerated, not writing")
            continue
        (HERE / name).mkdir(exist_ok=True)
        with open(out, "w") as f:
            for k in sorted(seen):
                f.write(json.dumps(seen[k]) + "\n")
        print(name, "total", len(seen))


if __name__ == "__main__":
    main()
