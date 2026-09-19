#!/usr/bin/env python3
"""harvest.py — found first-person seeds, cut by machine.

The stream draws 288 seeds a day. Picking a passage and shaping its last line by hand was
possible when experiments came in ones and twos; at this rate it is manual labour, so the seams
here are cut by this script. The lab's rule that the seam is bekh's still holds for experiments
(root `CLAUDE.md`); this folder is for the stream only.

A seed here is a slice of a public-domain Project Gutenberg text: an *i* already inside a
situation, mid-thought, with nothing asked of it. Nothing is composed, nothing is retyped — the
source list at the top of this file plus the rules below reproduce every file byte for byte.

    uv run --python 3.12 shelf/seeds/found/harvest.py <cache-dir>

The cache dir holds `pg<id>.txt`; a second run refetches nothing. To grow the pot, add rows to
SOURCES and raise PER_SOURCE. RANDOM_SEED fixes the draw, so an unchanged source list gives the
same seeds forever; changing it reshuffles everything, which is fine — the files are rewritten.
"""
import os
import random
import re
import sys
import time
import urllib.request

# (gutenberg id, short name, kind) — every one checked against the live catalogue, English,
# public domain, first-person prose. Breadth of situation is the point; no telephones and no
# telegraphs, the pot already leans that way, and nothing that repeats `first-person/`.
SOURCES = [
    (30197, "farthest-north", "polar"),          # Nansen, the Fram drifting in the ice, 1897
    (1356, "cachalot", "whaling"),               # Bullen, a sperm-whaler round the world, 1898
    (41234, "scrambles-alps", "mountain"),       # Whymper, the Matterhorn years, 1871
    (71609, "andersonville", "prison"),          # Ransom, a prisoner's daily diary, 1881
    (46179, "lunatic-asylum", "asylum"),         # Chase, committed and writing it down, 1868
    (18910, "nursing-sister", "nursing"),        # anonymous sister, the Western Front, 1915
    (13279, "yankee-trenches", "soldier"),       # Holmes, an American in the British army, 1918
    (37311, "woolman-journal", "religious"),     # Woolman's journal, a Quaker tailor, 1774
    (11039, "pfeiffer-journey", "travel"),       # Pfeiffer, Vienna to Brazil and on, 1852
    (12797, "log-of-a-cowboy", "trail"),         # Adams, a cattle drive told as a log, 1903
]

PER_SOURCE = 2          # seeds cut from each source
MINLEN, MAXLEN = 500, 1100   # characters of the finished seed
RANDOM_SEED = 20260919

UA = "eva-seed-harvest/1.0 (a base-model reading experiment; one fetch per book, cached)"
PAUSE = 2.0             # seconds between fetches
HERE = os.path.dirname(os.path.abspath(__file__))

# --- normalization, the same idea as first-person/cut.py -------------------------------------
PAGEMARK = re.compile(r"\[[ivxlc]+\.\d+\]")
FOOTMARK = re.compile(r"\[[A-Za-z0-9]{1,3}\]")
DIVIDER = re.compile(r"(?m)^[ \t]*(?:[*\-—] ?)+$")
ITALIC = re.compile(r"_([^_\n]+)_")
START = re.compile(r"(?m)^\*\*\* ?START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*$")
END = re.compile(r"(?m)^\*\*\* ?END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*$")

# --- what disqualifies a window --------------------------------------------------------------
WEB_CHARS = re.compile(r"[\[\]{}<>_|\\*#=~^]|//|@|https?:")
APPARATUS = re.compile(
    r"(?i)(\b(project gutenberg|gutenberg|ebook|transcriber|footnote|illustration|frontispiece|"
    r"appendix|chapter|contents|preface|index|plate|fig\.|vol\.|copyright|etext)\b"
    r"|see page|\bpp?\. ?\d)")            # a cross-reference is the book talking about itself
# a window that reports what somebody else said is a narrator's window, not an `i`'s
REPORTED = re.compile(r"(?i)\b((he|she|they) (said|answered|replied|remarked|observed|cried)"
                      r"|(said|answered|replied|cried) (he|she|they)\b)")
HEADING_WORD = re.compile(r"(?i)^(chapter|book|part|section|letter|appendix|note|preface|"
                          r"introduction|conclusion|postscript|index|contents)\b")
