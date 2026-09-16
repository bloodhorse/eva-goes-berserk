#!/usr/bin/env -S uv run --python 3.12
"""berserk.py — the loom walked by nobody: nemo writes, opus picks, bekh reads in the morning.

    uv run --python 3.12 berserk.py cycle                 # five pages, then the review
    uv run --python 3.12 berserk.py page --cycle 9 --page 1   # one page, for a smoke test
    uv run --python 3.12 berserk.py review --cycle 9      # the review alone, off the ledger

One page is one walk: a seed from `seeds/` becomes a bare room, then fifteen forks of fifteen
short branches each, and at every fork `claude -p --model opus` reads the fan against
`docs/berserk-picker.md` and says which line the document continues on. The page ends on a
closing fan nobody picks from — only keeps — which is exactly the shape `loom.build_artifact`
freezes, so the walk lands in `artifacts/` as the same file the page at eva.x would have
written. Then it goes up to the sheets site as html, and after the last page the same reader
sees all five whole and says which held anything.

Nothing here is bekh's judgement: opus is a **sieve**, and the rulebook says so at length.
The daemon's only opinions are structural — how long a branch is, how wide a fan, where the
document ends. The interesting failure mode is not a bad pick, it is a picker that answers
prose instead of json at 4am; that is why a failed parse costs one re-ask, then a random pick
and `picker_failed: true` on the ledger line, and never a dead run.

Observable on purpose, because this thing runs for hours with nobody watching it:
`berserk/ledger.jsonl` (a line per fork, per page, per cycle), `berserk/heartbeat` (rewritten
every branch — `berserk_monitor.py` reads its age), `berserk/state.json` (the run, gone on a
clean exit). Stderr is the log; launchd sends it to /tmp/eva-berserk.log.

Env: BERSERK_DIR (default berserk/), BERSERK_SEEDS (seeds/), BERSERK_SHEETS_HOST — empty
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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eva  # noqa: E402
import loom  # noqa: E402
from loom import check, complete, sitting_path, write_sitting  # noqa: E402

# The walk's levers, unchanged from docs/walk/walk.py and for its reasons: a genre locks in
# over length, so a pick every ~35 tokens steers at the forks instead of at the furniture,
# and the temperatures step across a range because one value per fan draws one branch four
# times. Change these and the fans stop being comparable to every walk already on the shelf.
TEMPS = [1.4, 1.7, 2.0, 2.2, 2.4]
XTC = {"xtc_probability": 0.5, "xtc_threshold": 0.1}

BERSERK = os.environ.get("BERSERK_DIR", os.path.join(HERE, "berserk"))
SEEDS = os.environ.get("BERSERK_SEEDS", os.path.join(HERE, "seeds"))
RULEBOOK = os.path.join(HERE, "docs", "berserk-picker.md")
LEDGER = os.path.join(BERSERK, "ledger.jsonl")
HEARTBEAT = os.path.join(BERSERK, "heartbeat")
STATE = os.path.join(BERSERK, "state.json")
PAGES = os.path.join(BERSERK, "pages")
CYCLES = os.path.join(BERSERK, "cycles")
NOTES = os.path.join(BERSERK, "notes")

# An empty host is not a missing host: the tests set it to "" to mean "post nowhere", and
# that has to be distinguishable from the default, or every test run scp's to the mini.
SHEETS_HOST = os.environ.get("BERSERK_SHEETS_HOST", "bek@100.69.218.90")
SHEETS_DIR = "~/sheets"
SSH_KEY = os.environ.get("BERSERK_SSH_KEY", "/Users/bekh/wrk/keys/ssh_keys/bekh_profi.key")
NTFY = os.environ.get("BERSERK_NTFY", "kk_alert")

# The picker is opus through the cli, with every tool off: it has one job, and a reader that
# can open files is a reader that will go and read the rest of the repo instead of the fan.
# Verified: `--tools ""` and `--strict-mcp-config` both take, and a prompt on stdin answers.
CLAUDE = ["claude", "-p", "--model", "opus", "--output-format", "text",
          "--tools", "", "--strict-mcp-config"]
PICKER_TIMEOUT = 300

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
    only way to tell a three-minute picker call from a hung one, after the fact."""
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
    stands on disk — including branches an earlier attempt left there.

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


