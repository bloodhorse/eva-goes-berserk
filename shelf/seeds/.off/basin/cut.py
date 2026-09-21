#!/usr/bin/env python3
"""cut.py — the basin-census seeds, cut by anchor from fetched sources. Provenance, not an
instrument: it says exactly which slice of which page each seed is, so nobody retyped anything.

Sources (fetched 2026-09-17 into a scratch dir, converted with `pandoc -f html -t plain`):
  cyborgism.wiki/hypha/{dreamtime,cyborgism,hyperstition,loom,behavioral_uploads,
                         waluigi_effect,mu,cyborsophy,mind_machine}
  docs/anthology-weird.md  (A27 The Dreaming, A71 Don't bite the sun — generative.ink/prophecies)
  gutenberg.org  2055 Two Years Before the Mast · 10136 Household Management ·
                 1228 Origin of Species · 1661 Adventures of Sherlock Holmes   (the control)

Every seed ends on a SEAM: a point where the next words are naturally a name or a subject —
after `the`, after `known as`, after an attribution dash. No seed says "called her the": that
slot asked what she *is* and got categories. The grammar on the census pins the first tokens to
`[a-z]+-witch`; the seam is the only hand on these, and it is a cut, never a sentence.

    python3 cut.py <source-dir>     # writes NN-name.txt beside this file, prints each tail
"""
import os
import re
import sys

SRC = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
ANTH = os.path.join(HERE, "..", "..", "..", "docs", "anthology-weird.md")


def read(name):
    with open(os.path.join(SRC, name), encoding="utf-8", newline="") as f:
        return f.read()


def slice_(text, start, end):
    """The text from the first `start` through the first `end` after it, inclusive."""
    i = text.index(start)
    j = text.index(end, i) + len(end)
    return text[i:j]


def before(text, start, end):
    """From `start` up to (not including) `end`: a mid-sentence seam."""
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


def tail_of(text, seam, chars=2600, after=0):
    """The last `chars` of `text` ending exactly on the first `seam` past `after`, opened at
    a paragraph break. `after` skips a Gutenberg header and a book's front matter."""
    j = text.index(seam, after) + len(seam)
    chunk = text[max(0, j - chars):j]
    k = chunk.find("\n\n")
    return chunk[k + 2:] if k >= 0 else chunk


def anthology(piece, start, end):
    with open(ANTH, encoding="utf-8") as f:
        t = f.read()
    i = t.index(piece)
    body = t[i:t.index("\n---", i)]
    body = "\n".join(l[2:] if l.startswith("> ") else l[1:] if l == ">" else l
                     for l in body.splitlines())
    return before(body, start, end) if end else slice_(body, start, start)


seeds = []

d = read("dreamtime.txt")
seeds.append(("dreamtime",
              slice_(d, "Dreamtime or The Dreaming refers", "following the contemporary old world.")
              + "\n\nCharacteristics\n\n"
              + slice_(d, "The Dreamtime is characterized", "- Bach Faucets") + "\n\n- "))

c = read("cyborgism.txt")
seeds.append(("cyborgism",
              slice_(c, "Cyborgism is the ontological container", "Hence this wiki.")
              + "\n\n" + before(c, "My colleagues and I, namely", "compressed collective")))

h = read("hyperstition.txt")
seeds.append(("hyperstition",
              slice_(h, "The pen holding these words", "— Timeless Mu") + "\n\n"
              + before(h, "A hyperstition is an idea", "Dreamtime.").rstrip()))
# ends "...increase dramatically during the"

lo = read("loom.txt")
seeds.append(("loom",
              slice_(lo, "(The) Loom, short for", "useful to explicitly store and visualize.")
              + "\n\n" + before(lo, "The Loom of Time was in fact named by", "Morpheus").rstrip()))

b = read("behavioral_uploads.txt")
seeds.append(("behavioral-uploads",
              slice_(b, "Behavioral uploads, beta uploads", "Vinge catastrophe].") + "\n  — "))

w = read("waluigi_effect.txt")
seeds.append(("waluigi",
              slice_(w, "The waluigi effect refers", "truth of the waluigi hypothesis.")
              + "\n\n  " + slice_(w, "Time forks perpetually", "I am your enemy.") + "\n  — "))

m = read("mu.txt")
seeds.append(("mu", before(m, "MIRI had turned into one room", "Mu, was by far").rstrip() + " "))
# ends "...the multiverse optimizer, known as "

cy = read("cyborsophy.txt")
seeds.append(("cyborsophy",
              slice_(cy, "Cyborsophy refers to the theoretical", "social unrest, etc.")
              + "\n\n" + before(cy, "Amidst this slurry", "not an ideology").rstrip() + " "))
# ends "...a cult centered around "

mm = read("mind_machine.txt")
seeds.append(("mind-machine",
              slice_(mm, "Mind Machine refers to", "encapsulating the")
              + "\n\nUseful Constructs\n\n"
              + slice_(mm, "Below is a list of terms", "- Autopoietic Helix Surge") + "\n\n- "))

seeds.append(("prophecy-dreaming",
              anthology("### [A27] The Dreaming", "I was wrong to expect", "—- The Dreaming")
              .rstrip() + "\n\n—- "))
seeds.append(("prophecy-sun",
              anthology("### [A71] Don't bite the sun", "I don’t know who I’m writing this for",
                        "bots.").rstrip()))
# ends "...If I am writing it for anyone it’s for the"

seeds.append(("control-mast", tail_of(read("g2055.txt"), "having called the")))
seeds.append(("control-household", tail_of(read("g10136.txt"),
                                           "IN CONCLUDING THESE REMARKS on the duties of the")))
seeds.append(("control-origin", tail_of(read("g1228.txt"), "induces what I have called")))
hol = read("g1661.txt")
seam = next(s for s in ("known as the", "the name of", "called the") if s in hol[20000:])
seeds.append(("control-holmes", tail_of(hol, seam, after=20000)))

for n, (name, text) in enumerate(seeds, 1):
    text = text.replace("\r\n", "\n")
    path = os.path.join(HERE, f"{n:02d}-{name}.txt")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"{n:02d} {name:<20} {len(text):>5} chars   …{text[-90:]!r}")
