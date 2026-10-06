import csv, glob, hashlib, html, json, os, re, subprocess, sys, unicodedata
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
import uspg

DUMP_MAX = 70173
F, S = "fantasy", "scifi"

FP_FORCE_SCIFI = set("20130110 20130111 20130112 20150701 20210166 20140326 20141201 20141232 20120511 20160545 20180440 20181110 20250845 20240146 20110107".split())
FP_FANTASY_AUTHORS = re.compile(r"Howard, Robert|Lovecraft|Smith, Clark|Hodgson|Merritt|Eddison|Peake|Cabell|Plunkett|James, M\. R|de la Mare|Williams, Charles|Morris, (William|Kenneth)|Hoffmann|Wakefield|Sinclair, May|Benson|Treece|Powys|White, T\. H|Lewis, C\. S|Shiel")
SCIFI_TITLES = re.compile(r"Voyage to Arcturus")

DISPLAY = {
    "Plunkett, Edward 18th Baron of Dunsany": "Lord Dunsany",
    "Linebarger, Paul Myron Anthony": "Cordwainer Smith",
    "Blair, Eric Arthur": "George Orwell",
    "Hoar, Roger Sherman": "Ralph Milne Farley",
    "Bouve, Edward Tracy": "Marjorie Bowen",
    "Orwell, George": "George Orwell",
    "Howard, Robert Ervin": "Robert E. Howard",
    "Howard, Robert E. (Robert Ervin)": "Robert E. Howard",
    "Benson, Edward Frederick": "E. F. Benson",
    "Giesy, John Ulrich": "J. U. Giesy",
    "Haggard, Henry Rider": "H. Rider Haggard",
    "Merritt, Abraham": "A. Merritt",
    "Shiel, Matt P.": "M. P. Shiel",
    "Wells, Herbert George": "H. G. Wells",
    "Smith, Edward Elmer ('Doc')": "E. E. Smith",
    "Cummings, Raymond King": "Ray Cummings",
    "Eddison, Eric Rücker": "E. R. Eddison",
    "Eddison, Eric Rucker": "E. R. Eddison",
    "Lovecraft, Howard Phillips": "H. P. Lovecraft",
    "Hoffmann, Ernst Theodor Amadeus": "E. T. A. Hoffmann",
    "Weinbaum, Stanley G.": "Stanley G. Weinbaum",
}
ALIAS_KEY = {"Robert E. Howard": "howard-r", "E. E. Smith": "smith-e", "Clark Ashton Smith": "smith-c", "Lord Dunsany": "dunsany", "Cordwainer Smith": "smith-cordwainer", "George Orwell": "orwell",
             "Ralph Milne Farley": "farley", "Marjorie Bowen": "bowen"}

NOTE_BLOCK = re.compile(r"^\s*\[?(transcriber['’]?s?|transcribers|editor['’]?s) notes?\b", re.I)
JUNK_LINE = re.compile(r"^\s*(A Project Gutenberg (of )?Australia e-?Book|\* A Project Gutenberg (of )?Australia e-?Book \*|Project Gutenberg (of )?Australia|Title:\s.*|Author:\s.*|-{10,}|\[(Illustration|Cover|Frontispiece|Decoration)[^\]]*\]|\{\d+\}|\[Pg \d+\]|\[\d+\]|Library of Congress.*|ISBN[ :].*|PRINTED IN .*|All rights reserved\.?|ALL RIGHTS RESERVED)\s*$", re.I)
LICENCE = re.compile(r"omitted (from|for) this e-?book|from this e-?book|This e-?book transcribed|Italics in the original|Catalog Card Number|^\s*PUBLISHER['’]S NOTE\s*$|BROWSE the site|SEARCH the entire site|Google Site Search|Copyright laws are changing|This file was produced from images|images generously made available|^\s*\[Source:|You are free: to copy|Creative Commons|creativecommons|This work is licensed|copyright ©|Copyright \(c\)|^\s*Copyright,? \d{4}|reproduced without permission|eBook No\.|Project Gutenberg (of )?Australia|Distributed Proofreaders|This e-?book (is|was)", re.I)
TAILNOTE = re.compile(r"^\s*\[?(Transcriber['’]?s? Notes?|The pre-title|Copyright notice provided|Inconsistent|Mis-?spelled|Spelling|Hyphenation|Punctuation|Obvious|Typographical|Misspelled|This story was drawn|Most of the stories are|Note: the above links|Source:|Minor (spelling|typographical)|Archaic|Printer|The following (changes|corrections)|Errors|Page numbers)", re.I)
TOC_HEAD = re.compile(r"^\s*(table of )?contents\.?\s*$|^\s*(TABLE OF )?CONTENTS\.?\s*$", re.I)


