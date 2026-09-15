#!/usr/bin/env -S uv run --python 3.12
"""evatest.py — eva.py driven by hand, against the fake llama-server.

    uv run --python 3.12 -m unittest tests/evatest.py

No pty anywhere: eva.Eva takes its input as a callable and its output as a stream, so a
test hands it a StringIO and calls `dispatch` with the lines a person would type. What is
actually under test is the file on disk — eva is a second author of the same sittings the
page writes, and the only thing that keeps them one tool is that the json comes out in the
same shape. So every test that changes the tree reads the file back and runs it through
loom.check, and the last test opens an eva-written sitting the way the page would.

The stub stands in for the 9 GB model, and it streams here — eva reads /completion as SSE.
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

TESTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS)
sys.path.insert(0, TESTS)
sys.path.insert(0, ROOT)
import stub_llama  # noqa: E402

# Before importing eva, and it has to be: loom reads LOOM_SITTINGS once, at import, and eva
# imports loom. A test run must not be able to reach a real sitting.
SHELF = tempfile.mkdtemp(prefix="eva-test-")
os.environ["LOOM_SITTINGS"] = SHELF

import eva  # noqa: E402
import loom  # noqa: E402

# …unless loom was already imported by another test module in the same run (loomtest does
# it, for the spread formula), in which case that module's env won a race this one can't
# see. Follow loom rather than argue with it: the whole point is never to touch the real
# shelf, and loom.SITTINGS is by definition the one being used.
if loom.SITTINGS != SHELF:
    shutil.rmtree(SHELF, ignore_errors=True)
    SHELF = loom.SITTINGS
    os.makedirs(SHELF, exist_ok=True)

STUB = None
EDITOR = os.path.join(SHELF, "fake_editor.py")
# The editor is a process eva shells out to, so the test provides a real one: it writes
# whatever this env var holds into the file it is given. That is enough to prove the /edit
# and /say paths without a human in a terminal.
EDITOR_SRC = "import os, sys\nopen(sys.argv[1], 'w').write(os.environ.get('EVA_TEXT', ''))\n"


def setUpModule() -> None:
    global STUB
    STUB = stub_llama.serve(0)
    threading.Thread(target=STUB.serve_forever, daemon=True).start()
    eva.LLAMA = f"http://127.0.0.1:{STUB.server_address[1]}"
    # The shelf can be gone by now: sharing it with loomtest means loomtest's teardown may
    # already have taken it away in a combined run.
    os.makedirs(SHELF, exist_ok=True)
    with open(EDITOR, "w", encoding="utf-8") as f:
        f.write(EDITOR_SRC)
    os.environ["EDITOR"] = f"{sys.executable} {EDITOR}"


def tearDownModule() -> None:
    if STUB:
        STUB.shutdown()
    shutil.rmtree(SHELF, ignore_errors=True)


def fresh(bare: bool = False) -> eva.Eva:
    ev = eva.Eva(out=io.StringIO(), read=lambda p: "", colour=False)
    assert ev.new(f"t{uuid.uuid4().hex[:8]}", bare), ev.out.getvalue()
    return ev


def on_disk(ev: eva.Eva) -> dict:
    """The sitting as the next process would read it — never the object in memory."""
    with open(os.path.join(SHELF, ev.sitting["name"] + ".json"), encoding="utf-8") as f:
        d = json.load(f)
    assert loom.check(d) == "", loom.check(d)
    return d


def screen(ev: eva.Eva) -> str:
    return ev.out.getvalue()


class NewSitting(unittest.TestCase):
    def test_chat_shape(self):
        ev = fresh()
        d = on_disk(ev)
        self.assertEqual(sorted(d), ["created", "current", "name", "nodes", "params",
                                     "root", "turn", "updated"])
        self.assertEqual(d["turn"], eva.TURN)
        self.assertEqual(d["params"]["stop"], ["\nbekh:", "\nbekh :", "\n\nbekh"])
        self.assertEqual(d["params"]["fan"], 4)
        self.assertEqual(d["params"]["dry_penalty_last_n"], 8192)
        root = d["nodes"][d["root"]]
        self.assertEqual(sorted(root), ["id", "kind", "meta", "parent", "posed", "pruned",
                                        "text", "ts"])
        self.assertEqual(root["kind"], "root")
        self.assertEqual(root["text"], eva.HEADER)
        self.assertIsNone(root["parent"])
        self.assertEqual(d["current"], d["root"])
        self.assertEqual(len(d["root"]), 8)
        # the document, and nothing framing it
        self.assertIn(eva.HEADER.strip(), screen(ev))

    def test_bare_shape(self):
        ev = fresh(bare=True)
        d = on_disk(ev)
        self.assertEqual(d["turn"], {"prefix": "", "suffix": ""})
        self.assertEqual(d["params"]["stop"], [])
        self.assertEqual(d["nodes"][d["root"]]["text"], "")
        self.assertTrue(ev.bare())
        self.assertEqual(ev.prompt(), "› ")

    def test_taken_name_is_a_noop(self):
        first = fresh()
        name = first.sitting["name"]
        path = os.path.join(SHELF, name + ".json")
        with open(path, "rb") as f:
            before = f.read()
        ev = eva.Eva(out=io.StringIO(), colour=False)
        self.assertFalse(ev.new(name))
        self.assertFalse(ev.new(name, True))
        self.assertIsNone(ev.sitting)
        self.assertIn("already exists", screen(ev))
        with open(path, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_bad_name(self):
        ev = eva.Eva(out=io.StringIO(), colour=False)
        self.assertFalse(ev.new("../escape"))
        self.assertIsNone(ev.sitting)
        self.assertIn("names are letters", screen(ev))


class LineAndFan(unittest.TestCase):
    def test_line_then_fan(self):
        ev = fresh()
        ev.dispatch("you up")
        d = on_disk(ev)

        human = d["nodes"][d["current"]]
        self.assertEqual(human["kind"], "human")
        self.assertEqual(human["text"], "\nbekh: you up\nseat:")
        self.assertEqual(human["parent"], d["root"])
        self.assertFalse(human["posed"])

        kids = [n for n in d["nodes"].values() if n["parent"] == d["current"]]
        self.assertEqual(len(kids), 4)                      # params.fan
        self.assertGreater(len({k["text"] for k in kids}), 1)   # a fan of one line is not a fan
        for k in kids:
            self.assertEqual(k["kind"], "model")
            self.assertEqual(sorted(k["meta"]), ["params", "probs", "stop_type",
                                                 "stopping_word", "tokens_predicted", "tps"])
            self.assertEqual(k["meta"]["stop_type"], "word")
            self.assertEqual(k["meta"]["stopping_word"], "\nbekh:")
            self.assertNotIn("\nbekh:", k["text"])          # llama ate it; the prefix puts it back
            self.assertGreater(k["meta"]["tokens_predicted"], 0)
            self.assertGreater(k["meta"]["tps"], 0)
            self.assertEqual(k["meta"]["params"]["temperature"], 1.0)
        # the prompt the model saw is the path, verbatim
        self.assertEqual(ev.prompt_from(human["id"]), eva.HEADER + "\nbekh: you up\nseat:")

        out = screen(ev)
        self.assertIn("seat:", out)
        for k in kids:                                      # streamed, so the text is on screen
            self.assertIn(k["text"].strip()[:20], out)

    def test_meta_params_are_frozen(self):
        ev = fresh()
        ev.dispatch("/set fan 1")
        ev.dispatch("you up")
        node = [n for n in ev.sitting["nodes"].values() if n["kind"] == "model"][0]
        ev.dispatch("/set temperature 0.2")
        self.assertEqual(ev.sitting["params"]["temperature"], 0.2)
        self.assertEqual(on_disk(ev)["nodes"][node["id"]]["meta"]["params"]["temperature"], 1.0)

    def test_empty_enter_adds_more(self):
        ev = fresh()
        ev.dispatch("/set fan 2")
        ev.dispatch("you up")
        here = ev.sitting["current"]
        self.assertEqual(len(ev.kids(here)), 2)
        ev.out = io.StringIO()
        ev.dispatch("")
        self.assertEqual(len(ev.kids(here)), 4)
        self.assertEqual(len(on_disk(ev)["nodes"]), 6)      # root + human + four branches
        # the numbering keeps climbing instead of starting over at 1
        self.assertIn("  3  ", screen(ev))
        self.assertIn("  4  ", screen(ev))

    def test_ctrl_c_keeps_what_landed_and_drops_the_half(self):
        ev = fresh()
        ev.dispatch("/set fan 3")
        ev.dispatch("you up")
        here = ev.sitting["current"]
        self.assertEqual(len(ev.kids(here)), 3)

        real, seen = eva.complete_stream, {"n": 0}

        def interrupted(prompt, params, on_chunk):
            seen["n"] += 1
            if seen["n"] == 2:
                on_chunk(" half a line")      # on the screen, then the hand goes to ^C
                raise KeyboardInterrupt
            return real(prompt, params, on_chunk)

        eva.complete_stream = interrupted
        ev.out = io.StringIO()
        try:
            ev.dispatch("")                   # a fan of three, cut on the second
        finally:
            eva.complete_stream = real

        out = screen(ev)
        self.assertIn("half a line", out)     # it was streamed, so it stays on the screen
        self.assertIn("── cut ──", out)
        kids = ev.kids(here)
        self.assertEqual(len(kids), 4)        # the three from before plus the one that landed
        self.assertNotIn(" half a line", [k["text"] for k in kids])
        self.assertEqual(len(on_disk(ev)["nodes"]), 6)

    def test_llama_down_is_one_line(self):
        ev = fresh()
        ev.dispatch("/set fan 1")
        was, eva.LLAMA = eva.LLAMA, "http://127.0.0.1:1"   # nothing listens on port 1
        try:
            ev.out = io.StringIO()
            ev.dispatch("anyone there")
        finally:
            eva.LLAMA = was
        self.assertIn("unreachable", screen(ev))
        self.assertEqual([n for n in ev.sitting["nodes"].values() if n["kind"] == "model"], [])
        on_disk(ev)     # the human line is still saved and the file is still a sitting


class SpreadAndProbabilities(unittest.TestCase):
    def test_fan_steps_the_temperature(self):
        ev = fresh()
        ev.dispatch("/set fan 4")
        ev.dispatch("/set spread 0.5")
        ev.dispatch("EVASPREADMARK")
        kids = ev.kids(ev.sitting["current"])
        self.assertEqual([k["meta"]["params"]["temperature"] for k in kids],
                         [0.5, 0.8333, 1.1667, 1.5])
        wire = [b for b in stub_llama.SEEN if "EVASPREADMARK" in (b.get("prompt") or "")]
        self.assertEqual([b["temperature"] for b in wire], [0.5, 0.8333, 1.1667, 1.5])
        for b in wire:                      # llama never sees the loom's own keys
            for k in ("fan", "spread", "dry_keep"):
                self.assertNotIn(k, b)

    def test_streamed_probabilities_are_collected_token_by_token(self):
        ev = fresh()
        ev.dispatch("/set fan 1")
        ev.dispatch("EVAPROBMARK")
        node = ev.kids(ev.sitting["current"])[0]
        probs = on_disk(ev)["nodes"][node["id"]]["meta"]["probs"]
        # Nothing rides on the final streamed event, so this is the whole test: if the
        # partials were not being read, `probs` would be empty, not short.
        self.assertEqual("".join(p["token"] for p in probs), node["text"])
        self.assertNotIn("bytes", probs[0])
        self.assertEqual(len(probs[0]["top_logprobs"]), 5)

    def test_old_rooms_get_the_new_keys_on_open(self):
        ev = fresh()
        name = ev.sitting["name"]
        for k in ("spread", "n_probs", "logit_bias", "dry_keep"):
            del ev.sitting["params"][k]
        ev.sitting["params"]["temperature"] = 0.7       # his own value, not to be touched
        ev.save()
        again = eva.Eva(out=io.StringIO(), colour=False)
        self.assertTrue(again.open(name))
        self.assertEqual(again.sitting["params"]["spread"], 0)
        self.assertEqual(again.sitting["params"]["n_probs"], 5)
        self.assertEqual(again.sitting["params"]["temperature"], 0.7)
        again.dispatch("/set spread 0.4")               # and /set can now see them
        self.assertEqual(on_disk(again)["params"]["spread"], 0.4)


class Walking(unittest.TestCase):
    def setUp(self):
        self.ev = fresh()
        self.ev.dispatch("/set fan 3")
        self.ev.dispatch("you up")
        self.at = self.ev.sitting["current"]

    def test_pick_moves_current(self):
        want = self.ev.kids(self.at)[1]
        self.ev.out = io.StringIO()
        self.ev.dispatch("2")
        self.assertEqual(self.ev.sitting["current"], want["id"])
        self.assertEqual(on_disk(self.ev)["current"], want["id"])
        # reprinted once, as the real line, so the scrollback stays a transcript
        self.assertIn("seat:" + want["text"].rstrip()[:12], screen(self.ev).replace("\n", ""))

    def test_bad_number(self):
        self.ev.out = io.StringIO()
        self.ev.dispatch("9")
        self.assertIn("no candidate 9", screen(self.ev))
        self.assertEqual(self.ev.sitting["current"], self.at)

    def test_back_relists(self):
        came = self.ev.kids(self.at)[0]
        self.ev.dispatch("1")
        self.ev.out = io.StringIO()
        self.ev.dispatch("/back")
        self.assertEqual(self.ev.sitting["current"], self.at)
        self.assertEqual(on_disk(self.ev)["current"], self.at)
        out = screen(self.ev)
        self.assertIn("── back ──", out)
        self.assertIn("bekh: you up", out)              # the parent's line, reprinted
        # the marker, then the text VERBATIM — the space a model's line opens with is text
        self.assertIn("* 1  " + came["text"][:8], out)
        self.assertNotIn("* 1  " + came["text"].lstrip()[:8], out)
        self.assertIn("  2  ", out)

    def test_back_at_the_root(self):
        self.ev.dispatch("/back")                        # off the human line, onto the root
        self.ev.out = io.StringIO()
        self.ev.dispatch("/back")
        self.assertIn("already at the root", screen(self.ev))

    def test_prune_hides_never_deletes(self):
        drop = self.ev.kids(self.at)[1]
        self.ev.dispatch("/prune 2")
        self.assertEqual(len(self.ev.kids(self.at)), 2)
        d = on_disk(self.ev)
        self.assertIn(drop["id"], d["nodes"])
        self.assertTrue(d["nodes"][drop["id"]]["pruned"])

    def test_prune_here_steps_back(self):
        keep = self.ev.kids(self.at)[0]
        self.ev.dispatch("1")
        self.ev.dispatch("/prune")
        self.assertEqual(self.ev.sitting["current"], self.at)
        self.assertTrue(on_disk(self.ev)["nodes"][keep["id"]]["pruned"])
        self.assertEqual(len(self.ev.kids(self.at)), 2)


class Editing(unittest.TestCase):
    def test_edit_a_candidate_is_posed_forever(self):
        ev = fresh()
        ev.dispatch("/set fan 1")
        ev.dispatch("say something")
        model = ev.kids(ev.sitting["current"])[0]
        self.assertFalse(model["posed"])
        os.environ["EVA_TEXT"] = " nah"
        ev.out = io.StringIO()
        ev.dispatch("/edit 1")
        d = on_disk(ev)
        self.assertEqual(d["nodes"][model["id"]]["text"], " nah")
        self.assertTrue(d["nodes"][model["id"]]["posed"])
        self.assertIn("posed", screen(ev))

    def test_edit_the_root_is_not_posed(self):
        ev = fresh()
        os.environ["EVA_TEXT"] = "two people, one of them is not sure it is awake.\n"
        ev.dispatch("/edit")
        d = on_disk(ev)
        self.assertEqual(d["nodes"][d["root"]]["text"], "two people, one of them is not sure it is awake.\n")
        self.assertFalse(d["nodes"][d["root"]]["posed"])   # his own words never get the tag

    def test_edit_unchanged_says_so(self):
        ev = fresh()
        os.environ["EVA_TEXT"] = eva.HEADER
        ev.out = io.StringIO()
        ev.dispatch("/edit")
        self.assertIn("unchanged", screen(ev))

    def test_say_is_one_human_node_then_a_fan(self):
        ev = fresh()
        ev.dispatch("/set fan 1")
        os.environ["EVA_TEXT"] = "\nfirst line\nsecond line\n\n"
        ev.dispatch("/say")
        node = ev.node(ev.sitting["current"])
        # trimmed of the OUTER newlines only: the one inside the block is his
        self.assertEqual(node["text"], "\nbekh: first line\nsecond line\nseat:")
        self.assertEqual(len(ev.kids(node["id"])), 1)

    def test_seed_goes_in_verbatim_and_does_not_fan(self):
        ev = fresh()
        block = "\nbekh: you up\nseat: mm\nbekh: ok\nseat:"
        os.environ["EVA_TEXT"] = block
        ev.dispatch("/seed")
        node = ev.node(ev.sitting["current"])
        self.assertEqual(node["text"], block)       # no prefix wrapped round a pasted room
        self.assertEqual(ev.kids(node["id"]), [])
        self.assertEqual(ev.prompt_from(node["id"]), eva.HEADER + block)
        on_disk(ev)


class Curation(unittest.TestCase):
    """janus's measure, on trees built by hand so the arithmetic is checkable."""

    def test_a_picked_branch_costs_log2_of_its_fan(self):
        ev = fresh()
        ev.sitting["nodes"] = {}
        root = ev.add_node("root", "", None)
        ev.sitting["root"] = ev.sitting["current"] = root["id"]
        kids = [ev.add_node("model", "x" * 40, root["id"]) for _ in range(4)]
        ev.sitting["current"] = kids[0]["id"]
        c = eva.curation(ev.sitting)
        # one of four kept, and an empty root costs nothing
        self.assertEqual(c["bits"], 2.0)
        self.assertEqual(c["picks"], 1)
        self.assertEqual(c["tokens"], 10)           # 40 chars, four to a token

    def test_pruned_branches_still_count_as_produced(self):
        ev = fresh()
        ev.sitting["nodes"] = {}
        root = ev.add_node("root", "", None)
        ev.sitting["root"] = root["id"]
        kids = [ev.add_node("model", "x" * 4, root["id"]) for _ in range(8)]
        for k in kids[1:]:
            k["pruned"] = True
        ev.sitting["current"] = kids[0]["id"]
        self.assertEqual(eva.curation(ev.sitting)["bits"], 3.0)      # log2(8/1)

    def test_two_kept_out_of_four_is_one_bit(self):
        ev = fresh()
        ev.sitting["nodes"] = {}
        root = ev.add_node("root", "", None)
        ev.sitting["root"] = root["id"]
        kids = [ev.add_node("model", "x" * 4, root["id"]) for _ in range(4)]
        ev.add_node("human", "", kids[1]["id"])     # continued, so it was kept too
        ev.sitting["current"] = kids[0]["id"]
        self.assertEqual(eva.curation(ev.sitting)["bits"], 1.0)      # log2(4/2)

    def test_typed_and_posed_lines_cost_their_tokens(self):
        ev = fresh()
        ev.sitting["nodes"] = {}
        root = ev.add_node("root", "", None)
        ev.sitting["root"] = root["id"]
        h = ev.add_node("human", "y" * 20, root["id"])
        m = ev.add_node("model", "z" * 40, h["id"])
        m["posed"] = True                            # he wrote it, whatever it says
        ev.sitting["current"] = m["id"]
        c = eva.curation(ev.sitting)
        self.assertEqual(c["bits"], 5 + 10)
        self.assertEqual(c["picks"], 2)

    def test_the_line_reads_and_doc_prints_it(self):
        ev = fresh()
        ev.dispatch("/set fan 4")
        ev.dispatch("you up")
        ev.dispatch("1")
        line = eva.curation_line(ev.sitting)
        self.assertTrue(line.startswith("curation: "))
        self.assertIn("bits/token", line)
        ev.out = io.StringIO()
        ev.dispatch("/doc")
        self.assertIn("curation: ", screen(ev))


