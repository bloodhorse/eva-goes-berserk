#!/usr/bin/env -S uv run --python 3.12 --script
"""eva.py — the loom with no browser: a repl whose scrollback IS the document.

    uv run --python 3.12 eva.py [name]

Same sittings, same json, same tree as loom.html — this is its python twin, not a second
tool. `loom.py` is imported for the four things that must not exist twice (where the shelf
is, what a legal name is, what a valid sitting looks like, how one is written atomically);
importing it starts no server, its module level is constants and defs.

The one design law, and everything below follows from it: **in chat mode the prompt is
literally the turn prefix trimmed plus a space — `bekh: ` — so what the terminal shows is
the document the model is reading.** The header, his line, the `seat:` cue, the branch he
picked: they scroll past in the order and the shape they have inside the file. That is why
nothing here draws a frame, a box or a status bar, and why the document is written out
VERBATIM and never wrapped — a wrap would put newlines on the screen that are not in the
text. Only things that are *not* in the document yet — the numbered candidates, the marker
lines — are wrapped, and they are wrapped with a hanging indent so they cannot be mistaken
for it.

In a bare sitting (prefix and suffix both empty — derived, never a stored flag, exactly as
in the page) there is no name to print, so the prompt is a dim `› `: visibly not text,
because there everything typed goes into the document as typed.

Env: LOOM_LLAMA (default http://127.0.0.1:8080 — llama-server DIRECTLY, this talks to no
loom.py), LOOM_SITTINGS (read by loom.py at import).
"""

from __future__ import annotations

import ast
import atexit
import http.client
import json
import math
import os
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlparse

# realpath, not abspath: `eva` on PATH is a symlink in ~/.local/bin, and abspath would look
# for the server next to the link instead of next to this file. loom.py is in eva/server,
# a sibling folder — the one store and transport this project has.
HERE = os.path.dirname(os.path.realpath(__file__))
SERVER = os.path.join(os.path.dirname(HERE), "server")
if SERVER not in sys.path:
    sys.path.insert(0, SERVER)
# name_ok and sitting_path and never a path spelled here: a room name is a path under the
# sittings dir now (`experiments/basin/s-01`), and two places that turn a name into a file
# are two rules about what a folder is.
from loom import (LOOM_ONLY, check, name_ok, shelf, sitting_path,  # noqa: E402
                  spread_temps, trim_probs, write_sitting)

LLAMA = os.environ.get("LOOM_LLAMA", "http://127.0.0.1:8080").rstrip("/")
COMPLETE_TIMEOUT = 900

# ---- the shape of a sitting ----------------------------------------------------------
# Copied verbatim from loom.html, on purpose and not parsed out of it: if somebody changes
# the header line or the turn strings there, this has to be changed too, by a human who
# reads why. The comments in the page explain each of these; the short of it —
#   HEADER ends in ONE newline, the prefix opens with its own, and the pair is the single
#   blank line a saved chat log has between its header and the first message.
HEADER = "a chat log between two friends, saved from a phone. no punctuation fixed, no capitals.\n"
# Measured against nemo on this box (docs/research-cyborgism-methods.md), and the one number
# that matters is the sampler CHAIN ORDER: this build runs penalties, dry, top_n_sigma,
# top_k, typ_p, top_p, min_p, xtc, and temperature LAST. So min_p truncates the model's
# untouched distribution and temperature only flattens what survived — which is why 2.5 is
# coherent here and 1.0 is where nemo copies its seed and loops. A new room starts hot and
# spread; a room already on the shelf keeps whatever it was written with.
PARAMS = {
    "n_predict": 220,
    "stop": ["\nbekh:", "\nbekh :", "\n\nbekh"],
    "temperature": 2.5, "min_p": 0.08, "top_k": 0, "top_p": 1.0,
    "top_n_sigma": -1,                       # -1 is off
    "xtc_probability": 0, "xtc_threshold": 0.1,
    "repeat_penalty": 1.05, "repeat_last_n": 512,
    "dry_multiplier": 0.8, "dry_base": 1.75, "dry_allowed_length": 3,
    "dry_penalty_last_n": 8192,
    "ignore_eos": False,
    "n_probs": 5, "logit_bias": [],
    "logit_bias_text": "",
    "fan": 4, "spread": 1.0, "dry_keep": 0.8,
}
# llama EATS the stop string. The prefix carries the newline AND the name so the next human
# node puts back what the stop ate; break this and the two speakers run together on a line.
TURN = {"prefix": "\nbekh: ", "suffix": "\nseat:"}

HISTORY = os.path.expanduser("~/.cache/eva/history")
HELP = ("a number picks · empty enter fans · /more /fan N /back /prune [N] /edit [N] "
        "/say /seed /doc /spin [name] /set [key value] /open [name] /new [bare] name /quit")


# ---- colour ---------------------------------------------------------------------------
RESET = "\033[0m"


