#!/usr/bin/env -S uv run --python 3.12
"""stub_llama.py — a fake llama-server, so the loom can be tested without a 9 GB model.

Answers the routes the loom actually uses, in llama-server's own shapes:

  GET  /health      -> {"status":"ok"}
  GET  /props       -> {"model_path", "default_generation_settings": {"n_ctx"}, "build_info"}
  POST /tokenize    -> {"tokens": [id, …]} — one id per whitespace-led word, so " the" is
                       one token and "hello there" is two
  POST /completion  -> {"content", "stop_type", "stopping_word", "tokens_predicted",
                        "timings":{"predicted_per_second": …}}
                       with "stream": true in the body, the same answer as text/event-stream:
                       one `data: {"content": …}` event per token and a final one with
                       "stop": true
  GET  /seen        -> {"seen": [every request body this process was sent]} — not a
                       llama-server route. It is how a test reads what actually went over
                       the wire: the per-branch temperature of a spread fan, the logit_bias
                       the drawer parsed. Asserting on the saved node would only prove the
                       page copied its own number into meta.

Three behaviours are copied on purpose because they are the ones that bite:

  * the stop string is EATEN — cut out of `content` and reported separately in
    `stopping_word`. The loom has to put it back when it builds the next prompt, and a
    stub that left it in would let that bug ship.
  * the continuation VARIES between calls. A stub that answered the same text every time
    would pass a fan test that a real fan of four identical branches would fail.
  * `completion_probabilities` is shaped exactly as llama-server shapes it (verified
    against tools/server/server-task.cpp on master): entries of
    {id, token, bytes, logprob, top_logprobs:[{id, token, bytes, logprob}]}, `bytes` and
    all, and — the part that is easy to get wrong — it rides on the FINAL object when the
    answer is one lump, but on EACH PARTIAL, one token at a time, when it streams. A
    reader that only looked at the last streamed event would collect nothing.

Two knobs of its own:

  * for the cancel test, a prompt containing SLOW takes three seconds instead of a third of
    one, so a test can reliably hang up on a call in flight.
  * for berserk's reader, `READER_MODE`. berserk asks the same model a second question at
    every fork, and the answer has to come OUT OF THE PROMPT, or nothing downstream can be
    tested at all. A stub answering its usual random line would only ever exercise the
    failure path. The seam is the shape of the prompt's last line, because that is all a
    markerless reader document has: `": “"` at the end is the quote ask (answered with a
    fragment's opening), `"scared me was about"` is the about ask (answered with a
    description — ten words of a fragment minus its first word, so it is not a quotation of
    anything), `"what scared me was"` is one margin note (answered with a note naming the
    fragment's third word, so the notes differ from each other), and `"because"` is the
    follow-up asking why. `READER_MODE = "quote"` means the stub cooperates with all three,
    `"garbage"` answers a sentence that is in no branch (every fork ends random), and the
    default `""` leaves the stub's ordinary random line, which also matches nothing.

Run standalone: `uv run --python 3.12 tests/stub_llama.py [port]` — prints the port it
bound. Imported by loomtest.py, which runs `serve()` on a thread.
"""

from __future__ import annotations

import json
import math
import random
import re
import sys
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LINES = [
    " yeah i know what you mean but it never lands like that",
    " nah man thats not it at all, listen",
    " ok so picture it this way, its the same thing twice",
    " hm. dunno. i keep coming back to the same bit",
    " thats the part i cant get past honestly",
    " sure, if you squint. i dont squint",
]
SLOW_MARK = "SLOW"
SLOW = 3.0
NORMAL = 0.3

# "" (ordinary lines), "quote" (answer with a branch's opening) or "garbage" (answer with a
# sentence that is in no branch). Set and put back by the test that wants it: this module is
# one per process and the whole suite shares it.
READER_MODE = ""
NO_BRANCH = "the witch counted her teeth"

# The last words of each of berserk's three frame lines. The prompt's ending is the only
# thing that says which ask this is — the documents themselves are markerless on purpose.
ABOUT_TAIL = "scared me was about"
MARGIN_TAIL = "what scared me was"
QUOTE_TAIL = ": “"

# Every request body, in order. A list and nothing else — the tests read it through
# GET /seen over the socket, or straight off the module when they run the stub in-thread.
SEEN: list[dict] = []

# Fixed, and deliberately spanning the whole range the page has to paint: a near-certain
# token, a coin flip, one under 10%, one under 1%. A stub with uniform probabilities would
# make any tint formula look right.
PROB_CYCLE = [0.92, 0.41, 0.07, 0.006, 0.63, 0.18]
ALTS = [" but", " and", " not", "\n", " the", " maybe"]


def tokens_of(text: str) -> list[str]:
    """Pieces that concatenate back to exactly `text`. Not a real tokenizer — the only
    property anything downstream depends on is that the pieces rebuild the string, because
    that is what lets the page paint a line and fork inside it."""
    return re.findall(r"\s+|\S+", text)


