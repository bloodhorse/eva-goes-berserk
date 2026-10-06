import glob
import json
import os
import re
import sys
from multiprocessing import Pool

import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recut

SRC, OUT, WANT = (sys.argv + ["", ""])[1], (sys.argv + ["", ""])[2], sys.argv[3:]
NOTE = re.compile(r"^\s*(\[\d+\]|\d{1,4}|Produced by .*|Transcriber'?s? [Nn]ote.*|E-text prepared by .*)\s*$")
ILLUS = re.compile(r"\[Illustration[^\]]*\]", re.S)
IDS = {}


def first_word(s):
    return s.split(None, 1)[0] if s.split() else ""


END = re.compile(r"""[.!?:;][\"'”’)\]]*$""")
CAP = re.compile(r"""^[\"'“‘(\[—-]*[A-Z]""")
PAGE = re.compile(r"""\[Pg\s*[\w.]+\]|\bp\. \d{1,4}(?=[A-Za-z“‘\"'])""")
START = re.compile(r"""^[\"'“‘(\[—-]*[A-Z0-9]""")


def clean(text):
    lines = PAGE.sub("", ILLUS.sub("", text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " "))).split("\n")
    rows, blank, seen = [], 0, False
    for line in lines:
        s = line.rstrip()
        if not s.strip():
            blank += 1
            continue
        if NOTE.match(s):
            continue
        rows.append((blank if seen else 0, re.sub(r"\s+", " ", s.strip())))
        blank, seen = 0, True
    if len(rows) < 2:
        return "\n\n".join(r[1] for r in rows), "empty"
    runs = [b for b, _ in rows[1:]]
    ones = sum(1 for r in runs if r == 1) / len(runs)
    gaps = sum(1 for r in runs if r >= 1) / len(runs)
    lens = sorted(len(s) for _, s in rows)
    p50, p90, p95 = lens[len(lens) // 2], lens[int(len(lens) * 0.9)], lens[int(len(lens) * 0.95)]
    wrapped = p95 <= 100 and p90 <= 1.4 * p50
    if not wrapped:
        mode = "lines"
    elif ones > 0.6:
        mode = "doubled"
    elif gaps < 0.02:
        mode = "filled"
    else:
        mode = "plain"
    ends = sum(1 for _, s in rows if END.search(s)) / len(rows)
    verse = wrapped and sum(1 for _, s in rows if CAP.match(s)) > 0.75 * len(rows)
    out, cur = [], [rows[0][1]]
    for (_, prev), (b, s) in zip(rows, rows[1:]):
        gap = b != 1 if mode == "doubled" else b >= 1
        turn = bool(END.search(prev) and START.match(s))
        if verse or mode == "plain":
            para = gap
        elif mode == "lines":
            para = turn or (gap and ends >= 0.6 and (bool(END.search(prev)) or not s[0].islower()))
        elif mode == "doubled":
            para = gap or (turn and len(prev) < 0.8 * p50)
        else:
            para = gap or (turn and len(prev) < 0.92 * p50)
        if para:
            out.append(cur)
            cur = [s]
        else:
            cur.append(("\n" if verse else " ") + s)
    out.append(cur)
    return "\n\n".join("".join(p) for p in out), mode + ("-verse" if verse else "")


def init(ids):
    IDS.update(ids)


def shard(path):
    t = pq.read_table(path, columns=["TEXT", "METADATA"]).to_pydict()
    done = []
    for text, meta in zip(t["TEXT"], t["METADATA"]):
        tid = str(json.loads(meta).get("text_id"))
        if tid not in IDS:
            continue
        body, mode = clean(text)
        body, _ = recut.clean(body)
        paras = body.split("\n\n")
        for shelf in IDS[tid]:
            with open(f"{OUT}/{shelf}/{tid}.txt", "w", encoding="utf-8") as f:
                f.write(body)
        done.append((tid, mode, len(body), len(paras), max(len(p) for p in paras)))
    return done


if __name__ == "__main__":
    for spec in WANT:
        shelf, listing = spec.split("=")
        os.makedirs(f"{OUT}/{shelf}", exist_ok=True)
        for line in open(listing):
            tid = line.strip().removesuffix(".txt")
            if tid.isdigit():
                IDS.setdefault(tid, []).append(shelf)
    files = sorted(glob.glob(f"{SRC}/data/*.parquet"))
    found = 0
    with Pool(min(12, os.cpu_count() or 2), initializer=init, initargs=(IDS,)) as p, open(f"{OUT}/cut2.tsv", "w") as log:
        for done in p.imap_unordered(shard, files):
            for row in done:
                found += 1
                log.write("\t".join(str(x) for x in row) + "\n")
    print(f"CUT2 {found} of {len(IDS)} books written", flush=True)
