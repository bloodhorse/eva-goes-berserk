import argparse
import hashlib
import json
import posixpath
import re
import unicodedata
import warnings
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup, NavigableString, Tag, XMLParsedAsHTMLWarning
from lxml import etree

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="bs4")

BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "pre", "section",
         "article", "header", "footer", "ul", "ol", "table", "tr", "td", "th", "dl", "dt", "dd",
         "figure", "hr", "center", "body", "main", "nav", "aside", "tbody", "thead"}
HEAD_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
STRIP_TAGS = {"head", "script", "style", "img", "svg", "image", "figcaption", "object", "audio",
              "video", "map", "area", "math", "noscript", "iframe"}

WATERMARK = re.compile(r"z-?lib|1lib|oceanofpdf|libgen|library\.sk|b-ok\.|bookfi|epubpub|"
                       r"https?://|www\.|\b[\w-]+\.(com|org|net|ru|sk|io|info|to)\b", re.I)
CREDIT = re.compile(r"this file was created|bookdesigner|converted by|created (with|by) calibre|"
                    r"epub base r|digital editor|\bepub r\d|scanned by|proofread by|ocr by|"
                    r"downloaded from|free ebooks? (at|from)", re.I)


KEEP_TYPES = {"bodymatter", "chapter", "part", "prologue", "epilogue", "epigraph", "appendix",
              "glossary", "conclusion", "division", "volume", "text", "start"}
DROP_TYPES = {
    "cover": "cover", "titlepage": "title page", "title-page": "title page",
    "halftitlepage": "half-title page", "fulltitle": "title page",
    "copyright-page": "copyright page", "copyright": "copyright page", "imprint": "copyright page",
    "toc": "table of contents", "landmarks": "table of contents", "loi": "list of illustrations",
    "lot": "list of tables", "dedication": "dedication", "acknowledgments": "acknowledgements",
    "acknowledgements": "acknowledgements", "foreword": "foreword", "preface": "preface",
    "introduction": "introduction", "afterword": "afterword", "colophon": "colophon",
    "contributors": "about the author", "other-credits": "credits", "errata": "errata",
    "footnotes": "footnotes", "endnotes": "endnotes", "rearnotes": "endnotes", "index": "index",
    "bibliography": "bibliography", "seriespage": "also by", "adcard": "also by",
    "teaser": "preview of another book", "praise": "praise", "credits": "credits",
}

LABEL_RULES = [
    (r"^(front ?)?cover$|^cubierta$|^portada$", "cover"),
    (r"^(half[- ]?)?title( ?page)?$|^titulo|^t[ií]tulo", "title page"),
    (r"copyright|^info$|^legal|^imprint|^colophon|^cr[eé]ditos", "copyright page"),
    (r"^(table of )?contents$|^toc$|^[ií]ndice$|^contenido", "table of contents"),
    (r"^dedicat|^dedicatoria", "dedication"),
    (r"acknowledg|^agradec|^thanks$", "acknowledgements"),
    (r"about the (author|translator|illustrator|editor|publisher)|^autor$|^about$|^bio(graphy)?$"
     r"|^author bio|^el autor|meet the author", "about the author"),
    (r"^also by|^books by|^by the same author|^other (books|titles|works) by|^more (books|from)"
     r"|^also available|^also from|^titles by|^works by", "also by"),
    (r"^praise|^advance praise|^critical acclaim|^reviews?$|^what (critics|people) are saying", "praise"),
    (r"^sinopsis$|^synopsis$|^blurb$|^back ?cover|^about the book|^summary$|^description$", "blurb"),
    (r"^foreword|^pr[oó]logo del|^preface|^introduction|^editor'?s? (note|introduction)"
     r"|^publisher'?s? note|^a note (on|about) the (text|translation|edition|type)", "introduction/foreword"),
    (r"^afterword|^postscript|^ep[ií]logo del|^appreciation|^critical essay|^an appreciation", "afterword"),
    (r"translator'?s? (note|preface|introduction|afterword)|^note on (the )?translation", "translator's note"),
    (r"reading (group|guide)|discussion (questions|guide)|^questions for discussion|book club", "reading guide"),
    (r"^(an )?interview|in conversation with|^a conversation with", "interview"),
    (r"excerpt|^preview|^sneak peek|^read on|^coming soon|^turn the page|^keep reading|^bonus|^teaser", "preview of another book"),
    (r"newsletter|^sign up|^join (our|the)|^get (updates|exclusive)|^follow us|^stay (up|in touch)|^discover more|^want more", "newsletter/ad"),
    (r"^(foot|end)?notes$|^notas$", "notes"),
    (r"^index$", "index"),
    (r"^bibliography$|^further reading$|^sources$", "bibliography"),
    (r"^map(s)?$|^illustrations$|^list of (illustrations|maps)", "maps/illustrations"),
]
KEEP_LABELS = re.compile(r"^(prologue|epilogue|coda|appendix|appendices|glossary|part\b|book\b|chapter\b"
                         r"|interlude|envoi|dramatis personae|epigraph)", re.I)

FILE_RULES = [
    (r"^(front)?cover|cubierta|portada|^cvi$|^cvt$|^cover", "cover"),
    (r"^(half)?title(page)?$|^titulo|^tp$|^htp$|^halftitle", "title page"),
    (r"copyright|^cop$|^info$|^legal|^imprint|^colophon|^credits", "copyright page"),
    (r"^toc$|^contents$|^indice$|^nav$", "table of contents"),
    (r"^ded(ic|ication|icatoria)?$|dedication", "dedication"),
    (r"^ack(s|nowledg\w*)?$|acknowledg|agradec", "acknowledgements"),
    (r"^(about)?(the)?author$|^autor$|^ata$|^bio$|^abouttheauthor|^aboutauthor", "about the author"),
    (r"^alsoby$|^also$|^adcard$|^ad$|^bm\d*$|^nbm\d*$|^otherbooks$|^booksby", "also by"),
    (r"^praise$|^col1$|^reviews$", "praise"),
    (r"^sinopsis$|^synopsis$|^blurb$|^backcover$|^description$", "blurb"),
    (r"^foreword$|^preface$|^intro(duction)?$|^fwd$|^pref$", "introduction/foreword"),
    (r"^afterword$|^aft$|^appreciation$", "afterword"),
    (r"^(teaser|excerpt|preview|sneakpeek|bonus)", "preview of another book"),
    (r"^newsletter|^signup|^ads?$", "newsletter/ad"),
    (r"^(foot|end)?notes$|^fn$", "notes"),
]

HYPE = re.compile(r"\b(bestsell\w*|best-sell\w*|masterpiece|award-winning|acclaimed|hugo|nebula|"
                  r"pulitzer|booker|winner of|now a major|classic of|the novel that|this novel|"
                  r"in this (novel|book)|new york times|stunning|tour de force|a must-read)\b", re.I)
QUOTE_ATTR = re.compile(r"^[—–-]{1,2}\s*\S|^[—–]\s*[A-Z]")
ROMAN = re.compile(r"^[IVXLC]+\.?$")
WS = re.compile(r"[ \t\r\f\v  -   　]+")
INVIS = re.compile(r"[­​‌‍⁠﻿]")
BREAK_CLASS = re.compile(r"break|scene|space|separ|orn|asterisk|salto|dingbat|divider|transition|gap|blank|fleuron|center-?star|tb\b", re.I)
BREAK_TEXT = re.compile(r"^[\s*·•∙~#◊⁂§❧☙✦✧❦❖⸙◆◇○●□■_=+\-–—.]*$")
SMALLCAP_CLASS = re.compile(r"small|smcap|\bsc\b|caps", re.I)
FOOTREF = re.compile(r"^\[?\(?[0-9ivx]{1,4}\)?\]?$|^[*†‡§]+$", re.I)


