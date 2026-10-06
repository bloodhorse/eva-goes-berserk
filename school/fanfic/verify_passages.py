import json
import sys

from common import ROOT

blocks = []
for chunk in (ROOT / "passages.txt").read_text(encoding="utf-8").split("=== ")[1:]:
    shelf, _, body = chunk.partition("\n")
    blocks.append((shelf.strip(), body.strip()))
for shelf in ("souls", "wired", "anime"):
    want = [(i, b) for i, (s, b) in enumerate(blocks) if s == shelf]
    found = {}
    with open(ROOT / f"{shelf}.jsonl", encoding="utf-8") as fh:
        for line in fh:
            if not want:
                break
            r = None
            for i, b in list(want):
                head = b[:60]
                if head in line or json.dumps(head, ensure_ascii=False)[1:-1] in line:
                    r = r or json.loads(line)
                    if b in r["text"]:
                        found[i] = (r["fandom"], r["category"], r["rating"], r["explicit"], r["words"])
                        want.remove((i, b))
                    else:
                        idx = r["text"].find(b[:60])
                        print("PARTIAL", shelf, i, repr(r["text"][idx: idx + len(b) + 40][:600]))
    for i, b in blocks:
        pass
    for i, (s, b) in enumerate(blocks):
        if s == shelf:
            print(shelf, i, "FOUND" if i in found else "MISSING", found.get(i, ""))