# ---- the picker -------------------------------------------------------------------------

def rulebook() -> str:
    return open(RULEBOOK, encoding="utf-8").read()


def notes_text(path: str | None) -> str:
    """bekh's notes for this cycle, if he left any. Appended under the rulebook, which says
    in its own first paragraph that they override it where they disagree."""
    if not path or not os.path.isfile(path):
        return ""
    return open(path, encoding="utf-8").read().strip()


def temp_of(node: dict) -> float | None:
    p = (node.get("meta") or {}).get("params") or {}
    return p.get("temperature")


def picker_prompt(doc: str, branches: list[dict], closing: bool, notes: str) -> str:
    """Rulebook, notes, document, fan. The branches go in raw — no repr, no quotes, no
    markdown fence: a base model's line is full of the characters a fence would eat, and the
    reader is being asked about exactly those characters."""
    parts = [rulebook()]
    if notes:
        parts.append("## bekh's notes for this cycle\n\n" + notes)
    parts.append("THE DOCUMENT SO FAR\n\n" + doc)
    head = ("THE FAN — this is the CLOSING FAN: the document ends here, there is no pick, "
            "keep 1–3 endings and answer with \"pick\": null."
            if closing else
            "THE FAN — an ordinary fork: pick one branch to continue on.")
    fan_txt = "\n".join(f"--- {i} (t={temp_of(b)})\n{b['text']}\n"
                        for i, b in enumerate(branches, 1))
    parts.append(head + "\n\n" + fan_txt)
    parts.append("Answer with the json object from \"the answer\" above and nothing else.")
    return "\n\n".join(parts)


def ask_claude(prompt: str) -> str:
    """One `claude -p` call, prompt on stdin. Never as an argv: a document runs to thousands
    of characters and carries quotes, backslashes and newlines, all of which an argv either
    truncates or mangles.

    CLAUDECODE and CLAUDE_CODE_ENTRYPOINT come out of the environment because a claude
    started from inside a claude session refuses to start; this daemon may be launched by
    hand from one. The cwd is the temp dir and not the repo, so this repo's CLAUDE.md —
    twenty kilobytes about the loom — is not auto-loaded into the head of a reader who was
    asked one question about a fan.
    """
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    r = subprocess.run(CLAUDE, input=prompt, capture_output=True, text=True,
                       timeout=PICKER_TIMEOUT, env=env, cwd=tempfile.gettempdir())
    if r.returncode != 0:
        raise ValueError(f"claude exited {r.returncode}: {(r.stderr or '')[-300:]}")
    return r.stdout