class Ink:
    """ANSI 16 only, and only when somebody is actually looking at a terminal.

    `rl` wraps a coloured prompt in readline's \\001/\\002 markers. Without them readline
    counts the escape bytes as printable, gets the cursor column wrong, and every line
    longer than the terminal is redrawn over itself.
    """

    def __init__(self, on: bool) -> None:
        self.on = on

    def _c(self, code: str, s: str) -> str:
        return f"\033[{code}m{s}{RESET}" if self.on else s

    def band(self, s):    return self._c("36", s)    # his own words, the one warm colour
    def dim(self, s):     return self._c("2", s)
    def magenta(self, s): return self._c("35", s)
    def red(self, s):     return self._c("31", s)

    def rl(self, s: str, code: str) -> str:
        if not self.on:
            return s
        return f"\001\033[{code}m\002{s}\001{RESET}\002"


# ---- wrapping ---------------------------------------------------------------------------
class Wrap:
    """Word-wrap text that arrives in pieces, because a candidate arrives token by token.

    One wrapper for the live stream and for anything reprinted later, so a branch looks the
    same while it lands and when it is listed again. It never rewrites what it has already
    written — that is the whole constraint: a token is on the screen the moment it is out of
    the model, and the only decision left is whether the next word starts a new line.
    """

    def __init__(self, write, width: int, indent: int, col: int | None = None) -> None:
        self.write = write
        self.indent = indent
        # A width that does not leave room for words is a wrapper that writes one letter
        # per line; below this it is better to overrun the terminal.
        self.width = max(width, indent + 16)
        self.col = indent if col is None else col
        self.word = ""
        # Spaces are held until we know whether a word follows them on this line: written
        # eagerly, every wrap would leave one hanging off the right edge, which is the
        # difference between a clean column and a page that looks ragged.
        self.pend = ""

    def _spend(self) -> None:
        if self.pend:
            self.write(self.pend)
            self.col += len(self.pend)
            self.pend = ""

    def _flush(self) -> None:
        if not self.word:
            return
        if self.col + len(self.pend) + len(self.word) > self.width and self.col > self.indent:
            self.write("\n" + " " * self.indent)   # the break is ours; the space it ate was too
            self.col = self.indent
            self.pend = ""
        else:
            # The space in front of a model's line is part of the text: kept, not hidden,
            # or the screen shows a branch that is not the branch on disk.
            self._spend()
        self.write(self.word)
        self.col += len(self.word)
        self.word = ""

    def feed(self, s: str) -> None:
        for ch in s:
            if ch == "\n":
                self._flush()
                self._spend()       # a space before a newline the TEXT asked for is text
                self.write("\n" + " " * self.indent)
                self.col = self.indent
            elif ch in " \t":
                self._flush()
                self.pend += ch
            else:
                self.word += ch
                if len(self.word) >= self.width - self.indent:
                    self._flush()   # one unbroken word longer than the line: let it run on

    def end(self) -> None:
        self._flush()
        self._spend()


