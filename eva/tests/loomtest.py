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
import math
import os
import shutil
import socket
import struct
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
EVA = os.path.dirname(TESTS)                      # eva/: server/ has loom
for d in (TESTS, os.path.join(EVA, "server")):
    sys.path.insert(0, d)
import stub_llama  # noqa: E402

# Before importing loom, and it has to be: loom reads LOOM_SITTINGS and LOOM_STORAGE once,
# at import. The server under test is a subprocess with the same env; this import is for
# the pieces the PAGE is a twin of — the spread formula — so `Tree` below can fan the way
# loom.html fans instead of guessing at it.
SHELF = tempfile.mkdtemp(prefix="loom-test-")
STORE = tempfile.mkdtemp(prefix="loom-store-")     # never the real, git-tracked storage/
ARTS = tempfile.mkdtemp(prefix="loom-arts-")       # nor artifacts/, which gets pushed
BERSERK = tempfile.mkdtemp(prefix="loom-berserk-")  # nor the daemon's real ledger
LEDGER = os.path.join(BERSERK, "ledger.jsonl")
os.environ["LOOM_SITTINGS"] = SHELF
os.environ["LOOM_STORAGE"] = STORE
os.environ["LOOM_ARTIFACTS"] = ARTS
os.environ["LOOM_LEDGER"] = LEDGER
import loom  # noqa: E402 — path first; this file may be started from anywhere