def decode(b):
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:]
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("cp1252", errors="replace")


def html_to_text(t):
    m = re.search(r"<body[^>]*>(.*)</body>", t, re.S | re.I)
    t = m.group(1) if m else t
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", t, flags=re.S | re.I)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</?(p|div|h\d|hr|table|tr|blockquote|li|ul|ol|center)\b[^>]*>", "\n\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t).replace("\xa0", " ")
    return t


def cut_fp(t):
    lines = t.split("\n")
    start = 0
    for i, l in enumerate(lines[:200]):
        if re.match(r"^\s*(This e-?book was produced by|Faded Page e-?book ?#)", l, re.I):
            start = i
    j = start
    while j < len(lines) and lines[j].strip():
        j += 1
    start = j
    end = len(lines)
    for i in range(len(lines) - 1, max(start, len(lines) - 400), -1):
        if re.match(r"^\s*\[(The )?end of ", lines[i], re.I):
            end = i
            break
    return "\n".join(lines[start:end])


def cut_pga(t):
    lines = t.split("\n")
    start = 0
    for i, l in enumerate(lines[:120]):
        if re.search(r"To contact Project Gutenberg (of )?Australia|gutenberg\.net\.au/licence\.html|Creative Commons Licence|creativecommons\.org", l, re.I):
            start = i + 1
    end = len(lines)
    tail = max(start, len(lines) - 60)
    for i in range(len(lines) - 1, tail, -1):
        if re.match(r"^\s*(Project Gutenberg (of )?Australia|GO TO Project Gutenberg|This site is full of FREE ebooks|THE END\.?|The End\.?|FINIS\.?)\s*$", lines[i]):
            end = i
    return "\n".join(lines[start:end])


def blocks_of(t):
    out, cur = [], []
    for l in t.split("\n"):
        if l.strip():
            cur.append(l.rstrip())
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def split_indented(lines):
    out, cur = [], []
    for l in lines:
        if cur and re.match(r"^\s{2,}\S", l):
            out.append(cur)
            cur = []
        cur.append(l)
    if cur:
        out.append(cur)
    return out


def is_toc_line(l):
    s = l.strip()
    return len(s) < 90 and (re.search(r"(\.{3,}|\s{3,})\s*\d+\s*$", s) or re.match(r"^(chapter\s+)?([IVXLC]+|\d+)[.:)]?\s", s, re.I) or len(s) < 60)


def drop_toc(blocks):
    while True:
        nb = drop_toc_once(blocks)
        if len(nb) == len(blocks):
            return nb
        blocks = nb


def drop_toc_once(blocks):
    n = len(blocks)
    for i, b in enumerate(blocks):
        if not TOC_HEAD.match(b[0]):
            continue
        rest = [x for x in b[1:] if not re.fullmatch(r"\s*(PAGE|Page|CHAPTER|Chapter)\s*", x)]
        if rest and not all(is_toc_line(x) for x in rest):
            continue
        first = re.sub(r"[\s.]+\d+\s*$", "", rest[0]).strip().lower() if rest else None
        j = i + 1
        while j < n:
            bj = blocks[j]
            if all(is_toc_line(x) for x in bj) and (len(bj) > 1 or len(bj[0].strip()) < 70):
                key = re.sub(r"\s+", " ", bj[0]).strip().lower()
                if first is None:
                    first = re.sub(r"[\s.]+\d+\s*$", "", key)
                elif len(bj) <= 2 and first and key.startswith(first[:25]) and j > i + 1:
                    break
                j += 1
                if j - i > 150:
                    break
                continue
            break
        return blocks[:i] + blocks[j:]
    return blocks


def is_prose(b):
    j = re.sub(r"\s+", " ", " ".join(b)).strip()
    letters = [c for c in j if c.isalpha()]
    if not letters or sum(1 for c in letters if c.islower()) / len(letters) < 0.6:
        return False
    if len(j) >= 100:
        return True
    return len(j) >= 50 and len(j.split()) >= 8 and re.search(r"[.!?\"”’']$", j) is not None


def drop_front(blocks):
    for i, b in enumerate(blocks[:80]):
        if is_prose(b):
            k = i
            kept = 0
            while k > 0 and kept < 2 and not is_prose(blocks[k - 1]) and len(blocks[k - 1]) <= 2:
                k -= 1
                kept += 1
            return blocks[k:]
    return blocks


def drop_notes(blocks):
    out, skip = [], False
    for b in blocks:
        if NOTE_BLOCK.match(b[0]):
            skip = True
            continue
        if len(b) <= 12 and LICENCE.search(" ".join(b)):
            continue
        if skip and (b[0].startswith((" ", "\t")) and len(b[0]) - len(b[0].lstrip()) >= 4):
            continue
        skip = False
        out.append(b)
    return out