class SpinOff(unittest.TestCase):
    def test_the_document_so_far_becomes_a_bare_room(self):
        ev = fresh()
        ev.dispatch("/set fan 1")
        ev.dispatch("/set temperature 1.3")
        ev.dispatch("you up")
        ev.dispatch("1")
        was = ev.sitting["name"]
        doc = ev.prompt_from(ev.sitting["current"])

        name = "spun" + uuid.uuid4().hex[:6]
        ev.dispatch("/spin " + name)
        self.assertEqual(ev.sitting["name"], name)
        d = on_disk(ev)
        # nothing stripped: header, names, colons, the branch — exactly what the model read
        self.assertEqual(d["nodes"][d["root"]]["text"], doc)
        self.assertEqual(d["turn"], {"prefix": "", "suffix": ""})
        self.assertEqual(d["params"]["stop"], [])
        self.assertEqual(d["params"]["temperature"], 1.3)      # the heat comes with it
        self.assertEqual(d["title"], "spun off from " + was)
        self.assertEqual(len(d["nodes"]), 1)
        # and it continues from there, with nothing inserted between the two
        ev.dispatch("")
        kid = [n for n in ev.sitting["nodes"].values() if n["kind"] == "model"][0]
        wire = [b for b in stub_llama.SEEN if b.get("prompt") == doc]
        self.assertTrue(wire)
        self.assertEqual(ev.prompt_from(kid["id"]), doc + kid["text"])

    def test_blank_name_and_a_taken_one(self):
        ev = fresh()
        ev.dispatch("/spin")
        self.assertRegex(ev.sitting["name"], r"^[0-9a-f]{8}$")
        taken = ev.sitting["name"]
        ev.out = io.StringIO()
        ev.dispatch("/spin " + taken)
        self.assertIn("already exists", screen(ev))
        self.assertEqual(ev.sitting["name"], taken)            # still standing where it was