# ---- transport ---------------------------------------------------------------------------
def complete_stream(prompt: str, params: dict, on_chunk) -> dict:
    """One streaming POST to llama's /completion. loom.py's `complete`, token by token.

    Streaming is the reason this is here and not a call into loom.py: in the page a branch
    is read when it is finished, beside three others; in a terminal the branch IS the
    reading, and a base model that takes twelve seconds to write a line has to be watched
    writing it or the tool feels dead.

    Returns the page's shape, or {"error": ...}. KeyboardInterrupt is NOT caught here — the
    caller decides what a cut branch means, and `finally` still drops the socket, which is
    what makes llama-server free the slot instead of generating into nobody.
    """
    body = {k: v for k, v in (params or {}).items() if k not in LOOM_ONLY}
    body["prompt"] = prompt
    body["cache_prompt"] = True
    body["stream"] = True
    # llama's n_predict default is -1, which is *infinite*: a base model that never hits a
    # stop string would write until the context is full.
    try:
        body["n_predict"] = int(body.get("n_predict") or 0) or 220
    except (TypeError, ValueError):
        body["n_predict"] = 220

    u = urlparse(LLAMA)
    conn = http.client.HTTPConnection(u.hostname or "127.0.0.1", u.port or 80,
                                      timeout=COMPLETE_TIMEOUT)
    prefix = (u.path or "").rstrip("/")
    parts: list[str] = []
    probs: list[dict] = []
    last: dict = {}
    try:
        conn.request("POST", prefix + "/completion",
                     body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        if resp.status != 200:
            raw = resp.read()
            return {"error": f"llama {resp.status}: {raw[:300].decode('utf-8', 'replace')}"}
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue                      # SSE keepalives, event: lines, blank spacers
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                d = json.loads(payload)
            except ValueError:
                continue
            piece = d.get("content") or ""
            if piece:
                parts.append(piece)
                on_chunk(piece)
            # Streaming splits the probabilities the way it splits the text: one token's
            # worth on each partial, and NOTHING on the final event — llama guards the
            # whole-array field with `if (!stream ...)`. Collect them here or lose them.
            got = d.get("completion_probabilities")
            if isinstance(got, list):
                probs.extend(got)
            if d.get("stop"):
                last = d                      # the only chunk carrying the timings and why it stopped
    except (OSError, http.client.HTTPException, ValueError) as exc:
        return {"error": f"llama unreachable: {exc}"}
    finally:
        try:
            conn.close()
        except OSError:
            pass

    timings = last.get("timings") or {}
    return {
        # `content` verbatim, and the stop string is NOT in it — llama eats it. The next
        # human node's prefix is what puts it back.
        "text": "".join(parts),
        "stop_type": last.get("stop_type") or "",
        "stopping_word": last.get("stopping_word") or "",
        "tokens_predicted": last.get("tokens_predicted") or 0,
        "tps": round(float(timings.get("predicted_per_second") or 0.0), 1),
        "probs": trim_probs(probs),
    }


# ---- small things ------------------------------------------------------------------------
def unesc(s: str) -> str:
    """`\\n` typed at the prompt into a real newline — loom.html's `unesc`, same rules.

    /set is the only way to change the turn strings from here, and every one of them has a
    newline in it; without this there would be no way to type one.
    """
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        i += 1
        if i >= len(s):
            out.append("\\")
            break
        d = s[i]
        i += 1
        out.append("\n" if d == "n" else "\t" if d == "t" else d)
    return "".join(out)


def blank(name: str, is_bare: bool = False, root_text: str | None = None) -> dict:
    """A new sitting, in the one shape the page and the repl both read.

    Here and not inside Eva because census.py makes rooms too, and a second copy of this
    shape is a second thing to change when the file format moves. `root_text` is for a room
    whose first text is neither the header nor nothing — a document handed in on the command
    line, or a branch spun off into a room of its own.
    """
    root = {"id": secrets.token_hex(4), "parent": None, "kind": "root",
            "text": (("" if is_bare else HEADER) if root_text is None else root_text),
            "ts": time.time(), "pruned": False, "posed": False, "meta": None}
    d = {"name": name, "created": time.time(), "updated": 0,
         "params": json.loads(json.dumps(PARAMS)),
         "turn": {"prefix": "", "suffix": ""} if is_bare else json.loads(json.dumps(TURN)),
         "root": root["id"], "current": root["id"], "nodes": {root["id"]: root}}
    # Without a stop string a branch runs to n_predict and may end mid-word. That is not a
    # defect, it is what continuation is; the next fan picks the word back up.
    if is_bare:
        d["params"]["stop"] = []
    return d


def est_tokens(text: str) -> int:
    """Tokens, guessed from characters. There is no tokenizer in this process, and asking
    llama for one would be a round trip per line; four characters to a token is the standard
    rough ratio, and everything this number feeds is itself a ratio."""
    return max(1, round(len(text) / 4)) if text else 0


def curation(sitting: dict) -> dict:
    """janus's bits of curation for the document as it stands (generative.ink).

    How much of this text is the human? Picking from a fan of n and keeping m of them
    acceptable costs log2(n/m) bits — that is the choice, measured. A line he typed, or a
    model line he edited, costs its whole token count instead: every token of it came from
    him and none from the model, and there are no logprobs for text nobody sampled.

    Along the CURRENT PATH only, because the document is what is on the path — the rest of
    the tree is roads not taken. Computed on the fly from what the nodes already carry: a
    stored number would be wrong the moment a branch is pruned.
    """
    nodes = sitting["nodes"]
    path, node = [], nodes.get(sitting["current"])
    while node:
        path.insert(0, node)
        node = nodes.get(node["parent"]) if node["parent"] else None
    bits, picks = 0.0, 0
    for n in path:
        if n["kind"] != "model" or n["posed"]:
            t = est_tokens(n["text"])
            if t:
                bits += t
                picks += 1
            continue
        # n is what the fan produced, pruned ones included — they were still written, and
        # rejecting them is the choice being measured. m is what survived it: a branch that
        # was continued, or the one being stood on.
        sibs = [s for s in nodes.values()
                if s["parent"] == n["parent"] and s["kind"] == "model"]
        kept = [s for s in sibs if not s["pruned"] and (
            s["id"] == n["id"] or any(k["parent"] == s["id"] for k in nodes.values()))]
        # A branch that says exactly what a kept branch says cost nothing to throw away —
        # the same text was on offer twice, so the choice was between fewer things than it
        # looks. (The page prunes verbatim twins on arrival for the same reason.)
        texts = {s["text"].strip() for s in kept}
        m = sum(1 for s in sibs if s in kept or s["text"].strip() in texts)
        if len(sibs) > 1 and 0 < m < len(sibs):
            bits += math.log2(len(sibs) / m)
            picks += 1
    tokens = est_tokens("".join(n["text"] for n in path))
    return {"bits": round(bits, 1), "tokens": tokens, "picks": picks,
            "per_token": round(bits / tokens, 3) if tokens else 0.0,
            "per_pick": round(tokens / picks) if picks else 0}


def curation_line(sitting: dict) -> str:
    c = curation(sitting)
    out = f"curation: {c['bits']} bits · {c['per_token']} bits/token"
    return out + (f" · 1 pick per {c['per_pick']} tokens" if c["picks"] else "")


def backfill(params: dict) -> dict:
    """Keys PARAMS has grown since the file was written, put back at their defaults.

    Every sitting on the shelf predates n_probs, spread and logit_bias, and /set refuses a
    key it cannot see — without this, an old room could never be given the new settings at
    all. Only missing keys are touched; anything already in the file is his.
    """
    for k, v in PARAMS.items():
        if k not in params:
            params[k] = json.loads(json.dumps(v))
    return params


def leading_nl(s: str) -> str:
    return s[:len(s) - len(s.lstrip("\n"))]


def edit_text(seed: str) -> str | None:
    """$EDITOR on a temp file; the text back, or None if the editor failed to run.

    shlex, not a bare exec: EDITOR is routinely `code -w` or `vim -u NONE`, and a plain
    [editor, path] would look for a program with a space in its name.
    """
    ed = os.environ.get("EDITOR") or "vi"
    fd, path = tempfile.mkstemp(prefix="eva-", suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(seed)
        try:
            subprocess.call(shlex.split(ed) + [path])
        except OSError:
            return None
        with open(path, encoding="utf-8") as f:
            return f.read()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# ---- the repl ------------------------------------------------------------------------------
class Eva:
    """The tree, the screen and the keyboard. One object so the tests can drive it.

    `read` and `out` are injected: the tests hand it a list of lines and a StringIO, which
    is the only reason this is testable without a pty.
    """

    def __init__(self, out=None, read=None, colour=None) -> None:
        self.out = out if out is not None else sys.stdout
        self.read = read if read is not None else console_read
        if colour is None:
            colour = not os.environ.get("NO_COLOR") and hasattr(self.out, "isatty") \
                and self.out.isatty()
        self.ink = Ink(bool(colour))
        self.sitting = None
        # Where the cursor is, and who put it there. `atbol` is plain bookkeeping; `borrowed`
        # is the interesting one: it means the last line break on the screen was OURS (a
        # candidate list, a marker) and not the document's. The next piece of document that
        # opens with a newline then skips it, so a pick does not leave a blank line behind
        # while a fresh header still gets its blank line. Without this the transcript
        # slowly grows gaps that are not in the file.
        self.atbol = True
        self.borrowed = False

    # -- screen ------------------------------------------------------------------
    def width(self) -> int:
        return shutil.get_terminal_size((80, 24)).columns

    def w(self, s: str) -> None:
        if not s:
            return
        self.out.write(s)
        try:
            self.out.flush()        # a streaming branch that sits in a buffer is not streaming
        except (AttributeError, ValueError):
            pass
        # Colour never decides where the line is: a string ending in the reset code ends
        # wherever it ended before the code.
        t = s[:-len(RESET)] if s.endswith(RESET) else s
        if t:
            self.atbol = t.endswith("\n")

    def bol(self) -> None:
        if not self.atbol:
            self.w("\n")

    def line(self, s: str = "") -> None:
        """A line that is NOT in the document — a marker, a candidate, an error."""
        self.bol()
        self.w(s + "\n")
        self.borrowed = True

    def doc(self, s: str) -> None:
        """A piece of the document, verbatim. Nothing is wrapped, nothing is added."""
        self.w(s)
        self.borrowed = False

    def doc_lead(self, s: str) -> None:
        """Document text that opens a line, with the one newline we already spent dropped.

        Every human node begins with the prefix's newline. When the last break on the
        screen was ours (`borrowed` — a candidate list, a marker) that break already is the
        one the document asks for, and printing a second opens a gap no reader of the file
        would ever see.
        """
        if self.borrowed and s.startswith("\n"):
            s = s[1:]
        self.doc(s)

    def err(self, s: str) -> None:
        self.line(self.ink.red(s))

    def note(self, s: str) -> None:
        self.line(self.ink.dim(s))

    # -- the tree (loom.html's, in python) ---------------------------------------
    def node(self, nid: str) -> dict:
        return self.sitting["nodes"][nid]

    def kids(self, nid: str) -> list[dict]:
        return sorted((n for n in self.sitting["nodes"].values()
                       if n["parent"] == nid and not n["pruned"]),
                      key=lambda n: n["ts"])

    def path(self) -> list[dict]:
        out, n = [], self.node(self.sitting["current"])
        while n:
            out.insert(0, n)
            n = self.node(n["parent"]) if n["parent"] else None
        return out

    def prompt_from(self, nid: str) -> str:
        """Concatenation along root→node, verbatim, nothing inserted between blocks. The one
        rule the whole tool rests on — a base model must never see a frame we imagined."""
        out, n = [], self.node(nid)
        while n:
            out.insert(0, n["text"])
            n = self.node(n["parent"]) if n["parent"] else None
        return "".join(out)

    def add_node(self, kind: str, text: str, parent, meta=None) -> dict:
        n = {"id": secrets.token_hex(4), "parent": parent, "kind": kind, "text": text,
             "ts": time.time(), "pruned": False, "posed": False, "meta": meta}
        self.sitting["nodes"][n["id"]] = n
        return n

    def bare(self) -> bool:
        """Not a mode: the same two settings emptied. Derived and never stored, so flipping
        the prefix with /set flips the behaviour and no file can carry a flag that lies."""
        t = self.sitting["turn"]
        return not (t["prefix"] or t["suffix"])

    def save(self) -> bool:
        why = check(self.sitting)
        if why:
            # Refusing to write beats writing a tree the page cannot open: the file is what
            # the next session reads back.
            self.err("not saved: " + why)
            return False
        try:
            write_sitting(self.sitting)
        except OSError as exc:
            self.err(f"not saved: {exc}")
            return False
        return True

    # -- rendering ---------------------------------------------------------------
    def echo_node(self, n: dict) -> None:
        """One node of the document, verbatim, with his own words in the band colour.

        The band is only the line he typed: the `seat:` cue after it is the model's turn
        marker and the newline before it is the seam between two speakers, so the text goes
        out as three pieces that concatenate back to exactly n["text"] — nothing added,
        nothing hidden. A node whose suffix does not match (an old one from before a
        rename) goes out plain rather than guessed at.
        """
        suf = self.sitting["turn"]["suffix"] or ""
        t = n["text"]
        if n["kind"] == "human" and (not suf or (t.endswith(suf) and len(t) > len(suf))):
            head = t[:-len(suf)] if suf else t
            lead = leading_nl(head)
            core = head[len(lead):]
            if core:
                self.doc_lead(lead)
                self.doc(self.ink.band(core))
                self.doc(suf)
                return
        self.doc_lead(t)

    def echo_doc(self) -> None:
        for n in self.path():
            self.echo_node(n)

    def echo_model(self, n: dict) -> None:
        """A model line reprinted once, so the transcript reads as a transcript.

        Wrapped, unlike the document echo, and on purpose: this is a redraw of a line that
        is already on the screen as candidate N, and the hanging indent under `seat: ` is
        what says "the break is the terminal's, not the text's".
        """
        if self.bare():
            self.bol()
            wr = Wrap(self.w, self.width(), 0, col=0)
            wr.feed(n["text"])
            wr.end()
        else:
            label = (self.sitting["turn"]["suffix"] or "").strip() or "…"
            self.bol()
            self.w(label)
            wr = Wrap(self.w, self.width(), len(label) + 1, col=len(label))
            wr.feed(n["text"])
            wr.end()
        if n["posed"]:
            self.w(self.ink.magenta("  posed"))
        self.w("\n")
        self.borrowed = True

    def marker(self, i: int, star: bool = False) -> str:
        # Fixed five columns so every candidate's text starts in the same place and the
        # hanging indent below it lines up; the star is the branch we came back from.
        return ("*" if star else " ") + f"{i:>2}" + "  "

    def card(self, i: int, n: dict, star: bool = False) -> None:
        mark = self.marker(i, star)
        self.bol()
        self.w(self.ink.dim(mark))
        wr = Wrap(self.w, self.width(), len(mark))
        # A human line opens with the prefix's newline (it is how the seam between speakers
        # gets into the file); in a card that newline would leave the number alone on its
        # row and the text hanging under it. The card is a listing, not the document, so
        # the seam is dropped here. Model text keeps whatever it starts with — in a bare
        # sitting a branch that opens with a newline is telling you something.
        wr.feed(n["text"].lstrip("\n") if n["kind"] == "human" else n["text"])
        wr.end()
        if n["posed"]:
            self.w(self.ink.magenta("  posed"))
        self.w("\n")
        self.borrowed = True

    def show_kids(self, nid: str, came=None) -> None:
        ks = self.kids(nid)
        if not ks:
            self.note("  (no candidates)")
            return
        for i, n in enumerate(ks, 1):
            self.card(i, n, star=(n["id"] == came))

    def stat(self) -> None:
        s = self.sitting
        live = sum(1 for n in s["nodes"].values() if not n["pruned"])
        self.line(self.ink.dim(
            f"eva · {s['name']} · {live} live · depth {len(self.path()) - 1}"))

    def present(self) -> None:
        """What opening a sitting looks like: the line, the document, what is on offer."""
        self.stat()
        self.echo_doc()
        if self.kids(self.sitting["current"]):
            self.show_kids(self.sitting["current"])

    # -- the prompt ---------------------------------------------------------------
    def prompt(self) -> str:
        if not self.sitting:
            return self.ink.rl("eva: ", "2")
        if self.bare():
            # Nothing but what is typed enters the document here, so the prompt must be
            # visibly not text.
            return self.ink.rl("› ", "2")
        core = (self.sitting["turn"]["prefix"] or "").strip() or "…"
        return self.ink.rl(core + " ", "36")

    def open_turn(self) -> None:
        """The newlines the turn prefix opens with, before readline writes the name.

        This is the half of the prefix readline cannot type for us: the prompt is only its
        trimmed tail. Skipped when the last break on the screen was ours (see `borrowed`).
        """
        if not self.sitting or self.bare():
            return
        self.doc_lead(leading_nl(self.sitting["turn"]["prefix"] or ""))

    # -- moves --------------------------------------------------------------------
    def fan(self, count: int) -> None:
        if not self.sitting:
            self.err("no sitting open")
            return
        from_id = self.sitting["current"]
        prompt = self.prompt_from(from_id)
        p = self.sitting["params"]
        # One temperature per branch, so a fan can be a slice through the range instead of
        # four draws at one setting. With spread 0 every value is the plain temperature and
        # this is the loop it always was.
        temps = spread_temps(p.get("temperature", 1.0), p.get("spread", 0), count)
        for temp in temps:
            # Numbered by where it lands in kids(from_id), so /more keeps climbing 4, 5, 6
            # and a prune in between is reflected the next time the list is drawn.
            num = len(self.kids(from_id)) + 1
            mark = self.marker(num)
            self.bol()
            self.w(self.ink.dim(mark))
            wr = Wrap(self.w, self.width(), len(mark))
            # A copy per branch: what goes into meta has to be the params that actually
            # made THIS line, or a spread fan reads back as four lines at one temperature.
            params = json.loads(json.dumps(p))
            params["temperature"] = temp
            try:
                d = complete_stream(prompt, params, wr.feed)
            except KeyboardInterrupt:
                # The socket is already shut (complete_stream's finally) so llama has the
                # slot back. The half-written branch is thrown away, not saved: a truncated
                # continuation nobody chose would be indistinguishable later from one the
                # model actually ended there.
                wr.end()
                self.w("\n")
                self.borrowed = True
                self.note("── cut ──")
                return
            wr.end()
            self.w("\n")
            self.borrowed = True
            if d.get("error"):
                self.err(d["error"])
                return
            self.add_node("model", d["text"], from_id, {
                "stop_type": d["stop_type"], "stopping_word": d["stopping_word"],
                "tokens_predicted": d["tokens_predicted"], "tps": d["tps"],
                "probs": d.get("probs"),
                # Frozen: a branch is only readable later if you know what produced it, and
                # the sampler moves between fans.
                "params": params,
            })
            self.save()

    def send(self, typed: str, fan: bool = True, echoed: bool = True) -> None:
        """His line into the document: prefix + typed + suffix, one flat string.

        Built here and stored whole, so the file is a document and the two names are
        nothing but settings — rename the seat with /set and the next node carries the new
        name while the old ones keep theirs.

        `echoed` is the difference between a line typed at the prompt and one that came out
        of $EDITOR: readline has already put `bekh: <line>` and the Enter on the screen, so
        only the suffix is left to print — minus its own newline, which the Enter was.
        """
        t = self.sitting["turn"]
        text = t["prefix"] + typed + t["suffix"]
        n = self.add_node("human", text, self.sitting["current"])
        self.sitting["current"] = n["id"]
        self.save()
        if echoed:
            suf = t["suffix"]
            self.doc(suf[1:] if suf.startswith("\n") else suf)
        else:
            self.echo_node(n)
        if fan:
            self.fan(self.sitting["params"].get("fan") or 4)

    def pick(self, i: int) -> None:
        ks = self.kids(self.sitting["current"])
        if not 1 <= i <= len(ks):
            self.err(f"no candidate {i}")
            return
        n = ks[i - 1]
        self.sitting["current"] = n["id"]
        self.save()
        self.echo_model(n)

    # -- commands ------------------------------------------------------------------
    def cmd_back(self) -> None:
        n = self.node(self.sitting["current"])
        if not n["parent"]:
            self.err("already at the root")
            return
        came = n["id"]
        self.sitting["current"] = n["parent"]
        self.save()
        self.note("── back ──")
        parent = self.node(self.sitting["current"])
        if parent["kind"] == "model":
            self.echo_model(parent)
        else:
            self.echo_node(parent)
        self.show_kids(parent["id"], came=came)

    def cmd_prune(self, arg: str) -> None:
        if not arg:
            n = self.node(self.sitting["current"])
            if n["kind"] != "model" or not n["parent"]:
                self.err("/prune N — or /prune on a model line you are standing on")
                return
            n["pruned"] = True          # hidden, never deleted: a branch cut in a bad mood is evidence too
            self.sitting["current"] = n["parent"]
            self.save()
            self.note("── pruned, back ──")
            self.show_kids(self.sitting["current"])
            return
        try:
            i = int(arg)
        except ValueError:
            self.err("/prune N")
            return
        ks = self.kids(self.sitting["current"])
        if not 1 <= i <= len(ks):
            self.err(f"no candidate {i}")
            return
        ks[i - 1]["pruned"] = True
        self.save()
        # Relisted because the numbers just moved under him, and a stale number is a pick
        # of the wrong branch.
        self.note("── pruned ──")
        self.show_kids(self.sitting["current"])

    def cmd_edit(self, arg: str) -> None:
        if arg:
            try:
                i = int(arg)
            except ValueError:
                self.err("/edit N — or /edit for the line you are standing on")
                return
            ks = self.kids(self.sitting["current"])
            if not 1 <= i <= len(ks):
                self.err(f"no candidate {i}")
                return
            n = ks[i - 1]
        else:
            n = self.node(self.sitting["current"])
            i = 0
        text = edit_text(n["text"])
        if text is None:
            self.err("no editor: set $EDITOR")
            return
        if text == n["text"]:
            self.note("── unchanged ──")
            return
        n["text"] = text
        if n["kind"] == "model":
            # Posed forever. The tag is the only thing standing between "the model said
            # this" and "we said this and forgot", which is the one confusion that would
            # make a whole sitting worthless as evidence.
            n["posed"] = True
        self.save()
        if i:
            self.card(i, n)
        else:
            self.note("── edited ──")

    def cmd_say(self, fan: bool) -> None:
        text = edit_text("")
        if text is None:
            self.err("no editor: set $EDITOR")
            return
        if fan:
            # Bare: whitespace is text. In chat the outer newlines are the turn strings' job.
            typed = text if self.bare() else text.strip("\n")
            if not typed:
                self.note("── nothing said ──")
                return
            self.send(typed, echoed=False)
            return
        # /seed puts the block in VERBATIM — no prefix, no suffix, no trim. This is for
        # pasting lines cut from a real room, which already carry both speakers' names;
        # wrapping them in "bekh: … seat:" would put a name inside a line that has one.
        if not text:
            self.note("── nothing seeded ──")
            return
        n = self.add_node("human", text, self.sitting["current"])
        self.sitting["current"] = n["id"]
        self.save()
        self.echo_node(n)

    def cmd_doc(self) -> None:
        self.bol()
        self.borrowed = False
        self.echo_doc()
        # After the document, not before it: the measure is of the thing just printed.
        self.note(curation_line(self.sitting))

    def cmd_set(self, arg: str) -> None:
        p = self.sitting["params"]
        if not arg:
            for k, v in p.items():
                self.line(f"  {k} = {v!r}")
            for k in ("prefix", "suffix"):
                # repr, so the newlines that make the turn work are visible as \n
                self.line(f"  {k} = {self.sitting['turn'][k]!r}")
            return
        key, _, val = arg.partition(" ")
        val = val.strip()
        if key in ("prefix", "suffix"):
            self.sitting["turn"][key] = unesc(val)
            self.save()
            self.note(f"  {key} = {self.sitting['turn'][key]!r}")
            return
        if key not in p:
            self.err(f"no such param: {key}")
            return
        cur = p[key]
        try:
            if key == "stop":
                new = ast.literal_eval(val)
                if not isinstance(new, list) or not all(isinstance(s, str) for s in new):
                    raise ValueError("stop is a list of strings")
            elif key == "logit_bias":
                # llama's own shape, typed out: [["word", -2], [1234, -100]]. A python
                # literal and not the page's one-per-line text, because the repl already
                # has literal_eval for `stop` and a second syntax here would be a second
                # thing to remember.
                new = ast.literal_eval(val)
                if not isinstance(new, list) or not all(
                        isinstance(e, (list, tuple)) and len(e) == 2 for e in new):
                    raise ValueError("logit_bias is a list of [token, bias] pairs")
                new = [list(e) for e in new]
                # The drawer's words no longer describe what is being sent.
                p.pop("logit_bias_text", None)
            elif key == "fan":
                new = max(1, int(val))
            elif isinstance(cur, bool):
                new = val.lower() in ("1", "true", "yes", "on")
            elif isinstance(cur, (int, float)):
                # By what was typed, not by the stored type: the page's js writes
                # `temperature: 1` as an int, and following that type would make
                # `/set temperature 0.9` fail on every sitting the browser made.
                new = int(val) if val.lstrip("-").isdigit() else float(val)
            else:
                new = val
        except (ValueError, SyntaxError) as exc:
            self.err(f"bad value for {key}: {exc}")
            return
        p[key] = new
        self.save()
        self.note(f"  {key} = {new!r}")

    def cmd_open(self, arg: str) -> None:
        name = arg.strip()
        if not name:
            name = self.choose()
            if not name:
                return
        self.open(name)

    def cmd_spin(self, arg: str) -> None:
        """The document down to where you are standing, as the root of a new bare room.

        Nothing is stripped: what goes in is exactly the string the model was reading. The
        sampler comes with it, so the continuation happens at the heat it was found at, and
        the stop strings do not — a bare room is a document, not a conversation.
        """
        name = arg.strip() or secrets.token_hex(4)
        text = self.prompt_from(self.sitting["current"])
        params = json.loads(json.dumps(self.sitting["params"]))
        title = ("spun off from " + (self.sitting.get("title") or self.sitting["name"]))[:120]
        if not self.new(name, True, text):
            return
        self.sitting["params"] = params
        self.sitting["params"]["stop"] = []
        self.sitting["title"] = title
        self.save()

    def cmd_new(self, arg: str) -> None:
        parts = arg.split()
        is_bare = bool(parts) and parts[0] == "bare"
        if is_bare:
            parts = parts[1:]
        if not parts:
            self.err("/new [bare] name")
            return
        self.new(parts[0], is_bare)

    # -- the shelf ------------------------------------------------------------------
    def choose(self) -> str:
        """The shelf, numbered; a number opens one, anything else is a name to make."""
        rows = shelf()
        if not rows:
            return (self.read(self.ink.rl("new sitting (name): ", "2")) or "").strip()
        for i, s in enumerate(rows, 1):
            self.line(self.ink.dim(self.marker(i)) + f"{s['name']}  " +
                      self.ink.dim(f"{s['nodes']} nodes"))
        ans = (self.read(self.ink.rl("open (number or a new name): ", "2")) or "").strip()
        if ans.isdigit() and 1 <= int(ans) <= len(rows):
            return rows[int(ans) - 1]["name"]
        return ans

    def open(self, name: str) -> bool:
        if not name_ok(name):
            self.err("names are letters, digits, _ . - and / for a folder")
            return False
        path = sitting_path(name)
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except OSError:
            self.err(f"no sitting called {name}")
            return False
        except ValueError:
            self.err(f"{name}.json isn't json any more")
            return False
        why = check(d)
        if why:
            self.err(f"{name}: {why}")
            return False
        backfill(d.setdefault("params", {}))
        self.sitting = d
        self.atbol, self.borrowed = True, False
        self.present()
        return True

    def new(self, name: str, is_bare: bool = False, root_text: str | None = None) -> bool:
        if not name_ok(name):
            self.err("names are letters, digits, _ . - and / for a folder")
            return False
        # A no-op on a name that's taken: without this, `/new ss` wrote an empty tree over a
        # real room, with no copy anywhere. Opening it is one command away and says so.
        if os.path.exists(sitting_path(name)):
            self.err(f"{name} already exists, nothing changed — /open {name}")
            return False
        # One line of scene-setting and an empty seed, and that is the whole of it. No
        # example exchanges ship with this tool: seeded lines have to be bekh's own, cut
        # from a real room, and anything invented here would be us writing his half.
        self.sitting = blank(name, is_bare, root_text)
        self.atbol, self.borrowed = True, False
        if not self.save():
            self.sitting = None
            return False
        self.present()
        return True

    # -- the keyboard -----------------------------------------------------------------
    def dispatch(self, line: str) -> bool:
        """One line from the prompt. False means stop the loop."""
        s = line.strip()

        if s.startswith("/"):
            cmd, _, arg = s[1:].partition(" ")
            arg = arg.strip()
            if cmd in ("quit", "q", "exit"):
                return False
            if cmd == "open":
                self.cmd_open(arg)
                return True
            if cmd == "new":
                self.cmd_new(arg)
                return True
            if not self.sitting:
                self.err("no sitting open — /open or /new name")
                return True
            if cmd == "back":
                self.cmd_back()
            elif cmd == "prune":
                self.cmd_prune(arg)
            elif cmd == "edit":
                self.cmd_edit(arg)
            elif cmd == "say":
                self.cmd_say(fan=True)
            elif cmd == "seed":
                self.cmd_say(fan=False)
            elif cmd == "doc":
                self.cmd_doc()
            elif cmd == "spin":
                self.cmd_spin(arg)
            elif cmd == "set":
                self.cmd_set(arg)
            elif cmd == "more":
                self.fan(self.sitting["params"].get("fan") or 4)
            elif cmd == "fan":
                try:
                    n = max(1, int(arg))
                except ValueError:
                    self.err("/fan N")
                    return True
                self.sitting["params"]["fan"] = n
                self.save()
                self.fan(n)
            else:
                self.note(HELP)
            return True

        if not self.sitting:
            self.err("no sitting open — /open or /new name")
            return True

        if s.isdigit():
            self.pick(int(s))
            return True

        if not s:
            self.fan(self.sitting["params"].get("fan") or 4)
            return True

        # Bare: whitespace is text. A trailing space is the difference between "continue
        # this word" and "start the next one", and trimming would decide it for him.
        self.send(line if self.bare() else s)
        return True

    def loop(self) -> None:
        while True:
            self.open_turn()
            try:
                line = self.read(self.prompt())
            except EOFError:
                self.w("\n")
                return
            except KeyboardInterrupt:
                # ^C at the prompt throws the half-typed line away and asks again; the
                # terminal has written "^C" where the cursor was, so one break, not two.
                self.atbol = False
                self.w("\n")
                self.borrowed = True
                continue
            # readline echoed the line and the Enter; the screen is at the start of a line
            # and that break is the document's own (the turn suffix accounts for it).
            self.atbol, self.borrowed = True, False
            try:
                if not self.dispatch(line):
                    return
            except KeyboardInterrupt:
                # The fan catches ^C inside the streaming window itself; this is the net for
                # the microseconds around it (a save, an editor spawn) — a traceback there
                # would kill the session over a keypress that meant "stop".
                self.atbol = False
                self.w("\n")
                self.borrowed = True
                self.note("── cut ──")


def console_read(prompt: str) -> str:
    s = input(prompt)
    if not sys.stdin.isatty():
        # No terminal echo behind a pipe, and the scrollback IS the document — put back
        # what a tty would have shown, or a piped run writes a transcript with holes.
        sys.stdout.write(s + "\n")
        sys.stdout.flush()
    return s


def hook_history() -> None:
    """History across sessions. Everything in here is optional by construction.

    Broad except on purpose: uv's macOS python backs readline with libedit, which differs
    from GNU readline on history files and on bind syntax, and none of that is worth a
    traceback in front of a sitting.
    """
    try:
        import readline
    except Exception:
        return
    try:
        for b in ("tab: self-insert", "bind ^I ed-insert"):   # GNU, then libedit
            try:
                readline.parse_and_bind(b)
            except Exception:
                pass
        os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
        try:
            readline.read_history_file(HISTORY)
        except Exception:
            pass

        def dump():
            try:
                readline.write_history_file(HISTORY)
            except Exception:
                pass
        atexit.register(dump)
    except Exception:
        pass


def main(argv: list[str]) -> int:
    hook_history()
    ev = Eva()
    name = argv[1].strip() if len(argv) > 1 else ""
    if not name:
        try:
            name = ev.choose()
        except (EOFError, KeyboardInterrupt):
            return 0
    if not name:
        return 0
    # A name that doesn't read at all goes to `new`, which is the one place that says why.
    if not name_ok(name) or not os.path.isfile(sitting_path(name)):
        if not ev.new(name):
            return 1
    elif not ev.open(name):
        return 1
    ev.loop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
