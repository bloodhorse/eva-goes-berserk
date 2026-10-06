import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
src, first, last, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
sys.argv = sys.argv[:1]
import cut2

DIGITS = re.compile(r"^[\dIl]{1,3}$")
OPEN = re.compile(r"""[.!?,;:'"’”)]$""")


def page(n):
    path = os.path.join(src, f"{n:08d}.txt")
    return [l.strip() for l in open(path, encoding="utf-8", errors="replace") if l.strip()] if os.path.exists(path) else []


pages = [page(n) for n in range(first, last + 1)]
heads = Counter(p[0] for p in pages if p)
chunks, cur = [], []
for p in pages:
    if p and DIGITS.match(p[-1]):
        p = p[:-1]
    if p and DIGITS.match(p[0]):
        chunks.append(cur)
        cur, p = [], p[1:]
    elif p and (heads[p[0]] >= 3 or (len(p[0].split()) <= 3 and not OPEN.search(p[0]))):
        p = p[1:]
    cur += [l for l in p if not l.startswith(("→", "->", "=>"))]
chunks.append(cur)
parts = []
for lines in chunks:
    joined = []
    for l in lines:
        if joined and joined[-1].endswith("-") and l[:1].islower():
            joined[-1] = joined[-1][:-1] + l
        else:
            joined.append(l)
    body, mode = cut2.clean("\n".join(joined))
    if body.strip():
        parts.append(body)
text = "\n\n* * *\n\n".join(parts)
open(out, "w", encoding="utf-8").write(text + "\n")
print(f"{out}: {len(pages)} pages, {len(parts)} parts, {len(text.split())} words, last mode {mode}")