def extract_json(text: str, opener: str = "{"):
    """The first {...} (or [...]) in whatever came back, fences stripped.

    The rulebook says "only json, nothing around it" and opus mostly obliges — but "mostly"
    at 4am, unattended, is the whole reason this function exists instead of a bare
    json.loads. Anything it cannot read raises ValueError, which upstairs means one re-ask.
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


def read_pick(answer: str, n: int, closing: bool) -> dict:
    """The picker's json, validated into {genre, pick, keep, note}. Raises ValueError with a
    sentence that is fed back verbatim on the re-ask — a reader told what it got wrong fixes
    it far more often than one told to try again."""
    d = extract_json(answer, "{")
    if not isinstance(d, dict):
        raise ValueError("the answer is not a json object")
    pick = d.get("pick")
    if closing:
        if pick is not None:
            raise ValueError("this is the closing fan: pick must be null")
    else:
        if not isinstance(pick, int) or isinstance(pick, bool) or not 1 <= pick <= n:
            raise ValueError(f"pick must be an integer between 1 and {n}, got {pick!r}")
    keep = d.get("keep") or []
    if not isinstance(keep, list):
        raise ValueError("keep must be a list of integers")
    out = []
    for k in keep:
        if not isinstance(k, int) or isinstance(k, bool) or not 1 <= k <= n:
            raise ValueError(f"keep holds {k!r}, which is not a branch number 1..{n}")
        if k == pick:
            raise ValueError("keep must not contain pick")
        if k not in out:
            out.append(k)
    if closing and not out:
        raise ValueError("the closing fan must keep at least one ending")
    return {"genre": str(d.get("genre") or "")[:200], "pick": pick, "keep": out,
            "note": str(d.get("note") or "")[:600]}


def pick_fan(branches: list[dict], doc: str, closing: bool, notes: str, ctx: dict) -> dict:
    """Ask, and on a bad answer ask once more with the complaint attached. Two failures and
    the walk takes a random branch and keeps nothing — a page with one arbitrary fork in it
    is still a page, and a daemon that stops at 4am because a reader got chatty is not."""
    n = len(branches)
    prompt = picker_prompt(doc, branches, closing, notes)
    for attempt in (1, 2):
        beat(**ctx, phase=f"picker try {attempt}")
        try:
            answer = ask_claude(prompt)
            return dict(read_pick(answer, n, closing), picker_failed=False)
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            log(f"picker attempt {attempt} failed: {exc}")
            prompt = (picker_prompt(doc, branches, closing, notes) +
                      f"\n\nYour previous answer could not be read: {exc}\n"
                      "Answer with json only — no prose, no fences.")
    k = random.randrange(1, n + 1)
    return {"genre": "", "pick": None if closing else k, "keep": [k] if closing else [],
            "note": "picker failed twice — random branch", "picker_failed": True}


def apply_pick(room: str, branches: list[dict], d: dict) -> list[str]:
    """The picker's answer written into the room: kept flags, a new `current`, and the genre
    and note parked on the node it chose, so the fork is readable at eva.x months later
    without this ledger beside it. On the closing fan there is no chosen node, so the note
    rides on the endings instead."""
    s = load(room)
    keep_ids = [branches[k - 1]["id"] for k in d["keep"]]
    took_id = branches[d["pick"] - 1]["id"] if d["pick"] else None
    for nid in keep_ids:
        s["nodes"][nid]["kept"] = True
    mark = {"genre": d["genre"], "note": d["note"], "keep": keep_ids}
    for nid in ([took_id] if took_id else keep_ids):
        meta = s["nodes"][nid].get("meta") or {}
        meta["berserk"] = mark
        s["nodes"][nid]["meta"] = meta
    if took_id:
        s["current"] = took_id
    save(s)
    return keep_ids


def fork_bits(n: int, named: int) -> float:
    """log2(C(n, k)) — the same measure loom.bits_of_keeping takes, for the ledger line, so
    the monitor can show bits piling up while a page is still being walked. The artifact's
    own number is the authority: it drops verbatim twins from the pool, which this does not."""
    if n < 2 or named < 1 or named >= n:
        return 0.0
    return round(math.log2(math.comb(n, named)), 3)


# ---- one fork, one page -----------------------------------------------------------------

def do_fork(room: str, fan_n: int, closing: bool, notes: str, ctx: dict) -> dict:
    """Fan, ask, apply. Returns the picker's answer plus what it cost."""
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
    d = pick_fan(branches, doc, closing, notes, ctx)
    keep_ids = apply_pick(room, branches, d)
    row = dict(ctx, closing=closing, fan_size=len(branches), pick=d["pick"], keep=d["keep"],
               genre=d["genre"], note=d["note"], picker_failed=d["picker_failed"],
               bits=fork_bits(len(branches), len(keep_ids) + (1 if d["pick"] else 0)),
               seconds=round(time.time() - t0, 1))
    ledger(row)
    log(f"fork {ctx['fork']}{' (closing)' if closing else ''}: {len(branches)} branches, "
        f"pick {d['pick']}, keep {d['keep']} — {d['genre']}")
    return dict(d, keep_ids=keep_ids, fan_size=len(branches))


def do_page(cycle: int, page: int, forks: int, fan_n: int, predict: int,
            notes: str) -> dict:
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
            fork_rows.append(do_fork(room, fan_n, False, notes, ctx))
        ctx = {"cycle": cycle, "page": page, "room": room, "fork": forks + 1}
        state_write(cycle=cycle, page=page, room=room, fork=forks + 1, started=RUN_STARTED)
        last = do_fork(room, fan_n, True, notes, ctx)
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
    ntfy(f"berserk c{cycle:02d} p{page:02d} landed",
         f"{art['bits']:g} bits · {fork_rows[-1]['genre'] or 'no genre named'}")
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


