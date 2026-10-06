import collections
import sys

import pyarrow.parquet as pq

path = sys.argv[1]
pf = pq.ParquetFile(path)
print(pf.schema_arrow)
print("rows", pf.metadata.num_rows, "row groups", pf.metadata.num_row_groups)
t = pf.read()
cols = t.column_names
cat = t.column("CATEGORY").to_pylist()
src = t.column("SOURCE").to_pylist()
lang = t.column("language").to_pylist()
tl = t.column("text_len").to_pylist()
text = t.column("TEXT").to_pylist()
print("sources", collections.Counter(src).most_common(10))
print("langs", collections.Counter(lang).most_common(10))
fand = collections.Counter(c.split(",")[0].strip() if c else None for c in cat)
print("fandoms", fand.most_common(30))
print("text_len sum", sum(tl), "chars sum", sum(len(x or "") for x in text))
quoted = sum(1 for x in text if x and x.startswith('"') and "\\n" in x[:2000])
html = sum(1 for x in text if x and ("<p>" in x or "<br" in x or "</" in x))
print("json-quoted", quoted, "html-ish", html)
rated = collections.Counter()
for x in text:
    if not x:
        continue
    low = x[:3000].lower()
    for k in ["rated m", "rated t", "rated k", "rated ma", "rating: m", "rating: t", "lemon", "underage"]:
        if k in low:
            rated[k] += 1
print("markers", rated)
n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
step = max(1, len(text) // n)
for i in range(0, len(text), step)[:n]:
    x = text[i]
    print("=" * 60, i, cat[i], src[i], lang[i], tl[i], len(x))
    print(x[:1500])
    print("..." )
    print(x[len(x) // 2: len(x) // 2 + 800])
    print("... END:")
    print(x[-600:])
