import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import fetch_raw, norm_paras, write_text, write_ledger, row, ROOT
from bs4 import BeautifulSoup
import pymupdf as fitz

SLUG = "watts"
AUTH = "Peter Watts"
BASE = "https://www.rifters.com/real/"

NOVELS = [
    ("Blindsight.htm", "blindsight", "Blindsight", 2006),
    ("STARFISH.htm", "starfish", "Starfish", 1999),
    ("MAELSTROM.htm", "maelstrom", "Maelstrom", 2001),
    ("Behemoth.htm", "behemoth", "βehemoth (β-Max and Seppuku, combined)", 2004),
]

STORIES = [
    ("PeterWatts_Home.pdf", "home", "Home", 1999),
    ("PeterWatts_Ambassador.pdf", "ambassador", "Ambassador", 2000),
    ("PeterWatts_Bethlehem.pdf", "bethlehem", "Bethlehem", 1997),
    ("PeterWatts_Niche.pdf", "a-niche", "A Niche", 1990),
    ("PeterWatts_Flesh.pdf", "flesh-made-word", "Flesh Made Word", 1994),
    ("WattsChanner_Bulk_Food.pdf", "bulk-food", "Bulk Food (with Laurie Channer)", 2000),
    ("PeterWatts_Fractals.pdf", "fractals", "Fractals", 1999),
    ("PeterWatts_2ndComing.pdf", "second-coming-of-jasmine-fitzgerald", "The Second Coming of Jasmine Fitzgerald", 1998),
    ("PeterWatts_Nimbus.pdf", "nimbus", "Nimbus", 1993),
    ("PeterWatts_Heathens.pdf", "a-word-for-heathens", "A Word for Heathens", 2004),
    ("Watts_Murphy_Mayfly.pdf", "mayfly", "Mayfly (with Derryl Murphy)", 2005),
    ("PeterWatts_RepeatingThePast.pdf", "repeating-the-past", "Repeating the Past", 2007),
    ("PeterWatts_Hillcrest_V._Velikovsky.pdf", "hillcrest-v-velikovsky", "Hillcrest v. Velikovsky", 2008),
    ("PeterWatts_TheIsland.pdf", "the-island", "The Island", 2009),
    ("PeterWatts_Malak.pdf", "malak", "Malak", 2010),
    ("PeterWatts_Hotshot.pdf", "hotshot", "Hotshot", 2014),
    ("TheThingsCompletePhoto-book.pdf", "the-things", "The Things", 2010),
]

DECLINED = [
    ("PeterWatts_Atwood.pdf", "The Hierarchy of Contempt", "declined:commentary, not fiction"),
    ("Mohn_and_Watts_Pain.pdf", "The Way of Pain", "declined:commentary, not fiction"),
    ("PeterWatts_Blindsight_Endnotes.pdf", "Blindsight Endnotes", "declined:endnotes, not fiction"),
    ("TheScorchedEarthSociety-transcript.pdf", "The Scorched-Earth Society", "declined:speech transcript, not fiction"),
    ("PeterWatts_Are-We-There-Yet.pdf", "En Route to Dystopia With The Angry Optimist", "declined:commentary, not fiction"),
]

END = re.compile(r"^(acknowledge?ments?|notes and references|references|creative commons)", re.I)
BLOCK = re.compile(r"^(p|h[1-6]|div|blockquote|li|center)$")
NOVEL_BASIS = "CC BY-NC-SA 2.5, stated in the book's own 'Creative Commons Licensing Information' section on rifters.com"
STORY_BASIS = "served free by the author at https://www.rifters.com/real/shorts.htm (page links CC BY-NC-SA 2.5)"


def clean_novel(raw):
    soup = BeautifulSoup(raw.decode("cp1252", "replace"), "lxml")
    for t in soup.find_all(["sup", "script", "style"]):
        t.decompose()
    for t in soup.find_all("br"):
        t.replace_with(" ")
    blocks = [b for b in soup.find_all(BLOCK) if not b.find(BLOCK)]
    out, started = [], False
    for b in blocks:
        t = " ".join(b.get_text("").split())
        head = b.name[0] == "h"
        if head and not t:
            continue
        if head and not started:
            started = True
        if not started:
            continue
        if head and END.match(t):
            break
        out.append(t)
    return norm_paras(out)