def render(b):
    lines = [x for x in b if not JUNK_LINE.match(x)]
    if not lines:
        return ""
    strip = [re.sub(r"\s+", " ", x).strip() for x in lines]
    if len(lines) >= 2 and max(len(x) for x in strip) < 60:
        return "\n".join(strip)
    return " ".join(strip)


def clean(t, kind):
    t = t.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
    if kind == "html":
        t = html_to_text(t)
    t = cut_fp(t) if kind == "fp" else cut_pga(t)
    t = re.sub(r"</?(i|b|em|strong|u|sc|small|p|br)\s*/?>", "", t, flags=re.I)
    t = re.sub(r"&(#\d+|#x[0-9a-f]+|[a-z]+\d*);", lambda m: html.unescape(m.group(0)), t, flags=re.I)
    t = re.sub(r"\[(Illustration|Cover Illustration|Decoration)[^\]]*\]", "", t, flags=re.S | re.I)
    t = re.sub(r"(?<![\w_])_([^_\n]+(?:\n[^_\n]+){0,3})_(?![\w_])", r"\1", t)
    t = re.sub(r"(?<![\w=])=([^=\n]+)=(?![\w=])", r"\1", t)
    lines = t.split("\n")
    blocks = blocks_of(t)
    nonblank = sum(1 for l in lines if l.strip())
    if nonblank > 200 and len(blocks) < nonblank / 25:
        blocks = [s for b in blocks for s in split_indented(b)]
    for k in range(max(int(len(blocks) * 0.75), len(blocks) - 30), len(blocks)):
        if len(blocks[k]) <= 4 and TAILNOTE.match(blocks[k][0]):
            blocks = blocks[:k]
            break
    blocks = drop_notes(blocks)
    blocks = drop_toc(blocks)
    blocks = drop_front(blocks)
    paras = [render(b) for b in blocks]
    paras = [p for p in paras if p and not re.fullmatch(r"(THE END|The End|FINIS|Finis)\.?", p)]
    return "\n\n".join(paras).strip() + "\n"


EN = set("the and of to a in was he that it his i you with had as for her she not but on at be".split())


def english(t):
    w = re.findall(r"[a-z']+", t[:200000].lower())
    return bool(w) and sum(1 for x in w if x in EN) / len(w) > 0.18


def words(t):
    return len(re.findall(r"[A-Za-z']+", t))


def slug(s, n=60):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:n].strip("-")


def display_author(a):
    if a in DISPLAY:
        return DISPLAY[a]
    a = re.sub(r"\s*\(.*?\)", "", a).strip()
    if "," in a:
        last, first = a.split(",", 1)
        return f"{first.strip()} {last.strip()}"
    return a


def author_key(disp):
    if disp in ALIAS_KEY:
        return ALIAS_KEY[disp]
    parts = re.sub(r"[^A-Za-z' .-]", "", disp).replace(".", " ").split()
    if not parts:
        return "anonymous"
    return slug(parts[-1] + ("-" + parts[0][0] if len(parts) > 1 else ""))


def fp_tags(pid):
    p = f"raw/fadedpage/show/{pid}.html"
    if not os.path.exists(p):
        return []
    t = open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"Tags:</td><td[^>]*>(.*?)</td>", t)
    return [html.unescape(x) for x in re.findall(r'tags=([^"]+)"', m.group(1))] if m else []


def pga_title(path):
    try:
        head = decode(open(path, "rb").read(3000))
    except OSError:
        return None
    m = re.search(r"^Title:\s+(.+?)\s*$", head, re.M)
    a = re.search(r"^Author:\s+(.+?)\s*$", head, re.M)
    if not m:
        return None
    return re.sub(r"\s*\(\d{4}\)$", "", m.group(1)).strip(), (a.group(1).strip() if a else None)


def same_title(a, b):
    na, nb = uspg.norm(a), uspg.norm(b)
    return not na or not nb or na[:12] in nb or nb[:12] in na


