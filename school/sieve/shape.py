import re
import statistics

import settings
import words as dedupe_words

QUOTE = re.compile(r"[“”\"]|(?:^|\s)‘\S")
OPEN_QUOTE = re.compile(r"^\W{0,3}[“\"‘']")
SENTENCE_CLOSE = ".!?…:;,\"”’')"
NAME_TOKEN = re.compile(r"(?:[A-Z][\w’'-]*\.?|[A-Z]\.(?:[A-Z]\.)*|de|del|della|van|von|der|den|la|le|du|da|di|bin|al|el|y|and|&|Jr\.?|Sr\.?|II|III)$")
NOT_NAMES = frozenset("""the a an in on at of to for from with by old new my his her our your their its this that
these those last first one two three four five six seven eight nine ten all no not what when where why how who is are was
were be it i we you he she they me us them part book chapter introduction notes day night time world life death man woman
men women girl boy city house home war love story stories tale tales end dead dark light black white red blue green
north south east west under over after before into out up down""".split())
CAPITAL_START = re.compile(r"[A-ZÀ-Þ]")
SPACES = re.compile(r"\s+")
LABEL_SPLIT = re.compile(r"\s*[:.]\s")


def paragraphs(text):
    out = []
    for block in dedupe_words.BLANK_LINE.split(dedupe_words.clean_newlines(text)):
        block = block.strip("\n")
        if block.strip():
            out.append(block)
    return out


def render(paras, keep):
    kept = [p for p, wanted in zip(paras, keep) if wanted]
    return "\n\n".join(kept) + "\n" if kept else ""


def count(text):
    return len(text.split())


def squash(text):
    return SPACES.sub(" ", text).strip()


def rate(pattern, text, total):
    if total <= 0:
        return 0.0
    return round(1000.0 * sum(1 for _ in pattern.finditer(text)) / total, 2)


def is_heading(paragraph, heading_max_words):
    lines = [line for line in paragraph.split("\n") if line.strip()]
    if not lines or len(lines) > 3:
        return False
    total = sum(len(line.split()) for line in lines)
    if total > heading_max_words + 4:
        return False
    return all(dedupe_words.heading_shaped(line, len(line.split()), heading_max_words)
               or dedupe_words.YEAR_LINE.fullmatch(line.strip()) for line in lines) \
        and any(dedupe_words.heading_shaped(line, len(line.split()), heading_max_words) for line in lines)


def name_shaped(line, max_tokens):
    tokens = line.strip().strip(",.;:").split()
    if not 2 <= len(tokens) <= max_tokens:
        return False
    if not all(NAME_TOKEN.match(t.strip(",")) for t in tokens):
        return False
    if any(t.strip(",.").casefold() in NOT_NAMES for t in tokens):
        return False
    return sum(1 for t in tokens if CAPITAL_START.match(t)) >= 2


def surnames(names):
    out = set()
    for name in names or []:
        tokens = [t for t in re.findall(r"[^\W\d_]{4,}", name) if t.lower() not in ("with", "junior", "translated")]
        if tokens:
            out.add(tokens[-1].casefold())
    return out


