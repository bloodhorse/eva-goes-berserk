#!/usr/bin/env -S uv run --python 3.12
"""anthology.py — one or more cycles as a single readable page, for the sheets site.

    uv run --python 3.12 anthology.py --cycles 80,81    # writes berserk-c80-c81.html, pushes it
    uv run --python 3.12 anthology.py --cycle 81        # one cycle, same thing
    uv run --python 3.12 anthology.py --cycles 80,81 --no-push

The artifact a short run writes is not worth reading — five forks of thirty-five tokens is the
seed plus six lines. What is worth reading is the **process**: one story per page, the fan
under it, what the reader said and why, the next fan, and at the end the text as it came out.
So the page is a tree, not a transcript, and it explains the experiment at the top, because it
is meant to be opened by someone who has not got the repo in front of them.

Three kinds of line, the same in every picker, so the eye learns the grammar once:

  * **nemo's words** — branches, what the reader said, the why, the margin notes. Ordinary
    text in the document's own pre style, escaped, never cut.
  * **what happened** — `attempt 2 · reshuffled`, `widened to 10`, `→ e`, `taken`. Dim, small,
    monospace, and never louder than the text. The `.plumb` class.
  * **folds** — the explainer, and the document each fan was drawn under.

The machine that resolves an answer into a branch is not a character here: its pick shows as
an arrow to a branch letter and nothing else. No bit counts anywhere — bits are a measure for
the shelf, not for reading.

Built off the ledger and the rooms on the shelf, and it writes nothing back to either. Two
things are not on the ledger and are recomputed: the **lead** — the unfinished line every
branch in a fan is finishing — from the branches' shared parent, and the **settings** the run
really used, from the room's own params and the temperatures stamped on its branches, so the
page describes the run that happened rather than whatever the constants say today.

Env: BERSERK_DIR and the sheets settings, all of them berserk.py's own.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import berserk  # noqa: E402 — same env, same shelf, same skin
from berserk import (CYCLES, DOC_STYLE, PAGES, SHEETS_DIR, SKIN, cycle_forks,  # noqa: E402
                     cycle_pages, ledger_rows, lead_of, load, log, prompt_to, push)

# The anthology's own rules, on top of the sheets skin. One accent — lilac, for the branch the
# walk took — and one dim voice, `.plumb`, for everything the machine did rather than wrote.
EXTRA = """
h1{font-weight:500;font-size:22px;color:#f5c8fe;margin:0 0 10px}
h2{font-weight:500;font-size:18px;color:#eee;margin:26px 0 4px}
h2.cyc{color:#f5c8fe;border-top:1px solid #333;padding-top:22px;margin-top:34px}
h3{font-weight:500;font-size:16px;color:#b9e8c4;margin:18px 0 4px}
.plumb{color:#9cc;font-size:13px;font-family:ui-monospace,Menlo,monospace;margin:3px 0;
  line-height:1.4}
.tree{border-left:2px solid #333;padding-left:12px;margin:10px 0 0}
.fan{margin:0 0 20px}
.card{display:flex;gap:8px;border-left:3px solid #333;padding-left:8px;margin:0 0 12px}
.card.taken{border-left-color:#f5c8fe}
.card .letter{flex:0 0 auto;padding-top:3px}
.card .body{flex:1 1 auto;min-width:0}
.note{margin:5px 0 0;font-style:italic;color:#ddd;white-space:pre-wrap}
.tries{margin:10px 0 0}
details{margin:8px 0} summary{color:#9cc;font-size:13px;cursor:pointer}
/* pre-wrap wraps at spaces and nowhere else, and a base model's document is full of urls
   and forty-character paths — one of those on a phone drags the whole page sideways. */
pre{margin:2px 0;overflow-wrap:anywhere}
/* A beat is the one line on this page nemo did not write: rose, the loom's own colour for a
   posed line, so a reader never mistakes our hand for the model's. It keeps the document's
   pre style because it IS in the document — the branches under it are continuing it. */
pre.beat{color:#f4b6c2}
"""

# Every room this render touched, read once. A page of fifteen fans asks the same room for its
# branches, its leads and its document, and berserk re-renders after every fork — so the cache
# is cleared at the top of `render` rather than kept: a cache that outlived one render would
# show the fork before last.
_ROOMS: dict[str, dict] = {}


# ---- reading the run back off the shelf --------------------------------------------------

def room_of(room: str) -> dict:
    if room not in _ROOMS:
        try:
            _ROOMS[room] = load(room)
        except (OSError, ValueError):
            _ROOMS[room] = {}
    return _ROOMS[room]


def ask_of(cycle: int, picker: str, rows: list[dict]) -> str:
    """The frame line this cycle really ran with. Off the ledger now — the fork row first,
    then the cycle event — and only then the old morning file, which is how cycles 80 and 81
    still name their ask. A cycle walked with `--ask` and no record left would otherwise be
    described by a line it never used, which is the one lie this page must not tell."""
    for r in rows:
        if r.get("ask"):
            return r["ask"]
    ev = cycle_event(cycle)
    if ev.get("ask"):
        return ev["ask"]
    try:
        with open(os.path.join(CYCLES, f"c{cycle:02d}.md"), encoding="utf-8") as f:
            m = re.search(r"^the ask: `(.+)`$", f.read(), re.M)
        if m:
            return m.group(1)
    except OSError:
        pass
    return berserk.FRAMES.get(picker, {}).get("ask", "")


def seed_name(room: str) -> str:
    """The seed a room was made from, off its title. The page row carries it too, but a page
    still being walked has no page row yet and this one must read mid-walk."""
    return (room_of(room).get("title") or "").split("· ")[-1]


def pages_of(cycle: int) -> list[dict]:
    """The rooms of a cycle, in the order they were walked — from the page rows where a page
    has landed, and from the fork rows where it has not. berserk re-renders this page after
    every fork, so the common case is a cycle with one room still mid-walk and no page row
    for it at all."""
    landed = {p["room"]: p for p in cycle_pages(cycle)}
    out, seen = [], set()
    for r in ledger_rows():
        if r.get("cycle") != cycle or r.get("event") is not None or r["room"] in seen:
            continue
        seen.add(r["room"])
        p = landed.get(r["room"])
        if p and p.get("error"):
            continue        # a page that aborted mid-walk is not a walk
        out.append(p or {"room": r["room"], "cycle": cycle, "seed": seed_name(r["room"])})
    return out


def cycle_event(cycle: int) -> dict:
    for r in ledger_rows():
        if r.get("event") == "cycle" and r.get("cycle") == cycle:
            return r
    return {}


def brakes_of(params: dict) -> str:
    """Whether the writing calls ran with a repetition brake, read off the room and not off
    the flag: the page describes the run that happened. Empty when the room is gone, because
    "on" would be a guess dressed as a fact."""
    if not params:
        return ""
    off = (params.get("dry_multiplier") or 0) == 0 and (params.get("repeat_penalty") or 1.0) == 1.0
    return "off" if off else "on"


def settings_of(pages: list[dict], rows: list[dict]) -> dict:
    """What the run actually used, dug out of the room rather than read off the constants at
    the top of berserk.py. A page describing a walk by today's defaults is a page that quietly
    rewrites history the first time somebody changes a default."""
    out = {"pages": len(pages), "fans": 0, "fan": "", "widened": "", "predict": "",
           "temps": "", "xtc": "", "brakes": "", "beats": ""}
    if pages:
        out["fans"] = len(cycle_forks(pages[0]["cycle"], pages[0]["room"]))
        # Which score the run was walked to. Off a page row, and off the cycle event where a
        # page has not landed yet — berserk renders this mid-walk, and the first page of a
        # cycle has no row of its own until it finishes.
        out["beats"] = next((p.get("beats") for p in pages if p.get("beats")),
                            cycle_event(pages[0]["cycle"]).get("beats") or "")
    sizes = sorted({r.get("fan_size") for r in rows if r.get("fan_size")})
    if sizes:
        out["fan"] = str(sizes[0])
        if len(sizes) > 1:
            out["widened"] = f"widened to {sizes[-1]} where nothing resolved"
    s = room_of(pages[0]["room"]) if pages else {}
    if not s:
        return out
    p = s.get("params") or {}
    out["predict"] = p.get("n_predict", "")
    out["brakes"] = brakes_of(p)
    temps = sorted({(n.get("meta") or {}).get("params", {}).get("temperature")
                    for n in s["nodes"].values() if n.get("kind") == "model"} - {None})
    out["temps"] = "–".join(f"{t:g}" for t in (temps[0], temps[-1])) if temps else ""
    if p.get("xtc_probability"):
        out["xtc"] = f"{p['xtc_probability']:g}/{p.get('xtc_threshold', 0):g}"
    return out


def parent_of(room: str, row: dict) -> str:
    """The node every branch in this fan hangs off — the document, as the reader saw it."""
    ids = row.get("order") or []
    s = room_of(room)
    try:
        return s["nodes"][ids[0]]["parent"] or ""
    except (KeyError, IndexError):
        return ""


def lead_for(room: str, row: dict) -> str:
    """The unfinished line the whole fan is finishing. Recomputed and not stored: every branch
    on the row shares a parent, and the document down to that parent is what the reader saw."""
    parent = parent_of(room, row)
    return lead_of(doc_to(room, parent)) if parent else ""


def doc_to(room: str, nid: str) -> str:
    try:
        return prompt_to(room_of(room), nid) if nid else ""
    except (KeyError, ValueError):
        return ""


def doc_final(room: str) -> str:
    """The story, as it came out: root down to the last node the walk took. The closing fan is
    kept and never taken, so `current` is exactly the document that fan was drawn under — and
    mid-walk it is the last branch taken, which is the same answer for a page still going."""
    s = room_of(room)
    return doc_to(room, s.get("current", "")) if s else ""


def branch_texts(room: str, ids: list[str]) -> dict[str, str]:
    s = room_of(room)
    if not s:
        return {}
    return {i: (s["nodes"][i]["text"] if i in s["nodes"] else "") for i in ids}


def seed_of(room: str) -> str:
    s = room_of(room)
    try:
        return s["nodes"][s["root"]]["text"]
    except (KeyError, TypeError):
        return ""


# ---- the three kinds of line -------------------------------------------------------------

def plumb(text: str) -> str:
    """What the machine did, never what it wrote. Dim, small, monospace — so that the eye
    walking down the page skips it unless it is looking for it."""
    return f'<div class="plumb">{html.escape(text)}</div>'


def pre(text: str) -> str:
    """Nemo's words, whole and escaped — never cut. The branches nobody took are the whole
    point of this page, and an 80-character opening of one is not evidence of anything."""
    return f'<pre style="{DOC_STYLE}">{html.escape(text)}</pre>'


def beat_pre(text: str) -> str:
    """Our line in the document, marked as ours. Not `plumb` — a beat is text the model read
    and answered, not a note about the machinery — and not plain `pre` either, or the page
    would be quietly claiming nemo wrote it."""
    return f'<pre class="beat" style="{DOC_STYLE}">{html.escape(text)}</pre>'


def fold(summary: str, body: str) -> str:
    return f"<details><summary>{html.escape(summary)}</summary>{body}</details>"


def letter(i: int) -> str:
    """a, b, c … aa. The branch's name on this page: the reader's order, not the fan's, and
    short enough to sit in the margin of a phone."""
    out, i = "", i + 1
    while i > 0:
        i, r = divmod(i - 1, 26)
        out = chr(97 + r) + out
    return out or "?"


# ---- the page ----------------------------------------------------------------------------

def numbers(cycle: int, rows: list[dict]) -> str:
    ev = cycle_event(cycle)
    matched = ev.get("matches")
    if matched is None:
        matched = sum(1 for r in rows if r.get("outcome") == "match")
    rnd = ev.get("random")
    if rnd is None:
        rnd = sum(1 for r in rows if r.get("outcome") == "random")
    return f"{len(rows)} fans · {matched} resolved · {rnd} random"


PICKER_PROSE = {
    "about": ("<strong>about</strong> — the reader is shown the whole fan at once, every branch "
              "as a bare paragraph in a shuffled order, and one line under it asking what the "
              "one that scared it was about. What comes back is a description rather than a "
              "piece of the text, so a second, blind reader — given the description and the "
              "branch openings, never the document — is asked which branch was being "
              "described."),
    "margin": ("<strong>margin</strong> — nothing reads the fan. Each branch gets its own short "
               "note, written with that branch alone in front of the model, under the line "
               "<em>reading this, what scared me was</em>. The notes are then read by "
               "themselves, without the branches and without the document, and the most "
               "pronounced reaction wins; the branch under that note is the one the walk "
               "takes."),
    "random": ("<strong>random</strong> — nobody is asked anything. The fan is drawn and one "
               "branch of it is taken by lot, every other branch kept beside it here. It is "
               "the control: whatever the reading pickers are doing, this is what the page "
               "looks like when nothing is choosing at all."),
    "quote": ("<strong>quote</strong> — the reader is shown the whole fan and asked to quote back "
              "the branch that scared it. It is the only form whose answer can be checked "
              "against the text with no judgement in the loop, so the quotation is matched to "
              "a branch letter for letter."),
}

INTRO = (
    "<p>Nemo 12b base is a pretrained model that was never taught to answer anybody: it only "
    "continues documents. berserk gives it a found document as a seed and takes a fan of "
    "continuations at every fork — and then asks the model itself which of them to keep going "
    "with. <strong>No person picks a branch anywhere on this page.</strong></p>"
    "<p>Two kinds of line, and they never mix: ordinary text is nemo's own words — branches, "
    "what it said about them, the notes in the margin, and nothing of it is ever cut. The dim "
    "monospace is the machinery saying what it did — which attempt this was, that the fan was "
    "widened, which branch an answer resolved to. The branch the walk took carries the accent "
    "line and the word <em>taken</em>.</p>")


def page_title(cycles: list[int], by_cycle: dict) -> str:
    if len(cycles) == 1:
        c = cycles[0]
        return f"berserk · cycle {c:02d} · {by_cycle[c]['picker']}"
    names = " and ".join(f"{c:02d}" for c in cycles) if len(cycles) < 3 \
        else ", ".join(f"{c:02d}" for c in cycles)
    return f"berserk · cycles {names}"


def head(cycles: list[int], by_cycle: dict) -> list[str]:
    """The top of the page: the title, one line of settings per cycle with the ask verbatim,
    and the explainer folded away — the settings are what a reader coming back to compare two
    runs needs in view, the prose is what a first-time reader opens once."""
    out = [f"<h1>{html.escape(page_title(cycles, by_cycle))}</h1>"]
    for c in cycles:
        d = by_cycle[c]
        s = d["settings"]
        bits = [f"{s['pages']} pages",
                f"{s['fans']} fans" if s["fans"] else "",
                (f"{s['fan']} branches" + (f" ({s['widened']})" if s["widened"] else ""))
                if s["fan"] else "",
                f"{s['predict']} tokens" if s["predict"] else "",
                f"t {s['temps']}" if s["temps"] else "",
                f"xtc {s['xtc']}" if s["xtc"] else "",
                f"brakes {s['brakes']}" if s["brakes"] else "",
                f"beats {s['beats']}" if s["beats"] else ""]
        line = " · ".join(b for b in bits if b)
        if len(cycles) > 1:
            line = f"cycle {c:02d} · {d['picker']} — " + line
        # No ask line at all under a picker that asks nothing — an empty "asked with:" would
        # read as a frame line that went missing rather than as a run that had none.
        asked = f'asked with: {html.escape(d["ask"])}<br>' if d["ask"] else ""
        out.append(f'<div class="plumb">{html.escape(line)}<br>{asked}'
                   f'{html.escape(numbers(c, d["rows"]))}</div>')

    pickers = []
    for c in cycles:
        p = by_cycle[c]["picker"]
        if p not in pickers:
            pickers.append(p)
    out.append(fold("what is this",
                    INTRO + "".join(f"<p>{PICKER_PROSE[p]}</p>"
                                    for p in pickers if p in PICKER_PROSE)))
    return out


def fallback_tries(row: dict, took_at: int | None) -> list[dict]:
    """A fork row written before `tries` existed, read back as best the row allows: every
    entry of `wished` was an ask that named nothing in the fan, and `quote` is the ask that
    landed. The why is only on the row for the last one, so the misses show without it —
    which is the whole reason berserk records the tries now.

    The widened ask is the last one made, so the mark goes on the last try. With an ask that
    came back empty (counted in `attempts`, never in `wished`) that is a guess; it is the only
    guess on this page, and it costs a label, not a branch.
    """
    tries = [{"said": w, "why": "", "hit": None, "widened": False}
             for w in (row.get("wished") or []) if (w or "").strip()]
    said = (row.get("quote") or "").strip()
    if said and row.get("outcome") == "match":
        tries.append({"said": said, "why": row.get("why") or "", "hit": took_at,
                      "widened": False})
    if row.get("widened") and tries:
        tries[-1]["widened"] = True
    return tries


def tries_block(row: dict, picker: str, took_at: int | None) -> list[str]:
    """Every ask this fan cost, in the order they happened. The reader of a page wants to see
    the machine miss: three attempts that named nothing, a fan widened, and then either an
    arrow or a coin toss."""
    tries = row.get("tries")
    if tries is None:
        tries = fallback_tries(row, took_at)
    out, widened_marked = [], False
    for k, t in enumerate(tries, 1):
        if t.get("widened") and not widened_marked:
            widened_marked = True
            out.append(plumb(f"widened to {row.get('fan_size')}"))
        out.append(plumb(f"attempt {k}" + (" · reshuffled" if k > 1 else "")))
        said = (t.get("said") or "").strip()
        if said:
            out.append(plumb("said"))
            out.append(pre(f"“{said}”" if picker == "quote" else said))
        else:
            out.append(plumb("said nothing"))
        why = (t.get("why") or "").strip()
        if why:
            out.append(plumb("why"))
            out.append(pre(why))
        hit = t.get("hit")
        out.append(plumb(f"→ {letter(hit)}" if isinstance(hit, int) else "not in the fan"))
    if row.get("outcome") == "random":
        # Nothing the reader said was in the fan. The walk went on anyway, and says so.
        out.append(plumb("random → " + (letter(took_at) if took_at is not None else "?")))
    return ['<div class="tries">'] + out + ["</div>"] if out else []


def fan_block(room: str, row: dict, picker: str, first: bool) -> list[str]:
    """One fan: the document it was drawn under, the branches lettered as the reader saw
    them, and then what was said about them."""
    ids = row.get("order") or []
    texts = branch_texts(room, ids)
    notes = row.get("notes") or []
    took = row.get("pick") or (row.get("keep") or [None])[0]
    took_at = ids.index(took) if took in ids else None
    closing = bool(row.get("closing"))

    out = ['<div class="fan">',
           f"<h3>fan {row.get('fork')}{' · closing' if closing else ''}</h3>"]
    if not first:
        # Where the walk had got to when this fan was drawn. Folded, because it is the same
        # text as the fan above plus one branch — open, it would be the page.
        before = doc_to(room, parent_of(room, row))
        if before:
            out.append(fold("document so far", pre(before)))
    beat = (row.get("beat") or "").strip()
    if beat:
        # Above the branches and below the fold, which is where it sits in the document: the
        # fan was drawn to continue THIS line, and a reader who has to open a fold to find
        # out what the branches are answering is reading the run backwards.
        out.append(plumb("beat"))
        out.append(beat_pre(beat))
    lead = lead_for(room, row)
    if lead:
        # Short, and the reader needs it: without it a branch that opens on a comma reads as
        # damage rather than as the end of a sentence somebody else started.
        out.append(plumb(f"every branch finishes: …{lead}"))

    for i, nid in enumerate(ids):
        taken = nid == took
        out.append(f'<div class="card{" taken" if taken else ""}">')
        out.append(f'<div class="letter plumb">{letter(i)}</div>')
        out.append('<div class="body">')
        text = texts.get(nid, "")
        # An empty branch is one dim line and not a paragraph: a base model standing on a
        # licence footer answers with nothing at all, and printing that nothing as prose was
        # half of what made this page unreadable.
        out.append(pre(text) if text.strip() else plumb("(empty)"))
        if picker == "margin":
            note = (notes[i] if i < len(notes) else "").strip()
            out.append(f'<p class="note">~ {html.escape(note)}</p>' if note
                       else '<p class="note">~ (nothing written)</p>')
        if taken:
            out.append(plumb("kept" if closing else "taken"))
        out.append("</div></div>")

    if picker == "margin":
        out.append(plumb(("random → " if row.get("outcome") == "random" else "→ ")
                         + (letter(took_at) if took_at is not None else "?")))
    else:
        out += tries_block(row, picker, took_at)
    out.append("</div>")
    return out


def page_block(cycle: int, p: dict, picker: str, walking: bool) -> list[str]:
    room = p["room"]
    short = room.rsplit("-", 1)[-1] if "-" in room else room
    out = [f"<h2>{html.escape(short)} · {html.escape(str(p.get('seed') or seed_name(room)))}"
           "</h2>",
           f'<div class="plumb"><a href="https://eva.x/api/artifact/text?name='
           f'{html.escape(room)}">the walk as one document at eva.x</a> · '
           # The same record drawn by the loom's own tree screen — the fans whole, the
           # attempts under them, on the machine where the rooms actually live.
           f'<a href="https://eva.x/#tree={html.escape(room)}">the tree at eva.x</a></div>']
    seed = seed_of(room)
    if seed:
        # Open, once, above the tree: the first fan finishes this text mid-sentence, so a
        # folded seed makes the first branch unreadable.
        out.append(pre(seed))

    out.append('<div class="tree">')
    rows = cycle_forks(cycle, room)
    for i, row in enumerate(rows):
        out += fan_block(room, row, picker, first=(i == 0))
    if walking:
        out.append(plumb("walking… this page is rewritten after every fork"))
    out.append("</div>")

    doc = doc_final(room)
    if doc:
        out += ["<h3>the text as it came out</h3>", pre(doc)]
    return out


def cycle_block(cycle: int, d: dict, walking: bool = False, multi: bool = False) -> list[str]:
    out = []
    if multi:
        # One page holding two cycles needs a seam; one cycle has the h1 already.
        out.append(f'<h2 class="cyc">cycle {cycle:02d} · {html.escape(d["picker"])}</h2>')
    for p in d["pages"]:
        out += page_block(cycle, p, d["picker"], walking and p is d["pages"][-1])
    out.append(f'<div class="plumb">{html.escape(numbers(cycle, d["rows"]))} · '
               f'{html.escape(time.strftime("%b %-d, %Y %H:%M"))}</div>')
    return out


def render(cycles: list[int], walking: bool = False) -> str:
    """The whole page. `walking` says the run is still going, which puts one line under the
    last fan — berserk re-renders this after every fork, and a reader who opens it mid-run
    has to be able to tell "this is all there was" from "this is all there is yet"."""
    _ROOMS.clear()
    by_cycle = {}
    for c in cycles:
        pages = pages_of(c)
        rows = [r for p in pages for r in cycle_forks(c, p["room"])]
        if not rows:
            raise SystemExit(f"cycle {c:02d}: no forks on the ledger")
        picker = (rows[0].get("picker") or "quote")
        by_cycle[c] = {"pages": pages, "rows": rows, "picker": picker,
                       "ask": ask_of(c, picker, rows), "settings": settings_of(pages, rows)}

    title = page_title(cycles, by_cycle)
    out = ["<!doctype html>", '<html lang="en"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           f"<title>{html.escape(title)}</title>",
           f"<style>\n{SKIN}\n{EXTRA}</style>", "</head><body>"]
    out += head(cycles, by_cycle)
    for i, c in enumerate(cycles):
        out += cycle_block(c, by_cycle[c], walking and i == len(cycles) - 1,
                           multi=len(cycles) > 1)
    out += ["</body></html>", ""]
    return "\n".join(out)


def page_name(cycles: list[int]) -> str:
    return "berserk-" + "-".join(f"c{c:02d}" for c in cycles) + ".html"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cycles", help="one or more, comma separated: 80,81")
    ap.add_argument("--cycle", type=int, help="the same thing, for one")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    raw = a.cycles or (str(a.cycle) if a.cycle is not None else "")
    try:
        cycles = [int(x) for x in raw.split(",") if x.strip()]
    except ValueError:
        raise SystemExit(f"--cycles wants numbers, got {raw!r}")
    if not cycles:
        raise SystemExit("pass --cycles 80,81 or --cycle 81")

    os.makedirs(PAGES, exist_ok=True)
    name = page_name(cycles)
    path = os.path.join(PAGES, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(cycles))
    log(f"anthology written: {path}")
    if not a.no_push:
        log(f"pushed: {push(path, f'{SHEETS_DIR}/berserk/{name}')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
