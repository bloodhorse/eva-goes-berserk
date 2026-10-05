import glob, json, sys
import pyarrow.parquet as pq
t = pq.read_table(sorted(glob.glob(sys.argv[1] + "/data/*.parquet"))[3], columns=["TEXT", "METADATA"]).slice(5, 3).to_pydict()
for text, meta in zip(t["TEXT"], t["METADATA"]):
    print(json.loads(meta).get("title"), "|", repr(text[20000:20420]))
