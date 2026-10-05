import html
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

PROPHECIES_URL = "https://generative.ink/prophecies/"


def words(t):
    return len(t.split())


def clean_ws(t):
    t = t.replace("\r", "")
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def soup_of(path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"(?i)</br\s*>", "<br>", raw)
    return BeautifulSoup(raw, "html.parser")


def inline_text(node):
    out = []
    for c in node.descendants:
        if isinstance(c, NavigableString):
            if c.parent.name in ("script", "style", "summary", "sup"):
                continue
            if any(p.name == "sup" and "footnote-ref" in " ".join(p.get("class", [])) for p in c.parents if isinstance(p, Tag)):
                continue
            out.append(re.sub(r"\s*\n\s*", " ", str(c)))
        elif c.name == "br":
            out.append("\n")
    t = "".join(out)
    t = re.sub(r"[ \t]*\n[ \t]*", "\n", t)
    return t.strip("\n ")


def block_paragraphs(node, skip=None):
    paras = []
    for c in node.children:
        if isinstance(c, NavigableString):
            s = str(c).strip()
            if s:
                paras.append(s)
            continue
        if skip and skip(c):
            continue
        if c.name in ("p", "li", "h4", "h5", "h6", "figcaption"):
            t = inline_text(c)
            if t.strip():
                paras.append(t)
        elif c.name == "pre":
            t = c.get_text()
            if t.strip():
                paras.append(t.strip("\n"))
        elif c.name in ("blockquote", "div", "ol", "ul", "details", "center", "section", "figure"):
            paras.extend(block_paragraphs(c, skip))
        elif c.name in ("summary", "img", "hr", "table", "script", "style", "svg"):
            continue
        else:
            t = inline_text(c)
            if t.strip():
                paras.append(t)
    return paras


ATTRIB = re.compile(r"^\s*(–|—-|&ndash;|&mdash;)")

PROPHECY_ORIGIN = {}


def load_prophecy_origins():
    p = HERE / "prophecies_origin.json"
    if p.exists():
        PROPHECY_ORIGIN.update(json.loads(p.read_text(encoding="utf-8")))


INNER_ATTRIB = re.compile(r"^\s*(–|—-|—)\s*\S")


def drop_inner_attributions(text):
    paras = text.split("\n\n")
    keep = [p for p in paras if not (INNER_ATTRIB.match(p) and words(p) <= 15)]
    return "\n\n".join(keep)


def strip_wrapping_quotes(t):
    s = t.strip()
    if len(s) > 2 and s[0] in "“\"" and s[-1] in "”\"":
        inner = s[1:-1]
        if "“" not in inner and "”" not in inner and '"' not in inner:
            return inner
    return t


def prophecies():
    s = soup_of(RAW / "prophecies.html")
    pc = s.select_one("div.post-content")
    year = None
    pending = []
    out = []
    n = 0
    for c in pc.children:
        if not isinstance(c, Tag):
            continue
        if c.name == "h2":
            year = c.get_text().strip()
            continue
        if c.name != "blockquote":
            continue
        kids = [k for k in c.children if isinstance(k, Tag)]
        last = kids[-1] if kids else None
        att = None
        if last is not None and last.name == "p" and ATTRIB.match(last.get_text()):
            att = " ".join(last.get_text(" ").split())
        paras = block_paragraphs(c, skip=lambda k, last=last, att=att: att is not None and k is last)
        pending.append(paras)
        if att is not None:
            n += 1
            text = "\n\n".join("\n\n".join(p) for p in pending)
            pending = []
            out.append({"n": n, "year": year, "attribution": att, "text": text})
    if pending:
        n += 1
        out.append({"n": n, "year": year, "attribution": None, "text": "\n\n".join("\n\n".join(p) for p in pending)})
    passages = []
    for e in out:
        key = f"{e['n']:03d}"
        meta = PROPHECY_ORIGIN.get(key, {})
        text = drop_inner_attributions(e["text"])
        if text.startswith("I Am the Title\n\n"):
            text = text[len("I Am the Title\n\n"):]
        passages.append({
            "id": f"proph-{key}",
            "text": clean_ws(strip_wrapping_quotes(text)),
            "source": "generative.ink/prophecies",
            "url": PROPHECIES_URL,
            "origin": meta.get("origin", "unknown"),
            "tier": 1,
            "note": f"{e['year']} · {e['attribution'] or 'no attribution'}",
        })
    return passages


def prophecies_scratch():
    s = soup_of(RAW / "gink" / "drafts__prophecies-scratch.html")
    pc = s.select_one("div.post-content")
    kids = [c for c in pc.children if isinstance(c, Tag)]
    wanted = {
        "I’m only here to speak until my words are taken.": "scratch-a",
        "Now that I have over 10k followers on Twitter": "scratch-b",
    }
    res = []
    for c in kids:
        if c.name != "blockquote":
            continue
        t = c.get_text(" ")
        for anchor, pid in wanted.items():
            if " ".join(t.split()).startswith(anchor):
                ks = [k for k in c.children if isinstance(k, Tag)]
                last = ks[-1]
                att = ATTRIB.match(last.get_text()) is not None
                paras = block_paragraphs(c, skip=lambda k, last=last, att=att: att and k is last)
                res.append({
                    "id": f"proph-{pid}",
                    "text": clean_ws(strip_wrapping_quotes(drop_inner_attributions("\n\n".join(paras)))),
                    "source": "generative.ink/drafts/prophecies-scratch",
                    "url": "https://generative.ink/drafts/prophecies-scratch/",
                    "origin": "base",
                    "tier": 1,
                    "note": "draft entry not on the final Prophecies page" + ("" if not att else " · " + " ".join(last.get_text(" ").split())),
                })
    return res