# ---- the review -------------------------------------------------------------------------

def cycle_pages(cycle: int) -> list[dict]:
    return [r for r in ledger_rows() if r.get("event") == "page" and r.get("cycle") == cycle]


def cycle_forks(cycle: int, room: str) -> list[dict]:
    return [r for r in ledger_rows()
            if r.get("room") == room and r.get("event") is None and r.get("cycle") == cycle]


def review_prompt(cycle: int, pages: list[dict], notes: str) -> str:
    parts = [rulebook()]
    if notes:
        parts.append("## bekh's notes for this cycle\n\n" + notes)
    parts.append(f"THE {len(pages)} PAGES OF CYCLE {cycle:02d}, each whole, with the fork "
                 "notes it was walked by.")
    for p in pages:
        room = p["room"]
        try:
            art = json.load(open(loom.artifact_path(room), encoding="utf-8"))
            doc = loom.artifact_text(art)
        except (OSError, ValueError):
            doc = "(this page's artifact could not be read)"
        forks = "\n".join(f"{r.get('fork')}. {r.get('genre') or '—'} — {r.get('note') or ''}"
                          for r in cycle_forks(cycle, room))
        parts.append(f"=== {room} ===\n\nTHE DOCUMENT\n\n{doc}\n\nTHE FORK NOTES\n\n{forks}")
    parts.append("Answer with the json list from \"the review\" above — one object per page, "
                 f"all {len(pages)} of them, in order, and nothing else.")
    return "\n\n".join(parts)


def read_review(answer: str, names: list[str]) -> list[dict]:
    d = extract_json(answer, "[")
    if not isinstance(d, list) or not d:
        raise ValueError("the answer is not a json list")
    out = []
    for e in d:
        if not isinstance(e, dict) or e.get("page") not in names:
            raise ValueError(f"{(e or {}).get('page')!r} is not one of this cycle's pages: "
                             f"{', '.join(names)}")
        out.append({"page": e["page"], "notable": bool(e.get("notable")),
                    "why": str(e.get("why") or ""), "quote": e.get("quote")})
    return out


def do_review(cycle: int, notes: str, settings: dict | None = None) -> list[dict]:
    """The five pages read whole by the same reader, then the report on disk and the notable
    ones promoted to the top of the sheets site.

    The ledger is the source of which pages this cycle has, not the filesystem: a page that
    aborted mid-walk is on the ledger with its error and must not be reviewed as if it were
    a finished walk.
    """
    pages = [p for p in cycle_pages(cycle) if not p.get("error")]
    if not pages:
        log(f"cycle {cycle:02d}: nothing to review")
        return []
    names = [p["room"] for p in pages]
    beat(cycle=cycle, page=0, room="", fork=0, branch=0, phase="review")
    prompt = review_prompt(cycle, pages, notes)
    verdicts, raw = [], ""
    for attempt in (1, 2):
        try:
            raw = ask_claude(prompt)
            verdicts = read_review(raw, names)
            break
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            log(f"review attempt {attempt} failed: {exc}")
            prompt = (review_prompt(cycle, pages, notes) +
                      f"\n\nYour previous answer could not be read: {exc}\n"
                      "Answer with a json list only.")
    for v in verdicts:
        if not v["notable"]:
            continue
        # Notable goes to the ROOT of the sheets folder, where bekh's reading list is. The
        # copy in berserk/ stays: promotion is a second link, not a move.
        push(os.path.join(PAGES, v["page"] + ".html"), f"{SHEETS_DIR}/{v['page']}.html")
    report(cycle, pages, verdicts, raw if not verdicts else "", notes, settings or {})
    n = sum(1 for v in verdicts if v["notable"])
    ledger({"event": "cycle", "cycle": cycle, "pages": len(pages), "notable": n,
            "review_failed": not verdicts})
    ntfy(f"berserk c{cycle:02d} done", f"{n} of {len(pages)} notable")
    log(f"cycle {cycle:02d}: {n} of {len(pages)} notable")
    return verdicts


