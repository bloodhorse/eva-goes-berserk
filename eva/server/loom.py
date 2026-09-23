#!/usr/bin/env -S uv run --python 3.12
"""loom.py — a document, a tree of continuations, and one browser to walk them in.

Run it: `uv run --python 3.12 loom.py` (the shebang above says the same thing, so
`./loom.py` works too). Stdlib only, on purpose — no venv to rot, no lockfile, nothing
to install on a box that already has python. Prints one line with the url and stops
there; it does not open a browser, because a tool that grabs the foreground is a tool
you stop leaving running.

What this process actually is: **a file store and a proxy, and nothing else.** The tree
lives in the page — the browser owns it, mutates it, and posts the whole thing back
after every change. That is deliberate. A sitting is text, a few tens of KB at worst,
and a server that also held the tree would be a second copy of the same structure with
its own opinions about what "pick" means, which is how two sources of truth start. On
reload the file is the truth; between reloads the page is.

No auth of any kind, and none is coming. Bind loopback and keep it there: anyone who can
reach this port can read every sitting on the disk and spend the whole GPU. The default
host is 127.0.0.1 and the only reason LOOM_HOST exists is a box where llama-server lives
somewhere else and you want the page on the tailnet — that is a decision, not a default.

  GET  /                     -> loom.html, re-read per request (edit it, hit reload)
  GET  /manifest.webmanifest -> what makes the page installable: added to an iPhone's home
                               screen it opens standalone, with no browser chrome at all
  GET  /icon-180.png         -> the home-screen icon (and /icon-192.png, /icon-512.png),
                               out of eva/front/icons/ — cached hard, unlike everything else
  GET  /api/health           -> {"ok", "llama", "readonly", "synced"}: is there a model behind
                                the port, and is this the mirror (synced = when the mac last
                                pushed the shelf to it, epoch seconds)
  GET  /api/sittings         -> the shelf, newest first — the whole tree, folders and all,
                               in one call; a room's name IS its path under sittings/
  GET  /api/folder?name=     -> one folder as the canvas reads it: every room under it,
                               sub-folders included, each with its nodes cut down to what
                               a picture of an experiment needs
  GET  /api/canvases         -> every board under shelf/canvases/ as {name, title, folder},
                               by name: a board is a saved canvas, a title and a list of rooms
  GET  /api/canvas?name=     -> one board as the canvas reads it — the same payload as
                               /api/folder, built from the rooms the board lists, plus
                               `board` and `title`; rooms that are gone are skipped
  GET  /stream               -> eva/front/stream.html, the reader for the dream stream
  GET  /stream/plate/<date>/<HHMM>.jpg -> the painting made for that dream, if there is one
  GET  /api/stream           -> the stream's pages, newest first: ?before=<room> pages
                               backwards, ?n=<k> how many, ?all=1 includes the ones the
                               filter flagged. Plus `status`, off the worker's heartbeat, and
                               where the interpreter has been: each page's `marked` copy and
                               its `segments`, the `reading` on the page that heads a block,
                               and the `story` of the pack of dreams each page belongs to.
                               Each page carries its `model` — who dreamt it, the writer's
                               seat name, or an older page's file name shortened — and its
                               `name` (the reader's, else the naming store's) and its
                               `verse`, `"12:3"` — the third scene of
                               the twelfth story; a story carries its `title` and `chapter`,
                               and its `text` — one continuous telling, seams marked with `|` —
                               beside `parts`, that same text cut at those seams, one per scene
  GET  /api/stream/events    -> the same stream, pushed: text/event-stream, held open, one
                               `event: change` with {"rooms": [the ones whose fingerprint
                               moved], "status": …} within ~2s of a passage, a note, a story,
                               a plate or a name landing, and a `: keepalive` comment between
                               them. A GET, so the mirror serves it too. And `event: live`
                               with {"text", "seed", "done", "model", "ts"} the moment the
                               writer posts the dream it is writing — first thing on connect,
                               too, while one is being written
  POST /api/stream/live      -> {"text": all of it so far, "seed", "done", "model"}: the
                               writer's dream while a dreamer writes it (`model` is which one,
                               optional), held in memory (never on disk) and pushed
                               down every held events connection. 403 on the mirror, whose
                               live state comes from LOOM_LIVE_UPSTREAM instead
  POST /api/mark           -> {"room", "node", "mark": "kept"|"good", "on"}: one branch
                               marked, in the room itself — the same flags the choose screen
                               leaves. `kept` goes in an artifact; `good` only says he liked
                               reading it, and nothing downstream reads it. A branch wears
                               AT MOST ONE: turning one on turns the other off, and the
                               answer carries the state of both after the write
  POST /api/keep             -> {"room", "node", "kept"}: /api/mark spelled the old way, for
                               anything written before there were two marks
  GET  /api/sitting?name=    -> one whole tree
  POST /api/sitting          -> the whole tree, written atomically
  POST /api/move             -> {"from", "to"}: a room or a whole folder moves; rename is a
                               move; folders on the way are made, emptied ones are dropped
  POST /api/delete           -> {"name"}: the sitting moves to sittings/.trash, off the shelf
  GET  /api/notes            -> storage: every note's name, newest first
  GET  /api/note?name=       -> {"name", "text"}
  POST /api/note             -> {"name", "text", "create"}: add (blank name = random hex,
                                taken name refused) or overwrite an existing one
  POST /api/clear            -> {"name"}: a COPY goes to sittings/.trash; the page then resets
                                the tree to its root and saves, the room itself stays
  POST /api/complete         -> {"prompt", "params"} through to llama's /completion; the
                                answer carries `probs` when params asked for n_probs
  POST /api/tokenize         -> {"contents": [str, …]} through to llama's /tokenize, so the
                                sampler drawer can turn words into the token ids logit_bias
                                actually listens to
  POST /api/cancel           -> hang up on every completion in flight
  GET  /api/berserk?name=    -> a room the berserk daemon walked, as the record it left:
                                the room itself, its fork rows off the ledger (each with the
                                lead its fan was finishing), and the document as it came out
  GET  /api/berserk/text?name= -> that document alone, plain text, to read or send
  GET  /api/artifacts        -> every artifact's name, title, created, steps, kept and fan
                                size, newest first
  GET  /api/artifact?name=   -> one artifact, whole
  GET  /api/artifact/text?name= -> that walk as one plain-text document, to read or send
  POST /api/artifact         -> {"room", "parent", "kept": [node ids], "name"?}: the server
                                reads that room off the disk, walks the path that reached
                                `parent`, and freezes every fork along it — the line taken,
                                the branches kept beside it — writing the file once; a taken
                                name is 409, never an overwrite
                             -> {"room", "parent", "sync": true}: what a star does. That fan's
                                own artifact is rebuilt from the kept flags on disk, made if it
                                isn't there, and put in artifacts/.trash when the last star goes

Env: LOOM_HOST, LOOM_PORT (8082 — 8080 is llama-server, 8081 is fim), LOOM_LLAMA,
LOOM_SITTINGS, LOOM_STORAGE, LOOM_ARTIFACTS, LOOM_LEDGER, LOOM_CANVASES, LOOM_READONLY (1 = the mirror: every POST 403 but marks),
LOOM_MARKS (the mirror's mark journal, replayed on the mac by eva/mirror/push.sh),
LOOM_STREAM_PAGE, STREAM_DIR and STREAM_INTERVAL (the dream stream — eva/stream/),
STREAM_EVENTS_TICK / STREAM_EVENTS_KEEPALIVE / STREAM_EVENTS_ROOMS (the held connection above),
STREAM_LIVE_STALE (600 s: a live dream older than that is a writer that died mid-dream),
LOOM_LIVE_UPSTREAM (the mirror: another loom whose live events this one pulls and passes on)
and LOOM_LIVE_RETRY_MAX (30 s, the longest wait between two tries at that upstream).
"""

from __future__ import annotations

import hashlib
import http.client
import json
import math
import os
import re
import secrets
import shutil
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))     # eva/server
ROOT = os.path.dirname(os.path.dirname(HERE))          # the repo: eva/ (code), shelf/ (text), docs/
# The page is in eva/front, a folder over: the server is a file store and a proxy, the front
# is the thing bekh looks at, and keeping them apart is what lets either be read alone.
# LOOM_PAGE exists for the mobile rig, which serves a doctored copy from a scratch dir.
PAGE = os.environ.get("LOOM_PAGE", os.path.join(ROOT, "eva", "front", "loom.html"))
# The home-screen icons, generated once by front/icons/make.py and committed. Beside the
# page and not beside the server: they are what the page looks like, not something it stores.
ICONS = os.path.join(ROOT, "eva", "front", "icons")
ICON_SIZES = (180, 192, 512)
HOST = os.environ.get("LOOM_HOST", "127.0.0.1")
PORT = int(os.environ.get("LOOM_PORT", "8082"))
LLAMA = os.environ.get("LOOM_LLAMA", "http://127.0.0.1:8080").rstrip("/")
# Everything the instruments write goes on the shelf, by kind. The env overrides exist only
# so the tests (and the rig) can run against scratch dirs instead of the real ones.
SHELF = os.path.join(ROOT, "shelf")
# The mirror on the mini (eva/mirror/): the same server over a copy of the shelf the mac
# pushes every minute, answering only while the mac is off. Every POST is refused, so there
# is never a second writer — whatever the page does there, the mac's shelf is the only one.
READONLY = os.environ.get("LOOM_READONLY") == "1"
# The push script stamps this after each successful sync; outside the shelf, because the
# shelf is rsynced with --delete and would wipe it.
SYNCED = os.path.join(ROOT, ".synced")
# The one write the mirror takes: a mark. Harvesting is what the phone is for, so a keep or a
# good made with the mac off lands in the mirror's copy of the room (so the page shows it) AND
# as a line here, which the mac's push replays through its own /api/mark before it pushes
# again. Outside the synced folder, or rsync --delete would take the journal with it. Unset =
# the mirror refuses marks like everything else.
MARKS_JOURNAL = os.environ.get("LOOM_MARKS", "")
SITTINGS = os.environ.get("LOOM_SITTINGS", os.path.join(SHELF, "sittings"))
# Storage: findings bekh wants to keep, one plain .txt per note, nothing but the text in it.
# Tracked by git on purpose (sittings are not) — a finding is worth its history.
STORAGE = os.environ.get("LOOM_STORAGE", os.path.join(SHELF, "storage"))
NOTE_MAX = 120
# Artifacts: one walk each, frozen — the document it started from and every fork along the
# way, with only the branches bekh kept. The opposite of a sitting on every axis: written
# once and never again, tracked by git and pushed. A room is a place to work; an artifact is
# what came out of it.
ARTIFACTS = os.environ.get("LOOM_ARTIFACTS", os.path.join(SHELF, "artifacts"))
# The berserk daemon's ledger, one json object per line. Read here and never written: the
# loom is the SECOND reading of that record, not a second writer of it. The first is the
# html page on the sheets site — same rows, same rooms, one drawn for a phone in bed and one
# for the screen where the rooms already live. LOOM_LEDGER is the tests' scratch override.
LEDGER = os.environ.get("LOOM_LEDGER", os.path.join(SHELF, "berserk", "ledger.jsonl"))
# Canvases (boards): one small json each, a title and the rooms it draws — a picture saved
# apart from where its rooms are filed, so one room can sit on three boards and a folder can
# be cut into four. Written by hand or by a script, never by this server: read only here.
CANVASES = os.environ.get("LOOM_CANVASES", os.path.join(SHELF, "canvases"))
# The dream stream (eva/stream/): its rooms are ordinary rooms under sittings/stream/, so
# everything above already reads them — what is new here is a second PAGE with nothing on it
# but the newest one, and the worker's heartbeat, which is the only thing on disk that can
# say whether the machine is still dreaming. Read here and never written: the loom is the
# reader of that record, exactly as it is of berserk's ledger.
STREAM_PAGE = os.environ.get("LOOM_STREAM_PAGE", os.path.join(ROOT, "eva", "front", "stream.html"))
STREAM_DIR = os.environ.get("STREAM_DIR", os.path.join(SHELF, "stream"))
STREAM_FOLDER = "stream"                  # where its rooms are filed under SITTINGS
STREAM_INTERVAL = int(os.environ.get("STREAM_INTERVAL", "300"))
# The sleeper's own dial, restated so the server can tell a dream that is still running from
# one that ended without keeping a second opinion about it. Change one and change the other
# (eva/stream/remembering.py). A story ends on its count alone — a stopped stream leaves it
# live, waiting for its next scene.
STREAM_DREAM_TURNS = int(os.environ.get("STREAM_DREAM_TURNS", "4"))
STREAM_N = 10                             # pages per call when nobody says
# A day is 288 passages at one every five minutes, and the page loads a day in one call now
# (bekh, 2026-09-21: load it honestly and stand the viewer at the bottom) — so the cap has to
# clear a day, or the honest bottom would be the middle of yesterday.
STREAM_N_MAX = 400
# /api/stream/events, the held connection that says what changed (see `stream_prints`). The
# tick is how long a landing can wait before a reader sees it; the keepalive is a comment line
# that keeps Cloudflare and caddy from calling a quiet connection idle and closing it; ROOMS
# caps the walk at the newest names, because a reader's window is the newest page or two and a
# shelf that grows for a month should not cost a month per tick.
STREAM_EVENTS_TICK = float(os.environ.get("STREAM_EVENTS_TICK", "2"))
STREAM_EVENTS_KEEPALIVE = float(os.environ.get("STREAM_EVENTS_KEEPALIVE", "20"))
STREAM_EVENTS_ROOMS = int(os.environ.get("STREAM_EVENTS_ROOMS", "400"))
# The dream while it is being written (see `set_live`). A writer that died mid-dream leaves its
# last post behind forever; past this age that post is nobody's dream and a late client must not
# be handed a half-page as if nemo were still at it. Ten minutes is two whole passages.
STREAM_LIVE_STALE = float(os.environ.get("STREAM_LIVE_STALE", "600"))
LIVE_UPSTREAM = os.environ.get("LOOM_LIVE_UPSTREAM", "").rstrip("/")
LIVE_RETRY_MAX = float(os.environ.get("LOOM_LIVE_RETRY_MAX", "30"))
# A passage is 170 tokens, a kilobyte or so. The cap is only there so a broken writer cannot
# park megabytes in memory that every held client is then sent.
LIVE_MAX = 64 * 1024
# How much of a branch he did NOT keep rides along: enough to see what the model could have
# said instead, not so much that the rejects outweigh what was kept.
OPENING = 80