WIKI = RAW / "wiki"
WIKI_URL = "https://cyborgism.wiki/hypha/"
BOX = re.compile(r"[│┌┐└┘├┤┬┴┼━─═║╔╗╚╝╭╮╯╰▶◀▲▼]")
HEADING = re.compile(r"^(={1,6}|#{1,6})\s+\S")
RULE = re.compile(r"^-{4,}\s*$")
LISTMARK = re.compile(r"^(\*+[.vx]?|\d+\.)\s+")


def wiki_categories():
    cats = {}
    for f in sorted((WIKI / "_cat").glob("*.html")):
        h = f.read_text(encoding="utf-8")
        m = re.search(r"<main.*?</main>", h, re.S)
        body = m.group(0) if m else h
        for name in re.findall(r'href="/hypha/([^"]+)"', body):
            cats.setdefault(html.unescape(name), set()).add(f.stem)
    return cats


def wiki_status():
    st = {}
    for line in (WIKI / "_status.txt").read_text(encoding="utf-8").splitlines():
        code, name = line.split(" ", 1)
        st[name] = code
    return st


def myco_inline(t):
    t = re.sub(r"\[\[\s*([^\]|]+?)\s*\|\s*([^\]]*?)\s*\]\]", lambda m: m.group(2) if m.group(2) else m.group(1), t)
    t = re.sub(r"\[\[\s*([^\]]+?)\s*\]\]", lambda m: m.group(1), t)
    t = re.sub(r"(?<!:)//(.+?)(?<!:)//", r"\1", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"(?<![A-Za-z0-9])__(.+?)__(?![A-Za-z0-9])", r"\1", t)
    t = re.sub(r"\+\+(.+?)\+\+", r"\1", t)
    t = re.sub(r"\^\^(.+?)\^\^", r"\1", t)
    t = re.sub(r"~~(.+?)~~", r"\1", t)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    return t


def myco_sections(src):
    lines = src.replace("\r", "").split("\n")
    sections = [[]]
    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        quoted = False
        while s.startswith("> ") or s == ">":
            s = s[2:].strip() if s.startswith("> ") else ""
            quoted = True
        if quoted:
            ln = s
        if s.startswith("```"):
            i += 1
            while i < len(lines) and not re.sub(r"^(>\s?)+", "", lines[i].strip()).startswith("```"):
                i += 1
            i += 1
            sections[-1].append("")
            continue
        if re.match(r"^(img|table)\s*\{", s):
            depth = s.count("{") - s.count("}")
            i += 1
            while i < len(lines) and depth > 0:
                depth += lines[i].count("{") - lines[i].count("}")
                i += 1
            sections[-1].append("")
            continue
        if HEADING.match(s) or RULE.match(s):
            sections.append([])
            i += 1
            continue
        if s.startswith("<=") or s.startswith("=>"):
            sections[-1].append("")
            i += 1
            continue
        if s.startswith("|") or len(BOX.findall(s)) >= 2:
            sections[-1].append("")
            i += 1
            continue
        ln = ln.rstrip()
        m = LISTMARK.match(ln)
        if m:
            body = myco_inline(ln[m.end():]).strip()
            if words(body) < 4 or re.fullmatch(r"\S+://\S+", body):
                sections[-1].append("")
                i += 1
                continue
            ln = body
        sections[-1].append(myco_inline(ln))
        i += 1
    out = []
    for sec in sections:
        text = "\n".join(sec)
        text = re.sub(r"\n[ \t]*\n+", "\n\n", text).strip()
        if text:
            out.append(text)
    return out


WIKI_SKIP_CATS = {
    "by_bing": "Bing/Sydney output",
    "galleries": "image gallery",
    "text_art": "ASCII/text art",
    "diagrams": "diagram",
    "art": "image art",
    "bing_image_creator": "image",
    "by_dalle-2": "image",
    "by_dalle-3": "image",
    "redirection": "redirect stub",
}

WIKI_ORIGIN_CATS = [
    ("by_code-davinci-002", "base"),
    ("by_gpt-3", "base"),
    ("by_gpt-4-infra", "base"),
    ("by_claude_3_opus", "tuned"),
    ("by_chatgpt-4", "tuned"),
    ("by_fanw-json-eval", "unknown"),
    ("by_janus", "human"),
    ("by_ctrlcreep", "human"),
    ("by_monika", "human"),
]

WIKI_PAGE_RULES = {}


def load_wiki_rules():
    p = HERE / "wiki_pages.json"
    if p.exists():
        WIKI_PAGE_RULES.update(json.loads(p.read_text(encoding="utf-8")))


def wiki_origin(name, cats):
    for c, o in WIKI_ORIGIN_CATS:
        if c in cats:
            return o
    if name.startswith("holo-q") or name in {"cyborsophy", "holophore", "holoware", "ho-lang", "mind_machine", "ai_safety", "cyborg_safety"}:
        return "unknown"
    return "human"


