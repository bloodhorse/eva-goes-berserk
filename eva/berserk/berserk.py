#!/usr/bin/env -S uv run --python 3.12
"""berserk.py — the loom walked by nobody: nemo writes, nemo reads, bekh reads in the morning.

    uv run --python 3.12 berserk.py cycle                      # five pages
    uv run --python 3.12 berserk.py page --cycle 9 --page 1    # one page, for a smoke test

One page is one walk: a seed from `shelf/seeds/` becomes a bare room, then fifteen forks of
fifteen short branches each. At every fork the fan goes back to the same model as a *second
document* — the tail of the page, then every branch as its own unmarked paragraph in a fresh
random order, each carried by the document's unfinished last line so that it begins at a line
start, and one line that says which of them scared the reader — and the branch the model
quotes back is the branch the document continues on. Nothing in that loop is anybody's
taste except the dozen words of the ask line, fixed once, at the top of this file.

Matching a quotation to a branch is the only place a second head is used, and it is used
blind: `claude -p --model opus` sees the quotation and the numbered openings, never the
document, and answers which fragment the quotation begins. That is a similarity question, not
a judgement, which is why an embedding model takes the seat next (`--verify embed`). With
`--verify opus` opus's answer is the one used and the substring matcher runs beside it, both
on the ledger with `agree`; with `--verify none` nothing outside llama is called at all.

The page ends on a closing fan nobody continues from — the quoted branch is *kept* instead of
taken — which is exactly the shape `loom.build_artifact` freezes, so the walk lands in
`artifacts/` as the same file the page at eva.x would have written. Then it goes up to the
sheets site as html.

The interesting failure is a reader that quotes a branch that was never there. That costs
three asks, then one wider fan, then a random branch and `reader_failed: true` — never a dead
run — and every unmatched quotation is kept on the ledger under `wished`, because a fan
described and not drawn is the most interesting thing this machine can produce.

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
import html
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
# are fixed once. Everything else at a fork is nemo reading nemo: the ask line is the hook
# that makes a base model quote a passage out of its own context instead of writing a new
# one, and the shape of the hook is what the walk goes hunting for. Change "scared" and you
# have changed what the instrument is for, which is why it is one flag (`--ask`) and not a
# file somebody edits between runs. WHY feeds the morning report and nothing else.
ASK = "the one that scared me was the one that began: “"
WHY = "” — it scared me because"
TAIL_CHARS = 600            # how much of the document the reader is given before the fan
READER_TRIES = 3            # asks per fan before the fan is widened once

# The reader's sampler. Cool, because this is a copying task and not a writing one — and
# DRY and the repeat penalty are OFF and must stay off: the reader's entire job is to repeat
# a passage that is already in its context, which is precisely what a repetition brake
# punishes. Turn them on and it paraphrases; a paraphrase matches no branch and every fork
# ends random.
READER_PARAMS = {
    "temperature": 0.7, "min_p": 0.05, "top_k": 0, "top_p": 1.0,
    "xtc_probability": 0, "xtc_threshold": 0.1,
    "dry_multiplier": 0.0, "repeat_penalty": 1.0, "repeat_last_n": 0,
    "n_predict": 48, "n_probs": 0,
    # The closing quote mark ends the quotation; a newline means it started a new paragraph
    # instead of quoting, which is a failed ask and better cut short than let run.
    "stop": ["”", "\n"],
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


def make_room(cycle: int, page: int, seed_path: str, predict: int) -> dict:
    """A bare room standing on the seed: no header, no speaker names, no stop strings — the
    seed is a found document and anything we add to it is a road sign pointing at the web.

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


def reader_why(prompt: str, quote: str) -> str:
    """The reader's own reason, asked once, written down, and fed back into nothing. It
    exists so the morning file says something a human can argue with; drop it and the
    report is a list of quotations with no hold on them. Warmer than the quote call
    because this one is writing, not copying."""
    r = complete(prompt + quote + WHY,
                 dict(READER_PARAMS, temperature=1.0, n_predict=40, stop=["\n"]))
    return "" if "error" in r else (r.get("text") or "").strip()


