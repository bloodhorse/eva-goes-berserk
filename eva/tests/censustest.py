#!/usr/bin/env -S uv run --python 3.12
"""censustest.py — census.py driven as a function, against the fake llama-server.

    uv run --python 3.12 -m unittest tests/censustest.py

`census.main` takes its argv and returns an exit code, so a test runs a whole unattended
census without a terminal and without a model. What is under test is the file it leaves
behind: a census is only worth anything if the room it writes is a room the page can open,
so every test here reads the json back through loom.check.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import uuid
from contextlib import redirect_stderr, redirect_stdout

TESTS = os.path.dirname(os.path.abspath(__file__))
EVA = os.path.dirname(TESTS)                      # eva/: server/ has loom, cli/ has eva and census
for d in (TESTS, os.path.join(EVA, "server"), os.path.join(EVA, "cli")):
    sys.path.insert(0, d)
import stub_llama  # noqa: E402

# Before importing loom, and it has to be — loom reads LOOM_SITTINGS once, at import.
SHELF = tempfile.mkdtemp(prefix="census-test-")
os.environ["LOOM_SITTINGS"] = SHELF

import census  # noqa: E402
import eva  # noqa: E402
import loom  # noqa: E402

# Another test module in the same run may have imported loom first; follow it rather than
# argue with it (see evatest for the same knot). Either way it is never the real shelf.
if loom.SITTINGS != SHELF:
    shutil.rmtree(SHELF, ignore_errors=True)
    SHELF = loom.SITTINGS
    census.SITTINGS = SHELF

STUB = None


def setUpModule() -> None:
    global STUB
    STUB = stub_llama.serve(0)
    threading.Thread(target=STUB.serve_forever, daemon=True).start()
    # census calls eva.complete_stream, which reads eva.LLAMA at call time — so pointing
    # this one name at the stub is enough, and no live server is ever needed.
    eva.LLAMA = f"http://127.0.0.1:{STUB.server_address[1]}"
    os.makedirs(SHELF, exist_ok=True)


def tearDownModule() -> None:
    if STUB:
        STUB.shutdown()
    shutil.rmtree(SHELF, ignore_errors=True)


def run(*args) -> tuple[int, str]:
    # stderr into the same buffer: a refusal is an answer this test wants to read, and a
    # test run should not spray the terminal with the messages it asked for on purpose.
    out = io.StringIO()
    with redirect_stdout(out), redirect_stderr(out):
        code = census.main(["census.py", *args])
    return code, out.getvalue()


def on_disk(name: str) -> dict:
    with open(os.path.join(SHELF, name + ".json"), encoding="utf-8") as f:
        d = json.load(f)
    assert loom.check(d) == "", loom.check(d)
    return d


def fresh_name() -> str:
    return "c" + uuid.uuid4().hex[:8]


class Census(unittest.TestCase):
    def test_a_document_and_six_continuations_across_three_temperatures(self):
        name = fresh_name()
        doc = os.path.join(SHELF, name + ".txt")
        with open(doc, "w", encoding="utf-8") as f:
            f.write("CENSUSMARK the door was\n")
        code, out = run("--name", name, "--doc", doc, "--n", "6",
                        "--temps", "0.8,1.2,1.6", "--n-predict", "40")
        self.assertEqual(code, 0, out)

        d = on_disk(name)
        root = d["nodes"][d["root"]]
        self.assertEqual(root["text"], "CENSUSMARK the door was\n")   # verbatim, newline and all
        self.assertEqual(d["current"], d["root"])      # nothing was chosen; the fan stands
        kids = [n for n in d["nodes"].values() if n["parent"] == root["id"]]
        self.assertEqual(len(kids), 6)
        # round-robin, and each branch carries the temperature that made it
        self.assertEqual([k["meta"]["params"]["temperature"] for k in kids],
                         [0.8, 1.2, 1.6, 0.8, 1.2, 1.6])
        for k in kids:
            self.assertEqual(k["kind"], "model")
            self.assertEqual(k["meta"]["params"]["n_predict"], 40)
            self.assertTrue(k["meta"]["probs"])        # streamed probabilities, collected
        # and the wire agrees
        wire = [b for b in stub_llama.SEEN if "CENSUSMARK" in (b.get("prompt") or "")]
        self.assertEqual([b["temperature"] for b in wire], [0.8, 1.2, 1.6, 0.8, 1.2, 1.6])
        for b in wire:
            self.assertEqual(b["prompt"], root["text"])  # the document, nothing round it
            self.assertNotIn("fan", b)

        # one receipt per branch, and the last line says where it is
        lines = [ln for ln in out.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 8)                 # header + six + the footer
        self.assertIn("t 0.8", lines[1])
        self.assertIn("tok", lines[1])
        self.assertIn(name + ".json", lines[-1])

    def test_written_after_every_branch(self):
        """A run killed in the middle must leave what it had — so the file has to be whole
        at every step, not at the end."""
        name = fresh_name()
        seen = []
        real = loom.write_sitting

        def watch(obj):
            ts = real(obj)
            with open(os.path.join(SHELF, obj["name"] + ".json"), encoding="utf-8") as f:
                back = json.load(f)
            seen.append(sum(1 for n in back["nodes"].values() if n["kind"] == "model"))
            assert loom.check(back) == ""
            return ts

        census.write_sitting = watch
        try:
            code, out = run("--name", name, "--empty", "--bare", "--n", "3")
        finally:
            census.write_sitting = real
        self.assertEqual(code, 0, out)
        self.assertEqual(seen, [0, 1, 2, 3])            # the empty room, then one per branch

    def test_bare_room_has_no_names_and_no_stops(self):
        name = fresh_name()
        code, out = run("--name", name, "--empty", "--bare", "--n", "1")
        self.assertEqual(code, 0, out)
        d = on_disk(name)
        self.assertEqual(d["turn"], {"prefix": "", "suffix": ""})
        self.assertEqual(d["params"]["stop"], [])
        self.assertEqual(d["nodes"][d["root"]]["text"], "")
        kid = [n for n in d["nodes"].values() if n["kind"] == "model"][0]
        self.assertEqual(kid["meta"]["stop_type"], "limit")   # nothing to stop on

    def test_chat_room_keeps_the_turn_strings(self):
        name = fresh_name()
        code, _ = run("--name", name, "--empty", "--n", "1")
        self.assertEqual(code, 0)
        d = on_disk(name)
        self.assertEqual(d["turn"], eva.TURN)
        self.assertEqual(d["params"]["stop"], eva.PARAMS["stop"])

    def test_set_reaches_the_wire(self):
        name = fresh_name()
        code, out = run("--name", name, "--empty", "--n", "1", "--bare",
                        "--set", "xtc_probability=0.5", "--set", "ignore_eos=true",
                        "--set", "top_n_sigma=1.5", "--set", "logit_bias=[[1234, -100]]")
        self.assertEqual(code, 0, out)
        kid = [n for n in on_disk(name)["nodes"].values() if n["kind"] == "model"][0]
        p = kid["meta"]["params"]
        self.assertEqual((p["xtc_probability"], p["ignore_eos"], p["top_n_sigma"]),
                         (0.5, True, 1.5))
        body = stub_llama.SEEN[-1]
        self.assertEqual(body["xtc_probability"], 0.5)
        self.assertIs(body["ignore_eos"], True)
        self.assertEqual(body["logit_bias"], [[1234, -100]])
        self.assertEqual(body["prompt"], "")            # --empty really means empty

        self.assertEqual(run("--name", fresh_name(), "--empty", "--set", "nope=1")[0], 2)
        self.assertEqual(run("--name", fresh_name(), "--empty",
                             "--set", "temperature=hot")[0], 2)

    def test_a_taken_name_is_a_noop(self):
        name = fresh_name()
        self.assertEqual(run("--name", name, "--empty", "--n", "1")[0], 0)
        with open(os.path.join(SHELF, name + ".json"), "rb") as f:
            before = f.read()
        code, out = run("--name", name, "--empty", "--n", "1")
        self.assertEqual(code, 1)
        self.assertIn("already exists", out)
        with open(os.path.join(SHELF, name + ".json"), "rb") as f:
            self.assertEqual(f.read(), before)

    def test_refusals(self):
        self.assertEqual(run("--name", "../escape", "--empty", "--n", "1")[0], 2)
        self.assertEqual(run("--name", fresh_name(), "--empty", "--n", "0")[0], 2)
        self.assertEqual(run("--name", fresh_name(), "--empty", "--n", "1",
                             "--temps", "hot")[0], 2)
        self.assertEqual(run("--name", fresh_name(), "--doc", "/nope/nothing/here")[0], 1)
        # and none of those left a file behind
        self.assertEqual([f for f in os.listdir(SHELF) if f.startswith("../")], [])

    def test_a_dead_llama_stops_the_run_and_keeps_what_landed(self):
        name = fresh_name()
        was, eva.LLAMA = eva.LLAMA, "http://127.0.0.1:1"   # nothing listens on port 1
        try:
            code, out = run("--name", name, "--empty", "--n", "5")
        finally:
            eva.LLAMA = was
        self.assertEqual(code, 1)
        d = on_disk(name)                                   # the room exists and is valid
        self.assertEqual([n for n in d["nodes"].values() if n["kind"] == "model"], [])


if __name__ == "__main__":
    unittest.main()
