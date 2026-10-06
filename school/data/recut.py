import os
import re
import sys
from multiprocessing import Pool

SRC, OUT = (sys.argv + ["", ""])[1:3]
CAPTION = re.compile(r"\s*[^\s.]{0,60}(?:\.[^\s.]{1,20}){0,3}\.(?:jpe?g|png|gif)\b(?:\s*\(\d+\s*[KkMm][Bb]?\))?(?:\s*Full Size)?", re.I)
SIZE = re.compile(r"\s*\(\d+K\)(?:\s*Full Size)?")
LINKS = re.compile(r"\s*\b(?:Full Size|Linked Image|Larger Image|Enlarged? Image|Click (?:on )?(?:the )?image[^.]*\.?)")
URL = re.compile(r"\s*\(?(?:https?://|www\.)[^\s]{1,300}", re.I)
HTM = re.compile(r"\s*[^\s.]{1,60}(?:\.[^\s.]{1,20}){0,3}\.html?\b(?:#[^\s]{0,60})?", re.I)
MARK = re.compile(r"\s*\*{3}\s*(?:START|END) OF TH(?:E|IS) PROJECT GUTENBERG[^*]{0,200}\*{3}", re.I)
BOILER = re.compile(r"Project Gutenberg|Distributed Proofread|pgdp\.net|E-?text prepared by|This e-?book is for the use of|Internet Archive", re.I)


def clean(text):
    out, cut = [], 0
    for para in text.split("\n\n"):
        if BOILER.search(para) and len(para) <= 800:
            cut += 1
            continue
        new = MARK.sub("", para)
        for rx in (CAPTION, SIZE, LINKS, URL, HTM):
            new = rx.sub("", new)
        if new != para:
            cut += 1
            new = re.sub(r"[ \t]{2,}", " ", new).strip()
        if new.strip():
            out.append(new)
    return "\n\n".join(out), cut


def one(name):
    src, dst = os.path.join(SRC, name), os.path.join(OUT, name)
    with open(src, encoding="utf-8", errors="replace") as f:
        text = f.read()
    new, cut = clean(text)
    if cut == 0:
        if not os.path.exists(dst):
            os.link(src, dst)
        return name, 0, 0
    with open(dst + ".tmp", "w", encoding="utf-8") as f:
        f.write(new)
    os.replace(dst + ".tmp", dst)
    return name, cut, len(text) - len(new)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    names = sorted(n for n in os.listdir(SRC) if os.path.isfile(os.path.join(SRC, n)))
    books = paras = chars = 0
    with Pool(8) as p, open(OUT.rstrip("/") + ".recut.tsv", "w") as log:
        for name, cut, lost in p.imap_unordered(one, names, chunksize=16):
            if cut:
                books += 1
                paras += cut
                chars += lost
                log.write(f"{name}\t{cut}\t{lost}\n")
    print(f"RECUT {SRC} -> {OUT}: {len(names)} books, {books} changed, {paras} paragraphs touched, {chars} chars removed", flush=True)
