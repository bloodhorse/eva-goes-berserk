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

One knob of its own, for the cancel test: a prompt containing SLOW takes three seconds
instead of a third of one, so a test can reliably hang up on a call in flight.

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
            # The three fields an artifact reads, shaped as llama-server shapes them.
            self._json(200, {"model_path": "/models/stub-base-12b.Q5_K_M.gguf",
                             "default_generation_settings": {"n_ctx": 8192},
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
        # is what the stop list is for, and what gets cut.
        text = random.choice(LINES) + "\nbekh: and then what"
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


def serve(port: int = 0) -> ThreadingHTTPServer:
    """Bound and ready, not yet serving. port 0 lets the OS pick — read it back off
    `srv.server_address[1]`, which is how the test avoids racing another process for a
    port it guessed."""
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    return srv


if __name__ == "__main__":
    srv = serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8099)
    print(f"stub llama up: http://127.0.0.1:{srv.server_address[1]}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
