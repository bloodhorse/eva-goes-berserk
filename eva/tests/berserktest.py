#!/usr/bin/env -S uv run --python 3.12
"""berserktest.py — berserk walked end to end, with a fake llama and a fake resolver.

    uv run --python 3.12 -m unittest discover -s eva/tests -p '*test.py'

Nothing inside berserk.py is mocked: a real berserk.py runs as a subprocess against the same
stub llama-server the loom's tests use, and against a **fake `claude`** — a short script put
first on PATH that reads the prompt off stdin, files it away, and answers the one json the
blind resolver is asked for. Those are the two seams worth faking, and both of them are a
subprocess with text going in and text coming out, where everything breaks silently.

One class per picker, because they fail differently: `About` (the default — the reader
describes and only the resolver can say which branch that was), `Margin` (a note per branch,
one pick over the notes, no fan reading at all) and `Quoted` (the reader quotes, and the
answer can be checked against the text). Plus the ways each one goes wrong: a resolver that
answers prose, a reader that names branches nobody drew, and margin with nobody to read.

The stub's `READER_MODE` is what makes any of it testable. berserk asks the model a second
question at every fork and expects the answer to come **out of its own prompt**; a stub
answering its usual random line would only ever exercise the failure path. `"quote"` means
the stub cooperates with all three frames, `"garbage"` answers a sentence that is in no branch
(nothing ever resolves, every fork ends random, the wished pile fills up). The fake claude has
a garbage mode of its own, for the run where the resolver is the thing that is broken.

Scratch everything: LOOM_SITTINGS / LOOM_ARTIFACTS, BERSERK_DIR, BERSERK_SEEDS. The sheets
host and the ntfy topic are set to the empty string, which berserk reads as "post nowhere" —
a test run must never scp to the mini or push to bekh's phone.
"""

from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
EVA = os.path.dirname(TESTS)                      # eva/: server/ has loom, berserk/ the daemon
for d in (TESTS, os.path.join(EVA, "server")):
    sys.path.insert(0, d)
import stub_llama  # noqa: E402

SHELF = tempfile.mkdtemp(prefix="berserk-sittings-")
ARTS = tempfile.mkdtemp(prefix="berserk-arts-")
os.environ["LOOM_SITTINGS"] = SHELF
os.environ["LOOM_ARTIFACTS"] = ARTS
import loom  # noqa: E402 — after the env, which loom reads once at import

# berserk itself, imported for the matcher's unit tests. BERSERK_DIR first, because the
# module resolves it at import and an unset one points at the real shelf — nothing is
# written by importing, but a test file that names the real shelf at all is a test file one
# edit away from writing to it.
IMPORT_DIR = tempfile.mkdtemp(prefix="berserk-import-")
os.environ["BERSERK_DIR"] = IMPORT_DIR
sys.path.insert(0, os.path.join(EVA, "berserk"))
import berserk  # noqa: E402

# One paragraph, on purpose: the reader document has no markers in it, so the stub finds the
# branches by taking every paragraph between the document's tail and the ask line. A seed
# with a blank line in it would put half of itself in the branch pool and the stub would
# quote the document back at berserk, which is a stub bug that would read as a matcher bug.
SEED = ("Municipal Lifts Office, acceptance tests following the removal of a floor.\n"
        "Test 3. Same load, with a hat placed on the upper sack. Stopped between third "
        "and fifth.\n")

# berserk's default ask line, restated as a literal: it is the only human contribution to the
# loop's taste, and if somebody edits it this test should fail and a human should read why.
ASK_TAIL = "was the one that began: “"

STUB = None
STUB_BASE = ""
REAL_LINES = None
REAL_MODE = ""
REAL_DIRS: tuple = ()


class UniqueLines:
    """A stand-in for the stub's LINES that never hands out the same branch twice.
    `random.choice` reads it as a sequence; what it actually does is count.

    Two identical branches in one fan are a real thing — they drop out of the artifact's bit
    pool as twins, and a quotation that begins both of them is a tie and therefore no match.
    Both are worth testing; neither is worth testing one run in twenty at random, which is
    what `random.choice` over a fixed list gives you.
    """

    def __init__(self) -> None:
        self.n = 0

    def __len__(self) -> int:
        return 60

    def __getitem__(self, i: int) -> str:
        self.n += 1
        return f" and entry {self.n} of the {i}th sack was recorded without remark"