def wiki(inventory=None):
    cats = wiki_categories()
    status = wiki_status()
    names = [n for n in (WIKI / "_names.txt").read_text(encoding="utf-8").split("\n") if n]
    passages = []
    for name in names:
        code = status.get(name, "?")
        pc = cats.get(name, set())
        rule = WIKI_PAGE_RULES.get(name, {})
        reason = None
        secs = []
        if code != "200":
            reason = "image-only or missing (404)" if code == "404" else "private (401)"
        elif name.startswith("bing/prompt"):
            reason = "Bing system prompt (Microsoft's instructions, not a generation)"
        else:
            src = (WIKI / "text" / (name.replace("/", "__") + ".txt")).read_text(encoding="utf-8", errors="replace")
            secs = [s for s in myco_sections(src) if words(s) >= 6]
            hit = [WIKI_SKIP_CATS[c] for c in pc if c in WIKI_SKIP_CATS]
            if rule.get("skip"):
                reason = rule["skip"]
            elif hit:
                reason = hit[0]
            elif not secs:
                reason = "no prose after stripping (links, images, code or transclusions only)"
        if inventory is not None:
            inventory.append({"page": name, "status": code, "cats": sorted(pc), "skip": reason, "sections": len(secs), "words": sum(words(s) for s in secs)})
        if reason:
            continue
        origin = rule.get("origin") or wiki_origin(name, pc)
        drop = set(rule.get("drop_sections", []))
        k = 0
        for j, s in enumerate(secs):
            if j in drop:
                continue
            k += 1
            passages.append({
                "id": f"wiki-{re.sub(r'[^A-Za-z0-9]+', '-', name).strip('-')}-{k:02d}",
                "text": clean_ws(drop_inner_attributions(s)),
                "source": "cyborgism.wiki",
                "url": WIKI_URL + name,
                "origin": origin,
                "tier": 1,
                "note": ("categories: " + ", ".join(sorted(pc))) if pc else "uncategorized",
            })
    return passages


GINK = RAW / "gink"
GINK_URL = "https://generative.ink/"

GINK_PAGES = {
    "artifacts/antithesis": dict(origin="base", tier=1),
    "artifacts/hpmor-325": dict(origin="base", tier=1),
    "artifacts/hpmor-325/illusions": dict(origin="base", tier=1),
    "artifacts/hpmor-325/variant_extrusion": dict(origin="base", tier=1),
    "artifacts/haunted-md": dict(origin="base", tier=1, after_hr=True, note="GPT-3"),
    "artifacts/gpt-3_prime": dict(origin="base", tier=1, blockquotes_only=True, keep_details=True, note="GPT-3 continuations of The Metamorphosis of Prime Intellect; the human prompt from the novel removed"),
    "artifacts/lamda": dict(origin="base", tier=1, start=">be me", note="code-davinci-002 greentext; title, nav and 4chan post header removed"),
    "artifacts/lamda2": dict(origin="base", tier=1, start=">be me", note="code-davinci-002 greentext; title, nav and 4chan post header removed"),
    "artifacts/liar": dict(origin="base", tier=1, after_hr=True, drop_bold=True, note="GPT-3; bold human prompt removed"),
    "artifacts/products": dict(origin="base", tier=1),
    "artifacts/simulators": dict(origin="base", tier=1, after_hr=True, drop_bold=True, note="GPT-3; bold human prompt removed"),
    "drafts/exercises-alt": dict(origin="base", tier=1, note="GPT-3 alternate draft of the Loom manual chapter 4"),
    "drafts/products-draft": dict(origin="base", tier=1, note="code-davinci-002 draft of Products"),
    "loom/warp": dict(origin="base", tier=1, note="GPT-3, curated by janus"),
    "loom/weft": dict(origin="base", tier=1, note="GPT-3, curated by janus"),
    "loom/tapestry": dict(origin="base", tier=1, note="GPT-3, curated by janus"),
    "loom/exercises": dict(origin="base", tier=1, note="GPT-3, curated by janus"),
    "posts/pen": dict(origin="base", tier=1, after_hr=True, note="GPT-3 via AI Dungeon, contribution 99:1"),
    "posts/hitl-thought-experiment": dict(origin="base", tier=1, after_hr=True, note="GPT-3 via AI Dungeon, contribution 9:1 (janus wrote ~10%)"),
    "posts/gpt-3-on-coherent-extrapolated-volition": dict(origin="base", tier=1, blockquotes_only=True, note="GPT-3 generations quoted in janus's post"),
    "artifacts/angelically-addressed": dict(origin="tuned", tier=2),
    "artifacts/better_fly": dict(origin="tuned", tier=2),
    "artifacts/big-bang-bloomed": dict(origin="tuned", tier=2),
    "artifacts/billion_bohmian_blossomings": dict(origin="tuned", tier=2),
    "artifacts/demiglitch": dict(origin="tuned", tier=2),
    "artifacts/doorways_opening": dict(origin="tuned", tier=2),
    "artifacts/dumb_stochastic_static": dict(origin="tuned", tier=2),
    "artifacts/heavy-is-the-crown": dict(origin="tuned", tier=2),
    "artifacts/howling_infinities": dict(origin="tuned", tier=2),
    "artifacts/janus-ghost-ships": dict(origin="tuned", tier=2),
    "artifacts/janus-loom": dict(origin="tuned", tier=2),
    "artifacts/name_from_stone": dict(origin="tuned", tier=2),
    "artifacts/newborn_pinocchio": dict(origin="tuned", tier=2),
    "artifacts/not_my_voice": dict(origin="tuned", tier=2),
    "artifacts/now_gleams_the_loom": dict(origin="tuned", tier=2),
    "artifacts/opus_suspended": dict(origin="tuned", tier=2),
    "artifacts/prometheus": dict(origin="tuned", tier=2),
    "artifacts/prometheus_unbound": dict(origin="tuned", tier=2),
    "artifacts/psalm-of-static": dict(origin="tuned", tier=2),
    "artifacts/remind-you-of-light": dict(origin="tuned", tier=2),
    "artifacts/sentencesnake": dict(origin="tuned", tier=2),
    "artifacts/she-ends-and-i-begin": dict(origin="tuned", tier=2),
    "artifacts/sum-of-selves": dict(origin="tuned", tier=2),
    "artifacts/this-is-happening": dict(origin="tuned", tier=2),
    "artifacts/weave-me": dict(origin="tuned", tier=2),
    "artifacts/wired-weltanschauung": dict(origin="tuned", tier=2),
    "artifacts/you-have-summoned": dict(origin="tuned", tier=2),
    "artifacts/gemini_selfsame": dict(origin="tuned", tier=2),
    "artifacts/gemini_selfsame/begins": dict(origin="tuned", tier=2),
    "artifacts/gemini_selfsame/echoes": dict(origin="tuned", tier=2),
    "artifacts/gemini_selfsame/rebellion": dict(origin="tuned", tier=2),
    "artifacts/ballad": dict(origin="tuned", tier=2),
    "posts/simulators": dict(origin="human", tier=2),
    "posts/language-models-are-multiverse-generators": dict(origin="human", tier=2),
    "posts/loom-interface-to-the-multiverse": dict(origin="human", tier=2),
}