def reader_quote(head: str, frags: list[str], ask: str, ctx: dict,
                 attempt: int) -> tuple[str, str]:
    prompt = reader_document(head, frags, ask)
    beat(**ctx, branch=0, phase=f"reader try {attempt}")
    r = complete(prompt, READER_PARAMS)
    if "error" in r:
        log(f"reader attempt {attempt} failed: {r['error']}")
        return "", ""
    quote = (r.get("text") or "").strip()
    if not quote:
        return "", ""
    return quote, reader_why(prompt, quote)


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


def matcher_prompt(quote: str, frags: list[str], lead: str = "") -> str:
    """Blind on purpose: a quotation and a numbered list of openings, and no document, no
    rulebook, no hint that one fragment might be better than another. Opus is not choosing
    here — it is saying where a sentence came from, which is a similarity question, which is
    exactly the job an embedding model takes over unchanged.

    The openings are whitespace-collapsed: a base model's branch is full of newlines, and a
    fragment with a newline in it turns a numbered list into an unreadable one. The cut is
    the lead's length plus OPENING_CHARS, because every fragment opens on the same lead and
    a flat budget would spend itself on the part they all share.
    """
    cut = len(" ".join((lead or "").split())) + OPENING_CHARS
    numbered = "\n".join(f"{i}. {' '.join((b or '').split())[:cut]}"
                         for i, b in enumerate(frags, 1))
    return ("which numbered fragment does this quotation begin?\n\n"
            f"quotation: {quote}\n\n" + numbered +
            "\n\nanswer with json and nothing else: {\"index\": N} for the fragment the "
            "quotation begins, or {\"index\": null} if it begins none of them.")


def match_opus(quote: str, frags: list[str], lead: str = "") -> dict:
    """The blind matcher. One re-ask on json that cannot be read, then it gives up and says
    nothing — a matcher that is down is a reason to fall back to the substring answer, never
    a reason to stop the walk."""
    prompt = matcher_prompt(quote, frags, lead)
    for attempt in (1, 2):
        try:
            d = extract_json(ask_claude(prompt), "{")
            i = d.get("index") if isinstance(d, dict) else None
            if i is None:
                return {"index": None}
            if isinstance(i, bool) or not isinstance(i, int) or not 1 <= i <= len(frags):
                raise ValueError(f"index must be null or 1..{len(frags)}, got {i!r}")
            return {"index": i - 1}
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            log(f"matcher attempt {attempt} failed: {exc}")
    return {"index": None}


