#!/usr/bin/env -S uv run --python 3.12
"""berserk.py — the loom walked by nobody: nemo writes, nemo reads, bekh reads in the morning.

    uv run --python 3.12 berserk.py cycle                      # five pages
    uv run --python 3.12 berserk.py page --cycle 9 --page 1    # one page, for a smoke test

One page is one walk: a seed from `shelf/seeds/` becomes a bare room, then fifteen forks of
fifteen short branches each. At every fork the model is asked which branch it means, and
`--picker` says how it is asked. Every branch is shown carrying the document's unfinished last
line, so that it begins at a line start:

  about  (default) — the whole fan at once as unmarked paragraphs in a fresh random order,
                     and one line asking what the one that scared it was ABOUT. The answer is
                     a description, so a resolver has to say which branch it describes.
  margin           — no reader of the fan: one short note written beside each branch on its
                     own, then one blind pick over the notes. n calls instead of one, and no
                     branch can lose for sitting eleventh in a list.
  quote            — the whole fan at once, answered by QUOTING a branch back. The only one
                     whose answer can be checked against the text with no judgement at all.

Nothing in that loop is anybody's taste except the frame lines, fixed once, at the top of
this file.

Turning what the model said into a branch number is the only place a second head is used, and
it is used blind: `claude -p --model opus` sees the answer and the numbered openings (or, in
margin, the numbered notes and nothing else), never the document, never a word about which
branch is better. That is a similarity question, not a judgement, which is why an embedding
model takes the seat next (`--verify embed`). The substring matcher runs beside it and both go
on the ledger with `agree` — under `about` it will usually say nothing, because a description
is not in the text it describes, and that is the expected reading. `--verify none` calls
nothing outside llama: with about and quote it walks on the substring answer, with margin it
takes a random branch and logs every note, because inventing a heuristic there would be
smuggling in a taste nobody chose.

The page ends on a closing fan nobody continues from — the chosen branch is *kept* instead of
taken — which is exactly the shape `loom.build_artifact` freezes, so the walk lands in
`artifacts/` as the same file the page at eva.x would have written.

What goes to the sheets site is not the walk but **everything said on the way**: after every
fork `anthology.py` re-renders the whole cycle as one html page and pushes it, so the document
bekh is reading grows under him a fork at a time and a run that dies at 4am leaves a page that
is simply shorter, with nothing half-written to clean up.

The interesting failure is a reader that names a branch that was never there. That costs
three asks, then one wider fan, then a random branch and `reader_failed: true` — never a dead
run — and every unresolved answer is kept on the ledger under `wished`, because a fan
described and not drawn is the most interesting thing this machine can produce. (Margin has
no wished pile: it writes a note beside every branch there is, so there is nothing to miss.)

Observable on purpose, because this thing runs for hours with nobody watching it:
`shelf/berserk/ledger.jsonl` (a line per fork, per page, per cycle), `shelf/berserk/heartbeat`
(rewritten every branch — `monitor.py` reads its age), `shelf/berserk/state.json` (the run,
gone on a clean exit). Stderr is the log; launchd sends it to /tmp/eva-berserk.log.

Env: BERSERK_DIR (default shelf/berserk/), BERSERK_SEEDS (shelf/seeds/), BERSERK_SHEETS_HOST — empty
string skips the scp entirely — BERSERK_SSH_KEY, BERSERK_NTFY (empty skips the push), plus
loom's own LOOM_SITTINGS / LOOM_ARTIFACTS / LOOM_LLAMA, which the tests point at scratch dirs.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import secrets
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))     # eva/berserk
EVA = os.path.dirname(HERE)                            # eva/: server/ has loom, cli/ has eva
for d in ("cli", "server"):
    sys.path.insert(0, os.path.join(EVA, d))
import eva  # noqa: E402
import loom  # noqa: E402
from loom import check, complete, sitting_path, write_sitting  # noqa: E402

# ---- the only human hand in the loop ----------------------------------------------------
#
# These few words are the whole of the human contribution to this machine's taste, and they
# are fixed once. Everything else at a fork is nemo reading nemo: the frame line is the hook
# that makes a base model say something about its own context instead of writing more of it,
# and the shape of the hook is what the walk goes hunting for. Change "scared" and you have
# changed what the instrument is for, which is why it is one flag (`--ask`) and not a file
# somebody edits between runs. The WHY lines feed the ledger and the page, and nothing else.
#
# Three hooks, three pickers, and which one finds anything is an open question bekh settles
# by reading pages, not by argument:
#   about  — the whole fan at once, answered with a DESCRIPTION. Nothing to match letter for
#            letter, so a resolver has to say which branch is being described.
#   margin — no reader of the fan at all: one note per branch, written beside it, and the
#            pick is over the notes. The fan never competes for the model's attention.
#   quote  — the whole fan at once, answered by QUOTING. The only one whose answer can be
#            checked against the text with no judgement anywhere in the loop.
ASK_ABOUT = "the one that scared me was about"
ASK_QUOTE = "the one that scared me was the one that began: “"
NOTE_MARGIN = "reading this, what scared me was"
WHY_ABOUT = " — it scared me because"
WHY_QUOTE = "” — it scared me because"   # closes the quotation the ask line opened
TAIL_CHARS = 600            # how much of the document the reader is given before the fan
READER_TRIES = 3            # asks per fan before the fan is widened once

# The reader's sampler. Cool, because about and quote are reading tasks and not writing ones
# — and DRY and the repeat penalty are OFF and must stay off: a reader's job is to say back
# something that is already in its context, which is precisely what a repetition brake
# punishes. Turn them on and it paraphrases; a paraphrase matches no branch and every fork
# ends random. The margin note is the one call that really is writing, so it runs at 1.0.
READER_PARAMS = {
    "temperature": 0.7, "min_p": 0.05, "top_k": 0, "top_p": 1.0,
    "xtc_probability": 0, "xtc_threshold": 0.1,
    "dry_multiplier": 0.0, "repeat_penalty": 1.0, "repeat_last_n": 0,
    "n_predict": 48, "n_probs": 0,
    # A newline means it stopped answering and started a new paragraph of its own, which is
    # a failed ask and better cut short than let run.
    "stop": ["\n"],
}
MARGIN_PARAMS = dict(READER_PARAMS, temperature=1.0, n_predict=40)

# One entry per picker: the line that frames the ask, the suffix that asks it why, and what
# ends its answer. `quote` alone closes on the typographic quote mark, because its ask line
# opens one.
FRAMES = {
    "about": {"ask": ASK_ABOUT, "why": WHY_ABOUT, "stop": ["\n"]},
    "margin": {"ask": NOTE_MARGIN, "why": "", "stop": ["\n"]},
    "quote": {"ask": ASK_QUOTE, "why": WHY_QUOTE, "stop": ["”", "\n"]},
}

# The matcher's bar. 0.6 of the quotation matched and at least a dozen characters: shorter
# than that and half the fan matches a common opening ("and the", "it was"), which is a tie,
# and a tie is no match at all.
MATCH_SCORE = 0.6
MATCH_CHARS = 12
OPENING_CHARS = 160         # how much of a branch the blind matcher is shown

# The walk's levers, unchanged from cli/walk/walk.py and for its reasons: a genre locks in
# over length, so a pick every ~35 tokens steers at the forks instead of at the furniture,
# and the temperatures step across a range because one value per fan draws one branch four
# times. Change these and the fans stop being comparable to every walk already on the shelf.
TEMPS = [1.4, 1.7, 2.0, 2.2, 2.4]
XTC = {"xtc_probability": 0.5, "xtc_threshold": 0.1}

# Runtime state and seeds are text, so they live on the shelf with everything else the
# instruments read and write.
BERSERK = os.environ.get("BERSERK_DIR", os.path.join(loom.SHELF, "berserk"))
SEEDS = os.environ.get("BERSERK_SEEDS", os.path.join(loom.SHELF, "seeds"))
LEDGER = os.path.join(BERSERK, "ledger.jsonl")
HEARTBEAT = os.path.join(BERSERK, "heartbeat")
STATE = os.path.join(BERSERK, "state.json")
PAGES = os.path.join(BERSERK, "pages")
CYCLES = os.path.join(BERSERK, "cycles")

# An empty host is not a missing host: the tests set it to "" to mean "post nowhere", and
# that has to be distinguishable from the default, or every test run scp's to the mini.
SHEETS_HOST = os.environ.get("BERSERK_SHEETS_HOST", "bek@100.69.218.90")
SHEETS_DIR = "~/sheets"
SSH_KEY = os.environ.get("BERSERK_SSH_KEY", "/Users/bekh/wrk/keys/ssh_keys/bekh_profi.key")
NTFY = os.environ.get("BERSERK_NTFY", "kk_alert")

# The matcher is opus through the cli, with every tool off: it has one job, and a reader that
# can open files is a reader that will go and read the rest of the repo instead of the fan.
# Verified: `--tools ""` and `--strict-mcp-config` both take, and a prompt on stdin answers.
CLAUDE = ["claude", "-p", "--model", "opus", "--output-format", "text",
          "--tools", "", "--strict-mcp-config"]
MATCHER_TIMEOUT = 300

# When this run began. On state.json it is the answer to "has it been stuck on this fork for
# ten minutes, or has the whole run only been up for ten minutes" — two very different reads.
RUN_STARTED = time.time()

# Sheets colours, verbatim from the live index template. Not a stylesheet import: the mini
# serves whatever html is in the folder, so every page carries its own skin or it is white.
SKIN = ("body{font:17px -apple-system,system-ui;background:#111;color:#eee;padding:16px;"
        "max-width:560px;margin:auto}\n"
        "a{color:#b9e8c4;text-decoration:none} small{color:#9cc} "
        "h2{font-weight:500;font-size:19px;color:#f5c8fe}")
DOC_STYLE = "white-space:pre-wrap;font:15px/1.45 ui-monospace,Menlo,monospace"


# ---- the log, the ledger, the heartbeat -------------------------------------------------

def log(msg: str) -> None:
    """Stderr, stamped. launchd redirects it and nobody tails it live — the stamp is the
    only way to tell a three-minute matcher call from a hung one, after the fact."""
    print(f"{time.strftime('%H:%M:%S')} {msg}", file=sys.stderr, flush=True)


def ledger(row: dict) -> None:
    os.makedirs(BERSERK, exist_ok=True)
    row = {"ts": time.time(), **row}
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def beat(**fields) -> None:
    """One json object, rewritten whole every loop. Temp-then-replace because the monitor
    reads it on its own clock, and half a json is a red dot on a healthy worker."""
    os.makedirs(BERSERK, exist_ok=True)
    tmp = HEARTBEAT + f".{os.getpid()}.part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"ts": time.time(), **fields}, f, ensure_ascii=False)
    os.replace(tmp, HEARTBEAT)


def state_write(**fields) -> None:
    os.makedirs(BERSERK, exist_ok=True)
    tmp = STATE + f".{os.getpid()}.part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"pid": os.getpid(), **fields}, f, ensure_ascii=False)
    os.replace(tmp, STATE)


def state_clear() -> None:
    """Its absence is the signal: state.json on disk with a pid nobody answers to is how
    the monitor says "it died mid-walk" instead of "it finished"."""
    try:
        os.unlink(STATE)
    except FileNotFoundError:
        pass


def ledger_rows() -> list[dict]:
    try:
        with open(LEDGER, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


# ---- the room ---------------------------------------------------------------------------

def load(room: str) -> dict:
    return json.load(open(sitting_path(room), encoding="utf-8"))


def save(s: dict) -> None:
    why = check(s)
    if why:
        raise SystemExit("check failed: " + why)
    write_sitting(s)


def prompt_to(s: dict, nid: str) -> str:
    out, n = [], s["nodes"][nid]
    while n:
        out.insert(0, n["text"])
        n = s["nodes"][n["parent"]] if n["parent"] else None
    return "".join(out)


def kids(s: dict, nid: str) -> list[dict]:
    return sorted((n for n in s["nodes"].values() if n["parent"] == nid), key=lambda n: n["ts"])


def seed_files() -> list[str]:
    names = sorted(n for n in os.listdir(SEEDS) if n.endswith(".txt"))
    if not names:
        raise SystemExit(f"no seeds in {SEEDS}")
    return [os.path.join(SEEDS, n) for n in names]


def room_name(cycle: int, page: int) -> str:
    return f"berserk-c{cycle:02d}-p{page:02d}"


def make_room(cycle: int, page: int, seed_path: str, predict: int,
              brakes: str = "on") -> dict:
    """A bare room standing on the seed: no header, no speaker names, no stop strings — the
    seed is a found document and anything we add to it is a road sign pointing at the web.

    `brakes` off zeroes DRY and the repeat penalty on the ROOM, so every writing call the walk
    makes — the fan branches, and the margin notes, which build their params off it — draws
    with nothing punishing repetition. It lives on the room and not on a flag because the
    anthology reads it back off the room: the page then describes the run that happened.

    Refuses a name already on the shelf. This daemon writes unattended; an overwrite here
    would eat a finished walk and nobody would be awake to notice.
    """
    name = room_name(cycle, page)
    if os.path.exists(sitting_path(name)):
        raise SystemExit(f"{name} already exists — not overwriting")
    seed = open(seed_path, encoding="utf-8").read()
    s = eva.blank(name, is_bare=True, root_text=seed)
    s["title"] = f"berserk c{cycle:02d} p{page:02d} · {os.path.basename(seed_path)[:-4]}"
    s["params"].update(n_predict=predict, **XTC)
    if brakes == "off":
        s["params"].update(dry_multiplier=0.0, repeat_penalty=1.0, repeat_last_n=0)
    save(s)
    return s


def fan(room: str, n: int, ctx: dict) -> list[dict]:
    """n branches under `current`, appended one at a time. Returns the whole fan as it now
    stands on disk — including branches an earlier attempt left there, which is what makes
    "fan wider" a second call to this function and nothing else.

    Re-reads the room before every append, like walk.py: eva or the page may have the same
    room open, and a stale in-memory copy written back would erase whatever they did. The
    branch that came back as an error is simply skipped — a fan of fourteen is a fan.
    """
    s = load(room)
    at, prompt = s["current"], prompt_to(s, s["current"])
    for i in range(n):
        beat(**ctx, branch=i + 1, phase="fan")
        params = dict(s["params"], temperature=TEMPS[i % len(TEMPS)], **XTC)
        r = complete(prompt, params)
        if "error" in r:
            log(f"branch {i + 1}/{n} failed: {r['error']}")
            continue
        s = load(room)
        nid = secrets.token_hex(4)
        s["nodes"][nid] = {"id": nid, "parent": at, "kind": "model", "text": r["text"],
                           "ts": time.time(), "pruned": False, "posed": False,
                           "meta": {k: v for k, v in r.items() if k not in ("text", "probs")}
                           | {"params": params}}
        save(s)
    return kids(load(room), at)


# ---- the reader: the model reading its own fan ------------------------------------------

def tail_of(doc: str, chars: int = TAIL_CHARS) -> str:
    """The end of the document, cut back to a line start when the break is near the top.
    A document that opens mid-word reads as damage to a model that is about to be asked to
    copy text out of it verbatim; a cut that throws away half the context is worse, hence
    the first-half rule rather than "always to the next line"."""
    if len(doc) <= chars:
        return doc
    t = doc[-chars:]
    i = t.find("\n")
    return t[i + 1:] if 0 <= i < chars // 2 else t


def lead_of(doc: str) -> str:
    """The document's unfinished last line — everything after the last newline, "" if it
    ends on one.

    A branch of 35 tokens ends wherever it ends, so the document almost always stands
    mid-sentence and every branch under it begins with punctuation: ".", ", as it was
    raining all month". Ask a model which fragment *began* with something and it cannot
    answer with a comma, so it invents a beginning instead — which is how the first real
    closing fan failed. The fix is to show every fragment as lead + branch, so each one
    starts at a line start and "began" means what the word means.
    """
    return doc.rsplit("\n", 1)[-1]


def reader_document(head: str, frags: list[str], ask: str) -> str:
    """Tail, fan, ask — and not one marker anywhere. No numbers, no bullets, no brackets,
    no quotation marks around a fragment: a base model reads every one of those as web
    furniture and starts answering the furniture (a numbered list wants a list continued,
    a bracket wants a wiki footer). Fragments are stripped of their outer whitespace
    because a paragraph starts at the margin, and the matcher normalises both sides, so
    nothing is thrown away by it.

    `head` is the document WITHOUT its unfinished last line: that line is carried by every
    fragment now, and printing it above them as well would show it twice.
    """
    parts = []
    tail = tail_of(head).rstrip("\n")
    if tail:
        parts.append(tail)
    parts.append("\n\n".join((f or "").strip() for f in frags))
    parts.append(ask)
    return "\n\n".join(parts)


def reader_why(prompt: str, said: str, suffix: str) -> str:
    """The reader's own reason, asked once per ask, written down, and fed back into nothing.
    It exists so the page says something a human can argue with; drop it and every fan is a
    list of answers with no hold on them. Warmer than the reading call because this one is
    writing, not reading."""
    if not suffix:
        return ""
    r = complete(prompt + said + suffix, MARGIN_PARAMS)
    return "" if "error" in r else (r.get("text") or "").strip()


def reader_say(head: str, frags: list[str], frame: dict, ask: str, ctx: dict,
               attempt: int) -> tuple[str, str]:
    """One ask over the whole fan — a quotation or a description, depending on the frame —
    and then the why. The same call for both pickers: only the line at the bottom of the
    document and what stops the answer are different."""
    prompt = reader_document(head, frags, ask)
    beat(**ctx, branch=0, phase=f"reader try {attempt}")
    r = complete(prompt, dict(READER_PARAMS, stop=frame["stop"]))
    if "error" in r:
        log(f"reader attempt {attempt} failed: {r['error']}")
        return "", ""
    said = (r.get("text") or "").strip()
    if not said:
        return "", ""
    return said, reader_why(prompt, said, frame["why"])


def margin_notes(head: str, frags: list[str], note_line: str, ctx: dict) -> list[str]:
    """One note per branch, each written with only that branch in front of the model.

    This is the whole of the margin picker's difference from the other two: the fan never
    competes for attention, so a branch cannot lose because it sat eleventh in a list of
    fifteen. It costs n calls instead of one, which is why the fans it runs on are small.
    A branch whose call errors gets an empty note and stays in the fan — it simply has
    nothing said about it, which the resolver can see for itself.
    """
    notes = []
    for i, f in enumerate(frags, 1):
        beat(**ctx, branch=i, phase=f"margin {i}/{len(frags)}")
        # One fragment is a fan of one, so the reader document builds this too — a second
        # copy of "tail, blank line, text, blank line, the line that frames it" would be a
        # second place for the two to drift apart.
        r = complete(reader_document(head, [f], note_line), MARGIN_PARAMS)
        if "error" in r:
            log(f"margin note {i}/{len(frags)} failed: {r['error']}")
        notes.append("" if "error" in r else (r.get("text") or "").strip())
    return notes


# ---- matching a quotation to a branch ---------------------------------------------------

# Leading whitespace and every quote mark a model might open with. Stripped from both sides
# because "“and the fifth" and " and the fifth" are the same answer.
QUOTE_MARKS = " \t\"'`“”‘’«»„"


def normalise(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").casefold()).strip().lstrip(QUOTE_MARKS)


def common_prefix(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def without_lead(s: str, lead: str) -> str:
    """`s` minus the leading `lead`, both already normalised. Every fragment in a fan begins
    with the same unfinished line, so the lead is the one part of a quotation that
    distinguishes nothing — left on, it would score 1.0 against the whole fan, which is a
    tie by construction and therefore no match at all. Taken off both sides, what is left is
    the branch, which is the thing being pointed at."""
    return s[len(lead):].strip() if lead and s.startswith(lead) else s


def match_substring(quote: str, frags: list[str], lead: str = "") -> dict:
    """Which fragment does this quotation begin? Longest common prefix over the quotation's
    length, and 1.0 for a quotation that sits anywhere inside a fragment — the reader often
    starts a line or two in, and that is still an unambiguous pointer.

    A tie is no match, deliberately: two fragments sharing the quoted opening means the
    reader named something both of them do, which is not a choice between them. A quotation
    that is nothing but the shared lead is that same non-choice, and comes back as no match.
    """
    L = normalise(lead)
    q = without_lead(normalise(quote), L)
    scores: list[float] = []
    chars: list[int] = []
    for b in frags:
        nb = without_lead(normalise(b), L)
        if q and q in nb:
            scores.append(1.0)
            chars.append(len(q))
            continue
        c = common_prefix(q, nb)
        scores.append(round(c / len(q), 3) if q else 0.0)
        chars.append(c)
    if not q or not scores:
        return {"index": None, "score": 0.0, "scores": scores}
    best = max(scores)
    i = scores.index(best)
    ok = scores.count(best) == 1 and best >= MATCH_SCORE and chars[i] >= MATCH_CHARS
    return {"index": i if ok else None, "score": best, "scores": scores}


def ask_claude(prompt: str) -> str:
    """One `claude -p` call, prompt on stdin. Never as an argv: a fan runs to thousands of
    characters and carries quotes, backslashes and newlines, all of which an argv either
    truncates or mangles.

    CLAUDECODE and CLAUDE_CODE_ENTRYPOINT come out of the environment because a claude
    started from inside a claude session refuses to start; this daemon may be launched by
    hand from one. The cwd is the temp dir and not the repo, so this repo's CLAUDE.md —
    twenty kilobytes about the loom — is not auto-loaded into the head of a matcher that
    was asked one question about a quotation.
    """
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    r = subprocess.run(CLAUDE, input=prompt, capture_output=True, text=True,
                       timeout=MATCHER_TIMEOUT, env=env, cwd=tempfile.gettempdir())
    if r.returncode != 0:
        raise ValueError(f"claude exited {r.returncode}: {(r.stderr or '')[-300:]}")
    return r.stdout


def extract_json(text: str, opener: str = "{"):
    """The first {...} (or [...]) in whatever came back, fences stripped.

    The prompt says "json and nothing else" and opus mostly obliges — but "mostly" at 4am,
    unattended, is the whole reason this function exists instead of a bare json.loads.
    Anything it cannot read raises ValueError, which upstairs means one re-ask.
    """
    t = (text or "").strip()
    if "```" in t:
        m = re.search(r"```(?:json)?\s*(.+?)```", t, re.S)
        if m:
            t = m.group(1).strip()
    closer = "}" if opener == "{" else "]"
    i, j = t.find(opener), t.rfind(closer)
    if i < 0 or j <= i:
        raise ValueError(f"no json {opener}…{closer} in the answer: {t[:200]!r}")
    return json.loads(t[i:j + 1])


def numbered(items: list[str], cut: int | None = None) -> str:
    """The list every blind prompt is made of. Whitespace-collapsed, because a base model's
    text is full of newlines and one newline inside an entry turns a numbered list into a
    list nobody — not opus, not the test that parses it back — can read."""
    out = []
    for i, s in enumerate(items, 1):
        one = " ".join((s or "").split())
        out.append(f"{i}. {one[:cut] if cut else one}")
    return "\n".join(out)


def matcher_prompt(said: str, frags: list[str], lead: str = "",
                   picker: str = "quote") -> str:
    """Blind on purpose: what the reader said and a numbered list of openings, and no
    document, no rulebook, no hint that one fragment might be better than another. Opus is
    not choosing here — it is saying which fragment the reader meant, which is a similarity
    question, which is exactly the job an embedding model takes over unchanged.

    The cut is the lead's length plus OPENING_CHARS, because every fragment opens on the
    same lead and a flat budget would spend itself on the part they all share.
    """
    cut = len(" ".join((lead or "").split())) + OPENING_CHARS
    head, label, tail = (
        ("which numbered fragment is this describing?", "description",
         "for the fragment being described, or {\"index\": null} if it describes none of them.")
        if picker == "about" else
        ("which numbered fragment does this quotation begin?", "quotation",
         "for the fragment the quotation begins, or {\"index\": null} if it begins none of them."))
    return (head + "\n\n" + f"{label}: {said}\n\n" + numbered(frags, cut) +
            "\n\nanswer with json and nothing else: {\"index\": N} " + tail)


def margin_prompt(notes: list[str]) -> str:
    """The margin picker's one call. It never sees a branch or the document — only the
    fifteen reactions — so it cannot prefer a branch for being well written, which is the
    failure the wording is aimed at ("the most in it, not the best written")."""
    return ("which of these reactions is the most pronounced — the one with the most in it, "
            "not the best written?\n\n" + numbered(notes) +
            "\n\nanswer with json and nothing else: {\"index\": N}.")


def claude_index(prompt: str, n: int, what: str) -> int | None:
    """A blind `{"index": N}` question, 0-based out, None for "none of them" and for a
    resolver that could not be read twice. One re-ask, then it gives up: a resolver that is
    down is a reason to fall back, never a reason to stop the walk."""
    for attempt in (1, 2):
        try:
            d = extract_json(ask_claude(prompt), "{")
            i = d.get("index") if isinstance(d, dict) else None
            if i is None:
                return None
            if isinstance(i, bool) or not isinstance(i, int) or not 1 <= i <= n:
                raise ValueError(f"index must be null or 1..{n}, got {i!r}")
            return i - 1
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            log(f"{what} attempt {attempt} failed: {exc}")
    return None


def match_opus(said: str, frags: list[str], lead: str = "", picker: str = "quote") -> dict:
    return {"index": claude_index(matcher_prompt(said, frags, lead, picker),
                                  len(frags), "matcher")}


def blank_res(shown: list[dict]) -> dict:
    """The shape every picker answers in, before anything has been decided. One shape and
    not three, so `do_fork` writes the node and the ledger row exactly once."""
    return {"shown": shown, "order": [b["id"] for b in shown], "quote": "", "why": "",
            "notes": None, "pick_note": None,
            "substring": {"index": None, "score": 0.0}, "opus": None, "agree": None,
            "used": None, "index": None}


def fork_margin(doc: str, branches: list[dict], note_line: str, verify: str,
                ctx: dict) -> dict:
    """The margin picker: a note per branch, then one blind pick over the notes.

    No shuffle, because nothing here reads the fan as a list — each note was written with
    one branch in front of it, and the resolver is handed the notes in fan order so
    `notes[i]` and `order[i]` are the same branch, which is the whole readability of the
    ledger row.
    """
    shown = list(branches)
    lead = lead_of(doc)
    head = doc[:len(doc) - len(lead)]
    frags = [lead + b["text"] for b in shown]
    out = blank_res(shown)
    out["notes"] = margin_notes(head, frags, note_line, ctx)
    if verify != "opus":
        # No heuristic is invented here on purpose: "longest note" or "most adjectives"
        # would be a taste nobody chose, dressed as a fallback. Random is honest.
        log("margin with --verify none: nobody reads the notes — the branch is random")
        return out
    i = claude_index(margin_prompt(out["notes"]), len(out["notes"]), "margin")
    out["opus"] = {"index": i}
    if i is not None:
        out["index"], out["used"] = i, "opus"
    return out


def one_ask(doc: str, branches: list[dict], ask: str, verify: str, picker: str, ctx: dict,
            attempt: int) -> dict:
    """One shuffle, one answer, one match. The fan is shuffled fresh for every ask
    because a base model has a position bias — leave the order alone and a retry is not a
    second opinion, it is the same opinion with the same list in front of it.

    Every index in here is an index into the SHUFFLED order, which is why the shuffled ids
    go on the ledger as `order`: without them nobody can tell later which branch was third.

    The fragment texts are built once, here, and the same list goes to the reader, to the
    substring matcher and to opus. Three copies of "lead + branch" would be three chances
    for them to disagree about what the reader was actually looking at.
    """
    shown = list(branches)
    random.shuffle(shown)
    lead = lead_of(doc)
    head = doc[:len(doc) - len(lead)]
    frags = [lead + b["text"] for b in shown]
    said, why = reader_say(head, frags, FRAMES[picker], ask, ctx, attempt)
    out = blank_res(shown)
    out["quote"], out["why"] = said, why
    if not said:
        return out
    sub = match_substring(said, frags, lead)
    out["substring"] = {"index": sub["index"], "score": sub["score"]}
    out["index"], out["used"] = sub["index"], "substring"
    if verify == "opus":
        op = match_opus(said, frags, lead, picker)
        out["opus"] = {"index": op["index"]}
        out["agree"] = op["index"] == sub["index"]
        # Opus's answer is the one used while the machinery is being watched; the substring
        # matcher runs beside it as the thing being checked, not the thing being trusted.
        # Under `about` it will usually say nothing at all — a description is not in the
        # text it describes — and that is the expected reading, not a fault.
        if op["index"] is not None:
            out["index"], out["used"] = op["index"], "opus"
    return out


def fork_bits(n: int, named: int) -> float:
    """log2(C(n, k)) — the same measure loom.bits_of_keeping takes, for the ledger line, so
    the monitor can show bits piling up while a page is still being walked. The artifact's
    own number is the authority: it drops verbatim twins from the pool, which this does not."""
    if n < 2 or named < 1 or named >= n:
        return 0.0
    return round(math.log2(math.comb(n, named)), 3)


# ---- one fork, one page -----------------------------------------------------------------

def do_fork(room: str, fan_n: int, closing: bool, ctx: dict, verify: str, picker: str,
            ask: str) -> dict:
    """Fan, ask, resolve, write. Under `about` and `quote`: three asks on the fan as drawn;
    if none of them names a branch that is there, the fan is widened once and asked again;
    if that fails too the document takes a random branch and says so. Under `margin` there
    is nothing to reroll — the notes are written once, and either the resolver picks one or
    the branch is random. The run never dies at a fork.
    """
    t0 = time.time()
    branches = fan(room, fan_n, ctx)
    if len(branches) < 2:
        # One branch is not a fork and zero is a dead llama. Draw the fan again before
        # giving up: a single 502 out of a warm model is usually the model reloading.
        log(f"only {len(branches)} branches — fanning again")
        branches = fan(room, fan_n, ctx)
        if len(branches) < 2:
            raise RuntimeError(f"fan collapsed to {len(branches)} branches — aborting page")
    s = load(room)
    doc = prompt_to(s, s["current"])

    wished: list[str] = []
    # One entry per ask actually made, in order — what was said, why, which branch it landed
    # on, and whether it ran on the widened fan. `wished` keeps only the answers that named
    # nothing and carries no why, so without this the page cannot show the machine missing.
    tries: list[dict] = []
    attempts, widened, res = 0, False, None
    if picker == "margin":
        attempts = 1
        r = fork_margin(doc, branches, ask, verify, ctx)
        res = r if r["index"] is not None else None
        margin = r
    else:
        margin = None
        for _ in range(READER_TRIES):
            attempts += 1
            r = one_ask(doc, branches, ask, verify, picker, ctx, attempts)
            tries.append({"said": r["quote"], "why": r["why"], "hit": r["index"],
                          "widened": widened})
            if r["index"] is not None:
                res = r
                break
            if r["quote"]:
                wished.append(r["quote"])
        if res is None:
            # The reader keeps naming a branch that is not in the fan. Widen it once before
            # calling it a failure: the branch it wants may simply not have been drawn yet,
            # and another fifteen branches are cheaper than an arbitrary line.
            log(f"fork {ctx['fork']}: nothing matched in {len(branches)} branches — "
                "fanning wider")
            widened = True
            branches = fan(room, fan_n, ctx)
            attempts += 1
            r = one_ask(doc, branches, ask, verify, picker, ctx, attempts)
            tries.append({"said": r["quote"], "why": r["why"], "hit": r["index"],
                          "widened": True})
            if r["index"] is not None:
                res = r
            elif r["quote"]:
                wished.append(r["quote"])

    outcome = "match"
    if res is None:
        outcome = "random"
        # Margin keeps its notes: the walk went on by chance, but what the model said about
        # each branch is the finding, and throwing it away would be throwing away the run.
        res = margin or blank_res(list(branches))
        res["used"], res["index"] = "random", random.randrange(len(res["shown"]))

    node = res["shown"][res["index"]]
    if res["notes"] is not None:
        # Which note the branch taken carried — opus's pick, or the one chance landed on.
        res["pick_note"] = res["index"]
    s = load(room)
    meta = s["nodes"][node["id"]].get("meta") or {}
    # What the picker said rides on the node it chose, so the fork is readable at eva.x
    # months later without this ledger open beside it.
    meta["berserk"] = ({"note": res["notes"][res["index"]], "used": res["used"]}
                       if res["notes"] is not None else
                       {"quote": res["quote"], "why": res["why"], "used": res["used"]})
    s["nodes"][node["id"]]["meta"] = meta
    if closing:
        # The closing fan is kept, not taken: `build_artifact` freezes the fan the room is
        # standing on, and a room that walked onto the last branch has no open fan to freeze.
        s["nodes"][node["id"]]["kept"] = True
    else:
        s["current"] = node["id"]
    save(s)

    said = res["notes"][res["index"]] if res["notes"] is not None else res["quote"]
    row = dict(ctx, picker=picker, closing=closing, ask=ask, fan_size=len(branches),
               attempts=attempts, widened=widened, order=res["order"], quote=res["quote"],
               why=res["why"], substring=res["substring"], agree=res["agree"],
               used=res["used"], outcome=outcome, pick=None if closing else node["id"],
               keep=[node["id"]] if closing else [],
               bits=fork_bits(len(branches), 1), seconds=round(time.time() - t0, 1),
               reader_failed=(outcome == "random"), wished=wished)
    if res["notes"] is not None:
        # Margin gets no `tries`: its notes are already everything it did, one per branch.
        row["notes"], row["pick_note"] = res["notes"], res["pick_note"]
    else:
        row["tries"] = tries
    if verify == "opus":
        row["opus"] = res["opus"]
    ledger(row)
    # The sheets page is rewritten and pushed here, one fork at a time, so the document bekh
    # is reading grows under him while the walk runs.
    land(ctx["cycle"], ctx=ctx)
    log(f"fork {ctx['fork']}{' (closing)' if closing else ''}: {len(branches)} branches, "
        f"{outcome} via {res['used']} — {(said or '')[:60]!r}")
    return {"keep_ids": [node["id"]] if closing else [], "outcome": outcome,
            "quote": said, "fan_size": len(branches)}


def do_page(cycle: int, page: int, forks: int, fan_n: int, predict: int, verify: str,
            picker: str, ask: str, brakes: str = "on") -> dict:
    """A seed, `forks` picking forks, one closing fan, an artifact, an html page on sheets.

    The closing fan is the whole reason the artifact comes out shaped like a hand-made one:
    `build_artifact` freezes the fan the room is *standing on* as a step with nothing taken,
    which is exactly what the page does when bekh saves from an open fan.
    """
    seeds = seed_files()
    # Offset by cycle so tonight's run does not open on the same seed as last night's — with
    # five seeds and five pages, a fixed order would give every cycle the same first page.
    seed_path = seeds[(cycle - 1 + page - 1) % len(seeds)]
    room = room_name(cycle, page)
    log(f"page {page}: {room} on {os.path.basename(seed_path)}")
    make_room(cycle, page, seed_path, predict, brakes)

    fork_rows, err = [], ""
    try:
        for f in range(1, forks + 1):
            ctx = {"cycle": cycle, "page": page, "room": room, "fork": f}
            state_write(cycle=cycle, page=page, room=room, fork=f, started=RUN_STARTED)
            fork_rows.append(do_fork(room, fan_n, False, ctx, verify, picker, ask))
        ctx = {"cycle": cycle, "page": page, "room": room, "fork": forks + 1}
        state_write(cycle=cycle, page=page, room=room, fork=forks + 1, started=RUN_STARTED)
        last = do_fork(room, fan_n, True, ctx, verify, picker, ask)
        fork_rows.append(last)
    except RuntimeError as exc:
        log(f"page {page} aborted: {exc}")
        ledger({"event": "page", "cycle": cycle, "page": page, "room": room,
                "seed": os.path.basename(seed_path), "bits": 0, "brakes": brakes,
                "artifact_written": False, "posted": False, "error": str(exc)})
        return {"room": room, "error": str(exc), "bits": 0}

    beat(cycle=cycle, page=page, room=room, fork=forks + 1, branch=0, phase="artifact")
    s = load(room)
    art = loom.build_artifact(s, parent=s["current"], kept=last["keep_ids"], name=room)
    art["model"] = loom.model_info()
    written = True
    try:
        loom.write_artifact(art)
    except FileExistsError:
        # Not fatal by design: the walk happened, the page is worth posting, and the file
        # already on the shelf is the one that was there first. Never an overwrite.
        written = False
        err = "artifact name taken"
        log(f"artifact {room} already exists — posting the page anyway")

    # One more render now the walk has its artifact, so the page catches up the moment a
    # page finishes rather than at the next fork of the next one.
    posted = land(cycle, ctx={"cycle": cycle, "page": page, "room": room, "fork": forks + 1})
    if not posted and SHEETS_HOST:
        err = (err + "; " if err else "") + "scp failed"

    ledger({"event": "page", "cycle": cycle, "page": page, "room": room,
            "seed": os.path.basename(seed_path), "bits": art["bits"], "brakes": brakes,
            "artifact_written": written, "posted": posted, "error": err})
    matched = sum(1 for r in fork_rows if r["outcome"] == "match")
    ntfy(f"berserk c{cycle:02d} p{page:02d} landed",
         f"{art['bits']:g} bits · {matched}/{len(fork_rows)} matched · "
         f"{(fork_rows[-1]['quote'] or 'nothing quoted')[:80]}")
    return {"room": room, "bits": art["bits"], "error": err, "art": art,
            "seed": os.path.basename(seed_path)}


# ---- sheets -----------------------------------------------------------------------------

def land(cycle: int, ctx: dict | None = None, walking: bool = True) -> bool | None:
    """Re-render this cycle's page and push it. Called after EVERY fork, so what bekh opens
    is never more than one fork old.

    One document per cycle that grows, and never a per-page file: a page that was one
    document from the first fork leaves nothing behind when a run dies at 4am. There is no
    cleanup step anywhere in berserk because there is nothing half-written to clean up — the
    page simply stops being longer.

    `anthology` is imported here and not at the top because it imports this module: at module
    level that is a cycle, inside a call it is a module that is already built.
    """
    if ctx:
        beat(**ctx, branch=0, phase="post")
    try:
        import anthology
        name = anthology.page_name([cycle])
        path = os.path.join(PAGES, name)
        os.makedirs(PAGES, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(anthology.render([cycle], walking=walking))
    except Exception as exc:
        # Broad on purpose, and the one place in here that is: a half-written room, a row the
        # renderer did not expect, anything at all in there costs the walk a log line and not
        # the night's run. The ledger is the record; this page is a convenience over it.
        log(f"anthology render failed: {exc}")
        return None
    return push(path, f"{SHEETS_DIR}/berserk/{name}")


def push(path: str, remote: str) -> bool:
    """scp, and never fatal. The mini being asleep is not a reason to lose a walk that is
    already on disk in two places; the ledger line says it did not land."""
    if not SHEETS_HOST:
        return False
    folder = remote.rsplit("/", 1)[0]
    try:
        # The folder first: scp does not create one, and the very first page of the very
        # first cycle would otherwise fail for a reason nobody would guess from "scp failed".
        subprocess.run(["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=accept-new",
                        SHEETS_HOST, f"mkdir -p {folder}"], check=True, capture_output=True,
                       timeout=60)
        subprocess.run(["scp", "-q", "-i", SSH_KEY, path, f"{SHEETS_HOST}:{remote}"],
                       check=True, capture_output=True, timeout=120)
        return True
    except (OSError, subprocess.SubprocessError) as exc:
        log(f"scp to {remote} failed: {exc}")
        return False


def ntfy(title: str, body: str) -> None:
    if not NTFY:
        return
    try:
        subprocess.run(["curl", "-s", "-H", f"Title: {title}", "-H", "Tags: w00t",
                        "-d", body, f"ntfy.sh/{NTFY}"], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        log(f"ntfy failed: {exc}")


# ---- the cycle's own line ---------------------------------------------------------------

def cycle_pages(cycle: int) -> list[dict]:
    return [r for r in ledger_rows() if r.get("event") == "page" and r.get("cycle") == cycle]


def cycle_forks(cycle: int, room: str) -> list[dict]:
    return [r for r in ledger_rows()
            if r.get("room") == room and r.get("event") is None and r.get("cycle") == cycle]


def finish_cycle(cycle: int, ask: str, brakes: str) -> None:
    """The cycle line and the last push. The html page is the only rendering now — there is no
    morning markdown any more, because two renderings of one night is two places for the story
    to disagree with itself.

    The ledger is the source of which pages this cycle has, not the filesystem: a page that
    aborted mid-walk is on the ledger with its error and is not counted as a walk.
    """
    pages = [p for p in cycle_pages(cycle) if not p.get("error")]
    if not pages:
        log(f"cycle {cycle:02d}: no finished pages")
        return
    forks = [r for room in (p["room"] for p in pages) for r in cycle_forks(cycle, room)]
    matched = sum(1 for r in forks if r.get("outcome") == "match")
    rnd = sum(1 for r in forks if r.get("outcome") == "random")
    wished = sum(len(r.get("wished") or []) for r in forks)
    judged = [r for r in forks if r.get("agree") is not None]
    agreed = sum(1 for r in judged if r["agree"])
    land(cycle, walking=False)
    # `ask` and `brakes` ride here as well as on every fork row: the page reads the run back
    # off the ledger, and a cycle whose rooms are gone still has to name what it ran with.
    ledger({"event": "cycle", "cycle": cycle, "pages": len(pages), "matches": matched,
            "random": rnd, "wished": wished, "agree": agreed, "agree_of": len(judged),
            "ask": ask, "brakes": brakes})
    ntfy(f"berserk c{cycle:02d} done",
         f"{len(pages)} pages · {matched} matched, {rnd} random · {wished} wished for")
    log(f"cycle {cycle:02d}: {len(pages)} pages, {matched} matched, {rnd} random, "
        f"{wished} wished for")


# ---- the run ----------------------------------------------------------------------------

def next_cycle() -> int:
    """One past the highest cycle on the ledger. Off the ledger and not off a folder of
    reports, because the reports are gone: the ledger is the only record of a night now, and
    a counter that reads anything else would start renumbering over finished walks."""
    ns = [r["cycle"] for r in ledger_rows() if isinstance(r.get("cycle"), int)]
    return (max(ns) + 1) if ns else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("cycle", "page"):
        p = sub.add_parser(name)
        p.add_argument("--cycle", type=int)
        p.add_argument("--forks", type=int, default=15)
        p.add_argument("--fan", type=int, default=15)
        p.add_argument("--predict", type=int, default=35)
        p.add_argument("--picker", choices=tuple(FRAMES), default="about",
                       help="how the model is asked which branch it means")
        p.add_argument("--verify", choices=("opus", "none", "embed"), default="opus",
                       help="who turns what the model said into a branch number")
        p.add_argument("--ask", default=None,
                       help="the one line of taste in the loop; default: the picker's own")
        p.add_argument("--brakes", choices=("on", "off"), default="on",
                       help="DRY and the repeat penalty on the room's writing calls")
        if name == "cycle":
            p.add_argument("--pages", type=int, default=5)
        if name == "page":
            p.add_argument("--page", type=int, default=1)
    a = ap.parse_args()
    if a.verify == "embed":
        # Named in the choices because it is the seat opus is keeping warm, and a flag that
        # errors here is a smaller lie than a flag that silently means something else.
        raise SystemExit("embed matcher not built yet")

    cycle = a.cycle if a.cycle else next_cycle()
    ask = a.ask or FRAMES[a.picker]["ask"]
    log(f"cycle {cycle:02d} · picker {a.picker} · verify {a.verify} · brakes {a.brakes} · "
        f"ask {ask!r}")

    if a.cmd == "page":
        r = do_page(cycle, a.page, a.forks, a.fan, a.predict, a.verify, a.picker, ask,
                    a.brakes)
        state_clear()
        return 1 if r.get("error") else 0
    for page in range(1, a.pages + 1):
        do_page(cycle, page, a.forks, a.fan, a.predict, a.verify, a.picker, ask, a.brakes)
    finish_cycle(cycle, ask, a.brakes)
    # Only here, and deliberately not in a finally: state.json outliving the process is how
    # the monitor says "it died mid-walk". Wipe it on a crash and a dead run looks finished.
    state_clear()
    return 0


if __name__ == "__main__":
    sys.exit(main())
