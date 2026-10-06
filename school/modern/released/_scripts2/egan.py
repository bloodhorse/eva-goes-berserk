import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Shelf

sh = Shelf("egan")
sh.log(url="https://www.gregegan.net/", slug="gregegan-net", title="Greg Egan's online fiction (whole site)", author="Greg Egan", year=None, kind="collection",
       licence_or_basis="free full text on author's site, all rights reserved",
       status="declined:robots.txt disallows CCBot, GPTBot, Google-Extended, ChatGPT-User, Omgilibot site-wide; the author's stated wish is no LM-training crawl, so our UA does not get to slip past it")
