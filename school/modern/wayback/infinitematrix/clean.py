import difflib
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import prose

RAW = HERE / "raw"
TEXT = HERE / "text"
SKIP_FILE = re.compile(r"^(index|sitemap|sleep_of_reason|sleep_of_reason_next|blindshrikehelp|blindshrike-letter|blindshrike-html|blindshrike|menu-rh13)\.html$", re.I)
FURNITURE = re.compile(r"date|pullout|copyright|invisible|size\d(sans)?serif(light|medium)?$", re.I)
NAV = re.compile(r"^\W*(\[\s*)?(part|page|chapter)\s+\w+\s*\]?(\s*\[\s*(part|page|chapter)\s+\w+\s*\])*\W*$|^\W*(next|previous|back|continue[ds]?|go to|read|on to)\b.{0,60}$|"
                 r"^\[.{0,80}\]$|^\|.*\|$|^home \|", re.I)
BIO = re.compile(r"\blives (in|with|on|near)\b|\bis an? (\w+[ -]){0,4}(writer|poet|author|novelist|editor|artist|journalist|critic|cartoonist|illustrator|mathematician)\b|"
                 r"\bis the author\b|\bauthor of\b|\b(stories|fiction|work|novels?|books?) (has|have) (appeared|been|won)\b|\bhas (been )?published\b|"
                 r"\b(his|her|their) (first|latest|most recent|new|next|second|third) (novel|book|collection|story)\b|\bweb ?site\b|\be-?mail\b|\bblog\b|"
                 r"\bcollection of (short )?stories\b|\b(hugo|nebula|world fantasy|tiptree|clarke|locus|campbell) award\b|\bclarion\b|\bforthcoming\b|"
                 r"\babout this story\b|\bthis story (was|is|first|originally|will)\b|\binfinite matrix\b|\billustration|\bphoto(graph)? by\b|\bcopyright\b|©|"
                 r"\bis a comics legend\b|\bteaches\b|\bwas born in\b|\bgrew up in\b|\bcan be (found|reached)\b|\bhas written\b|\bis working on\b|\bis at work on\b|\bfirst (appeared|published)\b|\boriginally (appeared|published)\b|\breprinted\b|\banthology\b", re.I)
HARDNAV = re.compile(r"^\W*\[\s*(previous|next|part \w+|page \w+)\s*\](\s*\[\s*(previous|next|part \w+|page \w+)\s*\])*\W*$", re.I)
DONATE = re.compile(r"^(like this story|keep 'em coming|we pay writers|you can contribute|paypal|amazon|t h a n k s|f u n d f e s t|if you like)", re.I)
SERIES = {"kadrey": ("Viper Wire", "Richard Kadrey"), "salmonson": ("", "Jessica Amanda Salmonson")}


def path_of(u):
    p = re.sub(r"^https?://[^/]+", "", u).split("?")[0]
    return re.sub(r"^/private/nextissue", "", p)


def load_index():
    idx = {}
    for f in sorted((HERE / "index").glob("*.html")):
        soup = prose.soup_of(prose.decode(f.read_bytes()))
        for a in soup.find_all("a"):
            h = (a.get("href") or "").replace("..stories", "../stories")
            m = re.search(r"(?:^|/)((?:stories/)?(?:shorts|shortshorts|swanwick|novels|excerpts)/[^#?\s]+\.html)", h)
            if not m:
                continue
            p = m.group(1)
            if not p.startswith("stories/"):
                p = "stories/" + p
            t = prose.fix(prose.norm_ws(a.get_text(" ")))
            if t and len(t) > 1:
                idx.setdefault("/" + p.lower(), t)
    return idx


MARK = re.compile(r"^\W*(begin|end|start)( of)?\b.{0,40}\b(text|blurb|bio|story|body|credits?|parts?)\W*$|^\W*(author|illustrator|artist|translator) bio\W*$|^link a?to additional parts.*$", re.I)
BRACKETS = re.compile(r"^\W*\[[^\[\]]{1,60}\](\s*\[[^\[\]]{1,60}\])+\W*$")
FILE_AUTHOR = {"varley": "John Varley", "salmonson": "Jessica Amanda Salmonson", "swanwick": "Michael Swanwick", "kadrey": "Richard Kadrey"}


