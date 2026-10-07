import re
from itertools import accumulate

import shape

APPARATUS_REASONS = (
    (re.compile(r"summation", re.I), "summation"),
    (re.compile(r"honou?rable", re.I), "honorable-mentions"),
    (re.compile(r"copyright|permissions?|this page constitutes|credits|publication history", re.I), "copyright"),
    (re.compile(r"acknowledge?ments?", re.I), "acknowledgments"),
    (re.compile(r"contents", re.I), "contents"),
    (re.compile(r"introduction|foreword|foreweird|preface|afterword|afterweird|editor|note|word", re.I), "introduction"),
    (re.compile(r"about the|contributors?|in memoriam", re.I), "contributors"),
    (re.compile(r"also|books by|anthologies|titles|praise", re.I), "also-by"),
    (re.compile(r"reading|bibliography|index", re.I), "bibliography"),
    (re.compile(r"dedication", re.I), "dedication"),
)
LIST_REASONS = ("honorable-mentions", "copyright", "acknowledgments", "contents", "also-by", "dedication")
TITLE_AUTHOR = re.compile(r"^(?P<a>.{2,90}?)\s*(?::|\s[-–—]\s|\bby\b)\s*(?P<b>.{2,60})$")


class Book:
    def __init__(self, cfg, paras):
        self.cfg = cfg
        self.paras = paras
        self.n = len(paras)
        limit = cfg.dedupe.structure.heading_max_words
        P = cfg.patterns
        self.counts = [shape.count(p) for p in paras]
        self.heading = [shape.is_heading(p, limit) for p in paras]
        self.words = [0] + list(accumulate(self.counts))
        self.meta = [0] + list(accumulate(sum(1 for _ in P["meta_words"].finditer(p)) for p in paras))
        self.biblio = [0] + list(accumulate(sum(1 for _ in P["biblio_words"].finditer(p)) for p in paras))
        self.narrative = [0] + list(accumulate(sum(1 for _ in P["narrative_words"].finditer(p)) for p in paras))
        self.quoted = [0] + list(accumulate(1 if shape.QUOTE.search(p) else 0 for p in paras))
        self.speech = [0] + list(accumulate(1 if shape.OPEN_QUOTE.match(p) else 0 for p in paras))
        self.listed = [0] + list(accumulate(1 if self.list_line(p) else 0 for p in paras))

    def list_line(self, paragraph):
        lines = [line for line in paragraph.split("\n") if line.strip()]
        return bool(lines) and all(self.cfg.patterns["list_line"].search(line.strip()) for line in lines)

    def rates(self, a, b):
        total = self.words[b] - self.words[a]
        scale = 1000.0 / total if total else 0.0
        return {
            "words": total,
            "meta": round((self.meta[b] - self.meta[a]) * scale, 2),
            "biblio": round((self.biblio[b] - self.biblio[a]) * scale, 2),
            "narrative": round((self.narrative[b] - self.narrative[a]) * scale, 2),
            "quote_share": round((self.quoted[b] - self.quoted[a]) / (b - a), 3) if b > a else 0.0,
            "speech_share": round((self.speech[b] - self.speech[a]) / (b - a), 3) if b > a else 0.0,
            "list_share": round((self.listed[b] - self.listed[a]) / (b - a), 3) if b > a else 0.0,
        }

    def narrative_stretch(self, a, b):
        B = self.cfg.books
        N = self.cfg.nonfiction
        return (b > a and self.words[b] - self.words[a] >= B.apparatus_window_words
                and self._narrative(self.rates(a, b), N, B))

    @staticmethod
    def _narrative(r, N, B):
        return (r["narrative"] >= N.narrative_high and r["meta"] + r["biblio"] < B.editorial_meta_min
                and r["speech_share"] >= B.narrative_speech_min)

    def editorial(self, a, b, front=False):
        B = self.cfg.books
        N = self.cfg.nonfiction
        r = self.rates(a, b)
        if r["words"] < B.editorial_short_words:
            return False, r
        if r["words"] < B.editorial_min_words:
            return (r["meta"] + r["biblio"] >= B.editorial_short_meta_min and r["speech_share"] == 0
                    and r["narrative"] < B.editorial_narrative_max), r
        if r["list_share"] >= B.list_line_share_min and b - a >= 4:
            return True, r
        floor = B.editorial_meta_min if front else B.editorial_inner_meta_min
        return (r["meta"] + r["biblio"] >= floor and r["narrative"] < B.editorial_narrative_max
                and r["speech_share"] < N.speech_share_high), r


