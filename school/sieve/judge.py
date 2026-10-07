import shape

HEAD_TAGS = {"magazine": ("nav", "pitch", "credit", "warning", "translator"),
             "podcast": ("nav", "pitch", "credit", "warning", "translator", "host"),
             "serial": ("nav", "pitch", "warning"),
             "plain": ("nav", "pitch", "credit")}
TAIL_TAGS = {"magazine": ("nav", "pitch", "credit", "translator", "bio", "teaser"),
             "podcast": ("nav", "pitch", "credit", "translator", "bio", "host", "teaser"),
             "serial": ("nav", "pitch"),
             "plain": ("nav", "pitch", "credit", "teaser")}
REASONS = {"nav": "nav", "pitch": "pitch", "credit": "credit", "warning": "content-warning", "translator": "credit",
           "bio": "author-bio", "teaser": "nav", "sandwich": "nav"}


def fired(evidence, signal, value, weight):
    evidence.append({"signal": signal, "value": value, "weight": weight})


def classify(cfg, doc, paras, feats):
    P = cfg.patterns
    S = cfg.stub
    N = cfg.nonfiction
    W = cfg.weights
    evidence = []
    total = feats["words"]
    title = doc.title or ""
    profile = doc.profile
    rated = total >= cfg.shape.min_words_for_rates

    verse_class = next((c for c in doc.classes if P["class_verse"].search(c)), None)
    if doc.label and P["label_verse"].search(doc.label):
        fired(evidence, "label-verse", doc.label, 0)
        return "verse", "the page is labelled verse", evidence
    if verse_class:
        fired(evidence, "class-verse", verse_class, 0)
        return "verse", "the page's classes say verse", evidence

    if total < S.tiny_words:
        fired(evidence, "tiny", total, 0)
        return "stub", f"under {S.tiny_words} words", evidence

    V = cfg.verse
    strong = P["title_nonfiction_strong"].search(title)
    notice = P["title_notice"].search(title)
    trusted = doc.source in cfg.fiction_index or profile in ("serial", "plain") \
        or any(P["class_fiction"].search(c) for c in doc.classes) \
        or bool(doc.label and P["label_fiction"].search(doc.label))
    if feats["lines"] >= V.min_lines and feats["line_words_mean"] <= V.max_line_words_mean and not (strong or notice):
        shaped = None
        if feats["stanza_share"] >= V.stanza_share_min:
            shaped = ("stanza-share", feats["stanza_share"], "most of its words stand in stanzas of short lines")
        elif feats["short_open_share"] >= V.short_line_share_min:
            shaped = ("short-open-line-share", feats["short_open_share"], "its lines are short and open-ended")
        if shaped:
            fired(evidence, shaped[0], shaped[1], 0)
            fired(evidence, "line-words-mean", feats["line_words_mean"], 0)
            if trusted:
                fired(evidence, "fiction-index", doc.source, 0)
                return "unsure", "shaped like verse on a fiction-only shelf", evidence
            return "verse", shaped[2], evidence

    tail_text = "\n".join(paras[-3:])
    head_text = "\n".join(paras[:3])
    if doc.words_in and total <= S.remnant_words and total <= S.remnant_share * doc.words_in:
        fired(evidence, "remnant", f"{total} of {doc.words_in} words left by the deduper", 0)
        return "stub", "what the deduper left of a longer file", evidence
    if total < S.teaser_words:
        teaser = P["teaser"].search(tail_text)
        if teaser:
            fired(evidence, "teaser", shape.squash(teaser.group(0))[:60], 0)
            return "stub", "a teaser that points elsewhere for the rest", evidence
        if doc.excerpt_hint:
            fired(evidence, "excerpt-hint", True, 0)
            return "stub", "the index calls it an excerpt and it is short", evidence
    if notice and total < S.notice_words:
        fired(evidence, "title-notice", shape.squash(notice.group(0)), 0)
        return "stub", "a short notice", evidence
    if profile == "podcast" and total < S.podcast_words:
        fired(evidence, "podcast-short", total, 0)
        return "stub", f"a podcast page under {S.podcast_words} words: show notes or the opening of a story", evidence

    non = 0.0
    fic = 0.0
    weak = None if strong else P["title_nonfiction_weak"].search(title)
    if strong:
        non += W.title_strong
        fired(evidence, "title", shape.squash(strong.group(0)), W.title_strong)
    elif notice:
        non += W.title_weak
        fired(evidence, "title-notice", shape.squash(notice.group(0)), W.title_weak)
    elif weak:
        non += W.title_weak
        fired(evidence, "title-hint", shape.squash(weak.group(0)), W.title_weak)
    if doc.label and P["label_nonfiction"].search(doc.label):
        non += W.label
        fired(evidence, "label", doc.label, W.label)
    class_non = next((c for c in doc.classes if P["class_nonfiction"].search(c)), None)
    if class_non:
        non += W.label
        fired(evidence, "class", class_non, W.label)
    url = P["url_nonfiction"].search(doc.url or "")
    if url:
        non += W.url
        fired(evidence, "url", url.group(0), W.url)
    if doc.columnist:
        non += W.columnist
        fired(evidence, "columnist", doc.columnist, W.columnist)
    if rated:
        if feats["qa_turns"] >= N.qa_min_turns and feats["qa_share"] >= N.qa_share_min and feats["qa_labels"] >= 2:
            non += W.qa
            fired(evidence, "question-and-answer", feats["qa_share"], W.qa)
        if feats["meta"] >= N.meta_high:
            non += W.meta_high
            fired(evidence, "talk-about-writing", feats["meta"], W.meta_high)
        elif feats["meta"] >= N.meta_mid:
            non += W.meta_mid
            fired(evidence, "talk-about-writing", feats["meta"], W.meta_mid)
        if feats["biblio"] >= N.biblio_high:
            non += W.biblio_high
            fired(evidence, "bibliography", feats["biblio"], W.biblio_high)
        if feats["address"] >= N.address_high:
            non += W.address
            fired(evidence, "addresses-readers", feats["address"], W.address)
        if feats["narrative"] < N.narrative_low:
            non += W.narrative_low
            fired(evidence, "not-narrative", feats["narrative"], W.narrative_low)

    if doc.source in cfg.fiction_index or profile in ("serial", "plain"):
        fic += W.fiction_index
        fired(evidence, "fiction-index", profile if profile in ("serial", "plain") else doc.source, -W.fiction_index)
    class_fic = next((c for c in doc.classes if P["class_fiction"].search(c)), None)
    if class_fic:
        fic += W.fiction_class
        fired(evidence, "class-fiction", class_fic, -W.fiction_class)
    if doc.label and P["label_fiction"].search(doc.label):
        fic += W.fiction_class
        fired(evidence, "label-fiction", doc.label, -W.fiction_class)
    if doc.ledger_kind in ("story", "novel", "novella", "novelette", "collection", "original", "classic"):
        fic += W.ledger_story
        fired(evidence, "ledger-kind", doc.ledger_kind, -W.ledger_story)
    if rated:
        if feats["narrative"] >= N.narrative_high:
            fic += W.narrative_high
            fired(evidence, "narrative", feats["narrative"], -W.narrative_high)
        if feats["speech_share"] >= N.speech_share_high:
            fic += W.speech
            fired(evidence, "dialogue", feats["speech_share"], -W.speech)
        if feats["meta"] < N.meta_low:
            fic += W.meta_low
            fired(evidence, "no-talk-about-writing", feats["meta"], -W.meta_low)
    if total >= N.long_fiction_words:
        fic += W.long_fiction
        fired(evidence, "long", total, -W.long_fiction)

    net = round(non - fic, 2)
    if non <= 0:
        if (V.unsure_stanza_share <= feats["stanza_share"] and feats["lines"] >= V.min_lines
                and feats["line_words_mean"] <= V.unsure_line_words_mean and total <= V.unsure_max_words):
            fired(evidence, "stanza-share", feats["stanza_share"], 0)
            return "unsure", "part verse, part prose", evidence
        return "fiction", "nothing says otherwise", [e for e in evidence if e["weight"] == 0]
    if net >= N.decide_min:
        return "nonfiction", f"non-fiction {non:g} against fiction {fic:g}", evidence
    if net >= N.unsure_min:
        return "unsure", f"non-fiction {non:g} against fiction {fic:g}: too close", evidence
    return "fiction", f"non-fiction {non:g} against fiction {fic:g}", evidence


