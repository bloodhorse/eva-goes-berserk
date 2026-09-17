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
# A second and a third fake llama, for --models: the comparison is only testable if two
# endpoints can be told apart, and the narrow one is how the context skip is reached without
# a seed of ten thousand words.
STUB_B = None
STUB_NARROW = None
URL_A = URL_B = URL_NARROW = ""


def setUpModule() -> None:
    global STUB, STUB_B, STUB_NARROW, URL_A, URL_B, URL_NARROW
    STUB = stub_llama.serve(0)
    STUB_B = stub_llama.serve(0, model_path="/models/stub-small-1b.Q8_0.gguf")
    STUB_NARROW = stub_llama.serve(0, n_ctx=12, model_path="/models/stub-tiny.gguf")
    for srv in (STUB, STUB_B, STUB_NARROW):
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    URL_A = f"http://127.0.0.1:{STUB.server_address[1]}"
    URL_B = f"http://127.0.0.1:{STUB_B.server_address[1]}"
    URL_NARROW = f"http://127.0.0.1:{STUB_NARROW.server_address[1]}"
    # census calls eva.complete_stream, which reads eva.LLAMA at call time — so pointing
    # this one name at the stub is enough, and no live server is ever needed.
    eva.LLAMA = URL_A
    os.makedirs(SHELF, exist_ok=True)


def tearDownModule() -> None:
    for srv in (STUB, STUB_B, STUB_NARROW):
        if srv:
            srv.shutdown()
    shutil.rmtree(SHELF, ignore_errors=True)


def run(*args) -> tuple[int, str]:
    # stderr into the same buffer: a refusal is an answer this test wants to read, and a
    # test run should not spray the terminal with the messages it asked for on purpose.
    out = io.StringIO()
    with redirect_stdout(out), redirect_stderr(out):
        code = census.main(["census.py", *args])
    return code, out.getvalue()


