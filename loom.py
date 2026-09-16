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
  GET  /api/health           -> {"ok", "llama"}: is there a model behind the port
  GET  /api/sittings         -> the shelf, newest first
  GET  /api/sitting?name=    -> one whole tree
  POST /api/sitting          -> the whole tree, written atomically
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
  GET  /api/artifacts        -> every artifact's name, title, created, steps, kept and fan
                                size, newest first
  GET  /api/artifact?name=   -> one artifact, whole
  GET  /api/artifact/text?name= -> that walk as one plain-text document, to read or send
  POST /api/artifact         -> {"room", "parent", "kept": [node ids], "name"?}: the server
                                reads that room off the disk, walks the path that reached
                                `parent`, and freezes every fork along it — the line taken,
                                the branches kept beside it — writing the file once; a taken
                                name is 409, never an overwrite

Env: LOOM_HOST, LOOM_PORT (8082 — 8080 is llama-server, 8081 is fim), LOOM_LLAMA,
LOOM_SITTINGS, LOOM_STORAGE, LOOM_ARTIFACTS.
"""

from __future__ import annotations

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

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "loom.html")
HOST = os.environ.get("LOOM_HOST", "127.0.0.1")
PORT = int(os.environ.get("LOOM_PORT", "8082"))
LLAMA = os.environ.get("LOOM_LLAMA", "http://127.0.0.1:8080").rstrip("/")
# Overridable only so the tests can run against a scratch shelf instead of the real one;
# everything else should leave it alone — sittings belong next to the script that made them.
SITTINGS = os.environ.get("LOOM_SITTINGS", os.path.join(HERE, "sittings"))
# Storage: findings bekh wants to keep, one plain .txt per note, nothing but the text in it.
# Tracked by git on purpose (sittings are not) — a finding is worth its history.
STORAGE = os.environ.get("LOOM_STORAGE", os.path.join(HERE, "storage"))
NOTE_MAX = 120
# Artifacts: one walk each, frozen — the document it started from and every fork along the
# way, with only the branches bekh kept. The opposite of a sitting on every axis: written
# once and never again, tracked by git and pushed. A room is a place to work; an artifact is
# what came out of it.
ARTIFACTS = os.environ.get("LOOM_ARTIFACTS", os.path.join(HERE, "artifacts"))
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

# A sitting name is a filename, and this API has no auth in front of it: no slashes, no
# dots-only, nothing that could climb out of SITTINGS. Checked on the way in AND on the
# way out, because a file dropped in that directory by hand is also untrusted input.
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")

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
    return os.path.join(SITTINGS, name + ".json")


def shelf() -> list[dict]:
    """Every sitting on the disk, newest first, as a card's worth of each.

    Reads every file — they are small, there will never be hundreds, and the alternative
    is a sidecar index that goes stale the first time a file is copied in by hand.
    """
    out = []
    try:
        names = os.listdir(SITTINGS)
    except OSError:
        return out
    for fname in names:
        if not fname.endswith(".json"):
            continue
        name = fname[:-5]
        if not NAME_RE.match(name):
            continue
        try:
            with open(os.path.join(SITTINGS, fname), encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        out.append({
            "name": name,
            "title": d.get("title") or name,
            "created": d.get("created") or 0,
            "updated": d.get("updated") or 0,
            "nodes": len(d.get("nodes") or {}),
        })
    out.sort(key=lambda s: s["updated"], reverse=True)
    return out


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
    if not isinstance(name, str) or not NAME_RE.match(name):
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
    os.makedirs(SITTINGS, exist_ok=True)
    ts = time.time()
    obj["updated"] = ts
    path = sitting_path(obj["name"])
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
    bin_ = os.path.join(SITTINGS, ".trash")
    os.makedirs(bin_, exist_ok=True)
    dst = os.path.join(bin_, f"{name}.{time.strftime('%Y%m%d-%H%M%S')}.json")
    if keep:
        shutil.copy2(src, dst)
    else:
        os.replace(src, dst)
    return dst


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


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a) -> None:
        pass  # the health poll is every 5s; access logs would be the only thing in the journal

    def _send(self, code: int, body, ctype: str = "application/json; charset=utf-8") -> None:
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        # no-store everywhere: the page is edited while the server runs, and a browser
        # that caches loom.html turns "reload" into "reload sometimes".
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length", "0") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self) -> None:
        u = urlparse(self.path)

        if u.path in ("/", "/loom.html"):
            try:
                with open(PAGE, "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._json(404, {"error": "no loom.html next to loom.py"})
            return

        if u.path == "/api/health":
            self._json(200, health())
            return

        if u.path == "/api/sittings":
            self._json(200, {"sittings": shelf()})
            return

        if u.path == "/api/sitting":
            name = (parse_qs(u.query).get("name", [""])[0] or "").strip()
            if not NAME_RE.match(name):
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
            if not isinstance(room, str) or not NAME_RE.match(room):
                self._json(400, {"error": "bad room name"})
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

        if u.path in ("/api/delete", "/api/clear"):
            name = payload.get("name")
            if not isinstance(name, str) or not NAME_RE.match(name):
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