def note_name_ok(name) -> bool:
    """A note name IS its file name, so it gets a looser rule than a sitting (spaces and
    any script are fine) but the same refusal of anything that could leave STORAGE: no
    slash or backslash, no control characters, no leading dot (`..`, hidden files), and
    no edge whitespace that would make two names look the same in the list."""
    return (isinstance(name, str) and 0 < len(name) <= NOTE_MAX and name == name.strip()
            and not name.startswith(".") and not re.search(r"[/\\\x00-\x1f\x7f]", name))

# One segment of a name, and the rule an artifact name still lives by whole: this API has
# no auth in front of it, so a name is the only thing between a request and the filesystem.
# Checked on the way in AND on the way out, because a file dropped in that directory by
# hand is also untrusted input.
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
# A cap on the whole path. Depth is not limited — an experiment files itself as deep as it
# likes — but an unbounded string still becomes a filesystem call, and every OS has an
# opinion about that at some length.
NAME_MAX = 512


def name_ok(name) -> bool:
    """A ROOM name is its path under SITTINGS, without the .json: `experiments/basin/s-01`.

    One validator for every name that becomes a file, so no route, cli or daemon can spell
    a path its own way. Segments are the old name rule; what the rule buys on top of it:

      - no empty segment, so no leading or trailing slash and no `//`
      - no segment starting with a dot — which is `.` and `..` (nothing climbs out of
        SITTINGS) and also `.trash`, so the bin can never be addressed as a room or a
        folder however it is spelled
      - no backslash, no control character: both are already outside the segment charset
    """
    if not isinstance(name, str) or not name or len(name) > NAME_MAX:
        return False
    return all(not seg.startswith(".") and NAME_RE.match(seg) for seg in name.split("/"))

# A completion is minutes, not seconds, on a big model at a long context.
COMPLETE_TIMEOUT = 900
HEALTH_TIMEOUT = 3
# Not sent to llama — llama has never heard of these and answers 400 to unknown fields on
# some builds. They ride in `params` anyway so they get saved and frozen into a node's meta
# with everything else that shaped it: `fan` is how many branches to ask for, `spread` how
# far apart their temperatures are, `dry_keep` the multiplier the dry switch puts back.
LOOM_ONLY = {"fan", "spread", "dry_keep", "logit_bias_text"}

# Below this a temperature is not a temperature any more: llama treats 0 as greedy, and a
# fan of greedy branches is one branch drawn four times.
TEMP_FLOOR = 0.05


def spread_temps(temperature, spread, n: int) -> list[float]:
    """The temperatures of one fan: n values evenly stepped from t-spread to t+spread.

    The instrument, not the seed, is where the strangeness is bought — so a fan is not four
    draws at one temperature but a slice through the range, and the node that comes back
    carries the temperature that actually made it. spread 0 is the old behaviour exactly,
    and must stay that way: it is the default, and every sitting written before this existed
    has no `spread` key at all.

    The floor is applied only to the stepped values. A temperature bekh set himself is his,
    including 0 — clamping that would silently refuse the one setting that means "greedy".
    """
    try:
        t = float(temperature)
    except (TypeError, ValueError):
        t = 1.0
    try:
        s = abs(float(spread or 0))
    except (TypeError, ValueError):
        s = 0.0
    n = max(1, int(n))
    if not s or n < 2:
        return [t] * n
    step = (2 * s) / (n - 1)
    return [round(max(t - s + step * i, TEMP_FLOOR), 4) for i in range(n)]


def trim_probs(probs):
    """llama's `completion_probabilities`, with the weight taken out of it.

    The shape is kept as llama shapes it — id, token, logprob, top_logprobs — because the
    page reads it and the next person to look this up will read llama's README, not ours.
    What goes is `bytes`: a duplicate of `token` as an integer array, which triples the size
    of a sitting for nothing. A 220-token branch keeps its probabilities in ~40 KB; with
    bytes it is three times that, and these files are written after every single move.
    """
    if not isinstance(probs, list):
        return None
    out = []
    for p in probs:
        if not isinstance(p, dict):
            continue
        row = {"id": p.get("id"), "token": p.get("token") or "",
               "logprob": _round_lp(p.get("logprob"))}
        top = []
        for a in (p.get("top_logprobs") or []):
            if isinstance(a, dict):
                top.append({"id": a.get("id"), "token": a.get("token") or "",
                            "logprob": _round_lp(a.get("logprob"))})
        row["top_logprobs"] = top
        out.append(row)
    return out or None


def _round_lp(x):
    """Four places is ~0.01% of probability — finer than anything the page paints, and it
    keeps a float out of json as `-1.7976931348623157e+308` (llama's stand-in for log 0)."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return round(max(v, -40.0), 4)


class Call:
    """One completion in flight, so /api/cancel has something to hang up on.

    `killed` is the whole reason this is a class and not a bare connection: tearing the
    socket down makes the reading thread raise, and without a flag that read looks
    exactly like llama crashing — the page would draw "llama unreachable" for a button
    bekh pressed on purpose.
    """

    def __init__(self, conn: http.client.HTTPConnection) -> None:
        self.conn = conn
        self.killed = False


INFLIGHT: set[Call] = set()
INFLIGHT_LOCK = threading.Lock()


def llama_conn(timeout: int) -> tuple[http.client.HTTPConnection, str]:
    """A fresh connection per call and its path prefix. No pooling: a cancelled call
    leaves its socket in a state nothing should reuse, and a connection costs nothing on
    loopback."""
    u = urlparse(LLAMA)
    conn = http.client.HTTPConnection(u.hostname or "127.0.0.1", u.port or 80, timeout=timeout)
    return conn, (u.path or "").rstrip("/")


def cancel_all() -> int:
    """Pull the floor: shut down every completion socket we are holding.

    `shutdown()` before `close()` and not instead of it — close alone only drops this
    thread's reference and the blocked recv in the request thread keeps waiting for a
    body that is still being generated. shutdown is what makes that recv return now.
    llama-server frees the slot the moment the client goes away, which is the actual
    point: the GPU stops working on a branch nobody wants.
    """
    with INFLIGHT_LOCK:
        calls = list(INFLIGHT)
    for call in calls:
        call.killed = True
        try:
            if call.conn.sock is not None:
                call.conn.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            call.conn.close()
        except OSError:
            pass
    return len(calls)


def complete(prompt: str, params: dict) -> dict:
    """One POST to llama's /completion. Returns the page's shape, or {"error": ...}.

    `/completion` is the raw route: no chat template is applied, and llama inserts BOS
    itself when the prompt is a string and the model asks for one. Nothing here writes a
    special token — hand-writing BOS on top of that gives you two.
    """
    body = {k: v for k, v in (params or {}).items() if k not in LOOM_ONLY}
    body["prompt"] = prompt
    # cache_prompt re-evaluates only the part of the document llama has not seen. On a
    # tree where every branch shares a long prefix this is the difference between a
    # two-second fan and a thirty-second one.
    body["cache_prompt"] = True
    # Streaming would mean an SSE parser here and a second one in the page, for a tool
    # whose whole read is "the finished branch, beside the other three".
    body["stream"] = False
    # llama's n_predict default is -1, which is *infinite*: forget this and a base model
    # that never hits a stop string writes until the context is full.
    try:
        body["n_predict"] = int(body.get("n_predict") or 0) or 220
    except (TypeError, ValueError):
        body["n_predict"] = 220

    conn, prefix = llama_conn(COMPLETE_TIMEOUT)
    call = Call(conn)
    with INFLIGHT_LOCK:
        INFLIGHT.add(call)
    try:
        conn.request("POST", prefix + "/completion",
                     body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        raw = resp.read()
        if resp.status != 200:
            return {"error": f"llama {resp.status}: {raw[:300].decode('utf-8', 'replace')}"}
        d = json.loads(raw)
    except (OSError, http.client.HTTPException, ValueError) as exc:
        # The flag, not the exception type: a cancelled call and a dead llama raise the
        # same OSError, and only one of them is worth a red line in the page.
        return {"error": "cancelled" if call.killed else f"llama unreachable: {exc}"}
    finally:
        with INFLIGHT_LOCK:
            INFLIGHT.discard(call)
        try:
            conn.close()
        except OSError:
            pass

    timings = d.get("timings") or {}
    return {
        # `content` verbatim, and the stop string is NOT in it — llama eats it. Whoever
        # builds the next prompt has to put it back; the page does, as the human node's
        # prefix. See loom.html's `turn`.
        "text": d.get("content") or "",
        "stop_type": d.get("stop_type") or "",
        "stopping_word": d.get("stopping_word") or "",
        "tokens_predicted": d.get("tokens_predicted") or 0,
        "tps": round(float(timings.get("predicted_per_second") or 0.0), 1),
        # None when n_probs is 0, which is also what an older llama build answers — the
        # page treats "no probabilities" and "probabilities off" as the same thing.
        "probs": trim_probs(d.get("completion_probabilities")),
    }


def tokenize(contents: list) -> dict:
    """Spellings to token ids, through llama's /tokenize. {"tokens": [[id, …], …]}.

    This exists because logit_bias's string form does not work on this build: measured
    against nemo, `[["the", -5]]` changed nothing, and the reason is that "the" and " the"
    are different tokens (3265 and 1278) — a bias on the wrong spelling is a bias on a token
    the model was never going to write there. So the page resolves every word to real ids
    and sends ids. One call per spelling; they are four-byte requests on loopback.
    """
    out = []
    for c in contents:
        if not isinstance(c, str) or not c:
            out.append([])
            continue
        conn, prefix = llama_conn(HEALTH_TIMEOUT * 4)
        try:
            conn.request("POST", prefix + "/tokenize",
                         body=json.dumps({"content": c, "add_special": False},
                                         ensure_ascii=False).encode("utf-8"),
                         headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            raw = resp.read()
            if resp.status != 200:
                return {"error": f"llama {resp.status}: {raw[:200].decode('utf-8', 'replace')}"}
            got = json.loads(raw).get("tokens")
            out.append([int(t) for t in got] if isinstance(got, list) else [])
        except (OSError, http.client.HTTPException, ValueError, TypeError) as exc:
            return {"error": f"llama unreachable: {exc}"}
        finally:
            try:
                conn.close()
            except OSError:
                pass
    return {"tokens": out}


def health() -> dict:
    """Never raises. A dead llama-server is a fact about the world, not an error in this
    process — the page draws a red dot and stays usable (you can still read and prune)."""
    if READONLY:
        # No model on the mirror's box, and nothing to ask: generation happens on the mac.
        try:
            synced = os.path.getmtime(SYNCED)
        except OSError:
            synced = None
        return {"ok": False, "llama": None, "readonly": True, "synced": synced}
    out = _llama_health()
    out["readonly"] = False
    return out


def _llama_health() -> dict:
    conn, prefix = llama_conn(HEALTH_TIMEOUT)
    try:
        conn.request("GET", prefix + "/health")
        resp = conn.getresponse()
        raw = resp.read()
        if resp.status != 200:
            return {"ok": False, "llama": None}
        return {"ok": True, "llama": json.loads(raw)}
    except (OSError, http.client.HTTPException, ValueError):
        return {"ok": False, "llama": None}
    finally:
        try:
            conn.close()
        except OSError:
            pass


def model_info() -> dict | None:
    """Which model llama says it has loaded, off /props. None when llama is unreachable or
    answers something that isn't props — an artifact saved with the model down is still an
    artifact, it just can't say what drew it.

    This is the model loaded at SAVE time. The loom never wrote the model into a branch's
    meta, so a fan drawn on nemo and saved after a swap would name the wrong one; on a box
    that runs one model that is a non-case, and the file name is the honest best available.
    """
    conn, prefix = llama_conn(HEALTH_TIMEOUT)
    try:
        conn.request("GET", prefix + "/props")
        resp = conn.getresponse()
        raw = resp.read()
        if resp.status != 200:
            return None
        d = json.loads(raw)
    except (OSError, http.client.HTTPException, ValueError):
        return None
    finally:
        try:
            conn.close()
        except OSError:
            pass
    if not isinstance(d, dict):
        return None
    path = d.get("model_path") if isinstance(d.get("model_path"), str) else ""
    gen = d.get("default_generation_settings")
    return {"file": os.path.basename(path) or None, "path": path or None,
            "n_ctx": gen.get("n_ctx") if isinstance(gen, dict) else None,
            "build": d.get("build_info") or None}


def sitting_path(name: str) -> str:
    """The file a room name points at. Raises on anything that is not a legal name — the
    one gate, so that a caller which forgot to check gets a refusal and not a path."""
    if not name_ok(name):
        raise ValueError(f"bad room name: {name!r}")
    return os.path.join(SITTINGS, *name.split("/")) + ".json"


def folder_path(name: str) -> str:
    """The same name read as a folder. A folder and a room can't share a name — every
    move refuses a target either of them already answers to."""
    if not name_ok(name):
        raise ValueError(f"bad folder name: {name!r}")
    return os.path.join(SITTINGS, *name.split("/"))


def leaf(name: str) -> str:
    """The last segment of a path — the room's own name, without the shelf it sits on."""
    return name.rsplit("/", 1)[-1]


def room_names() -> list[str]:
    """Every room on the shelf as a path relative to SITTINGS, folders walked through."""
    return json_names(SITTINGS)


