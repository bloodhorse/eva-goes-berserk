import collections
import json
import sys

import pyarrow.parquet as pq

from aggregate import split_category
from common import ROOT, cleanup, download
from minors import HARD, sexual

MAPPING = json.loads((ROOT / "mapping.json").read_text())
terms = collections.Counter()
works = collections.Counter()
sex = collections.Counter()
for name in sys.argv[1:]:
    d, p = download(name, print)
    t = pq.read_table(p, columns=["TEXT", "CATEGORY", "language"])
    cleanup(d)
    for raw, cat, lang in zip(*(t.column(c).to_pylist() for c in t.column_names)):
        if lang != "en" or not raw:
            continue
        m = MAPPING.get(split_category(cat)[0])
        if not m:
            continue
        found = set(x.group(0) for x in HARD.finditer(raw))
        if not found:
            continue
        shelf = m["shelf"]
        works[shelf] += 1
        if sexual(raw):
            sex[shelf] += 1
        for f in found:
            terms[(shelf, f)] += 1
print("works with hard terms", dict(works), "of which sexual", dict(sex))
for (s, f), n in terms.most_common(40):
    print(s, repr(f), n)
