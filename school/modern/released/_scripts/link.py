import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
from bs4 import BeautifulSoup
from _common import write_ledger, row, fetch_raw, norm_paras, write_text

AUTH = "Kelly Link"
SBP = ("smallbeerpress.com/robots.txt disallows / for CCBot and GPTBot (AI-training crawlers); "
       "fetching from smallbeerpress.com and lcrw.net was ruled out")
WHY_STH = ("declined:kellylink.net does not serve the CC release itself (its creative-commons page says the book is a free download but hosts no file; "
           "the download is the publisher's); the CC text is served only by Small Beer Press, and " + SBP + "; "
           "a copy fetched before that ruling was moved to the Trash")
WHY_MFB = ("declined:no longer released; kellylink.net/books/stranger-things-happen-old/creative-commons says "
           "'Magic for Beginners was taken down when the rights were resold'")

HAT = "https://kellylink.net/specialists-hat"


def hat():
    raw = fetch_raw("link", HAT, "specialists-hat.html", delay=360)
    soup = BeautifulSoup(raw.decode("utf-8", "replace"), "lxml")
    m = soup.find(class_="entry_content") or soup.find("article")
    for t in m.find_all("br"):
        t.replace_with(" ")
    paras = []
    for b in m.find_all(["p", "h1", "h2", "h3", "h4", "blockquote"]):
        if b.find(["p", "blockquote"]):
            continue
        t = " ".join(b.get_text("").split())
        if not t or t == "The Specialist\u2019s Hat" or t.startswith("Copyright \u00a9"):
            continue
        paras.append(t)
    return norm_paras(paras)


text = hat()
write_ledger("link", [
    row(HAT, "the-specialists-hat", "The Specialist\u2019s Hat", AUTH, 1998, "story", text,
        write_text("link", "the-specialists-hat", text),
        "served free in full by the author on her own site, listed at https://kellylink.net/read-me "
        "(story also part of the CC BY-NC-SA 2.5 release of Stranger Things Happen)", "ok"),
    row("https://kellylink.net/books/stranger-things-happen-old", "stranger-things-happen", "Stranger Things Happen",
        AUTH, 2001, "collection", "", "", "CC BY-NC-SA 2.5 (publisher's release, 2005)", WHY_STH),
    row("https://kellylink.net/books/magic-for-beginners-old", "magic-for-beginners", "Magic for Beginners",
        AUTH, 2005, "collection", "", "", "", WHY_MFB),
])