class Bare(unittest.TestCase):
    def test_whitespace_is_text(self):
        ev = fresh(bare=True)
        ev.dispatch("/set fan 1")
        ev.dispatch("  the door was  ")
        node = ev.node(ev.sitting["current"])
        self.assertEqual(node["text"], "  the door was  ")      # not stripped, either end
        self.assertEqual(ev.prompt_from(node["id"]), "  the door was  ")
        d = on_disk(ev)
        self.assertEqual(d["params"]["stop"], [])
        kid = [n for n in d["nodes"].values() if n["kind"] == "model"][0]
        # no stop strings: the branch runs to n_predict, which is what continuation is
        self.assertEqual(kid["meta"]["stop_type"], "limit")


class Settings(unittest.TestCase):
    def test_set_reads_and_writes(self):
        ev = fresh()
        ev.out = io.StringIO()
        ev.dispatch("/set")
        out = screen(ev)
        self.assertIn("temperature = 1.0", out)
        self.assertIn(r"prefix = '\nbekh: '", out)          # repr, so the newline is visible

        ev.dispatch("/set temperature 0.85")
        ev.dispatch("/set top_k 40")
        ev.dispatch("/set stop ['\\nyou:']")
        ev.dispatch("/set prefix \\nyou: ")
        d = on_disk(ev)
        self.assertEqual(d["params"]["temperature"], 0.85)
        self.assertEqual(d["params"]["top_k"], 40)
        self.assertIsInstance(d["params"]["top_k"], int)
        self.assertEqual(d["params"]["stop"], ["\nyou:"])
        self.assertEqual(d["turn"]["prefix"], "\nyou:")
        self.assertEqual(ev.prompt(), "you: ")              # the prompt IS the prefix, trimmed

    def test_set_float_on_a_page_written_int(self):
        # The browser's json writes `temperature: 1`, not `1.0`; a coercion that follows
        # the stored type would refuse 0.9 on every sitting the page made.
        ev = fresh()
        ev.out = io.StringIO()
        ev.sitting["params"]["temperature"] = 1
        ev.sitting["params"]["top_p"] = 1
        ev.dispatch("/set temperature 0.9")
        ev.dispatch("/set top_p 0.95")
        ev.dispatch("/set top_k 40")
        d = on_disk(ev)
        self.assertEqual(d["params"]["temperature"], 0.9)
        self.assertEqual(d["params"]["top_p"], 0.95)
        self.assertIsInstance(d["params"]["top_k"], int)
        self.assertNotIn("bad value", screen(ev))

    def test_set_logit_bias_and_dry_off(self):
        ev = fresh()
        ev.out = io.StringIO()
        ev.dispatch("/set logit_bias [[' the', -2], [1234, -100]]")
        ev.dispatch("/set dry_multiplier 0")
        d = on_disk(ev)
        self.assertEqual(d["params"]["logit_bias"], [[" the", -2], [1234, -100]])
        self.assertEqual(d["params"]["dry_multiplier"], 0)
        ev.dispatch("/set logit_bias ['the', -2]")      # not a list of pairs
        self.assertIn("bad value for logit_bias", screen(ev))
        self.assertEqual(ev.sitting["params"]["logit_bias"], [[" the", -2], [1234, -100]])

    def test_set_refuses_nonsense(self):
        ev = fresh()
        ev.out = io.StringIO()
        ev.dispatch("/set temperature hot")
        ev.dispatch("/set nosuchthing 3")
        out = screen(ev)
        self.assertIn("bad value for temperature", out)
        self.assertIn("no such param", out)
        self.assertEqual(ev.sitting["params"]["temperature"], 1.0)


class Shelf(unittest.TestCase):
    def test_reopen_and_shelf(self):
        ev = fresh()
        ev.dispatch("/set fan 1")
        ev.dispatch("you up")
        ev.dispatch("1")
        name, at = ev.sitting["name"], ev.sitting["current"]

        card = next(s for s in loom.shelf() if s["name"] == name)
        self.assertEqual(card["nodes"], len(ev.sitting["nodes"]))
        self.assertGreater(card["updated"], 0)

        again = eva.Eva(out=io.StringIO(), colour=False)
        self.assertTrue(again.open(name))
        self.assertEqual(again.sitting["current"], at)
        self.assertEqual(again.sitting["nodes"], ev.sitting["nodes"])
        # what it prints on open is the document, verbatim
        self.assertIn(ev.prompt_from(at), screen(again))

    def test_unknown_command_lists_them(self):
        ev = fresh()
        ev.out = io.StringIO()
        ev.dispatch("/nope")
        self.assertIn("/back", screen(ev))

    def test_open_missing(self):
        ev = eva.Eva(out=io.StringIO(), colour=False)
        self.assertFalse(ev.open("nobody-home"))
        self.assertIn("no sitting called", screen(ev))


if __name__ == "__main__":
    unittest.main()
