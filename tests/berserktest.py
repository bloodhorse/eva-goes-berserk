#!/usr/bin/env -S uv run --python 3.12
"""berserktest.py — one whole berserk cycle, with a fake llama and a fake opus.

    uv run --python 3.12 -m unittest tests/berserktest.py

Nothing inside berserk.py is mocked: a real berserk.py runs as a subprocess, against the
same stub llama-server the loom's tests use and against a **fake `claude`** — a three-line
script put first on PATH that reads the prompt off stdin, files it away, and prints the json
the rulebook asks for. That is the seam worth faking: the picker is a subprocess with a
prompt on stdin and json on stdout, and every one of those three things can break silently.

The fake claude also keeps every prompt it was handed, which is how the first test can assert
that the rulebook and the document really reached the reader — a picker walking a document it
was never shown would produce a perfectly valid-looking run.

Scratch everything: LOOM_SITTINGS / LOOM_ARTIFACTS, BERSERK_DIR, BERSERK_SEEDS. The sheets
host and the ntfy topic are set to the empty string, which berserk reads as "post nowhere" —
a test run must never scp to the mini or push to bekh's phone.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS)
sys.path.insert(0, TESTS)
sys.path.insert(0, ROOT)
import stub_llama  # noqa: E402

SHELF = tempfile.mkdtemp(prefix="berserk-sittings-")
ARTS = tempfile.mkdtemp(prefix="berserk-arts-")
os.environ["LOOM_SITTINGS"] = SHELF
os.environ["LOOM_ARTIFACTS"] = ARTS
import loom  # noqa: E402 — after the env, which loom reads once at import

SEED = ("Municipal Lifts Office\nAcceptance tests following the removal of a floor\n\n"
        "Test 3. Same load, with a hat placed on the upper sack. Stopped between third "
        "and fifth.\n")

# The rulebook's first heading, restated as a literal: if somebody retitles the rulebook,
# this test should fail and a human should read why the picker's prompt changed.
RULEBOOK_HEAD = "# the picker's rulebook"

STUB = None
STUB_BASE = ""
REAL_LINES: list[str] = []
REAL_DIRS: tuple = ()

# A picker that answers "pick 1, keep [2]" every time, and "pick null, keep [1]" when the
# prompt says the fan is a closing one. GARBAGE mode answers prose instead, twice, which is
# the 4am failure the daemon is built to survive.
FAKE_CLAUDE = '''#!/usr/bin/env python3
import os, sys
prompt = sys.stdin.read()
log = os.environ.get("FAKE_CLAUDE_LOG")
if log:
    with open(log, "a", encoding="utf-8") as f:
        f.write("\\n===PROMPT===\\n" + prompt)
if os.environ.get("FAKE_CLAUDE_MODE") == "garbage":
    print("Sure! Here is my thinking about the fan. I liked branch three a lot.")
    sys.exit(0)
if "CLOSING FAN" in prompt:
    print('{"genre": "lift report", "pick": null, "keep": [1], "note": "ends on a thing said"}')
elif "THE 1 PAGES" in prompt or "THE PAGES" in prompt or "json list" in prompt:
    print('[{"page": "PAGE", "notable": true, "why": "the hat", "quote": "a hat"}]')
else:
    print('{"genre": "municipal minute", "pick": 1, "keep": [2], "note": "keeps doors open"}')
'''


def setUpModule() -> None:
    global STUB, STUB_BASE, REAL_LINES, REAL_DIRS
    # loom reads LOOM_SITTINGS and LOOM_ARTIFACTS ONCE, at import, so when the whole suite
    # runs in one process loomtest has already imported it and pointed it at its own scratch
    # shelf. Repointed here and not at import: at import time this would fire during
    # collection, before the other files' tests run, and move the shelf out from under them.
    REAL_DIRS = (loom.SITTINGS, loom.ARTIFACTS)
    loom.SITTINGS, loom.ARTIFACTS = SHELF, ARTS
    # Distinct lines, and plenty of them: the stub picks its continuation at random, and two
    # branches of one fan coming back verbatim identical would drop out of the artifact's
    # bit pool as twins — a real property of build_artifact, but a flaky test. Put back in
    # tearDown, because the stub is a module the other test files share in one process.
    REAL_LINES = stub_llama.LINES
    stub_llama.LINES = [f" and the {i}th entry was recorded without remark" for i in range(60)]
    STUB = stub_llama.serve(0)
    threading.Thread(target=STUB.serve_forever, daemon=True).start()
    STUB_BASE = f"http://127.0.0.1:{STUB.server_address[1]}"


def tearDownModule() -> None:
    if REAL_LINES:
        stub_llama.LINES = REAL_LINES
    if REAL_DIRS:
        loom.SITTINGS, loom.ARTIFACTS = REAL_DIRS
    if STUB:
        STUB.shutdown()
    shutil.rmtree(SHELF, ignore_errors=True)
    shutil.rmtree(ARTS, ignore_errors=True)


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
        f.write(FAKE_CLAUDE.replace("#!/usr/bin/env python3", "#!" + sys.executable)
                .replace('"PAGE"', '"berserk-c01-p01"'))
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
    return subprocess.run([sys.executable, os.path.join(ROOT, "berserk.py"), *args],
                          env=env, capture_output=True, text=True, timeout=timeout)


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def rows(berserk: str) -> list[dict]:
    return [json.loads(line) for line in read(os.path.join(berserk, "ledger.jsonl")).splitlines()
            if line.strip()]


class Cycle(unittest.TestCase):
    """One page, two picking forks and a closing fan, walked end to end."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.s = scratch()
        cls.r = run(cls.s["env"], "cycle", "--cycle", "1", "--pages", "1",
                    "--forks", "2", "--fan", "3")
        cls.room = "berserk-c01-p01"

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.s["dir"], ignore_errors=True)
        for p in (loom.sitting_path(cls.room), loom.artifact_path(cls.room)):
            if os.path.exists(p):
                os.unlink(p)

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

    def test_kept_flags_landed(self) -> None:
        s = self.sitting()
        kept = [n for n in s["nodes"].values() if n.get("kept")]
        # One keep per fork, three forks — the closing one keeps too.
        self.assertEqual(len(kept), 3)
        # The genre and note are readable in the room itself, not only in the ledger.
        marks = [n["meta"]["berserk"] for n in s["nodes"].values()
                 if (n.get("meta") or {}).get("berserk")]
        self.assertTrue(any(m["genre"] == "municipal minute" for m in marks))

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

    def test_html_page_holds_the_escaped_document(self) -> None:
        path = os.path.join(self.s["berserk"], "pages", self.room + ".html")
        self.assertTrue(os.path.isfile(path))
        html = read(path)
        self.assertIn("Municipal Lifts Office", html)
        self.assertIn("plain text at eva.x", html)
        self.assertIn("background:#111", html)

    def test_ledger_has_a_line_per_fork_page_and_cycle(self) -> None:
        rs = rows(self.s["berserk"])
        forks = [r for r in rs if r.get("event") is None]
        self.assertEqual(len(forks), 3)
        self.assertTrue(forks[-1]["closing"])
        self.assertIsNone(forks[-1]["pick"])
        self.assertFalse(any(r["picker_failed"] for r in forks))
        pages = [r for r in rs if r.get("event") == "page"]
        self.assertEqual(len(pages), 1)
        self.assertTrue(pages[0]["artifact_written"])
        cycles = [r for r in rs if r.get("event") == "cycle"]
        self.assertEqual(len(cycles), 1)

    def test_report_names_the_page(self) -> None:
        path = os.path.join(self.s["berserk"], "cycles", "c01.md")
        self.assertTrue(os.path.isfile(path))
        md = read(path)
        self.assertIn(self.room, md)
        self.assertIn("notable", md)

    def test_state_is_gone_and_heartbeat_remains(self) -> None:
        self.assertFalse(os.path.exists(os.path.join(self.s["berserk"], "state.json")))
        hb = json.loads(read(os.path.join(self.s["berserk"], "heartbeat")))
        self.assertIn("phase", hb)

    def test_the_picker_saw_the_rulebook_and_the_document(self) -> None:
        prompts = read(self.s["log"])
        self.assertIn(RULEBOOK_HEAD, prompts)
        self.assertIn("Municipal Lifts Office", prompts)
        self.assertIn("--- 1 (t=1.4)", prompts)
        self.assertIn("CLOSING FAN", prompts)

    def test_a_second_run_refuses_the_same_room(self) -> None:
        r = run(self.s["env"], "page", "--cycle", "1", "--page", "1", "--forks", "1",
                "--fan", "2")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not overwriting", r.stderr)