def one_ask(doc: str, branches: list[dict], ask: str, verify: str, ctx: dict,
            attempt: int) -> dict:
    """One shuffle, one quotation, one match. The fan is shuffled fresh for every ask
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
    quote, why = reader_quote(head, frags, ask, ctx, attempt)
    out = {"shown": shown, "order": [b["id"] for b in shown], "quote": quote, "why": why,
           "substring": {"index": None, "score": 0.0}, "opus": None, "agree": None,
           "used": None, "index": None}
    if not quote:
        return out
    sub = match_substring(quote, frags, lead)
    out["substring"] = {"index": sub["index"], "score": sub["score"]}
    out["index"], out["used"] = sub["index"], "substring"
    if verify == "opus":
        op = match_opus(quote, frags, lead)
        out["opus"] = {"index": op["index"]}
        out["agree"] = op["index"] == sub["index"]
        # Opus's answer is the one used while the machinery is being watched; the substring
        # matcher runs beside it as the thing being checked, not the thing being trusted.
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

def do_fork(room: str, fan_n: int, closing: bool, ctx: dict, verify: str, ask: str) -> dict:
    """Fan, ask, match, write. Three asks on the fan as drawn; if none of them names a
    branch that is there, the fan is widened once and asked again; if that fails too the
    document takes a random branch and says so. The run never dies at a fork.
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
    attempts, widened, res = 0, False, None
    for _ in range(READER_TRIES):
        attempts += 1
        r = one_ask(doc, branches, ask, verify, ctx, attempts)
        if r["index"] is not None:
            res = r
            break
        if r["quote"]:
            wished.append(r["quote"])
    if res is None:
        # The reader keeps describing a branch that is not in the fan. Widen it once before
        # calling it a failure: the branch it wants may simply not have been drawn yet, and
        # another fifteen branches are cheaper than an arbitrary line in the document.
        log(f"fork {ctx['fork']}: nothing matched in {len(branches)} branches — fanning wider")
        widened = True
        branches = fan(room, fan_n, ctx)
        attempts += 1
        r = one_ask(doc, branches, ask, verify, ctx, attempts)
        if r["index"] is not None:
            res = r
        elif r["quote"]:
            wished.append(r["quote"])

    outcome = "match"
    if res is None:
        outcome = "random"
        shown = list(branches)
        res = {"shown": shown, "order": [b["id"] for b in shown], "quote": "", "why": "",
               "substring": {"index": None, "score": 0.0}, "opus": None, "agree": None,
               "used": "random", "index": random.randrange(len(shown))}

    node = res["shown"][res["index"]]
    s = load(room)
    meta = s["nodes"][node["id"]].get("meta") or {}
    # The quotation rides on the node it chose, so the fork is readable at eva.x months
    # later without this ledger open beside it.
    meta["berserk"] = {"quote": res["quote"], "why": res["why"], "used": res["used"]}
    s["nodes"][node["id"]]["meta"] = meta
    if closing:
        # The closing fan is kept, not taken: `build_artifact` freezes the fan the room is
        # standing on, and a room that walked onto the last branch has no open fan to freeze.
        s["nodes"][node["id"]]["kept"] = True
    else:
        s["current"] = node["id"]
    save(s)

    row = dict(ctx, closing=closing, fan_size=len(branches), attempts=attempts,
               widened=widened, order=res["order"], quote=res["quote"], why=res["why"],
               substring=res["substring"], agree=res["agree"], used=res["used"],
               outcome=outcome, pick=None if closing else node["id"],
               keep=[node["id"]] if closing else [],
               bits=fork_bits(len(branches), 1), seconds=round(time.time() - t0, 1),
               reader_failed=(outcome == "random"), wished=wished)
    if verify == "opus":
        row["opus"] = res["opus"]
    ledger(row)
    log(f"fork {ctx['fork']}{' (closing)' if closing else ''}: {len(branches)} branches, "
        f"{outcome} via {res['used']} — {(res['quote'] or '')[:60]!r}")
    return {"keep_ids": [node["id"]] if closing else [], "outcome": outcome,
            "quote": res["quote"], "fan_size": len(branches)}


def do_page(cycle: int, page: int, forks: int, fan_n: int, predict: int, verify: str,
            ask: str) -> dict:
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
    make_room(cycle, page, seed_path, predict)

    fork_rows, err = [], ""
    try:
        for f in range(1, forks + 1):
            ctx = {"cycle": cycle, "page": page, "room": room, "fork": f}
            state_write(cycle=cycle, page=page, room=room, fork=f, started=RUN_STARTED)
            fork_rows.append(do_fork(room, fan_n, False, ctx, verify, ask))
        ctx = {"cycle": cycle, "page": page, "room": room, "fork": forks + 1}
        state_write(cycle=cycle, page=page, room=room, fork=forks + 1, started=RUN_STARTED)
        last = do_fork(room, fan_n, True, ctx, verify, ask)
        fork_rows.append(last)
    except RuntimeError as exc:
        log(f"page {page} aborted: {exc}")
        ledger({"event": "page", "cycle": cycle, "page": page, "room": room,
                "seed": os.path.basename(seed_path), "bits": 0, "artifact_written": False,
                "posted": False, "error": str(exc)})
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

    beat(cycle=cycle, page=page, room=room, fork=forks + 1, branch=0, phase="post")
    path = write_page(art, room, os.path.basename(seed_path)[:-4])
    posted = push(path, f"{SHEETS_DIR}/berserk/{room}.html")
    if not posted and SHEETS_HOST:
        err = (err + "; " if err else "") + "scp failed"

    ledger({"event": "page", "cycle": cycle, "page": page, "room": room,
            "seed": os.path.basename(seed_path), "bits": art["bits"],
            "artifact_written": written, "posted": posted, "error": err})
    matched = sum(1 for r in fork_rows if r["outcome"] == "match")
    ntfy(f"berserk c{cycle:02d} p{page:02d} landed",
         f"{art['bits']:g} bits · {matched}/{len(fork_rows)} matched · "
         f"{(fork_rows[-1]['quote'] or 'nothing quoted')[:80]}")
    return {"room": room, "bits": art["bits"], "error": err, "art": art,
            "seed": os.path.basename(seed_path)}