def probs_for(text: str, n_probs: int) -> list[dict]:
    """llama-server's `completion_probabilities`, shape for shape (server-task.cpp's
    `probs_vector_to_json`): the chosen token with its logprob, then `top_logprobs` with at
    most n_probs entries, the chosen one among them. `bytes` is included precisely because
    the loom is supposed to throw it away before it ever reaches a saved sitting."""
    out = []
    for i, tok in enumerate(tokens_of(text)):
        p = PROB_CYCLE[i % len(PROB_CYCLE)]
        top = [entry(tok, p)]
        left = 1.0 - p
        for k in range(n_probs - 1):
            alt = ALTS[(i + k) % len(ALTS)]
            left = left / 2
            top.append(entry(alt, round(left, 6)))
        out.append(dict(entry(tok, p), top_logprobs=top))
    return out


def reader_reply(prompt: str) -> str | None:
    """berserk's reader, or None when this prompt is not one of its asks.

    Which ask it is can only be read off the last line, because the reader document carries
    no markers at all, by design. Same reason the branches are found as the paragraphs
    between the document's tail (the first one) and the ask line (the last one): paragraphs
    are the only structure there is.
    """
    if prompt.endswith("because"):
        return " it kept talking after the door had already shut"
    paras = [p for p in prompt.split("\n\n") if p.strip()]

    if prompt.endswith(ABOUT_TAIL):
        if READER_MODE == "garbage":
            return NO_BRANCH
        if READER_MODE != "quote" or len(paras) < 3:
            return None
        # A DESCRIPTION, not a quotation: ten words of a fragment with its first word cut
        # off, so it is no longer something the substring matcher can find at a fragment's
        # start. That is the whole point of the about picker — the resolver has to decide.
        return " ".join(random.choice(paras[1:-1]).split()[1:11])

    if prompt.endswith(MARGIN_TAIL):
        if READER_MODE != "quote" or len(paras) < 2:
            return None
        # One fragment per margin call, so it is the paragraph before the note line. The
        # third word goes in the note because it is the first word that differs between
        # branches — notes that all read alike would make the picking test meaningless.
        words = paras[-2].split()
        return f"the part where it said {words[2] if len(words) > 2 else 'nothing'}"

    if not prompt.endswith(QUOTE_TAIL):
        return None
    if READER_MODE == "garbage":
        return NO_BRANCH
    if READER_MODE != "quote" or len(paras) < 3:
        return None
    # Fourteen words, not eight: every fragment opens with the document's unfinished last
    # line, and once the document has grown that lead is a whole branch line long. A short
    # quotation would be nothing but the lead, which is the same for every fragment and
    # therefore matches none of them — a stub that could only ever quote the shared part
    # would test the failure path and call it the happy one.
    return " ".join(random.choice(paras[1:-1]).split()[:14])


def fake_id(text: str) -> int:
    """A stable id per spelling. crc32 and not sum-of-bytes: "the" and " The" have the same
    byte sum, and a stub where two spellings share an id would hide the very bug the
    drawer's four-spelling resolver exists to dodge."""
    return 1000 + (zlib.crc32(text.encode("utf-8")) % 30000)