# The blind resolver, faked — one script for all three of the questions berserk asks it,
# told apart the same way the real opus would tell them apart: by the question at the top.
# A quotation is resolved by "which fragment starts with this", a description by word
# overlap (a blind resolver has nothing else to go on), and the margin's "most pronounced"
# by the longest note, ties to the lowest number. GARBAGE mode answers prose instead, twice,
# which is the 4am failure the daemon is built to fall back from.
FAKE_CLAUDE = '''#!/usr/bin/env python3
import os, re, sys
prompt = sys.stdin.read()
log = os.environ.get("FAKE_CLAUDE_LOG")
if log:
    with open(log, "a", encoding="utf-8") as f:
        f.write("\\n===PROMPT===\\n" + prompt)
if os.environ.get("FAKE_CLAUDE_MODE") == "garbage":
    print("Sure! Here is my thinking about the fragments. I liked number three a lot.")
    sys.exit(0)
items, said = [], ""
for line in prompt.splitlines():
    m = re.match(r"^(\\d+)\\. (.*)$", line)
    if m:
        items.append((int(m.group(1)), m.group(2)))
    for tag in ("quotation: ", "description: "):
        if line.startswith(tag):
            said = line[len(tag):].strip()
answer = "null"
if "most pronounced" in prompt:
    if items:
        answer = str(max(items, key=lambda it: (len(it[1]), -it[0]))[0])
elif "is this describing" in prompt:
    want = set(said.lower().split())
    if items and want:
        answer = str(max(items, key=lambda it: (len(want & set(it[1].lower().split())),
                                                -it[0]))[0])
else:
    for i, text in items:
        if said and text.startswith(said):
            answer = str(i)
            break
print('{"index": %s}' % answer)
'''


def setUpModule() -> None:
    global STUB, STUB_BASE, REAL_LINES, REAL_MODE, REAL_DIRS
    # loom reads LOOM_SITTINGS and LOOM_ARTIFACTS ONCE, at import, so when the whole suite
    # runs in one process loomtest has already imported it and pointed it at its own scratch
    # shelf. Repointed here and not at import: at import time this would fire during
    # collection, before the other files' tests run, and move the shelf out from under them.
    REAL_DIRS = (loom.SITTINGS, loom.ARTIFACTS)
    loom.SITTINGS, loom.ARTIFACTS = SHELF, ARTS
    REAL_LINES, REAL_MODE = stub_llama.LINES, stub_llama.READER_MODE
    stub_llama.LINES = UniqueLines()
    STUB = stub_llama.serve(0)
    threading.Thread(target=STUB.serve_forever, daemon=True).start()
    STUB_BASE = f"http://127.0.0.1:{STUB.server_address[1]}"


def tearDownModule() -> None:
    # The stub is a module, one per process, shared with every other test file in the suite.
    if REAL_LINES is not None:
        stub_llama.LINES = REAL_LINES
    stub_llama.READER_MODE = REAL_MODE
    if REAL_DIRS:
        loom.SITTINGS, loom.ARTIFACTS = REAL_DIRS
    if STUB:
        STUB.shutdown()
    for d in (SHELF, ARTS, IMPORT_DIR):
        shutil.rmtree(d, ignore_errors=True)


def scratch(mode: str = "") -> dict:
    """A whole world for one run: a bin holding the fake claude, a seeds dir with one seed,
    a berserk dir, and the env that points berserk.py at all of it."""
    d = tempfile.mkdtemp(prefix="berserk-run-")
    binp, seeds = os.path.join(d, "bin"), os.path.join(d, "seeds")
    os.makedirs(binp)
    os.makedirs(seeds)
    with open(os.path.join(seeds, "lift-tests.txt"), "w", encoding="utf-8") as f:
        f.write(SEED)
    fake = os.path.join(binp, "claude")
    with open(fake, "w", encoding="utf-8") as f:
        f.write(FAKE_CLAUDE.replace("#!/usr/bin/env python3", "#!" + sys.executable))
    os.chmod(fake, 0o755)
    log = os.path.join(d, "prompts.txt")
    env = dict(os.environ,
               PATH=binp + os.pathsep + os.environ.get("PATH", ""),
               LOOM_SITTINGS=SHELF, LOOM_ARTIFACTS=ARTS, LOOM_LLAMA=STUB_BASE,
               BERSERK_DIR=os.path.join(d, "berserk"), BERSERK_SEEDS=seeds,
               BERSERK_SHEETS_HOST="", BERSERK_NTFY="",
               FAKE_CLAUDE_LOG=log, FAKE_CLAUDE_MODE=mode)
    return {"dir": d, "env": env, "log": log, "berserk": os.path.join(d, "berserk")}


def run(env: dict, *args, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, os.path.join(EVA, "berserk", "berserk.py"), *args],
                          env=env, capture_output=True, text=True, timeout=timeout)


def html_escape(s: str) -> str:
    """Exactly what the page does to a branch or a note before it prints it. Asserting on
    the raw string would pass today and fail the first time a model writes an ampersand."""
    return html.escape(s)


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def rows(berserk: str) -> list[dict]:
    return [json.loads(line) for line in read(os.path.join(berserk, "ledger.jsonl")).splitlines()
            if line.strip()]


