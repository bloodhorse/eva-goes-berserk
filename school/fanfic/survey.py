import collections
import json
import sys
import time

import pyarrow.parquet as pq

from common import ROOT, cleanup, download, key

OUT = ROOT / "survey"


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def main():
    OUT.mkdir(exist_ok=True)
    for name in sys.argv[1:]:
        idx = key(name)
        out = OUT / f"{idx}.json"
        if out.exists():
            continue
        d, p = download(name, log)
        t = pq.read_table(p, columns=["CATEGORY", "SOURCE", "language", "text_len", "perplexity_score"])
        agg = collections.defaultdict(lambda: [0, 0, 0.0, []])
        for c, s, l, n, ppl in zip(*(t.column(k).to_pylist() for k in t.column_names)):
            a = agg[(c, s, l)]
            a[0] += 1
            a[1] += n or 0
            a[2] += ppl or 0.0
            a[3].append(n or 0)
        rows = [[c, s, l, a[0], a[1], a[2], a[3]] for (c, s, l), a in agg.items()]
        tmp = out.with_suffix(".part")
        tmp.write_text(json.dumps(rows, ensure_ascii=False))
        tmp.rename(out)
        cleanup(d)
        log(f"done {idx} rows {t.num_rows}")


if __name__ == "__main__":
    main()
