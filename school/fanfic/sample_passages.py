import json
import random
import sys

from common import ROOT

shelf = sys.argv[1]
n = int(sys.argv[2])
random.seed(int(sys.argv[3]) if len(sys.argv) > 3 else 0)
res = []
with open(ROOT / f"{shelf}.jsonl", encoding="utf-8") as fh:
    for i, line in enumerate(fh):
        if len(res) < n:
            res.append(line)
        else:
            j = random.randint(0, i)
            if j < n:
                res[j] = line
for line in res:
    r = json.loads(line)
    paras = [p for p in r["text"].split("\n\n")]
    start = random.randint(len(paras) // 4, max(len(paras) // 4, 3 * len(paras) // 4 - 1)) if len(paras) > 4 else 0
    out = []
    size = 0
    for p in paras[start:]:
        out.append(p)
        size += len(p)
        if size > 700:
            break
    print(json.dumps({"fandom": r["fandom"], "category": r["category"], "rating": r["rating"], "explicit": r["explicit"], "tier": r["tier"], "words": r["words"], "passage": "\n\n".join(out)}, ensure_ascii=False))