class PickerFails(unittest.TestCase):
    """The picker answers prose. Twice. The walk still finishes, and says so on the ledger."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.s = scratch(mode="garbage")
        cls.r = run(cls.s["env"], "cycle", "--cycle", "2", "--pages", "1",
                    "--forks", "1", "--fan", "3")
        cls.room = "berserk-c02-p01"

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.s["dir"], ignore_errors=True)
        for p in (loom.sitting_path(cls.room), loom.artifact_path(cls.room)):
            if os.path.exists(p):
                os.unlink(p)

    def test_the_run_completes_anyway(self) -> None:
        self.assertEqual(self.r.returncode, 0, self.r.stderr[-3000:])
        self.assertTrue(os.path.isfile(loom.artifact_path(self.room)))

    def test_picker_failed_is_on_every_fork_line(self) -> None:
        forks = [r for r in rows(self.s["berserk"]) if r.get("event") is None]
        self.assertEqual(len(forks), 2)
        self.assertTrue(all(r["picker_failed"] for r in forks))
        # The closing fan still has to keep something, or there is no artifact to write.
        self.assertTrue(forks[-1]["keep"])

    def test_the_report_carries_the_unreadable_review(self) -> None:
        md = read(os.path.join(self.s["berserk"], "cycles", "c02.md"))
        self.assertIn("could not be read", md)
        self.assertIn("| 2 |", md, "two picker failures counted in the table")


if __name__ == "__main__":
    unittest.main()