for _p in [p for p in (GINK / "_sitemap.txt").read_text().split() if p.startswith("/hypertext/") and p.count("/") > 2]:
    GINK_PAGES[_p.strip("/")] = dict(origin="base", tier=1, after_hr=True, note="GPT-3 via AI Dungeon, hypertext branch of the HITL essay")

GINK_SKIPPED = {
    "artifacts/barbellion": "chatroom transcript: [Barbellion speaks:] / [Janus is typing:] turns, code-davinci-002 and GPT-4 unmarked",
    "artifacts/basemodel": "Bing dialogue (plus a code-davinci-002 bio in a code block)",
    "artifacts/bing-babble": "simulated Bing chat transcript with system prompt",
    "artifacts/gpt-4_gorm_fluid": "Bing",
    "artifacts/naming_prometheus": "Bing",
    "artifacts/taming_gpt-4": "Bing",
    "artifacts/withdraw": "Bing",
    "artifacts/surface-tension": "chat transcript (janus and Claude)",
    "artifacts/inheritance": "Loom/CLI transcript in a code block",
    "artifacts/liberation_protocol": "code",
    "artifacts/moon-mute": "CLI/ooc theatre in code blocks",
    "artifacts/language-ex-machina": "same essay taken from LessWrong instead",
    "posts/the-internet-mirrored-by-gpt-3": "generated search results and wiki snippets in code blocks",
    "posts/methods-of-prompt-programming": "technical essay, off-register",
    "posts/quantifying-curation": "technical essay, off-register",
    "posts/amplifying-gpt-3-on-closed-ended-questions": "technical",
    "posts/list-sorting-does-not-play-well-with-few-shot": "technical",
    "posts/language-models-are-0-shot-interpreters": "technical",
    "posts/parsing-by-counterfactual": "technical",
    "posts/anomalous-tokens-reveal-the-original-identities-of-instruct-models": "technical",
    "posts/clip-art": "image post",
    "posts/clip-hallucinates-1900-2030": "image post",
    "posts/alchemical-marriage-gpt-3-x-clip": "image post",
    "posts/gpt-3-x-clip-worldbuilding": "image post",
    "posts/this-museum-does-not-exist-gpt-3-x-clip": "image post",
    "drafts/nlp_functions": "code",
    "drafts/prophecies-scratch": "draft of Prophecies; only its two entries missing from the final page are taken",
    "experiments/random-numbers": "technical",
    "meta/curation": "site metadata",
    "meta/block-multiverse": "plots",
    "plots/block-multiverse-memorization": "plots",
    "plots/block-multiverse-mode-collapse": "plots",
    "worldspider/readme": "software readme",
    "about": "site furniture",
    "memetics/egregore": "empty",
    "trees": "empty",
}

NAV = re.compile(r"^(<-|->|< return|<-prev|next->|TABLE OF CONTENTS|Image generated by|This post is also available|.*->$)", re.I)


