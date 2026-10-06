import html
import json
import re

TAG_BREAK = re.compile(r"(?i)<\s*(br|p|/p|hr|div|/div|li|/li|tr|/tr|h\d|/h\d)\b[^>]*>")
TAG_ANY = re.compile(r"</?[a-zA-Z][a-zA-Z0-9]*\b[^<>]{0,200}>")
CHAPTER = re.compile(r"^\t+\d+\.\s.*$")
SCENE_WORD = re.compile(r"(?i)^[\W_]*(line ?break|page ?break|scene ?break|break|lb|pb|time ?skip|pov ?change|pov ?switch)[\W_]*$")
SCENE_SYM = re.compile(r"^[\W_xXoO0]*$")
HEADING = re.compile(r"(?i)^[\W_]*(chapter|ch\.?|chap\.?|part|prologue|epilogue|interlude|book|act|scene)\b[\s\W\d]*(\w[\w\s'’,:!?-]{0,60})?$")
MARK = "\x00"
BOLD = re.compile(r"\*\*")
UNDER = re.compile(r"(?<!\w)_+|_+(?!\w)")
BOLD_WRAP = re.compile(r"^[_\s]*\*\*.*\*\*[_\s]*$")
SEG_META = re.compile(r"(?i)\b(story|stories|fic|fics|upload\w*|wrote|written|writing|chapter|chapters|enjoy|review\w*|oneshot|one-shot|"
                      r"inspired|dedicat\w*|thanks|thank you|sorry|hope you|set (directly |right )?(after|before|during)|takes place|"
                      r"spoilers?|warning|au\b|alternate universe|season \d|episode|patreon|next time|repl(y|ies)|responses?|guest)\b")
AN_START = re.compile(
    r"(?i)^[\W_]*(a/n|an\s*:|a\.n\.|a\s*/\s*n|author'?s?'?\s*notes?|authors?\s+notes?|notes?\s*:|disclaimer|summary\b|"
    r"pairings?\b|warnings?\s*:|rated\s*:?\s*[a-z+-]{1,6}\b|rating\s*:|beta|beta'?d|dedicated|dedication|edit\s*:|update\s*:|"
    r"please\s+review|r\s*&\s*r|read\s+and\s+review|review|reviews|thanks?\s+(you\s+)?(for|to)|"
    r"word\s*count|genre\s*:|characters?\s*:|spoilers?\s*:|timeline\s*:|feedback\s*:|author\s*:|e-?mail\s*:|title\s*:|"
    r"fandom\s*:|status\s*:|category\s*:|archive\s*:|setting\s*:|ps\s*:|p\.s\.|pps\s*:)"
)
META_STRONG = re.compile(
    r"(?i)\b(fan\s?-?fics?|fan\s?-?fictions?|fanfiction\.net|a/n|author'?s note|authors note|disclaimer|"
    r"i\s+(do\s+not|don'?t|dont)\s+own|don'?t\s+own\s+(anything|any|the)|do\s+not\s+own|owns?\s+nothing|"
    r"r\s*&\s*r|please\s+review|leave\s+a\s+review|review\s+please|reviewers|flames|flamers|"
    r"(next|last|previous|this|first|new)\s+chapter|chapters?\s+\d+|one-?shot|drabbles?|ooc|oc's|"
    r"lemons?|pm\s+me|kudos|beta[- ]?read|my\s+beta|fav(e|ourite|orite)?s?\s+(and|&)\s+follow|"
    r"update\s+(soon|faster|more)|updating|hiatus|on\s+deviantart|ao3|wattpad|tumblr|"
    r"rights\s+reserved|copyright|belongs?\s+to\s+(the\s+)?(amazing|great|wonderful|respective))\b"
)
AN_SOFT = re.compile(
    r"(?i)\b(give me (some )?reviews|reviews? (please|plz|pls)|tell me what you (guys )?think|let me know what you (guys )?think|"
    r"thanks for reading|thank you for reading|hope you (all |guys )?(enjoy|enjoyed|like|liked)|until next time|see you (in the )?next chapter)\b"
)
NOTE_SOFT = re.compile(
    r"(?i)(\b(enjoy|hope you|thanks|thank you|sorry|anyway|guys|readers?|stories|writing|wrote|posted|reviews?|comments?|lol|update)\b|:\)|:D|\^\^|<3)"
)
SCRIPT_LINE = re.compile(r"^[-~]?\s?[A-Z]?[\w.' -]{1,24}\s?:\s?\S")
CHATSPEAK = re.compile(r"(?i)\b(u|ur|plz|pls|lol|omg|lmao|xd|thx|ya'll|cuz|kawaii|desu|nya)\b")
WORD = re.compile(r"[A-Za-z']+")

RATING = re.compile(
    r"(?i)\b(?:rated|rating)\s*(?:is|:|-|=)?\s*[\"'(\[]?\s*(k\+|k|t|m|ma|fr\d+|fr13|fr15|fr18|fr21|g|pg-?13|pg|r|nc-?17|x|e|explicit|mature|teen|teens?)(?=[\s\"').,\]!:;-]|$)"
)
RATING_MAP = {
    "k": "K", "k+": "K+", "g": "K", "pg": "K+", "t": "T", "teen": "T", "teens": "T", "pg13": "T", "pg-13": "T",
    "m": "M", "mature": "M", "r": "M", "fr15": "T", "fr13": "T", "fr18": "M", "fr21": "MA", "ma": "MA",
    "nc17": "MA", "nc-17": "MA", "x": "MA", "e": "MA", "explicit": "MA",
}