def forks_of(berserk: str) -> list[dict]:
    return [r for r in rows(berserk) if r.get("event") is None]


def reader_bodies(tail: str = ASK_TAIL) -> list[dict]:
    """Every request one of the readers made, off the stub's SEEN list. The frame line is
    the tell: nothing else in the suite ends a prompt that way, and asserting on the saved
    node would only prove berserk copied its own number into meta."""
    return [b for b in stub_llama.SEEN if (b.get("prompt") or "").endswith(tail)]


def cleanup(*rooms: str) -> None:
    for room in rooms:
        for p in (loom.sitting_path(room), loom.artifact_path(room)):
            if os.path.exists(p):
                os.unlink(p)


def overlap(a: str, b: str) -> int:
    return len(set(a.lower().split()) & set(b.lower().split()))


class SomeEmpty(UniqueLines):
    """UniqueLines, but every third branch comes back empty.

    That is not a contrived case: a real walk that drifts onto a licence footer gets fans
    where half the branches are the empty string, because the model has nothing to add
    there — cycle 81's second page drew 18 empty branches out of 30. A note is still written
    beside each of them, and the anthology still has to show that note something to sit under.
    """

    def __getitem__(self, i: int) -> str:
        self.n += 1
        if self.n % 3 == 0:
            return ""
        return f" and entry {self.n} of the {i}th sack was recorded without remark"


class Anthology(unittest.TestCase):
    """A margin cycle rendered as one page of reactions. Its own run, not Margin's: a test
    that reads another class's scratch dir is a test that depends on the order they load in."""

    @classmethod
    def setUpClass(cls) -> None:
        stub_llama.READER_MODE = "quote"
        cls.real_lines = stub_llama.LINES
        stub_llama.LINES = SomeEmpty()
        cls.s = scratch()
        cls.r = run(cls.s["env"], "cycle", "--cycle", "8", "--pages", "1", "--forks", "1",
                    "--fan", "4", "--picker", "margin")
        cls.a = subprocess.run(
            [sys.executable, os.path.join(EVA, "berserk", "anthology.py"),
             "--cycles", "8", "--no-push"],
            env=cls.s["env"], capture_output=True, text=True, timeout=120)
        cls.page = os.path.join(cls.s["berserk"], "pages", "berserk-c08.html")
        cls.room = "berserk-c08-p01"

    @classmethod
    def tearDownClass(cls) -> None:
        stub_llama.READER_MODE = ""
        stub_llama.LINES = cls.real_lines
        shutil.rmtree(cls.s["dir"], ignore_errors=True)
        cleanup(cls.room)

    def html(self) -> str:
        return read(self.page)

    def test_it_rendered_and_explains_itself(self) -> None:
        self.assertEqual(self.r.returncode, 0, self.r.stderr[-2000:])
        self.assertEqual(self.a.returncode, 0, self.a.stderr[-2000:])
        self.assertTrue(os.path.isfile(self.page))
        page = self.html()
        self.assertIn("background:#111", page, "the sheets skin")
        self.assertIn("No person picks a branch", page, "the experiment, explained up top")
        self.assertIn("<strong>margin</strong>", page, "the picker under test, described")
        self.assertIn(berserk.NOTE_MARGIN, page, "the frame line, verbatim")
        self.assertIn("tokens a branch", page, "the settings the run really used")
        self.assertIn(self.room, page)

    def test_every_note_is_on_the_page(self) -> None:
        page = self.html()
        n = 0
        for r in forks_of(self.s["berserk"]):
            for note in r["notes"]:
                self.assertIn(html_escape(note), page, note)
                n += 1
        self.assertGreaterEqual(n, 8, "four branches at each of two forks")

    def test_one_branch_is_marked_taken_per_fork(self) -> None:
        # The mark's own span, not the bare word: the page explains the word up top too.
        forks = forks_of(self.s["berserk"])
        page = self.html()
        self.assertEqual(page.count('class="mark">taken<'), len(forks))
        self.assertEqual(page.count('class="card taken"'), len(forks))

    def test_an_empty_branch_is_named_so_its_note_has_a_seat(self) -> None:
        page = self.html()
        s = json.loads(read(loom.sitting_path(self.room)))
        empties = sum(1 for r in forks_of(self.s["berserk"]) for i in r["order"]
                      if not s["nodes"][i]["text"].strip())
        self.assertGreater(empties, 0, "the stub was supposed to draw empty branches")
        self.assertEqual(page.count("(empty branch)"), empties)

    def test_the_lead_says_what_the_branches_are_finishing(self) -> None:
        # A lead is only there when the document stands mid-line, which depends on what the
        # walk took — with empty branches in the fan it may not. Every lead there IS has to
        # be on the page, though: it is the only thing that makes a fan of fragments read.
        page, seen = self.html(), 0
        s = json.loads(read(loom.sitting_path(self.room)))
        for r in forks_of(self.s["berserk"]):
            parent = s["nodes"][r["order"][0]]["parent"]
            lead = berserk.lead_of(berserk.prompt_to(s, parent))
            if lead:
                self.assertIn(html_escape(lead), page)
                seen += 1
        self.assertIn("every branch below finishes", page) if seen else None

    def test_branches_are_printed_whole_and_the_seed_once(self) -> None:
        # Nothing is cut to an opening anywhere: the branches nobody took are the point of
        # this page, and 80 characters of one is not evidence of anything.
        page = self.html()
        s = json.loads(read(loom.sitting_path(self.room)))
        for r in forks_of(self.s["berserk"]):
            for nid in r["order"]:
                text = s["nodes"][nid]["text"]
                if text.strip():
                    self.assertIn(html_escape(text), page)
        self.assertEqual(page.count(html_escape(SEED)), 1, "the seed, once per page")


