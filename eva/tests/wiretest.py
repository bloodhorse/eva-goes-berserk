#!/usr/bin/env -S uv run --python 3.12
"""wiretest.py — wire.py driven as a function, against two fake llama-servers.

    uv run --python 3.12 -m unittest tests/wiretest.py

`wire.main` takes its argv and returns an exit code, so a whole chain runs with no terminal and
no model. What is under test is the room it leaves behind and **what went over the wire**: a
chain is only a chain if each model was handed the WHOLE document so far, which is a fact about
the request bodies and not about the file — so most of these read `srv.seen`, one list per stub,
and not just the json.

Two stubs are the point of the file. Seat `a` and seat `b` have to be told apart, and the one
behaviour with no other way in — a model answering nothing twice and the other one taking its
turn — needs a server that can be told what to answer (`serve(..., lines=[...])`).
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
EVA = os.path.dirname(TESTS)                      # eva/: server/ has loom, cli/ has eva and wire
for d in (TESTS, os.path.join(EVA, "server"), os.path.join(EVA, "cli")):
    sys.path.insert(0, d)
import stub_llama  # noqa: E402

# Before importing loom, and it has to be — loom reads LOOM_SITTINGS once, at import.
SHELF = tempfile.mkdtemp(prefix="wire-test-")
os.environ["LOOM_SITTINGS"] = SHELF

import eva  # noqa: E402
import loom  # noqa: E402
import wire  # noqa: E402

# Another test module in the same run may have imported loom first; follow it rather than argue
# with it (censustest and evatest have the same knot). Either way it is never the real shelf.
if loom.SITTINGS != SHELF:
    shutil.rmtree(SHELF, ignore_errors=True)
    SHELF = loom.SITTINGS

# The marker every seed in this file carries, so `stub_llama.SEEN` — one list for the whole
# process — can be filtered down to this file's traffic. It must not be a substring of another
# test file's marker.
MARK = "WIREMARK"

STUB_A = STUB_B = STUB_MUTE = STUB_NARROW = None
URL_A = URL_B = URL_MUTE = URL_NARROW = ""

# Three words a piece and nothing random, so a document's length in stub tokens is arithmetic:
# the context test needs to know exactly when the window runs out.
SHORT = [" one two three"]


def setUpModule() -> None:
    global STUB_A, STUB_B, STUB_MUTE, STUB_NARROW, URL_A, URL_B, URL_MUTE, URL_NARROW
    STUB_A = stub_llama.serve(0, model_path="/models/stub-wire-a.gguf")
    STUB_B = stub_llama.serve(0, model_path="/models/stub-wire-b.gguf")
    # Answers nothing, twice, then something: the retry and the swap in one server.
    STUB_MUTE = stub_llama.serve(0, model_path="/models/stub-mute.gguf",
                                 lines=["", "", " it spoke on the third ask"])
    STUB_NARROW = stub_llama.serve(0, n_ctx=20, model_path="/models/stub-narrow.gguf",
                                  lines=SHORT)
    for srv in (STUB_A, STUB_B, STUB_MUTE, STUB_NARROW):
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    URL_A = f"http://127.0.0.1:{STUB_A.server_address[1]}"
    URL_B = f"http://127.0.0.1:{STUB_B.server_address[1]}"
    URL_MUTE = f"http://127.0.0.1:{STUB_MUTE.server_address[1]}"
    URL_NARROW = f"http://127.0.0.1:{STUB_NARROW.server_address[1]}"
    eva.LLAMA = URL_A            # nothing here uses the fallback, but a live box must not be it
    os.makedirs(SHELF, exist_ok=True)


def tearDownModule() -> None:
    for srv in (STUB_A, STUB_B, STUB_MUTE, STUB_NARROW):
        if srv:
            srv.shutdown()
            srv.server_close()        # or the listening socket leaks a warning per stub
    shutil.rmtree(SHELF, ignore_errors=True)


def run(*args) -> tuple[int, str]:
    # stderr into the same buffer: a refusal is an answer these tests want to read, and a test
    # run should not spray the terminal with the messages it asked for on purpose. SystemExit
    # is argparse refusing a flag, which is a refusal like any other.
    out = io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(out):
            code = wire.main(["wire.py", *args])
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
    return code, out.getvalue()


def on_disk(name: str) -> dict:
    with open(loom.sitting_path(name), encoding="utf-8") as f:
        d = json.load(f)
    assert loom.check(d) == "", loom.check(d)
    return d


def spine(d: dict) -> list[dict]:
    """The room as a list root→last. Also the proof that it IS a spine: every node has at most
    one child, and the walk reaches all of them."""
    kids: dict[str, dict] = {}
    for n in d["nodes"].values():
        p = n.get("parent")
        if p is None:
            continue
        assert p not in kids, f"node {p} has two children — not a chain"
        kids[p] = n
    out = []
    n = kids.get(d["root"])
    while n:
        out.append(n)
        n = kids.get(n["id"])
    assert len(out) == len(d["nodes"]) - 1, "the walk did not reach every node"
    return out


def models(d: dict) -> list[str]:
    return [n["meta"]["model"] for n in spine(d) if n["kind"] == "model"]


def fresh(prefix: str = "w") -> str:
    return prefix + uuid.uuid4().hex[:8]


def seed(name: str, text: str) -> str:
    path = os.path.join(SHELF, name + ".txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def beats_file(name: str, body: str) -> str:
    path = os.path.join(SHELF, name + ".beats.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


# A fixture, not the run's own beats (those are bekh's to decide): two lines per group, so the
# rotation has to wrap inside six turns and a test can see it wrap. The comment line is the
# point of the first line — the loader must skip it.
BEATS = """# posed — a test fixture, not a score
before the voice, one:
before the voice, two:

