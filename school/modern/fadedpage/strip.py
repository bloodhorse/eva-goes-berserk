import csv, gzip, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "..", "..", "pd2"))
import strip as pd2

IMG_LINE = re.compile(r"^\s*\S+\.(jpe?g|png|gif)\b.*$|^\s*\(?\d+K\)?\s*Full Size\s*$|^\s*Full Size\s*$", re.I | re.M)
CAPTION_EL = re.compile(r"<(div|p|span|figcaption)[^>]*class=\"[^\"]*(caption|illus|figure|fig|image|transnote|tnote)[^\"]*\"[^>]*>.*?</\1>", re.S | re.I)
FIG_EL = re.compile(r"<(figure|figcaption)[^>]*>.*?</\1>", re.S | re.I)
IMG_EL = re.compile(r"<img[^>]*>", re.I)
TN_TEXT = re.compile(r"\[?\s*Transcriber['’]?s? notes?\b.*?(\n\s*\n|\])", re.S | re.I)
BACK = re.compile(r"^\s*(THE END|The End|FINIS|Finis)\.?\s*$", re.M)
BACK_HEAD = re.compile(r"^(BY THE SAME AUTHOR|ALSO BY|OTHER BOOKS BY|BOOKS BY|ABOUT THE AUTHOR|A NOTE ON THE TYPE|COLOPHON|PRINTED IN|NOTES?|GLOSSARY|INDEX|APPENDIX|ACKNOWLEDG(E)?MENTS?)\b", re.I)
FRONT_HEAD = re.compile(r"^(DEDICATION|ACKNOWLEDG(E)?MENTS?|ALSO BY|BY THE SAME AUTHOR|BOOKS BY|FOREWORD|PREFACE|INTRODUCTION|NOTE|AUTHOR['’]S NOTE|CONTENTS)\.?$", re.I)


def pre_html(t):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", t, flags=re.S | re.I)
    t = CAPTION_EL.sub("", t)
    t = FIG_EL.sub("", t)
    t = IMG_EL.sub("", t)
    return t


def post(t):
    t = IMG_LINE.sub("", t)
    t = TN_TEXT.sub("\n\n", t)
    return t


def cut_back(paras):
    n = len(paras)
    total = sum(len(p) for p in paras) or 1
    run = 0
    for i, p in enumerate(paras):
        run += len(p)
        if run / total < 0.9:
            continue
        if BACK.fullmatch(p.strip()) or (len(p) < 60 and BACK_HEAD.match(p.strip())):
            return paras[:i]
    return paras


def cut_front(paras):
    total = sum(len(p) for p in paras) or 1
    run = 0
    for i, p in enumerate(paras[:60]):
        run += len(p)
        if run / total > 0.03:
            break
        if FRONT_HEAD.fullmatch(p.strip()):
            j = i + 1
            while j < len(paras) and j < i + 40 and not (len(paras[j]) < 50 and re.match(r"^(CHAPTER|Chapter|BOOK|Book|PART|Part|[IVXLC]+\.?$|ONE$|1\.?$)", paras[j].strip())):
                j += 1
            if j < len(paras) and j < i + 40:
                return paras[j:]
    return paras


PUB = re.compile(r"All rights reserved|Copyright|MANUFACTURED IN|Printed in|PRINTED IN|Published (in|by)|PUBLISHED BY|Library of Congress|First (published|edition|printing)|FIRST (PUBLISHED|EDITION|PRINTING)|Random House|RANDOM HOUSE|Scribner|SCRIBNER|Harcourt|Chatto|Faber|Heinemann|Knopf|KNOPF|Cape|Gollancz|Doubleday|Macmillan|MACMILLAN|Viking|Harper|Penguin|Inc\.|Ltd\.|Limited|Company|Publishers|PUBLISHERS|Toronto|London:|New York:|NEW YORK", re.S)
NOTE_TAIL = re.compile(r"changed to|corrected|[Tt]ranscriber|e-?[Bb]ook|printed edition|original (text|spelling|book|edition)|hyphenat|spelling|punctuation|inconsisten|typographical|deliberately|errors|have been (moved|retained|silently)|[Pp]age \d+|^\[p\. ?\d+\]|^\.\.\. ", re.S | re.M)


def front_junk(paras):
    total = sum(len(p) for p in paras) or 1
    run = 0
    out = []
    for i, p in enumerate(paras):
        if run / total < 0.03 and len(p) < 600 and PUB.search(p):
            run += len(p)
            continue
        run += len(p)
        out.append(p)
    return out


AD = re.compile(r"\d+s\. ?(\d+d\. )?net|net each|Crown 8vo|\bPrinters?\b|PRINTED (IN|BY)|Printed (in|by)|& CO\.|& Co\.,|Uniform with|NEW NOVELS|BY THE SAME AUTHOR|By the same author|Other books by|Also by|THE END")


