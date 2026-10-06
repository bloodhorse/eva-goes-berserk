import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Shelf, get, join, norm
from bs4 import BeautifulSoup

URL = "http://localroger.com/prime-intellect/mopiall.html"
sh = Shelf("williams")


def main():
    html = get(URL)
    sh.raw_html("mopiall", html)
    h = re.sub(r"(?is)<pre>(.*?)</pre>", lambda m: "¶" + m.group(1).replace("\n", " ") + "¶", html)
    h = re.sub(r"(?i)<img[^>]*1pix\.gif[^>]*>", "¶", h)
    h = re.sub(r"(?i)<(p|br|h\d|/h\d|tr|/table)\b[^>]*>", "¶", h)
    text = BeautifulSoup(h, "lxml").get_text()
    out, started = [], False
    for chunk in text.split("¶"):
        t = norm(chunk)
        if not t:
            continue
        if t.startswith("* Chapter"):
            started = True
            t = t.lstrip("* ").strip()
        if not started:
            continue
        if re.fullmatch(r"\*\s*END", t):
            break
        if re.fullmatch(r"[*\s]+", t):
            continue
        out.append(t)
    sh.write("metamorphosis-of-prime-intellect", join(out), url=URL, title="The Metamorphosis of Prime Intellect",
             author="Roger Williams", year=1994, kind="novel",
             licence_or_basis="served free in full by the author on his own site (all rights reserved; private use only): http://localroger.com/prime-intellect/mopilegl.html")
    sh.beat()


if __name__ == "__main__":
    main()
