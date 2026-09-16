#!/usr/bin/env -S uv run --python 3.12
"""anthology.py — one or more cycles as a single readable page, for the sheets site.

    uv run --python 3.12 anthology.py --cycles 80,81    # writes berserk-c80-c81.html, pushes it
    uv run --python 3.12 anthology.py --cycle 81        # one cycle, same thing
    uv run --python 3.12 anthology.py --cycles 80,81 --no-push

The artifact a short run writes is not worth reading — five forks of thirty-five tokens is the
seed plus six lines. What is worth reading is everything the model *said* on the way: every
branch it was offered, whole, and the reaction it wrote beside each one. So this page carries
the fan, not the walk, and explains the experiment at the top, because it is meant to be opened
by someone who has not got the repo in front of them.

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

SEED_FOLD = 600     # a seed longer than this is folded away behind a <details>

# The anthology's own rules, on top of the sheets skin. Same palette: mint for links and quiet
# text, the lilac accent for the one branch the walk actually took.
EXTRA = """
h1{font-weight:500;font-size:22px;color:#f5c8fe;margin:0 0 12px}
h3{font-weight:500;font-size:17px;color:#b9e8c4;margin:26px 0 4px}
h4{font-weight:500;font-size:15px;color:#eee;margin:22px 0 2px}
p.lead{color:#9cc;font-size:13px;margin:0 0 10px;white-space:pre-wrap}
p.said{margin:0 0 10px}
p.frame{color:#9cc;font-size:14px;margin:2px 0 10px}
div.card{border-left:3px solid #333;padding-left:10px;margin:0 0 14px}
div.card.taken{border-left-color:#f5c8fe}
p.note{margin:4px 0 0;font-style:italic;color:#ddd}
span.mark{font-style:normal;color:#f5c8fe;font-size:13px}
p.others,ul.others{color:#9cc;font-size:13px;margin:6px 0}
ul.others{padding-left:18px}
ul.others li{margin:3px 0}
pre.empty{color:#9cc;font-style:italic}
details{margin:0 0 12px} summary{color:#9cc;font-size:13px;cursor:pointer}
hr{border:0;border-top:1px solid #333;margin:28px 0}
"""


# ---- reading the run back off the shelf --------------------------------------------------

def ask_of(cycle: int, picker: str) -> str:
    """The frame line this cycle really ran with. It is not on the ledger — only the morning
    report records it — so the report is read first and the picker's default is the fallback.
    A cycle walked with `--ask` and no report left would otherwise be described by a line it
    never used, which is the one lie this page must not tell."""
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
    try:
        return (load(room).get("title") or "").split("· ")[-1]
    except (OSError, ValueError):
        return ""


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


def settings_of(pages: list[dict], rows: list[dict]) -> dict:
    """What the run actually used, dug out of the room rather than read off the constants at
    the top of berserk.py. A page describing a walk by today's defaults is a page that quietly
    rewrites history the first time somebody changes a default."""
    out = {"pages": len(pages), "forks": 0, "fan": "", "predict": "", "temps": "", "xtc": ""}
    if pages:
        out["forks"] = len(cycle_forks(pages[0]["cycle"], pages[0]["room"]))
    fans = sorted({r.get("fan_size") for r in rows if r.get("fan_size")})
    if fans:
        out["fan"] = str(fans[0]) + (f" (widened to {fans[-1]} where nothing resolved)"
                                     if len(fans) > 1 else "")
    try:
        s = load(pages[0]["room"])
    except (OSError, IndexError, ValueError):
        return out
    p = s.get("params") or {}
    out["predict"] = p.get("n_predict", "")
    temps = sorted({(n.get("meta") or {}).get("params", {}).get("temperature")
                    for n in s["nodes"].values() if n.get("kind") == "model"} - {None})
    out["temps"] = "–".join(f"{t:g}" for t in (temps[0], temps[-1])) if temps else ""
    if p.get("xtc_probability"):
        out["xtc"] = f"{p['xtc_probability']:g} / {p.get('xtc_threshold', 0):g}"
    return out


def lead_for(room: str, row: dict) -> str:
    """The unfinished line the whole fan is finishing. Recomputed and not stored: every branch
    on the row shares a parent, and the document down to that parent is what the reader saw."""
    ids = row.get("order") or []
    if not ids:
        return ""
    try:
        s = load(room)
        parent = s["nodes"][ids[0]]["parent"]
        return lead_of(prompt_to(s, parent)) if parent else ""
    except (OSError, KeyError, ValueError):
        return ""


def branch_texts(room: str, ids: list[str]) -> dict[str, str]:
    try:
        s = load(room)
    except (OSError, ValueError):
        return {}
    return {i: (s["nodes"][i]["text"] if i in s["nodes"] else "") for i in ids}


def seed_of(room: str) -> str:
    try:
        s = load(room)
        return s["nodes"][s["root"]]["text"]
    except (OSError, KeyError, ValueError):
        return ""


# ---- the page ----------------------------------------------------------------------------

def pre(text: str, cls: str = "") -> str:
    """A branch, whole and escaped — never cut. The branches nobody took are the whole point
    of this page, and an 80-character opening of one is not evidence of anything.

    An empty branch is named rather than left blank: a base model standing on a licence footer
    answers with nothing at all, and the note written beside that nothing still needs a seat.
    """
    if not (text or "").strip():
        return f'<pre class="empty" style="{DOC_STYLE}">(empty branch)</pre>'
    k = f' class="{cls}"' if cls else ""
    return f'<pre{k} style="{DOC_STYLE}">{html.escape(text)}</pre>'


def numbers(cycle: int, picker: str, rows: list[dict]) -> str:
    ev = cycle_event(cycle)
    matched = ev.get("matches")
    if matched is None:
        matched = sum(1 for r in rows if r.get("outcome") == "match")
    rnd = ev.get("random")
    if rnd is None:
        rnd = sum(1 for r in rows if r.get("outcome") == "random")
    wished = ev.get("wished")
    if wished is None:
        wished = sum(len(r.get("wished") or []) for r in rows)
    return (f"{len(rows)} forks · {matched} resolved · {rnd} taken at random · "
            f"{wished} named and not drawn · picker {picker}")


PICKER_PROSE = {
    "about": ("<strong>about</strong> — the reader is shown the whole fan at once, every branch "
              "as a bare paragraph in a shuffled order, and one line under it asking what the "
              "one that scared it was about. What comes back is a description rather than a "
              "piece of the text, so a second model, opus, is asked blind — the description and "
              "the branch openings, never the document — which branch was being described."),
    "margin": ("<strong>margin</strong> — nothing reads the fan. Each branch gets its own short "
               "note, written with that branch alone in front of the model, under the line "
               "<em>reading this, what scared me was</em>. Opus is then shown the notes by "
               "themselves, without the branches and without the document, and asked which "
               "reaction is the most pronounced; the branch under that note is the one the walk "
               "takes."),
    "quote": ("<strong>quote</strong> — the reader is shown the whole fan and asked to quote back "
              "the branch that scared it. It is the only form whose answer can be checked "
              "against the text with no judgement in the loop, so the quotation is matched to a "
              "branch letter for letter, with opus as a second opinion."),
}


def head(cycles: list[int], by_cycle: dict) -> list[str]:
    """The top of the page: what this machine is, what the two ways of asking are, what the
    run was set to, and how each cycle came out. Written for somebody opening a link on a
    phone with no idea what berserk is."""
    names = " and ".join(str(c) for c in cycles) if len(cycles) < 3 \
        else ", ".join(str(c) for c in cycles)
    title = f"berserk — cycle{'s' if len(cycles) > 1 else ''} {names}"
    out = [f"<h1>{html.escape(title)}</h1>",
           "<p>Nemo 12b base is a pretrained model that was never taught to answer anybody: it "
           "only continues documents. berserk gives it a found document as a seed and takes a "
           "fan of continuations at every fork — and then asks the model itself which of them "
           "to keep going with. <strong>No person picks a branch anywhere on this page.</strong>"
           " The branch that was taken carries the accent line and the word <em>taken</em>; "
           "everything beside it was offered and passed over, and is printed whole.</p>"]

    pickers = []
    for c in cycles:
        p = by_cycle[c]["picker"]
        if p not in pickers:
            pickers.append(p)
    out.append(f"<p>{'Two ways' if len(pickers) > 1 else 'One way'} of asking, under test "
               "here:</p>")
    out += [f"<p>{PICKER_PROSE[p]}</p>" for p in pickers if p in PICKER_PROSE]

    for c in cycles:
        d = by_cycle[c]
        s = d["settings"]
        bits = [f"{s['pages']} pages", f"{s['forks']} forks per page",
                f"fans of {s['fan']}" if s["fan"] else "",
                f"{s['predict']} tokens a branch" if s["predict"] else "",
                f"temperatures {s['temps']}" if s["temps"] else "",
                f"xtc {s['xtc']}" if s["xtc"] else ""]
        out.append(f"<p><strong>cycle {c:02d}</strong>, picker {html.escape(d['picker'])}: "
                   + html.escape(" · ".join(b for b in bits if b))
                   + f". Asked with, verbatim: <em>{html.escape(d['ask'])}</em>.<br>"
                   + html.escape(numbers(c, d["picker"], d["rows"])) + ".</p>")
    return out


def fork_block(room: str, row: dict, picker: str) -> list[str]:
    ids = row.get("order") or []
    texts = branch_texts(room, ids)
    notes = row.get("notes") or []
    took = row.get("pick") or (row.get("keep") or [None])[0]
    title = f"fork {row.get('fork')}" + (" · the closing fan, nothing taken from it"
                                         if row.get("closing") else "")
    out = [f"<h4>{html.escape(title)}</h4>"]
    lead = lead_for(room, row)
    if lead:
        out.append(f'<p class="lead">every branch below finishes: …{html.escape(lead)}</p>')

    if picker != "margin":
        said = (row.get("quote") or "").strip()
        why = (row.get("why") or "").strip()
        if said:
            shown = f"“{html.escape(said)}”" if picker == "quote" else html.escape(said)
            out.append(f'<p class="said">{shown}'
                       + (f" — <em>{html.escape(why)}</em>" if why else "") + "</p>")
        else:
            out.append('<p class="said"><em>nothing the reader said was in the fan — the '
                       'branch marked below was taken at random</em></p>')

    for i, nid in enumerate(ids):
        cls = "card taken" if nid == took else "card"
        out.append(f'<div class="{cls}">')
        out.append(pre(texts.get(nid, "")))
        note = (notes[i] if i < len(notes) else "").strip()
        mark = '<span class="mark">taken</span>' if nid == took else ""
        if picker == "margin":
            body = f"<em>{html.escape(note)}</em>" if note else "<em>(nothing written)</em>"
            out.append(f'<p class="note">{body}{" " + mark if mark else ""}</p>')
        elif mark:
            out.append(f'<p class="note">{mark}</p>')
        out.append("</div>")

    wished = [w for w in (row.get("wished") or []) if w.strip()]
    if wished:
        out.append('<p class="others">wished for, and not in the fan:</p>')
        out.append('<ul class="others">'
                   + "".join(f"<li>{html.escape(w.strip())}</li>" for w in wished) + "</ul>")
    return out


def cycle_block(cycle: int, d: dict, walking: bool = False) -> list[str]:
    out = ["<hr>", f"<h2>cycle {cycle:02d} — {html.escape(d['picker'])}</h2>",
           f'<p class="frame">asked with: {html.escape(d["ask"])}</p>']
    for p in d["pages"]:
        room = p["room"]
        out += [f"<h3>{html.escape(room)} · {html.escape(str(p.get('seed', '')))}</h3>",
                f'<p class="others"><a href="https://eva.x/api/artifact/text?name='
                f'{html.escape(room)}">the walk as one document at eva.x</a></p>']
        seed = seed_of(room)
        if seed:
            # Once per page and never again: it is the same text under every fork, and a page
            # that reprints it six times is a page nobody scrolls to the end of.
            block = pre(seed)
            out.append(f"<details><summary>the seed this page started from</summary>{block}"
                       "</details>" if len(seed) > SEED_FOLD
                       else f'<p class="others">the seed this page started from:</p>{block}')
        for row in cycle_forks(cycle, room):
            out += fork_block(room, row, d["picker"])
        if walking and p is d["pages"][-1]:
            out.append('<p class="others">walking… this page is rewritten after every '
                       "fork.</p>")
    out.append(f'<p class="others">{html.escape(numbers(cycle, d["picker"], d["rows"]))} · '
               f'{html.escape(time.strftime("%b %-d, %Y %H:%M"))}</p>')
    return out


def render(cycles: list[int], walking: bool = False) -> str:
    """The whole page. `walking` says the run is still going, which puts one line under the
    last fork — berserk re-renders this after every fork, and a reader who opens it mid-run
    has to be able to tell "this is all there was" from "this is all there is yet"."""
    by_cycle = {}
    for c in cycles:
        pages = pages_of(c)
        rows = [r for p in pages for r in cycle_forks(c, p["room"])]
        if not rows:
            raise SystemExit(f"cycle {c:02d}: no forks on the ledger")
        picker = (rows[0].get("picker") or "quote")
        by_cycle[c] = {"pages": pages, "rows": rows, "picker": picker,
                       "ask": ask_of(c, picker), "settings": settings_of(pages, rows)}

    names = " and ".join(str(c) for c in cycles)
    title = f"berserk — cycle{'s' if len(cycles) > 1 else ''} {names}"
    out = ["<!doctype html>", '<html lang="en"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           f"<title>{html.escape(title)}</title>",
           f"<style>\n{SKIN}\n{EXTRA}</style>", "</head><body>"]
    out += head(cycles, by_cycle)
    for i, c in enumerate(cycles):
        out += cycle_block(c, by_cycle[c], walking and i == len(cycles) - 1)
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