class About(unittest.TestCase):
    """The default picker. The reader answers with a description of the branch, not a piece
    of it, so the substring matcher has little to hold and the resolver does the work."""

    @classmethod
    def setUpClass(cls) -> None:
        stub_llama.READER_MODE = "quote"
        cls.s = scratch()
        cls.r = run(cls.s["env"], "cycle", "--cycle", "5", "--pages", "1",
                    "--forks", "1", "--fan", "4")
        cls.room = "berserk-c05-p01"

    @classmethod
    def tearDownClass(cls) -> None:
        stub_llama.READER_MODE = ""
        shutil.rmtree(cls.s["dir"], ignore_errors=True)
        cleanup(cls.room)

    def test_about_is_the_default_picker(self) -> None:
        self.assertEqual(self.r.returncode, 0, self.r.stderr[-3000:])
        self.assertTrue(all(r["picker"] == "about" for r in forks_of(self.s["berserk"])))

    def test_opus_resolved_every_fork(self) -> None:
        for r in forks_of(self.s["berserk"]):
            self.assertEqual(r["outcome"], "match")
            self.assertEqual(r["used"], "opus")
            self.assertIsNotNone(r["opus"]["index"])
            # The witness runs anyway and is allowed to say nothing: a description is not
            # in the text it describes. It is logged to be read, not to be obeyed.
            self.assertIn("substring", r)

    def test_the_branch_taken_is_the_one_described(self) -> None:
        s = json.loads(read(loom.sitting_path(self.room)))
        for r in forks_of(self.s["berserk"]):
            chosen = r["order"][r["opus"]["index"]]
            self.assertEqual(chosen, r["keep"][0] if r["closing"] else r["pick"])
            # And it really is the described one: of every branch in the fan, the one taken
            # shares the most words with the description.
            best = max(r["order"], key=lambda i: overlap(r["quote"], s["nodes"][i]["text"]))
            self.assertEqual(chosen, best, r["quote"])

    def test_the_resolver_asked_about_describing_and_stayed_blind(self) -> None:
        prompts = read(self.s["log"])
        self.assertIn("is this describing", prompts)
        self.assertIn("description: ", prompts)
        self.assertIn(forks_of(self.s["berserk"])[0]["quote"], prompts)
        self.assertNotIn("Municipal Lifts Office", prompts)

    def test_the_report_prints_the_description_without_quote_marks(self) -> None:
        md = read(os.path.join(self.s["berserk"], "cycles", "c05.md"))
        self.assertIn("picker about", md)
        for r in forks_of(self.s["berserk"]):
            self.assertIn(r["quote"], md)
            self.assertNotIn(f"“{r['quote']}”", md, "a description is not a quotation")