def pdf_paras(data):
    doc = fitz.open(stream=data, filetype="pdf")
    rows = []
    for page in doc:
        h = page.rect.height
        seen = set()
        groups = {}
        for w in page.get_text("words"):
            x0, y0, x1, y1, word, bno, lno, wno = w[:8]
            cx, cy = int(x0 // 2), int(y0 // 2)
            if any((cx + dx, cy + dy, word) in seen for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                continue
            seen.add((cx, cy, word))
            g = groups.setdefault(bno, {"y0": y0, "y1": y1, "lines": {}})
            g["y0"] = min(g["y0"], y0)
            g["y1"] = max(g["y1"], y1)
            g["lines"].setdefault(lno, []).append(word)
        for bno in sorted(groups):
            g = groups[bno]
            lines = [" ".join(ws) for _, ws in sorted(g["lines"].items())]
            rows.append((g["y0"] / h, g["y1"] / h, lines))
    paras = []
    for y0, y1, lines in rows:
        t = " ".join(lines)
        t = re.sub(r"(\w)- ([a-z])", r"\1-\2", t)
        if re.fullmatch(r"[\d\s\-–]+", t):
            continue
        if (y1 < 0.07 or y0 > 0.93) and len(t) < 90:
            continue
        paras.append(t)
    return paras


BYLINE = re.compile(r"^(by )?Peter Watts( and [A-Z][a-z]+ [A-Z][a-z]+)?( Illustration by [A-Z][a-z]+ [A-Z][a-z]+)?")
START = {"fractals": 2}


def clean_story(raw, slug):
    paras = pdf_paras(raw)
    start = START.get(slug)
    if start is None:
        start = 0
        for i, p in enumerate(paras[:12]):
            m = BYLINE.match(p)
            if m:
                rest = p[m.end():].strip()
                if len(rest) > 40:
                    paras[i] = rest
                    start = i
                else:
                    start = i + 1
                break
    title = {sl: t for _, sl, t, _ in STORIES}[slug].split(" (")[0].lower()
    out = []
    for p in paras[start:]:
        if "\u25a0" in p:
            out.append(p.split("\u25a0")[0])
            break
        p = re.sub(r"^\d{1,3} ((Peter )?Watts|Nimbus)(\s+(?=\S)|$)", "", p)
        if not p:
            continue
        if re.match(r"^\d{1,3} (Originally|Watts, P\.|First published|This story)", p):
            continue
        if len(p) < 60 and re.fullmatch(r"\d{1,3} .*|.* \d{1,3}", p) and (title[:8] in p.lower() or "watts" in p.lower()):
            continue
        if p.lower().startswith(title[:10]) and len(p) < 60 and re.search(r"\d$", p):
            continue
        if "Peter Watts" in p and len(p) < 70:
            continue
        if re.search(r"creative ?commons|rifters\.com|all rights reserved|copyright \u00a9|^\u00a9", p, re.I) and len(p) < 400:
            continue
        if out and re.match(r"[a-z]", p):
            out[-1] = out[-1] + " " + p
            continue
        out.append(p)
    return norm_paras(out)


def main():
    only = sys.argv[1:]
    rows = []
    for page, slug, title, year in NOVELS:
        if only and slug not in only:
            continue
        url = BASE + page
        raw = fetch_raw(SLUG, url, page.lower().replace(".htm", ".html"))
        text = clean_novel(raw)
        rows.append(row(url, slug, title, AUTH, year, "novel", text, write_text(SLUG, slug, text), NOVEL_BASIS))
    for pdf, slug, title, year in STORIES:
        if only and slug not in only:
            continue
        url = BASE + "shorts/" + pdf
        raw = fetch_raw(SLUG, url, pdf)
        text = clean_story(raw, slug)
        rows.append(row(url, slug, title, AUTH, year, "story", text, write_text(SLUG, slug, text), STORY_BASIS, "ok:pdf-derived"))
    if not only:
        rows = [r for r in rows if r["slug"] != "the-things"]
        rows.append(row(BASE + "shorts/TheThingsCompletePhoto-book.pdf", "the-things", "The Things", AUTH, 2010, "story", "", "", STORY_BASIS, "failed:image-only pdf, no text layer"))
        tp = os.path.join(ROOT, SLUG, "text", "the-things.txt")
        if os.path.exists(tp) and os.path.getsize(tp) < 5:
            os.replace(tp, os.path.join(ROOT, "_scratch", "the-things.empty.txt"))
    for pdf, title, why in DECLINED:
        rows.append(row(BASE + "shorts/" + pdf, "", title, AUTH, None, "essay", "", "", STORY_BASIS, why))
    rows.append(row("https://www.rifters.com/", "echopraxia", "Echopraxia", AUTH, 2014, "novel", "", "", "", "declined:not served in full by the author (only promotional extras under /echopraxia/)"))
    if not only:
        write_ledger(SLUG, rows)
    for r in rows:
        if r["words"]:
            print(r["slug"], r["words"])


main()
