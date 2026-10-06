import sys

import pyarrow.parquet as pq

from common import cleanup, download

name = sys.argv[1]
mode = sys.argv[2]
d, p = download(name, print)
t = pq.read_table(p, columns=["TEXT", "CATEGORY", "language"])
n = 0
for x, c, l in zip(*(t.column(k).to_pylist() for k in t.column_names)):
    if l != "en":
        continue
    if mode == "empty" and c:
        continue
    if mode not in ("empty", "all") and mode.lower() not in (c or "").lower():
        continue
    n += 1
    print(repr(c), repr(x[:300]))
    if n >= int(sys.argv[3]):
        break
cleanup(d)