class Margin(unittest.TestCase):
    """No reader of the fan at all: one note per branch, then one blind pick over the notes."""

    @classmethod
    def setUpClass(cls) -> None:
        stub_llama.READER_MODE = "quote"
        cls.s = scratch()
        cls.r = run(cls.s["env"], "cycle", "--cycle", "6", "--pages", "1",
                    "--forks", "1", "--fan", "5", "--picker", "margin")
        cls.room = "berserk-c06-p01"

    @classmethod
    def tearDownClass(cls) -> None:
        stub_llama.READER_MODE = ""
        shutil.rmtree(cls.s["dir"], ignore_errors=True)
        cleanup(cls.room)

    def test_a_note_per_branch(self) -> None:
        self.assertEqual(self.r.returncode, 0, self.r.stderr[-3000:])
        fs = forks_of(self.s["berserk"])
        self.assertEqual(len(fs), 2)
        for r in fs:
            self.assertEqual(r["picker"], "margin")
            self.assertEqual(len(r["notes"]), 5, "one note per branch of a fan of five")
            self.assertEqual(len(r["order"]), 5)
            self.assertEqual(r["attempts"], 1, "nothing to reroll: the notes are written once")
            self.assertFalse(r["widened"])
            self.assertFalse(r["wished"], "nothing can be wished for: every branch got a note")
        self.assertEqual(len(set(fs[0]["notes"])), 5, "the notes tell the branches apart")

    def test_the_branch_under_the_chosen_note_was_taken(self) -> None:
        s = json.loads(read(loom.sitting_path(self.room)))
        for r in forks_of(self.s["berserk"]):
            # The fake resolver picks the longest note, ties to the lowest number — and the
            # walk has to land on the branch that note was written beside, not on the note.
            flat = [" ".join(n.split()) for n in r["notes"]]
            self.assertEqual(r["pick_note"], flat.index(max(flat, key=len)))
            self.assertEqual(r["used"], "opus")
            chosen = r["order"][r["pick_note"]]
            self.assertEqual(chosen, r["keep"][0] if r["closing"] else r["pick"])
            mark = s["nodes"][chosen]["meta"]["berserk"]
            self.assertEqual(mark, {"note": r["notes"][r["pick_note"]], "used": "opus"})

    def test_the_resolver_saw_notes_and_nothing_else(self) -> None:
        prompts = read(self.s["log"])
        self.assertIn("most pronounced", prompts)
        self.assertNotIn("Municipal Lifts Office", prompts, "no document")
        self.assertNotIn("and entry", prompts, "no branches either — only the notes")

    def test_the_report_prints_the_picked_note_and_no_wished_pile(self) -> None:
        md = read(os.path.join(self.s["berserk"], "cycles", "c06.md"))
        self.assertIn("picker margin", md)
        for r in forks_of(self.s["berserk"]):
            self.assertIn(r["notes"][r["pick_note"]], md)
        self.assertNotIn("## wished for", md)


class MarginRandom(unittest.TestCase):
    """margin with nobody to read the notes. The notes are still written and still logged —
    that is the finding — but the branch is chance, and the run says so."""

    @classmethod
    def setUpClass(cls) -> None:
        stub_llama.READER_MODE = "quote"
        cls.s = scratch()
        cls.r = run(cls.s["env"], "cycle", "--cycle", "7", "--pages", "1", "--forks", "1",
                    "--fan", "3", "--picker", "margin", "--verify", "none")
        cls.room = "berserk-c07-p01"

    @classmethod
    def tearDownClass(cls) -> None:
        stub_llama.READER_MODE = ""
        shutil.rmtree(cls.s["dir"], ignore_errors=True)
        cleanup(cls.room)

    def test_random_but_the_notes_are_kept(self) -> None:
        self.assertEqual(self.r.returncode, 0, self.r.stderr[-3000:])
        self.assertIn("nobody reads the notes", self.r.stderr)
        for r in forks_of(self.s["berserk"]):
            self.assertEqual(r["outcome"], "random")
            self.assertEqual(r["used"], "random")
            self.assertTrue(r["reader_failed"])
            self.assertEqual(len(r["notes"]), 3)
            self.assertIsNotNone(r["pick_note"], "the note of the branch chance landed on")
        self.assertFalse(os.path.exists(self.s["log"]), "claude was never asked")


class TheLead(unittest.TestCase):
    """A 35-token branch ends anywhere, so the document almost always stands mid-sentence and
    the branches under it open on punctuation. These are the real openings from the first
    smoke run's closing fan, where the reader was asked which fragment "began: “" and — since
    none of them began with anything — invented four beginnings instead."""

    DOC = "the roll was read out in the hall\nthere will be no witch burning this year"
    BRANCHES = [".\nthe lanterns were put away", ", as it was raining all month",
                ", god help us all."]

    def frags(self) -> tuple[str, list[str]]:
        lead = berserk.lead_of(self.DOC)
        return lead, [lead + b for b in self.BRANCHES]

    def test_the_lead_is_the_unfinished_last_line(self) -> None:
        self.assertEqual(berserk.lead_of(self.DOC),
                         "there will be no witch burning this year")
        self.assertEqual(berserk.lead_of("a line that ended\n"), "")

    def test_the_lead_is_shown_once_per_fragment_and_never_above_them(self) -> None:
        lead, frags = self.frags()
        head = self.DOC[:len(self.DOC) - len(lead)]
        doc = berserk.reader_document(head, frags, berserk.ASK_QUOTE)
        self.assertEqual(doc.count(lead), len(frags), "in the fan, and not in the tail too")
        self.assertIn("the roll was read out in the hall", doc)
        self.assertTrue(doc.endswith(berserk.ASK_QUOTE))

    def test_a_fragment_is_matched_through_its_lead(self) -> None:
        lead, frags = self.frags()
        m = berserk.match_substring(lead + ", as it was raining", frags, lead)
        self.assertEqual(m["index"], 1)
        self.assertEqual(m["score"], 1.0)

    def test_quoting_the_lead_alone_is_no_match(self) -> None:
        # Every fragment begins with it, so it points at all three, which is to say at none.
        lead, frags = self.frags()
        self.assertIsNone(berserk.match_substring(lead, frags, lead)["index"])
        self.assertIsNone(berserk.match_substring(lead + ",", frags, lead)["index"])

    def test_the_blind_matcher_sees_the_same_fragments(self) -> None:
        lead, frags = self.frags()
        p = berserk.matcher_prompt("a quotation", frags, lead)
        for i, f in enumerate(frags, 1):
            self.assertIn(f"{i}. {' '.join(f.split())}", p)
        self.assertNotIn("the roll was read out in the hall", p, "still blind")