def json_names(base: str) -> list[str]:
    """Every `.json` under `base` as a name — its path without the extension — that
    `name_ok` passes. Rooms and boards are both spelled this way, so they share one walk.

    Dot-folders are pruned whole, which is how `.trash` stays off the shelf now that the
    shelf has more than one level: it was enough to list only the top directory before.
    """
    out = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        rel = os.path.relpath(dirpath, base)
        prefix = "" if rel == "." else rel.replace(os.sep, "/") + "/"
        for fname in filenames:
            if not fname.endswith(".json"):
                continue
            name = prefix + fname[:-5]
            if name_ok(name):
                out.append(name)
    return out


def resolve_room(name: str) -> str | None:
    """A name as somebody ELSE spells it → the path that room lives at now, or None.

    The berserk ledger names rooms by the bare name the daemon made them with
    (`berserk-c80-p01`) and knows nothing about folders, so a room filed away afterwards
    would drop off its own tree screen and off the link the sheets page prints. A name with
    no slash therefore also matches a room's last segment — and only when exactly one room
    answers to it, because two rooms with the same leaf is a question, not a pick.
    """
    if not name_ok(name):
        return None
    if os.path.isfile(sitting_path(name)):
        return name
    if "/" in name:
        return None
    hits = [n for n in room_names() if leaf(n) == name]
    return hits[0] if len(hits) == 1 else None


# path -> (mtime_ns, size, card). In memory only, and checked against the file on every
# call, so a room copied in by hand or rewritten by census is re-read the moment it changes.
_CARDS: dict[str, tuple[int, int, dict]] = {}


def shelf() -> list[dict]:
    """Every sitting on the disk, newest first, as a card's worth of each.

    Reads every file that changed since the last call. They were small once; a room with
    probs on every token is 1.6 MB now, and parsing the whole 40 MB shelf on each page load
    cost a second. The stat is the index — nothing written to disk, so nothing to go stale
    the first time a file is copied in by hand. The
    whole tree comes back in this one call and the page builds the folders out of the
    paths: a folder is not a thing on disk with a state of its own, it is where rooms are.
    """
    out = []
    # One read of the ledger for the whole list, not one per room: `berserk` is what puts
    # the tree control beside a room in the picker, and the picker is drawn on every boot.
    walked = berserk_rooms()
    seen = set()
    for name in room_names():
        path = sitting_path(name)
        try:
            st = os.stat(path)
            hit = _CARDS.get(path)
            if hit and hit[0] == st.st_mtime_ns and hit[1] == st.st_size:
                card = hit[2]
            else:
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
                card = {
                    "name": name,
                    "title": d.get("title") or name,
                    "created": d.get("created") or 0,
                    "updated": d.get("updated") or 0,
                    "nodes": len(d.get("nodes") or {}),
                }
                _CARDS[path] = (st.st_mtime_ns, st.st_size, card)
        except (OSError, ValueError, AttributeError):
            continue
        seen.add(path)
        # Nobody walked it = no fork rows = nothing for the tree screen to draw. The leaf
        # too: the ledger spells a room by the name it was made with, and a walked room
        # moved into a folder is still a walked room. Not cached: the ledger moves on its own.
        out.append(dict(card, berserk=name in walked or leaf(name) in walked))
    for gone in set(_CARDS) - seen:
        _CARDS.pop(gone, None)
    out.sort(key=lambda s: s["updated"], reverse=True)
    return out


# ---- a folder, as one picture -------------------------------------------------------------
# The canvas draws a whole experiment at once — thirty rooms of thirty branches — and it is a
# camera over one payload, not a screen that fetches as you pan. So this is the one route that
# hands over many rooms' nodes, and it is also the one route that has to be stingy: everything
# a picture of an experiment doesn't paint is dropped here rather than in the browser, because
# the cost is the wire, not the render.

def folder_rooms(name: str) -> list[str]:
    """Every room under this folder, its sub-folders included, by name.

    A folder is not a thing on disk with a state of its own — it exists because rooms are in
    it — so this is a prefix match over the room paths and nothing else, and `.trash` is
    already gone because `room_names` prunes every dot folder.
    """
    prefix = name + "/"
    return sorted(n for n in room_names() if n.startswith(prefix))


def canvas_node(node: dict) -> dict:
    """One node as the canvas reads it: where it hangs, what it says, and the two facts the
    page paints with — the temperature that drew it and the model that wrote it.

    Everything else goes, `probs` above all: one 220-token branch carries ~40 KB of
    probabilities and a folder can hold nine hundred branches. Keys that are false or missing
    are left out for the same reason; the page reads "absent" and "false" as the same thing,
    the way a room on the shelf already does with `kept`.
    """
    meta = node.get("meta") or {}
    params = meta.get("params")
    temp = params.get("temperature") if isinstance(params, dict) else None
    if temp is None:
        temp = meta.get("temperature")
    # Two spellings in the wild: berserk freezes llama's /props object into meta.model, a
    # hand-stamped room may carry the file name alone. Either is the model that wrote it.
    model = meta.get("model")
    if isinstance(model, dict):
        model = model.get("file")
    out = {"parent": node.get("parent"), "kind": node.get("kind"),
           "text": node.get("text") if isinstance(node.get("text"), str) else ""}
    if node.get("posed"):
        out["posed"] = True
    if node.get("kept"):
        out["kept"] = True
    if node.get("good"):
        out["good"] = True
    if temp is not None:
        out["temperature"] = temp
    if isinstance(model, str) and model:
        out["model"] = model
    return out


def folder_canvas(name: str) -> dict | None:
    """A folder's rooms, cut to what the canvas draws. None when no room is under it."""
    rooms = canvas_rooms(folder_rooms(name))
    return {"folder": name, "rooms": rooms} if rooms else None