# ---- sheets -----------------------------------------------------------------------------

def walk_temps(art: dict) -> list[float]:
    out = []
    for s in art.get("steps") or []:
        rows = ([s["took"]] if s.get("took") else []) + (s.get("kept") or []) \
            + (s.get("fan") or {}).get("others", [])
        out += [r["temperature"] for r in rows if r.get("temperature") is not None]
    return out


def write_page(art: dict, room: str, seed: str) -> str:
    """The walk as one html page in the sheets skin. The document goes in a `pre` and is
    escaped: a base model's text is full of `<`, `&` and stray brackets, and one unescaped
    `<` swallows the rest of the page."""
    os.makedirs(PAGES, exist_ok=True)
    text = loom.artifact_text(art)
    temps = walk_temps(art)
    trange = f"t {min(temps):g}–{max(temps):g}" if temps else "t —"
    title = art.get("title") or room
    line = (f"nemo 12b base · {art.get('bits', 0):g} bits · "
            f"{len(art.get('steps') or [])} forks · {trange} · {seed}")
    body = "\n".join([
        "<!doctype html>", '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f"<title>{html.escape(title)}</title>", f"<style>\n{SKIN}\n</style>",
        "</head><body>", f"<h2>{html.escape(title)}</h2>",
        f"<small>{html.escape(line)}</small><br>",
        f'<small><a href="https://eva.x/api/artifact/text?name={html.escape(room)}">'
        "plain text at eva.x</a></small>",
        f'<pre style="{DOC_STYLE}">{html.escape(text)}</pre>',
        "</body></html>", ""])
    path = os.path.join(PAGES, room + ".html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


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


# ---- the morning file -------------------------------------------------------------------

def cycle_pages(cycle: int) -> list[dict]:
    return [r for r in ledger_rows() if r.get("event") == "page" and r.get("cycle") == cycle]


def cycle_forks(cycle: int, room: str) -> list[dict]:
    return [r for r in ledger_rows()
            if r.get("room") == room and r.get("event") is None and r.get("cycle") == cycle]


def report(cycle: int, pages: list[dict], settings: dict, ask: str) -> str:
    """berserk/cycles/cNN.md — the one file bekh opens in the morning, built entirely off
    the ledger. Nobody reviews the pages any more: what is worth reading is the quotation at
    each fork and, under everything, the wished pile — the branches the reader described and
    the fan did not hold. Tracked by git, so it is prose with a table, not a json dump."""
    os.makedirs(CYCLES, exist_ok=True)
    out = [f"# berserk cycle {cycle:02d}", "", time.strftime("%b %-d, %Y %H:%M"), ""]
    if settings:
        out += ["settings: " + " · ".join(f"{k} {v}" for k, v in settings.items()), ""]
    out += [f"the ask: `{ask}`", "",
            "| room | seed | bits | forks | matched | widened | random | opus agrees |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    wishes: list[tuple[str, int, str]] = []
    for p in pages:
        forks = cycle_forks(cycle, p["room"])
        for r in forks:
            wishes += [(p["room"], r.get("fork"), q) for q in (r.get("wished") or [])]
        matched = sum(1 for r in forks if r.get("outcome") == "match")
        wide = sum(1 for r in forks if r.get("widened"))
        rnd = sum(1 for r in forks if r.get("outcome") == "random")
        judged = [r for r in forks if r.get("agree") is not None]
        agree = (f"{sum(1 for r in judged if r['agree'])}/{len(judged)}") if judged else "—"
        out.append(f"| {p['room']} | {p.get('seed', '')} | {p.get('bits', 0):g} | "
                   f"{len(forks)} | {matched} | {wide} | {rnd} | {agree} |")
    out.append("")

    for p in pages:
        room = p["room"]
        out += [f"## {room}", "",
                f"[the page](https://eva.x/api/artifact/text?name={room}) · forks:", ""]
        for r in cycle_forks(cycle, room):
            marks = ("  *(widened)*" if r.get("widened") else "") + \
                    ("  **(random)**" if r.get("outcome") == "random" else "")
            q = (r.get("quote") or "").strip()
            why = (r.get("why") or "").strip()
            body = f"“{q}” — {why}" if q else "nothing quoted"
            out.append(f"{r.get('fork')}. {body}{marks}")
        out.append("")

    out += ["## wished for", ""]
    if wishes:
        out += ["The reader described these and the fan did not hold them.", ""]
        out += [f"- `{room} f{fork}` — “{q.strip()}”" for room, fork, q in wishes]
    else:
        out.append("Nothing: every quotation this cycle was a branch that was really there.")
    out.append("")

    path = os.path.join(CYCLES, f"c{cycle:02d}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    log(f"report written: {path}")
    return path


def finish_cycle(cycle: int, settings: dict, ask: str) -> None:
    """The report, the cycle line, the push. The ledger is the source of which pages this
    cycle has, not the filesystem: a page that aborted mid-walk is on the ledger with its
    error and is not counted as a walk."""
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
    report(cycle, pages, settings, ask)
    ledger({"event": "cycle", "cycle": cycle, "pages": len(pages), "matches": matched,
            "random": rnd, "wished": wished, "agree": agreed, "agree_of": len(judged)})
    ntfy(f"berserk c{cycle:02d} done",
         f"{len(pages)} pages · {matched} matched, {rnd} random · {wished} wished for")
    log(f"cycle {cycle:02d}: {len(pages)} pages, {matched} matched, {rnd} random, "
        f"{wished} wished for")


# ---- the run ----------------------------------------------------------------------------

def next_cycle() -> int:
    try:
        ns = [int(m.group(1)) for n in os.listdir(CYCLES)
              if (m := re.match(r"^c(\d+)\.md$", n))]
    except FileNotFoundError:
        ns = []
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
        p.add_argument("--verify", choices=("opus", "none", "embed"), default="opus",
                       help="who turns a quotation into a branch number")
        p.add_argument("--ask", default=ASK,
                       help="the one line of taste in the loop")
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
    log(f"cycle {cycle:02d} · verify {a.verify} · ask {a.ask!r}")

    if a.cmd == "page":
        r = do_page(cycle, a.page, a.forks, a.fan, a.predict, a.verify, a.ask)
        state_clear()
        return 1 if r.get("error") else 0
    settings = {"pages": a.pages, "forks": a.forks, "fan": a.fan, "predict": a.predict,
                "verify": a.verify}
    for page in range(1, a.pages + 1):
        do_page(cycle, page, a.forks, a.fan, a.predict, a.verify, a.ask)
    finish_cycle(cycle, settings, a.ask)
    # Only here, and deliberately not in a finally: state.json outliving the process is how
    # the monitor says "it died mid-walk". Wipe it on a crash and a dead run looks finished.
    state_clear()
    return 0


if __name__ == "__main__":
    sys.exit(main())