class Quoted(unittest.TestCase):
    """The reader quotes a branch that is really there, and opus agrees with the substring
    matcher. Two picking forks and a closing fan, walked end to end."""

    @classmethod
    def setUpClass(cls) -> None:
        stub_llama.READER_MODE = "quote"
        cls.s = scratch()
        cls.r = run(cls.s["env"], "cycle", "--cycle", "1", "--pages", "1",
                    "--forks", "2", "--fan", "3", "--picker", "quote")
        cls.room = "berserk-c01-p01"

    @classmethod
    def tearDownClass(cls) -> None:
        stub_llama.READER_MODE = ""
        shutil.rmtree(cls.s["dir"], ignore_errors=True)
        cleanup(cls.room)

    def sitting(self) -> dict:
        return json.loads(read(loom.sitting_path(self.room)))

    def artifact(self) -> dict:
        return json.loads(read(loom.artifact_path(self.room)))

    def test_exit(self) -> None:
        self.assertEqual(self.r.returncode, 0, self.r.stderr[-3000:])

    def test_room_stands_on_the_seed_two_deep(self) -> None:
        s = self.sitting()
        self.assertEqual(s["nodes"][s["root"]]["text"], SEED)
        depth, n = 0, s["nodes"][s["current"]]
        while n["parent"]:
            depth += 1
            n = s["nodes"][n["parent"]]
        self.assertEqual(depth, 2, "two picking forks means the document is two lines deep")

    def test_every_fork_matched(self) -> None:
        fs = forks_of(self.s["berserk"])
        self.assertEqual(len(fs), 3)
        self.assertTrue(all(r["outcome"] == "match" for r in fs),
                        [r["outcome"] for r in fs])
        self.assertFalse(any(r["reader_failed"] for r in fs))
        self.assertFalse(any(r["widened"] for r in fs))

    def test_ledger_rows_carry_the_quote_the_use_and_the_order(self) -> None:
        for r in forks_of(self.s["berserk"]):
            self.assertTrue(r["quote"].strip(), r)
            self.assertEqual(r["used"], "opus", "opus is the used answer while verify=opus")
            self.assertEqual(len(r["order"]), r["fan_size"],
                             "the shuffled branch ids, exactly as the reader saw them")
            self.assertEqual(len(set(r["order"])), r["fan_size"])
            self.assertGreaterEqual(r["substring"]["score"], 0.6)
            self.assertGreater(r["bits"], 0)

    def test_the_quote_rides_on_the_chosen_node(self) -> None:
        marks = [(n["meta"] or {}).get("berserk") for n in self.sitting()["nodes"].values()]
        marks = [m for m in marks if m]
        self.assertEqual(len(marks), 3, "two taken and one kept carry the reader's quote")
        self.assertTrue(all(m["quote"] and m["used"] == "opus" for m in marks), marks)

    def test_opus_and_the_substring_matcher_agree(self) -> None:
        fs = forks_of(self.s["berserk"])
        self.assertTrue(all(r["agree"] for r in fs), [(r["opus"], r["substring"]) for r in fs])
        self.assertTrue(all(r["opus"]["index"] == r["substring"]["index"] for r in fs))

    def test_the_matcher_was_blind(self) -> None:
        prompts = read(self.s["log"])
        quote = forks_of(self.s["berserk"])[0]["quote"]
        self.assertIn(quote, prompts, "the quotation is what it was asked about")
        self.assertNotIn("Municipal Lifts Office", prompts, "no document reaches the matcher")
        self.assertNotIn("rulebook", prompts.lower(), "there is no rulebook any more")
        self.assertNotIn("THE DOCUMENT", prompts)

    def test_the_reader_ran_with_the_brakes_off(self) -> None:
        # DRY and the repeat penalty punish copying, which is the reader's whole job; xtc
        # refuses the likeliest token at a fork, which here is the branch it means to quote.
        bodies = reader_bodies()
        self.assertTrue(bodies, "the reader never called llama")
        for b in bodies:
            self.assertEqual(b["dry_multiplier"], 0.0)
            self.assertEqual(b["repeat_penalty"], 1.0)
            self.assertEqual(b["xtc_probability"], 0)

    def test_the_closing_fan_kept_one_and_took_nothing(self) -> None:
        last = forks_of(self.s["berserk"])[-1]
        self.assertTrue(last["closing"])
        self.assertIsNone(last["pick"])
        self.assertEqual(len(last["keep"]), 1)
        kept = [n for n in self.sitting()["nodes"].values() if n.get("kept")]
        self.assertEqual(len(kept), 1, "only the closing fan keeps")

    def test_artifact_is_a_three_step_walk(self) -> None:
        art = self.artifact()
        self.assertEqual(len(art["steps"]), 3, "two taken plus the closing fan")
        self.assertIsNone(art["steps"][-1]["took"], "nothing is taken at the closing fan")
        self.assertTrue(art["steps"][-1]["kept"])
        self.assertGreater(art["bits"], 0)
        self.assertEqual(art["prompt"], SEED)

    def test_artifact_text_is_the_document(self) -> None:
        # artifact_text opens with its own five-line head (title, model, sampler, walk,
        # saved) and then the document — so the seed starts the document, not the string.
        text = loom.artifact_text(self.artifact())
        head, doc = text.split("\n\n", 1)
        self.assertIn("model:", head)
        self.assertTrue(doc.startswith(SEED), repr(doc[:200]))

    def test_the_sheets_page_grew_fork_by_fork(self) -> None:
        # berserk re-renders the cycle's one page after every fork, so by the end of a
        # two-fork page plus its closing fan all three are on it — and there is no per-room
        # html any more, which is the point: nothing half-written to clean up after a crash.
        path = os.path.join(self.s["berserk"], "pages", "berserk-c01.html")
        self.assertTrue(os.path.isfile(path))
        page = read(path)
        for n in (1, 2, 3):
            self.assertIn(f"<h4>fork {n}", page)
        self.assertIn("the closing fan, nothing taken from it", page)
        self.assertIn("Municipal Lifts Office", page, "the seed it started from")
        self.assertIn("background:#111", page, "the sheets skin")
        self.assertNotIn("walking…", page, "the cycle finished")
        self.assertFalse(os.path.exists(os.path.join(self.s["berserk"], "pages",
                                                     self.room + ".html")))

    def test_ledger_has_a_line_per_fork_page_and_cycle(self) -> None:
        rs = rows(self.s["berserk"])
        pages = [r for r in rs if r.get("event") == "page"]
        self.assertEqual(len(pages), 1)
        self.assertTrue(pages[0]["artifact_written"])
        cycles = [r for r in rs if r.get("event") == "cycle"]
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0]["matches"], 3)
        self.assertEqual(cycles[0]["random"], 0)
        self.assertEqual(cycles[0]["wished"], 0)
        self.assertEqual(cycles[0]["agree"], 3)

    def test_report_names_the_page_and_the_quotes(self) -> None:
        md = read(os.path.join(self.s["berserk"], "cycles", "c01.md"))
        self.assertIn(self.room, md)
        self.assertIn("the ask:", md)
        for r in forks_of(self.s["berserk"]):
            self.assertIn(r["quote"], md)
        self.assertIn("## wished for", md)
        self.assertIn("every answer this cycle was a branch that was really there", md)

    def test_state_is_gone_and_heartbeat_remains(self) -> None:
        self.assertFalse(os.path.exists(os.path.join(self.s["berserk"], "state.json")))
        hb = json.loads(read(os.path.join(self.s["berserk"], "heartbeat")))
        self.assertIn("phase", hb)

    def test_a_second_run_refuses_the_same_room(self) -> None:
        r = run(self.s["env"], "page", "--cycle", "1", "--page", "1", "--forks", "1",
                "--fan", "2", "--picker", "quote")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not overwriting", r.stderr)


