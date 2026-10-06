import collections
import re
import sys

import pyarrow.parquet as pq

t = pq.read_table(sys.argv[1], columns=["TEXT", "CATEGORY", "language"])
text = t.column("TEXT").to_pylist()
lang = t.column("language").to_pylist()
first = collections.Counter()
heads = collections.Counter()
ends = collections.Counter()
starts = collections.Counter()
html = collections.Counter()
for x, l in zip(text, lang):
    if l != "en":
        continue
    lines = x.split("\n")
    for ln in lines:
        s = ln.strip()
        m = re.match(r"^(\d+)\. (.{0,40})", s)
        if m and len(s) < 80:
            heads[m.group(1)] += 1
        if s and len(s) < 40 and not re.search(r"[A-Za-z]{3}", s):
            first[s] += 1
        w = s[:12].lower()
        for k in ["a/n", "an:", "author", "disclaimer", "note:", "**a/n", "(a/n", "warning", "summary", "pairing", "rated", "review"]:
            if w.startswith(k):
                starts[k] += 1
    for tag in re.findall(r"<[a-zA-Z/][^>]{0,10}>|&[a-z]+;", x):
        html[tag] += 1
    ends[x.strip()[-30:]] += 1
print("chapter numbers", sorted(heads.items(), key=lambda kv: -kv[1])[:15])
print("symbol lines", first.most_common(40))
print("para starts", starts.most_common())
print("html", html.most_common(20))
print("ends", ends.most_common(5))
i = int(sys.argv[2]) if len(sys.argv) > 2 else 0
n = 0
for x, l in zip(text, lang):
    if l == "en" and len(re.findall(r"(?m)^\d+\. ", x)) > 3:
        n += 1
        if n == i + 1:
            for m in re.finditer(r"(?m)^\d+\. .*$", x):
                a = m.start()
                print("-----")
                print(x[max(0, a - 300):a + 500])
            break
