import sys, re
from bs4 import BeautifulSoup

path = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else "heads"
raw = open(path, "rb").read()
soup = BeautifulSoup(raw.decode("cp1252", "replace"), "lxml")
tags = {}
for t in soup.find_all(True):
    tags[t.name] = tags.get(t.name, 0) + 1
print(sorted(tags.items(), key=lambda x: -x[1])[:12])
blocks = soup.find_all(re.compile(r"^(p|h[1-6]|div|blockquote|li|center)$"))
blocks = [b for b in blocks if not b.find(re.compile(r"^(p|h[1-6]|div|blockquote|li|center)$"))]
print("blocks", len(blocks))
for i, b in enumerate(blocks):
    t = " ".join(b.get_text(" ").split())
    if mode == "heads":
        if b.name.startswith("h") or (0 < len(t) < 40 and not t.endswith((".", ",", "?", "!", '"', "”"))):
            print(i, b.name, t[:60])
    elif mode.startswith("range"):
        a, z = map(int, mode[5:].split(":"))
        if a <= i < z:
            print(i, b.name, t[:100])
