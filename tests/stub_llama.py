#!/usr/bin/env -S uv run --python 3.12
"""stub_llama.py — a fake llama-server, so the loom can be tested without a 9 GB model.

Answers the two routes the loom actually uses, in llama-server's own shapes:

  GET  /health      -> {"status":"ok"}
  POST /completion  -> {"content", "stop_type", "stopping_word", "tokens_predicted",
                        "timings":{"predicted_per_second": …}}
                       with "stream": true in the body, the same answer as text/event-stream:
                       a few `data: {"content": …}` events and a final one with "stop": true

Two behaviours are copied on purpose because they are the ones that bite:

  * the stop string is EATEN — cut out of `content` and reported separately in
    `stopping_word`. The loom has to put it back when it builds the next prompt, and a
    stub that left it in would let that bug ship.
  * the continuation VARIES between calls. A stub that answered the same text every time
    would pass a fan test that a real fan of four identical branches would fail.

One knob of its own, for the cancel test: a prompt containing SLOW takes three seconds
instead of a third of one, so a test can reliably hang up on a call in flight.

Run standalone: `uv run --python 3.12 tests/stub_llama.py [port]` — prints the port it
bound. Imported by loomtest.py, which runs `serve()` on a thread.
"""

from __future__ import annotations

import json
import random
import sys
import time
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
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/completion":
            self._json(404, {"error": "not found"})
            return
        n = int(self.headers.get("Content-Length", "0") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
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

        done = {
            "content": text,
            "stop_type": stop_type,
            "stopping_word": word,
            "tokens_predicted": max(1, len(text.split())),
            "timings": {"predicted_per_second": round(random.uniform(20.0, 60.0), 2)},
        }
        if body.get("stream"):
            self._sse(done)
            return
        self._json(200, done)

    def _sse(self, done: dict) -> None:
        """The same answer, in pieces, the way llama-server streams it.

        eva.py reads this route with an SSE parser, so a stub that only ever answered in
        one lump would let a parser that mishandles chunk boundaries pass its tests. The
        final event carries `stop` and the timings and NO new text — the loom's own rule is
        that the text is the concatenation of the pieces, not a field on the last one.
        """
        text = done["content"]
        n = 3
        size = max(1, -(-len(text) // n))
        pieces = [text[i:i + size] for i in range(0, len(text), size)] or [""]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        for piece in pieces:
            self._event({"content": piece, "stop": False})
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
