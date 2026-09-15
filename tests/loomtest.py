#!/usr/bin/env -S uv run --python 3.12
"""loomtest.py — every route of loom.py, end to end, against the fake llama-server.

    uv run --python 3.12 -m unittest tests/loomtest.py

Nothing is mocked inside the server: a real loom.py runs in a subprocess against a real
socket, and the stub stands in for the only thing that would otherwise cost 9 GB and a
warm GPU. The sittings go to a temp directory (LOOM_SITTINGS) so a test run can never
touch a real one.

The tree moves — pick, prune, human line, edit — live in the browser, not in the server,
so `Tree` below is a small python twin of loom.html's own tree code. That is the point of
testing them here: if the page's rules and this file's rules drift, the round trip through
POST /api/sitting is where it shows up, because the server validates the shape both ways.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import uuid

TESTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS)
sys.path.insert(0, TESTS)
import stub_llama  # noqa: E402 — path first; this file may be started from anywhere

# loom.html's own defaults, restated. Kept as literals rather than parsed out of the page
# on purpose: if somebody changes the header line or the turn strings in the page, this
# file should have to be changed too, by a human who reads why.
HEADER = "a chat log between two friends, saved from a phone. no punctuation fixed, no capitals.\n"
TURN = {"prefix": "\nbekh: ", "suffix": "\nseat:"}
PARAMS = {
    "n_predict": 220, "stop": ["\nbekh:", "\nbekh :", "\n\nbekh"],
    "temperature": 1.0, "min_p": 0.08, "top_k": 0, "top_p": 1.0,
    "repeat_penalty": 1.05, "repeat_last_n": 512,
    "dry_multiplier": 0.8, "dry_base": 1.75, "dry_allowed_length": 3,
    "dry_penalty_last_n": 8192, "fan": 4,
}

STUB = None
LOOM = None
BASE = ""
SHELF = ""


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def call(path: str, body=None, timeout: float = 30):
    """(status, parsed body). An HTTP error is an answer here, not an exception: the loom
    says 400 and 502 on purpose and the tests want to read what it said."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method="POST" if data else "GET",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw, status, ctype = r.read(), r.status, r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raw, status, ctype = e.read(), e.code, e.headers.get("Content-Type", "")
    if "json" in ctype:
        return status, json.loads(raw)
    return status, raw.decode("utf-8", "replace")