def unquote(text):
    if text.startswith('"') and text.endswith('"') and "\\n" in text[:5000]:
        try:
            return json.loads(text)
        except Exception:
            return text
    return text


def is_scene_break(p):
    if not p:
        return False
    if SCENE_WORD.match(p):
        return True
    if SCENE_SYM.match(p) and len(p) <= 80:
        return True
    return False


def note_block(seg):
    size = sum(len(x) for x in seg)
    hits = sum(1 for x in seg if SEG_META.search(x) or SCRIPT_LINE.match(x))
    if len(seg) <= 4 and size <= 1200 and hits:
        return True
    return len(seg) <= 12 and size <= 3000 and hits / len(seg) >= 0.4


def trim_segments(kept, stats):
    bounds = [i for i, x in enumerate(kept) if x in ("* * *", MARK)]
    if bounds:
        first = bounds[0]
        head = kept[:first]
        if head and len(kept) - first > 3 and note_block(head):
            stats["an"] += len(head)
            kept = kept[first + 1:]
    bounds = [i for i, x in enumerate(kept) if x in ("* * *", MARK)]
    if bounds:
        last = bounds[-1]
        tail = kept[last + 1:]
        if tail and last > 3 and note_block(tail):
            stats["an"] += len(tail)
            kept = kept[:last]
    kept = [x for x in kept if x != MARK]
    while kept and kept[0] == "* * *":
        kept.pop(0)
    while kept and kept[-1] == "* * *":
        kept.pop()
    return kept


def clean(raw):
    t = unquote(raw)
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = TAG_BREAK.sub("\n", t)
    t = TAG_ANY.sub("", t)
    t = html.unescape(t)
    t = t.replace(" ", " ").replace("​", "")
    lines = t.split("\n")
    if lines:
        lines = lines[1:]
    chapters = [[]]
    for ln in lines:
        if CHAPTER.match(ln):
            chapters.append([])
            continue
        s = ln.strip()
        if s.startswith(">"):
            s = s.lstrip(">").strip()
        bold = bool(BOLD_WRAP.match(s))
        s = UNDER.sub("", BOLD.sub("", s))
        s = re.sub(r"[ \t]+", " ", s).strip()
        if not s:
            continue
        chapters[-1].append((s, bold))
    while chapters and chapters[-1] and chapters[-1][-1][0].lower().rstrip(".") == "end file":
        chapters[-1].pop()
    stats = {"an": 0, "heading": 0}
    out = []
    for ch in chapters:
        if not ch:
            continue
        n = len(ch)
        kept = []
        in_note = False
        for i, (p, bold) in enumerate(ch):
            edge = i < 6 or i >= n - 6
            low = p.lower()
            if is_scene_break(p):
                in_note = False
                kept.append("* * *")
                continue
            if i == 0 and len(p) < 60 and not p.endswith((".", '"', "?", "!", "”", "'", "…", "’")):
                stats["heading"] += 1
                continue
            if len(p) < 70 and HEADING.match(p) and (i < 2 or not p.endswith((".", '"', "?", "!", "”"))):
                stats["heading"] += 1
                if edge and kept:
                    kept.append(MARK)
                continue
            if bold and edge:
                stats["an"] += 1
                if kept:
                    kept.append(MARK)
                continue
            if AN_START.match(p):
                stats["an"] += 1
                in_note = edge
                continue
            if META_STRONG.search(low) and (edge or len(p) < 400) or AN_SOFT.search(p) and not p.startswith(('"', "'", "\u201c")) and (edge or len(p) < 300):
                stats["an"] += 1
                continue
            if in_note and edge and (p.startswith(("(", "[")) or NOTE_SOFT.search(p)):
                stats["an"] += 1
                continue
            in_note = False
            kept.append(p)
        kept = trim_segments(kept, stats)
        if kept:
            if out:
                out.append("* * *")
            out.extend(kept)
    final = []
    for p in out:
        if p == "* * *" and final and final[-1] == "* * *":
            continue
        final.append(p)
    return "\n\n".join(final), final, stats


def rating_of(raw):
    head = raw[:6000]
    m = RATING.search(head)
    if not m:
        return "unknown"
    k = m.group(1).lower().replace(" ", "")
    return RATING_MAP.get(k, RATING_MAP.get(k.replace("-", ""), "unknown"))


def quality(paras, words):
    reasons = []
    if words < 300:
        reasons.append("short")
    body = [p for p in paras if p != "* * *"]
    if not body:
        return ["empty"]
    letters = [p for p in body if p[0].isalpha()]
    if letters:
        lower = sum(1 for p in letters if p[0].islower()) / len(letters)
        if lower > 0.35:
            reasons.append("lowercase")
    script = sum(1 for p in body if SCRIPT_LINE.match(p)) / len(body)
    if script > 0.2:
        reasons.append("script")
    if words:
        chat = len(CHATSPEAK.findall(" ".join(body[:400]))) * 1000 / max(1, min(words, sum(len(p.split()) for p in body[:400])))
        if chat > 4:
            reasons.append("chatspeak")
    return reasons