before the caller, one:
before the caller, two:
"""

MODELS = lambda: f"a=alpha={URL_A},b=beta={URL_B}"        # noqa: E731


class Wire(unittest.TestCase):
    # ---- the plain chain ----------------------------------------------------------------
    def test_two_models_alternate_down_one_spine(self):
        name = fresh()
        doc = seed(name, MARK + " the line went faint:")
        code, out = run("--name", name, "--doc", doc, "--models", MODELS(),
                        "--lines", "6", "--n-predict", "12")
        self.assertEqual(code, 0, out)

        d = on_disk(name)
        self.assertEqual(d["nodes"][d["root"]]["text"], MARK + " the line went faint:")
        chain = spine(d)                      # asserts one child each, and nothing orphaned
        self.assertEqual(len(chain), 6)
        # a writes the odd turns, b the even ones — the whole experiment is that alternation
        self.assertEqual(models(d), ["alpha", "beta"] * 3)
        self.assertEqual([n["meta"]["turn"] for n in chain], [1, 2, 3, 4, 5, 6])
        # `current` is the newest line, so the page opens on the end of the transcript
        self.assertEqual(d["current"], chain[-1]["id"])
        for n in chain:
            self.assertEqual(n["kind"], "model")
            self.assertFalse(n["posed"])
            self.assertEqual(n["meta"]["params"]["n_predict"], 12)
            # the newline seam: every line ends on one, so the next model starts on a fresh line
            self.assertTrue(n["text"].endswith("\n"), repr(n["text"]))
            self.assertEqual(n["text"].count("\n"), 1, repr(n["text"]))
            self.assertEqual(n["text"], n["text"].rstrip() + "\n")   # no trailing space kept

        # one receipt per turn, and the last line says where the room is
        lines = [ln for ln in out.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 8)                  # header + six + the footer
        self.assertIn("turn 1 · alpha", lines[1])
        self.assertIn("turn 2 · beta", lines[2])
        self.assertIn(name + ".json", lines[-1])

    def test_each_model_is_handed_the_whole_document_so_far(self):
        name = fresh()
        doc = seed(name, MARK + "SEEN a switch, and a hum in it:")
        before_a, before_b = len(STUB_A.seen), len(STUB_B.seen)
        code, out = run("--name", name, "--doc", doc, "--models", MODELS(),
                        "--lines", "4", "--n-predict", "12")
        self.assertEqual(code, 0, out)
        d = on_disk(name)
        chain = spine(d)

        asked = lambda srv, n: [b for b in srv.seen[n:] if "prompt" in b]      # noqa: E731
        got_a = asked(STUB_A, before_a)
        got_b = asked(STUB_B, before_b)
        self.assertEqual(len(got_a), 2)                  # turns 1 and 3
        self.assertEqual(len(got_b), 2)                  # turns 2 and 4
        # The document as the page reads it, rebuilt here from the file rather than from the
        # request: if the two ever disagree, the wire and the room are two different documents.
        want = d["nodes"][d["root"]]["text"]
        for i, body in enumerate([got_a[0], got_b[0], got_a[1], got_b[1]]):
            self.assertEqual(body["prompt"], want, f"turn {i + 1}")
            # No stop string: llama's would fire on the newline a base model answers a newline
            # with, and the line is cut out of the budget here instead (see wire.line_of).
            self.assertEqual(body["stop"], [])
            self.assertEqual(body["n_predict"], 12)
            want += chain[i]["text"]
        self.assertEqual(want, loom.prompt_to(d, d["current"]))

    def test_the_brakes_are_on_and_the_room_is_bare(self):
        name = fresh()
        doc = seed(name, MARK + " a relay:")
        self.assertEqual(run("--name", name, "--doc", doc, "--models", MODELS(),
                             "--lines", "1")[0], 0)
        d = on_disk(name)
        self.assertEqual(d["turn"], {"prefix": "", "suffix": ""})   # bare: no speaker names
        self.assertEqual(d["params"]["stop"], [])
        p = d["nodes"][d["current"]]["meta"]["params"]
        # a two-voice loop echoes, so dry and the repeat penalty stay where the room has them
        self.assertEqual(p["dry_multiplier"], eva.PARAMS["dry_multiplier"])
        self.assertEqual(p["repeat_penalty"], eva.PARAMS["repeat_penalty"])
        self.assertEqual(p["min_p"], 0.08)
        self.assertEqual(p["xtc_probability"], 0)

    def test_a_temperature_per_seat(self):
        name = fresh()
        doc = seed(name, MARK + " two heats:")
        code, out = run("--name", name, "--doc", doc, "--models", MODELS(),
                        "--lines", "4", "--temps", "a=1.4,b=2.6")
        self.assertEqual(code, 0, out)
        chain = spine(on_disk(name))
        self.assertEqual([n["meta"]["params"]["temperature"] for n in chain],
                         [1.4, 2.6, 1.4, 2.6])
        # and one number for both, whichever flag says it
        self.assertEqual(wire.temps_of("", 1.9), {"a": 1.9, "b": 1.9})
        self.assertEqual(wire.temps_of("2.2", 1.4), {"a": 2.2, "b": 2.2})

    def test_written_after_every_line(self):
        """A run killed in the middle must leave what it had, so the file is whole at every
        step. It is also what makes a page open on the room watch the transcript grow."""
        name = fresh()
        doc = seed(name, MARK + " watching:")
        seen, real = [], loom.write_sitting

        def watch(obj):
            ts = real(obj)
            with open(loom.sitting_path(obj["name"]), encoding="utf-8") as f:
                back = json.load(f)
            seen.append(sum(1 for n in back["nodes"].values() if n["kind"] == "model"))
            assert loom.check(back) == ""
            return ts

        wire.write_sitting = watch
        try:
            code, out = run("--name", name, "--doc", doc, "--models", MODELS(), "--lines", "3")
        finally:
            wire.write_sitting = real
        self.assertEqual(code, 0, out)
        self.assertEqual(seen, [0, 1, 2, 3])          # the seeded room, then one per line

    def test_the_line_is_cut_out_of_the_budget_not_by_a_stop_string(self):
        """The bug that ate the first real chain: a base model handed a prompt ending on a
        newline answers with another newline, so llama's `stop: ["\\n"]` fires on token 1 and
        the seat looks mute. The line is the first line with something in it."""
        self.assertEqual(wire.line_of("\n\nIt is not yours.\n\nWhat is this noise?"),
                         "It is not yours.")
        self.assertEqual(wire.line_of(" and then the hum   \nmore after it"),
                         " and then the hum")      # leading space kept, trailing gone
        self.assertEqual(wire.line_of("\n \n\t\n"), "")            # nothing but blank lines
        self.assertEqual(wire.line_of(""), "")

        # and end to end: a server that opens every answer with two newlines is not mute
        srv = stub_llama.serve(0, model_path="/models/stub-para.gguf",
                               lines=["\n\nthe switch answered after all"])
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            name = fresh()
            doc = seed(name, MARK + " a paragraph opener:")
            code, out = run("--name", name, "--doc", doc, "--lines", "2", "--models",
                            f"a=para=http://127.0.0.1:{srv.server_address[1]},b=beta={URL_B}")
            self.assertEqual(code, 0, out)
            chain = spine(on_disk(name))
            self.assertEqual(chain[0]["text"], "the switch answered after all\n")
            self.assertEqual(chain[0]["meta"]["model"], "para")
            self.assertNotIn("empty_retries", chain[0]["meta"])
        finally:
            srv.shutdown()
            srv.server_close()

    # ---- the miss: an empty line, a retry, and the other model taking the turn ----------
    def test_an_empty_line_is_retried_then_the_other_model_takes_the_turn(self):
        name = fresh()
        doc = seed(name, MARK + " nobody answered:")
        code, out = run("--name", name, "--doc", doc, "--lines", "2", "--n-predict", "12",
                        "--models", f"a=mute={URL_MUTE},b=beta={URL_B}")
        self.assertEqual(code, 0, out)
        chain = spine(on_disk(name))
        self.assertEqual(len(chain), 2)
        # turn 1 was mute's: nothing, nothing, and then beta wrote it
        one = chain[0]["meta"]
        self.assertEqual(one["model"], "beta")
        self.assertEqual(one["empty_retries"], 2)
        self.assertEqual(one["swapped_from"], "mute")
        self.assertTrue(chain[0]["text"].strip())
        # turn 2 was beta's own and needed nothing
        self.assertEqual(chain[1]["meta"]["model"], "beta")
        self.assertNotIn("empty_retries", chain[1]["meta"])
        self.assertNotIn("swapped_from", chain[1]["meta"])
        self.assertIn("2 empty", out)
        self.assertIn("mute 2 empty", out)             # and the closing line counts the misses

    def test_one_empty_then_the_same_model_keeps_its_turn(self):
        # A stub scripted to miss once and answer on the retry: the swap must NOT fire, or a
        # single blank line would hand every other turn to the wrong seat.
        srv = stub_llama.serve(0, model_path="/models/stub-once.gguf",
                               lines=["", " and then it did answer"])
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            name = fresh()
            doc = seed(name, MARK + " once mute:")
            code, out = run("--name", name, "--doc", doc, "--lines", "1", "--models",
                            f"a=once=http://127.0.0.1:{srv.server_address[1]},b=beta={URL_B}")
            self.assertEqual(code, 0, out)
            meta = spine(on_disk(name))[0]["meta"]
            self.assertEqual(meta["model"], "once")
            self.assertEqual(meta["empty_retries"], 1)
            self.assertNotIn("swapped_from", meta)
        finally:
            srv.shutdown()
            srv.server_close()

    # ---- the window ---------------------------------------------------------------------
    def test_a_document_outgrowing_a_window_stops_the_chain(self):
        name = fresh()
        doc = seed(name, MARK + " the line is")            # four stub tokens
        code, out = run("--name", name, "--doc", doc, "--lines", "8", "--n-predict", "8",
                        "--models", f"a=wide={URL_A},b=narrow={URL_NARROW}")
        self.assertEqual(code, 0, out)
        self.assertIn("stop · context · narrow", out)
        self.assertIn("window is 20", out)
        d = on_disk(name)
        chain = spine(d)
        # short of the eight asked for, and the room says why, on the line the document ends on
        self.assertLess(len(chain), 8)
        self.assertGreaterEqual(len(chain), 1)
        self.assertEqual(chain[-1]["meta"]["stopped"], "context")
        for n in chain[:-1]:
            self.assertNotIn("stopped", n["meta"])
        # never truncated: every prompt the narrow server saw was the whole document
        for body in [b for b in STUB_NARROW.seen if "prompt" in b]:
            self.assertTrue(body["prompt"].startswith(MARK + " the line is"), body["prompt"][:40])

    # ---- beats: the padding that says whose turn it is ----------------------------------
    def test_beats_are_posed_lines_between_the_turns(self):
        name = fresh()
        doc = seed(name, MARK + " a beaten line:")
        bf = beats_file(name, BEATS)
        code, out = run("--name", name, "--doc", doc, "--models", MODELS(),
                        "--lines", "6", "--n-predict", "12", "--beats", bf, "--first", "a")
        self.assertEqual(code, 0, out)
        d = on_disk(name)
        chain = spine(d)
        # six lines and five beats, alternating, and the FIRST line has no beat before it: the
        # seed's own last sentence is the only introduction the opening turn gets.
        self.assertEqual([n["kind"] for n in chain],
                         ["model", "human", "model", "human", "model", "human",
                          "model", "human", "model", "human", "model"])
        self.assertEqual(models(d), ["alpha", "beta"] * 3)

        posed = [n for n in chain if n["kind"] == "human"]
        self.assertEqual(len(posed), 5)
        for n in posed:
            self.assertTrue(n["posed"])
            self.assertEqual(n["meta"], {"beat": True})
            self.assertNotIn("model", n["meta"])          # nobody wrote it; we posed it
            self.assertTrue(n["text"].startswith("\n\n") and n["text"].endswith("\n"))
        # Each beat introduces whoever speaks NEXT, out of that seat's own group, rotating and
        # wrapping: b speaks at turns 2, 4, 6 and a at 3, 5.
        self.assertEqual([n["text"] for n in posed], [
            "\n\nbefore the voice, one:\n",      # turn 2, b
            "\n\nbefore the caller, one:\n",     # turn 3, a
            "\n\nbefore the voice, two:\n",      # turn 4, b
            "\n\nbefore the caller, two:\n",     # turn 5, a
            "\n\nbefore the voice, one:\n",      # turn 6, b — wrapped
        ])
        # and the beat is in the prompt of the line under it, at the end of it
        want = d["nodes"][d["root"]]["text"]
        for n in chain:
            if n["kind"] == "model":
                body = [b for b in stub_llama.SEEN if b.get("prompt") == want]
                self.assertTrue(body, f"nobody was handed the document up to {n['id']}")
            want += n["text"]

    def test_first_says_who_opens_and_the_beats_follow(self):
        name = fresh()
        doc = seed(name, MARK + " and the voice replies:")
        bf = beats_file(name, BEATS)
        code, out = run("--name", name, "--doc", doc, "--models", MODELS(),
                        "--lines", "3", "--n-predict", "12", "--beats", bf, "--first", "b")
        self.assertEqual(code, 0, out)
        d = on_disk(name)
        chain = spine(d)
        # b opens — the seed already handed the turn to the far end, so the opening beat would
        # say it a second time — and the first beat is therefore the caller's.
        self.assertEqual(models(d), ["beta", "alpha", "beta"])
        self.assertEqual([n["text"] for n in chain if n["kind"] == "human"],
                         ["\n\nbefore the caller, one:\n", "\n\nbefore the voice, one:\n"])
        self.assertIn("b first", out)

    def test_a_beats_file_is_two_groups_and_a_comment(self):
        name = fresh()
        got = wire.read_beats(beats_file(name, BEATS))
        self.assertEqual(got, {"b": ["before the voice, one:", "before the voice, two:"],
                               "a": ["before the caller, one:", "before the caller, two:"]})
        # a run of blank lines is one separator, and the comment can sit anywhere
        got = wire.read_beats(beats_file(name + "2", "v1\n\n\n\n# a note\na1\n"))
        self.assertEqual(got, {"b": ["v1"], "a": ["a1"]})
        # one group, or three, is not a beats file: which seat each line belongs to would be a
        # guess, and a beat handed to the wrong seat makes the caller answer himself
        for bad in ("only one group\nand another line\n", "a\n\nb\n\nc\n", "# nothing but this\n"):
            with self.assertRaises(ValueError):
                wire.read_beats(beats_file(name + "3", bad))

    def test_beats_without_a_file_leave_a_bare_spine(self):
        name = fresh()
        doc = seed(name, MARK + " unpadded:")
        self.assertEqual(run("--name", name, "--doc", doc, "--models", MODELS(),
                             "--lines", "3")[0], 0)
        self.assertEqual([n["kind"] for n in spine(on_disk(name))], ["model"] * 3)

    # ---- refusals -----------------------------------------------------------------------
    def test_a_taken_name_is_a_noop(self):
        name = fresh()
        doc = seed(name, MARK + " taken:")
        self.assertEqual(run("--name", name, "--doc", doc, "--models", MODELS(),
                             "--lines", "1")[0], 0)
        with open(loom.sitting_path(name), "rb") as f:
            before = f.read()
        code, out = run("--name", name, "--doc", doc, "--models", MODELS(), "--lines", "1")
        self.assertEqual(code, 1)
        self.assertIn("already exists", out)
        with open(loom.sitting_path(name), "rb") as f:
            self.assertEqual(f.read(), before)

    def test_a_name_with_slashes_files_the_room_in_a_folder(self):
        name = f"{fresh()}/wire/chain-01"
        doc = seed(fresh(), MARK + " filed:")
        code, out = run("--name", name, "--doc", doc, "--models", MODELS(), "--lines", "2")
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.isfile(os.path.join(SHELF, *name.split("/")) + ".json"))
        self.assertEqual(on_disk(name)["name"], name)
        self.assertIn(name, [s["name"] for s in loom.shelf()])

    def test_refusals(self):
        doc = seed(fresh(), MARK + " refused:")
        bad_models = ("nourl", f"a=alpha={URL_A}", f"a=alpha={URL_A},a=beta={URL_B}",
                      f"c=alpha={URL_A},b=beta={URL_B}", f"a=alpha={URL_A},b=beta={URL_B},"
                      f"a=third={URL_A}", f"a=al pha={URL_A},b=beta={URL_B}",
                      f"a=alpha=notaurl,b=beta={URL_B}", f"a={URL_A},b={URL_B}")
        for bad in bad_models:
            self.assertEqual(run("--name", fresh(), "--doc", doc,
                                 "--models", bad, "--lines", "1")[0], 2, bad)
        for bad_name in ("../escape", "a//b", ".trash/x", "a/", "/a"):
            self.assertEqual(run("--name", bad_name, "--doc", doc,
                                 "--models", MODELS(), "--lines", "1")[0], 2, bad_name)
        self.assertEqual(run("--name", fresh(), "--doc", doc, "--models", MODELS(),
                             "--lines", "0")[0], 2)
        self.assertEqual(run("--name", fresh(), "--doc", doc, "--models", MODELS(),
                             "--lines", "1", "--temps", "a=hot")[0], 2)
        self.assertEqual(run("--name", fresh(), "--doc", doc, "--models", MODELS(),
                             "--lines", "1", "--first", "c")[0], 2)
        self.assertEqual(run("--name", fresh(), "--doc", "/nope/nothing/here",
                             "--models", MODELS(), "--lines", "1")[0], 1)
        self.assertEqual(run("--name", fresh(), "--doc", doc, "--models", MODELS(),
                             "--lines", "1", "--beats", "/nope/nothing/here")[0], 2)

    def test_a_dead_llama_stops_the_run_and_keeps_what_landed(self):
        name = fresh()
        doc = seed(name, MARK + " dead:")
        code, out = run("--name", name, "--doc", doc, "--lines", "4",
                        "--models", f"a=alpha={URL_A},b=gone=http://127.0.0.1:1")
        self.assertEqual(code, 1)
        d = on_disk(name)                                # the room exists and is valid
        self.assertEqual(len(spine(d)), 1)               # turn 1 landed, turn 2 could not


if __name__ == "__main__":
    unittest.main()