def manifest():
    global idx
    idx = uspg.load("raw/pgus/pg_catalog.csv")
    items = []
    fp = {}
    for l in open("fp_all.tsv", encoding="utf-8"):
        f = l.rstrip("\n").split("\t")
        fp[f[0]] = f
    for path in sorted(glob.glob("raw/fadedpage/txt/*")):
        pid, ext = os.path.basename(path).rsplit(".", 1)
        if ext not in ("txt", "html") or pid not in fp:
            continue
        _, author, title, year = fp[pid]
        tags = fp_tags(pid)
        if pid in FP_FORCE_SCIFI or SCIFI_TITLES.search(title):
            shelf = S
        elif FP_FANTASY_AUTHORS.search(author):
            shelf = F
        else:
            shelf = S if "science fiction" in tags else F
        num = uspg.lookup(idx, author, title) or ""
        items.append(dict(shelf=shelf, author=author, title=title, url=f"https://www.fadedpage.com/showbook.php?pid={pid}",
                          raw=path, kind="fp" if ext == "txt" else "fphtml", site="fadedpage", uspg=num))
    for l in open("pga_pick.tsv", encoding="utf-8"):
        shelf, author, title, base, num = l.rstrip("\n").split("\t")
        bid = base.rsplit("/", 1)[1]
        for path, kind, url in ((f"raw/pgau/txt/{bid}.txt", "pga", base + ".txt"), (f"raw/pgau/html/{bid}h.html", "html", base + "h.html")):
            if os.path.exists(path) and os.path.getsize(path) > 0:
                ht = pga_title(path) if kind == "pga" else None
                if ht and not same_title(ht[0], title):
                    title = ht[0]
                    if ht[1] and uspg.surname(ht[1]) != uspg.surname(author):
                        author = ht[1]
                    num = uspg.lookup(idx, author, title) or ""
                items.append(dict(shelf=shelf, author=author, title=title, url=url, raw=path, kind=kind, site="pgau", uspg=num))
                break
    return items


def phash(p):
    return hashlib.md5(re.sub(r"[^a-z]", "", p.lower()).encode()).hexdigest()


def main():
    items = manifest()
    out_root = "text"
    if os.path.exists(out_root):
        subprocess.run(["osascript", "-e", f'tell app "Finder" to delete POSIX file "{os.path.abspath(out_root)}"'], capture_output=True)
    for s in (F, S):
        os.makedirs(f"{out_root}/{s}", exist_ok=True)
    done = []
    skipped = []
    for it in items:
        if it["uspg"] and int(it["uspg"]) <= DUMP_MAX:
            skipped.append((it, f"in US PG #{it['uspg']} (in our Feb 2023 dump)"))
            continue
        raw = decode(open(it["raw"], "rb").read())
        kind = {"fp": "fp", "fphtml": "html", "pga": "pga", "html": "html"}[it["kind"]]
        if it["kind"] == "fphtml":
            body = clean(html_to_text(raw), "fp")
        else:
            body = clean(raw, kind)
        it["body"] = body
        it["words"] = words(body)
        if not english(body):
            skipped.append((it, "not English"))
            continue
        if it["words"] < 120:
            skipped.append((it, f"too short after cleaning ({it['words']} words)"))
            continue
        done.append(it)
    done.sort(key=lambda x: -x["words"])
    seen = set()
    kept = []
    for it in done:
        paras = [p for p in it["body"].split("\n\n") if len(p) > 80]
        hs = [phash(p) for p in paras]
        if hs:
            dup = sum(1 for h in hs if h in seen) / len(hs)
            if dup >= 0.6:
                skipped.append((it, f"duplicate text ({dup:.0%} of paragraphs already taken)"))
                continue
            it["overlap"] = dup
        seen.update(hs)
        kept.append(it)
    names = set()
    rows = []
    for it in sorted(kept, key=lambda x: (x["shelf"], x["author"], x["title"])):
        disp = display_author(it["author"])
        base = f"{author_key(disp)}-{slug(it['title'])}"
        name = base
        k = 2
        while (it["shelf"], name) in names:
            name = f"{base}-{k}"
            k += 1
        names.add((it["shelf"], name))
        with open(f"{out_root}/{it['shelf']}/{name}.txt", "w", encoding="utf-8") as f:
            f.write(it["body"])
        rows.append((it["shelf"], disp, it["title"], it["url"], it["words"], it["site"], name, it.get("uspg", ""), round(it.get("overlap", 0), 2), len(it["body"].encode())))
    with open("catalog.tsv", "w", encoding="utf-8") as f:
        f.write("shelf\tauthor\ttitle\tsource_url\twords\n")
        for r in rows:
            f.write("\t".join(str(x) for x in r[:5]) + "\n")
    with open("text/_stats.json", "w") as f:
        json.dump(dict(rows=rows, skipped=[(s["shelf"], s["author"], s["title"], s["url"], why) for s, why in skipped]), f, indent=1)
    tot = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        tot[r[0]][0] += 1
        tot[r[0]][1] += r[4]
        tot[r[0]][2] += r[9]
    for s, (n, w, b) in sorted(tot.items()):
        print(f"{s}: {n} books, {w/1e6:.2f} M words, {b/1e6:.1f} MB")
    print(f"skipped {len(skipped)}")


if __name__ == "__main__":
    main()