def norm_ws(s):
    s = INVIS.sub("", s)
    lines = [WS.sub(" ", ln).strip() for ln in s.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def ascii_slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def clean_title(t):
    t = re.sub(r"\s*[\(\[].*?[\)\]]", "", t or "")
    t = WATERMARK.sub("", t)
    return t.strip(" .-_:")


def author_surname(a):
    a = re.sub(r"\s*[\(\[].*?[\)\]]", "", a or "").strip()
    if not a:
        return "unknown"
    a = re.split(r"\s*(?:&|;| and )\s*", a)[0]
    if "," in a:
        return a.split(",")[0].strip()
    parts = [p for p in a.split() if not re.match(r"^(jr|sr|ii|iii|phd)\.?$", p, re.I)]
    return parts[-1] if parts else a


def make_slug(title, author):
    t = clean_title(title)
    t = re.split(r"\s*[:;]\s+|\s+[-–—]\s+", t)[0]
    words = ascii_slug(t).split("-")
    if len(words) > 1 and words[0] in {"the", "a", "an"}:
        words = words[1:]
    words = [w for w in words if w][:4]
    return "-".join([ascii_slug(author_surname(author)) or "unknown"] + (words or ["untitled"]))


def label_reason(label):
    l = (label or "").strip().lower()
    l = re.sub(r"^[\d\W_]+", "", l)
    if not l or KEEP_LABELS.match(l):
        return None
    for pat, why in LABEL_RULES:
        if re.search(pat, l):
            return why
    return None


def file_reason(href):
    stem = posixpath.splitext(posixpath.basename(href))[0].lower()
    toks = [t for t in re.split(r"[^a-z0-9]+", stem) if t]
    cands = toks + ["".join(toks)]
    for pat, why in FILE_RULES:
        if any(re.search(pat, t) for t in cands):
            return why
    return None


class Block:
    __slots__ = ("text", "head", "links", "brk", "tag", "cls", "gap", "sc")

    def __init__(self, text, head=False, links=0.0, brk=False, tag="p", cls=""):
        self.text, self.head, self.links, self.brk, self.tag = text, head, links, brk, tag
        self.cls, self.gap, self.sc = cls, False, 0

    @property
    def words(self):
        return len(self.text.split())


def is_smallcap(tag):
    if tag.name == "small":
        return True
    cls = " ".join(tag.get("class") or [])
    if re.search(r"drop|initial|first-?letter|dcap", cls, re.I):
        return False
    st = tag.get("style") or ""
    return bool(SMALLCAP_CLASS.search(cls)) or "small-caps" in st


def inline_pieces(node, out, in_link=False, in_sc=False):
    for ch in node.children:
        if isinstance(ch, NavigableString):
            if ch.__class__.__name__ in ("Comment", "Doctype", "ProcessingInstruction", "CData"):
                continue
            out.append([str(ch), in_link, in_sc])
        elif isinstance(ch, Tag):
            if ch.name == "br":
                out.append(["\n", in_link, in_sc])
                continue
            link = in_link or (ch.name == "a" and ch.get("href") is not None)
            inline_pieces(ch, out, link, in_sc or is_smallcap(ch))


def make_block(tag):
    pieces = []
    inline_pieces(tag, pieces)
    pos, sc = 0, 0
    for k, p in enumerate(pieces):
        rest = "".join(q[0] for q in pieces[k + 1:] if not q[2])
        if p[2] and len(p[0].strip()) > 1 and p[0].strip().isupper() and pos <= 2 and re.search(r"[a-z]", rest):
            p[0] = p[0].lower()
            sc = pos + len(p[0])
        pos += len(p[0].strip())
    raw = "".join(p[0] for p in pieces)
    text = norm_ws(raw)
    total = sum(len(p[0].strip()) for p in pieces) or 1
    linked = sum(len(p[0].strip()) for p in pieces if p[1])
    head = tag.name in HEAD_TAGS or bool(re.search(r"head|title|chap", " ".join(tag.get("class") or []), re.I))
    brk = False
    if tag.name == "hr":
        brk = True
    elif BREAK_TEXT.match(text) and (text or BREAK_CLASS.search(" ".join(tag.get("class") or []))
                                      or tag.get("data-ornament") is not None or tag.find(["img", "svg"]) is not None):
        brk = bool(text) or bool(BREAK_CLASS.search(" ".join(tag.get("class") or []))) or tag.find(["img", "svg"]) is not None
    if text and re.fullmatch(r"[*·•∙◊⁂❧☙✦✧❦❖⸙◆◇~#§\s]+", text):
        brk = True
    b = Block(text, head, linked / total, brk, tag.name, " ".join(tag.get("class") or []))
    b.sc = sc
    return b


def has_block_child(tag):
    return any(isinstance(c, Tag) and c.name in BLOCK for c in tag.children)


def collect_blocks(node, out):
    buf = []
    for ch in list(node.children):
        if isinstance(ch, Tag) and ch.name in BLOCK:
            if buf:
                t = norm_ws("".join(buf))
                if t:
                    out.append(Block(t))
                buf = []
            if ch.name == "hr":
                out.append(Block("", brk=True, tag="hr"))
            elif has_block_child(ch):
                collect_blocks(ch, out)
            else:
                b = make_block(ch)
                if b.text or b.brk:
                    out.append(b)
        elif isinstance(ch, Tag):
            buf.append(ch.get_text())
        elif isinstance(ch, NavigableString) and ch.__class__.__name__ == "NavigableString":
            buf.append(str(ch))
    if buf:
        t = norm_ws("".join(buf))
        if t:
            out.append(Block(t))


def epub_types(soup):
    found = set()
    for el in soup.find_all(True):
        for k in ("epub:type", "type", "role"):
            v = el.get(k)
            if v and el.name not in ("a", "link", "script", "style", "input", "ol", "li", "span", "aside", "sup"):
                for t in re.split(r"\s+", v):
                    found.add(t.split(":")[-1].replace("doc-", "").lower())
    return found


def preclean(soup):
    for t in soup.find_all(STRIP_TAGS):
        if t.name in ("img", "svg", "image") and t.parent is not None:
            t.replace_with(soup.new_string(""))
            continue
        t.decompose()
    for t in soup.find_all(True):
        et = (t.get("epub:type") or "") + " " + (t.get("role") or "")
        if re.search(r"pagebreak|page-break|noteref|footnote|endnote|rearnote|doc-backlink", et):
            t.decompose()
    for t in soup.find_all("aside"):
        t.decompose()
    for t in soup.find_all(["span", "a"]):
        if t.parent is None:
            continue
        cls = " ".join(t.get("class") or []) + " " + (t.get("id") or "")
        txt = t.get_text().strip()
        if re.search(r"page|pg\b|pagenum", cls, re.I) and re.fullmatch(r"[\divxlc]*", txt, re.I) and t.name == "span":
            t.decompose()
    for a in soup.find_all("a"):
        if a.parent is None or a.get("href") is None:
            continue
        txt = a.get_text().strip()
        if FOOTREF.match(txt) or (a.parent.name == "sup"):
            a.decompose()
    for s in soup.find_all("sup"):
        if s.parent is not None and FOOTREF.match(s.get_text().strip() or "x"):
            s.decompose()


def html_blocks(data):
    soup = BeautifulSoup(data, "lxml")
    types = epub_types(soup)
    preclean(soup)
    body = soup.body or soup
    out = []
    collect_blocks(body, out)
    return out, types


def read_xml(z, name):
    return etree.fromstring(z.read(name), parser=etree.XMLParser(recover=True))


def xp(node, path):
    return node.xpath(path)


def nav_labels(z, opf_dir, manifest, opf):
    labels, landmarks = {}, {}

    def put(href, label, base):
        if not href:
            return
        full = posixpath.normpath(posixpath.join(base, unquote(href.split("#")[0])))
        labels.setdefault(full, norm_ws(label or ""))

    for it in manifest.values():
        props = it.get("properties") or ""
        mt = it.get("media-type") or ""
        href = posixpath.normpath(posixpath.join(opf_dir, unquote(it.get("href") or "")))
        try:
            if "nav" in props.split():
                soup = BeautifulSoup(z.read(href), "lxml")
                base = posixpath.dirname(href)
                for nav in soup.find_all("nav"):
                    kind = (nav.get("epub:type") or "").split(":")[-1]
                    for a in nav.find_all("a"):
                        if kind == "landmarks":
                            full = posixpath.normpath(posixpath.join(base, unquote((a.get("href") or "").split("#")[0])))
                            landmarks[full] = ((a.get("epub:type") or "").split(":")[-1].lower(), a.get_text())
                        elif kind == "toc":
                            put(a.get("href"), a.get_text(), base)
            elif mt == "application/x-dtbncx+xml":
                ncx = read_xml(z, href)
                base = posixpath.dirname(href)
                for np in xp(ncx, "//*[local-name()='navPoint']"):
                    lab = " ".join(xp(np, "./*[local-name()='navLabel']//text()"))
                    src = xp(np, "./*[local-name()='content']/@src")
                    if src:
                        put(src[0], lab, base)
        except KeyError:
            continue
    for ref in xp(opf, "//*[local-name()='guide']/*[local-name()='reference']"):
        full = posixpath.normpath(posixpath.join(opf_dir, unquote((ref.get("href") or "").split("#")[0])))
        landmarks.setdefault(full, ((ref.get("type") or "").lower(), ref.get("title") or ""))
    return labels, landmarks


def content_reason(sec, title, author, zone):
    txt = sec["text"]
    w = sec["words"]
    low = txt.lower()
    first = sec["first"].lower()
    if w == 0:
        return "no text (image or blank page)"
    if sec["links"] > 0.6 and w < 3000:
        return "table of contents (link list)"
    if w < 800 and re.search(r"©|\(c\) ?\d{4}|all rights reserved|\bisbn\b|library of congress|"
                             r"printed in (the )?(usa|united states|great britain)|first (published|edition)|"
                             r"published by|copyright \d{4}|cataloging-in-publication", low):
        return "copyright/publisher page"
    if w < 1500 and re.search(r"^(also by|books by|by the same author|other (books|titles|works) by|also available)", first):
        return "also by"
    if w < 1500 and re.search(r"^(praise for|advance praise|acclaim for)", first):
        return "praise"
    if w < 1000 and CREDIT.search(low):
        return "converter credit"
    if w < 600 and zone != "body" and re.search(r"\b(is the author of|was born in|was born on|lives (in|with)|"
                                                 r"died in \d{4}|his (first|latest) novel|her (first|latest) novel|"
                                                 r"\(born \w+ \d|is an? (american|british|english|canadian|irish|scottish|australian)[\w\- ]* (writer|author|novelist))", low):
        return "about the author"
    if w < 400 and zone != "body" and re.search(r"\b(wish(es)? to thank|grateful|my thanks|thanks (are due )?to|indebted to)\b", low):
        return "acknowledgements"
    quotes = len(re.findall(r"[”\"]\s*\n?\s*[—–]\s*[A-Z]", txt))
    if zone != "body" and quotes >= 2 and w < 3000:
        return "praise (review quotes)"
    if zone == "front" and w < 40:
        sur = author_surname(author).lower()
        t = clean_title(title).lower()
        if (t and t in low) or (sur and sur in low):
            return "title page"
        if re.match(r"^(for|to)\b", first):
            return "dedication"
    if zone == "front" and w < 400 and HYPE.search(txt):
        return "blurb"
    if zone == "front" and w < 400 and clean_title(title).lower() in low and not sec["has_attr"]:
        return "blurb"
    if zone == "back" and w >= 300:
        sur = author_surname(author)
        if sur and len(re.findall(r"\b" + re.escape(sur) + r"\b", txt[:6000])) >= 2:
            return "afterword by someone else (writes about the author)"
    if zone == "back" and w < 300 and not sec["kept_label"]:
        return "short back-matter page"
    return None


def section_record(blocks):
    text = "\n".join(b.text for b in blocks if b.text)
    first = next((b.text for b in blocks if b.text), "")
    chars = sum(len(b.text) for b in blocks) or 1
    links = sum(b.links * len(b.text) for b in blocks) / chars
    has_attr = any(QUOTE_ATTR.match(b.text) for b in blocks)
    return {"text": text, "words": len(text.split()), "first": first[:200], "links": links, "has_attr": has_attr}


def drop_toc_runs(blocks):
    keep, i, dropped = [], 0, 0
    while i < len(blocks):
        j = i
        while j < len(blocks) and blocks[j].links > 0.8 and blocks[j].words <= 15:
            j += 1
        if j - i >= 3:
            dropped += sum(b.words for b in blocks[i:j])
            i = j
            continue
        keep.append(blocks[i])
        i += 1
    return keep, dropped


def scrub_blocks(blocks, first_body):
    out, notes = [], []
    for k, b in enumerate(blocks):
        if b.text and (WATERMARK.search(b.text) or (b.words <= 25 and CREDIT.search(b.text))):
            if b.words <= 40:
                notes.append(f"line with url/watermark/credit ({b.words}w): {b.text[:60]!r}")
                continue
            parts = re.split(r"(?<=[.!?…”])\s+", b.text)
            bad = [x for x in parts if WATERMARK.search(x)]
            b.text = " ".join(x for x in parts if not WATERMARK.search(x))
            notes.append(f"sentence with url/watermark cut from a paragraph: {bad[0][:60]!r}")
            if not b.text:
                continue
        if b.text and re.fullmatch(r"\d{1,4}", b.text) and k > 0 and not b.head:
            continue
        if b.text and re.fullmatch(r"(page|p\.)\s*\d+", b.text, re.I):
            continue
        out.append(b)
    out, tocw = drop_toc_runs(out)
    if tocw:
        notes.append(f"in-file table of contents ({tocw}w)")
    if first_body:
        res = []
        seen_prose = False
        for b in out:
            if b.words >= 40:
                seen_prose = True
            if not seen_prose and b.words <= 30 and re.match(r"^(for|to)\s+\S", b.text, re.I) and not QUOTE_ATTR.match(b.text) \
                    and not re.search(r"[.?!…]$", b.text.split("\n")[-1].strip()) and not any(x in b.text for x in "“\"‘"):
                notes.append(f"dedication line ({b.words}w): {b.text[:50]!r}")
                continue
            res.append(b)
        out = res
    return out, notes


CHAP_RE = re.compile(r"^(\d{1,3}|[IVXLC]+)\b|^(chapter|part|book|prologue|epilogue)\b", re.I)


def unwrap(t):
    ls = t.split("\n")
    if len(ls) < 2:
        return t
    lower_start = any(re.match(r"^[“\"‘'(]?[a-z]", x) for x in ls[1:])
    if not lower_start and sorted(len(x) for x in ls)[len(ls) // 2] < 40:
        return t
    out = ls[0]
    for x in ls[1:]:
        out = out + x if re.search(r"[a-z]-$", out) and x[:1].islower() else out + " " + x
    return out


def render(blocks):
    lines = []
    prev_head = False
    for b in blocks:
        if b.brk:
            if lines and lines[-1] != "* * *":
                lines.append("* * *")
            prev_head = False
            continue
        t = b.text
        if lines and lines[-1] == "* * *" and (b.head or (b.words <= 8 and CHAP_RE.match(t))):
            lines.pop()
        if b.gap and lines and lines[-1] != "* * *" and not prev_head and not (b.words <= 8 and CHAP_RE.match(t)):
            lines.append("* * *")
        if b.head:
            t = " ".join(t.split())
            if prev_head and lines and b.words <= 8 and len(lines[-1].split()) <= 8:
                lines[-1] = lines[-1].rstrip(":.") + ": " + t
                continue
        else:
            t = unwrap(t)
        prev_head = b.head and b.words <= 8
        lines.append(t)
    while lines and lines[0] == "* * *":
        lines.pop(0)
    while lines and lines[-1] == "* * *":
        lines.pop()
    return lines


def process_epub(path, src_name=None):
    z = zipfile.ZipFile(path)
    warns = []
    try:
        opf_path = read_xml(z, "META-INF/container.xml").xpath("//*[local-name()='rootfile']/@full-path")[0]
    except (KeyError, IndexError):
        opf_path = next(n for n in z.namelist() if n.endswith(".opf"))
        warns.append("no container.xml rootfile")
    opf = read_xml(z, opf_path)
    opf_dir = posixpath.dirname(opf_path)
    title = norm_ws(" ".join(xp(opf, "//*[local-name()='metadata']/*[local-name()='title'][1]//text()")))
    creators = xp(opf, "//*[local-name()='metadata']/*[local-name()='creator']")
    author = ""
    for c in creators:
        role = c.get("{http://www.idpf.org/2007/opf}role") or c.get("role") or "aut"
        if role in ("aut", ""):
            author = norm_ws(c.text or "")
            break
    if not author and creators:
        author = norm_ws(creators[0].text or "")
    lang = norm_ws(" ".join(xp(opf, "//*[local-name()='metadata']/*[local-name()='language']/text()")))
    manifest = {it.get("id"): it for it in xp(opf, "//*[local-name()='manifest']/*[local-name()='item']")}
    labels, landmarks = nav_labels(z, opf_dir, manifest, opf)
    secs = []
    for ir in xp(opf, "//*[local-name()='spine']/*[local-name()='itemref']"):
        it = manifest.get(ir.get("idref"))
        if it is None:
            continue
        href = posixpath.normpath(posixpath.join(opf_dir, unquote(it.get("href") or "")))
        if "html" not in (it.get("media-type") or "html"):
            continue
        try:
            blocks, types = html_blocks(z.read(href))
        except KeyError:
            warns.append(f"missing spine file {href}")
            continue
        sec = {"href": href, "blocks": blocks, "types": types, "label": labels.get(href, ""),
               "landmark": landmarks.get(href, ("", ""))[0], "linear": ir.get("linear") != "no"}
        sec.update(section_record(blocks))
        head = next((b.text for b in blocks if b.text), "")
        sec["head"] = head if len(head.split()) <= 12 else ""
        secs.append(sec)
    mark_gaps(z, secs, warns)
    return title, author, lang, secs, warns


GAP_CSS = re.compile(r"([^{}]+)\{([^}]*)\}")
GAP_PROP = re.compile(r"(?:margin|padding)-top\s*:\s*([\d.]+)\s*(em|rem|px|pt|%)", re.I)


def mark_gaps(z, secs, warns):
    css = "".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.lower().endswith(".css"))
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    gaps = set()
    for sel, body in GAP_CSS.findall(css):
        m = GAP_PROP.search(body)
        if not m:
            continue
        v, u = float(m.group(1)), m.group(2).lower()
        if (u in ("em", "rem") and v >= 1) or (u in ("px", "pt") and v >= 14) or (u == "%" and 3 <= v <= 20):
            for c in re.findall(r"\.([\w-]+)", sel):
                gaps.add(c)
    if not gaps:
        return
    count, total = {}, 0
    for sec in secs:
        for b in sec["blocks"]:
            if b.tag == "p" and not b.head and b.words > 3:
                total += 1
                for c in b.cls.split():
                    count[c] = count.get(c, 0) + 1
    use = {c for c in gaps if 0 < count.get(c, 0) <= 0.2 * max(total, 1)}
    hits = 0
    for sec in secs:
        if sec["words"] < 1000:
            continue
        seen = False
        for b in sec["blocks"]:
            if seen and b.tag == "p" and not b.head and b.words > 3 and set(b.cls.split()) & use:
                b.gap = True
                hits += 1
            seen = seen or b.words >= 20
    if hits:
        warns.append(f"scene breaks from css spacing classes {sorted(use)}: {hits}")


def strong_reason(sec):
    lm = sec["landmark"]
    if lm in KEEP_TYPES:
        return None, True
    types = sec["types"]
    keep_hit = types & KEEP_TYPES
    for t in sorted(types):
        if t in DROP_TYPES and not keep_hit:
            return f"epub:type {t} ({DROP_TYPES[t]})", False
    if lm in DROP_TYPES and not (lm == "toc" and sec["links"] < 0.5 and sec["words"] > 1000):
        return f"guide/landmark {lm} ({DROP_TYPES[lm]})", False
    if lm == "cover" or lm.startswith("cover"):
        return "guide cover", False
    for src, val in (("nav label", sec["label"]), ("heading", sec["head"])):
        if val and KEEP_LABELS.match(re.sub(r"^[\d\W_]+", "", val.lower())):
            return None, True
        r = label_reason(val)
        if r:
            return f"{src} {val[:40]!r} ({r})", False
    r = file_reason(sec["href"])
    if r:
        return f"file name {posixpath.basename(sec['href'])} ({r})", False
    return None, bool(keep_hit)


def classify(title, author, secs, warns):
    for s in secs:
        s["reason"], s["kept_label"] = strong_reason(s)
        if not s["linear"] and not s["reason"] and not s["kept_label"]:
            s["reason"] = "spine linear=no"
    body_idx = [i for i, s in enumerate(secs) if not s["reason"] and (s["words"] >= 300 or s["kept_label"]) and s["links"] < 0.6]
    if not body_idx:
        warns.append("no body section found by structure; keeping all non-matter sections")
        body_idx = [i for i, s in enumerate(secs) if not s["reason"]] or [0]
    lo, hi = body_idx[0], body_idx[-1]
    for i, s in enumerate(secs):
        zone = "front" if i < lo else "back" if i > hi else "body"
        s["zone"] = zone
        if s["reason"]:
            continue
        r = content_reason(s, title, author, zone)
        if r:
            if zone == "body" and s["words"] >= 300 and not r.startswith(("copyright", "table", "also", "praise", "converter")):
                warns.append(f"{posixpath.basename(s['href'])}: looks like {r} but sits inside the body; kept")
            else:
                s["reason"] = r
                continue
        if zone == "front" and not s["kept_label"] and s["words"] > 0:
            s["note"] = "front-matter section kept as epigraph/part of work"
        if zone == "back" and not s["kept_label"] and s["words"] >= 300:
            s["note"] = "back-matter section kept (unlabelled, may be author's own)"
    return lo


def same_title(text, title):
    k = lambda x: re.sub(r"[\W_]+", "", unicodedata.normalize("NFKD", x).lower())
    return bool(k(title)) and k(text) == k(title)


def recase(secs):
    caps, low = {}, {}
    for s in secs:
        if s.get("reason"):
            continue
        for b in s["blocks"]:
            for m in re.finditer(r"(?<![.!?:“\"‘—]\s)(?<=\s)([A-Za-z][a-z']+)", b.text):
                w = m.group(1)
                d = caps if w[0].isupper() else low
                d[w.lower()] = d.get(w.lower(), 0) + 1
    for s in secs:
        for b in s["blocks"]:
            if not b.sc:
                continue
            head, tail = b.text[:b.sc], b.text[b.sc:]
            fix = lambda m: m.group(0).capitalize() if caps.get(m.group(0), 0) >= 3 and caps.get(m.group(0), 0) > 4 * low.get(m.group(0), 0) else m.group(0)
            b.text = head[:1] + re.sub(r"[a-z']+", fix, head[1:]) + tail


def assemble(secs, lo, warns, title=""):
    recase(secs)
    kept, dropped, out = [], [], []
    first_body = True
    for i, s in enumerate(secs):
        name = posixpath.basename(s["href"])
        if s["reason"]:
            dropped.append({"file": name, "words": s["words"], "reason": s["reason"], "start": s["first"][:60]})
            continue
        blocks, notes = scrub_blocks(s["blocks"], first_body and i >= lo)
        if not out:
            lead = [b for b in blocks[:3] if same_title(b.text, title)]
            if lead:
                notes.append(f"book title repeated as a line: {lead[0].text[:50]!r}")
                blocks = [b for b in blocks if b not in lead]
        if i >= lo:
            first_body = False
        lines = render(blocks)
        w = sum(len(l.split()) for l in lines)
        if w == 0:
            dropped.append({"file": name, "words": s["words"], "reason": "nothing left after scrub", "start": s["first"][:60]})
            continue
        entry = {"file": name, "words": w, "start": lines[0][:60]}
        if notes:
            entry["scrubbed"] = notes
        if s.get("note"):
            entry["note"] = s["note"]
            warns.append(f"{name}: {s['note']} ({w}w): {lines[0][:50]!r}")
        kept.append(entry)
        out.extend(lines)
    return out, kept, dropped


def finish_text(lines):
    text = "\n\n".join(lines)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def from_epub(path):
    title, author, lang, secs, warns = process_epub(path)
    lo = classify(title, author, secs, warns)
    lines, kept, dropped = assemble(secs, lo, warns, clean_title(title))
    if len(secs) <= 4 and sum(s["words"] for s in secs) > 20000:
        warns.append(f"only {len(secs)} spine files for the whole book: matter inside them is judged by line heuristics only")
    return title, author, lang, finish_text(lines), kept, dropped, warns


def from_mobi(path):
    try:
        import mobi
    except ImportError:
        raise SystemExit("mobi/azw3 needs: --with mobi")
    tmp, out = mobi.extract(str(path))
    out = Path(out)
    if out.suffix.lower() == ".pdf":
        res = from_pdf(out)
        res[6].append("mobi/azw3 held only a pdf")
        return res
    if out.suffix.lower() == ".epub":
        res = from_epub(out)
        res[6].append("converted from mobi/azw3 (KF8 epub)")
        return res
    title, author = "", ""
    opfs = list(Path(tmp).rglob("*.opf"))
    if opfs:
        o = etree.parse(str(opfs[0]), etree.XMLParser(recover=True))
        title = norm_ws(" ".join(o.xpath("//*[local-name()='title'][1]//text()")))
        author = norm_ws(" ".join(o.xpath("//*[local-name()='creator'][1]//text()")))
    data = out.read_bytes()
    parts = re.split(rb"<mbp:pagebreak\s*/?>", data, flags=re.I)
    secs = []
    for k, part in enumerate(parts):
        blocks, types = html_blocks(part)
        sec = {"href": f"part{k:03d}.html", "blocks": blocks, "types": types, "label": "", "landmark": "", "linear": True}
        sec.update(section_record(blocks))
        head = next((b.text for b in blocks if b.text), "")
        sec["head"] = head if len(head.split()) <= 12 else ""
        secs.append(sec)
    warns = ["mobi (old format): sections split on page breaks, matter judged by heuristics only"]
    lo = classify(title, author, secs, warns)
    lines, kept, dropped = assemble(secs, lo, warns, clean_title(title))
    return title, author, "", finish_text(lines), kept, dropped, warns


def name_guess(path):
    stem = WATERMARK.sub("", Path(path).stem)
    stem = re.sub(r"\((?:[^)]*(?:lib|\.sk|\.com)[^)]*)\)", "", stem)
    stem = re.sub(r"^_+|_OceanofPDF|_+$", "", stem).replace("_", " ")
    m = re.match(r"(.+?)\s*\(([^)]+)\)\s*$", stem.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = re.match(r"(.+?)\s+-\s+(.+)$", stem.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return stem.strip(), ""


def text_sections(raw):
    paras = [norm_ws(p) for p in re.split(r"\n\s*\n", raw.replace("\r\n", "\n"))]
    secs, cur = [], []
    for p in paras:
        if not p:
            continue
        if re.match(r"^(chapter|part|book|prologue|epilogue)\b|^[IVXLC]+\.?$|^\d{1,3}\.?$", p, re.I) and cur:
            secs.append(cur)
            cur = []
        cur.append(Block(p.replace("\n", " ") if len(p) > 200 else p, head=len(p.split()) <= 8))
    if cur:
        secs.append(cur)
    return secs


def from_plain(path, raw, warns, fmt):
    title, author = name_guess(path)
    secs = []
    for k, blocks in enumerate(text_sections(raw)):
        for b in blocks:
            if BREAK_TEXT.match(b.text) and b.text.strip():
                b.brk = True
        sec = {"href": f"{fmt}{k:03d}", "blocks": blocks, "types": set(), "label": "", "landmark": "", "linear": True}
        sec.update(section_record(blocks))
        sec["head"] = blocks[0].text if blocks[0].words <= 12 else ""
        secs.append(sec)
    lo = classify(title, author, secs, warns)
    lines, kept, dropped = assemble(secs, lo, warns, clean_title(title))
    return title, author, "", finish_text(lines), kept, dropped, warns


def from_txt(path):
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            raw = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    return from_plain(path, raw, ["plain text: no metadata, title/author guessed from file name"], "txt")


def from_pdf(path):
    try:
        import pymupdf
    except ImportError:
        raise SystemExit("pdf needs: --with pymupdf")
    doc = pymupdf.open(str(path))
    pages = []
    for page in doc:
        t = page.get_text("text")
        lines = [ln for ln in t.split("\n") if not re.fullmatch(r"\s*\d{1,4}\s*", ln)]
        pages.append("\n".join(lines))
    raw = "\n".join(pages)
    raw = re.sub(r"-\n(?=[a-z])", "", raw)
    raw = re.sub(r"(?<![.!?:”\"’])\n(?=[a-z“‘\"])", " ", raw)
    warns = ["PDF LAST RESORT: layout text, running heads and hyphenation may survive; audit by hand"]
    meta = doc.metadata or {}
    res = list(from_plain(path, raw, warns, "pdf"))
    if meta.get("title"):
        res[0] = meta["title"]
    if meta.get("author"):
        res[1] = meta["author"]
    return tuple(res)


def fingerprint(text, n=64):
    words = re.findall(r"\w+", text.lower())
    sh = {" ".join(words[i:i + 8]) for i in range(0, max(len(words) - 8, 1), 3)}
    mins = []
    for seed in range(n):
        s = seed.to_bytes(2, "big")
        mins.append(min((int.from_bytes(hashlib.blake2b(s + x.encode(), digest_size=8).digest(), "big") for x in sh), default=0))
    return mins


def similarity(a, b):
    return sum(x == y for x, y in zip(a, b)) / max(len(a), 1)


def load_ledger(path):
    rows = []
    if path.exists():
        for ln in path.read_text().splitlines():
            if ln.strip():
                rows.append(json.loads(ln))
    return rows


STOP_EN = set("the and of to a in that it was he i his you with for as on had is but at not her she be they by this from have my which or all were one we so said an there what are me when been their no would if who out him them up into".split())
STOP_OTHER = {
    "es": set("de la que el en los del las por con una para como más pero sus le ya fue este ha sí porque esta son entre cuando muy sin sobre también se lo".split()),
    "it": set("di che il la non per un una del della con sono le gli si ma come anche alla nel questo ha era io mi ti lo è".split()),
    "pl": set("nie się że na jak to jest do za po ale tak już czy jego od mnie przez tylko był jej go mu co".split()),
    "fr": set("le la les de des et un une est que qui dans pour pas sur au avec il elle ce ne se je".split()),
    "de": set("der die das und ist nicht ein eine zu den mit sich des auf für ich er sie es dem".split()),
}
SCAN = re.compile(r"proofed|scann(ed|er'?s)|#bookz|this document is unfinished|needs formatting|scan notes|\bv\d\.\d\b|\bocr\b", re.I)
SCAN_STRONG = re.compile(r"#bookz|proofed (by|for)|scanned (by|for)|scan notes|scanner's (quick )?note|\bv\d\.\d+ proofed", re.I)
COPY = re.compile(r"copyright|all rights reserved|\bisbn\b|e-book to you|without (the )?(prior )?(written )?permission|\bDRM\b|piracy|electronic sharing", re.I)
NAMES = [
    ("ROADSIDE PICNIC", "Arkady Strugatsky", "Roadside Picnic"),
    ("M. John Harrison - Viriconium 2", "M. John Harrison", "A Storm of Wings"),
    ("Vernor Vinge_ True Names", "Vernor Vinge", "True Names"),
    ("Light_ M. John Harrison", "M. John Harrison", "Light"),
]
FIXES = {
    "simmons-fall-of-hyperion": {"lead_fragment": True, "end": r"^\* \* \*\n\nThe shattering saga",
                                 "warn": "the source epub lacks the novel's opening pages (it begins mid-sentence); kept from the first whole sentence"},
    "vinge-true-names": {"start": r"^In the once-upon-a-time days of the First Age of Magic", "end_after": r"were millennia\. And Ery\."},
    "strugatsky-roadside-picnic": {"start": r"^You have to make the good out of the bad"},
    "stephenson-diamond-age": {"start": r"^By nature, men are"},
    "sterling-schismatrix-plus": {"end": r"^A Shaper/Mechanist Chronology$"},
    "delany-dhalgren": {"end": r"^ABOUT THE AUTHOR"},
    "dick-ubik": {"start": r"^ONE$"},
    "tanigawa-melancholy-of-haruhi-suzumiya": {"end": r"^CHECK OUT A PREVIEW"},
    "schulz-fictions-of-bruno-schulz": {
        "sub": [(r"\s*\b\d{1,3}\s+(?:THE STREET OF CROCODILES|SANATORIUM UNDER THE SIGN OF THE HOURGLASS)(?:\s+[A-Z][A-Z' ,.-]*[A-Z])?\s+\d{1,3}\b\s*", " "),
                (r"(?m)^(?:THE STREET OF CROCODILES|SANATORIUM UNDER THE SIGN OF THE HOURGLASS)\s+(?=[a-z])", "")],
        "start": r"In July my father went"},
    "vance-eyes-of-the-overworld": {"start": r"^I\n\nThe Overworld!"},
    "carter-bloody-chamber-and-other": {"end": r"About The Author: Angela Carter was born"},
    "ballard-atrocity-exhibition": {"end": r"^AN INVESTIGATIVE SPIRIT$"},
    "calvino-invisible-cities": {"start": r"Kublai Khan does not necessarily"},
}


def language(text):
    letters = re.findall(r"[^\W\d_]", text[:400000])
    if letters and sum(1 for c in letters if "Ѐ" <= c <= "ӿ") / len(letters) > 0.3:
        return "ru"
    words = re.findall(r"[^\W\d_]+", text.lower())
    if len(words) > 60000:
        words = words[len(words) // 10: len(words) // 10 + 60000]
    if not words:
        return "und"
    en = sum(w in STOP_EN for w in words) / len(words)
    if en >= 0.2:
        return "en"
    best = max(STOP_OTHER, key=lambda k: sum(w in STOP_OTHER[k] for w in words))
    return best if sum(w in STOP_OTHER[best] for w in words) / len(words) > en else "und"


def sniff(path):
    ext = path.suffix.lower()
    with open(path, "rb") as f:
        head = f.read(65536)
    if head.startswith(b"Rar!"):
        what = "a RAR archive"
    elif head.startswith(b"\xd0\xcf\x11\xe0"):
        what = "a Word/OLE document"
    elif head.startswith(b"7z\xbc\xaf"):
        what = "a 7z archive"
    elif head.startswith(b"%PDF"):
        what = "a PDF"
    elif head.startswith(b"{\\rtf"):
        what = "RTF"
    elif re.match(rb"\s*(<\?xml[^>]*>\s*)?(<!doctype html|<html)", head, re.I):
        what = "HTML"
    elif head.startswith(b"PK"):
        what = "zip"
    elif head[60:68] in (b"BOOKMOBI", b"TEXtREAd"):
        what = "mobi"
    else:
        txt = head.decode("utf-8", "ignore")
        what = f"plain text in '{language(txt)}'" if txt.strip() else "binary data"
    if ext == ".epub":
        if what != "zip":
            return f"not a readable epub ({what})"
        try:
            with zipfile.ZipFile(path) as z:
                names = [n for n in z.namelist() if not n.endswith("/")]
        except zipfile.BadZipFile:
            return "not a readable epub (a damaged zip)"
        if not any(n.lower().endswith(".opf") for n in names):
            kinds = sorted({posixpath.splitext(n)[1].lower() or "no extension" for n in names})
            return f"not a readable epub (a zip of {', '.join(kinds[:5])} files with no OPF)"
    elif ext == ".txt" and what in ("RTF", "HTML"):
        return f"markup, not plain text ({what})"
    elif ext == ".pdf" and what != "a PDF":
        return f"not a readable pdf ({what})"
    elif ext in (".mobi", ".azw", ".azw3") and what != "mobi":
        return f"not a readable {ext[1:]} ({what})"
    return None


def file_names(src):
    for key, a, t in NAMES:
        if key in src:
            return a, t
    stem = re.sub(r"(\.(epub|txt|fb2|pdf|mobi))+$", "", src, flags=re.I)
    stem = re.sub(r"\[[^\]]*\]|\([^)]*\)|\bv\d+(\.\d+)?\b", " ", stem, flags=re.I)
    stem = WATERMARK.sub(" ", stem).replace("__", " ").strip(" _-")
    stem = re.sub(r"\s+", " ", re.sub(r"_(?! )", " ", stem))
    m = re.match(r"^([^,_-]+),\s*([^-_]+?)\s+-\s+(?:.+?\s+\d+(?:\.\d+)?\s+-\s+)?(.+)$", stem)
    if m:
        return f"{m.group(2).strip()} {m.group(1).strip()}", m.group(3).strip(" -")
    m = re.match(r"^(.+?)_\s+(.+)$", stem)
    if m and re.fullmatch(r"([A-Z][\w.'’]*\s?){2,4}", m.group(2).strip()):
        return m.group(2).strip(), m.group(1).strip()
    m = re.match(r"^(.+?)\s+-\s+(.+)$", stem)
    if m:
        return m.group(1).strip(), re.sub(r"^[-\s]+", "", m.group(2)).strip()
    return "", stem.strip()


def junk_meta(title, author):
    t, a = (title or "").strip(), (author or "").strip()
    if not a or a.lower() in ("unknown", "unknown author") or not t:
        return True
    if re.search(r"\s-\s|_|\.\w{3,4}$|\bv\d", t) or re.search(r"\d|\s-\s|\bv\d", a):
        return True
    at = set(re.findall(r"\w+", a.lower()))
    return bool(at) and at <= set(re.findall(r"\w+", t.lower())) | {"the", "a", "of"}


def surname_of(author):
    a = re.sub(r"\s*[\(\[].*?[\)\]]", "", author or "").strip()
    a = re.split(r"\s*(?:&|;| and )\s*", a)[0]
    if "," in a:
        return a.split(",")[0].strip()
    parts = [p for p in a.split() if not re.match(r"^(jr|sr|ii|iii|phd)\.?$", p, re.I)]
    if len(parts) >= 3 and parts[-2].lower() in ("le", "de", "van", "von", "der", "du", "la", "di"):
        return parts[-2] + " " + parts[-1]
    return parts[-1] if parts else "unknown"


def book_slug(title, author):
    t = clean_title(title)
    t = re.split(r"\s*[:;]\s+|\s+[-–—]\s+", t)[0]
    words = [w for w in ascii_slug(t).split("-") if w]
    if len(words) > 1 and words[0] in {"the", "a", "an"}:
        words = words[1:]
    return "-".join([ascii_slug(surname_of(author)) or "unknown"] + (words[:4] or ["untitled"]))


def polish(text, slug, title, author, src, warns):
    drops = []

    def drop(p, why):
        if p.strip():
            drops.append({"file": "text", "words": len(p.split()), "reason": why, "start": p.strip()[:60]})

    fx = FIXES.get(slug, {})
    if fx.get("warn"):
        warns.append(fx["warn"])
    for pat, rep in fx.get("sub", []):
        text, n = re.subn(pat, rep, text)
        if n:
            drops.append({"file": "text", "words": 0, "reason": f"per-book: {n} running heads cut out of paragraphs", "start": ""})
    if fx.get("start"):
        m = re.search(fx["start"], text, re.M)
        if m:
            drop(text[:m.start()], "per-book: everything before the work's first sentence")
            text = text[m.start():]
        else:
            warns.append("per-book start marker not found")
    for key in ("end", "end_after"):
        if fx.get(key):
            m = re.search(fx[key], text, re.M)
            if m:
                cut = m.start() if key == "end" else m.end()
                drop(text[cut:], "per-book: everything after the work's last sentence")
                text = text[:cut]
            else:
                warns.append(f"per-book {key} marker not found")
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    if fx.get("lead_fragment") and paras and re.match(r"^[a-z]", paras[0]):
        m = re.search(r"[.!?]\s+(?=[A-Z“\"])", paras[0])
        if m:
            drop(paras[0][:m.end()], "a fragment of a sentence whose start is missing from the source")
            paras[0] = paras[0][m.end():]
    cnt = Counter(p for p in paras if len(p.split()) <= 8 and not BREAK_TEXT.match(p))
    heads = {p for p, c in cnt.items() if c >= 6 and not CHAP_RE.match(p) and not re.search(r"[.!?…”\"’)\]]$", p)}
    if heads:
        for h in heads:
            drops.append({"file": "text", "words": len(h.split()) * cnt[h], "reason": f"running head x{cnt[h]}", "start": h[:60]})
        paras = [p for p in paras if p not in heads]
    open_end = sum(1 for a, b in zip(paras, paras[1:]) if not re.search(r"[.!?…:;”\"’)\]*—-]$", a) and re.match(r"^[a-z]", b))
    if paras and open_end / len(paras) > 0.1:
        joined = []
        for p in paras:
            if joined and re.match(r"^[a-z]", p) and not re.search(r"[.!?…”\"’)\]*—]$", joined[-1]):
                joined[-1] = joined[-1][:-1] + p if joined[-1].endswith("-") else joined[-1] + " " + p
            else:
                joined.append(p)
        drops.append({"file": "text", "words": 0, "reason": f"{len(paras) - len(joined)} paragraphs broken at line ends joined back", "start": ""})
        paras = joined
    keep = []
    for p in paras:
        if len(p.split()) < 40 and (SCAN_STRONG.search(p) or re.fullmatch(r"\W*(https?://|www\.)\S+\W*", p)):
            drop(p, "scanner/proofing note or url")
        else:
            keep.append(p)
    paras = keep
    toks = set(re.findall(r"[a-z]+", f"{title} {author} {src}".lower())) | {
        "of", "the", "a", "an", "and", "or", "by", "volume", "book", "new", "edition", "novel", "stories", "complete"}
    sur = surname_of(author)
    prev = None
    while paras:
        p = paras[0]
        w = re.findall(r"[a-z]+", p.lower())
        why = None
        if SCAN.search(p) and len(w) < 60:
            why = "scanner/proofing note"
        elif COPY.search(p) and len(w) < 150:
            why = "copyright/DRM notice"
        elif len(w) <= 14 and w and all(x in toks for x in w):
            why = "title/author line"
        elif len(w) <= 16 and re.match(r"^(\(?\d{4}\)?\s|(?i:translated|first published)|[Bb]y\s+[A-Z][\w.]*(\s+[A-Z][\w.]*){0,3}$)", p):
            why = "publication line"
        elif len(w) <= 14 and re.match(r"^(?i:to|for)\s+[A-Z]|^(?i:this book is dedicated|dedicated to)", p) and not re.search(r"[?!]", p):
            why = "dedication"
        elif len(w) <= 90 and p[:1] in "“\"" and len(paras) > 1 and re.match(r"^[—–-]\s*\S", paras[1]):
            why = "review blurb"
        elif prev == "review blurb" and re.match(r"^[—–-]\s*\S", p) and len(w) <= 14:
            why = "review blurb"
        elif prev == "dedication" and p.upper() == p and len(w) <= 6:
            why = "dedication"
        elif sur != "unknown" and len(w) < 200 and re.search(rf"\b{re.escape(sur)}\b.{{0,80}}\b(was born|is the author|lives in|died in)", p, re.I):
            why = "about the author"
        if not why:
            k = 0
            while k < len(paras) and re.fullmatch(r"(?i)(chapter|part|book)\s+[\w-]+", paras[k]):
                k += 1
            if k >= 3:
                drop("\n".join(paras[:k]), "opening: table of contents")
                del paras[:k]
                continue
            break
        drop(p, f"opening: {why}")
        paras.pop(0)
        prev = why
    blurb = False
    while paras:
        p = paras[-1]
        w = re.findall(r"\w+", p.lower())
        why = None
        if SCAN.search(p) and len(w) < 60:
            why = "scanner/proofing note"
        elif re.fullmatch(r"(the end|fin|notes?|(<\.?p>)+|\d{1,2}[/.]\d{1,2}[/.]\d{2,4}|[\W_]*)", p.strip(), re.I):
            why = "end marker, date or stray line"
        elif re.match(r"^(about the author|acknowledg|also by|books by|praise for|other books|by the same author)", p, re.I):
            why = "back matter"
        elif re.match(r"^[—–-]\s*\S", p) and len(w) <= 14:
            why, blurb = "review blurb", True
        elif re.search(r"(?i)now on sale|books are sold|loved this book|users also downloaded|creative commons|unported license|licensed under", p) and len(w) < 80:
            why, blurb = "distributor's note or advert", True
        elif blurb and len(w) <= 8 and not re.search(r"[.!?…”\"’]$", p):
            why = "advert/blurb block"
        elif blurb and (p[:1] in "“\"" or HYPE.search(p)) and len(w) < 90:
            why = "review blurb"
        elif re.fullmatch(r"([A-Z][\w.'’-]*\s?){2,3}", p) and len(paras) > 50:
            why = "name line after the text"
        elif re.match(r"^[“\"][^”\"]{1,60}[”\"],?\s", p) and len(w) <= 12:
            why = "list of other books"
        elif re.search(r"\s\d{1,4}$", p) and len(w) <= 10 and not CHAP_RE.match(p):
            why = "table of contents line"
        elif COPY.search(p) and len(w) < 120:
            why = "copyright notice"
        if not why:
            break
        drop(p, f"ending: {why}")
        paras.pop()
    return finish_text(paras), drops


def shingles(text):
    words = re.findall(r"\w+", text.lower())
    return {hash(" ".join(words[i:i + 8])) for i in range(0, max(len(words) - 8, 1))}


def skip_list(inbox):
    for d in (inbox, Path(__file__).resolve().parent.parent / "inbox"):
        f = d / "skip.txt"
        if f.exists():
            return [ln.strip() for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return []


def main():
    ap = argparse.ArgumentParser(description="ebooks in a folder -> clean body text")
    ap.add_argument("inbox", nargs="?", default=str(Path(__file__).resolve().parent.parent / "inbox"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    inbox = Path(a.inbox)
    out = Path(a.out) if a.out else inbox / "clean"
    out.mkdir(parents=True, exist_ok=True)
    ledger_path = out / "ledger.jsonl"
    ledger = load_ledger(ledger_path)
    done = {r["source"] for r in ledger}
    handlers = {".epub": from_epub, ".mobi": from_mobi, ".azw3": from_mobi, ".azw": from_mobi, ".txt": from_txt, ".pdf": from_pdf}
    files = sorted(p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() in handlers)
    if a.force:
        names = {p.name for p in files}
        ledger = [r for r in ledger if r["source"] not in names]
        done = {r["source"] for r in ledger}
    skips = skip_list(inbox)
    results = []
    for p in files:
        if p.name in done:
            continue
        fmt = p.suffix.lower()[1:]
        hit = next((k for k in skips if k in p.name), None)
        if hit:
            results.append({"source": p.name, "status": "skipped", "reason": "skipped: on the skip list", "format": fmt})
            continue
        bad = sniff(p)
        if bad:
            results.append({"source": p.name, "status": "skipped", "reason": f"skipped: {bad}", "format": fmt})
            continue
        try:
            title, author, lang, text, kept, dropped, warns = handlers[p.suffix.lower()](p)
        except Exception as e:
            results.append({"source": p.name, "status": "error", "error": f"{type(e).__name__}: {e}", "format": fmt})
            continue
        title = clean_title(title) or name_guess(p)[0]
        if fmt == "txt" or junk_meta(title, author):
            fa, ft = file_names(p.name)
            title, author = clean_title(ft) or title, fa or author
        else:
            for key, fa, ft in NAMES:
                if key in p.name:
                    title, author = ft, fa
        slug = book_slug(title, author)
        text, more = polish(text, slug, title, author, p.name, warns)
        lang = language(text)
        if lang != "en":
            results.append({"source": p.name, "status": "skipped", "reason": f"skipped: language {lang}", "format": fmt,
                            "title": title, "author": author})
            continue
        rec = {"source": p.name, "status": "ok", "slug": slug, "title": title, "author": author,
               "language": lang, "format": fmt, "words": len(text.replace("* * *", "").split()),
               "sections_kept": kept, "sections_dropped": dropped + more, "warnings": warns,
               "fingerprint": fingerprint(text), "_text": text, "_sh": shingles(text)}
        if rec["words"] < 5000:
            warns.append(f"only {rec['words']} words kept")
        results.append(rec)
    oks = sorted([r for r in results if r.get("status") == "ok"], key=lambda r: r["words"])
    for i, r in enumerate(oks):
        for o in oks[i + 1:]:
            if o.get("status") != "ok" or not r["_sh"]:
                continue
            if len(r["_sh"] & o["_sh"]) / len(r["_sh"]) >= 0.8:
                r["status"] = "duplicate"
                r["duplicate_of"] = o["source"]
                r["reason"] = f"duplicate: contained in {o['slug']}"
                break
    pool = [r for r in ledger if r.get("status") == "ok"] + [r for r in results if r.get("status") == "ok"]
    for r in results:
        if r.get("status") != "ok":
            continue
        for o in pool:
            if o is r or o.get("status") != "ok":
                continue
            same_meta = ascii_slug(o["title"]) == ascii_slug(r["title"]) and ascii_slug(author_surname(o["author"])) == ascii_slug(author_surname(r["author"]))
            near = similarity(o.get("fingerprint", []), r["fingerprint"]) >= 0.7
            if same_meta or near:
                loser = r if r["words"] <= o["words"] else o
                winner = o if loser is r else r
                if loser.get("status") == "ok":
                    loser["status"] = "duplicate"
                    loser["duplicate_of"] = winner["source"]
                    loser["reason"] = f"duplicate: {'same title and author as' if same_meta else 'near-identical to'} {winner.get('slug')}"
                    if loser in ledger:
                        old = out / f"{loser['slug']}.txt"
                        if old.exists() and loser["slug"] != winner["slug"]:
                            (out / ".duplicates").mkdir(exist_ok=True)
                            old.rename(out / ".duplicates" / old.name)
    taken = {r["slug"]: r["source"] for r in ledger if r.get("status") == "ok"}
    for r in results:
        if r.get("status") != "ok":
            continue
        slug = r["slug"]
        k = 2
        while slug in taken and taken[slug] != r["source"]:
            slug = f"{r['slug']}-{k}"
            k += 1
        r["slug"] = slug
        taken[slug] = r["source"]
        (out / f"{slug}.txt").write_text(r["_text"], encoding="utf-8")
    final = ledger + results
    with ledger_path.open("w", encoding="utf-8") as f:
        for r in final:
            f.write(json.dumps({k: v for k, v in r.items() if k not in ("_text", "_sh")}, ensure_ascii=False) + "\n")
    for r in results:
        if r.get("status") == "error":
            print(f"ERROR  {r['source']}: {r['error']}")
            continue
        if r["status"] == "skipped":
            print(f"SKIP {r['source'][:60]:60} {r['reason']}")
            continue
        flag = "DUP  " if r["status"] == "duplicate" else "ok   "
        print(f"{flag}{r['slug']:40} {r['words']:7}w {r.get('reason', '')}  kept {len(r['sections_kept']):3}  dropped {len(r['sections_dropped']):3}  warnings {len(r['warnings'])}")
    if not results:
        print("nothing new (use --force to redo)")


if __name__ == "__main__":
    main()