# a scene and not a sermon: the `i` doing something in past time, or a dated entry. Without one
# of these a devotional or expository passage passes every other test and hands over a homily.
ACTED = re.compile(
    r"\b(I|we) (?:[a-z']+ly )?(?:[a-z']+ed|was|were|had|did|went|came|saw|took|got|made|felt|"
    r"found|told|gave|left|stood|ran|wrote|knew|thought|heard|sent|kept|put|began|lay|sat|"
    r"rode|slept|ate|drank|spent|bought|caught|held|drew|built|met|read)\b")
DATED = re.compile(
    r"(?m)^((Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day|Easter|New Year|"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?[ ]\d|\d{1,2}(st|nd|rd|th)[ ]|"
    r"(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh|Twelfth|"
    r"Thirteenth|Fourteenth|Fifteenth|Twentieth|Thirtieth|Twenty)[a-z-]*[ ]?[Dd]ay)")
BROKEN_HYPHEN = re.compile(r"\w- [a-z]")   # a word hyphenated across a line by the scan. Never
                                           # repaired, only refused: no character is ever altered
SENT_START = re.compile(r"(?<=[.!?])[ ]+(?=[A-Z])")
FIRST_PERSON = re.compile(r"\b(I|I'm|I've|I'd|I'll|my|me|mine|myself|we|us|our|ours)\b")
WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")
NUMBER = re.compile(r"\d+")