def first_line(paragraph):
    return paragraph.strip().split("\n")[0].strip()


def ledger_starts(cfg, book, record):
    B = cfg.books
    found = {}
    position = -1
    for section in (record or {}).get("sections_kept") or []:
        start = section.get("start") or ""
        whole = shape.squash(start).casefold()[:B.start_probe_chars]
        line = shape.squash(first_line(start)).casefold()[:B.start_probe_chars] if start.strip() else ""
        if len(whole) < B.start_min_chars:
            continue
        for i in range(position + 1, book.n):
            mine = shape.squash(book.paras[i]).casefold()[:B.start_probe_chars]
            mine_line = shape.squash(first_line(book.paras[i])).casefold()[:B.start_probe_chars]
            if mine == whole or (len(line) >= B.start_min_chars and mine_line == line) \
                    or (len(mine) >= 24 and whole.startswith(mine) and len(whole) < B.start_probe_chars):
                found[i] = shape.squash(first_line(start))[:80]
                position = i
                break
    return found


def heading_run(book, i, limit):
    j = i
    while j < book.n and book.heading[j] and j - i < limit + 1:
        j += 1
    return j


def loose_heading(book, i, limit):
    paragraph = book.paras[i].strip()
    return (book.heading[i] or (book.counts[i] <= limit and paragraph.count("\n") <= 2
                                and paragraph[-1:] not in ".!?…”\"’'" and not shape.OPEN_QUOTE.match(paragraph)))


def names_in(cfg, lines):
    out = []
    for line in lines:
        line = line.strip()
        bare = re.sub(r"^\W*by\s+", "", line, flags=re.I)
        if shape.name_shaped(bare, cfg.books.name_max_tokens):
            out.append(bare)
            continue
        split = TITLE_AUTHOR.match(line)
        if split:
            for part in (split.group("b"), split.group("a")):
                if shape.name_shaped(part, cfg.books.name_max_tokens):
                    out.append(part)
                    break
    return out


def apparatus_reason(title):
    for pattern, reason in APPARATUS_REASONS:
        if pattern.search(title):
            return reason
    return "apparatus"


def title_key(line):
    return re.sub(r"[\W_]+", " ", line.casefold()).strip()


def headnote(cfg, book, start, stop, surnames, head_lines):
    B = cfg.books
    limit = min(stop, start + B.headnote_max_paragraphs)
    keys = {title_key(line) for line in head_lines if len(title_key(line)) >= 4}
    spent = 0
    for j in range(start, min(stop, start + 2 * B.headnote_max_paragraphs)):
        if book.heading[j] and j > start and any(title_key(line) in keys for line in book.paras[j].split("\n")):
            if not any(shape.OPEN_QUOTE.match(book.paras[i]) for i in range(start, j)):
                return j
            break
        spent += book.counts[j]
        if spent > 2 * B.headnote_max_words:
            break
    end = start
    chain = True
    spent = 0
    for j in range(start, limit):
        if book.heading[j] and book.counts[j] <= 12:
            break
        if spent + book.counts[j] > B.headnote_max_words:
            break
        named, other, presenting = shape.headnote_parts(book.paras[j], cfg, surnames)
        if other < 0:
            break
        spent += book.counts[j]
        qualifies = (named and other >= B.headnote_named_score) or other >= B.headnote_min_score
        follows = chain and end > start and (presenting or (named and other >= 1))
        if (qualifies and (chain or named)) or follows:
            end = j + 1
            chain = True
        elif book.counts[j] >= 8:
            chain = False
    return end