def canvas_rooms(names: list[str]) -> list[dict]:
    """These rooms, in this order, cut to what the canvas draws — the one builder behind both
    a folder and a board, so the two pictures can never disagree about what a room is.

    The room's own shape is kept — `root`, `current` and the nodes by id — because the page
    redraws the tree out of it: a fan is a node's model children, and which card sits on the
    path root→current is what tells a walk from a census. A name with no readable room behind
    it is skipped, not raised: a picture with a hole in it is still a picture.
    """
    walked = berserk_rooms()
    rooms = []
    for room in names:
        try:
            with open(sitting_path(room), encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue                      # a file that isn't json is not the canvas's problem
        nodes = d.get("nodes")
        if not isinstance(nodes, dict):
            continue
        rooms.append({
            "name": room,
            "title": d.get("title") or room,
            "created": d.get("created") or 0,
            "updated": d.get("updated") or 0,
            "root": d.get("root"),
            "current": d.get("current"),
            "berserk": room in walked or leaf(room) in walked,
            "nodes": {nid: canvas_node(n) for nid, n in nodes.items() if isinstance(n, dict)},
        })
    return rooms


# ---- a board: a canvas saved as a file ----------------------------------------------------
# A folder is where rooms were filed when they were made; a board is how bekh wants to READ
# them — four boards over one folder of twenty wire rooms, one per condition, so a comparison
# is a step from one picture to the next instead of a hunt across one. Its name is its path
# under CANVASES without the .json, through the same `name_ok` as a room, so `..` and dot
# folders are as unaddressable here as on the shelf.

def board_path(name: str) -> str:
    if not name_ok(name):
        raise ValueError(f"bad board name: {name!r}")
    return os.path.join(CANVASES, *name.split("/")) + ".json"


def read_board(name: str) -> dict | None:
    """The board file as a dict, or None when there is none. A file that isn't json raises
    ValueError — a board somebody broke by hand should say so, not read as missing."""
    try:
        with open(board_path(name), encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        return None
    if not isinstance(d, dict):
        raise ValueError("a board is a json object")
    return d


def boards() -> list[dict]:
    """Every board for the menu: name, title and the folder it sits in ('' at the top), by
    name — which is also the order the page's `‹ ›` steps through a folder of them."""
    out = []
    for name in sorted(json_names(CANVASES)):
        try:
            d = read_board(name)
        except (OSError, ValueError):
            continue                      # a broken board is left out of the list, not fatal
        if d is None:
            continue
        title = d.get("title")
        out.append({"name": name,
                    "title": title if isinstance(title, str) and title else leaf(name),
                    "folder": name.rsplit("/", 1)[0] if "/" in name else ""})
    return out


def board_canvas(name: str) -> dict | None:
    """A board as the canvas reads it: `canvas_rooms` over the rooms it lists, plus its name
    and title. None for no such board, or one whose every room has gone.

    A listed room goes through `resolve_room`, so a board may spell a room by its path or by
    the bare name it was made with, and a room filed away since still answers. One that no
    longer exists is skipped. A room listed twice is drawn once — two copies of one block
    would be two sets of marks on one set of nodes.
    """
    d = read_board(name)
    if d is None:
        return None
    listed = d.get("rooms") if isinstance(d.get("rooms"), list) else []
    names = []
    for r in listed:
        path = resolve_room(r) if isinstance(r, str) else None
        if path and path not in names:
            names.append(path)
    rooms = canvas_rooms(names)
    if not rooms:
        return None
    title = d.get("title")
    return {"board": name, "title": title if isinstance(title, str) and title else leaf(name),
            "rooms": rooms}


MARKS = ("kept", "good")
"""The two marks a branch can wear, and the only two. `kept` is "this made me feel something,
keep it"; `good` is "kind of nice, i would not keep it" — the second one exists so a model
comparison has counts to read, which is what `kept` was being spent on while a blind
three-model fan went past, and that is how a mark that means everything comes to mean nothing.

**A branch wears at most one** (2026-09-17): star or circle, never both, and the server is the
one place that rule lives — see set_mark. Nothing downstream — build_artifact above all — has
ever heard of `good`."""


def set_mark(room: str, nid: str, mark: str, on: bool) -> dict:
    """Mark or unmark one branch, in the room itself.

    Turning a mark ON pops the other one in the same read-write, because the two answer one
    question and a card wearing both answers it twice. Turning a mark off touches nothing
    else. One load, one save: a clear and its mark can never land as two writes and leave a
    card wearing both for the length of a disk flush.

    The same flags the choose screen leaves, so a harvest made on the canvas is in the
    rooms and in git, and not in some second list only the canvas knows about. Absent means
    not marked — the key is deleted rather than set false, like every room written before
    keep existed.

    Read and write sit next to each other on purpose. census.py and eva write this file whole
    while they run, so a branch one of them appends between this load and this save is lost,
    and a keep made while a census is appending can be the thing that loses. That is the
    project's dry-run law — a lost fan is an acceptable loss, and no locking is coming — and
    the window is one json load plus one dict lookup wide.

    Returns {"parent", "kept", "good", "cleared"}: the fan this branch hangs off — which a
    keep has to sync — both marks as they now stand, and the marks this write took off to
    make room for `mark`. The caller needs `cleared` because a circle that knocked a star off
    is a star coming off, and that fan's artifact has to follow it.
    Raises FileNotFoundError (no room), KeyError (no such node) and ValueError (not a branch,
    or not a mark we have).
    """
    if mark not in MARKS:
        raise ValueError("no such mark: " + str(mark))
    path = sitting_path(room)
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    node = (d.get("nodes") or {}).get(nid)
    if not isinstance(node, dict):
        raise KeyError(nid)
    if node.get("kind") != "model":
        raise ValueError("only a branch can be marked")
    cleared = []
    if on:
        node[mark] = True
        # The one place the at-most-one rule lives. Every hand that marks — the choose
        # screen, the canvas, the mirror's replay, /api/keep — comes through here, so no
        # caller can leave a card wearing both by forgetting.
        for other in MARKS:
            if other != mark and node.pop(other, None) is not None:
                cleared.append(other)
    else:
        node.pop(mark, None)
    write_sitting(d)
    return {"parent": node.get("parent"), "cleared": cleared,
            "kept": bool(node.get("kept")), "good": bool(node.get("good"))}


def set_kept(room: str, nid: str, kept: bool) -> None:
    """What set_mark was before there were two marks. Kept as a name, not as a second
    implementation: berserk and the walk scripts import loom, and one of them will call this."""
    set_mark(room, nid, "kept", kept)


def prompt_to(sitting: dict, nid: str) -> str:
    """The document root→this node: every text on the path, joined with NOTHING between them.

    A sitting is a tree and a document is one path through it, and this is the answer to "what
    has the model actually been handed". The join is bare concatenation because the turn
    strings already live inside the nodes (a bare room has none at all) — put a separator here
    and the page and the wire would be reading two different documents. berserk.py and
    walk/walk.py carry their own copy of these five lines from before this one existed; new
    callers take this one, so the answer has one home.
    """
    nodes = sitting["nodes"]
    out, n = [], nodes[nid]
    while n:
        out.insert(0, n["text"])
        n = nodes[n["parent"]] if n.get("parent") else None
    return "".join(out)


def check(obj) -> str:
    """The shape, or a sentence saying what is wrong with it. "" means fine.

    Not a schema for its own sake: this file is what the next session reads back, so a
    half-formed tree written now is a sitting lost later. The checks are exactly the
    invariants the page depends on — a root that exists, a current that exists, and
    every node pointing at a parent that is really there.
    """
    if not isinstance(obj, dict):
        return "not an object"
    name = obj.get("name")
    if not name_ok(name):
        return "bad name"
    title = obj.get("title")
    if title is not None and (not isinstance(title, str) or not title.strip() or len(title) > 120):
        return "title must be between 1 and 120 characters"
    nodes = obj.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        return "no nodes"
    for nid, node in nodes.items():
        if not isinstance(node, dict):
            return f"node {nid} is not an object"
        if node.get("id") != nid:
            return f"node {nid} disagrees with its key"
        if node.get("kind") not in ("root", "model", "human"):
            return f"node {nid} has no kind"
        if not isinstance(node.get("text"), str):
            return f"node {nid} has no text"
        parent = node.get("parent")
        if parent is not None and parent not in nodes:
            return f"node {nid} points at a parent that isn't here"
    if obj.get("root") not in nodes:
        return "root isn't a node"
    if obj.get("current") not in nodes:
        return "current isn't a node"
    return ""


def write_sitting(obj: dict) -> float:
    """Temp file then os.replace, because a half-written sitting is worse than no sitting.

    The browser posts the whole tree after every single move, so this runs constantly; a
    crash or a full disk mid-write would otherwise leave a truncated json where an hour
    of branching used to be. os.replace is atomic on the same filesystem — the temp file
    is made in SITTINGS for exactly that reason.
    """
    path = sitting_path(obj["name"])
    # The folders a name names are made here and nowhere else: a room's name IS its path,
    # so `experiments/basin/s-01` posted at a shelf that has no `experiments` is not an
    # error, it is the first room of a new folder.
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ts = time.time()
    obj["updated"] = ts
    tmp = f"{path}.{os.getpid()}.part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)
    return ts


def trash_sitting(name: str, keep: bool = False) -> str:
    """Into SITTINGS/.trash — as a move (Delete) or a copy (Clear), never an unlink.

    Timestamped, so the shelf stops seeing it (shelf() only lists top-level .json) and the
    same room cleared five times keeps five runs instead of the last one clobbering the
    rest. A mis-click is then one `mv` away from undone; an os.remove would have a priest.
    Clear copies rather than moves because the room has to stay on the shelf the whole
    time: the page writes the reset tree over the original right after this returns.
    """
    src = sitting_path(name)
    if not os.path.isfile(src):
        raise FileNotFoundError(name)
    # The bin mirrors the shelf's folders, so two rooms called `smoke-01` in two experiments
    # can both be thrown away without one landing on the other. `.trash` is a dot folder, so
    # nothing under it is ever listed however deep it goes.
    dst = os.path.join(SITTINGS, ".trash", *name.split("/"))
    dst = f"{dst}.{time.strftime('%Y%m%d-%H%M%S')}.json"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if keep:
        shutil.copy2(src, dst)
    else:
        os.replace(src, dst)
        prune_folders(name)
    return dst


def prune_folders(name: str) -> None:
    """Drop the folders the thing at `name` has just left, while they are empty.

    A folder exists because a room is in it — there is no file that says otherwise and no
    way to make one on purpose — so a folder the last room walked out of has to go, or it
    would sit in the move sheet's list of choices forever with nothing behind it. Climbs to
    the sittings root and never touches it: rmdir on SITTINGS would take the shelf.
    """
    rel = name.rsplit("/", 1)[0] if "/" in name else ""
    while rel:
        try:
            os.rmdir(os.path.join(SITTINGS, *rel.split("/")))
        except OSError:
            return          # not empty, or already gone: either way stop climbing
        rel = rel.rsplit("/", 1)[0] if "/" in rel else ""


def stamp_name(path: str, name: str) -> None:
    """Write the room's new path into the file as its `name`.

    A sitting carries its own name and every writer posts the whole object back, so a moved
    file still saying where it used to live would be saved straight back there by the next
    write_sitting — the move would undo itself the first time anybody typed a line. Written
    in place, temp-then-replace, with `updated` left alone: a move is not a new version of
    the room and must not reorder the shelf.
    """
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return              # a file that isn't json is not ours to rewrite; it still moved
    if not isinstance(d, dict) or d.get("name") == name:
        return
    d["name"] = name
    tmp = f"{path}.{os.getpid()}.part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, path)


def move_room(src: str, dst: str) -> int:
    """Move a room or a whole folder to `dst`, and say how many rooms went. Rename is this.

    Raises ValueError (a bad path, or a folder into itself), FileNotFoundError (nothing at
    `src`) and FileExistsError (something already at `dst`) — the handler turns those into
    400, 404 and 409. One os.rename does the work, which is atomic on one filesystem and is
    why nothing here has to cope with half a folder having arrived.
    """
    if not name_ok(src) or not name_ok(dst):
        raise ValueError("a path is segments of letters, digits, _ . - "
                         "with no empty segment and none starting with a dot")
    if src == dst:
        raise ValueError("that is where it already is")
    room, folder = os.path.isfile(sitting_path(src)), os.path.isdir(folder_path(src))
    if not room and not folder:
        raise FileNotFoundError(src)
    if os.path.exists(sitting_path(dst)) or os.path.isdir(folder_path(dst)):
        raise FileExistsError(dst)
    # `experiments` into `experiments/basin` would rename a directory into itself and, on
    # some filesystems, quietly succeed at losing it.
    if folder and (dst + "/").startswith(src + "/"):
        raise ValueError("a folder can't move inside itself")

    from_, to = (sitting_path(src), sitting_path(dst)) if room \
        else (folder_path(src), folder_path(dst))
    os.makedirs(os.path.dirname(to), exist_ok=True)
    os.rename(from_, to)
    prune_folders(src)
    if room:
        stamp_name(to, dst)
        return 1
    n = 0
    for name in room_names():
        if name == dst or name.startswith(dst + "/"):
            stamp_name(sitting_path(name), name)
            n += 1
    return n


def note_path(name: str) -> str:
    return os.path.join(STORAGE, name + ".txt")


def notes() -> list[dict]:
    """Every note, newest first by file time — a hand edit in the folder counts as new."""
    out = []
    try:
        names = os.listdir(STORAGE)
    except OSError:
        return out
    for fname in names:
        if not fname.endswith(".txt") or not note_name_ok(fname[:-4]):
            continue
        try:
            out.append({"name": fname[:-4],
                        "updated": os.path.getmtime(os.path.join(STORAGE, fname))})
        except OSError:
            continue
    out.sort(key=lambda n: n["updated"], reverse=True)
    return out


def write_note(name: str, text: str) -> None:
    """Exactly the text, nothing else — no header, no trailing newline added. newline=""
    so python never rewrites line endings in something he pasted."""
    os.makedirs(STORAGE, exist_ok=True)
    path = note_path(name)
    tmp = os.path.join(STORAGE, f".{secrets.token_hex(6)}.part")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, path)


def artifact_path(name: str) -> str:
    return os.path.join(ARTIFACTS, name + ".json")


def bits_of_keeping(n: int, k: int) -> float:
    """log2(C(n, k)): the bits it takes to say WHICH k of n branches were kept.

    janus's measure, the same one eva.py's `curation` takes along a path, where a pick is
    log2(n/m) — how hard the filter squeezed. For one kept branch the two are the same
    number, log2(n). They part at k > 1, and on purpose: an artifact records the exact
    subset, and two named branches out of six (C(6,2) = 15, 3.9 bits) is more of bekh in
    the file than "a third of them survived" (log2 3, 1.6 bits). Keeping all of them, or
    a fan of one, is no choice at all: 0.
    """
    if n < 2 or k < 1 or k >= n:
        return 0.0
    return math.log2(math.comb(n, k))


def spine(nodes: dict, start) -> list[dict]:
    """root→`start` as a list of nodes, root first — the document as one line of blocks.

    The seen-set is only there because check() doesn't look for cycles, and a hand-edited
    file with one would hang this request forever.
    """
    out, seen, n = [], set(), nodes.get(start)
    while n and n["id"] not in seen:
        seen.add(n["id"])
        out.insert(0, n)
        n = nodes.get(n["parent"]) if n["parent"] else None
    return out


def build_artifact(sitting: dict, parent, kept, name: str) -> dict:
    """The WALK that reached this fan, frozen: the document it started from, then one step
    per fork along the way — the line bekh took, the branches he kept beside it, and the
    rest of that fan as openings. Raises ValueError with a sentence the page can show.

    The spine is root→`current`, because that is the document as it stands. The curation is
    the `kept: true` flags he left on cards while walking, so freezing asks for no new
    gesture — he keeps as he goes and saves at the end. `parent` is the fan he has open when
    he saves, and for THAT fork the posted ids win over the flags: what is on his screen now
    is the newer statement. It is also always a step, whatever its size — a branch he named
    by hand is never silently dropped — while a fork found on the spine has to have had
    something to choose between, so a fan of one is not a step.

    Built here and not in the page, so there is one place that decides what an artifact is,
    and the tests can hold it to that. The room is the one ON DISK — the page saves before
    it asks — because the file is what anyone can check the artifact against later.
    """
    why = check(sitting)
    if why:
        raise ValueError(f"that room doesn't read: {why}")
    nodes = sitting["nodes"]
    if not isinstance(parent, str) or parent not in nodes:
        raise ValueError("the fan point isn't a node of that room")
    if not isinstance(kept, list) or not kept:
        raise ValueError("nothing is kept — keep at least one branch")
    ids: list[str] = []
    for k in kept:
        if not isinstance(k, str):
            raise ValueError("kept is a list of node ids")
        if k not in ids:
            ids.append(k)

    def fan_of(pid):
        # The fan as the page lists it: model children of the fan point, oldest first —
        # pruned ones included, because they were written and not keeping them is part of
        # the choice. sorted() is stable, like the page's sort, so two branches with one ts
        # keep file order.
        return sorted((n for n in nodes.values()
                       if n.get("parent") == pid and n.get("kind") == "model"),
                      key=lambda n: n.get("ts") or 0)

    here = {n["id"] for n in fan_of(parent)}
    for k in ids:
        if k not in here:
            raise ValueError(f"{k} isn't a branch of that fan")

    walk = spine(nodes, sitting.get("current"))
    if parent not in [n["id"] for n in walk]:
        # He saved from a fan that is not under the document as it stands — a room walked
        # back, or a side branch opened from the menu. The path that reached THAT fan is the
        # honest spine; the rest of the tree is roads not taken.
        walk = spine(nodes, parent)
    pidx = [n["id"] for n in walk].index(parent)

    # Fan point → the line taken there, for every fork on the spine, in document order. The
    # fan he has open gets an entry with no line taken yet (setdefault leaves it alone if he
    # already picked there and walked on).
    forks = {i - 1: i for i, n in enumerate(walk)
             if i and n.get("kind") == "model"
             and (len(fan_of(n["parent"])) > 1 or n["parent"] == parent)}
    forks.setdefault(pidx, None)

    def temp_of(node):
        # The page and census freeze the whole sampler into meta.params; a branch written by a
        # one-off script may carry only a bare meta.temperature. Either is the real draw.
        meta = node.get("meta") or {}
        p = meta.get("params")
        if isinstance(p, dict) and p.get("temperature") is not None:
            return p.get("temperature")
        return meta.get("temperature")

    def row(s, at):
        # probs out: 40 KB per branch of numbers nobody reads off a frozen card, in a file
        # that lives in git forever.
        meta = {k: v for k, v in (s.get("meta") or {}).items() if k != "probs"}
        return {"id": s["id"], "at": at, "text": s["text"], "temperature": temp_of(s),
                "posed": bool(s.get("posed")), "meta": meta}

    def opening(s, at):
        return {"id": s["id"], "at": at, "opening": s["text"][:OPENING],
                "length": len(s["text"]), "temperature": temp_of(s),
                "pruned": bool(s.get("pruned"))}

    prompt, steps, total = "", [], 0.0
    reach = None        # how far down the spine the document has been written out already
    for head_i, took_i in sorted(forks.items()):
        head, took = walk[head_i], (walk[took_i] if took_i is not None else None)
        sibs = fan_of(head["id"])
        at = {s["id"]: i + 1 for i, s in enumerate(sibs)}
        # Everything between the last line taken and this fan point — his own lines, mostly.
        # prompt + every step's (lead + the line taken) is the document, verbatim, again.
        if reach is None:
            prompt = "".join(n["text"] for n in walk[:head_i + 1])
            lead = ""
        else:
            lead = "".join(n["text"] for n in walk[reach + 1:head_i + 1])
        reach = head_i if took is None else took_i
        chosen = set(ids) if head["id"] == parent else {s["id"] for s in sibs if s.get("kept")}
        if took is not None:
            chosen.discard(took["id"])      # the line taken is the spine, not a flank
        named = chosen | ({took["id"]} if took is not None else set())
        # A branch that says verbatim what a named one says was not a road refused — the same
        # text was on offer twice, so it leaves the pool the choice was made from. Same rule
        # as `curation` in eva.py and the page's ×2: a fan of six with one twin is a pick
        # from five.
        same = {s["text"].strip() for s in sibs if s["id"] in named}
        pool = sum(1 for s in sibs if s["id"] in named or s["text"].strip() not in same)
        bits = bits_of_keeping(pool, len(named))
        total += bits
        steps.append({
            "at": head["id"],
            "lead": lead,
            "took": row(took, at[took["id"]]) if took is not None else None,
            "kept": [row(s, at[s["id"]]) for s in sibs if s["id"] in chosen],
            "fan": {"size": len(sibs),
                    "others": [opening(s, at[s["id"]]) for s in sibs if s["id"] not in named]},
            "bits": round(bits, 3),
        })

    # The spine as nodes, as far as the steps reach, so an artifact can be stood up as a room
    # again with its turns intact: the prompt and the leads are the same text flattened, and a
    # chat room rebuilt from flat text would show its whole conversation as one header.
    blocks = [{"id": n["id"], "kind": n.get("kind"), "text": n["text"],
               "posed": bool(n.get("posed"))} for n in walk[:(reach if reach is not None else 0) + 1]]

    source_title = sitting.get("title") or sitting["name"]
    now = time.time()
    lt = time.localtime(now)
    stamp = f" · {lt.tm_mday} {time.strftime('%b', lt).lower()}"
    return {
        "name": name,
        "title": source_title[:120 - len(stamp)] + stamp,
        "created": now,
        "source": {"room": sitting["name"], "title": sitting.get("title"), "node": parent},
        "model": None,          # filled in by the caller: it is a network call, made last
        "prompt": prompt,
        "turn": json.loads(json.dumps(sitting.get("turn") or {"prefix": "", "suffix": ""})),
        "params": json.loads(json.dumps(sitting.get("params") or {})),
        "steps": steps,
        "blocks": blocks,
        # The walk's bits are the steps' bits ADDED. Each fork is its own choice made on its
        # own fan, so they compose the way curation's log2(n/m) does along a path: two steps
        # of 3.9 bits are 7.8 bits of bekh, not 3.9 twice over.
        "bits": round(total, 3),
    }


def write_artifact(obj: dict) -> None:
    """Once, and never over anything. Raises FileExistsError on a taken name.

    Temp file, then os.link onto the real name: link refuses an existing target, where
    os.replace — what sittings use — would quietly clobber it. So two saves racing for one
    name cannot both win, and the check-then-write gap in the handler is not a hole.
    Indented, because this file is read on github and diffed in git, unlike a sitting.
    """
    os.makedirs(ARTIFACTS, exist_ok=True)
    tmp = os.path.join(ARTIFACTS, f".{secrets.token_hex(6)}.part")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    try:
        os.link(tmp, artifact_path(obj["name"]))
    finally:
        os.unlink(tmp)


def replace_artifact(obj: dict) -> None:
    """The one writer allowed over a name: a star's artifact is a snapshot of its fan as the
    stars stand now, so the next star rewrites it. Temp file then os.replace, like a sitting."""
    os.makedirs(ARTIFACTS, exist_ok=True)
    tmp = os.path.join(ARTIFACTS, f".{secrets.token_hex(6)}.part")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, artifact_path(obj["name"]))