def tags_of(cfg, doc, paragraph, position):
    P = cfg.patterns
    n = shape.count(paragraph)
    out = []
    lines = [line for line in paragraph.split("\n") if line.strip()]
    first = lines[0] if lines else ""
    quoted = bool(shape.QUOTE.search(paragraph))
    if n <= 40 and not quoted and all(P["nav"].search(line) for line in lines):
        out.append("nav")
    if n <= 160 and not quoted and P["pitch"].search(paragraph) and P["pitch_address"].search(paragraph):
        out.append("pitch")
    if n <= 120 and (P["credit"].search(first) or (n <= 25 and any(P["credit"].search(line) for line in lines))):
        out.append("credit")
    if n <= 80 and P["translator"].search(first):
        out.append("translator")
    if position == "head" and n <= 120 and P["warning"].search(first):
        out.append("warning")
    if n <= 200 and P["host"].search(paragraph) and not shape.OPEN_QUOTE.match(paragraph):
        out.append("host")
    if position == "tail" and shape.bio_score(paragraph, cfg, doc.surnames) >= cfg.edges.bio_min_score:
        out.append("bio")
    if position == "tail" and n <= 40 and P["teaser"].search(paragraph):
        out.append("teaser")
    return out


def reason_of(tag, position):
    if tag == "host":
        return "host-intro" if position == "head" else "outro"
    return REASONS[tag]