def entry(tok: str, p: float) -> dict:
    raw = tok.encode("utf-8")
    return {"id": fake_id(tok), "token": tok, "bytes": list(raw), "logprob": math.log(p)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a) -> None:
        pass

    def _json(self, code: int, obj: dict) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"status": "ok"})
            return
        if self.path == "/props":
            # The three fields an artifact reads, shaped as llama-server shapes them. The
            # path and the window come off THIS server, not off the module: a census that
            # compares two models runs two stubs in one process, and they have to be able
            # to answer different names and different context sizes.
            self._json(200, {"model_path": getattr(self.server, "model_path",
                                                   "/models/stub-base-12b.Q5_K_M.gguf"),
                             "default_generation_settings": {
                                 "n_ctx": getattr(self.server, "n_ctx", 8192)},
                             "build_info": "b0000-stub", "total_slots": 1})
            return
        if self.path == "/seen":
            self._json(200, {"seen": list(SEEN)})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path not in ("/completion", "/tokenize"):
            self._json(404, {"error": "not found"})
            return
        n = int(self.headers.get("Content-Length", "0") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        SEEN.append(body)
        # And once more per server. SEEN is one list for the whole process, so with two
        # stubs up it cannot say WHICH of them was asked — which is exactly the thing a
        # two-model census has to prove.
        getattr(self.server, "seen", []).append(body)
        if self.path == "/tokenize":
            # One id per whitespace-led word, so " the" is one token and "hello there" is
            # two — which is the only property the drawer's resolver depends on: a spelling
            # that comes back as more than one token cannot be biased and is dropped.
            content = body.get("content") or ""
            ids = [fake_id(w) for w in re.findall(r"\s*\S+", content)]
            self._json(200, {"tokens": ids})
            return
        prompt = body.get("prompt") or ""
        stops = [s for s in (body.get("stop") or []) if isinstance(s, str) and s]

        time.sleep(SLOW if SLOW_MARK in prompt else NORMAL)

        # A whole turn: the reply, then the other man starting to speak. The second half
        # is what the stop list is for, and what gets cut. A berserk reader ask answers a
        # quotation instead — see READER_MODE.
        quoted = reader_reply(prompt)
        if quoted is not None:
            text = quoted
        else:
            # A server may carry its own script of lines, handed out IN ORDER and wrapping —
            # `srv.lines`, beside `n_ctx` and `model_path`, for the same reason those exist: a
            # test with two stubs in one process needs one of them to answer something
            # particular. wire.py's retry-then-swap is only reachable that way, because it
            # turns on a model answering NOTHING twice and then the other one answering, and
            # the module's random pick can neither be empty on demand nor twice in a row.
            own = getattr(self.server, "lines", None)
            if own:
                i = getattr(self.server, "_line_i", 0)
                self.server._line_i = i + 1
                line = own[i % len(own)]
            else:
                line = random.choice(LINES)
            # A LINES entry that is the empty string means the model answered with NOTHING,
            # not "a blank line and then the other speaker" — which is what a base model
            # standing on a licence footer really does, and what the fan, the artifact and
            # berserk's anthology page all have to survive. Append the turn unconditionally
            # and no test can ever produce an empty branch.
            text = (line + "\nbekh: and then what") if line else ""
        stop_type, word = "limit", ""
        cut = [(text.find(s), s) for s in stops if text.find(s) >= 0]
        if cut:
            at, word = min(cut)
            text, stop_type = text[:at], "word"
        # n_predict is honoured crudely — enough that a tiny n_predict visibly truncates.
        cap = body.get("n_predict")
        if isinstance(cap, int) and 0 < cap < len(text.split()):
            text = " ".join(text.split()[:cap])
            stop_type, word = "limit", ""

        try:
            n_probs = int(body.get("n_probs") or 0)
        except (TypeError, ValueError):
            n_probs = 0

        done = {
            "content": text,
            "stop_type": stop_type,
            "stopping_word": word,
            "tokens_predicted": max(1, len(text.split())),
            "timings": {"predicted_per_second": round(random.uniform(20.0, 60.0), 2)},
        }
        if body.get("stream"):
            self._sse(done, n_probs)
            return
        if n_probs > 0:
            done["completion_probabilities"] = probs_for(text, n_probs)
        self._json(200, done)

    def _sse(self, done: dict, n_probs: int) -> None:
        """The same answer, in pieces, the way llama-server streams it.

        eva.py reads this route with an SSE parser, so a stub that only ever answered in
        one lump would let a parser that mishandles chunk boundaries pass its tests. The
        final event carries `stop` and the timings and NO new text — the loom's own rule is
        that the text is the concatenation of the pieces, not a field on the last one.

        One token per event, each carrying its own single-entry `completion_probabilities`,
        because that is llama's own split: `if (!stream && ...)` guards the whole-array
        field, so a streamed run NEVER gets the probabilities in one lump at the end.
        """
        text = done["content"]
        pieces = tokens_of(text)
        probs = probs_for(text, n_probs) if n_probs > 0 else []
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        for i, piece in enumerate(pieces):
            ev = {"content": piece, "stop": False}
            if probs:
                ev["completion_probabilities"] = [probs[i]]
            self._event(ev)
        self._event(dict(done, content="", stop=True))

    def _event(self, obj: dict) -> None:
        self.wfile.write(b"data: " + json.dumps(obj, ensure_ascii=False).encode("utf-8") + b"\n\n")
        self.wfile.flush()


def serve(port: int = 0, n_ctx: int = 8192,
          model_path: str = "/models/stub-base-12b.Q5_K_M.gguf",
          lines: list[str] | None = None) -> ThreadingHTTPServer:
    """Bound and ready, not yet serving. port 0 lets the OS pick — read it back off
    `srv.server_address[1]`, which is how the test avoids racing another process for a
    port it guessed.

    `n_ctx` and `model_path` are what this one answers on /props, `lines` is its own script of
    answers in order (an empty string means it answered nothing), and `srv.seen` is what it
    alone was asked: four things a second stub in the same process needs of its own.
    """
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    srv.n_ctx = n_ctx
    srv.model_path = model_path
    srv.lines = lines
    srv.seen = []
    return srv


if __name__ == "__main__":
    srv = serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8099)
    print(f"stub llama up: http://127.0.0.1:{srv.server_address[1]}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