def fan_artifact(room: str, parent: str) -> str | None:
    """The name of the artifact the stars made for this fan, or None.

    Only files marked `"by": "star"` answer: berserk's walks and the artifacts saved by hand
    before stars made them are frozen, and a star must never rewrite one of those."""
    try:
        names = os.listdir(ARTIFACTS)
    except OSError:
        return None
    for fname in names:
        if not fname.endswith(".json") or not NAME_RE.match(fname[:-5]):
            continue
        try:
            with open(os.path.join(ARTIFACTS, fname), encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        src = d.get("source") or {}
        if d.get("by") == "star" and src.get("room") == room and src.get("node") == parent:
            return fname[:-5]
    return None


def sync_artifact(room: str, parent) -> dict:
    """Make this fan's artifact say what its stars say: rebuilt while any branch is kept,
    trashed when none is. A room renamed since the last star gets a new artifact and the old
    one stays where it was — dry run.

    Raises FileNotFoundError (no room) and ValueError (a room or fan point that doesn't read).
    """
    with open(sitting_path(room), encoding="utf-8") as f:
        sitting = json.load(f)
    nodes = sitting.get("nodes") if isinstance(sitting, dict) else None
    if not isinstance(nodes, dict) or not isinstance(parent, str) or parent not in nodes:
        raise ValueError("the fan point isn't a node of that room")
    kept = [n["id"] for n in sorted(
        (n for n in nodes.values() if isinstance(n, dict) and n.get("parent") == parent
         and n.get("kind") == "model" and n.get("kept")),
        key=lambda n: n.get("ts") or 0)]
    name = fan_artifact(room, parent)
    if not kept:
        if name:
            # Out of the list, not out of the world: the same .trash the rooms have.
            bin_ = os.path.join(ARTIFACTS, ".trash")
            os.makedirs(bin_, exist_ok=True)
            os.replace(artifact_path(name),
                       os.path.join(bin_, f"{name}-{int(time.time())}.json"))
        return {"name": None, "gone": name}
    if not name:
        name = secrets.token_hex(6)
        while os.path.exists(artifact_path(name)):
            name = secrets.token_hex(6)
    art = build_artifact(sitting, parent, kept, name)
    art["by"] = "star"
    art["model"] = model_info()
    replace_artifact(art)
    return {"name": name, "title": art["title"], "gone": None}


def artifact_card(d: dict) -> dict:
    """A row for the list: how many steps, how many branches the walk names, out of how
    many the fans offered.

    Two shapes read here and only here, so nothing else has to know: a walk has `steps`,
    and an artifact written before walks existed is one fan with `kept` and `fan` at the
    top. The older files are never rewritten — `steps` is the whole test.
    """
    steps = d.get("steps")
    if isinstance(steps, list):
        # The line taken counts as named too: it is the branch he chose out of that fan.
        kept = sum(len(s.get("kept") or []) + (1 if s.get("took") else 0) for s in steps)
        fan = sum((s.get("fan") or {}).get("size") or 0 for s in steps)
        return {"steps": len(steps), "kept": kept, "fan": fan}
    return {"steps": 0, "kept": len(d.get("kept") or []),
            "fan": (d.get("fan") or {}).get("size") or 0}


def artifact_steps(d: dict) -> list[dict]:
    """A walk's steps, with a pre-walk artifact read as a walk of one step nobody picked
    from. Same two shapes as `artifact_card`, same rule: `steps` is the whole test."""
    steps = d.get("steps")
    if isinstance(steps, list):
        return steps
    return [{"at": (d.get("source") or {}).get("node"), "lead": "", "took": None,
             "kept": d.get("kept") or [], "fan": d.get("fan") or {"size": 0, "others": []},
             "bits": d.get("bits") or 0}]


def artifact_text(d: dict) -> str:
    """The walk as ONE document: the prompt, then every step's lead and the line taken,
    joined with nothing between them — the text the model actually saw and wrote, not a
    transcript of the tree. The branches kept beside the path are left out, this being the
    story and not the fan, except at the open fork it ends on: there nothing was taken and
    those keeps are the only ending there is, each under a bare `[generation begins]`.

    It lives here and not in the page for the same reason `build_artifact` does — one place
    decides what an artifact reads like, and the tests can hold it to that. The page shows
    what this returns; `/api/artifact/text` is the same string at a url.

    Nothing is trimmed. Whitespace at the end of a branch is text the model wrote, and this
    string is the evidence of what it wrote — which is also why it goes out as plain text:
    a base model's document is full of `> > >`, `//` and stray brackets, exactly what a
    markdown reader would swallow.
    """
    steps = artifact_steps(d)
    doc = (d.get("prompt") or "") + "".join(
        (s.get("lead") or "") + ((s.get("took") or {}).get("text") or "") for s in steps)
    last = steps[-1] if steps else None
    if last and not last.get("took"):
        for k in last.get("kept") or []:
            doc += "\n\n[generation begins]\n\n" + (k.get("text") or "")
    m, p = d.get("model") or {}, d.get("params") or {}
    sampler = " · ".join(f"{k} {p[k]}" for k in
                         ("temperature", "min_p", "xtc_probability", "n_predict") if k in p)
    lt = time.localtime(d.get("created") or 0)
    head = "\n".join([
        d.get("title") or d.get("name") or "",
        "model: " + (m.get("file") or "not recorded"),
        "sampler: " + sampler,
        f"walk: {len(steps)} step{'' if len(steps) == 1 else 's'} · "
        f"{round(d.get('bits') or 0, 3):g} bits of curation",
        "saved: " + time.strftime("%b %-d, %Y %I:%M %p", lt),
    ])
    return head + "\n\n" + doc


def artifacts() -> list[dict]:
    """Every artifact, newest first by the time it was made — not file time, because a
    git checkout rewrites every mtime to the moment of the clone."""
    out = []
    try:
        names = os.listdir(ARTIFACTS)
    except OSError:
        return out
    for fname in names:
        if not fname.endswith(".json") or not NAME_RE.match(fname[:-5]):
            continue
        try:
            with open(os.path.join(ARTIFACTS, fname), encoding="utf-8") as f:
                d = json.load(f)
            out.append(dict({"name": fname[:-5], "title": d.get("title") or fname[:-5],
                             "created": d.get("created") or 0},
                            **artifact_card(d)))
        except (OSError, ValueError, AttributeError):
            continue
    out.sort(key=lambda a: a["created"], reverse=True)
    return out


# ---- what berserk left behind -------------------------------------------------------------
# A night the daemon walked is recorded in two places at once: the ROOM, which holds every
# branch of every fan, and the LEDGER, which holds what the reader said about them and which
# branch that resolved to. Neither alone is the record — and the artifact is neither, because
# it keeps the branches nobody took as 80-character openings and not a word of what was said.
# So the tree screen reads these two, through one route, and the sheets page reads the same
# two. Two renderings, one record; a third instrument writing the same rows gets both for free.

def ledger_rows() -> list[dict]:
    """Every line of the ledger that parses, in the order it was written.

    A line that doesn't parse is skipped and is not an error. berserk appends to this file
    while it walks — one row per fork, over hours — so the last line is regularly half on
    disk, and a screen that 500s for the milliseconds a json takes to land is a screen that
    breaks at exactly the moment somebody is watching a run.
    """
    out = []
    try:
        with open(LEDGER, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    out.append(row)
    except OSError:
        return []
    return out


def berserk_rooms() -> set[str]:
    """Which rooms berserk has walked at least one fork of."""
    return {r["room"] for r in ledger_rows()
            if r.get("event") is None and isinstance(r.get("room"), str)}


def berserk_forks(name: str) -> list[dict]:
    """One room's fork rows, in fork order. A row with an `event` is the run's own
    bookkeeping — a page finished, a cycle finished — and has no fan to draw."""
    rows = [r for r in ledger_rows() if r.get("event") is None and r.get("room") == name]
    # Stable, so two rows that somehow share a fork number keep the order they were written.
    rows.sort(key=lambda r: r.get("fork") or 0)
    return rows


def lead_of(doc: str) -> str:
    """The document's unfinished last line — everything after the last newline.

    Every branch of a fan is finishing THIS, and a 35-token branch nearly always leaves the
    document mid-sentence, so without it a branch that opens on a comma reads as damage
    rather than as the end of somebody else's sentence. berserk's own rule, restated here so
    the screen can say what the reader was actually looking at.
    """
    return doc.rsplit("\n", 1)[-1]


def berserk_text(sitting: dict) -> str:
    """The story as it came out: root down to `current`, joined with nothing between.

    The closing fan is kept and never taken, so `current` is exactly the document that fan
    was drawn under — and mid-walk it is the last branch taken, which is the same answer for
    a page still going. One implementation, like `artifact_text`: the screen, the download
    and the link are the same string or they are three answers to one question.
    """
    return "".join(n["text"] for n in spine(sitting.get("nodes") or {}, sitting.get("current")))


def berserk_room(sitting: dict, rows: list[dict]) -> dict:
    """A walked room as the tree screen reads it: the room, its fork rows, the document.

    `lead` is added per row and is the one thing here that is computed rather than read. It
    is a fact about the room and not about the run, so storing it would be storing an answer
    that can go stale against the file it describes.
    """
    nodes = sitting.get("nodes") or {}
    out = []
    for r in rows:
        ids = r.get("order") or []
        parent = (nodes.get(ids[0]) or {}).get("parent") if ids else None
        row = dict(r)
        row["lead"] = lead_of("".join(n["text"] for n in spine(nodes, parent))) if parent else ""
        out.append(row)
    return {"sitting": sitting, "rows": out, "text": berserk_text(sitting)}


# ---- the dream stream ---------------------------------------------------------------------
# One page every five minutes, written by nobody's hand (eva/stream/). Its rooms are ordinary
# rooms — `stream/<YYYY-MM-DD>/<HHMM>`, a bare root and one model node — so the loom, the
# canvas and the marks already work on them. This section exists for the one thing they do not
# do: hand a PHONE the newest page and nothing else, and say whether the machine is awake.
#
# The order is the NAME's order and not the file's mtime: the names are timestamps, so paging
# backwards costs one directory walk and no json at all until a page is actually wanted.

def stream_room_names() -> list[str]:
    """Every stream room, newest first."""
    try:
        return sorted(folder_rooms(STREAM_FOLDER), reverse=True)
    except ValueError:
        return []


# The interpreter's readings (eva/stream/interpreter.py): one small json per reading, a block
# of rooms with a few sentences about them and, per room, opus's own re-typed copy of the dream
# with its underlines — already diffed against the raw text into render-ready segments. Read
# here and never written, like berserk's ledger. Parsed files are cached on mtime because the
# whole tree is walked per request; when a day of these is thousands of files, index it by day
# instead of walking it all.
_READINGS: dict[str, tuple[int, int, dict]] = {}


def reading_files() -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(STREAM_DIR, "readings")):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fname in filenames:
            if fname.endswith(".json"):
                out.append(os.path.join(dirpath, fname))
    return out


def stream_readings() -> tuple[dict, dict]:
    """(what each room's copy looks like, which room heads which reading).

    `by_room[room]` is `{"marked", "segments"}` — opus's verbatim copy and the diff of it
    against the dream. `heads[room]` is the reading itself, hung off `rooms[0]`, the newest
    passage of its block, which is where the page draws it.
    """
    by_room, heads, seen, loaded = {}, {}, set(), []
    for path in reading_files():
        try:
            st = os.stat(path)
            hit = _READINGS.get(path)
            if hit and hit[0] == st.st_mtime_ns and hit[1] == st.st_size:
                d = hit[2]
            else:
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
                if not isinstance(d, dict):
                    continue
                _READINGS[path] = (st.st_mtime_ns, st.st_size, d)
        except (OSError, ValueError):
            continue
        seen.add(path)
        loaded.append(d)
    # A dream can have more than one note — the seat changed family on 2026-09-21 and
    # `reread.py` exists — and the NEWEST by its own `ts` is the one the page shows. Sorted
    # here and not trusted to file order: the walk hands files over in whatever order the disk
    # likes, so "the later file replaces the earlier" was luck, and three of five re-read
    # dreams kept their old note on the page until this was written.
    for d in sorted(loaded, key=lambda d: d.get("ts") or 0):
        rooms = d.get("rooms") if isinstance(d.get("rooms"), list) else []
        marked = d.get("marked") if isinstance(d.get("marked"), dict) else {}
        segs = d.get("segments") if isinstance(d.get("segments"), dict) else {}
        names = d.get("names") if isinstance(d.get("names"), dict) else {}
        for room in rooms:
            if isinstance(room, str):
                by_room[room] = {"marked": marked.get(room),
                                 "segments": segs.get(room),
                                 # **The name is the menu** (bekh, 2026-09-22). Written by the
                                 # reader with its note; readings from before it existed simply
                                 # have none, and the naming store below covers those.
                                 "name": names.get(room) or None}
        if rooms and isinstance(rooms[0], str) and isinstance(d.get("reading"), str):
            heads[rooms[0]] = {"text": d["reading"], "ts": d.get("ts") or 0, "rooms": rooms}
    for gone in set(_READINGS) - seen:
        _READINGS.pop(gone, None)
    return by_room, heads


# The names of the back catalogue (eva/stream/naming.py): `names/<YYYY-MM-DD>.json` = {room:
# name}, one file per day. Its own store and not a field on a reading, because the ~150 dreams
# dreamt before names existed already HAVE notes, and a naming pass that wrote reading files
# would replace every marked copy on the page with an empty one. Cached on mtime like the
# readings; a note's own name always wins over this.
_NAMES: dict[str, tuple[int, int, dict]] = {}


def stream_names() -> dict:
    """{room: name} across every day's file."""
    out, seen = {}, set()
    root = os.path.join(STREAM_DIR, "names")
    try:
        files = [os.path.join(root, f) for f in os.listdir(root) if f.endswith(".json")]
    except OSError:
        files = []
    for path in files:
        try:
            st = os.stat(path)
            hit = _NAMES.get(path)
            if hit and hit[0] == st.st_mtime_ns and hit[1] == st.st_size:
                d = hit[2]
            else:
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
                if not isinstance(d, dict):
                    continue
                _NAMES[path] = (st.st_mtime_ns, st.st_size, d)
        except (OSError, ValueError):
            continue
        seen.add(path)
        for room, name in d.items():
            if isinstance(room, str) and isinstance(name, str) and name:
                out[room] = name
    for gone in set(_NAMES) - seen:
        _NAMES.pop(gone, None)
    return out


# The third voice (eva/stream/remembering.py): the sleeper remembering. One small json per
# rewrite, a dream's worth of them under a day — what he is handed are scenes of ONE dream, not
# separate ones. Read here and never written, like the readings. What the page wants off them is
# one thing: which pack of dreams a room belongs to, and that pack's latest account.
_DREAMS: dict[str, tuple[int, int, dict]] = {}


def dream_files() -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(STREAM_DIR, "dreams")):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fname in filenames:
            if fname.endswith(".json"):
                out.append(os.path.join(dirpath, fname))
    return out


