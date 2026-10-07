import re
import unicodedata

import ftfy
from bs4 import BeautifulSoup, Comment, NavigableString, Tag

HR = "\x00HR"
BREAK = "* * *"
LINK = "\x01"
DROP_TAGS = {"script", "style", "object", "embed", "iframe", "audio", "video", "img", "figure", "figcaption",
             "noscript", "button", "form", "input", "svg", "source", "param", "map", "area", "select", "applet",
             "head", "title", "meta", "link"}
BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "blockquote", "pre", "center",
              "table", "tr", "td", "th", "section", "article", "dl", "dt", "dd", "address", "body", "html", "tbody"}
BREAKISH = re.compile(r"^[\s*#~§•·⁂◊○●×xX+=_\-–—.:|/\\<>]{1,30}$")
URL = re.compile(r"https?://\S+|www\.\S+")
END = re.compile(r"^[\W_]*(the end|end|fin|finis)[\W_]*$", re.I)
CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f�​﻿]")
C1 = {0x80: "€", 0x82: "‚", 0x83: "ƒ", 0x84: "„", 0x85: "…", 0x86: "†", 0x87: "‡",
      0x88: "ˆ", 0x89: "‰", 0x8a: "Š", 0x8b: "‹", 0x8c: "Œ", 0x8e: "Ž", 0x91: "‘",
      0x92: "’", 0x93: "“", 0x94: "”", 0x95: "•", 0x96: "–", 0x97: "—", 0x98: "˜",
      0x99: "™", 0x9a: "š", 0x9b: "›", 0x9c: "œ", 0x9e: "ž", 0x9f: "Ÿ"}


def decode(b):
    m = re.search(rb"charset\s*=\s*[\"']?([A-Za-z0-9_-]+)", b[:4000])
    declared = m.group(1).decode("ascii", "replace").lower() if m else ""
    if b[:3] == b"\xef\xbb\xbf":
        return b[3:].decode("utf-8", "replace")
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        pass
    if declared in ("utf-8", "utf8"):
        bad = len(re.findall(rb"[\x80-\xff]", b)) - 2 * len(re.findall(rb"[\xc2-\xef][\x80-\xbf]", b))
        if bad < 20:
            return b.decode("utf-8", "replace")
    if declared in ("x-mac-roman", "macintosh", "mac"):
        return b.decode("mac_roman", "replace")
    return b.decode("cp1252", "replace")


def fix(s):
    s = s.translate(C1)
    s = ftfy.fix_text(s, uncurl_quotes=False, fix_latin_ligatures=False, fix_character_width=False, normalization="NFC")
    s = CTRL.sub("", s)
    return s


def norm_ws(s):
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def soup_of(htmltext):
    return BeautifulSoup(htmltext, "lxml")


def paragraphs(node, drop_class=None, drop=None):
    if isinstance(node, str):
        node = soup_of(node)
        node = node.body or node
    for t in node.find_all(DROP_TAGS):
        t.decompose()
    if drop_class is not None:
        for t in node.find_all(class_=drop_class):
            t.decompose()
    if drop is not None:
        for t in list(node.find_all(drop)):
            t.decompose()
    for c in node.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    out = []
    buf = []

    def end_line():
        line = norm_ws("".join(buf))
        buf.clear()
        if line:
            out.append(line)

    def walk(n):
        for ch in list(n.children):
            if isinstance(ch, NavigableString):
                buf.append(str(ch))
            elif isinstance(ch, Tag):
                name = ch.name
                if name == "br":
                    end_line()
                elif name == "hr":
                    end_line()
                    out.append(HR)
                elif name in BLOCK_TAGS:
                    end_line()
                    walk(ch)
                    end_line()
                else:
                    walk(ch)

    walk(node)
    end_line()
    res = []
    for p in out:
        if p == HR or BREAKISH.match(p):
            if res and res[-1] != BREAK:
                res.append(BREAK)
            continue
        p = fix(URL.sub(LINK, p))
        p = re.sub(r"[ \t]+", " ", p).strip()
        if p:
            res.append(p)
    return res


def trim(paras):
    while paras and (paras[-1] == BREAK or END.match(paras[-1])):
        paras.pop()
    while paras and paras[0] == BREAK:
        paras.pop(0)
    return paras


def join(paras):
    res = []
    for p in paras:
        if p == BREAK and (not res or res[-1] == BREAK):
            continue
        res.append(p)
    res = [re.sub(r"[ \t]+", " ", p.replace(LINK, "")).strip() for p in trim(res)]
    return "\n\n".join(p for p in res if p) + "\n"


def slug(s, n=80):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:n].strip("-") or "untitled"


def key(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


STOP = set("the of and to a in is was that it he she i you his her for on with as but not at my me we they".split())


def english(text):
    w = re.findall(r"[a-zA-Z’']+", text.lower())
    if len(w) < 150:
        return True
    return sum(1 for x in w if x in STOP) / len(w) >= 0.06