class NoVerify(unittest.TestCase):
    """--verify none: the substring matcher alone, and `claude` is never started at all."""

    @classmethod
    def setUpClass(cls) -> None:
        stub_llama.READER_MODE = "quote"
        cls.s = scratch()
        cls.r = run(cls.s["env"], "cycle", "--cycle", "3", "--pages", "1",
                    "--forks", "1", "--fan", "3", "--picker", "quote", "--verify", "none")
        cls.room = "berserk-c03-p01"

    @classmethod
    def tearDownClass(cls) -> None:
        stub_llama.READER_MODE = ""
        shutil.rmtree(cls.s["dir"], ignore_errors=True)
        cleanup(cls.room)

    def test_the_walk_still_happened(self) -> None:
        self.assertEqual(self.r.returncode, 0, self.r.stderr[-3000:])
        self.assertTrue(os.path.isfile(loom.artifact_path(self.room)))

    def test_claude_was_never_invoked(self) -> None:
        # The fake claude is still first on PATH and writes this file the moment it runs, so
        # its absence is the assertion: not "opus answered nothing", but "nobody asked it".
        self.assertFalse(os.path.exists(self.s["log"]))

    def test_the_substring_matcher_was_used_and_opus_is_not_on_the_row(self) -> None:
        for r in forks_of(self.s["berserk"]):
            self.assertEqual(r["outcome"], "match")
            self.assertEqual(r["used"], "substring")
            self.assertIsNone(r["agree"])
            self.assertNotIn("opus", r)

    def test_embed_is_named_and_refused(self) -> None:
        r = run(self.s["env"], "page", "--cycle", "9", "--verify", "embed")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("embed matcher not built yet", r.stderr)