def tail_notes(cfg, book, start, stop, surnames):
    P = cfg.patterns
    j = stop
    reasons = {}
    while j > start and stop - j < 4:
        p = book.paras[j - 1]
        if shape.bio_score(p, cfg, surnames) >= cfg.edges.bio_min_score + 1:
            reasons[j - 1] = "author-bio"
        elif book.counts[j - 1] <= 120 and P["credit"].search(first_line(p)):
            reasons[j - 1] = "copyright"
        else:
            break
        j -= 1
    return j, reasons


def plan_book(cfg, doc, paras, record):
    B = cfg.books
    P = cfg.patterns
    book = Book(cfg, paras)
    n = book.n
    limit = cfg.dedupe.structure.heading_max_words
    keep_essays = bool(cfg.book(doc.slug).get("keep_essays", False))
    flags = []

    bounds = {}
    for i, title in ledger_starts(cfg, book, record).items():
        bounds[i] = ("ledger", title)
    i = 0
    while i < n:
        line = first_line(paras[i])
        if book.counts[i] <= 14 and P["apparatus_titles"].search(line) and (book.heading[i] or book.counts[i] <= 6):
            bounds[i] = ("apparatus", shape.squash(paras[i])[:80])
            i += 1
            continue
        if book.heading[i] and (i == 0 or not book.heading[i - 1]):
            j = heading_run(book, i, B.heading_run_max)
            if j - i > B.heading_run_max:
                k = j
                while k < n and book.heading[k]:
                    k += 1
                if i not in bounds:
                    bounds[i] = ("contents", shape.squash(paras[i])[:80])
                bounds.setdefault(k, ("after-contents", ""))
                i = k
                continue
            if i not in bounds and j < n:
                lines = [line for p in paras[i:j] for line in p.split("\n") if line.strip()]
                surnames = shape.surnames(names_in(cfg, lines))
                named, other, _ = shape.headnote_parts(paras[j], cfg, surnames)
                if named and other >= 2:
                    bounds[i] = ("heading", shape.squash(" / ".join(lines))[:80])
            i = j
            continue
        i += 1
    bounds.pop(n, None)
    if 0 not in bounds:
        bounds[0] = ("start", "")
    order = sorted(bounds)

    reasons = {}
    sections = []
    first_story_seen = False
    for k, a in enumerate(order):
        b = order[k + 1] if k + 1 < len(order) else n
        how, title = bounds[a]
        j = heading_run(book, a, B.heading_run_max) if book.heading[a] else a
        if how == "ledger":
            while j < b and j - a < B.heading_run_max and loose_heading(book, j, limit):
                j += 1
        j = min(j, b)
        head_lines = [line for p in paras[a:j] for line in p.split("\n") if line.strip()]
        if how == "ledger" and not head_lines:
            head_lines = []
        names = names_in(cfg, head_lines)
        if how == "ledger":
            names += names_in(cfg, [title])
        surnames = shape.surnames(names)
        label = title or shape.squash(" / ".join(head_lines))[:80] or shape.squash(paras[a])[:60]
        section = {"paragraphs": [a, b], "title": label, "found_by": how, "words": book.words[b] - book.words[a]}
        mine = {}

        reason = None
        if how in ("apparatus", "contents"):
            reason = "contents" if how == "contents" else apparatus_reason(first_line(paras[a]))
            if reason == "introduction" and first_story_seen:
                inner_editorial, _ = book.editorial(j, b, True)
                if not inner_editorial:
                    how = "inner-heading"
                    section["found_by"] = how
        if how in ("apparatus", "contents"):
            end = b
            window = B.apparatus_window_paragraphs
            if reason not in ("honorable-mentions",):
                for c in range(j, max(j, b - window + 1)):
                    if book.narrative_stretch(c, c + window):
                        end = c
                        while end > j and (book.meta[end] - book.meta[end - 1]) + (book.biblio[end] - book.biblio[end - 1]) == 0:
                            end -= 1
                        flags.append({"signal": "apparatus-ends-at-narrative",
                                      "value": f"{label[:40]}: paragraph {end} of {a}–{b}", "weight": 0})
                        break
            kept = keep_essays and reason not in LIST_REASONS
            section.update(kind="nonfiction-kept" if kept else "apparatus", reason=reason)
            if end < b:
                section["paragraphs"] = [a, end]
                section["words"] = book.words[end] - book.words[a]
            if not kept:
                for i in range(a, end):
                    mine[i] = reason
            section["words_cut"] = sum(book.counts[i] for i in mine)
            sections.append(section)
            reasons.update(mine)
            if end < b:
                tail = {"paragraphs": [end, b], "title": shape.squash(paras[end])[:60], "found_by": "narrative",
                        "words": book.words[b] - book.words[end], "kind": "story", "words_cut": 0}
                sections.append(tail)
                first_story_seen = True
            continue

        body_start = j
        note_end = headnote(cfg, book, body_start, b, surnames, head_lines)
        titled = reason == "introduction"
        is_editorial, rates = book.editorial(note_end, b, not first_story_seen or titled)
        whole_editorial, whole_rates = book.editorial(body_start, b, not first_story_seen or titled)
        if how == "heading" and first_story_seen:
            whole_editorial = False
        if whole_editorial and (is_editorial or book.words[b] - book.words[note_end] < B.story_min_words):
            reason = "introduction" if not first_story_seen else "editor-note"
            if whole_rates["list_share"] >= B.list_line_share_min:
                reason = "contents" if not first_story_seen else "list"
            if how == "start" and whole_rates["words"] > B.front_matter_max_words and reason != "contents":
                section.update(kind="story", reason=None, words_cut=0)
                flags.append({"signal": "long-untitled-front-matter", "value": whole_rates["words"], "weight": 0})
                sections.append(section)
                first_story_seen = True
                continue
            kept = keep_essays and reason not in ("contents", "list")
            section.update(kind="nonfiction-kept" if kept else "editorial", reason=reason,
                           rates={k: whole_rates[k] for k in ("meta", "biblio", "narrative", "quote_share")})
            if not kept:
                for i in range(a, b):
                    mine[i] = reason
            section["words_cut"] = sum(book.counts[i] for i in mine)
            sections.append(section)
            reasons.update(mine)
            continue

        note = {}
        if note_end > body_start:
            for i in range(body_start, note_end):
                note[i] = "editor-note"
        tail_start, tail = tail_notes(cfg, book, note_end, b, surnames)
        body_words = book.words[tail_start] - book.words[note_end]
        if (note or tail) and body_words <= B.orphan_max_words:
            for i in range(a, b):
                mine[i] = note.get(i) or tail.get(i) or ("editor-note" if i >= body_start else "orphan-heading")
            if keep_essays:
                mine = {}
                section.update(kind="nonfiction-kept", reason="editor-note", words_cut=0)
            else:
                section.update(kind="orphan", reason="a heading and its note, the story gone",
                               words_cut=sum(book.counts[i] for i in mine))
            sections.append(section)
            reasons.update(mine)
            continue
        if not keep_essays:
            mine.update(note)
        mine.update(tail)
        section.update(kind="story" if body_words >= B.story_min_words else "fragment",
                       words_cut=sum(book.counts[i] for i in mine))
        if note:
            section["headnote_words"] = sum(book.counts[i] for i in note)
            if keep_essays:
                section["headnote_kept"] = True
        if body_words >= B.story_min_words:
            first_story_seen = True
        sections.append(section)
        reasons.update(mine)

    if not keep_essays:
        stories = [k for k, s in enumerate(sections) if s["kind"] == "story"]
        if stories:
            for k, s in enumerate(sections):
                if s["kind"] != "fragment" or stories[0] < k < stories[-1]:
                    continue
                a, b = s["paragraphs"]
                why = "front-matter" if k < stories[0] else "back-matter"
                for i in range(a, b):
                    reasons.setdefault(i, why)
                s.update(kind="apparatus", reason=why, words_cut=s["words"])
    return reasons, sections, flags, book.counts
