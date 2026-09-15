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
import urllib.parse
import urllib.request
import uuid

TESTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS)
sys.path.insert(0, TESTS)
sys.path.insert(0, ROOT)
import stub_llama  # noqa: E402

# Before importing loom, and it has to be: loom reads LOOM_SITTINGS and LOOM_STORAGE once,
# at import. The server under test is a subprocess with the same env; this import is for
# the pieces the PAGE is a twin of — the spread formula — so `Tree` below can fan the way
# loom.html fans instead of guessing at it.
SHELF = tempfile.mkdtemp(prefix="loom-test-")
STORE = tempfile.mkdtemp(prefix="loom-store-")     # never the real, git-tracked storage/
os.environ["LOOM_SITTINGS"] = SHELF
os.environ["LOOM_STORAGE"] = STORE
import loom  # noqa: E402 — path first; this file may be started from anywhere

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
    "dry_penalty_last_n": 8192, "n_probs": 5, "logit_bias": [],
    "fan": 4, "spread": 0, "dry_keep": 0.8,
}

STUB = None
LOOM = None
BASE = ""
STUB_BASE = ""


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


def seen() -> list[dict]:
    """Every body the stub llama was actually sent, in order. The only place the wire can
    be read: a saved node only proves the page copied its own number into meta."""
    with urllib.request.urlopen(STUB_BASE + "/seen", timeout=10) as r:
        return json.load(r)["seen"]