class MatcherGarbage(unittest.TestCase):
    """The reader quotes fine; opus answers prose. The substring answer carries the walk."""

    @classmethod
    def setUpClass(cls) -> None:
        stub_llama.READER_MODE = "quote"
        cls.s = scratch(mode="garbage")
        cls.r = run(cls.s["env"], "cycle", "--cycle", "4", "--pages", "1",
                    "--forks", "1", "--fan", "3", "--picker", "quote")
        cls.room = "berserk-c04-p01"

    @classmethod
    def tearDownClass(cls) -> None:
        stub_llama.READER_MODE = ""
        shutil.rmtree(cls.s["dir"], ignore_errors=True)
        cleanup(cls.room)

    def test_it_fell_back_to_the_substring_answer(self) -> None:
        self.assertEqual(self.r.returncode, 0, self.r.stderr[-3000:])
        for r in forks_of(self.s["berserk"]):
            self.assertEqual(r["outcome"], "match")
            self.assertEqual(r["used"], "substring")
            self.assertIsNone(r["opus"]["index"])
            self.assertFalse(r["agree"])


class NothingMatches(unittest.TestCase):
    """The reader quotes a branch that was never in the fan. Every fork widens once, then
    goes random, the walk still finishes, and the quotes land on the wished pile."""

    @classmethod
    def setUpClass(cls) -> None:
        stub_llama.READER_MODE = "garbage"
        cls.s = scratch()
        cls.r = run(cls.s["env"], "cycle", "--cycle", "2", "--pages", "1",
                    "--forks", "1", "--fan", "3", "--picker", "quote")
        cls.room = "berserk-c02-p01"

    @classmethod
    def tearDownClass(cls) -> None:
        stub_llama.READER_MODE = ""
        shutil.rmtree(cls.s["dir"], ignore_errors=True)
        cleanup(cls.room)

    def test_the_run_completes_anyway(self) -> None:
        self.assertEqual(self.r.returncode, 0, self.r.stderr[-3000:])
        self.assertTrue(os.path.isfile(loom.artifact_path(self.room)))

    def test_every_fork_widened_and_went_random(self) -> None:
        fs = forks_of(self.s["berserk"])
        self.assertEqual(len(fs), 2)
        for r in fs:
            self.assertEqual(r["outcome"], "random")
            self.assertTrue(r["reader_failed"])
            self.assertTrue(r["widened"])
            self.assertEqual(r["attempts"], 4, "three asks, then one wider fan asked once")
            self.assertEqual(r["fan_size"], 6, "the fan was drawn a second time under it")
            self.assertEqual(r["used"], "random")
            self.assertTrue(r["wished"])
        # The closing fan still keeps something, or there is no artifact to write.
        self.assertTrue(fs[-1]["keep"])

    def test_the_report_carries_the_wished_pile(self) -> None:
        md = read(os.path.join(self.s["berserk"], "cycles", "c02.md"))
        self.assertIn("## wished for", md)
        self.assertIn(stub_llama.NO_BRANCH, md)
        self.assertIn("**(random)**", md)
        self.assertIn("*(widened)*", md)

    def test_the_cycle_line_counts_the_wishes(self) -> None:
        c = [r for r in rows(self.s["berserk"]) if r.get("event") == "cycle"][0]
        self.assertEqual(c["matches"], 0)
        self.assertEqual(c["random"], 2)
        self.assertEqual(c["wished"], 8, "four unmatched quotations at each of two forks")


if __name__ == "__main__":
    unittest.main()