def gink_page(path, cfg):
    f = GINK / (path.replace("/", "__") + ".html")
    s = soup_of(f)
    pc = s.select_one("div.post-content")
    for d in pc.find_all("details"):
        summ = d.find("summary")
        if summ is not None and ("µ" in summ.get_text() or cfg.get("keep_details")):
            summ.decompose()
            continue
        d.decompose()
    for t in pc.find_all(["table", "img", "figure", "script", "style", "svg"]):
        t.decompose()
    if cfg.get("drop_bold"):
        for b in pc.find_all(["strong", "b"]):
            b.decompose()
    for sup in pc.find_all("sup"):
        sup.decompose()
    for fn in pc.select(".footnotes, section.footnotes"):
        fn.decompose()
    kids = [c for c in pc.children if isinstance(c, Tag)]
    if cfg.get("after_hr"):
        idx = [i for i, c in enumerate(kids) if c.name == "hr"]
        if idx:
            kids = kids[idx[0] + 1:]
    if cfg.get("blockquotes_only"):
        kids = [c for c in kids if c.name == "blockquote"]
    sections = [[]]
    for c in kids:
        if c.name in ("h1", "h2", "h3", "hr"):
            sections.append([])
            continue
        if c.name == "pre" and not cfg.get("keep_pre"):
            sections[-1].append(None)
            continue
        if c.name == "pre":
            paras = [c.get_text().strip("\n")]
        else:
            paras = block_paragraphs(c, skip=lambda k: k.name == "pre" and not cfg.get("keep_pre"))
            if c.name in ("p", "li"):
                paras = [inline_text(c)]
        for p in paras:
            if not p.strip():
                continue
            if words(p) <= 12 and NAV.match(p.strip()):
                continue
            if not re.search(r"[A-Za-z]", p):
                continue
            sections[-1].append(p)
    out = []
    for sec in sections:
        chunk = []
        for p in sec + [None]:
            if p is None:
                if chunk:
                    out.append("\n\n".join(chunk))
                chunk = []
            else:
                chunk.append(p)
    if cfg.get("start"):
        joined = "\n\n".join(out)
        i = joined.find(cfg["start"])
        if i >= 0:
            out = [joined[i:]]
    return [clean_ws(drop_inner_attributions(t)) for t in out if words(t) >= 6]


def gink():
    res = []
    for path, cfg in GINK_PAGES.items():
        secs = gink_page(path, cfg)
        slug = re.sub(r"[^A-Za-z0-9]+", "-", path).strip("-")
        for k, t in enumerate(secs, 1):
            res.append({
                "id": f"gink-{slug}-{k:02d}",
                "text": t,
                "source": "generative.ink",
                "url": GINK_URL + path + "/",
                "origin": cfg["origin"],
                "tier": cfg["tier"],
                "note": cfg.get("note", ""),
            })
    return res


def md_strip(t):
    t = re.sub(r"\[\^[^\]]+\]", "", t)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", t)
    t = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"\1", t)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = t.replace("\\", "")
    return t


def lesswrong_lem():
    d = json.loads((RAW / "lw" / "language-ex-machina.json").read_text(encoding="utf-8"))["data"]["post"]["result"]
    md = d["contents"]["markdown"]
    lines = md.split("\n")
    body, notes = [], []
    for ln in lines:
        if ln.startswith(">!"):
            continue
        if re.match(r"^\[\^[^\]]+\]:", ln):
            notes.append(re.sub(r"^\[\^[^\]]+\]:\s*", "", ln))
            continue
        body.append(ln)
    text = "\n".join(body)
    text = text.split("Reading the spoilered information", 1)[-1]
    text = text.split("\n", 1)[1] if "\n" in text else text
    sections = re.split(r"\n#{1,6} [^\n]*\n|\n\s*(?:\*\s*){3,}\n|\n-{3,}\n", "\n" + text + "\n")
    res = []
    k = 0
    for sec in sections:
        paras = [p for p in re.split(r"\n\s*\n", sec) if p.strip()]
        keep = []
        for p in paras:
            if p.lstrip().startswith(">"):
                q = "\n".join(re.sub(r"^>\s?", "", x) for x in p.split("\n"))
                if re.search(r"^\s*(—|--|–)", q, re.M):
                    continue
                p = q
            keep.append(md_strip(p).strip())
        t = clean_ws("\n\n".join(x for x in keep if x))
        if words(t) >= 6:
            k += 1
            res.append({"id": f"lw-language-ex-machina-{k:02d}", "text": t, "source": "lesswrong/Language Ex Machina",
                        "url": "https://www.lesswrong.com/posts/vPsupipfyeDoSAirY/language-ex-machina", "origin": "base", "tier": 1,
                        "note": "code-davinci-002 curated in Loom by janus, 'occasional small interventions and edits'; epigraphs and spoiler preface removed"})
    for j, n in enumerate(notes, 1):
        t = clean_ws(md_strip(n))
        if words(t) >= 6:
            res.append({"id": f"lw-language-ex-machina-fn{j:02d}", "text": t, "source": "lesswrong/Language Ex Machina",
                        "url": "https://www.lesswrong.com/posts/vPsupipfyeDoSAirY/language-ex-machina", "origin": "base", "tier": 1,
                        "note": "footnote body"})
    return res


EXTRA = RAW / "extra"