def story_parts(d: dict) -> list[str]:
    """The telling cut at its seams (`eva/stream/remembering.py`, `split_parts`).

    **The `|` never leaves `text`**: it is what the sleeper wrote and the shelf keeps it, marks
    and all. `parts` rides beside it so the page — and anything else reading this — does not
    re-implement the split. The stored list is used when it is there; a version written before
    the seams existed is split here, which for an unmarked telling is the whole of it as one
    part. Nothing is validated: the wrong number of marks is the wrong number of parts, and the
    page holds the mismatch.
    """
    saved = d.get("parts")
    if isinstance(saved, list) and all(isinstance(p, str) for p in saved) and saved:
        return saved
    return [p.strip() for p in (d.get("text") or "").split("|")]


def stream_stories() -> tuple[dict, str | None, dict]:
    """({room: the story that room belongs to}, the id of the live one, {room: "12:3"}).

    **A story belongs to a pack of dreams** (bekh, 2026-09-21). There is no current-versus-
    finished distinction to make here: a pack is four dreams, the newest pack may not be full
    yet, and that is the whole of it. So every room a dream's versions ever covered carries
    that dream's LATEST account, and the page groups the rooms that share one into a pack.

    `live` is the one state left: the newest dream overall, while it is inside its gap and
    under its scene cap. Only a live pack shows a count.

    **Chapter and verse** (bekh, 2026-09-22): a story is a chapter, a scene is a verse, and
    `12:3` is the third scene of the twelfth story. Both numbers are READ, never counted here —
    the chapter is stamped on the version when the story starts and the verse is that version's
    own `turn`. A version written before the numbering has no chapter and its room has no
    verse; `remembering.py --number` is the backfill.
    """
    rows, seen = [], set()
    for path in dream_files():
        try:
            st = os.stat(path)
            hit = _DREAMS.get(path)
            if hit and hit[0] == st.st_mtime_ns and hit[1] == st.st_size:
                d = hit[2]
            else:
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
                if not isinstance(d, dict) or not isinstance(d.get("text"), str):
                    continue
                _DREAMS[path] = (st.st_mtime_ns, st.st_size, d)
        except (OSError, ValueError):
            continue
        seen.add(path)
        if isinstance(d.get("dream"), str):
            rows.append(d)
    for gone in set(_DREAMS) - seen:
        _DREAMS.pop(gone, None)
    rows.sort(key=lambda d: d.get("ts") or 0)

    latest: dict[str, dict] = {}          # dream id -> its newest version
    members: dict[str, list[str]] = {}    # dream id -> every room it covers
    first: dict[str, dict] = {}           # room -> the version that brought it in
    for d in rows:
        latest[d["dream"]] = d
        if isinstance(d.get("room"), str):
            members.setdefault(d["dream"], []).append(d["room"])
            # The FIRST version covering a room is the one whose turn is that room's verse: a
            # rewrite of the same scene under a new name would otherwise renumber it.
            first.setdefault(d["room"], d)

    live = None
    if rows:
        last = latest[rows[-1]["dream"]]
        if (last.get("turn") or 0) < (last.get("of") or STREAM_DREAM_TURNS):
            live = last["dream"]

    by_room, verses = {}, {}
    for dream, rooms in members.items():
        d = latest[dream]
        chapter = d.get("chapter") if isinstance(d.get("chapter"), int) else None
        story = {"dream": dream, "text": d["text"], "parts": story_parts(d),
                 "turn": d.get("turn") or 0,
                 "of": d.get("of") or STREAM_DREAM_TURNS, "live": dream == live,
                 # The name the sleeper gave it, off the LATEST version — a story renamed as it
                 # was rewritten is a story that turned out to be about something else.
                 "title": d.get("title") or None,
                 "chapter": chapter}
        for room in rooms:
            by_room[room] = story
            turn = (first.get(room) or {}).get("turn")
            if chapter and isinstance(turn, int):
                verses[room] = f"{chapter}:{turn}"
    return by_room, live, verses


# A plate is one painting per room, made by hand with eva/stream/plate.py. Served as a file
# and never read into a payload: it is a quarter of a megabyte, and the page puts it behind the
# passage's text as a background image.
def plate_path(room: str) -> str | None:
    """The jpg for this room, or None. The path is built from a name `name_ok` has passed and
    from nothing else — this is the one route here that hands back a file off the disk."""
    parts = room.split("/")
    if len(parts) != 3 or not name_ok(room):
        return None
    path = os.path.join(STREAM_DIR, "plates", parts[1], parts[2] + ".jpg")
    return path if os.path.isfile(path) else None


def plate_url(room: str) -> str | None:
    """`/stream/plate/<date>/<HHMM>.jpg?v=<mtime>`. The stamp is what lets the file be cached
    hard and still change: a re-run replaces the plate under the same name."""
    path = plate_path(room)
    if not path:
        return None
    parts = room.split("/")
    try:
        v = int(os.path.getmtime(path))
    except OSError:
        v = 0
    return f"/stream/plate/{parts[1]}/{parts[2]}.jpg?v={v}"


def stream_model(meta: dict) -> str | None:
    """Who wrote a stream page, as a short name for the head of the dream.

    Since 2026-09-23 the writer stamps the seat's own name (`nemo`, `gpt2`) and that passes
    untouched. Pages from before — and any written on the one-server path — carry the model's
    FILE name, which is shortened here and not mapped: `Mistral-Nemo-Base-2407.Q5_K_M.gguf` →
    `mistral-nemo-base-2407`, the extension and the quant off, lowercased because the page is.
    No table of known files, so a model nobody listed still says what it is. The room keeps the
    stamp as written; this is display, the way the ragged-end trim is.
    """
    m = meta.get("model")
    if isinstance(m, dict):                     # berserk's shape: llama's whole /props
        m = m.get("model_path")
    if not isinstance(m, str) or not m:
        return None
    m = os.path.basename(m)
    if m.lower().endswith(".gguf"):
        m = re.sub(r"\.(?:i?q\d[\w]*|f16|f32|bf16)$", "", m[:-5], flags=re.I)
    m = m.lower()
    # One dreamer, one name: the ~200 pages written before the seats existed carry nemo's
    # file name, and a feed that says `mistral-nemo-base-2407` above them and `nemo` above
    # tonight's is two dreamers where there is one. The only alias, for the only model that
    # wrote pages before it had a seat name.
    if m.startswith("mistral-nemo"):
        return "nemo"
    return m