def on_disk(name: str) -> dict:
    with open(loom.sitting_path(name), encoding="utf-8") as f:
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
            # Even with no --models, a branch says what drew it: llama's own file name,
            # read once per run off /props — the same string an artifact is saved with.
            self.assertEqual(k["meta"]["model"], "stub-base-12b.Q5_K_M.gguf")
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

    def test_a_name_with_slashes_files_the_room_in_a_folder(self):
        # A census is dozens of branches in one room, and dozens of those rooms in one
        # night: the point of the path is that they can be filed as they are made.
        name = f"{fresh_name()}/basin/free-01"
        code, out = run("--name", name, "--empty", "--n", "2")
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.isfile(os.path.join(SHELF, *name.split("/")) + ".json"))
        d = on_disk(name)
        self.assertEqual(d["name"], name)
        self.assertEqual(len([n for n in d["nodes"].values() if n["kind"] == "model"]), 2)
        self.assertIn(name, [s["name"] for s in loom.shelf()])
        self.assertIn(name, out)                    # the line it prints is the path it wrote
        # and a taken path is the same no-op a taken name is
        self.assertEqual(run("--name", name, "--empty", "--n", "1")[0], 1)

    def test_refusals(self):
        self.assertEqual(run("--name", "../escape", "--empty", "--n", "1")[0], 2)
        for bad in ("a//b", ".trash/x", "a/", "/a"):
            self.assertEqual(run("--name", bad, "--empty", "--n", "1")[0], 2, bad)
        self.assertEqual(run("--name", fresh_name(), "--empty", "--n", "0")[0], 2)
        self.assertEqual(run("--name", fresh_name(), "--empty", "--n", "1",
                             "--temps", "hot")[0], 2)
        self.assertEqual(run("--name", fresh_name(), "--doc", "/nope/nothing/here")[0], 1)
        # and none of those left a file behind
        self.assertEqual([f for f in os.listdir(SHELF) if f.startswith("../")], [])

    # ---- --models: the blind comparison ------------------------------------------------
    def test_models_split_the_fan_evenly_and_stamp_every_branch(self):
        name = fresh_name()
        before_a, before_b = len(STUB.seen), len(STUB_B.seen)
        code, out = run("--name", name, "--empty", "--bare", "--n", "6",
                        "--temps", "1.4,2.2", "--models", f"a={URL_A},b={URL_B}")
        self.assertEqual(code, 0, out)

        d = on_disk(name)
        kids = sorted((n for n in d["nodes"].values() if n["kind"] == "model"),
                      key=lambda n: n["ts"])
        self.assertEqual(len(kids), 6)
        got = [k["meta"]["model"] for k in kids]
        self.assertEqual(sorted(got), ["a", "a", "a", "b", "b", "b"])   # 3/3, not 4/2
        # each model got the same slice of the temperature range
        for who in ("a", "b"):
            mine = sorted(k["meta"]["params"]["temperature"]
                          for k in kids if k["meta"]["model"] == who)
            self.assertEqual(mine, [1.4, 1.4, 2.2])
        # both servers were really asked, and only three times each
        self.assertEqual(len(STUB.seen) - before_a, 3)
        self.assertEqual(len(STUB_B.seen) - before_b, 3)
        # position says nothing: the written order is not a grouped by model
        self.assertNotEqual(got, ["a", "a", "a", "b", "b", "b"])
        self.assertNotEqual(got, ["b", "b", "b", "a", "a", "a"])
        # and it is exactly the order the plan laid out from the room name
        self.assertEqual(got, [m for m, _ in census.plan(6, [1.4, 2.2], ["a", "b"], name)])

    def test_the_order_is_seeded_from_the_room_name(self):
        """A rerun under the same name must lay the pile out the same way — the shuffle is
        the thing that hides the key, and a key that cannot be recomputed is lost."""
        a = census.plan(30, [1.4, 2.2], ["x", "y", "z"], "experiments/three-models/s")
        b = census.plan(30, [1.4, 2.2], ["x", "y", "z"], "experiments/three-models/s")
        self.assertEqual(a, b)
        self.assertEqual([m for m, _ in a].count("x"), 10)              # 10/10/10
        self.assertNotEqual(a, census.plan(30, [1.4, 2.2], ["x", "y", "z"], "other"))
        # a remainder goes to the models named first, and nothing is lost
        counts = [m for m, _ in census.plan(7, [1.0], ["x", "y", "z"], "n")]
        self.assertEqual((counts.count("x"), counts.count("y"), counts.count("z")), (3, 2, 2))

    def test_a_model_whose_window_is_too_small_is_skipped(self):
        name = fresh_name()
        doc = os.path.join(SHELF, name + ".txt")
        with open(doc, "w", encoding="utf-8") as f:
            f.write("CENSUSNARROW " + " ".join(f"word{i}" for i in range(40)))
        code, out = run("--name", name, "--doc", doc, "--bare", "--n", "4",
                        "--n-predict", "8",
                        "--models", f"wide={URL_A},narrow={URL_NARROW}")
        self.assertEqual(code, 0, out)
        self.assertIn("skip · narrow", out)
        d = on_disk(name)
        kids = [n for n in d["nodes"].values() if n["kind"] == "model"]
        # the narrow model's share is dropped, not handed to the other one: a comparison
        # with a model missing has to LOOK short
        self.assertEqual([k["meta"]["model"] for k in kids], ["wide", "wide"])
        self.assertEqual(STUB_NARROW.seen[-1].get("content"), d["nodes"][d["root"]]["text"])

    def test_tail_cuts_the_document_to_whole_paragraphs(self):
        name = fresh_name()
        doc = os.path.join(SHELF, name + ".txt")
        first = "CENSUSTAIL " + " ".join(f"old{i}" for i in range(30))
        with open(doc, "w", encoding="utf-8") as f:
            f.write(first + "\n\nthe second one is short.\n\nand the last one ends here")
        code, out = run("--name", name, "--doc", doc, "--bare", "--n", "1", "--tail", "12")
        self.assertEqual(code, 0, out)
        root = on_disk(name)["nodes"][on_disk(name)["root"]]["text"]
        # a verbatim suffix, opening on a paragraph, ending exactly where the seed ended
        self.assertEqual(root, "the second one is short.\n\nand the last one ends here")
        self.assertNotIn("CENSUSTAIL", root)
        self.assertIn("tail · 12 tokens", out)
        # and the wire saw the cut text, not the file
        wire = [b for b in stub_llama.SEEN if b.get("prompt") == root]
        self.assertTrue(wire)

    def test_tail_falls_back_to_a_sentence_when_no_paragraph_fits(self):
        one = "CENSUSSENT " + " ".join(f"w{i}" for i in range(20)) + ". a short last one."
        self.assertEqual(census.trim_tail(one, 6, lambda t: len(t.split())),
                         "a short last one.")
        # already short enough: untouched, whatever the paragraphs look like
        self.assertEqual(census.trim_tail("a\n\nb", 99, lambda t: len(t.split())), "a\n\nb")

    def test_bad_models_are_refused(self):
        for bad in ("nourl", "=http://127.0.0.1:1", "a=", "a=x,a=y", "a b=http://h:1"):
            self.assertEqual(run("--name", fresh_name(), "--empty", "--n", "1",
                                 "--models", bad)[0], 2, bad)

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
