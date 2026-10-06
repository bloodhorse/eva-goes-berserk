import json, os, sys

src, out, field = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
n = 0
for line in open(src, encoding="utf-8"):
    r = json.loads(line)
    text = (r.get(field) or "").strip()
    if len(text) < 2000:
        continue
    open(f"{out}/{n:06d}.txt", "w", encoding="utf-8").write(text)
    n += 1
print(out, n, "files", flush=True)