def fetch(gid, cache):
    """The plain text of one book, cached. A 404 comes back as an HTML page, so check."""
    path = os.path.join(cache, f"pg{gid}.txt")
    if not os.path.exists(path) or os.path.getsize(path) < 20000:
        url = f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read().decode("utf-8", "replace")
        if "<!DOCTYPE html>" in body[:400] or len(body) < 20000:
            raise SystemExit(f"{gid}: not a book at {url} (a 404 page, most likely)")
        os.makedirs(cache, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(body)
        time.sleep(PAUSE)
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def paragraphs(raw):
    """The body of the book as paragraphs, one string each, hard wrapping undone.

    Each paragraph carries a `verse` flag decided before the wrapping is undone — once the lines
    are joined there is no way to tell a poem from prose."""
    t = raw.replace("\r\n", "\n").replace("﻿", "")
    m = START.search(t)
    if m:
        t = t[m.end():]
    m = END.search(t)
    if m:
        t = t[:m.start()]
    t = PAGEMARK.sub("", t)
    t = FOOTMARK.sub("", t)
    t = DIVIDER.sub("", t)
    out, cur = [], []
    for line in t.split("\n"):
        line = line.rstrip()
        if line.strip():
            cur.append(line)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    paras = []
    for lines in out:
        stripped = [ln.strip() for ln in lines]
        # verse: several lines, all short, and most of them starting with a capital
        short = sum(1 for ln in stripped if len(ln) < 52)
        verse = len(stripped) >= 3 and short == len(stripped)
        # so is a block where every line is indented past the first one (a quoted stanza)
        indents = [len(ln) - len(ln.lstrip()) for ln in lines]
        verse = verse or (len(lines) >= 3 and min(indents) >= 6)
        paras.append({"text": ITALIC.sub(r"\1", " ".join(stripped)), "verse": verse})
    return paras


def looks_like_heading(p):
    t = p["text"]
    letters = [c for c in t if c.isalpha()]
    if not letters:
        return True
    if len(t) < 70 and sum(c.isupper() for c in letters) / len(letters) > 0.6:
        return True
    if len(t) < 70 and t[-1] not in ".!?”\"'":
        return True
    return bool(HEADING_WORD.match(t))


def bad_paragraph(p):
    """True for anything that is not plain running prose by a person."""
    t = p["text"]
    if p["verse"] or looks_like_heading(p):
        return True
    if WEB_CHARS.search(t) or APPARATUS.search(t):
        return True
    if len(NUMBER.findall(t)) >= 4:
        return True
    return False


def seed_is_good(text):
    """The finished slice, judged as a whole."""
    if not (MINLEN <= len(text) <= MAXLEN):
        return False
    if text != text.rstrip() or "\t" in text:
        return False
    if not text[-1].isalpha():           # mid-sentence, on a whole word: never a comma, colon,
        return False                     # question mark, dash or a trailing space
    if not (text[0].isupper() or text[0].isdigit()):
        return False
    words = WORD.findall(text)
    if len(words) < 90:
        return False
    fp = len(FIRST_PERSON.findall(text))
    if fp / len(words) * 100 < 2.5 or fp < 4:
        return False
    if not re.search(r"\b(I|we)\b", " ".join(words[:40])):
        return False                     # the `i` is in the situation from the first lines, and
                                         # a possessive is not enough: an essay says "our age"
    if not FIRST_PERSON.search(" ".join(words[-60:])):
        return False                     # and it is still there at the seam. A passage that
                                         # drifts into exposition hands the model an essay
    if REPORTED.search(text) or BROKEN_HYPHEN.search(text):
        return False
    if not (ACTED.search(text) or DATED.search(text)):
        return False
    if any(q in text for q in ('"', "“", "”")):
        return False                     # no reported speech: a seam inside an open quotation
                                         # continues somebody else's talking, not the `i`
    if sum(c.isdigit() for c in text) / len(text) > 0.012:
        return False
    if "?" in text:                      # a question in the slice invites an answer
        return False
    return True


def sentence_starts(text):
    return [0] + [m.end() for m in SENT_START.finditer(text)]


def cut_one(paras, i, rng):
    """A seed starting at paragraph `i`, or None. The seam lands a few words into a sentence
    that is underway — that word decides the first word of every continuation."""
    if bad_paragraph(paras[i]):
        return None
    acc, j = paras[i]["text"], i
    while len(acc) < MAXLEN + 200 and j + 1 < len(paras):
        j += 1
        if bad_paragraph(paras[j]):
            break
        acc += "\n\n" + paras[j]["text"]
    if len(acc) < MINLEN:
        return None
    starts = sentence_starts(acc)
    good = []
    for p in range(MINLEN, min(MAXLEN, len(acc) - 1) + 1):
        if not (acc[p - 1].isalpha() and acc[p] == " "):
            continue
        s = max(x for x in starts if x <= p)
        if not (18 <= p - s <= 110):      # three to twenty words into the live sentence
            continue
        text = acc[:p]
        if seed_is_good(text):
            good.append(text)
    # by lot, not the longest: taking the longest valid seam every time pins every seed to the
    # 1100 ceiling, and a long seed is a style lesson
    return rng.choice(good) if good else None


def harvest(gid, name, cache, rng):
    paras = paragraphs(fetch(gid, cache))
    total = sum(len(p["text"]) for p in paras)
    # skip the front and back matter wholesale; the book's own middle is where the work happens
    running, lo, hi = 0, 0, len(paras)
    for k, p in enumerate(paras):
        running += len(p["text"])
        if running < 0.08 * total:
            lo = k
        if running < 0.94 * total:
            hi = k
    span = hi - lo
    seeds = []
    for b in range(PER_SOURCE):           # one seed per band, so two seeds are never neighbours
        band = list(range(lo + span * b // PER_SOURCE, lo + span * (b + 1) // PER_SOURCE))
        rng.shuffle(band)
        for i in band:
            text = cut_one(paras, i, rng)
            if text:
                seeds.append(text)
                break
        else:
            print(f"  {gid} {name}: band {b + 1} gave nothing")
    return seeds


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cache = args[0] if args else "."
    # --out lands the seeds somewhere else: a seed written here is live on the stream's next
    # tick, so a run that is being judged writes to a scratch dir first.
    out = HERE
    for a in sys.argv[1:]:
        if a.startswith("--out="):
            out = a.split("=", 1)[1]
    os.makedirs(out, exist_ok=True)
    rng = random.Random(RANDOM_SEED)
    for gid, name, kind in SOURCES:
        for n, text in enumerate(harvest(gid, name, cache, rng), 1):
            path = os.path.join(out, f"{gid}-{n:02d}.txt")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(text)                      # no final newline: the seam is the last byte
            print(f"{gid}-{n:02d} {kind:<9} {len(text):>5}c  …{text[-56:]!r}")


if __name__ == "__main__":
    main()