def setUpModule() -> None:
    global STUB, LOOM, BASE, STUB_BASE
    STUB = stub_llama.serve(0)
    threading.Thread(target=STUB.serve_forever, daemon=True).start()
    STUB_BASE = f"http://127.0.0.1:{STUB.server_address[1]}"
    port = free_port()
    BASE = f"http://127.0.0.1:{port}"
    env = dict(os.environ,
               LOOM_HOST="127.0.0.1", LOOM_PORT=str(port), LOOM_SITTINGS=SHELF,
               LOOM_STORAGE=STORE,
               LOOM_LLAMA=STUB_BASE)
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
    if STORE:
        shutil.rmtree(STORE, ignore_errors=True)


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
        """The page's runFan: one request per branch, one temperature per branch, and the
        params that made a branch frozen into its own meta."""
        out = []
        p = self.d["params"]
        for temp in loom.spread_temps(p.get("temperature", 1.0), p.get("spread", 0), n):
            branch = dict(json.loads(json.dumps(p)), temperature=temp)
            st, d = call("/api/complete", {"prompt": self.prompt_from(self.d["current"]),
                                           "params": branch})
            assert st == 200, d
            out.append(self.add("model", d["text"], self.d["current"], {
                "stop_type": d["stop_type"], "stopping_word": d["stopping_word"],
                "tokens_predicted": d["tokens_predicted"], "tps": d["tps"],
                "probs": d.get("probs"),
                "params": branch,
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


def note_get(name: str):
    return call("/api/note?name=" + urllib.parse.quote(name))


class Notes(unittest.TestCase):
    def test_add_read_list_and_the_file_is_only_the_text(self):
        name = f"a finding — {uuid.uuid4().hex[:6]}"
        text = "line one\r\n  indented, with Capitals\n\nno trailing newline"
        st, d = call("/api/note", {"name": name, "text": text, "create": True})
        self.assertEqual((st, d.get("name")), (200, name), d)
        st, back = note_get(name)
        self.assertEqual((st, back["text"]), (200, text))
        with open(os.path.join(STORE, name + ".txt"), "rb") as f:
            self.assertEqual(f.read(), text.encode("utf-8"))     # no metadata, no newline added
        self.assertIn(name, [n["name"] for n in call("/api/notes")[1]["notes"]])

    def test_blank_name_gets_random_hex(self):
        for blank in ("", "   ", None):
            st, d = call("/api/note", {"name": blank, "text": "x", "create": True})
            self.assertEqual(st, 200, d)
            self.assertRegex(d["name"], r"^[0-9a-f]{8}$")
            self.assertEqual(note_get(d["name"])[1]["text"], "x")

    def test_taken_name_is_refused_and_untouched(self):
        name = f"taken-{uuid.uuid4().hex[:6]}"
        call("/api/note", {"name": name, "text": "first", "create": True})
        st, d = call("/api/note", {"name": name, "text": "second", "create": True})
        self.assertEqual(st, 409, d)
        self.assertEqual(note_get(name)[1]["text"], "first")

    def test_edit_overwrites_and_needs_an_existing_note(self):
        name = f"edit-{uuid.uuid4().hex[:6]}"
        call("/api/note", {"name": name, "text": "first", "create": True})
        st, d = call("/api/note", {"name": name, "text": "first\nand more later", "create": False})
        self.assertEqual(st, 200, d)
        self.assertEqual(note_get(name)[1]["text"], "first\nand more later")
        self.assertEqual(call("/api/note", {"name": "nobody-" + name, "text": "x"})[0], 404)

    def test_newest_first(self):
        a, b = f"old-{uuid.uuid4().hex[:6]}", f"new-{uuid.uuid4().hex[:6]}"
        call("/api/note", {"name": a, "text": "a", "create": True})
        time.sleep(0.02)
        call("/api/note", {"name": b, "text": "b", "create": True})
        names = [n["name"] for n in call("/api/notes")[1]["notes"]]
        self.assertLess(names.index(b), names.index(a))

    def test_bad_names_never_leave_storage(self):
        for bad in ("../escape", "a/b", "a\\b", ".hidden", " edge", "x" * 121, "tab\there", 42):
            st, _ = call("/api/note", {"name": bad, "text": "x", "create": True})
            self.assertEqual(st, 400, bad)
        for bad in ("../loom", ".hidden", ""):
            self.assertEqual(note_get(bad)[0], 400, bad)
        self.assertEqual(note_get("nobody-home")[0], 404)
        self.assertEqual(call("/api/note", {"name": "no-text", "create": True})[0], 400)


class Sittings(unittest.TestCase):
    def test_title_renames_without_changing_file_or_tree(self):
        t = fresh("title")
        t.human("a saved line")
        t.save()
        name = t.d["name"]
        t.d["title"] = "A room / with spaces — 河"
        self.assertEqual(t.save()[0], 200)
        st, back = call("/api/sitting?name=" + name)
        self.assertEqual(st, 200)
        self.assertEqual(back["name"], name)
        self.assertEqual(back["title"], t.d["title"])
        self.assertEqual(back["nodes"], t.d["nodes"])
        self.assertEqual(back["current"], t.d["current"])
        row = next(s for s in call("/api/sittings")[1]["sittings"] if s["name"] == name)
        self.assertEqual(row["title"], t.d["title"])

    def test_bad_title_leaves_saved_room_unchanged(self):
        t = fresh("bad-title")
        for title in ("", "  ", "x" * 121, 42, []):
            t.d["title"] = title
            self.assertEqual(t.save()[0], 400)
        back = call("/api/sitting?name=" + t.d["name"])[1]
        self.assertNotIn("title", back)

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

    def test_clear_keeps_the_room(self):
        t = fresh("again")
        name = t.d["name"]
        t.d["params"]["temperature"] = 1.3      # a room setting that must survive
        t.human("first run")
        t.fan(2)
        t.save()
        full = len(t.d["nodes"])
        st, d = call("/api/clear", {"name": name})
        self.assertEqual(st, 200, d)
        # the old run is copied to .trash, whole
        kept = [f for f in os.listdir(os.path.join(SHELF, ".trash")) if f.startswith(name + ".")]
        self.assertEqual(len(kept), 1)
        with open(os.path.join(SHELF, ".trash", kept[0]), encoding="utf-8") as f:
            self.assertEqual(len(json.load(f)["nodes"]), full)
        # the page's half, twinned: root only, current on it, everything else untouched
        root = t.d["nodes"][t.d["root"]]
        t.d["nodes"] = {root["id"]: root}
        t.d["current"] = root["id"]
        st, d = t.save()
        self.assertEqual(st, 200, d)
        back = call("/api/sitting?name=" + name)[1]
        self.assertEqual(list(back["nodes"]), [root["id"]])
        self.assertEqual(back["nodes"][root["id"]]["text"], HEADER)
        self.assertEqual(back["params"]["temperature"], 1.3)
        self.assertEqual(back["turn"], TURN)
        self.assertIn(name, [s["name"] for s in call("/api/sittings")[1]["sittings"]])
        self.assertEqual(call("/api/clear", {"name": "nobody-home"})[0], 404)

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


class Spread(unittest.TestCase):
    """A fan is four draws at one temperature only when spread is 0."""

    def test_the_stepping(self):
        self.assertEqual(loom.spread_temps(1.0, 0.5, 4), [0.5, 0.8333, 1.1667, 1.5])
        self.assertEqual(loom.spread_temps(1.0, 0.5, 2), [0.5, 1.5])

    def test_off_by_default_and_floored_when_on(self):
        self.assertEqual(loom.spread_temps(1.0, 0, 4), [1.0] * 4)
        self.assertEqual(loom.spread_temps(1.0, 0.5, 1), [1.0])
        # greedy is a setting he is allowed to ask for; the floor is only for the arithmetic
        self.assertEqual(loom.spread_temps(0.0, 0, 2), [0.0, 0.0])
        self.assertEqual(loom.spread_temps(0.3, 2.0, 3)[0], 0.05)

    def test_a_fan_goes_out_at_four_temperatures(self):
        t = fresh("spread")
        t.d["params"]["spread"] = 0.5
        t.human("SPREADMARK")
        t.fan(4)
        bodies = [b for b in seen() if "SPREADMARK" in (b.get("prompt") or "")]
        self.assertEqual([b["temperature"] for b in bodies], [0.5, 0.8333, 1.1667, 1.5])
        # the loom's own keys never reach llama, which answers 400 to a field it doesn't know
        for b in bodies:
            for k in ("fan", "spread", "dry_keep"):
                self.assertNotIn(k, b)
        self.assertEqual(
            [n["meta"]["params"]["temperature"] for n in t.kids(t.d["current"])],
            [0.5, 0.8333, 1.1667, 1.5])
        self.assertEqual(t.save()[0], 200)


class Probabilities(unittest.TestCase):
    def test_kept_whole_and_stripped_of_bytes(self):
        t = fresh("probs")
        t.human("PROBMARK")
        node = t.fan(1)[0]
        probs = node["meta"]["probs"]
        self.assertTrue(probs)
        # The one property the page's painting rests on: the tokens rebuild the line.
        self.assertEqual("".join(p["token"] for p in probs), node["text"])
        for p in probs:
            self.assertNotIn("bytes", p)                    # `token` again, as integers
            self.assertEqual(len(p["top_logprobs"]), 5)     # n_probs
            self.assertNotIn("bytes", p["top_logprobs"][0])
            self.assertLessEqual(p["logprob"], 0)
            self.assertEqual(p["top_logprobs"][0]["token"], p["token"])
        self.assertEqual(
            [b for b in seen() if "PROBMARK" in (b.get("prompt") or "")][0]["n_probs"], 5)
        self.assertEqual(t.save()[0], 200)
        back = call("/api/sitting?name=" + t.d["name"])[1]
        self.assertEqual(back["nodes"][node["id"]]["meta"]["probs"], probs)

    def test_zero_is_off(self):
        t = fresh("noprobs")
        t.d["params"]["n_probs"] = 0
        t.human("NOPROBMARK")
        self.assertIsNone(t.fan(1)[0]["meta"]["probs"])


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