def markers(paras, gaps):
    out = []
    mode = "body"
    seen_main = False
    for x in paras:
        if MARK.match(x):
            low = x.lower()
            if re.search(r"begin main (story|body) text|begin (story|body) text|start of (story|body)", low):
                out = []
                mode = "body"
                seen_main = True
            elif re.search(r"begin|^\W*(author|illustrator|artist|translator) bio|link a?to", low):
                mode = "skip"
            elif re.search(r"end( of)? (story|body|main)", low):
                mode = "done"
            elif mode == "skip" and re.search(r"end( of)? fundraising", low):
                mode = "body"
            continue
        if mode == "body":
            out.append(x)
    for i, x in enumerate(out):
        if BRACKETS.match(x) and i >= 0.4 * len(out):
            out = out[:i]
            break
    out = [x for x in out if not BRACKETS.match(x)]
    return out, ([g for g in gaps if g < len(out)] if out == paras else [])


def parse(m):
    soup = prose.soup_of(prose.decode((RAW / m["file"]).read_bytes()))
    head = prose.fix(prose.norm_ws(soup.title.get_text(" "))) if soup.title else ""
    bits = [b.strip() for b in head.split("|")]
    author = bits[1] if len(bits) >= 3 else ""
    title = bits[2] if len(bits) >= 3 else (bits[-1] if bits else "")
    t7 = soup.find(class_=re.compile(r"size7serif"))
    shown = prose.fix(prose.norm_ws(t7.get_text(" "))) if t7 else ""
    by = ""
    for s in soup.find_all(class_=re.compile(r"size3sanserif")):
        x = prose.fix(prose.norm_ws(s.get_text(" ")))
        if re.match(r"by\s+\S", x, re.I):
            by = re.sub(r"^by\s+", "", x, flags=re.I)
            break
    date = soup.find(class_="date")
    posted = ""
    if date:
        d = re.search(r"(\d\d)\.(\d\d)\.(\d\d)", date.get_text())
        if d:
            posted = f"20{d.group(3)}-{d.group(1)}-{d.group(2)}"
    links = [(a.get("href") or "").split("/")[-1].lower() for a in soup.find_all("a")]
    best, score = None, 0
    for td in soup.find_all(["td", "body"]):
        ps = [p for p in td.find_all("p", recursive=False) if not p.get("class")]
        w = sum(len(p.get_text().split()) for p in ps)
        if w > score:
            best, score = td, w
    paras = []
    gaps = []
    if best is not None:
        for t in list(best.find_all(True, recursive=False)):
            c = " ".join(t.get("class") or [])
            if c and FURNITURE.search(c):
                t.decompose()
            elif t.name == "table":
                t.decompose()
        for t in best.find_all(class_=FURNITURE):
            if t.name in ("p", "div", "td", "table"):
                t.decompose()
        for child in list(best.children):
            if getattr(child, "name", None) is None:
                txt = prose.norm_ws(str(child))
                if txt:
                    paras += prose.paragraphs("<p>" + txt + "</p>")
                continue
            got = prose.paragraphs(child)
            if not got:
                gaps.append(len(paras))
            paras += got
    paras, gaps = markers(paras, gaps)
    author = by or author
    author = re.split(r"\s+(?:translated|with an?|illustrat|art by|as told)\b", author, flags=re.I)[0].strip(" ,")
    if author and author == author.lower():
        author = " ".join(w.capitalize() if not re.match(r"o[’']", w) else w[:2].upper() + w[2:].capitalize() for w in author.split())
    return {"author": author, "title": title or shown, "shown": shown, "posted": posted, "links": links,
            "paras": paras, "gaps": gaps, "soft404": bool(re.search(r"404 Error|not found", head, re.I))}