def walk(cfg, doc, paras, counts, order, allowed, position, word_limit):
    E = cfg.edges
    taken = {}
    pending = []
    spent = 0
    for i in order[:E.zone_paragraphs]:
        tags = [t for t in tags_of(cfg, doc, paras[i], position) if t in allowed]
        if tags:
            cost = counts[i] + sum(counts[j] for j in pending)
            if spent + cost > word_limit:
                break
            for j in pending:
                taken[j] = "sandwich"
            pending = []
            taken[i] = tags[0]
            spent += cost
            continue
        if counts[i] <= E.sandwich_words and len(pending) < 3:
            pending.append(i)
            continue
        break
    return taken


def cut_edges(cfg, doc, paras):
    E = cfg.edges
    P = cfg.patterns
    profile = doc.profile
    n = len(paras)
    counts = [shape.count(p) for p in paras]
    total = sum(counts)
    flags = []
    reasons = {}
    end = n
    head_stop = 0

    if profile == "serial":
        navs = [i for i in range(n) if counts[i] <= 12 and not shape.QUOTE.search(paras[i])
                and all(P["chapter_nav"].search(line) for line in paras[i].split("\n") if line.strip())]
        before = [0]
        for c in counts:
            before.append(before[-1] + c)
        tails = [i for i in navs if before[i] >= E.tail_marker_zone_share * total
                 and total - before[i] <= E.note_max_words and total - before[i] <= E.serial_note_max_share * total]
        if tails:
            first = tails[0]
            for i in range(first, n):
                tags = tags_of(cfg, doc, paras[i], "tail")
                reasons[i] = "nav" if i in navs else "pitch" if "pitch" in tags else "author-note"
            end = first
        heads = [i for i in navs if i < E.zone_paragraphs and before[i + 1] <= E.head_max_words and i < end]
        if heads:
            last = heads[-1]
            head_stop = last + 1
            for i in range(0, last + 1):
                tags = tags_of(cfg, doc, paras[i], "head")
                if i in navs:
                    reasons[i] = "nav"
                elif tags or counts[i] > 3:
                    reasons[i] = "pitch" if "pitch" in tags else "content-warning" if "warning" in tags else "author-note"

    running = 0
    marker_at = None
    for i in range(n):
        if running >= E.tail_marker_zone_share * total and counts[i] <= E.marker_max_words and marker_at is None:
            line = paras[i].strip()
            rest = total - running
            if P["comments_marker"].search(line) and profile != "plain":
                if rest - counts[i] >= E.comments_min_words:
                    marker_at = (i, "comments")
            elif P["bio_marker"].search(line) and profile != "plain":
                if rest <= E.tail_max_words:
                    marker_at = (i, "author-bio")
                else:
                    flags.append({"signal": "long-tail-after-marker", "value": f"{line[:40]}: {rest} words", "weight": 0})
            elif P["note_marker"].search(line) and profile != "plain":
                limit = E.note_max_words
                share = E.serial_note_max_share if profile == "serial" else E.tail_max_share
                if rest <= limit and rest <= share * total:
                    marker_at = (i, "author-note")
                else:
                    flags.append({"signal": "long-tail-after-marker", "value": f"{line[:40]}: {rest} words", "weight": 0})
        running += counts[i]
    if marker_at and marker_at[0] < end:
        start, why = marker_at
        current = why
        for i in range(start, end):
            line = paras[i].strip()
            if counts[i] <= E.marker_max_words:
                if P["comments_marker"].search(line):
                    current = "comments"
                elif P["bio_marker"].search(line):
                    current = "author-bio"
                elif P["note_marker"].search(line):
                    current = "author-note"
            reasons[i] = current
        end = start

    tail_limit = min(E.tail_max_words, int(E.tail_max_share * total))
    tail = walk(cfg, doc, paras, counts, list(range(end - 1, head_stop - 1, -1)), TAIL_TAGS[profile], "tail", tail_limit)
    for i, tag in tail.items():
        reasons[i] = reason_of(tag, "tail")
    stop = min([end] + list(tail))
    head = walk(cfg, doc, paras, counts, list(range(head_stop, stop)), HEAD_TAGS[profile], "head", E.head_max_words)
    for i, tag in head.items():
        reasons[i] = reason_of(tag, "head")

    for where, group in (("head", head), ("tail", tail)):
        sandwiched = [i for i, tag in group.items() if tag == "sandwich"]
        for i in sandwiched:
            neighbours = [reasons[j] for j in (i - 1, i + 1) if j in reasons and group.get(j) != "sandwich"]
            if neighbours:
                reasons[i] = neighbours[0]

    left = total - sum(counts[i] for i in reasons)
    if reasons and left < min(E.min_body_words, total):
        flags.append({"signal": "edge-cuts-refused", "value": f"would leave {left} of {total} words", "weight": 0})
        return [], flags
    return spans(reasons, counts), flags


def spans(reasons, counts):
    out = []
    for i in sorted(reasons):
        if out and out[-1]["paragraphs"][1] == i and out[-1]["reason"] == reasons[i]:
            out[-1]["paragraphs"][1] = i + 1
            out[-1]["words"] += counts[i]
        else:
            out.append({"paragraphs": [i, i + 1], "reason": reasons[i], "words": counts[i]})
    return out
