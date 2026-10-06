import collections
import random
import sys

import pyarrow.parquet as pq

from aggregate import split_category
from clean import WORD, clean, quality, rating_of
from common import cleanup, download
from minors import verdict

name = sys.argv[1]
want = sys.argv[2] if len(sys.argv) > 2 else ""
show = int(sys.argv[3]) if len(sys.argv) > 3 else 3
d, p = download(name, print)
t = pq.read_table(p, columns=["TEXT", "CATEGORY", "language"])
cleanup(d)
q = collections.Counter()
mv = collections.Counter()
ratings = collections.Counter()
samples = []
an = 0
rawchars = cleanchars = 0
for raw, cat, lang in zip(*(t.column(c).to_pylist() for c in t.column_names)):
    if lang != "en" or not raw:
        continue
    fandom, _ = split_category(cat)
    if want and want.lower() not in fandom.lower():
        continue
    q["en"] += 1
    v = verdict(raw, fandom, False)
    if v:
        mv[v] += 1
        continue
    text, paras, cs = clean(raw)
    an += cs["an"]
    words = len(WORD.findall(text))
    r = quality(paras, words)
    for x in r:
        q[x] += 1
    if r:
        if random.random() < 0.05:
            samples.append(("DROPPED " + ",".join(r), cat, raw[:200], text[:600]))
        continue
    q["kept"] += 1
    rawchars += len(raw)
    cleanchars += len(text)
    ratings[rating_of(raw)] += 1
    samples.append(("KEPT", cat, raw[:1500], text[:1500]))
print(q)
print(mv)
print(ratings)
print("an paras", an, "chars kept raw->clean", rawchars, cleanchars)
random.seed(int(sys.argv[4]) if len(sys.argv) > 4 else 1)
for s in random.sample(samples, min(show, len(samples))):
    print("=" * 70, s[0], s[1])
    print("--- RAW:")
    print(s[2])
    print("--- CLEAN:")
    print(s[3])