def report(cycle: int, pages: list[dict], verdicts: list[dict], raw: str, notes: str,
           settings: dict) -> None:
    """berserk/cycles/cNN.md — the one file bekh opens in the morning. Tracked by git, so it
    is written as prose with a table, not as a json dump."""
    os.makedirs(CYCLES, exist_ok=True)
    by_page = {v["page"]: v for v in verdicts}
    out = [f"# berserk cycle {cycle:02d}", "",
           time.strftime("%b %-d, %Y %H:%M"), ""]
    if settings:
        out += ["settings: " + " · ".join(f"{k} {v}" for k, v in settings.items()), ""]
    if notes:
        out += ["bekh's notes for this cycle:", "", "> " + notes.replace("\n", "\n> "), ""]
    out += ["| room | seed | bits | forks | picker failures | notable |",
            "| --- | --- | --- | --- | --- | --- |"]
    for p in pages:
        forks = cycle_forks(cycle, p["room"])
        fails = sum(1 for r in forks if r.get("picker_failed"))
        v = by_page.get(p["room"])
        out.append(f"| {p['room']} | {p.get('seed', '')} | {p.get('bits', 0):g} | "
                   f"{len(forks)} | {fails} | "
                   f"{'yes' if v and v['notable'] else 'no'} |")
    out.append("")
    if raw:
        out += ["The reviewer's answer could not be read twice; nothing is marked notable.",
                "Its last answer, verbatim:", "", "```", raw.strip(), "```", ""]
    for p in pages:
        room = p["room"]
        v = by_page.get(room)
        out.append(f"## {room}" + ("  — notable" if v and v["notable"] else ""))
        out.append("")
        if v:
            out += [v["why"] or "(no reason given)", ""]
            if v.get("quote"):
                out += ["> " + str(v["quote"]).replace("\n", "\n> "), ""]
        out += [f"[the page](https://eva.x/api/artifact/text?name={room}) · forks:", ""]
        for r in cycle_forks(cycle, room):
            mark = " **(picker failed)**" if r.get("picker_failed") else ""
            close = " (closing)" if r.get("closing") else ""
            out.append(f"{r.get('fork')}.{close} *{r.get('genre') or '—'}* — "
                       f"{r.get('note') or ''}{mark}")
        out.append("")
    path = os.path.join(CYCLES, f"c{cycle:02d}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    log(f"report written: {path}")


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
    for name in ("cycle", "page", "review"):
        p = sub.add_parser(name)
        p.add_argument("--cycle", type=int)
        p.add_argument("--notes")
        if name != "review":
            p.add_argument("--forks", type=int, default=15)
            p.add_argument("--fan", type=int, default=15)
            p.add_argument("--predict", type=int, default=35)
        if name == "cycle":
            p.add_argument("--pages", type=int, default=5)
        if name == "page":
            p.add_argument("--page", type=int, default=1)
    a = ap.parse_args()

    cycle = a.cycle if a.cycle else next_cycle()
    notes_path = a.notes or os.path.join(NOTES, f"c{cycle:02d}.md")
    notes = notes_text(notes_path)
    log(f"cycle {cycle:02d} · notes {'yes' if notes else 'none'} ({notes_path})")

    if a.cmd == "review":
        do_review(cycle, notes)
        state_clear()
        return 0
    settings = {"pages": getattr(a, "pages", 1), "forks": a.forks, "fan": a.fan,
                "predict": a.predict}
    if a.cmd == "page":
        r = do_page(cycle, a.page, a.forks, a.fan, a.predict, notes)
        state_clear()
        return 1 if r.get("error") else 0
    for page in range(1, a.pages + 1):
        do_page(cycle, page, a.forks, a.fan, a.predict, notes)
    do_review(cycle, notes, settings)
    # Only here, and deliberately not in a finally: state.json outliving the process is how
    # the monitor says "it died mid-walk". Wipe it on a crash and a dead run looks finished.
    state_clear()
    return 0


if __name__ == "__main__":
    sys.exit(main())
