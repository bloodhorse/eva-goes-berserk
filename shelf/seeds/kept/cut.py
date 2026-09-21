#!/usr/bin/env python3
"""cut.py — seeds cut from the stream's own first day, by window. Provenance, not an instrument.

bekh, 2026-09-21: rather than hunt for perfect seeds and never start, take the quotes opus
listed in `docs/ledgers/stream-2026-09-19.md` from its beginning up to (not including) the group
"a rule extended past sense" — the measurement documents, which he did not love — as seeds.
His cut: **the window goes UP, not down.** Opus ended the quotes in the right place and started
them too short, so each seed is the quote plus about twice its length of the text ABOVE it in the
room it came from (seed and dream read as one document), moved forward to a sentence start; the
end is opus's end, untouched. Nothing is retyped: the text is lifted from the room files.

    uv run --python 3.12 shelf/seeds/kept/cut.py            # writes NN-HHMM.txt beside this file

The stream's writer hands these to nemo WHOLE (stream.py skips its 45-word tail trim for
`seeds/kept/`): they are already cut by hand, and the trim would take the lead-in back off.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LEDGER = os.path.join(REPO, "docs", "ledgers", "stream-2026-09-19.md")
ROOMS = os.path.join(REPO, "shelf", "sittings")
STOP = "a rule extended past sense"
SENT_END = r"[.!?…][\"'”’»)\]]*\s+"

def norm(s): return re.sub(r"\s+", " ", s).strip()

def room_text(room):
    d = json.load(open(os.path.join(ROOMS, room + ".json"), encoding="utf-8"))
    root = d["nodes"][d["root"]]["text"]
    dream = next(n["text"] for n in d["nodes"].values() if n.get("kind") == "model")
    return root + dream

def window(full, quote):
    """Locate the quote in the room's text whatever its whitespace, extend ~2x its length up."""
    pat = r"\s+".join(re.escape(w) for w in norm(quote).split())
    m = re.search(pat, full)
    if not m:
        return None
    start = max(0, m.start() - 2 * (m.end() - m.start()))
    lead = full[start:m.start()]
    s = re.search(SENT_END, lead)             # forward to a sentence start, if the lead has one
    if start > 0:
        start += s.end() if s else (re.search(r"\s", lead).end() if re.search(r"\s", lead) else 0)
    return full[start:m.end()].lstrip()

text = open(LEDGER, encoding="utf-8").read()
text = text.split("\n## ", 1)[1]
out, group = [], None
for part in ("## " + text).split("\n## ")[0:]:
    title = part.split("\n", 1)[0].replace("## ", "").strip()
    if title.startswith(STOP):
        break
    for m in re.finditer(r"\(https://eva\.x/#room=(stream/[\d-]+/[\w-]+)\).*?\n((?:.*\n)*?)(?=\n\*\*\[|\Z)", part):
        room, body = m.group(1), m.group(2)
        for q in re.findall(r"(?m)^> (.+(?:\n> .+)*)", body):
            out.append((title, room, re.sub(r"(?m)^> ", "", q)))

made = 0
for i, (title, room, quote) in enumerate(out, 1):
    w = window(room_text(room), quote)
    if w is None:
        print("NOT FOUND", room, norm(quote)[:60], file=sys.stderr); continue
    name = f"{i:02d}-{room.rsplit(chr(47), 1)[1]}.txt"
    with open(os.path.join(HERE, name), "w", encoding="utf-8", newline="") as f:
        f.write(w.rstrip(" \t"))
    made += 1
    print(f"{name} [{title[:28]}] {len(norm(quote).split())}w -> {len(w.split())}w")
print(made, "of", len(out), "cut")