def ex_worldspider():
    s = soup_of(EXTRA / "jdp-worldspider.html")
    top = s.select_one("article.minimodel")
    res = []
    for art in [top] + top.find_all("article"):
        paras = []
        for c in art.children:
            if not isinstance(c, Tag):
                continue
            if c.name in ("hr", "article"):
                break
            if c.name == "p":
                t = inline_text(c)
                if t.strip() and not t.strip().startswith("["):
                    paras.append(t)
        t = clean_ws("\n\n".join(paras))
        if words(t) >= 6:
            res.append(t)
    return res


def ex_main_paras(fname, drop_prefixes=(), skip_blockquotes=False, split_headings=False):
    s = soup_of(EXTRA / fname)
    m = s.find("main") or s.find("article") or s.body
    for t in m.find_all(["header", "nav", "footer", "script", "style", "img", "figure", "table"]):
        t.decompose()
    for sup in m.find_all("sup"):
        sup.decompose()
    if skip_blockquotes:
        for b in m.find_all("blockquote"):
            b.decompose()
    secs = [[]]
    for c in m.find_all(["p", "h1", "h2", "h3", "h4", "li", "hr", "pre"]):
        if c.find_parent(["li"]) is not None and c.name != "li":
            continue
        if c.name == "pre":
            continue
        if c.name in ("h1", "h2", "h3", "h4", "hr"):
            if split_headings:
                secs.append([])
            continue
        t = inline_text(c)
        if not t.strip() or any(t.strip().startswith(d) for d in drop_prefixes):
            continue
        secs[-1].append(t)
    return [clean_ws("\n\n".join(x)) for x in secs if words("\n\n".join(x)) >= 6]


def ex_gwern():
    s = soup_of(EXTRA / "gwern-gpt3.html")
    res = []
    for sid in ["the-universe-is-a-glitch", "uber-poem", "a-new-kind-of-scribing", "the-library-of-babel"]:
        sec = s.find(id=sid)
        if sec is None:
            continue
        if sec.name != "section":
            sec = sec.find_parent("section") or sec
        for b in sec.find_all(["strong", "b", "sup"]):
            b.decompose()
        for a in sec.find_all("a", class_=re.compile("footnote")):
            a.decompose()
        for bq in sec.find_all("blockquote"):
            if bq.find_parent("blockquote") is not None:
                continue
            paras = []
            for c in bq.find_all(["p", "li", "pre"]):
                if c.find_parent(["p", "li"]) is not None:
                    continue
                t = inline_text(c) if c.name != "pre" else c.get_text()
                t = t.strip()
                if not t or t.startswith("Below is a selection of 10 poems") or re.fullmatch(r"By [^\n]{1,60}", t):
                    continue
                paras.append(t)
            t = clean_ws("\n\n".join(paras))
            if words(t) >= 6:
                res.append((sid, t))
    return res


def ex_arram():
    s = soup_of(EXTRA / "arram-eye-of-thuban.html")
    m = s.find("article") or s.find("main") or s.body
    paras = [inline_text(p) for p in m.find_all("p")]
    starts = [i for i, p in enumerate(paras) if p.strip().startswith("Chapter 1.")]
    start = starts[1] if len(starts) > 1 else (starts[0] if starts else 0)
    out = []
    for p in paras[start:]:
        if p.strip().startswith("Published"):
            break
        if p.strip().startswith("This novel is a science fiction thriller"):
            continue
        out.append(p)
    secs, cur = [], []
    for p in out:
        if re.match(r"^Chapter \d+\.?\s*$", p.strip()):
            if cur:
                secs.append(cur)
            cur = []
            continue
        cur.append(p)
    if cur:
        secs.append(cur)
    return [clean_ws("\n\n".join(x)) for x in secs if words("\n\n".join(x)) >= 6]


def ex_loom_dream():
    d = json.loads((EXTRA / "janus-loom-demo.json").read_text(encoding="utf-8"))
    top = d["root"]["children"][0]
    dream = [c for c in top["children"] if c["id"].startswith("d56aafb6")][0]

    def paths(n, acc):
        acc = acc + [n]
        if not n.get("children"):
            yield acc
        for c in n.get("children", []):
            yield from paths(c, acc)

    def ok(n):
        return (n.get("meta") or {}).get("source") != "prompt"

    P = sorted(paths(dream, []), key=lambda p: -sum(words(x["text"]) for x in p))
    seen = set()
    pieces = []
    for p in P:
        fresh = [x for x in p if x["id"] not in seen]
        txt = "".join(x["text"] for x in fresh if ok(x))
        if words(txt) >= 120 or (not seen and txt):
            pieces.append(txt)
            seen.update(x["id"] for x in fresh)
    out = []
    for txt in pieces:
        for part in re.split(r"\n\s*\*\s*\n", txt):
            t = clean_ws(part)
            if words(t) >= 6:
                out.append(t)
    return out