def strip_tail(paras, author, gaps):
    names = [n for n in re.split(r"\s*(?:,|&| and )\s*", author) if n.strip()]
    firsts = {n.split()[0].lower() for n in names if n.split()} | {n.split()[-1].lower() for n in names if n.split()}
    removed = []
    hard = [i for i, x in enumerate(paras) if HARDNAV.match(x)]
    if hard and hard[-1] >= 0.5 * len(paras):
        removed = list(reversed(paras[hard[-1]:]))
        paras = paras[:hard[-1]]
    paras = [x for x in paras if not HARDNAV.match(x)]
    n = len(paras)
    for g in sorted({x for x in gaps if 0.6 * n <= x < n}, reverse=False):
        tail = paras[g:]
        words = sum(len(x.split()) for x in tail)
        starts = sum(1 for x in tail if x.split() and x.split()[0].strip("\"'“‘").lower().rstrip(".,'’s") in firsts)
        if words < 450 and (any(BIO.search(x) for x in tail) or starts):
            removed += list(reversed(tail))
            paras = paras[:g]
            break
    floor = max(len(paras) - 10, 1)
    while len(paras) > floor:
        p = paras[-1]
        w = p.split()
        if p == prose.BREAK or prose.END.match(p) or NAV.match(p) or DONATE.match(p) or prose.LINK in p:
            removed.append(paras.pop())
            continue
        if len(w) < 170 and (BIO.search(p) or (w and w[0].strip("\"'“‘").lower().rstrip(".,'’s") in firsts and len(removed) > 0)):
            removed.append(paras.pop())
            continue
        if len(w) < 170 and w and w[0].lower().strip("\"'“‘") in firsts and re.match(r"^\S+( \S+){0,3} (is|was|has|lives|writes|teaches|works|grew|began|says|multitasks|runs|can)\b", p):
            removed.append(paras.pop())
            continue
        break
    return paras, removed


def strip_head(paras, title, author):
    tk = prose.key(title)
    eaten = ""
    while paras:
        p = paras[0]
        k = prose.key(p)
        short = len(p.split()) <= 10 and not re.search(r"[.!?\"”,]$", p)
        if p == prose.BREAK or DONATE.match(p) or NAV.match(p) or re.fullmatch(r"\W*(main )?(body|story) text\W*", p, re.I):
            paras.pop(0)
            continue
        if re.fullmatch(r"\d\d\.\d\d\.\d\d", p) or (re.match(r"^by\s+\S", p, re.I) and len(p.split()) <= 9):
            paras.pop(0)
            continue
        if short and k and tk and (k in tk or tk in k or difflib.SequenceMatcher(None, k, tk).ratio() > 0.8 or tk.startswith(eaten + k) or prose.key(author) == k):
            eaten += k
            paras.pop(0)
            continue
        if short and eaten and difflib.SequenceMatcher(None, eaten + k, tk).ratio() > 0.8:
            paras.pop(0)
            continue
        if re.match(r"^(part|page) (one|two|three|1|2|3)\W*$", p, re.I):
            paras.pop(0)
            continue
        break
    return paras


