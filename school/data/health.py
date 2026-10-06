import os
import re
import sys

DIRT = {
    "image file": re.compile(r"\.(?:jpe?g|png|gif)\b", re.I),
    "Full Size": re.compile(r"Full Size"),
    "url": re.compile(r"https?://|www\.", re.I),
    "Project Gutenberg": re.compile(r"Project Gutenberg", re.I),
    "piracy watermark": re.compile(r"z-lib|1lib|OceanofPDF|libgen", re.I),
    "copyright page": re.compile(r"All rights reserved|ISBN[ :-]*\d|Copyright ©", re.I),
    "page marker": re.compile(r"\[Pg\s*\w+\]"),
}


def health(path):
    files = sorted(f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and f.endswith(".txt"))
    nested = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d)) and not d.startswith(".")]
    total = glued = glued_books = tiny = 0
    lens, dirt = [], dict.fromkeys(DIRT, 0)
    for f in files:
        text = open(os.path.join(path, f), encoding="utf-8", errors="replace").read()
        paras = [p for p in text.split("\n\n") if p.strip()]
        total += len(text)
        tiny += len(text.split()) < 300
        if sum(len(p) for p in paras if len(p) > 20000) > 0.5 * len(text):
            glued_books += 1
            glued += len(text)
        lens += [len(p) for p in paras[:: max(1, len(paras) // 200)]]
        for k, rx in DIRT.items():
            dirt[k] += len(rx.findall(text))
    lens.sort()
    mid = lens[len(lens) // 2] if lens else 0
    p90 = lens[int(len(lens) * 0.9)] if lens else 0
    flags = []
    if not files:
        flags.append("EMPTY")
    if nested:
        flags.append(f"NESTED ({len(nested)} folders prep.py will skip)")
    if total and glued > 0.02 * total:
        flags.append("GLUED")
    if files and mid < 60:
        flags.append("SHREDDED-OR-VERSE")
    if any(dirt.values()):
        flags.append("DIRT")
    print(f"{path}: {len(files)} files, {total / 1e6:.1f} MB, paragraph median {mid} p90 {p90} chars, "
          f"glued {glued_books} books ({100 * glued / max(total, 1):.2f}% of text), under 300 words {tiny}")
    print("   left: " + ", ".join(f"{k} {v}" for k, v in dirt.items() if v) if any(dirt.values()) else "   left: nothing")
    print("   " + ("LOOK: " + ", ".join(flags) if flags else "OK"))
    return not flags


if __name__ == "__main__":
    ok = [health(p) for p in sys.argv[1:]]
    sys.exit(0 if all(ok) else 1)
