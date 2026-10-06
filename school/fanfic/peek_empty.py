import collections
import json
from pathlib import Path

from aggregate import split_category

ROOT = Path.home() / "eva-olmo" / "school" / "fanfic"
raw = collections.Counter()
where = collections.Counter()
for f in sorted((ROOT / "survey").glob("*.json")):
    for c, s, l, n, chars, ppl, lens in json.loads(f.read_text()):
        if l == "en" and split_category(c)[0] == "":
            raw[c] += n
            where[f.stem] += n
print(raw.most_common(20))
print(len(where), where.most_common(5))