# loom.html's own defaults, restated. Kept as literals rather than parsed out of the page
# on purpose: if somebody changes the header line or the turn strings in the page, this
# file should have to be changed too, by a human who reads why.
HEADER = "a chat log between two friends, saved from a phone. no punctuation fixed, no capitals.\n"
TURN = {"prefix": "\nbekh: ", "suffix": "\nseat:"}
PARAMS = {
    "n_predict": 220, "stop": ["\nbekh:", "\nbekh :", "\n\nbekh"],
    "temperature": 2.5, "min_p": 0.08, "top_k": 0, "top_p": 1.0,
    "top_n_sigma": -1, "xtc_probability": 0, "xtc_threshold": 0.1,
    "repeat_penalty": 1.05, "repeat_last_n": 512,
    "dry_multiplier": 0.8, "dry_base": 1.75, "dry_allowed_length": 3,
    "dry_penalty_last_n": 8192, "ignore_eos": False,
    "n_probs": 5, "logit_bias": [], "logit_bias_text": "",
    "fan": 4, "spread": 1.0, "dry_keep": 0.8,
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
               LOOM_STORAGE=STORE, LOOM_ARTIFACTS=ARTS, LOOM_LEDGER=LEDGER,
               LOOM_LLAMA=STUB_BASE)
    LOOM = subprocess.Popen([sys.executable, os.path.join(EVA, "server", "loom.py")],
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
    if ARTS:
        shutil.rmtree(ARTS, ignore_errors=True)
    if BERSERK:
        shutil.rmtree(BERSERK, ignore_errors=True)


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

    def fork_at(self, n: dict, i: int, k: int) -> dict:
        """The page's forkAt: a sibling whose text is the line up to token i plus the k-th
        alternative there, then one completion to fill it out from that point."""
        probs = n["meta"]["probs"]
        alt = probs[i]["top_logprobs"][k]
        head = "".join(p["token"] for p in probs[:i]) + alt["token"]
        params = json.loads(json.dumps(n["meta"]["params"]))
        head_probs = probs[:i] + [{"id": alt["id"], "token": alt["token"],
                                   "logprob": alt["logprob"],
                                   "top_logprobs": probs[i]["top_logprobs"]}]
        fork = self.add("model", head, n["parent"], {
            "params": params, "probs": head_probs,
            "fork": {"at_token": i, "chosen": alt["token"], "from_node": n["id"]}})
        self.d["current"] = fork["id"]
        st, d = call("/api/complete", {"prompt": self.prompt_from(fork["id"]),
                                       "params": params})
        assert st == 200, d
        fork["text"] += d["text"]
        fork["meta"]["probs"] = head_probs + (d.get("probs") or [])
        fork["meta"]["stop_type"] = d["stop_type"]
        return fork

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
        # A name is a path now, so `a/b` is a room in a folder and reads as missing, not as
        # illegal. Everything that could climb out of the sittings dir, name the bin, or
        # leave an empty segment behind is still a refusal before anything touches the disk.
        for bad in ["", "../loom", "/loom", "loom/", "a//b", "a/../b", "a/./b",
                    ".trash/x", "x/.hidden", "x" * 65, "a/" + "x" * 65]:
            self.assertEqual(call("/api/sitting?name=" + urllib.parse.quote(bad))[0], 400, bad)
        self.assertEqual(call("/api/sitting?name=a/b")[0], 404)
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
        self.assertEqual(call("/api/complete", {"prompt": 3, "params": PARAMS})[0], 400)

    def test_an_empty_prompt_is_a_prompt(self):
        # A bare room with an empty root has nothing else to send, and llama takes it:
        # BOS goes in and the model starts the document itself.
        st, d = call("/api/complete", {"prompt": "", "params": PARAMS})
        self.assertEqual(st, 200, d)
        self.assertTrue(d["text"])


def raw(path: str):
    """(status, headers, bytes) — for the routes whose body is not text. `call` decodes
    utf-8 and a PNG is not utf-8."""
    try:
        with urllib.request.urlopen(BASE + path, timeout=10) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


class HomeScreen(unittest.TestCase):
    """The manifest and the icons: what turns the page into an app on bekh's phone. Held
    here because the tags in loom.html are read by iOS exactly once, when the icon is
    added, and a manifest that 404s that one time fails silently and forever."""

    def test_manifest(self):
        st, hdr, body = raw("/manifest.webmanifest")
        self.assertEqual(st, 200)
        self.assertIn("application/manifest+json", hdr.get("Content-Type", ""))
        d = json.loads(body)
        self.assertEqual(d["display"], "standalone")      # the whole reason it exists
        self.assertEqual((d["start_url"], d["scope"]), ("/", "/"))
        self.assertEqual(d["short_name"], "eva")
        self.assertEqual(d["background_color"], "#232323")
        self.assertEqual({i["sizes"] for i in d["icons"]}, {"180x180", "192x192", "512x512"})
        # the manifest itself must not be cached: a re-add has to see today's copy
        self.assertEqual(hdr.get("Cache-Control"), "no-store")

    def test_icons(self):
        for n in (180, 192, 512):
            st, hdr, body = raw(f"/icon-{n}.png")
            self.assertEqual(st, 200, n)
            self.assertEqual(hdr.get("Content-Type"), "image/png")
            self.assertTrue(body.startswith(b"\x89PNG\r\n\x1a\n"), n)
            # the size is in the IHDR, bytes 16..24 — proof the file is the icon it claims
            self.assertEqual(struct.unpack(">II", body[16:24]), (n, n))
            self.assertIn("max-age", hdr.get("Cache-Control", ""))

    def test_a_size_we_do_not_have(self):
        self.assertEqual(raw("/icon-181.png")[0], 404)
        self.assertEqual(raw("/icon-.png")[0], 404)
        self.assertEqual(raw("/icon-../../server/loom.png")[0], 404)

    def test_the_page_asks_for_them(self):
        body = call("/")[1]
        for tag in ('name="apple-mobile-web-app-capable" content="yes"',
                    'content="black-translucent"',
                    'rel="manifest" href="/manifest.webmanifest"',
                    'rel="apple-touch-icon" href="/icon-180.png"',
                    "viewport-fit=cover"):
            self.assertIn(tag, body, tag)


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


class Folders(unittest.TestCase):
    """A room's name is its path under the sittings dir, and that is the whole feature: the
    shelf is a tree because the names are, `/api/move` renames a file or a folder, and
    nothing on disk says a folder exists apart from the rooms in it."""

    def names(self) -> list[str]:
        return [s["name"] for s in call("/api/sittings")[1]["sittings"]]

    def test_a_path_is_a_name_and_the_folders_are_made_on_the_way(self):
        here = "folders-" + uuid.uuid4().hex[:6]
        t = Tree(f"{here}/basin/smoke-01")
        st, d = t.save()
        self.assertEqual(st, 200, d)
        self.assertTrue(os.path.isfile(os.path.join(SHELF, here, "basin", "smoke-01.json")))
        self.assertIn(f"{here}/basin/smoke-01", self.names())
        # and it reads back by the same path, whole
        st, back = call(f"/api/sitting?name={here}/basin/smoke-01")
        self.assertEqual(st, 200, back)
        self.assertEqual(back["nodes"].keys(), t.d["nodes"].keys())

    def test_the_listing_walks_the_tree_and_never_the_bin(self):
        here = "listing-" + uuid.uuid4().hex[:6]
        for name in (f"{here}/top", f"{here}/one/deep", f"{here}/one/two/deeper"):
            st, d = Tree(name).save()
            self.assertEqual(st, 200, d)
        names = self.names()
        for name in (f"{here}/top", f"{here}/one/deep", f"{here}/one/two/deeper"):
            self.assertIn(name, names)
        # deleted from a folder: into .trash under the same folders, and off the shelf
        st, d = call("/api/delete", {"name": f"{here}/one/two/deeper"})
        self.assertEqual(st, 200, d)
        bin_ = os.path.join(SHELF, ".trash", here, "one", "two")
        self.assertEqual(len(os.listdir(bin_)), 1)
        self.assertNotIn(f"{here}/one/two/deeper", self.names())
        # nothing under a dot folder is ever listed, however deep it is
        self.assertFalse([n for n in self.names() if n.startswith(".")])
        # and the folder it emptied is gone, while the one still holding a room stays
        self.assertFalse(os.path.isdir(os.path.join(SHELF, here, "one", "two")))
        self.assertTrue(os.path.isdir(os.path.join(SHELF, here, "one")))

    def test_every_rule_a_name_has(self):
        for ok in ("a", "a/b", "a/b/c", "a.b-c_d", "x" * 64, "a/" + "x" * 64):
            self.assertTrue(loom.name_ok(ok), ok)
        for bad in ("", "/a", "a/", "a//b", ".", "..", "a/..", "../a", ".trash",
                    ".trash/a", "a/.hidden", "a\\b", "a b", "a/b c", "x" * 65,
                    "a/" + "x" * 65, "a/" * 300, None, 42, "a\nb", "a\x00b"):
            self.assertFalse(loom.name_ok(bad), bad)
        # and the one gate: a name that doesn't read never becomes a path
        with self.assertRaises(ValueError):
            loom.sitting_path("../escape")

    def test_move_a_room_and_the_name_inside_it_goes_too(self):
        here = "mv-" + uuid.uuid4().hex[:6]
        t = fresh(f"{here}-room")
        was = t.d["name"]
        stamped = call("/api/sitting?name=" + was)[1]["updated"]
        to = f"{here}/kept/{was}"
        st, d = call("/api/move", {"from": was, "to": to})
        self.assertEqual(st, 200, d)
        self.assertEqual(d["moved"], 1)
        self.assertEqual(call("/api/sitting?name=" + was)[0], 404)
        st, back = call("/api/sitting?name=" + to)
        self.assertEqual(st, 200, back)
        # the file carries its own name and every writer posts the whole object back: a
        # stale name inside would put the room back where it came from on the next save
        self.assertEqual(back["name"], to)
        self.assertEqual(back["updated"], stamped, "a move is not a new version")
        st, d = call("/api/sitting", back)
        self.assertEqual(st, 200, d)
        self.assertIn(to, self.names())

    def test_rename_is_a_move(self):
        here = "rn-" + uuid.uuid4().hex[:6]
        t = fresh(here)
        st, d = call("/api/move", {"from": t.d["name"], "to": t.d["name"] + "-again"})
        self.assertEqual(st, 200, d)
        self.assertIn(t.d["name"] + "-again", self.names())
        self.assertNotIn(t.d["name"], self.names())

    def test_move_a_whole_folder(self):
        here = "fold-" + uuid.uuid4().hex[:6]
        for name in (f"{here}/basin/a", f"{here}/basin/b", f"{here}/basin/deep/c"):
            self.assertEqual(Tree(name).save()[0], 200)
        st, d = call("/api/move", {"from": f"{here}/basin", "to": f"{here}/filed/basin"})
        self.assertEqual(st, 200, d)
        self.assertEqual(d["moved"], 3)
        names = self.names()
        for name in ("a", "b", "deep/c"):
            self.assertIn(f"{here}/filed/basin/{name}", names)
            self.assertNotIn(f"{here}/basin/{name}", names)
        # every room under it says where it lives now
        st, back = call(f"/api/sitting?name={here}/filed/basin/deep/c")
        self.assertEqual(back["name"], f"{here}/filed/basin/deep/c")
        self.assertFalse(os.path.isdir(os.path.join(SHELF, here, "basin")))

    def test_the_refusals(self):
        here = "no-" + uuid.uuid4().hex[:6]
        a, b = fresh(f"{here}-a"), fresh(f"{here}-b")
        self.assertEqual(Tree(f"{here}/deep/one").save()[0], 200)
        # a name that doesn't read, either end of it
        for bad in ("", "../escape", ".trash/x", "a//b", None, 42):
            self.assertEqual(call("/api/move", {"from": a.d["name"], "to": bad})[0], 400, bad)
            self.assertEqual(call("/api/move", {"from": bad, "to": a.d["name"]})[0], 400, bad)
        # nothing there
        self.assertEqual(call("/api/move", {"from": "ghost-" + uuid.uuid4().hex[:6],
                                            "to": f"{here}/x"})[0], 404)
        # a room already at the target, or a folder wearing that name
        self.assertEqual(call("/api/move", {"from": a.d["name"], "to": b.d["name"]})[0], 409)
        self.assertEqual(call("/api/move", {"from": a.d["name"], "to": here})[0], 409)
        # a folder into itself, and the same folder onto itself
        self.assertEqual(call("/api/move", {"from": here, "to": f"{here}/deep/{here}"})[0], 400)
        self.assertEqual(call("/api/move", {"from": here, "to": here})[0], 400)
        # not one refusal moved anything
        names = self.names()
        self.assertIn(a.d["name"], names)
        self.assertIn(b.d["name"], names)
        self.assertIn(f"{here}/deep/one", names)

    def test_an_emptied_folder_goes_and_the_shelf_itself_never_does(self):
        here = "prune-" + uuid.uuid4().hex[:6]
        self.assertEqual(Tree(f"{here}/one/two/only").save()[0], 200)
        top = fresh(f"{here}-top")
        st, d = call("/api/move", {"from": f"{here}/one/two/only", "to": f"{here}/one/only"})
        self.assertEqual(st, 200, d)
        self.assertFalse(os.path.isdir(os.path.join(SHELF, here, "one", "two")))
        self.assertTrue(os.path.isdir(os.path.join(SHELF, here, "one")))
        # the last room out of the whole tree takes every folder with it, and stops there
        st, d = call("/api/move", {"from": f"{here}/one/only", "to": f"{here}-loose"})
        self.assertEqual(st, 200, d)
        self.assertFalse(os.path.isdir(os.path.join(SHELF, here)))
        self.assertTrue(os.path.isdir(SHELF))
        self.assertIn(top.d["name"], self.names())

    def test_a_walked_room_answers_to_its_bare_name_after_it_moves(self):
        # The ledger names a room the way berserk made it and knows nothing about folders,
        # and every `#tree=` link the sheets pages ever printed spells it that way too.
        t, _, _ = walked_room("brz-filed")
        bare = t.d["name"]
        st, d = call("/api/move", {"from": bare, "to": f"nights/{bare}"})
        self.assertEqual(st, 200, d)
        st, d = call("/api/berserk?name=" + bare)
        self.assertEqual(st, 200, d)
        self.assertEqual([r["fork"] for r in d["rows"]], [1, 2])
        self.assertEqual(d["text"], ROOT_TEXT + TOOK_TEXT)
        # by its path as well, and the text route resolves the same way
        self.assertEqual(call(f"/api/berserk?name=nights/{bare}")[0], 200)
        self.assertEqual(call("/api/berserk/text?name=" + bare)[1], ROOT_TEXT + TOOK_TEXT)
        # and the shelf still says a walk hangs off it, wherever it is filed
        row = next(s for s in call("/api/sittings")[1]["sittings"]
                   if s["name"] == f"nights/{bare}")
        self.assertIs(row["berserk"], True)

    def test_two_rooms_with_one_leaf_is_a_question_not_a_pick(self):
        leaf = "twin-" + uuid.uuid4().hex[:6]
        for folder in ("one", "two"):
            self.assertEqual(Tree(f"ambig/{folder}/{leaf}").save()[0], 200)
        self.assertIsNone(loom.resolve_room(leaf))
        st, d = call("/api/berserk?name=" + leaf)
        self.assertEqual(st, 404, d)
        self.assertEqual(d["error"], "no such sitting")


class Canvas(unittest.TestCase):
    """One folder as a picture. `/api/folder` is the only route that hands over many rooms'
    nodes at once, so it is also the only one that has to be stingy: what a picture doesn't
    paint is dropped on the server, because the cost is the wire and not the render."""

    def folder(self, name):
        return call("/api/folder?name=" + urllib.parse.quote(name))

    def test_every_room_under_it_sub_folders_and_all(self):
        here = "canv-" + uuid.uuid4().hex[:6]
        for name in (f"{here}/b-two", f"{here}/a-one", f"{here}/deep/c-three"):
            self.assertEqual(Tree(name).save()[0], 200)
        # a room whose name only STARTS like the folder is not in the folder
        self.assertEqual(Tree(here + "-elsewhere").save()[0], 200)
        st, d = self.folder(here)
        self.assertEqual(st, 200, d)
        self.assertEqual(d["folder"], here)
        self.assertEqual([r["name"] for r in d["rooms"]],
                         [f"{here}/a-one", f"{here}/b-two", f"{here}/deep/c-three"])
        # every room comes with what the canvas draws a room out of
        for r in d["rooms"]:
            self.assertEqual(set(r) & {"root", "current", "nodes", "title", "berserk"},
                             {"root", "current", "nodes", "title", "berserk"})

    def test_a_node_is_cut_to_what_the_canvas_paints(self):
        here = "canvcut-" + uuid.uuid4().hex[:6]
        t = Tree(f"{here}/one")
        root = t.d["root"]
        # the two spellings of a model in the wild, and 40 KB of probabilities that must not
        # leave the disk
        a = t.add("model", "one", root, {"params": {"temperature": 2.2},
                                         "probs": [{"id": 1, "token": "one"}],
                                         "model": {"file": "nemo-q5.gguf"}})
        b = t.add("model", "two", root, {"temperature": 1.9, "model": "pythia.gguf"})
        b["kept"] = True
        c = t.add("human", "\n\nlater.\n", a["id"])
        c["posed"] = True
        t.d["current"] = a["id"]
        self.assertEqual(t.save()[0], 200)
        st, d = self.folder(here)
        self.assertEqual(st, 200, d)
        room = d["rooms"][0]
        nodes = room["nodes"]
        self.assertEqual(nodes[a["id"]], {"parent": root, "kind": "model", "text": "one",
                                          "temperature": 2.2, "model": "nemo-q5.gguf"})
        # a bare meta.temperature is the real draw too, for a branch a script wrote
        self.assertEqual(nodes[b["id"]]["temperature"], 1.9)
        self.assertEqual(nodes[b["id"]]["model"], "pythia.gguf")
        self.assertIs(nodes[b["id"]]["kept"], True)
        self.assertIs(nodes[c["id"]]["posed"], True)
        # false and missing are the same thing here, and the payload says so by saying nothing
        self.assertNotIn("kept", nodes[a["id"]])
        self.assertNotIn("posed", nodes[a["id"]])
        self.assertNotIn("probs", json.dumps(nodes))
        # the room's own shape rides along: the page redraws the tree out of it
        self.assertEqual(room["root"], root)
        self.assertEqual(room["current"], a["id"])
        self.assertIs(room["berserk"], False)
        self.assertEqual(nodes[root]["kind"], "root")

    def test_a_walked_room_says_so(self):
        t, _, _ = walked_room("canv-brz")
        bare = t.d["name"]
        here = "canvnight-" + uuid.uuid4().hex[:6]
        st, d = call("/api/move", {"from": bare, "to": f"{here}/{bare}"})
        self.assertEqual(st, 200, d)
        st, d = self.folder(here)
        self.assertEqual(st, 200, d)
        self.assertIs(d["rooms"][0]["berserk"], True)

    def test_the_bin_is_not_a_folder_and_an_empty_one_is_a_404(self):
        here = "canvbin-" + uuid.uuid4().hex[:6]
        self.assertEqual(Tree(f"{here}/gone").save()[0], 200)
        self.assertEqual(call("/api/delete", {"name": f"{here}/gone"})[0], 200)
        # the only room in it went to .trash, so the folder is not a folder any more
        st, d = self.folder(here)
        self.assertEqual(st, 404, d)
        self.assertEqual(d["error"], "no rooms in that folder")
        # and the bin itself is unaddressable, however it is spelled
        for bad in ("", "../escape", ".trash", ".trash/" + here, "a//b", "a/"):
            st, d = self.folder(bad)
            self.assertEqual(st, 400, (bad, d))
            self.assertEqual(d["error"], "bad name")
        st, d = self.folder("ghost-" + uuid.uuid4().hex[:6])
        self.assertEqual(st, 404, d)


class Keep(unittest.TestCase):
    """The canvas's keep writes the same `kept: true` the choose screen leaves, into the room
    itself, so a harvest made on the picture is in the rooms and in git."""

    def read(self, name):
        st, d = call("/api/sitting?name=" + name)
        assert st == 200, d
        return d

    def branch(self, prefix):
        """One room in its own folder, standing on one branch — the smallest thing a keep
        can be made on, and filed, so the canvas route can be asked about it too."""
        here = f"{prefix}-{uuid.uuid4().hex[:6]}"
        t = Tree(f"{here}/room")
        b = t.add("model", "a branch", t.d["root"], {"params": {"temperature": 1.2}})
        t.d["current"] = b["id"]
        st, d = t.save()
        assert st == 200 and d.get("ok"), d
        return t, b, here

    def test_it_lands_in_the_room_and_comes_off_again(self):
        t, b, here = self.branch("keep")
        before = self.read(t.d["name"])
        st, d = call("/api/keep", {"room": t.d["name"], "node": b["id"], "kept": True})
        self.assertEqual(st, 200, d)
        after = self.read(t.d["name"])
        self.assertIs(after["nodes"][b["id"]]["kept"], True)
        # nothing else moved. `updated` does, because write_sitting stamps every write — a
        # keep is a new version of the file, and the shelf orders by it.
        self.assertGreaterEqual(after["updated"], before["updated"])
        same = json.loads(json.dumps(after))
        same["updated"] = before["updated"]
        del same["nodes"][b["id"]]["kept"]
        self.assertEqual(same, before)
        # and the canvas reads it back off the same file
        st, d = call("/api/folder?name=" + here)
        self.assertEqual(st, 200, d)
        self.assertIs(d["rooms"][0]["nodes"][b["id"]]["kept"], True)
        # off again: the key goes, it is never set false — like every room written before
        # keep existed
        st, d = call("/api/keep", {"room": t.d["name"], "node": b["id"], "kept": False})
        self.assertEqual(st, 200, d)
        self.assertNotIn("kept", self.read(t.d["name"])["nodes"][b["id"]])

    def test_the_refusals(self):
        t, b, here = self.branch("keepno")
        h = t.human("you up")
        self.assertEqual(t.save()[0], 200)
        room = t.d["name"]
        for body, code in (
            ({"room": "ghost-" + uuid.uuid4().hex[:6], "node": b["id"], "kept": True}, 404),
            ({"room": room, "node": "nosuchnode", "kept": True}, 404),
            # a root and a line of his own are not branches: keeping is a statement about
            # what the model offered
            ({"room": room, "node": t.d["root"], "kept": True}, 400),
            ({"room": room, "node": h["id"], "kept": True}, 400),
            ({"room": "../escape", "node": b["id"], "kept": True}, 400),
            ({"room": room, "node": "", "kept": True}, 400),
            ({"room": room, "node": b["id"], "kept": "yes"}, 400),
            ({"room": room, "node": b["id"]}, 400),
        ):
            st, d = call("/api/keep", body)
            self.assertEqual(st, code, (body, d))
            self.assertIn("error", d)
        # not one refusal marked anything
        self.assertNotIn("kept", self.read(room)["nodes"][b["id"]])


class Mark(unittest.TestCase):
    """The same write, addressed by mark name. `good` is the second one: "i liked reading
    this and i would not keep it" — the thing keep was being spent on while a blind fan was
    being read. The two are independent everywhere, and nothing downstream reads `good`.

    Keep's two helpers, borrowed rather than inherited: subclassing would re-run Keep's own
    tests under this name, and the alias is already tested once above."""

    read = Keep.read
    branch = Keep.branch

    def test_good_lands_and_comes_off(self):
        t, b, here = self.branch("good")
        st, d = call("/api/mark", {"room": t.d["name"], "node": b["id"],
                                   "mark": "good", "on": True})
        self.assertEqual(st, 200, d)
        self.assertEqual((d["mark"], d["on"], d["good"]), ("good", True, True))
        self.assertIs(self.read(t.d["name"])["nodes"][b["id"]]["good"], True)
        # and the canvas gets it in the folder payload, like kept
        st, d = call("/api/folder?name=" + here)
        self.assertIs(d["rooms"][0]["nodes"][b["id"]]["good"], True)
        st, d = call("/api/mark", {"room": t.d["name"], "node": b["id"],
                                   "mark": "good", "on": False})
        self.assertEqual(st, 200, d)
        self.assertNotIn("good", self.read(t.d["name"])["nodes"][b["id"]])

    def test_the_two_are_independent(self):
        t, b, here = self.branch("both")
        room, nid = t.d["name"], b["id"]
        for mark in ("kept", "good"):
            self.assertEqual(call("/api/mark", {"room": room, "node": nid,
                                                "mark": mark, "on": True})[0], 200)
        node = self.read(room)["nodes"][nid]
        self.assertEqual((node.get("kept"), node.get("good")), (True, True))
        # taking one off leaves the other exactly where it was
        self.assertEqual(call("/api/mark", {"room": room, "node": nid,
                                            "mark": "kept", "on": False})[0], 200)
        node = self.read(room)["nodes"][nid]
        self.assertNotIn("kept", node)
        self.assertIs(node["good"], True)

    def test_a_mark_we_do_not_have(self):
        t, b, here = self.branch("nomark")
        room = t.d["name"]
        for body in ({"room": room, "node": b["id"], "mark": "loved", "on": True},
                     {"room": room, "node": b["id"], "mark": "", "on": True},
                     {"room": room, "node": b["id"], "on": True},
                     {"room": room, "node": b["id"], "mark": "good", "on": "yes"},
                     {"room": room, "node": b["id"], "mark": "good"}):
            st, d = call("/api/mark", body)
            self.assertEqual(st, 400, (body, d))
        node = self.read(room)["nodes"][b["id"]]            # nothing was marked
        self.assertNotIn("good", node)
        self.assertNotIn("kept", node)

    def test_the_refusals_are_the_same_by_the_new_name(self):
        t, b, here = self.branch("markno")
        h = t.human("you up")
        self.assertEqual(t.save()[0], 200)
        room = t.d["name"]
        for body, code in (
            ({"room": "ghost-" + uuid.uuid4().hex[:6], "node": b["id"]}, 404),
            ({"room": room, "node": "nosuchnode"}, 404),
            ({"room": room, "node": t.d["root"]}, 400),
            ({"room": room, "node": h["id"]}, 400),
            ({"room": "../escape", "node": b["id"]}, 400),
            ({"room": room, "node": ""}, 400),
        ):
            st, d = call("/api/mark", dict(body, mark="good", on=True))
            self.assertEqual(st, code, (body, d))
            self.assertIn("error", d)
        self.assertNotIn("good", self.read(room)["nodes"][b["id"]])


class Branching(unittest.TestCase):
    def test_fan_pick_prune(self):
        t = fresh("branch")
        t.human("you up")
        branches = t.fan(6)
        self.assertEqual(len(t.kids(t.d["current"])), 6)
        # A fan of identical branches is not a fan. The stub varies on purpose.
        self.assertGreater(len({b["text"] for b in branches}), 1)
        # and a fan is a slice through the range, not six draws at one setting
        self.assertEqual(len({b["meta"]["params"]["temperature"] for b in branches}), 6)

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
        t.d["params"]["temperature"] = 1.0
        t.d["params"]["spread"] = 0.5
        # Not "SPREADMARK": the stub's SEEN is one list per process, and evatest's
        # "EVASPREADMARK" contains it — under `discover` the two modules share the stub module.
        t.human("LOOMSPREADMARK")
        t.fan(4)
        bodies = [b for b in seen() if "LOOMSPREADMARK" in (b.get("prompt") or "")]
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

    def test_tokenize_is_how_a_word_becomes_a_bias(self):
        """The drawer's resolver, twinned: llama's string form of logit_bias does not work
        on this build, so a word has to be resolved to ids before it is sent."""
        st, d = call("/api/tokenize", {"contents": ["the", " the", "The", " The",
                                                    "hello there", ""]})
        self.assertEqual(st, 200, d)
        ids = d["tokens"]
        self.assertEqual([len(t) for t in ids], [1, 1, 1, 1, 2, 0])
        # four spellings of one word are four different tokens — which is the whole reason
        # the resolver tries all four
        self.assertEqual(len({t[0] for t in ids[:4]}), 4)
        self.assertEqual(call("/api/tokenize", {"contents": "the"})[0], 400)
        self.assertEqual(call("/api/tokenize", {"contents": ["x"] * 65})[0], 400)

        t = fresh("resolved")
        # what the page stores after resolving: ids on the wire, the words kept beside them
        t.d["params"]["logit_bias"] = [[i[0], -2] for i in ids[:4]]
        t.d["params"]["logit_bias_text"] = "the  -2"
        t.human("RESOLVEDMARK")
        t.fan(1)
        body = [b for b in seen() if "RESOLVEDMARK" in (b.get("prompt") or "")][-1]
        self.assertEqual(body["logit_bias"], [[i[0], -2] for i in ids[:4]])
        self.assertNotIn("logit_bias_text", body)   # the words are ours, not llama's
        self.assertEqual(t.save()[0], 200)

    def test_logit_bias_goes_through_in_llamas_own_shape(self):
        t = fresh("bias")
        # strings and ids in one list, and `false` to ban — all three are llama's, checked
        # against tools/server/server-schema.cpp on master
        t.d["params"]["logit_bias"] = [[" the", -2], [1234, -100], ["\n", False]]
        t.d["params"]["dry_multiplier"] = 0        # the page's dry switch, in the file
        t.d["params"]["dry_keep"] = 0.8
        t.human("BIASMARK")
        t.fan(1)
        body = [b for b in seen() if "BIASMARK" in (b.get("prompt") or "")][-1]
        self.assertEqual(body["logit_bias"], [[" the", -2], [1234, -100], ["\n", False]])
        self.assertEqual(body["dry_multiplier"], 0)
        self.assertNotIn("dry_keep", body)         # the switch's memory is ours, not llama's
        self.assertEqual(t.save()[0], 200)

    def test_fork_at_a_token(self):
        t = fresh("fork")
        t.human("FORKMARK")
        line = t.fan(1)[0]
        at = 2
        alt = line["meta"]["probs"][at]["top_logprobs"][1]
        self.assertNotEqual(alt["token"], line["meta"]["probs"][at]["token"])
        head = "".join(p["token"] for p in line["meta"]["probs"][:at]) + alt["token"]

        fork = t.fork_at(line, at, 1)
        self.assertTrue(fork["text"].startswith(head))
        self.assertGreater(len(fork["text"]), len(head))        # it filled out from there
        # A sibling, not a child: the fork stands beside the line it came from and the
        # ‹ n/m › walk finds it like any other candidate.
        self.assertEqual(fork["parent"], line["parent"])
        self.assertEqual([n["id"] for n in t.kids(line["parent"])], [line["id"], fork["id"]])
        self.assertEqual(fork["meta"]["fork"],
                         {"at_token": at, "chosen": alt["token"], "from_node": line["id"]})
        # and the merged probabilities still rebuild the line, so it can be painted and
        # forked again
        self.assertEqual("".join(p["token"] for p in fork["meta"]["probs"]), fork["text"])
        # what llama was actually asked to continue ends in the chosen alternative
        body = [b for b in seen() if "FORKMARK" in (b.get("prompt") or "")][-1]
        self.assertTrue(body["prompt"].endswith(head))
        self.assertEqual(t.save()[0], 200)


def kept_fan(prefix: str, n: int = 6, keep=(1, 4)):
    """A room with one fan of n and the branches at positions `keep` (0-based) marked the
    way the page marks them — `kept: true` on the node — saved, so the server can read it."""
    t = fresh(prefix)
    t.human("KEEPMARK and a Capital")
    branches = t.fan(n)
    # The stub draws from six lines at random, so a fan of six nearly always holds a verbatim
    # twin — and a twin is not a choice, which would move every bits number below. Numbered,
    # every branch is its own; the twin test adds its twin on purpose.
    for i, br in enumerate(branches):
        br["text"] += f" #{i}"
    for i in keep:
        branches[i]["kept"] = True
    assert t.save()[0] == 200
    return t, branches


def walk_room(prefix: str, plan=((6, (1, 4)), (4, ()), (5, (0, 2)), (3, (1,)))):
    """A room walked several forks deep, the way the page walks one: a line typed, a fan,
    some cards kept, one of them picked, on to the next fork. `plan` is (fan size, which
    positions were kept) per fork. The line taken is always one he did NOT keep, so took and
    kept can never stand in for each other in an assertion below.

    Returns the tree and one row per fork — (fan point, branches, the line taken, the ids
    kept beside it) — in document order.
    """
    t = fresh(prefix)
    walk = []
    for i, (n, keeps) in enumerate(plan):
        t.human(f"line {i} KEEPMARK")
        head = t.d["current"]
        branches = t.fan(n)
        for j, br in enumerate(branches):
            br["text"] += f" #{i}.{j}"       # every branch its own; see kept_fan
        for j in keeps:
            branches[j]["kept"] = True
        took = next(br for j, br in enumerate(branches) if j not in keeps)
        t.d["current"] = took["id"]          # the page's pickNode
        walk.append((head, branches, took, [branches[j]["id"] for j in keeps]))
    assert t.save()[0] == 200
    return t, walk


def art_get(name: str):
    return call("/api/artifact?name=" + urllib.parse.quote(name))


def save_walk(t, walk):
    """What the page posts when he saves: the room, the fan he has open, and the ids kept in
    THAT fan. Everything earlier on the walk the server finds by itself."""
    head, _, _, keeps = walk[-1]
    st, d = call("/api/artifact", {"room": t.d["name"], "parent": head, "kept": keeps})
    assert st == 200, d
    st, a = art_get(d["name"])
    assert st == 200, a
    return a


class Artifacts(unittest.TestCase):
    def test_create_list_get(self):
        t, b = kept_fan("art")
        at = t.d["current"]
        st, d = call("/api/artifact", {"room": t.d["name"], "parent": at,
                                       "kept": [b[4]["id"], b[1]["id"]]})
        self.assertEqual(st, 200, d)
        self.assertRegex(d["name"], r"^[0-9a-f]{12}$")
        self.assertTrue(os.path.isfile(os.path.join(ARTS, d["name"] + ".json")))

        st, a = art_get(d["name"])
        self.assertEqual(st, 200, a)
        self.assertEqual(a["name"], d["name"])
        self.assertEqual(a["title"], d["title"])
        self.assertTrue(a["title"].startswith(t.d["name"] + " · "))   # untitled room: its name
        self.assertLessEqual(len(a["title"]), 120)
        self.assertEqual(a["source"], {"room": t.d["name"], "title": None, "node": at})
        self.assertEqual(a["turn"], TURN)
        self.assertEqual(a["params"], t.d["params"])
        self.assertEqual(a["model"]["file"], "stub-base-12b.Q5_K_M.gguf")
        self.assertEqual(a["model"]["n_ctx"], 8192)

        row = next(r for r in call("/api/artifacts")[1]["artifacts"] if r["name"] == d["name"])
        self.assertEqual((row["steps"], row["kept"], row["fan"], row["title"]),
                         (1, 2, 6, a["title"]))

    def test_the_prompt_is_verbatim(self):
        t, b = kept_fan("art-prompt")
        at = t.d["current"]
        d = call("/api/artifact", {"room": t.d["name"], "parent": at, "kept": [b[1]["id"]]})[1]
        a = art_get(d["name"])[1]
        # exactly what a fan from that point sent llama — header, names, the capital, all of it
        self.assertEqual(a["prompt"], t.prompt_from(at))
        sent = [s for s in seen() if "KEEPMARK" in (s.get("prompt") or "")][-1]["prompt"]
        self.assertEqual(a["prompt"], sent)

    def test_kept_and_others(self):
        t, b = kept_fan("art-split")
        d = call("/api/artifact", {"room": t.d["name"], "parent": t.d["current"],
                                   "kept": [b[4]["id"], b[1]["id"], b[1]["id"]]})[1]
        a = art_get(d["name"])[1]
        # He kept two cards and saved without picking, so the whole walk is that one open
        # fan: a step with no line taken.
        self.assertEqual(len(a["steps"]), 1)
        step = a["steps"][0]
        self.assertIsNone(step["took"])
        self.assertEqual(step["at"], t.d["current"])
        self.assertEqual(step["lead"], "")
        # in fan order whatever order they were sent in, a repeat counted once
        self.assertEqual([k["id"] for k in step["kept"]], [b[1]["id"], b[4]["id"]])
        self.assertEqual([k["at"] for k in step["kept"]], [2, 5])
        for k, src in zip(step["kept"], (b[1], b[4])):
            self.assertEqual(k["text"], src["text"])
            self.assertEqual(k["temperature"], src["meta"]["params"]["temperature"])
            self.assertEqual(k["meta"]["tokens_predicted"], src["meta"]["tokens_predicted"])
            self.assertEqual(k["meta"]["stop_type"], src["meta"]["stop_type"])
            self.assertNotIn("probs", k["meta"])
            self.assertFalse(k["posed"])
        self.assertEqual(step["fan"]["size"], 6)
        others = step["fan"]["others"]
        self.assertEqual([o["id"] for o in others], [b[i]["id"] for i in (0, 2, 3, 5)])
        self.assertEqual([o["at"] for o in others], [1, 3, 4, 6])
        for o in others:
            src = t.d["nodes"][o["id"]]
            self.assertEqual(o["opening"], src["text"][:80])
            self.assertEqual(o["length"], len(src["text"]))
            self.assertEqual(o["temperature"], src["meta"]["params"]["temperature"])

    def test_bits_are_log2_of_n_choose_k(self):
        t, b = kept_fan("art-bits")
        d = call("/api/artifact", {"room": t.d["name"], "parent": t.d["current"],
                                   "kept": [b[1]["id"], b[4]["id"]]})[1]
        self.assertEqual(art_get(d["name"])[1]["bits"], round(math.log2(math.comb(6, 2)), 3))
        # one kept is the same number curation gives a pick: log2 of the fan
        d = call("/api/artifact", {"room": t.d["name"], "parent": t.d["current"],
                                   "kept": [b[0]["id"]]})[1]
        self.assertEqual(art_get(d["name"])[1]["bits"], round(math.log2(6), 3))
        self.assertEqual(loom.bits_of_keeping(6, 6), 0.0)
        self.assertEqual(loom.bits_of_keeping(1, 1), 0.0)

    def test_a_twin_of_a_kept_branch_is_not_a_choice(self):
        t, b = kept_fan("art-twin", n=4, keep=(0,))
        # the page prunes a verbatim twin on arrival; it still counts as written, not as refused
        twin = t.add("model", b[0]["text"], t.d["current"], dict(b[0]["meta"]))
        twin["pruned"] = True
        twin["ts"] = b[-1]["ts"] + 1
        self.assertEqual(t.save()[0], 200)
        d = call("/api/artifact", {"room": t.d["name"], "parent": t.d["current"],
                                   "kept": [b[0]["id"]]})[1]
        step = art_get(d["name"])[1]["steps"][0]
        self.assertEqual(step["fan"]["size"], 5)
        self.assertEqual(step["bits"], round(math.log2(4), 3))
        self.assertTrue(step["fan"]["others"][-1]["pruned"])

    def test_refusals(self):
        t, b = kept_fan("art-no")
        room, at = t.d["name"], t.d["current"]
        before = set(os.listdir(ARTS))

        st, d = call("/api/artifact", {"room": room, "parent": at, "kept": []})
        self.assertEqual(st, 400, d)
        self.assertEqual(call("/api/artifact", {"room": room, "parent": at})[0], 400)
        # the human line is a node of the room but not a branch of this fan
        st, d = call("/api/artifact", {"room": room, "parent": at, "kept": [b[0]["id"], at]})
        self.assertEqual(st, 400, d)
        self.assertEqual(call("/api/artifact", {"room": room, "parent": at,
                                                "kept": ["ghost123"]})[0], 400)
        self.assertEqual(call("/api/artifact", {"room": room, "parent": "ghost",
                                                "kept": [b[0]["id"]]})[0], 400)
        self.assertEqual(call("/api/artifact", {"room": "nobody-home", "parent": at,
                                                "kept": [b[0]["id"]]})[0], 404)
        # An ARTIFACT name is still one flat segment — artifacts are not filed in folders —
        # while the room it is cut from is a path, so `a/b` is refused as a name and read as
        # a missing room.
        for bad in ("../escape", "a/b", "x" * 65, 42):
            self.assertEqual(call("/api/artifact", {"room": room, "parent": at, "name": bad,
                                                    "kept": [b[0]["id"]]})[0], 400, bad)
        for bad in ("../escape", ".trash/x", "x" * 65, 42):
            self.assertEqual(call("/api/artifact", {"room": bad, "parent": at,
                                                    "kept": [b[0]["id"]]})[0], 400, bad)
        self.assertEqual(call("/api/artifact", {"room": "a/b", "parent": at,
                                                "kept": [b[0]["id"]]})[0], 404)
        self.assertEqual(set(os.listdir(ARTS)), before)     # not one refusal wrote a file

        name = f"taken-{uuid.uuid4().hex[:6]}"
        st, d = call("/api/artifact", {"room": room, "parent": at, "name": name,
                                       "kept": [b[0]["id"]]})
        self.assertEqual(st, 200, d)
        with open(os.path.join(ARTS, name + ".json"), "rb") as f:
            first = f.read()
        st, d = call("/api/artifact", {"room": room, "parent": at, "name": name,
                                       "kept": [b[1]["id"]]})
        self.assertEqual(st, 409, d)
        with open(os.path.join(ARTS, name + ".json"), "rb") as f:
            self.assertEqual(f.read(), first)               # frozen: never overwritten
        self.assertFalse([f for f in os.listdir(ARTS) if f.endswith(".part")])

    def test_bad_names_on_the_way_out(self):
        for bad in ("../loom", "a/b", ""):
            self.assertEqual(art_get(bad)[0], 400, bad)
        self.assertEqual(art_get("nobody-home")[0], 404)
        # a file dropped in by hand with a name the api would refuse is not on the list
        with open(os.path.join(ARTS, "bad name!.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "sneaked in", "created": time.time()}, f)
        self.assertNotIn("bad name!", [r["name"] for r in call("/api/artifacts")[1]["artifacts"]])

    def test_list_newest_first(self):
        t, b = kept_fan("art-order", n=2, keep=(0,))
        body = {"room": t.d["name"], "parent": t.d["current"], "kept": [b[0]["id"]]}
        a = call("/api/artifact", body)[1]["name"]
        time.sleep(0.02)
        z = call("/api/artifact", body)[1]["name"]
        names = [r["name"] for r in call("/api/artifacts")[1]["artifacts"]]
        self.assertLess(names.index(z), names.index(a))

    def test_a_star_is_the_save(self):
        """sync: one artifact per fan, rebuilt as the stars change, trashed with the last one,
        and never a frozen artifact rewritten — only the ones stars made."""
        t, b = kept_fan("art-star", keep=(1,))
        room, at = t.d["name"], t.d["current"]
        frozen = call("/api/artifact", {"room": room, "parent": at, "kept": [b[1]["id"]]})[1]["name"]
        st, d = call("/api/artifact", {"room": room, "parent": at, "sync": True})
        self.assertEqual(st, 200, d)
        first = d["name"]
        self.assertNotEqual(first, frozen)
        a = art_get(first)[1]
        self.assertEqual(a["by"], "star")
        self.assertEqual([k["id"] for k in a["steps"][-1]["kept"]], [b[1]["id"]])
        # the spine rides along as nodes, so the artifact can be a room again
        self.assertEqual(a["blocks"][0]["kind"], "root")
        self.assertEqual(a["blocks"][-1]["id"], at)

        b[3]["kept"] = True
        assert t.save()[0] == 200
        d = call("/api/artifact", {"room": room, "parent": at, "sync": True})[1]
        self.assertEqual(d["name"], first)                  # the same file, rewritten
        a = art_get(first)[1]
        self.assertEqual({k["id"] for k in a["steps"][-1]["kept"]}, {b[1]["id"], b[3]["id"]})

        # the canvas route syncs too: unkeep both there and the artifact goes to .trash
        for br in (b[1], b[3]):
            st, d = call("/api/keep", {"room": room, "node": br["id"], "kept": False})
            self.assertEqual(st, 200, d)
        self.assertEqual(art_get(first)[0], 404)
        self.assertTrue(any(f.startswith(first) for f in os.listdir(os.path.join(ARTS, ".trash"))))
        self.assertEqual(art_get(frozen)[0], 200)           # the hand-saved one never moved
        # nothing kept and nothing there: fine, nothing happens
        d = call("/api/artifact", {"room": room, "parent": at, "sync": True})[1]
        self.assertIsNone(d["name"])
        self.assertEqual(call("/api/artifact", {"room": room, "parent": "ghost",
                                                "sync": True})[0], 400)

    def test_kept_flags_ride_in_the_room(self):
        t, b = kept_fan("art-flags")
        back = call("/api/sitting?name=" + t.d["name"])[1]
        self.assertEqual([n["id"] for n in back["nodes"].values() if n.get("kept")],
                         [b[1]["id"], b[4]["id"]])

    def test_a_walk_of_several_steps(self):
        # Four forks walked, the keeps left on cards along the way, and one save at the end:
        # the server finds every earlier step by itself, off the flags in the room.
        t, walk = walk_room("art-walk")
        a = save_walk(t, walk)
        self.assertEqual(len(a["steps"]), len(walk))
        self.assertEqual([s["at"] for s in a["steps"]], [head for head, _, _, _ in walk])
        for s, (head, branches, took, keeps) in zip(a["steps"], walk):
            at = {br["id"]: i + 1 for i, br in enumerate(branches)}
            self.assertEqual(s["took"]["id"], took["id"])
            self.assertEqual(s["took"]["text"], took["text"])
            self.assertEqual(s["took"]["at"], at[took["id"]])
            self.assertEqual(s["took"]["temperature"], took["meta"]["params"]["temperature"])
            self.assertNotIn("probs", s["took"]["meta"])
            # the keeps made at THAT fork, in fan order, and never the line he took
            self.assertEqual([k["id"] for k in s["kept"]], keeps)
            self.assertEqual([k["at"] for k in s["kept"]], [at[k] for k in keeps])
            self.assertNotIn(took["id"], [k["id"] for k in s["kept"]])
            self.assertEqual(s["fan"]["size"], len(branches))
            named = {took["id"], *keeps}
            self.assertEqual([o["id"] for o in s["fan"]["others"]],
                             [br["id"] for br in branches if br["id"] not in named])
            for o in s["fan"]["others"]:
                src = t.d["nodes"][o["id"]]
                self.assertEqual(o["opening"], src["text"][:80])
                self.assertEqual(o["length"], len(src["text"]))
        row = next(r for r in call("/api/artifacts")[1]["artifacts"] if r["name"] == a["name"])
        self.assertEqual((row["steps"], row["kept"], row["fan"]), (4, 4 + 5, 6 + 4 + 5 + 3))

    def test_the_prompt_and_the_leads_rebuild_the_document(self):
        t, walk = walk_room("art-doc")
        a = save_walk(t, walk)
        # the prompt is the document the FIRST fan was drawn from, verbatim
        self.assertEqual(a["prompt"], t.prompt_from(walk[0][0]))
        self.assertEqual(a["steps"][0]["lead"], "")    # the prompt already reaches that fan
        doc = a["prompt"] + "".join(s["lead"] + (s["took"] or {}).get("text", "")
                                    for s in a["steps"])
        self.assertEqual(doc, t.prompt_from(t.d["current"]))

    def test_a_step_with_no_keeps_is_still_a_step(self):
        t, walk = walk_room("art-nokeeps")
        step = save_walk(t, walk)["steps"][1]          # the fan of four he kept nothing in
        self.assertEqual(step["kept"], [])
        self.assertEqual(step["took"]["id"], walk[1][2]["id"])
        self.assertEqual(step["fan"]["size"], 4)
        self.assertEqual(len(step["fan"]["others"]), 3)
        # naming one of four is exactly what curation charges for a pick
        self.assertEqual(step["bits"], round(math.log2(4), 3))

    def test_a_fan_of_one_is_not_a_step(self):
        t, walk = walk_room("art-single", plan=((3, (1,)), (1, ()), (4, (0,))))
        a = save_walk(t, walk)
        self.assertEqual([s["at"] for s in a["steps"]], [walk[0][0], walk[2][0]])
        # a line with no siblings was no choice, so it leaves the picture — but not the
        # document: it rides in the next step's lead
        self.assertIn(walk[1][2]["text"], a["steps"][1]["lead"])

    def test_bits_per_step_and_the_total(self):
        t, walk = walk_room("art-walkbits")
        a = save_walk(t, walk)
        # k is the line taken plus the branches kept beside it: 3 of 6, 1 of 4, 3 of 5, 2 of 3
        want = [math.log2(math.comb(6, 3)), math.log2(math.comb(4, 1)),
                math.log2(math.comb(5, 3)), math.log2(math.comb(3, 2))]
        self.assertEqual([s["bits"] for s in a["steps"]], [round(w, 3) for w in want])
        self.assertEqual(a["bits"], round(sum(want), 3))

    def test_an_old_one_step_artifact_still_opens(self):
        # Written before the walk existed: `kept` and `fan` at the top and no `steps`. It is
        # never migrated, so it has to come back exactly as it lies on the disk, and the list
        # has to count it without guessing.
        name = f"old-{uuid.uuid4().hex[:6]}"
        old = {"name": name, "title": "one fan, frozen · 16 sep", "created": time.time(),
               "source": {"room": "a-room-since-cleared", "title": None, "node": "b765724a"},
               "model": {"file": "nemo.gguf", "path": None, "n_ctx": 8192, "build": None},
               "prompt": "ST. CATHERINE OF THE CHROME\n",
               "turn": TURN, "params": PARAMS,
               "kept": [{"id": "k1", "at": 13, "text": " and maybe she was the last witch",
                         "temperature": 1.8, "posed": False, "meta": {"tokens_predicted": 60}}],
               "fan": {"size": 40, "others": [{"id": "o1", "at": 1, "opening": " No-witch.",
                                               "length": 208, "temperature": 1.8,
                                               "pruned": False}]},
               "bits": 5.322}
        with open(os.path.join(ARTS, name + ".json"), "w", encoding="utf-8") as f:
            json.dump(old, f, ensure_ascii=False)
        st, a = art_get(name)
        self.assertEqual(st, 200, a)
        self.assertEqual(a, old)
        self.assertNotIn("steps", a)
        row = next(r for r in call("/api/artifacts")[1]["artifacts"] if r["name"] == name)
        self.assertEqual((row["steps"], row["kept"], row["fan"]), (0, 1, 40))

    def test_the_document_at_a_url(self):
        # What the export screen reads, and what a browser opened at that address shows: a
        # short head, a blank line, and then the room's own text, verbatim.
        t, walk = walk_room("art-text")
        a = save_walk(t, walk)
        st, text = call("/api/artifact/text?name=" + urllib.parse.quote(a["name"]))
        self.assertEqual(st, 200, text)
        head, _, doc = text.partition("\n\n")
        self.assertEqual(head.split("\n")[0], a["title"])
        self.assertIn("model: " + a["model"]["file"], head)
        self.assertIn(f"temperature {a['params']['temperature']}", head)
        self.assertIn(f"walk: {len(a['steps'])} steps", head)
        self.assertEqual(doc, t.prompt_from(t.d["current"]))

    def test_the_document_ends_on_the_keeps_of_an_open_fan(self):
        # Nothing was taken at the fan he saved from, so the keeps ARE the ending — each
        # under a bare mark, in fan order, and the document itself untouched before them.
        t, b = kept_fan("art-text-open")
        at = t.d["current"]
        d = call("/api/artifact", {"room": t.d["name"], "parent": at,
                                   "kept": [b[4]["id"], b[1]["id"]]})[1]
        text = call("/api/artifact/text?name=" + d["name"])[1]
        doc = text.partition("\n\n")[2]
        self.assertEqual(doc, t.prompt_from(at) +
                         "\n\n[generation begins]\n\n" + b[1]["text"] +
                         "\n\n[generation begins]\n\n" + b[4]["text"])

    def test_the_document_says_no_in_plain_text(self):
        # Whatever opens this url is reading, not parsing: a json error here would be a page
        # of braces in a browser window.
        for path, code, want in (("?name=nope", 404, "no such artifact"),
                                 ("?name=../secrets", 400, "bad name")):
            st, body = call("/api/artifact/text" + path)
            self.assertEqual(st, code, body)
            self.assertEqual(body.strip(), want)


# ---- the walks berserk left ---------------------------------------------------------------
# The record of a night is the ROOM plus the LEDGER, so the route reads both and the tests
# write both. Nothing here touches the real shelf or the real ledger: LOOM_LEDGER points at a
# temp file, the way LOOM_SITTINGS points at a temp shelf.
LEDGER_ROWS: list[dict] = []


def ledger_write(tail: str = "") -> None:
    """The ledger as berserk leaves it, one json object per line. `tail` is a line written
    only half way — what the last line of a live run looks like between two disk writes."""
    with open(LEDGER, "w", encoding="utf-8") as f:
        for r in LEDGER_ROWS:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.write(tail)


ROOT_TEXT = "THE ERRATA SLIP\nleaf torn, entry 4,"
TOOK_TEXT = " and the ink had run."


def walked_room(prefix: str, rows: bool = True):
    """A room shaped like one berserk walked: a seed, a fan of three under it with one branch
    taken, and a closing fan of three under that with one kept and nothing taken.

    Built by hand rather than through the stub, so the leads and the document are exact
    strings a test can name instead of whatever the fake llama felt like saying.
    """
    t = Tree(f"{prefix}-{uuid.uuid4().hex[:6]}")
    root = t.d["root"]
    t.d["nodes"][root]["text"] = ROOT_TEXT
    one = [t.add("model", txt, root, {"params": dict(PARAMS, temperature=temp)})
           for txt, temp in ((" the slip was blank.", 1.4), (TOOK_TEXT, 1.7), ("", 2.4))]
    took = one[1]
    two = [t.add("model", txt, took["id"], {"params": dict(PARAMS, temperature=temp)})
           for txt, temp in ((" nobody signed it.", 1.4), (" the clerk was gone.", 2.0),
                             (" it had been returned.", 2.4))]
    # `current` stands on the branch TAKEN: the closing fan is kept, never continued from.
    t.d["current"] = took["id"]
    st, d = t.save()
    assert st == 200 and d.get("ok"), d
    if not rows:
        return t, one, two
    name = t.d["name"]
    LEDGER_ROWS.extend([
        # Written out of order on purpose: the route sorts by fork, it does not trust the file.
        {"cycle": 90, "page": 1, "room": name, "fork": 2, "picker": "margin", "closing": True,
         "fan_size": 3, "attempts": 1, "widened": False,
         "order": [two[2]["id"], two[0]["id"], two[1]["id"]],
         "notes": ["that it had come back at all", "", "the clerk's own hand"],
         "pick_note": 2, "pick": None, "keep": [two[1]["id"]], "outcome": "match"},
        {"cycle": 90, "page": 1, "room": name, "fork": 1, "picker": "about", "closing": False,
         "fan_size": 3, "attempts": 2, "widened": False,
         "order": [one[0]["id"], one[1]["id"], one[2]["id"]],
         "ask": "the one that scared me was about",
         "quote": "the ink running over the entry",
         "why": "because a record that runs is no record",
         "wished": ["a slip nobody ever drew"],
         "tries": [{"said": "a slip nobody ever drew", "why": "", "hit": None, "widened": False},
                   {"said": "the ink running over the entry",
                    "why": "because a record that runs is no record", "hit": 1,
                    "widened": False}],
         "outcome": "match", "pick": one[1]["id"], "keep": []},
        # The run's own bookkeeping, not a fan: it must not come back as a row.
        {"event": "page", "cycle": 90, "page": 1, "room": name, "seed": "errata-slip.txt"},
    ])
    ledger_write()
    return t, one, two


class Berserk(unittest.TestCase):
    def test_the_room_the_rows_and_the_document(self):
        t, one, two = walked_room("brz")
        st, d = call("/api/berserk?name=" + t.d["name"])
        self.assertEqual(st, 200, d)
        # the room verbatim, so the page can read a branch's text without a second request
        self.assertEqual(d["sitting"]["nodes"].keys(), t.d["nodes"].keys())
        self.assertEqual([r["fork"] for r in d["rows"]], [1, 2])
        self.assertEqual([r["picker"] for r in d["rows"]], ["about", "margin"])
        # the page event is bookkeeping and never a fan
        self.assertTrue(all(r.get("event") is None for r in d["rows"]))
        # the lead: the unfinished last line of the document each fan hangs under
        self.assertEqual(d["rows"][0]["lead"], "leaf torn, entry 4,")
        self.assertEqual(d["rows"][1]["lead"], "leaf torn, entry 4," + TOOK_TEXT)
        # the story, as it came out: root down to the last branch TAKEN, nothing between
        self.assertEqual(d["text"], ROOT_TEXT + TOOK_TEXT)
        # what the two shapes carry through untouched
        self.assertEqual(len(d["rows"][0]["tries"]), 2)
        self.assertEqual(d["rows"][1]["notes"][2], "the clerk's own hand")

    def test_a_lot_drawn_under_a_beat_comes_through_whole(self):
        # berserk's `--picker random` with `--beats`: no reader, no tries, and one line of
        # ours posed into the document before the fan. The route reads the ledger as it
        # finds it, so the only thing it has to get right here is the lead — the beat ends
        # on a newline, so there is nothing unfinished for the branches to be carrying.
        t = Tree("brz-lot-" + uuid.uuid4().hex[:6])
        root = t.d["root"]
        t.d["nodes"][root]["text"] = ROOT_TEXT + TOOK_TEXT
        beat = t.add("human", "\n\nlater.\n", root)
        beat["posed"] = True
        fan = [t.add("model", txt, beat["id"], {"params": dict(PARAMS, temperature=1.4)})
               for txt in ("the hall was still.", "nobody came back for it.")]
        t.d["current"] = fan[1]["id"]
        st, d = t.save()
        self.assertEqual(st, 200, d)
        LEDGER_ROWS.append(
            {"cycle": 91, "page": 1, "room": t.d["name"], "fork": 1, "picker": "random",
             "closing": False, "ask": "", "beat": "later.", "fan_size": 2, "attempts": 1,
             "widened": False, "order": [n["id"] for n in fan], "quote": "", "why": "",
             "wished": [], "used": "lot", "outcome": "random", "reader_failed": False,
             "pick": fan[1]["id"], "keep": []})
        ledger_write()
        st, d = call("/api/berserk?name=" + t.d["name"])
        self.assertEqual(st, 200, d)
        row = d["rows"][0]
        self.assertEqual(row["beat"], "later.")
        self.assertEqual(row["used"], "lot")
        self.assertEqual(row["lead"], "", "the beat ends the line it stands on")
        self.assertNotIn("tries", row)
        self.assertEqual(d["text"], ROOT_TEXT + TOOK_TEXT + "\n\nlater.\n" + fan[1]["text"])

    def test_a_half_written_last_line_is_skipped(self):
        t, one, two = walked_room("brz-torn")
        # berserk appends to this file while it walks: the last line is regularly half on
        # disk, and a screen that 500s for those milliseconds breaks when somebody is watching.
        ledger_write(tail='{"cycle": 90, "room": "' + t.d["name"] + '", "fork": 3, "ord')
        st, d = call("/api/berserk?name=" + t.d["name"])
        self.assertEqual(st, 200, d)
        self.assertEqual([r["fork"] for r in d["rows"]], [1, 2])
        ledger_write()

    def test_a_room_nobody_walked_is_a_404(self):
        t, _, _ = walked_room("brz-unwalked", rows=False)
        for path, code, want in ((t.d["name"], 404, "berserk never walked that room"),
                                 ("nope-" + uuid.uuid4().hex[:6], 404, "no such sitting"),
                                 ("../secrets", 400, "bad name")):
            st, d = call("/api/berserk?name=" + urllib.parse.quote(path))
            self.assertEqual(st, code, d)
            self.assertEqual(d["error"], want)

    def test_the_shelf_says_which_rooms_were_walked(self):
        t, _, _ = walked_room("brz-flag")
        plain = fresh("brz-plain")
        rows = {s["name"]: s["berserk"] for s in call("/api/sittings")[1]["sittings"]}
        self.assertIs(rows[t.d["name"]], True)
        self.assertIs(rows[plain.d["name"]], False)

    def test_the_document_at_a_url(self):
        # The same string the json route carries, at an address that can be sent — one
        # implementation on the server, like the artifact's.
        t, _, _ = walked_room("brz-text")
        st, text = call("/api/berserk/text?name=" + t.d["name"])
        self.assertEqual(st, 200, text)
        self.assertEqual(text, ROOT_TEXT + TOOK_TEXT)
        self.assertEqual(text, call("/api/berserk?name=" + t.d["name"])[1]["text"])

    def test_the_document_says_no_in_plain_text(self):
        # Whatever opens this url is reading, not parsing: braces in a browser window are
        # not an error message.
        t, _, _ = walked_room("brz-text-no", rows=False)
        for path, code, want in ((t.d["name"], 404, "berserk never walked that room"),
                                 ("../secrets", 400, "bad name")):
            st, body = call("/api/berserk/text?name=" + urllib.parse.quote(path))
            self.assertEqual(st, code, body)
            self.assertEqual(body.strip(), want)


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


class ReadOnly(unittest.TestCase):
    """The mirror on the mini: a second loom over the same shelf with LOOM_READONLY=1. It
    reads everything the real one reads and refuses every write but a mark, which it also
    journals for the mac to replay — so the only writer of record stays the mac."""

    def setUp(self):
        global BASE
        self.t, self.b = kept_fan("mirror")       # written through the real loom
        self.base = BASE
        self.journal = os.path.join(BERSERK, f"marks-{uuid.uuid4().hex[:6]}.jsonl")
        port = free_port()
        env = dict(os.environ, LOOM_HOST="127.0.0.1", LOOM_PORT=str(port), LOOM_SITTINGS=SHELF,
                   LOOM_STORAGE=STORE, LOOM_ARTIFACTS=ARTS, LOOM_LEDGER=LEDGER,
                   LOOM_LLAMA=STUB_BASE, LOOM_READONLY="1", LOOM_MARKS=self.journal)
        self.proc = subprocess.Popen([sys.executable, os.path.join(EVA, "server", "loom.py")],
                                     env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        BASE = f"http://127.0.0.1:{port}"
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                if call("/api/health")[0] == 200:
                    return
            except OSError:
                time.sleep(0.15)
        raise RuntimeError("the read-only loom never came up")

    def tearDown(self):
        global BASE
        BASE = self.base
        self.proc.terminate()
        self.proc.wait(timeout=5)

    def test_reads_everything_writes_only_marks(self):
        st, h = call("/api/health")
        self.assertEqual((st, h["readonly"], h["ok"]), (200, True, False))
        self.assertEqual(call("/")[0], 200)
        names = [r["name"] for r in call("/api/sittings")[1]["sittings"]]
        self.assertIn(self.t.d["name"], names)
        st, room = call("/api/sitting?name=" + self.t.d["name"])
        self.assertEqual((st, room["current"]), (200, self.t.d["current"]))
        arts = set(os.listdir(ARTS))
        room, nid = self.t.d["name"], self.b[0]["id"]
        self.assertEqual(call("/api/keep", {"room": room, "node": nid, "kept": True})[0], 200)
        self.assertEqual(call("/api/mark", {"room": room, "node": nid, "mark": "good",
                                            "on": True})[0], 200)
        self.assertEqual(call("/api/mark", {"room": room, "node": "ghost", "mark": "good",
                                            "on": True})[0], 404)
        with open(os.path.join(SHELF, room + ".json"), encoding="utf-8") as f:
            node = json.load(f)["nodes"][nid]
        self.assertTrue(node.get("kept") and node.get("good"))    # the page sees them at once
        with open(self.journal, encoding="utf-8") as f:
            lines = [json.loads(x) for x in f]
        self.assertEqual([(x["node"], x["mark"], x["on"]) for x in lines],
                         [(nid, "kept", True), (nid, "good", True)])   # the refused one isn't in
        self.assertEqual(set(os.listdir(ARTS)), arts)    # artifacts are built on the mac, later

        for path, body in (("/api/sitting", self.t.d),
                           ("/api/artifact", {"room": self.t.d["name"],
                                              "parent": self.t.d["current"], "sync": True}),
                           ("/api/complete", {"prompt": "x", "params": {}})):
            st, d = call(path, body)
            self.assertEqual(st, 403, path)
            self.assertIn("read-only", d["error"])
        # and the real loom still says it is not the mirror
        self.assertFalse(json.loads(urllib.request.urlopen(self.base + "/api/health",
                                                           timeout=10).read())["readonly"])


if __name__ == "__main__":
    unittest.main()