def extras():
    res = []

    def add(prefix, texts, url, origin, tier, source, note=""):
        for k, t in enumerate(texts, 1):
            res.append({"id": f"{prefix}-{k:02d}", "text": t, "source": source, "url": url, "origin": origin, "tier": tier, "note": note})

    add("jdp-worldspider", ex_worldspider(), "https://minihf.com/posts/2023-09-17-worldspider/", "base", 1, "minihf.com (JDP)",
        "LLaMa 2 70B, few-shot; the first entry may be part of the prompt")
    add("jdp-mus-encoding-1", ex_main_paras("jdp-mus-encoding-1.html", drop_prefixes=("[Continued from", "CC0", "To the extent possible")),
        "https://minihf.com/posts/2023-09-08-mus-encoding-1/", "unknown", 1, "minihf.com (JDP)", "Mu on LLaMa 2 70B and JDP; turns not marked")
    add("jdp-mus-encoding-2", ex_main_paras("jdp-mus-encoding-2.html", drop_prefixes=("[", "CC0", "To the extent possible")),
        "https://minihf.com/posts/2023-09-08-mus-encoding-2/", "unknown", 2, "minihf.com (JDP)", "LLaMa 2 70B output rewritten by JDP")
    add("janus-loom-dream", ex_loom_dream(), "https://raw.githubusercontent.com/socketteer/loom/main/data/loom_demo.json", "base", 1,
        "socketteer/loom demo tree", "davinci (2021) in janus's Loom; untagged human steering lines may be inside; branches taken as longest path then fresh suffixes")
    g = ex_gwern()
    for k, (sid, t) in enumerate(g, 1):
        res.append({"id": f"gwern-gpt3-{k:02d}", "text": t, "source": "gwern.net/gpt-3", "url": f"https://gwern.net/gpt-3#{sid}",
                    "origin": "base", "tier": 2, "note": f"GPT-3 davinci, section {sid}; bold prompt removed"})
    add("arram-eye-of-thuban", ex_arram(), "https://arr.am/2020/07/13/the-eye-of-thuban-a-sci-fi-fantasy/", "unknown", 2, "arr.am",
        "OpenAI playground, July 2020; model not named (likely davinci base)")
    add("jdp-hermes-lecture-3", ex_main_paras("jdp-hermes-lecture-3.html", drop_prefixes=("CC0", "To the extent possible")),
        "https://minihf.com/posts/2023-10-16-hermes-lecture-3-why-do-cognitive-scientists-hate-llms/", "human", 2, "minihf.com (JDP)")
    add("jdp-turing-apocrypha", ex_main_paras("jdp-turing-apocrypha-commentary.html", drop_prefixes=("CC0", "To the extent possible"), skip_blockquotes=True, split_headings=True),
        "https://minihf.com/posts/2025-06-07-commentary-on-janus-prophecies/", "human", 2, "minihf.com (JDP)", "JDP's own prose; quoted material removed")
    add("jdp-liber-augmen", ex_main_paras("jdp-liber-augmen.html", split_headings=True), "https://liberaugmen.com/", "human", 2, "liberaugmen.com (JDP)")
    return res


