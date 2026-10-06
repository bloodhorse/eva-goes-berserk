import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import write_ledger, row, ROOT

WHY = ("declined:antipope.org/robots.txt disallows / for anthropic-ai, ClaudeBot, Claude-Web, GPTBot, CCBot, "
       "Google-Extended, cohere-ai, PerplexityBot and other AI-training crawlers; our UA is not named, "
       "but the site owner's intent excludes collection for model training, so nothing was fetched")

os.makedirs(os.path.join(ROOT, "stross"), exist_ok=True)
write_ledger("stross", [
    row("https://www.antipope.org/charlie/blog-static/fiction/accelerando/accelerando.html", "accelerando",
        "Accelerando", "Charles Stross", 2005, "novel", "", "", "CC BY-NC-ND 2.5 (per the book's own release)", WHY),
    row("https://www.antipope.org/charlie/blog-static/fiction/", "", "other fiction on antipope.org (not enumerated)",
        "Charles Stross", None, "story", "", "", "", WHY),
])