def features(paras, cfg):
    text = "\n\n".join(paras)
    total = count(text)
    lines = [line for p in paras for line in p.split("\n") if line.strip()]
    line_words = [len(line.split()) for line in lines]
    limit = cfg.shape.verse_line_max_words
    stanza_words = 0
    for p in paras:
        own = [len(line.split()) for line in p.split("\n") if line.strip()]
        if len(own) >= 2 and statistics.median(own) <= limit:
            stanza_words += sum(own)
    short_open = sum(1 for line, n in zip(lines, line_words)
                     if n <= limit and line.rstrip()[-1:] not in SENTENCE_CLOSE)
    quoted = sum(1 for p in paras if QUOTE.search(p))
    labels = {}
    turns = 0
    for p in paras:
        head = p.lstrip()[:80]
        if cfg.patterns["speaker_label"].match(head):
            label = LABEL_SPLIT.split(head, 1)[0].strip()
            if len(label.split()) <= cfg.shape.label_max_words:
                labels[label] = labels.get(label, 0) + 1
                turns += 1
    repeated = sum(n for n in labels.values() if n >= 2)
    lowered = text
    out = {
        "words": total,
        "paragraphs": len(paras),
        "lines": len(lines),
        "line_words_mean": round(sum(line_words) / len(lines), 2) if lines else 0.0,
        "stanza_share": round(stanza_words / total, 3) if total else 0.0,
        "short_open_share": round(short_open / len(lines), 3) if lines else 0.0,
        "quote_share": round(quoted / len(paras), 3) if paras else 0.0,
        "speech_share": round(sum(1 for p in paras if OPEN_QUOTE.match(p)) / len(paras), 3) if paras else 0.0,
        "qa_turns": repeated,
        "qa_share": round(repeated / len(paras), 3) if paras else 0.0,
        "qa_labels": len([1 for n in labels.values() if n >= 2]),
        "meta": rate(cfg.patterns["meta_words"], lowered, total),
        "biblio": rate(cfg.patterns["biblio_words"], lowered, total),
        "narrative": rate(cfg.patterns["narrative_words"], lowered, total),
        "address": rate(cfg.patterns["address_words"], lowered, total),
    }
    return out


def span_rates(paras, cfg):
    text = "\n\n".join(paras)
    total = count(text)
    quoted = sum(1 for p in paras if QUOTE.search(p))
    return {
        "words": total,
        "meta": rate(cfg.patterns["meta_words"], text, total),
        "biblio": rate(cfg.patterns["biblio_words"], text, total),
        "narrative": rate(cfg.patterns["narrative_words"], text, total),
        "quote_share": round(quoted / len(paras), 3) if paras else 0.0,
    }


def bio_score(paragraph, cfg, author_surnames):
    n = count(paragraph)
    if n > cfg.edges.bio_max_words or n < 6:
        return 0
    if OPEN_QUOTE.match(paragraph):
        return 0
    score = 0
    lowered = paragraph.casefold()
    opening = paragraph.strip().split()
    named = any(s in lowered for s in author_surnames)
    verbs = len({m.group(0).casefold() for m in cfg.patterns["bio_verbs"].finditer(paragraph)})
    if named and verbs:
        score += 2
    lead = 0
    for token in opening[:5]:
        if NAME_TOKEN.match(token.strip(",")) and CAPITAL_START.match(token):
            lead += 1
        else:
            break
    after = opening[lead].casefold().strip(",") if lead < len(opening) else ""
    if lead >= 2 and (after in ("is", "lives", "was", "has", "writes", "grew", "works", "lived", "holds", "teaches",
                                "received", "studied", "currently", "(she/her)", "(he/him)", "(they/them)")
                      or after.startswith("(")):
        score += 1
    score += min(verbs, 3)
    if sum(1 for _ in cfg.patterns["biblio_words"].finditer(paragraph)) >= 2:
        score += 1
    if QUOTE.search(paragraph) and not verbs:
        score -= 2
    return score


def names(paragraph, author_surnames):
    for surname in author_surnames:
        for found in re.finditer(rf"(?<![^\W\d_]){re.escape(surname)}(?![^\W\d_])", paragraph, re.I):
            if found.group(0)[:1].isupper():
                return True
    return False


def headnote_parts(paragraph, cfg, author_surnames):
    n = count(paragraph)
    if n < 8:
        return False, 0, False
    named = names(paragraph, author_surnames)
    other = 2 * min(len({m.group(0).casefold() for m in cfg.patterns["headnote_phrases"].finditer(paragraph)}), 3)
    if sum(1 for _ in cfg.patterns["biblio_words"].finditer(paragraph)) >= 2:
        other += 1
    if sum(1 for _ in cfg.patterns["meta_words"].finditer(paragraph)) >= 3:
        other += 1
    presenting = bool(cfg.patterns["headnote_presenting"].search(paragraph))
    if OPEN_QUOTE.match(paragraph) and not (named and other >= 2):
        return False, -1, False
    return named, other, presenting


def is_headnote(paragraph, cfg, author_surnames):
    named, other, presenting = headnote_parts(paragraph, cfg, author_surnames)
    return (named and other >= cfg.books.headnote_named_score) or other >= cfg.books.headnote_min_score