def ad_tail(paras):
    total = sum(len(p) for p in paras) or 1
    run = 0
    for i, p in enumerate(paras):
        run += len(p)
        if run / total > 0.95 and len(p) < 400 and AD.search(p):
            return paras[:i]
    return paras


def tail_notes(paras):
    k = len(paras)
    while k > 0 and len(paras) - k < 40 and NOTE_TAIL.search(paras[k - 1]) and len(paras[k - 1]) < 1500:
        k -= 1
    if k < len(paras) and k > len(paras) * 0.8:
        return paras[:k]
    return paras


def cut_front2(paras):
    total = sum(len(p) for p in paras) or 1
    f = None
    run = 0
    for i, p in enumerate(paras[:80]):
        if len(p) >= 200 and "\n" not in p and re.search(r"[a-z]{3,}[.,;!?]", p):
            f = i
            break
        run += len(p)
    if f is None or run / total > 0.05:
        return paras
    keep = []
    for p in paras[:f]:
        s = p.strip()
        if "\n" in s and not re.match(r"^(CHAPTER|Chapter|BOOK|Book|PART|Part)\b", s):
            continue
        if re.match(r"^(To|For|TO|FOR|In memory|IN MEMORY)\b", s) and len(s) < 150:
            continue
        if FRONT_HEAD.fullmatch(s) or BACK_HEAD.match(s) or re.search(r"books by|by the same|also by", s, re.I):
            continue
        keep.append(p)
    return keep + paras[f:]


def clean_fp(raw, ext):
    t = pd2.decode(raw)
    if ext == "html":
        t = pd2.html_to_text(pre_html(t))
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = pd2.cut_fp(t)
    t = post(t)
    t = re.sub(r"=_|_=", "", t)
    t = re.sub(r"\[\*\s*(.*?)\s*\*\]", r"\1", t)
    t = re.sub(r"(?<![A-Za-z0-9])_|_(?![A-Za-z0-9])", "", t)
    t = pd2.clean(t, "noop")
    paras = [p for p in t.split("\n\n") if p.strip() and not IMG_LINE.fullmatch(p.strip())]
    paras = [p for p in paras if re.search(r"[A-Za-z0-9]", p) or re.fullmatch(r"[*.\s]+", p)]
    paras = ad_tail(tail_notes(cut_back(cut_front2(cut_front(front_junk(paras))))))
    return "\n\n".join(paras).strip() + "\n"


def main():
    only = set(sys.argv[1:])
    pd2.cut_pga = lambda t: t
    picks = {r["id"]: r for r in csv.DictReader(open(os.path.join(ROOT, "picks.tsv"), encoding="utf-8"), delimiter="\t")}
    skipped = {}
    log = os.path.join(ROOT, "fetch.log")
    if os.path.exists(log):
        for l in open(log, encoding="utf-8"):
            m = re.match(r"skip (\S+) \[(.*?)\]", l)
            if m:
                skipped[m.group(1)] = m.group(2)
    os.makedirs(os.path.join(ROOT, "text"), exist_ok=True)
    rows = []
    for pid, r in picks.items():
        if only and pid not in only:
            continue
        src = None
        for ext, fn in (("txt", f"{pid}.txt"), ("html", f"{pid}.html.gz")):
            p = os.path.join(ROOT, "raw", "txt", fn)
            if os.path.exists(p):
                src = (ext, p)
        row = {"url": f"https://www.fadedpage.com/showbook.php?pid={pid}", "slug": pid, "title": r["title"], "author": r["author"], "year": r["year"], "kind": "novel", "words": 0, "file": "", "licence_or_basis": "Faded Page (Canadian public domain; may be under copyright elsewhere)", "status": ""}
        if src is None:
            row["status"] = f"declined:tags [{skipped[pid]}]" if pid in skipped else "missing"
            rows.append(row)
            continue
        raw = open(src[1], "rb").read() if src[0] == "txt" else gzip.open(src[1]).read()
        t = clean_fp(raw, src[0])
        if not pd2.english(t):
            row["status"] = "declined:not english"
            rows.append(row)
            continue
        out = os.path.join(ROOT, "text", f"{pid}.txt")
        open(out, "w", encoding="utf-8").write(t)
        row.update(words=pd2.words(t), file=f"text/{pid}.txt", status="ok")
        if re.search(r"stories|tales|collected|case-book|carnival|round up|takes|furthermore|somewhat|take it easy|haunted house|wild body|here lies|long valley|in our time|men without|winner take|sad young|holiday|teeth of|eternal moment|human nature|certain people|brief candles|limbo|armour|white paternoster|rosie plum|left leg|rotting hill|whipoorwill|trouble is|simple art|waiting|smethers|work suspended", r["title"], re.I):
            row["kind"] = "collection"
        rows.append(row)
    if not only:
        with open(os.path.join(ROOT, "ledger.jsonl"), "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    ok = [x for x in rows if x["status"] == "ok"]
    print(len(rows), "rows", len(ok), "ok", sum(x["words"] for x in ok), "words")


if __name__ == "__main__":
    main()
