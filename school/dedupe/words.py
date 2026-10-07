import hashlib
import re
import unicodedata

import numpy as np

NORMALISER_VERSION = 5

ALNUM = r"[^\W_]"
GLUE = "'’‘ʼ＇­​‌‍⁠﻿̀-ͯ"
LINE_HYPHEN = r"[-‐‑]\n[ \t]*(?=[a-z])"
WORD = re.compile(rf"{ALNUM}+(?:(?:[{GLUE}]+|{LINE_HYPHEN}){ALNUM}+)*")
GLUE_RUN = re.compile(rf"[{GLUE}]+|[-‐‑]\n[ \t]*")
PIECE = re.compile(rf"{ALNUM}+")
BLANK_LINE = re.compile(r"\n[ \t\f\v]*(?:\n[ \t\f\v]*)+")
SENTENCE_END = re.compile(r"[.!?…]+[\"'”’)\]]*\s+(?=[\"'“‘(\[]?[A-Z0-9])")
SMALL_WORDS = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}
INNER_HEADINGS = {"chapter", "part", "book", "section", "act", "scene", "epilogue", "prologue", "coda", "interlude",
                  "envoi", "postscript", "afterword", "finale", "one", "two", "three", "four", "five", "six",
                  "seven", "eight", "nine", "ten", "eleven", "twelve", "first", "second", "third", "later",
                  "end", "fin"}
NUMERAL = re.compile(r"[\divxlcdm]+", re.I)
DIGIT = re.compile(r"\d")

FLAG_CONTINUES = 1
FLAG_HEADING = 2

MIX_A = np.uint64(0xBF58476D1CE4E5B9)
MIX_B = np.uint64(0x94D049BB133111EB)
POLY = np.uint64(0x9E3779B97F4A7C15)

_word_cache = {}


def hash32(token):
    return int.from_bytes(hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest(), "little")


def hash64(data):
    return int.from_bytes(hashlib.blake2b(data, digest_size=8).digest(), "little")


def normalise_word(raw):
    joined = GLUE_RUN.sub("", raw)
    folded = unicodedata.normalize("NFKC", joined).casefold()
    bare = "".join(c for c in unicodedata.normalize("NFKD", folded) if unicodedata.category(c) != "Mn")
    return tuple(PIECE.findall(bare))


def word_codes(raw):
    codes = _word_cache.get(raw)
    if codes is None:
        codes = tuple(hash32(t) for t in normalise_word(raw))
        if len(_word_cache) > 1_000_000:
            _word_cache.clear()
        _word_cache[raw] = codes
    return codes


def clean_newlines(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def sentences(paragraph):
    cuts = [m.end() for m in SENTENCE_END.finditer(paragraph)]
    if not cuts:
        return [paragraph]
    edges = [0] + cuts + [len(paragraph)]
    return [paragraph[a:b] for a, b in zip(edges, edges[1:]) if paragraph[a:b].strip()]


def units(text, long_paragraph_words):
    out = []
    for block in BLANK_LINE.split(clean_newlines(text)):
        block = block.strip("\n")
        if not block.strip():
            continue
        if len(block.split()) > long_paragraph_words:
            pieces = sentences(block)
            out.append((pieces[0], False))
            out.extend((p, True) for p in pieces[1:])
        else:
            out.append((block, False))
    return out


def join_units(all_units, keep):
    parts = []
    paragraph = -1
    last_paragraph = None
    for (text, continues), wanted in zip(all_units, keep):
        if not continues:
            paragraph += 1
        if not wanted:
            continue
        if last_paragraph is None:
            parts.append(text.strip() if continues else text.strip("\n"))
        elif paragraph == last_paragraph:
            parts.append(("" if parts[-1].endswith((" ", "\n")) else " ") + text.strip("\n"))
        else:
            parts[-1] = parts[-1].rstrip()
            parts.append("\n\n" + text.strip("\n"))
        last_paragraph = paragraph
    return "".join(parts).rstrip() + "\n" if parts else ""


def heading_shaped(unit_text, word_count, heading_max_words):
    stripped = unit_text.strip()
    if not stripped or "\n" in stripped or word_count == 0 or word_count > heading_max_words:
        return False
    if not (stripped[-1].isalnum() or stripped[-1] in ")?!"):
        return False
    words = [w for w in stripped.split() if any(c.isalnum() for c in w)]
    if not words:
        return False
    bare = [w.strip(".,:;()[]").lower() for w in words]
    if bare[0] in INNER_HEADINGS or (bare[0] == "the" and bare[-1] == "end"):
        return False
    if all(NUMERAL.fullmatch(w) for w in bare):
        return False
    first = next(c for c in words[0] if c.isalnum())
    if not (first.isupper() or first.isdigit()):
        return False
    weighty = [w for w in words if w.lower().strip(".,:;") not in SMALL_WORDS]
    if not weighty:
        return False
    capital = sum(1 for w in weighty if next(c for c in w if c.isalnum()).isupper() or w[0].isdigit())
    return capital >= 0.6 * len(weighty)


def prefix_key(unit_text):
    head = unit_text.split(None, 2)[:2]
    if not head or all(NUMERAL.fullmatch(w.strip(".,:;()[]")) for w in unit_text.split()[:6]):
        return 0
    shape = DIGIT.sub("0", unicodedata.normalize("NFKC", " ".join(head)).casefold())
    return hash64(shape.encode("utf-8")) | 1


def unit_codes(unit_text):
    out = []
    for raw in WORD.findall(unit_text):
        out.extend(word_codes(raw))
    return out


def word_positions(unit_text):
    out = []
    for m in WORD.finditer(unit_text):
        for token in normalise_word(m.group()):
            out.append((token, m.start(), m.end()))
    return out


class Encoded:
    __slots__ = ("codes", "ends", "words", "hashes", "prefixes", "flags")


def encode(text, long_paragraph_words, heading_max_words):
    codes, ends, words, hashes, prefixes, flags = [], [], [], [], [], []
    for unit_text, continues in units(text, long_paragraph_words):
        mine = unit_codes(unit_text)
        codes.extend(mine)
        ends.append(len(codes))
        count = len(unit_text.split())
        words.append(count)
        hashes.append(hash64(np.asarray(mine, dtype="<u4").tobytes()) | 1 if mine else 0)
        prefixes.append(prefix_key(unit_text) if mine else 0)
        flag = FLAG_CONTINUES if continues else 0
        if not continues and heading_shaped(unit_text, count, heading_max_words):
            flag |= FLAG_HEADING
        flags.append(flag)
    enc = Encoded()
    enc.codes = np.asarray(codes, dtype="<u4")
    enc.ends = np.asarray(ends, dtype="<u4")
    enc.words = np.asarray(words, dtype="<u4")
    enc.hashes = np.asarray(hashes, dtype="<u8")
    enc.prefixes = np.asarray(prefixes, dtype="<u8")
    enc.flags = np.asarray(flags, dtype="u1")
    return enc


def shingles(codes, size):
    n = len(codes) - size + 1
    if n <= 0:
        return np.empty(0, dtype=np.uint64)
    wide = codes.astype(np.uint64)
    h = np.zeros(n, dtype=np.uint64)
    with np.errstate(over="ignore"):
        for i in range(size):
            h = h * POLY + wide[i:i + n] + np.uint64(1)
        h ^= h >> np.uint64(30)
        h *= MIX_A
        h ^= h >> np.uint64(27)
        h *= MIX_B
        h ^= h >> np.uint64(31)
    return h


def sampled(unique_hashes, modulus):
    return unique_hashes[unique_hashes % np.uint64(modulus) == 0]