def stream_page(name: str, readings: tuple[dict, dict] | None = None,
                stories: dict | None = None, verses: dict | None = None,
                names: dict | None = None) -> dict | None:
    """One page as the reader reads it: the seed, the page, the two marks, the flag, and — when
    the interpreter has been past — its copy of the dream and the reading it heads.

    None for a room that isn't one of the worker's — a hand-made room filed under `stream/`,
    or a file that stopped being json. The node id goes out because the reader marks through
    `/api/mark`, which takes a room and a node and knows nothing about streams.
    """
    try:
        with open(sitting_path(name), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    nodes = d.get("nodes")
    if not isinstance(nodes, dict):
        return None
    root = nodes.get(d.get("root"))
    kids = sorted((n for n in nodes.values()
                   if isinstance(n, dict) and n.get("kind") == "model"
                   and n.get("parent") == d.get("root")),
                  key=lambda n: n.get("ts") or 0)
    if not isinstance(root, dict) or not kids:
        return None
    node = kids[0]
    meta = node.get("meta") or {}
    params = meta.get("params") if isinstance(meta.get("params"), dict) else {}
    by_room, heads = readings if readings is not None else ({}, {})
    read = by_room.get(name) or {}
    return {"room": name, "node": node.get("id"),
            "seed": root.get("text") or "", "text": node.get("text") or "",
            "ts": node.get("ts") or d.get("created") or 0,
            "kept": bool(node.get("kept")), "good": bool(node.get("good")),
            "flag": meta.get("flag") or None,
            "temperature": params.get("temperature"),
            # Which dreamer wrote it (bekh, 2026-09-23 — two of them, turn and turn about, and
            # the name is the first thing in the head). See `stream_model`.
            "model": stream_model(meta),
            # The interpreter's copy, verbatim, and the same copy already diffed against the
            # dream. The page draws the segments; the string is the record.
            "marked": read.get("marked"),
            "segments": read.get("segments"),
            "reading": heads.get(name),
            # **The menu** (bekh, 2026-09-22): the dream's name, and its psalm number. The
            # note's own name first, then the back-catalogue store, then nothing — a dream the
            # reader named today should not be answered for by an older naming pass.
            "name": read.get("name") or (names or {}).get(name),
            "verse": (verses or {}).get(name),
            # The account for the PACK this dream belongs to. Every room of a pack carries
            # the same object; the page groups on `story.dream` and draws it once, beside them.
            "story": (stories or {}).get(name),
            # The painting for this dream, if one was made by hand. A url, not the bytes.
            "plate": plate_url(name)}


def stream_pages(before: str = "", n: int = STREAM_N, flagged: bool = False) -> dict:
    """`n` pages, newest first, older than `before`. `{"pages", "more"}`.

    `more` is whether there is anything further back, so the reader can grey its own button
    instead of asking again and finding out. Flagged pages are skipped unless asked for:
    the filter is a column on the card, and this is the one place it acts like a filter.
    """
    names = stream_room_names()
    if before:
        names = [x for x in names if x < before]
    # The readings are indexed ONCE for the whole batch: ten passages is ten lookups, not ten
    # walks of a folder that grows by a hundred and forty files a day.
    readings = stream_readings()
    stories, _live, verses = stream_stories()
    named = stream_names()
    pages, more = [], False
    for name in names:
        if len(pages) >= max(1, min(int(n), STREAM_N_MAX)):
            more = True
            break
        page = stream_page(name, readings, stories, verses, named)
        if page is None or (page["flag"] and not flagged):
            continue
        pages.append(page)
    # No top-level `dream` any more: every page carries the story of its own pack, and the
    # phone draws that pack's story as an inset at its head. One field, one rule, one place.
    return {"pages": pages, "more": more}


def stream_status() -> dict:
    """Is the machine dreaming? `{"state", "since", "room", "interval"}`.

    Off the worker's heartbeat and nothing else — not off the newest room, which would call a
    stream alive for as long as its last page sat on the shelf. Younger than two intervals is
    `dreaming`; one missed run is a busy GPU, two is something to look at.
    """
    try:
        with open(os.path.join(STREAM_DIR, "heartbeat.json"), encoding="utf-8") as f:
            hb = json.load(f)
    except (OSError, ValueError):
        hb = {}
    if not isinstance(hb, dict):
        hb = {}
    since = hb.get("last_ok") if isinstance(hb.get("last_ok"), (int, float)) else None
    awake = since is not None and (time.time() - since) < 2 * STREAM_INTERVAL
    return {"state": "dreaming" if awake else "asleep", "since": since,
            "room": hb.get("room"), "interval": STREAM_INTERVAL}


# ---- watching the stream --------------------------------------------------------------------
# A dream is written by five processes that never talk to the page — the worker, the reader, the
# sleeper, the painter, the namer — so the page used to ask every sixty seconds whether anything
# had happened. `/api/stream/events` holds the connection open instead and says which rooms
# changed within a couple of seconds of their changing.
#
# The fingerprint is per ROOM and covers exactly what `/api/stream` hands over for that room,
# built from the same four helpers the route itself uses (`stream_readings`, `stream_stories`,
# `stream_names`, `plate_url`) — never a second spelling of where those files live. The three
# index reads are cached on mtime inside those helpers, so a tick that changes nothing is three
# directory walks plus three stats a room.
#
# **What it costs, measured on the real shelf 2026-09-22** (185 stream rooms — `ls -R
# shelf/sittings/stream | wc -l` = 194 — 131 readings, 38 story versions, 43 plates): **4.4 ms**
# per tick warm, 8.1 ms with the mtime caches cold — 0.22% of a core at a tick of 2s. It grows
# with the shelf at roughly 2.4 ms per hundred rooms, which is why the walk is capped at the
# newest STREAM_EVENTS_ROOMS names: 288 passages a day would put this past 50 ms a tick inside a
# fortnight, and a reader's window is the newest page or two anyway.

def stream_prints(n: int = 0) -> dict[str, str]:
    """{room: a short digest of everything the reader sees for it}.

    Not a timestamp: a plate redrawn under the same name, a note re-read, a story rewritten
    under a new title all change what is on the page without moving the room's own file, and a
    mark written through `/api/mark` moves the file without changing anything else. One digest
    over all of it is the only thing that is true for every writer.
    """
    by_room, heads = stream_readings()
    stories, _live, verses = stream_stories()
    named = stream_names()
    out: dict[str, str] = {}
    for name in stream_room_names()[:max(1, n or STREAM_EVENTS_ROOMS)]:
        try:
            st = os.stat(sitting_path(name))
        except (OSError, ValueError):
            continue
        read = by_room.get(name) or {}
        story = stories.get(name) or {}
        key = (st.st_mtime_ns, st.st_size, plate_url(name),
               (heads.get(name) or {}).get("ts"),
               read.get("name"), named.get(name), verses.get(name),
               read.get("marked"), read.get("segments"),
               story.get("dream"), story.get("turn"), story.get("live"),
               story.get("title"), story.get("text"))
        out[name] = hashlib.blake2b(repr(key).encode("utf-8", "replace"),
                                    digest_size=8).hexdigest()
    return out


# ---- the dream while it is being written ------------------------------------------------------
# The writer (eva/stream/stream.py) streams nemo's answer and posts the text so far here about
# twice a second, then once more with `done` just before the room lands. It is ONE state and it
# lives in memory only: the room file is still the record, and a half-page on disk would be a
# second record that can disagree with it. A loom restart mid-dream loses the typing and nothing
# else — the room lands on the shelf as it always did.
#
# Held connections are woken by the condition, not by a shorter tick: the tick walks the shelf
# and costs milliseconds, the wake costs nothing, and a post has to reach the page in the same
# instant or the text arrives in two-second lurches instead of as it is written.

LIVE: dict | None = None
LIVE_SEQ = 0                      # bumped on every post; a held loop compares it to what it sent
LIVE_COND = threading.Condition()


def set_live(text: str, seed: str, done: bool, model: str | None = None) -> dict:
    """Take a new live state and wake every held events connection. Returns the state.

    `model` is who is typing — the writer's seat name since there are two dreamers — and None
    from a writer that does not say (the one-server path), which the page reads as no name."""
    global LIVE, LIVE_SEQ
    state = {"text": text, "seed": seed, "done": bool(done), "model": model or None,
             "ts": time.time()}
    with LIVE_COND:
        LIVE = state
        LIVE_SEQ += 1
        LIVE_COND.notify_all()
    return state


def live_now() -> dict | None:
    """The live state, or None when there is none or it is stale — a writer that died mid-dream
    must not be handed to the next reader as nemo still writing."""
    with LIVE_COND:
        state = LIVE
    if state is None or time.time() - state["ts"] > STREAM_LIVE_STALE:
        return None
    return state


def live_check(payload) -> str:
    """Why a live post is refused, or ''. Strings and a boolean, nothing else is looked at."""
    if not isinstance(payload, dict):
        return "a live post is an object"
    text, seed, done = payload.get("text"), payload.get("seed", ""), payload.get("done", False)
    if not isinstance(text, str) or not isinstance(seed, str) or not isinstance(done, bool):
        return "a live post takes text and seed as strings and done as a boolean"
    model = payload.get("model")
    if model is not None and not (isinstance(model, str) and len(model) <= 64):
        return "a live post's model is a short string"
    if len(text) + len(seed) > LIVE_MAX:
        return "a live post that size is not a passage"
    return ""


def pull_live(base: str) -> None:
    """The mirror's side: hold `<base>/api/stream/events` open and take the `live` events out of it.

    The mini serves dreamshit.net through a pipe it already holds open, so the typing gets there
    by this loom holding ONE connection to the mac's loom and passing every live state on to its
    own clients through `set_live` — the same wake a local post uses. The `change` events on the
    upstream are ignored: the mirror learns about rooms from its own shelf, which the push fills.

    Forever, on a daemon thread, and never a crash: the mac sleeping is the ordinary state, so an
    upstream that refuses, hangs or drops is a wait (doubling to LIVE_RETRY_MAX) and another try.
    One line on stderr when the upstream goes away and one when it comes back — never one per
    try, or a night with the lid shut would be the whole journal.
    """
    u = urlparse(base)
    prefix = (u.path or "").rstrip("/")
    wait, up = 1.0, None
    while True:
        conn = None
        try:
            # 3x the upstream's keepalive: a connection that has said nothing for a minute is
            # dead (a mac that went to sleep mid-connection never sends the FIN).
            conn = http.client.HTTPConnection(u.hostname or "127.0.0.1", u.port or 80,
                                              timeout=max(3 * STREAM_EVENTS_KEEPALIVE, 10))
            conn.request("GET", prefix + "/api/stream/events")
            resp = conn.getresponse()
            if resp.status != 200:
                raise OSError(f"upstream said {resp.status}")
            if up is not True:
                print(f"live · upstream {base} up", file=sys.stderr, flush=True)
            up, wait = True, 1.0
            event = ""
            for raw in resp:
                line = raw.decode("utf-8", "replace").rstrip("\r\n")
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:") and event == "live":
                    try:
                        d = json.loads(line[5:].strip())
                    except ValueError:
                        d = None
                    if not live_check(d):
                        set_live(d["text"], d.get("seed", ""), d.get("done", False),
                                 d.get("model"))
                elif not line:
                    event = ""
            raise OSError("upstream closed")
        # Everything, not a list of expected errors: this thread dying would end the typing on
        # the mirror silently until the next restart, which is worse than any one bad line.
        except Exception as exc:  # noqa: BLE001
            if up is not False:
                print(f"live · upstream {base} gone ({exc}); retrying quietly",
                      file=sys.stderr, flush=True)
            up = False
        finally:
            if conn is not None:
                try:
                    conn.close()
                except OSError:
                    pass
        time.sleep(wait)
        wait = min(wait * 2, LIVE_RETRY_MAX)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a) -> None:
        pass  # the health poll is every 5s; access logs would be the only thing in the journal

    def _send(self, code: int, body, ctype: str = "application/json; charset=utf-8",
              cache: str = "no-store") -> None:
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        # no-store everywhere by default: the page is edited while the server runs, and a
        # browser that caches loom.html turns "reload" into "reload sometimes". The icons
        # are the one exception — they are bytes that change once a year, and the phone
        # re-fetches them on every launch of the installed app if we say nothing.
        self.send_header("Cache-Control", cache)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def _refuse(self, plain: bool, code: int, msg: str) -> None:
        """The same refusal in whichever language the caller asked in. A route with a json
        twin and a text twin has to say no twice, and one of them saying `{"error": …}` to a
        browser tab is the kind of thing nobody notices until they open the link."""
        if plain:
            self._send(code, msg + "\n", "text/plain; charset=utf-8")
        else:
            self._json(code, {"error": msg})

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length", "0") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def stream_events(self) -> None:
        """`/api/stream/events` — the connection is held and the changes are pushed down it.

        One `event: change` per tick that changed anything, carrying the rooms whose
        fingerprint moved or appeared and the same `status` object `/api/stream` returns; a
        status-only change (the writer went to sleep) comes with `rooms: []`. Between them a
        `: keepalive` comment, because a connection that says nothing for a minute is a
        connection cloudflare and caddy are entitled to close. And `event: live` the moment the
        writer posts (see `set_live`) — out of band from the tick, woken by the condition.

        The server is a `ThreadingHTTPServer`, so a held connection is one thread and the loom
        goes on answering everything else; this is also why the tick is a plain `sleep` and not
        a scheduler. Nothing here writes, so the mirror serves it exactly as the mac does —
        `LOOM_READONLY` gates POST and this is a GET.

        The client going away is the ordinary ending: a write into a socket nobody is reading
        raises, and that is a `return`, not a traceback in the log.
        """
        self.close_connection = True
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        # Nginx's word for "do not buffer this", which caddy and cloudflare both honour. Without
        # it a proxy is free to hold the whole thing and hand it over when it ends, which for a
        # connection that never ends means the page shows nothing, forever.
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.end_headers()
        prints, status = stream_prints(), stream_status()
        with LIVE_COND:
            seen = LIVE_SEQ
        try:
            # A byte straight away, before any waiting: the headers alone may sit in a proxy,
            # and this is what proves the whole pipe is open while somebody is watching curl.
            self.wfile.write(b": open\n\n")
            # A reader arriving mid-dream sees it mid-way, not from the next post on. A finished
            # one is not sent: its room has landed or is landing, and a `done` with no `change`
            # after it would leave a block on the page that nothing ever takes away.
            cur = live_now()
            if cur is not None and not cur["done"]:
                self.live_event(cur)
            self.wfile.flush()
            said = time.monotonic()
            tick = said + STREAM_EVENTS_TICK
            while True:
                # Sleep until the tick OR a live post, whichever comes first. The wait is on the
                # condition so a post reaches every held client at once; the tick is unchanged.
                with LIVE_COND:
                    LIVE_COND.wait_for(lambda: LIVE_SEQ != seen,
                                       timeout=max(0.0, tick - time.monotonic()))
                    seq, state = LIVE_SEQ, LIVE
                if seq != seen:
                    # Posts that came faster than this loop are coalesced into the newest: the
                    # text is the whole text so far every time, so nothing is lost by skipping.
                    seen = seq
                    if state is not None:
                        self.live_event(state)
                        self.wfile.flush()
                        said = time.monotonic()
                    continue
                tick = time.monotonic() + STREAM_EVENTS_TICK
                fresh, now = stream_prints(), stream_status()
                changed = sorted(r for r, fp in fresh.items() if prints.get(r) != fp)
                if changed or now != status:
                    prints, status = fresh, now
                    data = json.dumps({"rooms": changed, "status": status}, ensure_ascii=False)
                    self.wfile.write(b"event: change\ndata: " + data.encode("utf-8") + b"\n\n")
                elif time.monotonic() - said < STREAM_EVENTS_KEEPALIVE:
                    continue
                else:
                    self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
                said = time.monotonic()
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            return

    def live_event(self, state: dict) -> None:
        data = json.dumps(state, ensure_ascii=False)
        self.wfile.write(b"event: live\ndata: " + data.encode("utf-8") + b"\n\n")

    def do_GET(self) -> None:
        u = urlparse(self.path)

        if u.path in ("/", "/loom.html"):
            try:
                with open(PAGE, "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._json(404, {"error": f"no page at {PAGE}"})
            return

        # What makes the page installable. Small enough to live here as a literal: a file on
        # disk would be a fourth place the palette is written down, and it has to agree with
        # loom.html's --bg and its theme-color or the splash flashes a different room.
        # NOT cached — the whole point is that a re-add picks up whatever this says today.
        if u.path == "/manifest.webmanifest":
            self._send(200, json.dumps({
                "name": "eva — the loom",
                "short_name": "eva",
                "start_url": "/",
                "scope": "/",
                "display": "standalone",
                "background_color": "#232323",
                "theme_color": "#232323",
                "icons": [{"src": f"/icon-{n}.png", "sizes": f"{n}x{n}", "type": "image/png"}
                          for n in ICON_SIZES],
            }, ensure_ascii=False), "application/manifest+json; charset=utf-8")
            return

        # Three sizes, by name, and nothing else out of that folder: the path is built from
        # an integer we already know, never from the url, so there is no static file server
        # here to walk out of.
        if u.path.startswith("/icon-") and u.path.endswith(".png"):
            try:
                n = int(u.path[len("/icon-"):-len(".png")])
            except ValueError:
                n = 0
            if n not in ICON_SIZES:
                self._json(404, {"error": "no icon that size"})
                return
            try:
                with open(os.path.join(ICONS, f"icon-{n}.png"), "rb") as f:
                    self._send(200, f.read(), "image/png", "public, max-age=31536000, immutable")
            except OSError:
                self._json(404, {"error": "the icons have not been generated"})
            return

        # The stream's own page, at its own address. A second file and not a screen inside
        # loom.html on purpose: the loom is a desk instrument and this is one page of text on
        # a phone, and the two share a palette and nothing else.
        if u.path in ("/stream", "/stream.html"):
            try:
                with open(STREAM_PAGE, "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._json(404, {"error": f"no page at {STREAM_PAGE}"})
            return

        # The one route that serves a file out of the shelf. The name is rebuilt from the url
        # and put through `name_ok` before it becomes a path, so `..` and dot segments are as
        # unaddressable here as they are everywhere else.
        if u.path.startswith("/stream/plate/") and u.path.endswith(".jpg"):
            rest = u.path[len("/stream/plate/"):-len(".jpg")]
            path = plate_path("stream/" + rest) if rest.count("/") == 1 else None
            if path is None:
                self._json(404, {"error": "no plate there"})
                return
            try:
                with open(path, "rb") as f:
                    # Hard cache: the url carries the file's mtime, so a re-drawn plate is a
                    # different url and nothing has to be revalidated.
                    self._send(200, f.read(), "image/jpeg",
                               "public, max-age=31536000, immutable")
            except OSError:
                self._json(404, {"error": "no plate there"})
            return

        # Before /api/stream, and not a query on it: this one never returns.
        if u.path == "/api/stream/events":
            self.stream_events()
            return

        if u.path == "/api/stream":
            q = parse_qs(u.query)
            before = (q.get("before", [""])[0] or "").strip()
            if before and not name_ok(before):
                self._json(400, {"error": "bad name"})
                return
            try:
                n = int(q.get("n", [""])[0] or STREAM_N)
            except ValueError:
                n = STREAM_N
            out = stream_pages(before, n, (q.get("all", ["0"])[0] or "0") not in ("0", ""))
            self._json(200, dict(out, status=stream_status()))
            return

        if u.path == "/api/health":
            self._json(200, health())
            return

        if u.path == "/api/sittings":
            self._json(200, {"sittings": shelf()})
            return

        if u.path == "/api/folder":
            name = (parse_qs(u.query).get("name", [""])[0] or "").strip()
            # Same validator as every other name that becomes a path, so `.trash` and `..`
            # are unaddressable here too, however they are spelled.
            if not name_ok(name):
                self._json(400, {"error": "bad name"})
                return
            d = folder_canvas(name)
            if d is None:
                self._json(404, {"error": "no rooms in that folder"})
                return
            self._json(200, d)
            return

        if u.path == "/api/canvases":
            self._json(200, {"canvases": boards()})
            return

        if u.path == "/api/canvas":
            name = (parse_qs(u.query).get("name", [""])[0] or "").strip()
            if not name_ok(name):
                self._json(400, {"error": "bad name"})
                return
            try:
                d = board_canvas(name)
            except (OSError, ValueError):
                self._json(500, {"error": "that board isn't readable json"})
                return
            if d is None:
                self._json(404, {"error": "no such board, or none of its rooms are left"})
                return
            self._json(200, d)
            return

        if u.path == "/api/sitting":
            name = (parse_qs(u.query).get("name", [""])[0] or "").strip()
            if not name_ok(name):
                self._json(400, {"error": "bad name"})
                return
            try:
                with open(sitting_path(name), encoding="utf-8") as f:
                    self._send(200, f.read())
            except OSError:
                self._json(404, {"error": "no such sitting"})
            except ValueError:
                self._json(500, {"error": "that file isn't json any more"})
            return

        if u.path == "/api/notes":
            self._json(200, {"notes": notes()})
            return

        if u.path == "/api/note":
            name = parse_qs(u.query).get("name", [""])[0]
            if not note_name_ok(name):
                self._json(400, {"error": "bad note name"})
                return
            try:
                with open(note_path(name), encoding="utf-8", newline="") as f:
                    self._json(200, {"name": name, "text": f.read()})
            except FileNotFoundError:
                self._json(404, {"error": "no such note"})
            except (OSError, UnicodeDecodeError) as exc:
                self._json(500, {"error": f"can't read it: {exc}"})
            return

        # The two halves of a berserk night at one url, and the document alone at the other.
        # They refuse the same things, so they share a body; `/text` answers in plain text
        # because whatever opens it is reading, not parsing.
        if u.path in ("/api/berserk", "/api/berserk/text"):
            plain = u.path.endswith("/text")
            name = (parse_qs(u.query).get("name", [""])[0] or "").strip()
            if not name_ok(name):
                self._refuse(plain, 400, "bad name")
                return
            # By path first, then by bare name: the ledger and every `#tree=` link the
            # sheets pages ever printed spell a room the way berserk made it, and filing
            # that room into a folder must not break a link written months ago.
            here = resolve_room(name)
            if not here:
                self._refuse(plain, 404, "no such sitting")
                return
            try:
                with open(sitting_path(here), encoding="utf-8") as f:
                    sitting = json.load(f)
            except FileNotFoundError:
                self._refuse(plain, 404, "no such sitting")
                return
            except (OSError, ValueError) as exc:
                self._refuse(plain, 500, f"can't read that room: {exc}")
                return
            # A room with no fork rows is a room berserk never walked — a hand-made one, or
            # one whose ledger lines are gone. 404 and not an empty tree: a blank screen
            # behind a link is worse than a refusal that says what is missing.
            rows = berserk_forks(here) or berserk_forks(leaf(here))
            if not rows:
                self._refuse(plain, 404, "berserk never walked that room")
                return
            if plain:
                self._send(200, berserk_text(sitting), "text/plain; charset=utf-8")
            else:
                self._json(200, berserk_room(sitting, rows))
            return

        if u.path == "/api/artifacts":
            self._json(200, {"artifacts": artifacts()})
            return

        if u.path == "/api/artifact":
            name = parse_qs(u.query).get("name", [""])[0]
            if not NAME_RE.match(name):
                self._json(400, {"error": "bad name"})
                return
            try:
                with open(artifact_path(name), encoding="utf-8") as f:
                    self._json(200, json.load(f))
            except FileNotFoundError:
                self._json(404, {"error": "no such artifact"})
            except (OSError, ValueError) as exc:
                self._json(500, {"error": f"can't read it: {exc}"})
            return

        # The document at a url, as plain text: the export screen reads it, and so does a
        # browser opened straight at it — a link that can be sent, reloaded and pasted into
        # sheets, where a blob download is a file and nothing more. Errors are plain text
        # too, because whatever opens this is reading, not parsing.
        if u.path == "/api/artifact/text":
            name = parse_qs(u.query).get("name", [""])[0]
            if not NAME_RE.match(name):
                self._send(400, "bad name\n", "text/plain; charset=utf-8")
                return
            try:
                with open(artifact_path(name), encoding="utf-8") as f:
                    self._send(200, artifact_text(json.load(f)), "text/plain; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "no such artifact\n", "text/plain; charset=utf-8")
            except (OSError, ValueError) as exc:
                self._send(500, f"can't read it: {exc}\n", "text/plain; charset=utf-8")
            return

        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        u = urlparse(self.path)
        if READONLY and not (MARKS_JOURNAL and u.path in ("/api/mark", "/api/keep")):
            self._json(403, {"error": "read-only: the mac is off, this is the mini's copy"})
            return
        try:
            payload = self._read_json()
        except ValueError:
            self._json(400, {"error": "bad json"})
            return

        if u.path == "/api/sitting":
            why = check(payload)
            if why:
                self._json(400, {"error": why})
                return
            try:
                ts = write_sitting(payload)
            except OSError as exc:
                self._json(500, {"error": f"can't write it: {exc}"})
                return
            self._json(200, {"ok": True, "updated": ts})
            return

        # The writer's dream while nemo writes it. Past the READONLY gate above on purpose: the
        # mirror's live state is the mac's, pulled (LIVE_UPSTREAM), and a second writer posting
        # to the mini would be two dreams fighting over one block.
        if u.path == "/api/stream/live":
            why = live_check(payload)
            if why:
                self._json(400, {"error": why})
                return
            set_live(payload["text"], payload.get("seed", ""), payload.get("done", False),
                     payload.get("model"))
            self._json(200, {"ok": True})
            return

        if u.path in ("/api/mark", "/api/keep"):
            # One route, two spellings. /api/keep is what the page called before `good`
            # existed and what anything outside this repo may still call, so it stays —
            # as a spelling of /api/mark and never as a second copy of the write.
            room, nid = payload.get("room"), payload.get("node")
            if u.path == "/api/keep":
                mark, want = "kept", payload.get("kept")
            else:
                mark, want = payload.get("mark"), payload.get("on")
            if not name_ok(room) or not isinstance(nid, str) or not nid \
                    or not isinstance(want, bool) or mark not in MARKS:
                self._json(400, {"error": "a mark takes a room path, a node id, "
                                          "one of " + "/".join(MARKS) + " and a boolean"})
                return
            try:
                done = set_mark(room, nid, mark, want)
                parent = done["parent"]
                if READONLY:
                    # Artifacts are the mac's to build: the replay goes through this same
                    # route there, and the sync below runs then. The line says what was
                    # asked for, not what it cleared — the rule is in set_mark on both
                    # machines, so the replay lands on the same two flags.
                    with open(MARKS_JOURNAL, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"room": room, "node": nid, "mark": mark,
                                            "on": want, "ts": time.time()}) + "\n")
                # A star on the canvas is a star: its fan's artifact follows it. So does a
                # circle that knocked a star off — that is a star coming off, and without
                # this the fan keeps an artifact no flag on disk stands behind.
                elif parent and (mark == "kept" or "kept" in done["cleared"]):
                    sync_artifact(room, parent)
            except FileNotFoundError:
                self._json(404, {"error": "no such sitting"})
                return
            except KeyError:
                self._json(404, {"error": "no such node in that room"})
                return
            except ValueError as exc:
                # Both a node that isn't a branch and a file that stopped being json: the
                # caller can do nothing about either, and neither is a server fault.
                self._json(400, {"error": str(exc)})
                return
            except OSError as exc:
                self._json(500, {"error": f"can't write it: {exc}"})
                return
            # Both marks, as they stand after the write and not as the caller asked: setting
            # one clears the other, and the page repaints a card off this answer.
            self._json(200, {"ok": True, "room": room, "node": nid, "mark": mark, "on": want,
                             "kept": done["kept"], "good": done["good"]})
            return

        if u.path == "/api/complete":
            prompt = payload.get("prompt")
            # "" is a legal prompt and not a missing one: llama inserts BOS and evaluates a
            # single token, and a bare room with an empty root — the thing census.py makes
            # with --empty — has nothing else to send. Only a missing or non-string prompt
            # is a bug in the caller.
            if not isinstance(prompt, str):
                self._json(400, {"error": "no prompt"})
                return
            params = payload.get("params")
            out = complete(prompt, params if isinstance(params, dict) else {})
            # 502 and not 500: the thing that failed is behind us, not in us. The page
            # reads `error` either way and never has to look at the status.
            self._json(502 if out.get("error") else 200, out)
            return

        if u.path == "/api/note":
            # create:true = the + button: a blank name gets a random hex one, and a taken
            # name is refused — adding must never overwrite a finding. create:false = edit:
            # the note has to exist already.
            text = payload.get("text")
            if not isinstance(text, str):
                self._json(400, {"error": "no text"})
                return
            create = bool(payload.get("create"))
            name = payload.get("name")
            if create and (name is None or (isinstance(name, str) and not name.strip())):
                name = secrets.token_hex(4)
                while os.path.exists(note_path(name)):
                    name = secrets.token_hex(4)
            if not note_name_ok(name):
                self._json(400, {"error": "names are up to 120 characters, no slashes, "
                                          "no leading dot or edge spaces"})
                return
            exists = os.path.exists(note_path(name))
            if create and exists:
                self._json(409, {"error": f"a note called “{name}” already exists"})
                return
            if not create and not exists:
                self._json(404, {"error": "no such note"})
                return
            try:
                write_note(name, text)
            except OSError as exc:
                self._json(500, {"error": f"can't write it: {exc}"})
                return
            self._json(200, {"ok": True, "name": name})
            return

        if u.path == "/api/artifact":
            room = payload.get("room")
            if not name_ok(room):
                self._json(400, {"error": "bad room name"})
                return
            if payload.get("sync") is True:
                try:
                    out = sync_artifact(room, payload.get("parent"))
                except FileNotFoundError:
                    self._json(404, {"error": "no such sitting"})
                    return
                except ValueError as exc:
                    self._json(400, {"error": str(exc)})
                    return
                except OSError as exc:
                    self._json(500, {"error": f"can't write it: {exc}"})
                    return
                self._json(200, dict({"ok": True}, **out))
                return
            # No name = a random hex one, like a room the page makes. A name that is given
            # gets the room rule, because it is a file name behind an api with no auth.
            name = payload.get("name")
            if name is None or (isinstance(name, str) and not name.strip()):
                name = secrets.token_hex(6)
                while os.path.exists(artifact_path(name)):
                    name = secrets.token_hex(6)
            if not isinstance(name, str) or not NAME_RE.match(name):
                self._json(400, {"error": "bad name"})
                return
            if os.path.exists(artifact_path(name)):
                self._json(409, {"error": f"an artifact called {name} already exists"})
                return
            try:
                with open(sitting_path(room), encoding="utf-8") as f:
                    sitting = json.load(f)
            except FileNotFoundError:
                self._json(404, {"error": "no such sitting"})
                return
            except (OSError, ValueError) as exc:
                self._json(500, {"error": f"can't read that room: {exc}"})
                return
            try:
                art = build_artifact(sitting, payload.get("parent"), payload.get("kept"), name)
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
                return
            art["model"] = model_info()
            try:
                write_artifact(art)
            except FileExistsError:
                self._json(409, {"error": f"an artifact called {name} already exists"})
                return
            except OSError as exc:
                self._json(500, {"error": f"can't write it: {exc}"})
                return
            self._json(200, {"ok": True, "name": name, "title": art["title"]})
            return

        if u.path == "/api/tokenize":
            contents = payload.get("contents")
            # A cap, because this is a loop of network calls with no auth in front of it.
            if not isinstance(contents, list) or len(contents) > 64:
                self._json(400, {"error": "contents is a list of up to 64 strings"})
                return
            out = tokenize(contents)
            self._json(502 if out.get("error") else 200, out)
            return

        if u.path == "/api/cancel":
            self._json(200, {"ok": True, "cut": cancel_all()})
            return

        if u.path == "/api/move":
            src, dst = payload.get("from"), payload.get("to")
            try:
                moved = move_room(src if isinstance(src, str) else "",
                                  dst if isinstance(dst, str) else "")
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
                return
            except FileNotFoundError:
                self._json(404, {"error": "nothing on the shelf by that name"})
                return
            except FileExistsError:
                self._json(409, {"error": f"“{dst}” is taken"})
                return
            except OSError as exc:
                self._json(500, {"error": f"can't move it: {exc}"})
                return
            self._json(200, {"ok": True, "from": src, "to": dst, "moved": moved})
            return

        if u.path in ("/api/delete", "/api/clear"):
            name = payload.get("name")
            if not name_ok(name):
                self._json(400, {"error": "bad name"})
                return
            try:
                trash_sitting(name, keep=(u.path == "/api/clear"))
            except FileNotFoundError:
                self._json(404, {"error": "no such sitting"})
                return
            except OSError as exc:
                self._json(500, {"error": f"can't move it: {exc}"})
                return
            self._json(200, {"ok": True})
            return

        self._json(404, {"error": "not found"})


def main() -> int:
    os.makedirs(SITTINGS, exist_ok=True)
    os.makedirs(STORAGE, exist_ok=True)
    os.makedirs(ARTIFACTS, exist_ok=True)
    print(f"loom up: http://{HOST}:{PORT}  (llama {LLAMA}, sittings {SITTINGS})", flush=True)
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    # Only with the env var: the mac's loom is the upstream and pulls from nobody.
    if LIVE_UPSTREAM:
        threading.Thread(target=pull_live, args=(LIVE_UPSTREAM,), daemon=True,
                         name="live-upstream").start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # Ctrl-C with three branches in flight would otherwise leave llama generating
        # into sockets nobody will ever read.
        cancel_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