def main():
    idx = load_index()
    man = [json.loads(l) for l in open(HERE / "raw.jsonl")]
    pages = {}
    for m in man:
        if m["status"] != 200 or not m["file"]:
            continue
        p = path_of(m["original"]).lower()
        if not p.startswith("/stories/") or not p.endswith(".html"):
            continue
        if p in pages and "/private/" in m["original"]:
            continue
        if re.search(rb"<title>[^<]*404 Error", (RAW / m["file"]).read_bytes()[:2000], re.I):
            continue
        pages[p] = m
    works = defaultdict(dict)
    for p, m in pages.items():
        parts = p.split("/")
        name = parts[-1]
        section = "/".join(parts[2:-1])
        if SKIP_FILE.match(name):
            continue
        stem = name[:-5]
        if section == "shorts":
            g = re.match(r"^(.*?)[_-]?(\d)?$", stem)
            base, n = g.group(1), int(g.group(2) or 1)
            if base + ".html" not in [x.split("/")[-1] for x in pages] and stem[-1:].isdigit() and (stem[:-1] + str(3 - n) + ".html" not in [x.split("/")[-1] for x in pages]) and n != 2:
                base, n = stem, 1
            works[(section, base)][n] = (p, m)
        else:
            works[(section, stem)][1] = (p, m)
    if TEXT.exists():
        shutil.rmtree(TEXT)
    TEXT.mkdir()
    recs = []
    for (section, base), parts in sorted(works.items()):
        order = sorted(parts)
        parsed = [parse(parts[n][1]) for n in order]
        first = parsed[0]
        url = "http://www.infinitematrix.net" + parts[order[0]][0]
        title = idx.get(parts[order[0]][0], "") or first["shown"] or first["title"]
        title = re.sub(r"\s*[,:(-]?\s*\(?(part|page)?\s*\b(1|one|i)\)?$", "", title, flags=re.I).strip() if len(order) > 1 or re.search(r"\d\.html$", parts[order[0]][0]) else title
        if title == title.lower():
            title = title.title().replace("’S", "’s").replace("'S", "'s")
        author = first["author"]
        if section == "shortshorts":
            for k, v in FILE_AUTHOR.items():
                if base.startswith(k):
                    author = v
        rec = {"source": "The Infinite Matrix (infinitematrix.net)", "section": section, "title": title, "author": author,
               "posted": first["posted"], "url": url,
               "wayback": [f"{parts[n][1]['served_timestamp']} {parts[n][1]['original']}" for n in order],
               "year": int(first["posted"][:4]) if first["posted"] else int(parts[order[0]][1]["served_timestamp"][:4]),
               "pages": len(order), "pages_expected": 0, "words": 0, "file": "", "status": "ok"}
        expected = len(order)
        for pp in (parsed if section == "shorts" else []):
            for l in pp["links"]:
                g = re.match(re.escape(base) + r"[_-]?(\d)\.html$", l)
                if g:
                    expected = max(expected, int(g.group(1)))
        rec["pages_expected"] = expected
        paras = []
        removed_all = []
        for pp in parsed:
            page, removed = strip_tail(list(pp["paras"]), author, pp["gaps"])
            for cand in (title, pp["shown"], pp["title"], title):
                if cand:
                    page = strip_head(page, cand, author)
            removed_all += removed
            paras += page
        text = prose.join(paras)
        rec["words"] = len(text.split())
        rec["_text"] = text
        if section.startswith("excerpts") or section.startswith("novels"):
            rec["status"] = "skipped: excerpt"
        elif expected > len(order) or order != list(range(1, len(order) + 1)):
            rec["status"] = f"incomplete: parts {order} of {expected} captured"
        elif re.search(r"bananas_foster|williams-rh12|menu-rh", parts[order[0]][0]):
            rec["status"] = "skipped: not fiction (a recipe)"
        elif rec["words"] < 60:
            rec["status"] = "skipped: under 60 words of prose (image or comic piece, or a one-paragraph squib)"
        elif not prose.english(text):
            rec["status"] = "skipped: not English"
        recs.append(rec)
    seen = {}
    for r in recs:
        if r["status"] != "ok":
            continue
        k = prose.key(r["_text"][:600])
        if k in seen:
            r["status"] = f"duplicate-of:{seen[k]['url']}"
            continue
        seen[k] = r
    have = {r["url"].lower() for r in recs}
    for p, t in sorted(idx.items()):
        u = "http://www.infinitematrix.net" + p
        if u in have or any(u in " ".join(r["wayback"]).lower() for r in recs) or SKIP_FILE.match(p.split("/")[-1]):
            continue
        base = re.sub(r"\d?\.html$", "", p)
        if any(r["url"].lower().startswith("http://www.infinitematrix.net" + base) for r in recs):
            continue
        recs.append({"source": "The Infinite Matrix (infinitematrix.net)", "section": "/".join(p.split("/")[2:-1]), "title": t, "author": "",
                     "posted": "", "url": u, "wayback": [], "year": None, "pages": 0, "pages_expected": 0, "words": 0, "file": "",
                     "status": "missing: no capture of the page"})
    used = set()
    for r in recs:
        if r["status"] != "ok":
            continue
        name = prose.slug((r["author"].split()[-1] + "-" if r["author"] else "") + (r["title"] or r["url"].split("/")[-1][:-5]))
        if name in used:
            name = name + "-" + prose.slug(r["url"].split("/")[-1][:-5])
        used.add(name)
        r["file"] = f"text/{name}.txt"
        (HERE / r["file"]).write_text(r["_text"], encoding="utf-8")
    with open(HERE / "ledger.jsonl", "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, ensure_ascii=False) + "\n")
    c = Counter((r["section"], r["status"].split(":")[0]) for r in recs)
    for k, v in sorted(c.items()):
        print(v, *k)
    print("words ok", sum(r["words"] for r in recs if r["status"] == "ok"))


if __name__ == "__main__":
    main()