def setUpModule() -> None:
    global STUB, LOOM, BASE, SHELF
    STUB = stub_llama.serve(0)
    threading.Thread(target=STUB.serve_forever, daemon=True).start()
    SHELF = tempfile.mkdtemp(prefix="loom-test-")
    port = free_port()
    BASE = f"http://127.0.0.1:{port}"
    env = dict(os.environ,
               LOOM_HOST="127.0.0.1", LOOM_PORT=str(port), LOOM_SITTINGS=SHELF,
               LOOM_LLAMA=f"http://127.0.0.1:{STUB.server_address[1]}")
    LOOM = subprocess.Popen([sys.executable, os.path.join(ROOT, "loom.py")],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    deadline = time.time() + 20
    while time.time() < deadline:
        if LOOM.poll() is not None:
            raise RuntimeError("loom died on start: " + LOOM.stdout.read().decode())
        try:
            if call("/")[0] == 200:
                return
        except OSError:
            pass
        time.sleep(0.15)
    raise RuntimeError("loom never came up")


def tearDownModule() -> None:
    if LOOM and LOOM.poll() is None:
        LOOM.terminate()          # by handle, never by name: pkill -f would match this test
        try:
            LOOM.wait(timeout=5)
        except subprocess.TimeoutExpired:
            LOOM.kill()
    if STUB:
        STUB.shutdown()
    if SHELF:
        shutil.rmtree(SHELF, ignore_errors=True)


class Tree:
    """loom.html's tree, in python. Same rules, stated where the tests can read them."""

    def __init__(self, name: str) -> None:
        root = self.node("root", HEADER, None)
        self.d = {"name": name, "created": time.time(), "updated": 0,
                  "params": json.loads(json.dumps(PARAMS)),
                  "turn": json.loads(json.dumps(TURN)),
                  "root": root["id"], "current": root["id"],
                  "nodes": {root["id"]: root}}

    @staticmethod
    def node(kind: str, text: str, parent):
        return {"id": uuid.uuid4().hex[:8], "parent": parent, "kind": kind, "text": text,
                "ts": time.time(), "pruned": False, "posed": False, "meta": None}

    def add(self, kind: str, text: str, parent, meta=None) -> dict:
        n = self.node(kind, text, parent)
        n["meta"] = meta
        self.d["nodes"][n["id"]] = n
        return n

    def prompt_from(self, nid: str) -> str:
        """Concatenation along root→node, verbatim, nothing inserted. The one rule the
        whole tool rests on — a base model must never see a frame we imagined."""
        out, n = [], self.d["nodes"][nid]
        while n:
            out.insert(0, n["text"])
            n = self.d["nodes"][n["parent"]] if n["parent"] else None
        return "".join(out)

    def human(self, typed: str) -> dict:
        """prefix + typed + suffix, and the prefix carries the newline and the name
        because llama ate the stop string off the end of the model's line."""
        n = self.add("human", self.d["turn"]["prefix"] + typed + self.d["turn"]["suffix"],
                     self.d["current"])
        self.d["current"] = n["id"]
        return n

    def edit(self, nid: str, text: str) -> None:
        n = self.d["nodes"][nid]
        n["text"] = text
        if n["kind"] == "model":
            n["posed"] = True     # forever; root and human lines are his own words

    def kids(self, nid: str) -> list:
        return [n for n in self.d["nodes"].values() if n["parent"] == nid and not n["pruned"]]

    def save(self):
        return call("/api/sitting", self.d)

    def fan(self, n: int) -> list:
        out = []
        for _ in range(n):
            st, d = call("/api/complete", {"prompt": self.prompt_from(self.d["current"]),
                                           "params": self.d["params"]})
            assert st == 200, d
            out.append(self.add("model", d["text"], self.d["current"], {
                "stop_type": d["stop_type"], "stopping_word": d["stopping_word"],
                "tokens_predicted": d["tokens_predicted"], "tps": d["tps"],
                "params": json.loads(json.dumps(self.d["params"])),
            }))
        return out


def fresh(prefix: str) -> Tree:
    t = Tree(f"{prefix}-{uuid.uuid4().hex[:6]}")
    st, d = t.save()
    assert st == 200 and d.get("ok"), d
    return t


class Plumbing(unittest.TestCase):
    def test_page(self):
        st, body = call("/")
        self.assertEqual(st, 200)
        self.assertIn("<title>loom</title>", body)

    def test_health(self):
        st, d = call("/api/health")
        self.assertEqual(st, 200)
        self.assertTrue(d["ok"])
        self.assertEqual(d["llama"]["status"], "ok")

    def test_unknown_route(self):
        self.assertEqual(call("/api/nope")[0], 404)
        self.assertEqual(call("/api/nope", {})[0], 404)

    def test_bad_name_and_traversal(self):
        for bad in ["", "../loom", "a/b", "x" * 65]:
            self.assertEqual(call("/api/sitting?name=" + bad)[0], 400, bad)
        self.assertEqual(call("/api/sitting?name=nobody-home")[0], 404)
        st, d = call("/api/sitting", {"name": "../escape", "nodes": {}, "root": "a", "current": "a"})
        self.assertEqual(st, 400)
        self.assertEqual(d["error"], "bad name")

    def test_bad_shape(self):
        t = Tree("shape-check")
        t.d["current"] = "ghost"
        st, d = call("/api/sitting", t.d)
        self.assertEqual(st, 400)
        self.assertIn("current", d["error"])

    def test_complete(self):
        t = fresh("complete")
        st, d = call("/api/complete", {"prompt": t.prompt_from(t.d["current"]),
                                       "params": t.d["params"]})
        self.assertEqual(st, 200)
        self.assertTrue(d["text"])
        # The stub cuts at the first stop string and reports it, exactly as llama does —
        # so the text must NOT still contain it.
        self.assertEqual(d["stop_type"], "word")
        self.assertEqual(d["stopping_word"], "\nbekh:")
        self.assertNotIn("\nbekh:", d["text"])
        self.assertGreater(d["tokens_predicted"], 0)
        self.assertGreater(d["tps"], 0)

    def test_complete_needs_a_prompt(self):
        st, d = call("/api/complete", {"params": PARAMS})
        self.assertEqual(st, 400)
        self.assertEqual(d["error"], "no prompt")


class Sittings(unittest.TestCase):
    def test_round_trip(self):
        t = fresh("round")
        t.human("you up")
        t.fan(1)
        st, d = t.save()
        self.assertEqual(st, 200)
        st, back = call("/api/sitting?name=" + t.d["name"])
        self.assertEqual(st, 200)
        self.assertEqual(back["nodes"], t.d["nodes"])
        self.assertEqual(back["current"], t.d["current"])
        self.assertEqual(back["turn"], TURN)
        self.assertEqual(back["params"]["dry_penalty_last_n"], 8192)

    def test_shelf_newest_first(self):
        a, b = fresh("shelf-a"), fresh("shelf-b")
        time.sleep(0.02)
        b.human("later")
        b.save()
        names = [s["name"] for s in call("/api/sittings")[1]["sittings"]]
        self.assertIn(a.d["name"], names)
        self.assertLess(names.index(b.d["name"]), names.index(a.d["name"]))
        card = next(s for s in call("/api/sittings")[1]["sittings"] if s["name"] == b.d["name"])
        self.assertEqual(card["nodes"], len(b.d["nodes"]))
        self.assertGreater(card["updated"], 0)

    def test_delete_moves_to_trash(self):
        t = fresh("oops")
        name = t.d["name"]
        st, d = call("/api/delete", {"name": name})
        self.assertEqual(st, 200, d)
        self.assertNotIn(name, [s["name"] for s in call("/api/sittings")[1]["sittings"]])
        self.assertEqual(call("/api/sitting?name=" + name)[0], 404)
        # moved, not unlinked: the tree is still on disk in .trash
        kept = [f for f in os.listdir(os.path.join(SHELF, ".trash")) if f.startswith(name + ".")]
        self.assertEqual(len(kept), 1)
        self.assertEqual(call("/api/delete", {"name": name})[0], 404)
        self.assertEqual(call("/api/delete", {"name": "../loom"})[0], 400)

    def test_human_line_is_the_document(self):
        t = fresh("human")
        n = t.human("so what is it like in there")
        self.assertEqual(n["text"], "\nbekh: so what is it like in there\nseat:")
        self.assertEqual(t.prompt_from(n["id"]),
                         HEADER + "\nbekh: so what is it like in there\nseat:")
        self.assertEqual(t.save()[0], 200)


class Branching(unittest.TestCase):
    def test_fan_pick_prune(self):
        t = fresh("branch")
        t.human("you up")
        branches = t.fan(6)
        self.assertEqual(len(t.kids(t.d["current"])), 6)
        # A fan of identical branches is not a fan. The stub varies on purpose.
        self.assertGreater(len({b["text"] for b in branches}), 1)
        for b in branches:
            self.assertEqual(b["meta"]["params"]["temperature"], 1.0)

        keep, drop = branches[0], branches[1]
        t.d["current"] = keep["id"]             # pick
        t.d["nodes"][drop["id"]]["pruned"] = True   # prune: hidden, never deleted
        self.assertEqual(t.save()[0], 200)

        st, back = call("/api/sitting?name=" + t.d["name"])
        self.assertEqual(st, 200)
        self.assertEqual(back["current"], keep["id"])
        self.assertTrue(back["nodes"][drop["id"]]["pruned"])
        self.assertIn(drop["id"], back["nodes"])    # pruned is not gone
        self.assertEqual(len(t.kids(keep["parent"])), 5)

        # Picking one makes its own children the next fan — empty until he fans again.
        self.assertEqual(t.kids(keep["id"]), [])
        t.fan(2)
        self.assertEqual(len(t.kids(keep["id"])), 2)
        # And the prompt for the deeper branch is the whole path, verbatim.
        self.assertTrue(t.prompt_from(keep["id"]).startswith(HEADER + "\nbekh: you up\nseat:"))

    def test_edit_marks_posed(self):
        t = fresh("posed")
        t.human("say something")
        model = t.fan(1)[0]
        self.assertFalse(model["posed"])
        t.edit(model["id"], " nah")
        self.assertTrue(model["posed"])
        # His own words never get the tag — root and human lines are his.
        t.edit(t.d["root"], HEADER + "\n")
        t.edit([n for n in t.d["nodes"].values() if n["kind"] == "human"][0]["id"],
               "\nbekh: say anything\nseat:")
        self.assertFalse(t.d["nodes"][t.d["root"]]["posed"])
        self.assertFalse([n for n in t.d["nodes"].values() if n["kind"] == "human"][0]["posed"])
        self.assertEqual(t.save()[0], 200)
        back = call("/api/sitting?name=" + t.d["name"])[1]
        self.assertTrue(back["nodes"][model["id"]]["posed"])   # forever, across a reload


class Cancel(unittest.TestCase):
    def test_cancel_with_nothing_running(self):
        st, d = call("/api/cancel", {})
        self.assertEqual(st, 200)
        self.assertTrue(d["ok"])
        self.assertEqual(d["cut"], 0)

    def test_cancel_a_call_in_flight(self):
        t = fresh("cancel")
        out = {}

        def go():
            # SLOW is the stub's own knob: three seconds, so the hang-up below is not a race.
            out["r"] = call("/api/complete",
                            {"prompt": t.prompt_from(t.d["current"]) + "\nSLOW",
                             "params": t.d["params"]})

        th = threading.Thread(target=go)
        th.start()
        time.sleep(0.6)
        st, d = call("/api/cancel", {})
        self.assertEqual(st, 200)
        self.assertEqual(d["cut"], 1)
        th.join(timeout=10)
        status, body = out["r"]
        self.assertEqual(status, 502)
        # "cancelled" and not "llama unreachable": the killed flag is what tells a decision
        # apart from a crash, and the page draws no red line for a decision.
        self.assertEqual(body["error"], "cancelled")


if __name__ == "__main__":
    unittest.main()