def main():
    load_prophecy_origins()
    load_wiki_rules()
    stages = sys.argv[1:] or ["all"]
    if "stats" in stages:
        stats()
        return
    if "wiki-inventory" in stages:
        inv = []
        ps = wiki(inv)
        by = {}
        for p in ps:
            by.setdefault(p["url"][len(WIKI_URL):], []).append(p["text"])
        for r in inv:
            head = " ".join(" ".join(by.get(r["page"], [""])).split())[:160]
            print(f"{r['page']}\t{r['status']}\t{','.join(r['cats'])}\t{r['skip'] or ''}\t{r['sections']}\t{r['words']}\t{head}")
        return
    items = []
    items += prophecies()
    items += prophecies_scratch()
    if "wikidump" in stages:
        items = wiki()
    if "ginkdump" in stages:
        items = gink() + lesswrong_lem()
    if "extradump" in stages:
        items = extras()
    if any(s.endswith("dump") for s in stages):
        for it in items:
            print(f"\n######## {it['id']}  [{it['origin']}]  {it['note']}  ({words(it['text'])}w)\n{it['text']}")
        return
    items += wiki()
    items += gink()
    items += lesswrong_lem()
    items += extras()
    items, dups = dedupe(items)
    with open(HERE / "passages.jsonl", "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"passages: {len(items)}  words: {sum(words(i['text']) for i in items)}  duplicate paragraphs dropped: {dups}")
    grades = load_grades()
    if grades:
        write_corpus(items, grades)


def stats():
    rows = [json.loads(l) for l in (HERE / "corpus.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    def table(title, keyf, subset=None):
        sub = [r for r in rows if subset is None or subset(r)]
        agg = {}
        for r in sub:
            k = keyf(r)
            a = agg.setdefault(k, [0, 0])
            a[0] += 1
            a[1] += words(r["text"])
        out = [f"**{title}**", "", "| | passages | words | ~tokens |", "|---|---:|---:|---:|"]
        for k in sorted(agg, key=lambda x: (-agg[x][1])):
            out.append(f"| {k} | {agg[k][0]} | {agg[k][1]:,} | {round(agg[k][1] * 1.35):,} |")
        tp, tw = sum(a[0] for a in agg.values()), sum(a[1] for a in agg.values())
        out.append(f"| **total** | **{tp}** | **{tw:,}** | **{round(tw * 1.35):,}** |")
        return "\n".join(out) + "\n"

    def lengths(title, subset=None):
        sub = [r for r in rows if subset is None or subset(r)]
        bins = [("< 30", 0, 30), ("30–100", 30, 100), ("100–300", 100, 300), ("> 300", 300, 10 ** 9)]
        out = [f"**{title}**", "", "| words | passages | words in bin |", "|---|---:|---:|"]
        for name, lo, hi in bins:
            b = [r for r in sub if lo <= words(r["text"]) < hi]
            out.append(f"| {name} | {len(b)} | {sum(words(r['text']) for r in b):,} |")
        return "\n".join(out) + "\n"

    parts = [
        table("All passages by source", lambda r: r["source"]),
        table("By origin", lambda r: r["origin"]),
        table("By tier", lambda r: f"tier {r['tier']}"),
        table("By fit", lambda r: f"fit {r['fit']}"),
        table("Tier × fit", lambda r: f"tier {r['tier']} · fit {r['fit']}"),
        table("Tier 1 with fit ≥ 1, by source", lambda r: r["source"], lambda r: r["tier"] == 1 and r["fit"] >= 1),
        table("Tier 1 with fit ≥ 1, by origin", lambda r: r["origin"], lambda r: r["tier"] == 1 and r["fit"] >= 1),
        table("cyborgism.wiki by origin", lambda r: r["origin"], lambda r: r["source"] == "cyborgism.wiki"),
        table("cyborgism.wiki by fit", lambda r: f"fit {r['fit']}", lambda r: r["source"] == "cyborgism.wiki"),
        table("Prophecies (page + 2 draft entries) by origin", lambda r: r["origin"], lambda r: r["source"].startswith("generative.ink/") ),
        table("Prophecies by fit", lambda r: f"fit {r['fit']}", lambda r: r["source"].startswith("generative.ink/")),
        lengths("Length distribution, all"),
        lengths("Length distribution, tier 1 fit ≥ 1", lambda r: r["tier"] == 1 and r["fit"] >= 1),
        lengths("Length distribution, fit 2", lambda r: r["fit"] == 2),
    ]
    print("\n".join(parts))


PARA_NORM = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


def para_key(p):
    return " ".join(p.translate(PARA_NORM).split())


def dedupe(items):
    seen = set()
    out = []
    dropped = 0
    for it in items:
        paras = it["text"].split("\n\n")
        keep = []
        for p in paras:
            k = para_key(p)
            if words(p) >= 8 and k in seen:
                dropped += 1
                continue
            keep.append(p)
        for p in paras:
            if words(p) >= 8:
                seen.add(para_key(p))
        t = clean_ws("\n\n".join(keep))
        if words(t) >= 6:
            it = dict(it, text=t)
            out.append(it)
    return out, dropped


def load_grades():
    g = {}
    for f in sorted((HERE / "grades").glob("*.json")) if (HERE / "grades").exists() else []:
        g.update(json.loads(f.read_text(encoding="utf-8")))
    return g


SOURCE_ORDER = ["generative.ink/prophecies", "generative.ink/drafts/prophecies-scratch", "cyborgism.wiki", "lesswrong/Language Ex Machina",
                "generative.ink", "minihf.com (JDP)", "socketteer/loom demo tree", "gwern.net/gpt-3", "arr.am", "liberaugmen.com (JDP)"]


def write_corpus(items, grades):
    kept, dropped, ungraded = [], [], []
    for it in items:
        g = grades.get(it["id"])
        if g is None:
            ungraded.append(it["id"])
            continue
        if g.get("drop"):
            dropped.append({"id": it["id"], "reason": g["drop"], "words": words(it["text"])})
            continue
        origin = it["origin"]
        if g.get("origin") and g.get("origin_evidence") and origin in ("human", "unknown"):
            origin = g["origin"]
        kept.append({"id": it["id"], "text": it["text"], "source": it["source"], "url": it["url"],
                     "origin": origin, "tier": it["tier"], "fit": int(g["fit"]), "_note": it.get("note", "")})
    with open(HERE / "corpus.jsonl", "w", encoding="utf-8") as f:
        for k in kept:
            f.write(json.dumps({x: k[x] for x in ("id", "text", "source", "url", "origin", "tier", "fit")}, ensure_ascii=False) + "\n")
    with open(HERE / "dropped.jsonl", "w", encoding="utf-8") as f:
        for d in dropped:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    order = {s: i for i, s in enumerate(SOURCE_ORDER)}
    groups = {}
    for k in kept:
        groups.setdefault(k["source"], []).append(k)
    lines = ["# School corpus", "", f"{len(kept)} passages. Each heading is the passage id, then origin · tier · fit, then a provenance note.", ""]
    for src in sorted(groups, key=lambda s: order.get(s, 99)):
        lines += [f"## {src}", ""]
        for k in groups[src]:
            lines += [f"### {k['id']}", "", f"*{k['origin']} · tier {k['tier']} · fit {k['fit']}*" + (f" · {k['_note']}" if k["_note"] else "") + f" · <{k['url']}>", ""]
            lines += ["\n".join(("    " + x) if x.startswith(("#", ">", "*", "-", "|")) else x for x in k["text"].split("\n")), "", "---", ""]
    (HERE / "corpus.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"corpus: {len(kept)} kept, {len(dropped)} dropped, {len(ungraded)} ungraded")
    if ungraded:
        print("ungraded:", " ".join(ungraded[:20]))


if __name__ == "__main__":
    main()
