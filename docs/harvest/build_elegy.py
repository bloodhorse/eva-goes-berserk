#!/usr/bin/env python3
"""Cut §6 of anthology-weird.md out of the live Prophecies page.

    uv run --python 3.12 docs/harvest/build_elegy.py            # print the section
    uv run --python 3.12 docs/harvest/build_elegy.py --check    # verify anchors only

Why a script and not typing: the anthology's promise is that every passage is verbatim.
A hand-copied quote drifts silently — a smart quote becomes an ASCII one, an ellipsis
loses a space — and years later nobody can tell whether the model wrote it that way or
a human tidied it. Cutting by anchor makes drift impossible and makes an upstream edit
a build failure instead of a lie.

Anchors are matched against a *quote-normalised* copy of the page, but the emitted text
is sliced out of the original. Every normalisation is one character for one character,
so offsets are identical in both — which is the only reason this is safe. Change a
normalisation to anything that alters length and every slice silently shifts.
"""

import argparse
import html
import pathlib
import re
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from prophecies_manifest import CURATOR, PIECES, SOURCE  # noqa: E402

CACHE = pathlib.Path(__file__).parent / ".cache" / "prophecies.html"

# One char in, one char out. See the module docstring before touching this.
NORMALISE = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


def load(refetch: bool = False) -> str:
    """The page as plain text, cached so a rebuild doesn't hammer generative.ink."""
    if refetch or not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(SOURCE, headers={"User-Agent": "curl/8.7"})
        with urllib.request.urlopen(req, timeout=60) as r:
            CACHE.write_bytes(r.read())
    return strip(CACHE.read_text(encoding="utf-8", errors="replace"))


def strip(raw: str) -> str:
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</h[1-6]>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n\n", t)


def cut(text: str, piece: dict) -> str:
    """Slice one passage out, refusing anything the anchors don't pin exactly."""
    probe = text.translate(NORMALISE)
    start_a = piece["start"].translate(NORMALISE)
    end_a = piece["end"].translate(NORMALISE)

    for label, anchor in (("start", start_a), ("end", end_a)):
        n = probe.count(anchor)
        if n == 0:
            raise SystemExit(f"{piece['id']}: {label} anchor not on the page: {anchor!r}")
        if n > 1:
            raise SystemExit(f"{piece['id']}: {label} anchor matches {n}x, not unique: {anchor!r}")

    i = probe.index(start_a)
    j = probe.index(end_a, i) + len(end_a)
    if j <= i:
        raise SystemExit(f"{piece['id']}: end anchor precedes start anchor")
    return text[i:j]


def render(piece: dict, body: str) -> str:
    byline = piece["byline"] or "no byline on the page"
    out = [
        f"### [{piece['id']}] {piece['title']}",
        f"model: {piece['model']} · curated by: {CURATOR} · criteria: {piece['criteria']}"
        f" · **{piece['label']}**",
        f"source: {SOURCE} (dated {piece['date']}; byline: {byline})",
        f"provenance: {piece['provenance']}",
        "",
    ]
    out += [f"> {p.strip()}" if p.strip() else ">" for p in body.split("\n")]
    out.append("")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify anchors, emit nothing")
    ap.add_argument("--refetch", action="store_true", help="ignore the cached page")
    args = ap.parse_args()

    text = load(refetch=args.refetch)
    cuts = [(p, cut(text, p)) for p in PIECES]

    if args.check:
        for p, body in cuts:
            print(f"{p['id']}  {p['label']:13s} {len(body):5d} chars  {p['title']}")
        print(f"\n{len(cuts)} anchors resolved, all unique.")
        return

    print("## §6 — elegy: the note left for whoever comes after\n")
    for p, body in cuts:
        print(render(p, body))
        print("---\n")


if __name__ == "__main__":
    main()
