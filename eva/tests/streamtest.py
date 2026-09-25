#!/usr/bin/env -S uv run --python 3.12
"""streamtest.py — the dream stream: the worker, and the two routes that read it.

    uv run --python 3.12 -m unittest discover -s eva/tests -p '*test.py'

Two halves, because the stream has two. `stream.main` takes its argv and returns an exit
code, so a whole unattended run happens in-process against the fake llama-server; the api
is a real loom.py in a subprocess against a real socket, exactly as loomtest drives it.

Everything is scratch: a temp sittings shelf, a temp STREAM_DIR for the ledger and the
heartbeat, a temp seeds folder. The real shelf is never touched, and no test here ever
starts a launchd agent or asks the live nemo for anything.
"""

from __future__ import annotations

import http.client
import http.server
import io
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
from contextlib import redirect_stderr, redirect_stdout

TESTS = os.path.dirname(os.path.abspath(__file__))
EVA = os.path.dirname(TESTS)                  # eva/: server/ has loom, stream/ has the worker
for d in (TESTS, os.path.join(EVA, "server"), os.path.join(EVA, "cli"),
          os.path.join(EVA, "stream")):
    sys.path.insert(0, d)
import stub_llama  # noqa: E402

# Before importing loom, and it has to be — loom reads these once, at import.
BOX = tempfile.mkdtemp(prefix="stream-test-")
SHELF = os.path.join(BOX, "sittings")
ARTS = os.path.join(BOX, "artifacts")
STREAM_DIR = os.path.join(BOX, "stream")
SEEDS = os.path.join(BOX, "seeds")
os.environ["LOOM_SITTINGS"] = SHELF
os.environ["LOOM_ARTIFACTS"] = ARTS
os.environ["STREAM_DIR"] = STREAM_DIR
os.environ["STREAM_SEEDS"] = SEEDS
os.environ["STREAM_INTERVAL"] = "300"
os.environ["STREAM_SEED_LOWER"] = "0"     # the seed tests compare text exactly; lowering has its own

import codex  # noqa: E402
import interpreter  # noqa: E402
import analyst  # noqa: E402
import naming  # noqa: E402
import plate  # noqa: E402
import plating  # noqa: E402
import loom  # noqa: E402
import opus  # noqa: E402
import remembering  # noqa: E402
import stream  # noqa: E402

# Another test module in the same run may have imported loom first and pointed it at ITS
# scratch shelf; follow rather than argue (censustest carries the same knot). Either way it
# is never the real one — and the stream's own dirs are ours, set by name above.
if loom.SITTINGS != SHELF:
    SHELF = loom.SITTINGS
loom.STREAM_DIR = STREAM_DIR
loom.ARTIFACTS = ARTS
plate.STREAM = STREAM_DIR
plate.PLATES = os.path.join(STREAM_DIR, "plates")
plate.LEDGER = os.path.join(STREAM_DIR, "ledger.jsonl")

STUB = None            # the ordinary one: a random line per call
STUB_DIRTY = None      # answers a licence footer, so the filter has something to catch
STUB_CLEAN = None      # answers one plain sentence, so "no flag" is not luck
LOOM = None
BASE = STUB_BASE = DIRTY_BASE = CLEAN_BASE = ""

MARK = "STREAMSEEDMARK"        # not a substring of any other test file's marker


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def call(path: str, body=None, timeout: float = 30):
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
    global STUB, STUB_DIRTY, STUB_CLEAN, LOOM, BASE, STUB_BASE, DIRTY_BASE, CLEAN_BASE
    STUB = stub_llama.serve(0)
    STUB_DIRTY = stub_llama.serve(0, lines=["Unless otherwise stated, all rights reserved."])
    STUB_CLEAN = stub_llama.serve(0, lines=["the lamp in the hall was still warm at four."])
    for srv in (STUB, STUB_DIRTY, STUB_CLEAN):
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    STUB_BASE = f"http://127.0.0.1:{STUB.server_address[1]}"
    DIRTY_BASE = f"http://127.0.0.1:{STUB_DIRTY.server_address[1]}"
    CLEAN_BASE = f"http://127.0.0.1:{STUB_CLEAN.server_address[1]}"
    # loom.complete and loom.model_info read this module global at CALL time, so one
    # assignment points the worker at the fake and no live server is ever needed.
    loom.LLAMA = STUB_BASE
    os.makedirs(SHELF, exist_ok=True)
    os.makedirs(SEEDS, exist_ok=True)

    port = free_port()
    BASE = f"http://127.0.0.1:{port}"
    env = dict(os.environ, LOOM_HOST="127.0.0.1", LOOM_PORT=str(port), LOOM_SITTINGS=SHELF,
               LOOM_ARTIFACTS=ARTS, LOOM_LLAMA=STUB_BASE, STREAM_DIR=STREAM_DIR,
               STREAM_INTERVAL="300", STREAM_ANALYST_SEAT="analyst")
    LOOM = subprocess.Popen([sys.executable, os.path.join(EVA, "server", "loom.py")],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    deadline = time.time() + 20
    while time.time() < deadline:
        if LOOM.poll() is not None:
            raise RuntimeError("loom died on start: " + LOOM.stdout.read().decode())
        try:
            if call("/api/health")[0] == 200:
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
    for srv in (STUB, STUB_DIRTY, STUB_CLEAN):
        if srv:
            srv.shutdown()
    shutil.rmtree(BOX, ignore_errors=True)


def wipe_stream() -> None:
    """The stream's rooms, ledger, heartbeat, readings, dreams and plates, gone — so a test's pot B, its page count and
    its status are its own and not the last test's leftovers."""
    shutil.rmtree(os.path.join(SHELF, "stream"), ignore_errors=True)
    shutil.rmtree(STREAM_DIR, ignore_errors=True)
    for name in os.listdir(SEEDS):
        os.unlink(os.path.join(SEEDS, name))


def put_seed(name: str, text: str) -> str:
    path = os.path.join(SEEDS, name)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return path


def run(*args) -> tuple[int, str]:
    out = io.StringIO()
    with redirect_stdout(out), redirect_stderr(out):
        code = stream.main(["stream.py", *args])
    return code, out.getvalue()


def rooms() -> list[str]:
    return sorted(loom.folder_rooms("stream"))


def on_disk(name: str) -> dict:
    with open(loom.sitting_path(name), encoding="utf-8") as f:
        d = json.load(f)
    assert loom.check(d) == "", loom.check(d)
    return d


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def heartbeat() -> dict:
    with open(os.path.join(STREAM_DIR, "heartbeat.json"), encoding="utf-8") as f:
        return json.load(f)


def ledger_rows() -> list[dict]:
    try:
        with open(os.path.join(STREAM_DIR, "ledger.jsonl"), encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except OSError:
        return []


class Rng:
    """A loaded die. `draw_seed` asks it for exactly two things — a coin and a pick — so a
    stub with two methods is the whole of what the lot depends on, and a test can say which
    pot won instead of seeding a Mersenne twister and hoping."""

    def __init__(self, coin: float, which: int = 0) -> None:
        self.coin, self.which = coin, which

    def random(self) -> float:
        return self.coin

    def choice(self, seq):
        return seq[self.which % len(seq)]

    def uniform(self, lo, hi):
        return lo

    def shuffle(self, seq):
        pass                      # the bag keeps sorted order, so a test can name the next seed

    def randrange(self, n):
        return n - 1              # a seed that turns up mid-bag goes to the BACK of what is left


# ---- the worker ---------------------------------------------------------------------------

class Worker(unittest.TestCase):
    def setUp(self):
        wipe_stream()
        loom.LLAMA = STUB_BASE

    def test_a_run_writes_one_page_as_a_room(self):
        put_seed("one.txt", MARK + " the door was\n")
        code, out = run("--once")
        self.assertEqual(code, 0, out)

        names = rooms()
        self.assertEqual(len(names), 1, names)
        name = names[0]
        # stream/<YYYY-MM-DD>/<HHMM>: three segments, the middle one a date, so a day is a
        # folder and the names sort chronologically.
        head, day, clock = name.split("/")
        self.assertEqual(head, "stream")
        self.assertRegex(day, r"^\d{4}-\d{2}-\d{2}$")
        self.assertRegex(clock, r"^\d{4}$")

        d = on_disk(name)
        self.assertEqual(d["turn"], {"prefix": "", "suffix": ""})      # bare, no speakers
        self.assertEqual(d["params"]["stop"], [])
        root = d["nodes"][d["root"]]
        self.assertEqual(root["text"], MARK + " the door was\n")       # the seed, verbatim
        kids = [n for n in d["nodes"].values() if n["kind"] == "model"]
        self.assertEqual(len(kids), 1)                                 # one page, no fan
        node = kids[0]
        self.assertEqual(d["current"], node["id"])
        meta = node["meta"]

        # The whole point of the meta shape: a flat list of numbers, and NOT llama's tables.
        self.assertNotIn("probs", meta)
        self.assertIsInstance(meta["logprobs"], list)
        self.assertTrue(meta["logprobs"])
        for lp in meta["logprobs"]:
            self.assertIsInstance(lp, float)       # scalars, never llama's row objects
        # one number per generated token, and the whole node stays small because of it
        self.assertEqual(len(meta["logprobs"]), len(stub_llama.tokens_of(node["text"])))
        self.assertLess(len(json.dumps(meta)), 8000)

        self.assertEqual(meta["seed"], "seeds/one.txt")
        self.assertIsNone(meta["flag"])
        self.assertEqual(meta["model"], "stub-base-12b.Q5_K_M.gguf")
        p = meta["params"]
        self.assertTrue(1.8 <= p["temperature"] <= 2.5, p["temperature"])
        self.assertEqual((p["min_p"], p["top_k"], p["top_p"]), (0.08, 0, 1.0))
        self.assertEqual((p["repeat_penalty"], p["repeat_last_n"]), (1.05, 512))
        # half a phone screen, cut from 350 after bekh read the first live ones: a genre
        # locks in over length, so what is worth reading is near the top
        self.assertEqual(p["n_predict"], 170)
        self.assertEqual(p["stop"], [])
        self.assertEqual(p["n_probs"], 1)          # the minimum that buys a logprob at all

        # and the wire agrees: the seed alone went out, nothing of ours around it
        wire = [b for b in stub_llama.SEEN if MARK in (b.get("prompt") or "")]
        self.assertEqual(wire[-1]["prompt"], root["text"])
        self.assertEqual(wire[-1]["n_probs"], 1)

        row = ledger_rows()[-1]
        self.assertEqual((row["room"], row["seed"], row["flag"]), (name, "seeds/one.txt", None))
        self.assertTrue(row["tokens"] >= 1)
        hb = heartbeat()
        self.assertEqual((hb["ok"], hb["room"]), (True, name))
        self.assertEqual(hb["ts"], hb["last_ok"])

    def test_the_lot_draws_from_both_pots(self):
        put_seed("a.txt", MARK + " pot a\n")
        # Nothing starred yet: the coin cannot help, pot A is the only pot.
        self.assertEqual(stream.draw_seed(Rng(0.0))[0], "seeds/a.txt")

        # A starred page makes pot B, and then the coin decides.
        code, out = run("--once")
        self.assertEqual(code, 0, out)
        name = rooms()[0]
        d = on_disk(name)
        node = [n for n in d["nodes"].values() if n["kind"] == "model"][0]
        loom.set_mark(name, node["id"], "kept", True)

        self.assertEqual(stream.draw_seed(Rng(0.9))[0], "seeds/a.txt")       # heads: pot A
        ident, text = stream.draw_seed(Rng(0.0))                             # tails: pot B
        self.assertEqual(ident, "tail:" + name)
        # the tail is seed AND page, cut back from the end of the two together
        self.assertTrue(text)
        self.assertNotIn("\n\n\n", text)

        # One star must not take half the stream: a tail weighs what one seed weighs. With
        # nine more seeds in pot A the star's share is 1 in 11, so a coin of 0.3 — which a
        # flat fair coin would hand to pot B — stays in pot A.
        for i in range(9):
            put_seed(f"more-{i}.txt", MARK + f" pot a {i}\n")
        self.assertTrue(stream.draw_seed(Rng(0.3))[0].startswith("seeds/"))
        self.assertEqual(stream.draw_seed(Rng(0.05))[0], "tail:" + name)

        # `good` is not `kept`: the circle means "i wouldn't keep it", and feeding it back
        # would drift the stream toward the merely nice.
        loom.set_mark(name, node["id"], "good", True)        # pops the star, at-most-one
        self.assertEqual(stream.pot_b(), [])

    def test_the_bag_deals_every_seed_before_any_returns(self):
        for n in ("a.txt", "b.txt", "c.txt"):
            put_seed(n, MARK + " " + n + "\n")
        first = [stream.draw_seed(Rng(0.9))[0] for _ in range(3)]
        self.assertEqual(sorted(first), ["seeds/a.txt", "seeds/b.txt", "seeds/c.txt"])
        # the round is over: the next three are a fresh deal of the same three
        second = [stream.draw_seed(Rng(0.9))[0] for _ in range(3)]
        self.assertEqual(sorted(second), sorted(first))
        # a seed that appears mid-round is dealt within THIS round, not after a whole extra one
        stream.draw_seed(Rng(0.9))
        put_seed("d.txt", MARK + " d\n")
        rest = [stream.draw_seed(Rng(0.9))[0] for _ in range(3)]
        self.assertIn("seeds/d.txt", rest)
        self.assertEqual(len(set(rest)), 3)
        # a deleted seed is skipped, a broken bag file is a reshuffle and not an error
        os.unlink(os.path.join(SEEDS, "a.txt"))
        with open(stream.BAG, "w") as f:
            f.write("{not json")
        self.assertNotEqual(stream.draw_seed(Rng(0.9))[0], "seeds/a.txt")

    def test_a_long_seed_is_handed_over_as_its_tail_and_its_end_is_never_touched(self):
        long = ("The first sentence is far away and must go. " * 12
                + "Here the tail begins, a whole sentence. And the rule was that the hat stayed"
                + " on the upper sack until the doors had")
        self.assertEqual(stream.seed_tail("short seed, left alone", 45), "short seed, left alone")
        tail = stream.seed_tail(long, 20)
        self.assertTrue(long.endswith(tail))                 # the seam is the original's
        self.assertTrue(tail.endswith("until the doors had"))
        self.assertLessEqual(len(tail.split()), 20)
        self.assertTrue(tail.startswith("And the rule"))     # moved forward to a sentence start
        self.assertEqual(stream.seed_tail(long, 0), long)    # 0 turns it off
        verse = "one line\n" * 30 + "the last line\nand the seam"
        self.assertIn("\n", stream.seed_tail(verse, 8))      # line breaks survive

        # a hand-cut seed under kept/ is never trimmed
        os.makedirs(os.path.join(SEEDS, "kept"), exist_ok=True)
        put_seed(os.path.join("kept", "k.txt"), MARK + " " + long)
        self.assertEqual(stream.draw_seed(Rng(0.9))[1], MARK + " " + long)
        shutil.rmtree(os.path.join(SEEDS, "kept"))
        shutil.rmtree(STREAM_DIR, ignore_errors=True)      # the bag remembers kept/k.txt

        put_seed("long.txt", MARK + " " + long)
        code, out = run("--once")
        self.assertEqual(code, 0, out)
        d = on_disk(rooms()[0])
        root = d["nodes"][d["root"]]["text"]
        self.assertLessEqual(len(root.split()), 45)          # what is stored is what nemo saw
        self.assertTrue(root.endswith("until the doors had"))

        # lowercased at hand-over when the switch is on; the file on the shelf keeps its capitals
        stream.SEED_LOWER = True
        try:
            self.assertEqual(stream.draw_seed(Rng(0.9))[1], stream.seed_tail(MARK + " " + long, 45).lower())
        finally:
            stream.SEED_LOWER = False

    def test_a_seed_too_big_never_enters_the_pot(self):
        put_seed("small.txt", "a" * 100)
        put_seed("huge.txt", "b" * (stream.SEED_MAX_CHARS + 1))
        self.assertEqual([os.path.basename(p) for p in stream.pot_a()], ["small.txt"])

    def test_a_trailing_space_is_stripped_and_a_newline_is_not(self):
        put_seed("space.txt", MARK + " the door was   ")
        code, out = run("--once")
        self.assertEqual(code, 0, out)
        root = on_disk(rooms()[0])["nodes"][on_disk(rooms()[0])["root"]]
        self.assertEqual(root["text"], MARK + " the door was")
        wire = [b for b in stub_llama.SEEN if MARK in (b.get("prompt") or "")]
        self.assertFalse(wire[-1]["prompt"].endswith(" "))

        # newlines are the document's own shape and are left exactly as they were
        put_seed("nl.txt", "already\n\n")
        self.assertEqual(stream.draw_seed(Rng(0.9, 0))[1], "already\n\n")

    def test_the_filter_is_a_column_and_not_a_knife(self):
        # The rules themselves, one line each, so a change to the list is visible here.
        for text, want in [
            ("she went down to the water and did not come back.", None),
            ("see http://example.com/thing for the rest", "url"),
            ("<p>the door</p>", "html"),
            ("\n## chapter one\n", "markdown header"),
            ("read [the letter](https://x.y) again", "url"),
            ("photo by someone else", "byline"),
            ("posted by the night porter", "byline"),
            ("3 comments on this entry", "blog chrome"),
            ("subscribe for more", "blog chrome"),
            ("author's note: sorry for the wait", "blog chrome"),
            ("\nChapter 4\n", "chapter"),
            ("© 1974 the company", "copyright"),
            ("all rights reserved", "copyright"),
            ("[WIP] the long one", "bracket tag"),
            ("ask @someone about it", "handle"),
            ("#witchcore forever", "hashtag"),
        ]:
            self.assertEqual(stream.flag_of(text), want, text)

        # end to end: a flagged page is still WRITTEN, with the rule on the node
        put_seed("f.txt", MARK + " and then\n")
        loom.LLAMA = DIRTY_BASE
        code, out = run("--once")
        self.assertEqual(code, 0, out)
        node = [n for n in on_disk(rooms()[0])["nodes"].values() if n["kind"] == "model"][0]
        self.assertEqual(node["meta"]["flag"], "copyright")
        self.assertEqual(ledger_rows()[-1]["flag"], "copyright")

        # and a clean one carries no flag at all
        wipe_stream()
        put_seed("c.txt", MARK + " and then\n")
        loom.LLAMA = CLEAN_BASE
        self.assertEqual(run("--once")[0], 0)
        node = [n for n in on_disk(rooms()[0])["nodes"].values() if n["kind"] == "model"][0]
        self.assertIsNone(node["meta"]["flag"])

    def test_an_unreachable_llama_is_a_ledger_line_and_exit_zero(self):
        put_seed("d.txt", MARK + " nothing listens\n")
        loom.LLAMA = "http://127.0.0.1:1"          # nothing listens on port 1
        code, out = run("--once")
        # Exit 0 on purpose: launchd backs a job off when it exits non-zero, and a stream
        # that punished itself for a GPU being busy would stop dreaming.
        self.assertEqual(code, 0, out)
        self.assertEqual(rooms(), [])              # no half-room on the shelf either
        row = ledger_rows()[-1]
        self.assertIsNone(row["room"])
        self.assertIn("unreachable", row["error"])
        hb = heartbeat()
        self.assertIs(hb["ok"], False)
        self.assertIsNone(hb["last_ok"])           # nothing has ever landed here

    def test_the_reader_is_tapped_only_when_a_page_landed(self):
        """stream.py starts the interpreter when a dream is finished; the reader has no clock.
        Never reach launchctl from a test — the flag is off unless a test turns it on."""
        put_seed("k.txt", MARK + " and then\n")
        seen = []
        real = stream.subprocess.run

        def watch(cmd, **kw):
            seen.append(cmd)
            return real([sys.executable, "-c", ""], **kw)

        stream.subprocess.run = watch
        try:
            self.assertFalse(stream.KICK)            # unset in the tests, and it must stay so
            self.assertEqual(run("--once")[0], 0)
            self.assertEqual(seen, [], "a subprocess was spawned with the kick off")

            wipe_stream()
            put_seed("k.txt", MARK + " and then\n")
            stream.KICK = True
            self.assertEqual(run("--once")[0], 0)
            # every other job, each tapped on its own — the analyst among them
            self.assertEqual(seen, [["launchctl", "kickstart", f"gui/{os.getuid()}/{job}"]
                                    for job in stream.KICK_JOBS])
            self.assertIn(["launchctl", "kickstart",
                           f"gui/{os.getuid()}/com.bekh.eva-stream-analyst"], seen)
        finally:
            stream.subprocess.run = real
            stream.KICK = False

    def test_one_voice_failing_to_start_does_not_stop_the_other(self):
        # The first job and the last one: a failure at either end leaves every other tapped.
        for failing in ("interpreter", "analyst"):
            wipe_stream()
            put_seed("k.txt", MARK + " and then\n")
            seen = []
            real = stream.subprocess.run

            def half(cmd, **kw):
                seen.append(cmd[-1])
                if failing in cmd[-1]:
                    raise OSError("launchctl went away")
                return real([sys.executable, "-c", ""], **kw)

            stream.subprocess.run = half
            stream.KICK = True
            try:
                code, out = run("--once")
            finally:
                stream.subprocess.run = real
                stream.KICK = False
            self.assertEqual(code, 0, out)
            self.assertEqual([j.rsplit("/", 1)[-1] for j in seen], list(stream.KICK_JOBS))
            self.assertIn(f"kick · com.bekh.eva-stream-{failing}", out)

    def test_a_kick_that_fails_costs_the_page_nothing(self):
        put_seed("k.txt", MARK + " and then\n")
        real = stream.subprocess.run
        stream.subprocess.run = lambda *a, **kw: (_ for _ in ()).throw(OSError("no launchctl"))
        stream.KICK = True
        try:
            code, out = run("--once")
        finally:
            stream.subprocess.run = real
            stream.KICK = False
        self.assertEqual(code, 0, out)               # never an error exit
        self.assertEqual(len(rooms()), 1)
        row = ledger_rows()[-1]
        self.assertEqual(row["kind"], "page")
        self.assertNotIn("error", row)               # never a ledger failure row
        self.assertIs(heartbeat()["ok"], True)       # never a heartbeat change
        self.assertIn("kick ·", out)                 # one log line, and that is all

    def test_no_seed_at_all_is_a_ledger_line_too(self):
        code, out = run("--once")                  # wipe_stream left the seeds folder empty
        self.assertEqual(code, 0, out)
        self.assertIsNone(ledger_rows()[-1]["room"])
        self.assertEqual(ledger_rows()[-1]["error"], "no seed")

    def test_the_tail_is_cut_to_whole_sentences(self):
        text = "a first one that runs on. the middle sentence. and the last one. a scrap"
        self.assertEqual(stream.sentences_tail(text, 40), "and the last one.")
        # nothing to cut on: the raw tail rather than nothing at all
        self.assertEqual(stream.sentences_tail("aaaa bbbb cccc", 9), "bbbb cccc")


# ---- the two routes -------------------------------------------------------------------

def make_page(name: str, seed: str, text: str, flag=None, ts=None, model=None) -> str:
    """A stream room written by hand, so the api tests do not depend on what a stub said.
    `model` is the writer's stamp (`meta.model`) — none, as on the one-server path, by default."""
    import eva as eva_mod
    s = eva_mod.blank(name, is_bare=True, root_text=seed)
    nid = "n" + name.replace("/", "").replace("-", "")[-8:]
    meta = {"logprobs": [-0.1, -2.0], "flag": flag, "params": {"temperature": 2.0},
            "seed": "seeds/x.txt"}
    if model:
        meta["model"] = model
    s["nodes"][nid] = {"id": nid, "parent": s["root"], "kind": "model", "text": text,
                       "ts": ts or time.time(), "pruned": False, "posed": False,
                       "meta": meta}
    s["current"] = nid
    loom.write_sitting(s)
    return nid


def write_heartbeat(**fields) -> None:
    os.makedirs(STREAM_DIR, exist_ok=True)
    with open(os.path.join(STREAM_DIR, "heartbeat.json"), "w", encoding="utf-8") as f:
        json.dump(fields, f)


class Routes(unittest.TestCase):
    def setUp(self):
        wipe_stream()
        make_page("stream/2026-09-19/1000", "seed one\n", "page one")
        make_page("stream/2026-09-19/1005", "seed two\n", "page two — footer", flag="copyright")
        make_page("stream/2026-09-19/1010", "seed three\n", "page three")
        make_page("stream/2026-09-20/0800", "seed four\n", "page four")

    def test_the_page_is_served(self):
        code, body = call("/stream")
        self.assertEqual(code, 200)
        self.assertIn("<title>stream</title>", body)

    def test_newest_first_and_flagged_hidden(self):
        code, d = call("/api/stream")
        self.assertEqual(code, 200)
        self.assertEqual([p["room"] for p in d["pages"]],
                         ["stream/2026-09-20/0800", "stream/2026-09-19/1010",
                          "stream/2026-09-19/1000"])
        p = d["pages"][0]
        self.assertEqual((p["seed"], p["text"]), ("seed four\n", "page four"))
        self.assertEqual((p["kept"], p["good"], p["flag"]), (False, False, None))
        self.assertEqual(p["temperature"], 2.0)
        self.assertTrue(p["node"])
        self.assertIs(d["more"], False)

    def test_all_shows_what_the_filter_caught(self):
        code, d = call("/api/stream?all=1")
        self.assertEqual(code, 200)
        self.assertEqual(len(d["pages"]), 4)
        flagged = [p for p in d["pages"] if p["room"] == "stream/2026-09-19/1005"][0]
        self.assertEqual(flagged["flag"], "copyright")

    def test_before_pages_backwards_and_n_caps_the_batch(self):
        code, d = call("/api/stream?n=1")
        self.assertEqual([p["room"] for p in d["pages"]], ["stream/2026-09-20/0800"])
        self.assertIs(d["more"], True)
        code, d = call("/api/stream?n=1&before=stream/2026-09-20/0800")
        self.assertEqual([p["room"] for p in d["pages"]], ["stream/2026-09-19/1010"])
        self.assertIs(d["more"], True)
        # the oldest one has nothing behind it
        code, d = call("/api/stream?before=stream/2026-09-19/1000")
        self.assertEqual(d["pages"], [])
        self.assertIs(d["more"], False)
        self.assertEqual(call("/api/stream?before=.trash")[0], 400)

    def test_status_is_read_off_the_heartbeat(self):
        now = time.time()
        write_heartbeat(ts=now, last_ok=now - 60, room="stream/2026-09-20/0800", ok=True)
        code, d = call("/api/stream?n=1")
        self.assertEqual(d["status"]["state"], "dreaming")
        self.assertEqual(d["status"]["interval"], 300)
        self.assertAlmostEqual(d["status"]["since"], now - 60, places=1)

        # one missed turn is still dreaming; past twice the interval it is asleep, and the
        # since-timestamp is when a page last landed
        write_heartbeat(ts=now, last_ok=now - 400, room="x", ok=True)
        self.assertEqual(call("/api/stream?n=1")[1]["status"]["state"], "dreaming")
        write_heartbeat(ts=now, last_ok=now - 3600, room="x", ok=False)
        d = call("/api/stream?n=1")[1]["status"]
        self.assertEqual(d["state"], "asleep")
        self.assertAlmostEqual(d["since"], now - 3600, places=1)

        # no heartbeat at all: asleep, and the page has nothing to print a time from
        os.unlink(os.path.join(STREAM_DIR, "heartbeat.json"))
        d = call("/api/stream?n=1")[1]["status"]
        self.assertEqual((d["state"], d["since"]), ("asleep", None))

    def test_a_mark_through_the_existing_route_shows_up_here(self):
        page = call("/api/stream?n=1")[1]["pages"][0]
        code, d = call("/api/mark", {"room": page["room"], "node": page["node"],
                                     "mark": "good", "on": True})
        self.assertEqual(code, 200, d)
        self.assertEqual((d["good"], d["kept"]), (True, False))
        back = call("/api/stream?n=1")[1]["pages"][0]
        self.assertEqual((back["good"], back["kept"]), (True, False))

        # a star pops the circle — the at-most-one rule is the server's, and this reads it
        code, d = call("/api/mark", {"room": page["room"], "node": page["node"],
                                     "mark": "kept", "on": True})
        self.assertEqual((d["kept"], d["good"]), (True, False))
        back = call("/api/stream?n=1")[1]["pages"][0]
        self.assertEqual((back["kept"], back["good"]), (True, False))

    def test_a_star_on_a_page_freezes_it_as_an_artifact(self):
        """What survives a stream room is what he starred: the rooms are untracked and
        disposable, `shelf/artifacts/` is in git. This is the existing /api/mark behaviour
        on a one-node room, pinned here so a change to it is visible."""
        page = call("/api/stream?n=1")[1]["pages"][0]
        before = {a["name"] for a in call("/api/artifacts")[1]["artifacts"]}
        call("/api/mark", {"room": page["room"], "node": page["node"],
                           "mark": "kept", "on": True})
        after = [a for a in call("/api/artifacts")[1]["artifacts"] if a["name"] not in before]
        self.assertEqual(len(after), 1, after)
        text = call("/api/artifact/text?name=" + after[0]["name"])[1]
        self.assertIn(page["seed"].strip(), text)
        self.assertIn(page["text"], text)          # seed AND page, so the room can go
        # and taking the star off trashes it again
        call("/api/mark", {"room": page["room"], "node": page["node"],
                           "mark": "kept", "on": False})
        self.assertNotIn(after[0]["name"],
                         [a["name"] for a in call("/api/artifacts")[1]["artifacts"]])


# ---- the interpreter ---------------------------------------------------------------------
# A fake `claude` first on PATH, the way berserktest does it: a script that writes the prompt
# it was handed to a file the moment it runs — so its ABSENCE is how a test proves the cli was
# never started — and answers by FAKE_MODE. It reads the passages out of the prompt, because
# what is under test is that the right passages went out and the answer came back attached to
# the right rooms.

FAKE_CLAUDE = r'''#!/usr/bin/env python3
import io, json, os, re, sys, uuid
prompt = sys.stdin.read()
with open(os.environ["FAKE_CLAUDE_LOG"], "a", encoding="utf-8") as f:
    f.write(prompt + "\n=====\n")
# The argv too, one json line per call, beside the prompts: the analyst's memory is a resumed
# session, and `--resume <id>` on the command line is the only place that shows.
with open(os.environ["FAKE_CLAUDE_LOG"] + ".argv", "a", encoding="utf-8") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
mode = os.environ.get("FAKE_MODE", "")
SESSION = ""

USAGE = {"input_tokens": 12, "cache_read_input_tokens": 6642,
         "cache_creation_input_tokens": 3, "output_tokens": 301}

def answer(text, error=False):
    # The cli's own --output-format json shape: one result event with the usage block on it.
    json.dump({"type": "result", "subtype": "success", "is_error": error, "result": text,
               "usage": USAGE, "total_cost_usd": 0.0021782, "session_id": SESSION}, sys.stdout)
    raise SystemExit(0)

if mode == "boom":
    raise SystemExit(3)

# The analyst: a session id like the real cli's — the one resumed, or a fresh one — and a
# portrait that says how many dreams it has been handed this turn, so a test can count them.
if re.search(r"^--- (the dreams|\d+ more dreams) ---$", prompt, re.M):
    if mode != "nosession":
        SESSION = sys.argv[sys.argv.index("--resume") + 1] if "--resume" in sys.argv \
            else str(uuid.uuid4())
    if mode == "garbage":
        answer("i would rather not say who this is")
    # A header is the minute, and the dreamer after it when the page says who that was.
    k = len(re.findall(r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?: · [\w.-]+)?\]$", prompt, re.M))
    # The portrait alone; the line is its closing, cut by the tool — nothing else is asked.
    answer(f"here it is\n<portrait>\n  a dreamer of {k} more dreams.\n</portrait>\n")

# The sleeper remembering asks a different question and takes a different tag.
if "--- the new scene ---" in prompt:
    if mode == "garbage":
        answer("i don't remember any of it")
    m = re.search(r"\[scene\] (.*)\Z", prompt, re.S) or \
        re.search(r"--- the new scene ---\n\n(.*)\Z", prompt, re.S)
    scene = m.group(1).strip()
    held = re.search(r"--- what you remember of the dream so far ---\n\n(.*?)\n\n---",
                     prompt, re.S).group(1).strip()
    first = held.startswith("Nothing yet")
    if mode == "seams":
        # One continuous telling with a | where each later scene comes in, mid-sentence — the
        # shape bekh asked for. The held text still carries its marks, so counting them is how
        # this stub knows which scene it is on.
        n = 1 if first else held.count("|") + 2
        seamed = ["i was in it again and the door", "was a lift going down, and the",
                  "bones sang until it", "stopped just before the end."]
        answer("<dream>" + "|".join(seamed[:n]) + "</dream><title>the seamed night</title>")
    n = 1 if first else held.count(";") + 2
    # The sleeper names the dream too since 2026-09-22, and renames it as he rewrites it — the
    # latest version's title is the story's name, so it carries the turn.
    title = "" if mode == "noname" else f"<title>the night of {n}.</title>"
    answer("<dream>I was in it again" + ("" if first else " and before that " + held.split(";")[0])
           + "; then " + scene[:40] + " (" + str(n) + ")</dream>" + title)

# The back-catalogue namer (naming.py) asks for a name and nothing else, over one dream.
if "--- the dream ---" in prompt:
    d = prompt.split("--- the dream ---", 1)[1].strip()
    if mode == "noname":
        answer("i would rather not name it")
    answer('<name>A dream about ' + d[:24].strip() + '.</name>')

# The material since 2026-09-21: the dream alone under the header, no seed and no labels; a
# block of several is cut by "passage N" lines; with STREAM_READ_SEEDS=1 the old labels return.
_m = re.search(r"--- the latest stretch ---\n\n(.*)\Z", prompt, re.S)
dreams = []
for _part in re.split(r"(?m)^passage \d+\n\n", _m.group(1) if _m else ""):
    if not _part.strip() or _part.startswith("(each passage grew"):
        continue
    if "[dream] " in _part:
        _part = _part.split("[dream] ", 1)[1]
    dreams.append(_part.rstrip("\n"))
if mode == "garbage":
    answer("i could not read these, sorry")
out = io.StringIO()
print("<reading>", file=out)
print("the switch keeps answering a call nobody placed.", file=out)
print("</reading>", file=out)
for i, d in enumerate(dreams, 1):
    if mode == "script":
        body = "<script>alert(1)</script> " + d
    elif mode == "unbalanced":
        body = "<mark>one</mark></mark> two <mark>three"
    elif mode == "altered":
        # five different things for the diff to tell apart: a word replaced, a word inserted
        # inside an underline, a sentence dropped, an underline on a word he did NOT touch,
        # and whitespace he normalised
        body = d.replace("switch", "SWITCH", 1).replace("\n\n", "\n")
        body = body.replace("hums", "<mark>hums quietly</mark>", 1)
        body = body.replace("The second sentence goes. ", "")
        body = body.replace("line", "<mark>line</mark>", 1)
    else:
        body = d
    print(f'<passage n="{i}">{body}</passage>', file=out)
# The name, last, as bekh's paragraph asks for it — with the prefix he told it NOT to write and
# a full stop, because that is what a voice does anyway and the cleaning is what catches it.
if mode != "noname" and dreams:
    print(f'<name>A dream about {dreams[-1][:24].strip()}.</name>', file=out)
answer(out.getvalue())
'''


def fake_claude(mode: str = "") -> dict:
    """A bin dir with the fake first on PATH, and the env that reaches it. Returns the paths
    so a test can assert on the prompt — or on the log file not existing at all."""
    d = tempfile.mkdtemp(prefix="stream-claude-")
    binp = os.path.join(d, "bin")
    os.makedirs(binp)
    path = os.path.join(binp, "claude")
    with open(path, "w", encoding="utf-8") as f:
        f.write(FAKE_CLAUDE.replace("#!/usr/bin/env python3", "#!" + sys.executable))
    os.chmod(path, 0o755)
    return {"dir": d, "bin": binp, "log": os.path.join(d, "prompts.txt"), "mode": mode}


def with_fake(fake: dict, fn):
    """Run something with the fake claude first on PATH, and put the env back after."""
    was_path, was_mode = os.environ.get("PATH", ""), os.environ.get("FAKE_MODE")
    os.environ["PATH"] = fake["bin"] + os.pathsep + was_path
    os.environ["FAKE_CLAUDE_LOG"] = fake["log"]
    os.environ["FAKE_MODE"] = fake["mode"]
    out = io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(out):
            code = fn()
    finally:
        os.environ["PATH"] = was_path
        if was_mode is None:
            os.environ.pop("FAKE_MODE", None)
        else:
            os.environ["FAKE_MODE"] = was_mode
    return code, out.getvalue()


def interpret(fake: dict) -> tuple[int, str]:
    return with_fake(fake, lambda: interpreter.main(["interpreter.py", "--once"]))


def remember(fake: dict) -> tuple[int, str]:
    return with_fake(fake, lambda: remembering.main(["remembering.py", "--once"]))


def dream_versions() -> list[dict]:
    out = []
    for path in remembering.version_files():
        with open(path, encoding="utf-8") as f:
            out.append(json.load(f))
    out.sort(key=lambda d: d.get("ts") or 0)
    return out


def readings_on_disk() -> list[dict]:
    out = []
    for path in interpreter.reading_files():
        with open(path, encoding="utf-8") as f:
            out.append(json.load(f))
    out.sort(key=lambda d: d.get("ts") or 0)
    return out


def put_reading(rooms: list[str], text: str, ts: float) -> None:
    """A reading straight onto disk, for the memory test: writing six of them through the
    interpreter would mean twelve passages and twelve fake calls."""
    lt = time.localtime(ts)
    day = os.path.join(STREAM_DIR, "readings", time.strftime("%Y-%m-%d", lt))
    os.makedirs(day, exist_ok=True)
    with open(os.path.join(day, f"{int(ts)}.json"), "w", encoding="utf-8") as f:
        json.dump({"ts": ts, "rooms": rooms, "reading": text, "marked": {}, "segments": {},
                   "model": "opus", "seconds": 1.0}, f)


class OpusName(unittest.TestCase):
    """What the ledger says wrote a note is the id the cli reports, not the alias we asked for
    (bekh, 2026-09-23: he wanted to know the seat is really on the newest opus)."""

    def test_the_cli_names_the_model_and_a_silent_cli_leaves_the_alias(self):
        said = {"modelUsage": {"claude-opus-5-5": {"canonicalModel": "claude-opus-5-5"}}}
        self.assertEqual(opus.model_of(said), "claude-opus-5-5")
        # a fallback mid-run: the last entry is what finished the answer
        two = {"modelUsage": {"claude-opus-5-5": {"canonicalModel": "claude-opus-5-5"},
                              "claude-sonnet-5": {"canonicalModel": "claude-sonnet-5"}}}
        self.assertEqual(opus.model_of(two), "claude-sonnet-5")
        # nothing, junk, or a key with no canonical name
        self.assertEqual(opus.model_of({}), "opus")
        self.assertEqual(opus.model_of({"modelUsage": "nonsense"}), "opus")
        self.assertEqual(opus.model_of({"modelUsage": {"claude-opus-5-5": {}}}), "claude-opus-5-5")


class Interpreter(unittest.TestCase):
    def setUp(self):
        wipe_stream()
        self.fakes = []
        self.every = interpreter.EVERY

    def block_of(self, n: int) -> None:
        """A note covers one passage by default; the file format still holds a block of
        several, and the old readings on the shelf are blocks of two."""
        interpreter.EVERY = n
        self.addCleanup(setattr, interpreter, "EVERY", self.every)

    def tearDown(self):
        for f in self.fakes:
            shutil.rmtree(f["dir"], ignore_errors=True)

    def fake(self, mode: str = "") -> dict:
        f = fake_claude(mode)
        self.fakes.append(f)
        return f

    def pages(self, *specs) -> list[str]:
        """Rooms oldest first; a spec is (hhmm, dream) or (hhmm, dream, flag)."""
        out = []
        for spec in specs:
            hhmm, text = spec[0], spec[1]
            flag = spec[2] if len(spec) > 2 else None
            name = f"stream/2026-09-19/{hhmm}"
            make_page(name, f"seed for {hhmm}\n", text, flag=flag)
            out.append(name)
        return out

    def test_one_new_passage_is_a_note(self):
        """The default since 2026-09-19: a note for every generation."""
        self.assertEqual(interpreter.EVERY, 1)
        rooms = self.pages(("1000", "the switch hums."))
        f = self.fake()
        code, out = interpret(f)
        self.assertEqual(code, 0, out)
        got = readings_on_disk()
        self.assertEqual([d["rooms"] for d in got], [rooms])

    def test_nothing_new_is_read_by_nobody(self):
        self.pages(("1000", "one."))
        self.assertEqual(interpret(self.fake())[0], 0)      # covers it
        f = self.fake()
        code, out = interpret(f)
        self.assertEqual(code, 0, out)
        # The fake writes its log the moment it runs, so its absence is the proof.
        self.assertFalse(os.path.exists(f["log"]), "claude was started with nothing new")
        self.assertEqual(len(readings_on_disk()), 1)

    def test_a_short_stretch_is_not_read_at_all(self):
        self.block_of(2)
        self.pages(("1000", "only one passage so far."))
        f = self.fake()
        code, out = interpret(f)
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(f["log"]), "claude was started for one passage")
        self.assertEqual(readings_on_disk(), [])
        self.assertEqual(ledger_rows(), [])          # not even a row: this is the usual state

    def test_the_block_is_the_newest_two_unflagged(self):
        self.block_of(2)
        self.pages(("1000", "the oldest one."), ("1005", "a footer.", "copyright"),
                   ("1010", "the switch hums. The second sentence goes."),
                   ("1015", "the newest one."))
        f = self.fake()
        self.assertEqual(interpret(f)[0], 0)
        got = readings_on_disk()
        self.assertEqual(len(got), 1)
        # newest first on the file, and the flagged one is not in it
        self.assertEqual(got[0]["rooms"],
                         ["stream/2026-09-19/1015", "stream/2026-09-19/1010"])
        self.assertEqual(got[0]["reading"],
                         "the switch keeps answering a call nobody placed.")
        # the prompt read them oldest first, and the seeds stayed out of his sight
        prompt = read_text(f["log"])
        self.assertLess(prompt.index("the switch hums"), prompt.index("the newest one."))
        self.assertNotIn("seed for 1015", prompt)
        self.assertNotIn("[dream]", prompt)
        self.assertNotIn("a footer.", prompt)
        row = [r for r in ledger_rows() if r.get("kind") == "reading"][-1]
        self.assertEqual(row["rooms"], got[0]["rooms"])
        self.assertEqual(row["marked"], 2)

        # and a second run has nothing above the watermark, so it asks nobody
        f2 = self.fake()
        self.assertEqual(interpret(f2)[0], 0)
        self.assertFalse(os.path.exists(f2["log"]))

    def test_the_persona_file_goes_out_verbatim(self):
        self.block_of(2)
        self.pages(("1000", "one."), ("1005", "two."))
        f = self.fake()
        self.assertEqual(interpret(f)[0], 0)
        with open(interpreter.PERSONA, encoding="utf-8") as fh:
            persona = fh.read()
        prompt = read_text(f["log"])
        self.assertIn(persona.rstrip("\n"), prompt)
        # the plumbing is appended after it and is not in bekh's file
        self.assertNotIn("<reading>", persona)
        self.assertIn("<passage n=\"1\">", prompt)

    def test_no_memory_by_default_and_the_last_four_when_it_is_turned_on(self):
        self.block_of(2)
        for i in range(6):
            put_reading([f"stream/2026-09-18/{1000 + i}"], f"memory number {i}",
                        time.time() - 10000 + i)
        # Off by default: shown his own notes he copied their format, 81 of 97 opening
        # "Last time…" on the first day. Not one of them may reach the prompt.
        self.pages(("1050", "zero."), ("1055", "half."))
        f0 = self.fake()
        self.assertEqual(interpret(f0)[0], 0)
        self.assertNotIn("memory number", read_text(f0["log"]))

        was = interpreter.MEMORY
        interpreter.MEMORY = 4
        self.addCleanup(setattr, interpreter, "MEMORY", was)
        self.pages(("1100", "one."), ("1105", "two."))
        f = self.fake()
        self.assertEqual(interpret(f)[0], 0)
        prompt = read_text(f["log"])
        for i in (3, 4, 5):
            self.assertIn(f"memory number {i}", prompt)
        for i in (0, 1):
            self.assertNotIn(f"memory number {i}", prompt)

    def test_an_unreadable_answer_is_a_ledger_row_and_exit_zero(self):
        self.block_of(2)
        self.pages(("1000", "one."), ("1005", "two."))
        code, out = interpret(self.fake("garbage"))
        self.assertEqual(code, 0, out)
        self.assertEqual(readings_on_disk(), [])
        row = [r for r in ledger_rows() if r.get("kind") == "reading"][-1]
        self.assertIn("no <reading>", row["error"])
        self.assertEqual(len(row["rooms"]), 2)

    def test_a_cli_that_dies_is_a_ledger_row_too(self):
        self.block_of(2)
        self.pages(("1000", "one."), ("1005", "two."))
        self.assertEqual(interpret(self.fake("boom"))[0], 0)
        self.assertIn("exited 3",
                      [r for r in ledger_rows() if r.get("kind") == "reading"][-1]["error"])

    # ---- his copy, kept as he typed it ----------------------------------------------------
    def test_two_marks_and_what_they_mean(self):
        """Since 2026-09-21 he marks two things and the colours mean them: touched and
        strange. Legacy `<mark>` still reads, because nothing on the shelf is rewritten."""
        segs, dropped = interpreter.segments_of(
            "a <touched>one</touched> b <strange>two</strange> c")
        self.assertEqual([(x["t"], x["mark"]) for x in segs],
                         [("a ", False), ("one", "touched"), (" b ", False),
                          ("two", "strange"), (" c", False)])
        self.assertEqual(dropped, 0)
        self.assertEqual(interpreter.segments_of("a <mark>legacy</mark> b")[0][1],
                         {"t": "legacy", "mark": True})
        self.assertEqual(interpreter.segments_of("no tags"),
                         ([{"t": "no tags", "mark": False}], 0))
        # runs of one state join, so the page draws one span and not one per word
        self.assertEqual(interpreter.segments_of("<mark>a</mark><mark>b</mark>")[0],
                         [{"t": "ab", "mark": True}])

    def test_the_first_of_each_kind_wins_and_the_rest_go_plain(self):
        segs, dropped = interpreter.segments_of(
            "<touched>one</touched> x <touched>two</touched> y <strange>s</strange>")
        self.assertEqual(dropped, 1)
        self.assertEqual([(x["t"], x["mark"]) for x in segs],
                         [("one", "touched"), (" x two y ", False), ("s", "strange")])
        # the text is never lost, only the paint
        self.assertIn("two", "".join(x["t"] for x in segs))
        # and an unclosed tag paints to the end rather than throwing
        self.assertEqual(interpreter.segments_of("a <touched>unclosed b")[0][-1],
                         {"t": "unclosed b", "mark": "touched"})

    def test_an_altered_copy_is_stored_and_served_exactly_as_typed(self):
        dream = "the switch hums.\n\nThe second sentence goes. the line stayed open."
        self.pages(("1005", dream))
        self.assertEqual(interpret(self.fake("altered"))[0], 0)
        got = readings_on_disk()[0]
        room = "stream/2026-09-19/1005"
        # his copy, verbatim, tags and all
        self.assertIn("<mark>", got["marked"][room])
        self.assertIn("SWITCH", got["marked"][room])
        # the room on the shelf is untouched — the record is still the record
        node = [v for v in on_disk(room)["nodes"].values() if v["kind"] == "model"][0]
        self.assertEqual(node["text"], dream)
        segs = got["segments"][room]
        # nothing is compared against the dream any more: no kinds, no red, just his text
        self.assertEqual({k for x in segs for k in x}, {"t", "mark"})
        import re as _re
        self.assertEqual("".join(x["t"] for x in segs),
                         _re.sub(r"</?(touched|strange|mark)>", "", got["marked"][room]))
        self.assertTrue(any(x["mark"] for x in segs))
        row = [r for r in ledger_rows() if r.get("kind") == "reading"][-1]
        self.assertNotIn("new", row)
        self.assertNotIn("gone", row)

    def test_only_mark_is_a_tag_and_a_stray_close_is_survivable(self):
        segs, _ = interpreter.segments_of("a <b><touched>bold</touched></b></touched> claim")
        whole = "".join(x["t"] for x in segs)
        self.assertIn("<b>", whole)                  # any other tag is characters, not markup
        self.assertNotIn("<touched>", whole)
        self.assertTrue(any(x["mark"] and "bold" in x["t"] for x in segs))

    # ---- what the api does with all that --------------------------------------------------
    def test_the_api_carries_the_copy_and_hangs_the_reading_on_the_head(self):
        self.block_of(2)
        rooms = self.pages(("1000", "one."), ("1005", "two."))
        self.assertEqual(interpret(self.fake())[0], 0)
        d = call("/api/stream?n=5")[1]
        by = {p["room"]: p for p in d["pages"]}
        head, tail = rooms[1], rooms[0]              # newest is the head of the block
        self.assertEqual(by[head]["reading"]["text"],
                         "the switch keeps answering a call nobody placed.")
        self.assertEqual(by[head]["reading"]["rooms"], [head, tail])
        self.assertIsNone(by[tail]["reading"])       # one reading per block, on its head
        for r in (head, tail):
            self.assertTrue(by[r]["segments"])
            self.assertEqual("".join(s["t"] for s in by[r]["segments"]), by[r]["text"])

    def test_a_page_nobody_has_read_carries_nulls(self):
        self.pages(("1000", "alone."))
        p = call("/api/stream?n=1")[1]["pages"][0]
        self.assertIsNone(p["marked"])
        self.assertIsNone(p["segments"])
        self.assertIsNone(p["reading"])

    def test_a_script_tag_in_his_copy_reaches_the_page_as_text(self):
        self.block_of(2)
        self.pages(("1000", "one."), ("1005", "the door."))
        self.assertEqual(interpret(self.fake("script"))[0], 0)
        p = [x for x in call("/api/stream?n=5")[1]["pages"]
             if x["room"] == "stream/2026-09-19/1005"][0]
        # It survives as characters in a segment — the page renders every segment with
        # textContent, so this can only ever be read and never run.
        self.assertIn("<script>", "".join(s["t"] for s in p["segments"]))
        self.assertIn("<script>", p["marked"])

    def test_an_old_readings_gone_segments_still_reach_the_page(self):
        """Reading files written before 2026-09-19 carry a `kind` per segment from the retype
        check. They are served as they are — the page drops the `gone` ones, which is where
        that decision belongs; nothing rewrites a file on the shelf."""
        room = self.pages(("1000", "the line stayed open."))[0]
        day = os.path.join(STREAM_DIR, "readings", "2026-09-18")
        os.makedirs(day, exist_ok=True)
        with open(os.path.join(day, "2300.json"), "w", encoding="utf-8") as f:
            json.dump({"ts": time.time() - 3600, "rooms": [room], "reading": "an old note",
                       "marked": {room: "the line <mark>stayed</mark> shut."},
                       "segments": {room: [{"t": "the line ", "mark": False, "kind": "same"},
                                           {"t": "stayed", "mark": True, "kind": "same"},
                                           {"t": " open.", "mark": False, "kind": "gone"},
                                           {"t": " shut.", "mark": False, "kind": "new"}]},
                       "model": "opus", "seconds": 1.0}, f)
        p = [x for x in call("/api/stream?n=5")[1]["pages"] if x["room"] == room][0]
        self.assertEqual(p["reading"]["text"], "an old note")
        kept = [x for x in p["segments"] if x.get("kind") != "gone"]
        self.assertEqual("".join(x["t"] for x in kept), "the line stayed shut.")

    def test_unbalanced_marks_still_produce_segments(self):
        self.block_of(2)
        self.pages(("1000", "one."), ("1005", "one two three"))
        self.assertEqual(interpret(self.fake("unbalanced"))[0], 0)
        p = [x for x in call("/api/stream?n=5")[1]["pages"]
             if x["room"] == "stream/2026-09-19/1005"][0]
        segs = p["segments"]
        self.assertTrue(segs)
        self.assertTrue(any(s["mark"] for s in segs))
        self.assertNotIn("<mark>", "".join(s["t"] for s in segs))
        self.assertEqual("".join(s["t"] for s in segs), "one two three")


# ---- the reader's other family ---------------------------------------------------------------
# A stub `codex` beside the stub `claude`, speaking the cli's JSONL event stream: a
# `thread.started`, one `item.completed` carrying the agent message, one `turn.completed`
# carrying the token counts. It writes its own ARGV as well as the prompt, because half of
# what this seat is made of is flags — base_instructions, the seat dir, the sandbox.

FAKE_CODEX_READER = r'''#!/usr/bin/env python3
import io, json, os, re, sys
prompt = sys.stdin.read()
with open(os.environ["FAKE_CODEX_LOG"], "w", encoding="utf-8") as f:
    f.write("\n".join(sys.argv[1:]) + "\n=====\n" + prompt)
mode = os.environ.get("FAKE_CODEX_MODE", "")
if mode == "boom":
    raise SystemExit(4)

def event(d):
    json.dump(d, sys.stdout); sys.stdout.write("\n")

_m = re.search(r"--- the latest stretch ---\n\n(.*)\Z", prompt, re.S)
dreams = [p.rstrip("\n") for p in re.split(r"(?m)^passage \d+\n\n", _m.group(1) if _m else "")
          if p.strip()]
if mode == "garbage":
    text = "I had a look but there is nothing here I can read."
else:
    out = io.StringIO()
    print("<reading>", file=out)
    print("gpt read it and pencilled this in the margin.", file=out)
    print("</reading>", file=out)
    for i, d in enumerate(dreams, 1):
        print('<passage n="%d">%s</passage>' % (i, d), file=out)
    print('<name>a dream about %s</name>' % (dreams[-1][:20].strip() if dreams else "nothing"),
          file=out)
    text = out.getvalue()
event({"type": "thread.started", "thread_id": "t1"})
event({"type": "item.completed", "item": {"type": "agent_message", "text": text}})
event({"type": "turn.completed",
       "usage": {"input_tokens": 2100, "cached_input_tokens": 1800,
                 "cache_write_input_tokens": 0, "output_tokens": 180,
                 "reasoning_output_tokens": 0, "total_tokens": 2280}})
'''


def fake_reader(codex_mode: str = "", claude_mode: str = "") -> dict:
    """One bin dir holding BOTH stubs, since a fallback run starts one and then the other."""
    d = tempfile.mkdtemp(prefix="stream-reader-")
    binp = os.path.join(d, "bin")
    os.makedirs(binp)
    for name, body in (("codex", FAKE_CODEX_READER), ("claude", FAKE_CLAUDE)):
        path = os.path.join(binp, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(body.replace("#!/usr/bin/env python3", "#!" + sys.executable))
        os.chmod(path, 0o755)
    return {"dir": d, "bin": binp, "log": os.path.join(d, "prompts.txt"),
            "codex_log": os.path.join(d, "codex.txt"), "mode": claude_mode,
            "codex_mode": codex_mode}


def interpret_as(reader: str, fake: dict) -> tuple[int, str]:
    was_reader, was_codex_mode = interpreter.READER, os.environ.get("FAKE_CODEX_MODE")
    interpreter.READER = reader
    os.environ["FAKE_CODEX_LOG"] = fake["codex_log"]
    os.environ["FAKE_CODEX_MODE"] = fake["codex_mode"]
    try:
        return with_fake(fake, lambda: interpreter.main(["interpreter.py", "--once"]))
    finally:
        interpreter.READER = was_reader
        if was_codex_mode is None:
            os.environ.pop("FAKE_CODEX_MODE", None)
        else:
            os.environ["FAKE_CODEX_MODE"] = was_codex_mode


class CodexReader(unittest.TestCase):
    """bekh, 2026-09-21: *we use opus on the left and opus on the right… how about we use
    codex for the summarization of the dreams, so they are two different families.* The switch
    changes who answers and nothing else — same prompt, same parser, same storage."""

    def setUp(self):
        wipe_stream()
        self.fakes = []

    def tearDown(self):
        for f in self.fakes:
            shutil.rmtree(f["dir"], ignore_errors=True)

    def fake(self, codex_mode: str = "", claude_mode: str = "") -> dict:
        f = fake_reader(codex_mode, claude_mode)
        self.fakes.append(f)
        return f

    def page(self, hhmm: str = "1000", text: str = "the switch hums.") -> str:
        name = f"stream/2026-09-19/{hhmm}"
        make_page(name, f"seed for {hhmm}\n", text)
        return name

    def test_codex_is_sent_the_same_prompt_and_writes_the_note(self):
        room = self.page()
        f = self.fake()
        code, out = interpret_as("codex", f)
        self.assertEqual(code, 0, out)
        got = readings_on_disk()
        self.assertEqual([d["rooms"] for d in got], [[room]])
        self.assertEqual(got[0]["model"], "codex:" + codex.MODEL)
        self.assertEqual(got[0]["reading"], "gpt read it and pencilled this in the margin.")
        self.assertEqual(got[0]["usage"]["tokens"], 2280)
        self.assertFalse(os.path.exists(f["log"]), "opus was started as well")

        argv, prompt = read_text(f["codex_log"]).split("\n=====\n", 1)
        # bekh's persona file goes out verbatim, exactly as it does to opus, and the plumbing
        # that is not his is appended after it — same prompt, different family.
        with open(interpreter.PERSONA, encoding="utf-8") as fh:
            self.assertIn(fh.read().rstrip("\n"), prompt)
        self.assertIn('<passage n="1">', prompt)
        self.assertIn("the switch hums.", prompt)
        self.assertNotIn("seed for 1000", prompt)          # no seed
        self.assertNotIn("your own earlier readings", prompt)   # no memory

        # and the flags that make this a reading seat instead of a coding agent
        self.assertIn("base_instructions=", argv)
        self.assertIn(codex.SEAT, argv.splitlines())
        self.assertIn("-C", argv.splitlines())
        self.assertIn("--json", argv.splitlines())
        self.assertIn("read-only", argv.splitlines())
        self.assertIn(codex.MODEL, argv.splitlines())
        row = [r for r in ledger_rows() if r.get("kind") == "reading"][-1]
        self.assertEqual(row["model"], "codex:" + codex.MODEL)
        self.assertNotIn("fell_back", row)

    def test_the_seat_carries_a_countermand_of_the_global_instructions(self):
        """The strong channel. No flag turns ~/.codex/AGENTS.md off, so the seat's own file
        has to be there and has to say the work doctrine is off."""
        with open(os.path.join(codex.SEAT, "AGENTS.md"), encoding="utf-8") as f:
            said = f.read().lower()
        for word in ("no tools", "countermand", "prompt"):
            self.assertIn(word, said)

    def test_codex_garbage_is_opuss_note(self):
        """A note belongs to a dream and nothing later fills the hole, so an answer with no
        <reading> in it costs one fallback, not one missing note."""
        self.page()
        f = self.fake(codex_mode="garbage")
        code, out = interpret_as("codex", f)
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.exists(f["codex_log"]), "codex was never asked")
        got = readings_on_disk()
        self.assertEqual([d["model"] for d in got], ["opus"])
        self.assertIn("no <reading>",
                      [r for r in ledger_rows() if r.get("kind") == "reading"][-1]["fell_back"])

    def test_a_dead_codex_is_opuss_note_too(self):
        self.page()
        self.assertEqual(interpret_as("codex", self.fake(codex_mode="boom"))[0], 0)
        row = [r for r in ledger_rows() if r.get("kind") == "reading"][-1]
        self.assertEqual(row["model"], "opus")
        self.assertIn("exited 4", row["fell_back"])

    def test_both_families_down_is_a_ledger_row_and_exit_zero(self):
        self.page()
        code, out = interpret_as("codex", self.fake(codex_mode="boom", claude_mode="boom"))
        self.assertEqual(code, 0, out)
        self.assertEqual(readings_on_disk(), [])
        self.assertIn("exited 3",
                      [r for r in ledger_rows() if r.get("kind") == "reading"][-1]["error"])

    def test_the_default_is_opus_and_codex_is_never_started(self):
        self.assertEqual(interpreter.READER, "opus")
        self.page()
        f = self.fake()
        self.assertEqual(interpret_as("opus", f)[0], 0)
        self.assertFalse(os.path.exists(f["codex_log"]), "codex was started by an opus seat")
        self.assertEqual([d["model"] for d in readings_on_disk()], ["opus"])

    def test_a_reader_nobody_has_heard_of_is_refused_loudly(self):
        self.page()
        code, out = interpret_as("gpt2", self.fake())
        self.assertEqual(code, 2)
        self.assertIn("STREAM_READER", out)

    def test_the_event_stream_is_read_leniently(self):
        text, usage = codex.parse(
            'not json at all\n'
            '{"type": "thread.started", "thread_id": "t"}\n'
            '{"type": "error", "message": "Reconnecting... 2/5"}\n'
            '{"type": "item.completed", "item": {"type": "agent_message", "text": "a note"}}\n'
            '{"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 3}}\n')
        # A mid-stream error it recovered from is not a failure: fim.py lost whole answers to
        # treating the first one as fatal.
        self.assertEqual(text, "a note")
        self.assertEqual(usage["tokens"], 13)          # no total given: in + out
        with self.assertRaises(ValueError):
            codex.parse('{"type": "error", "message": "it fell over"}')


# ---- names, chapters and verses --------------------------------------------------------------
# bekh, 2026-09-22: the page has very little separation between dreams and he does not read them
# all, so the names are a MENU — every dream named by the reader, every story named by the
# sleeper, and every dream carrying a psalm's number, `12:3` for the third scene of the twelfth
# story.

class Names(unittest.TestCase):
    def setUp(self):
        wipe_stream()
        self.fakes = []

    def tearDown(self):
        for f in self.fakes:
            shutil.rmtree(f["dir"], ignore_errors=True)

    def fake(self, mode: str = "") -> dict:
        f = fake_claude(mode)
        self.fakes.append(f)
        return f

    def codex_fake(self, mode: str = "") -> dict:
        f = fake_reader(mode)
        self.fakes.append(f)
        return f

    def page(self, hhmm: str = "1000", text: str = "the switch hums under the floor") -> str:
        name = f"stream/2026-09-19/{hhmm}"
        make_page(name, f"seed for {hhmm}\n", text)
        return name

    # ---- what a name is, once it has been cleaned ---------------------------------------------
    def test_the_prefix_and_the_full_stop_come_off(self):
        """His paragraph says to write only what comes after "a dream about" — and a voice
        writes it anyway. The page says that half once, in how it is laid out."""
        for raw, want in (("A dream about a monster of the sea.", "a monster of the sea"),
                          ("  dream about: the brass head  ", "the brass head"),
                          ('"the widows’ names"', "the widows’ names"),
                          ("a line\nthat wrapped", "a line that wrapped"),
                          ("", "")):
            self.assertEqual(interpreter.clean_name(raw), want)
        long = interpreter.clean_name("x " * 200)
        self.assertLessEqual(len(long), interpreter.NAME_MAX + 1)
        self.assertTrue(long.endswith("…"))

    def test_the_reader_names_the_dream(self):
        room = self.page()
        f = self.fake()
        code, out = interpret(f)
        self.assertEqual(code, 0, out)
        d = readings_on_disk()[0]
        self.assertEqual(d["names"], {room: "the switch hums under th"})
        # bekh's own paragraph went out, verbatim and last
        prompt = read_text(f["log"])
        with open(interpreter.PERSONA, encoding="utf-8") as fh:
            self.assertIn("Last, name the dream.", fh.read())
        self.assertIn("<name>", prompt)             # the plumbing's shape, not his file
        row = [r for r in ledger_rows() if r.get("kind") == "reading"][-1]
        self.assertEqual(row["name"], "the switch hums under th")

    def test_a_note_with_no_name_is_still_a_note(self):
        room = self.page()
        self.assertEqual(interpret(self.fake("noname"))[0], 0)
        d = readings_on_disk()[0]
        self.assertEqual(d["names"], {})
        self.assertEqual(d["rooms"], [room])        # the note landed anyway
        self.assertTrue(d["reading"])

    def test_the_codex_seat_names_it_too(self):
        room = self.page()
        f = self.codex_fake()
        code, out = interpret_as("codex", f)
        self.assertEqual(code, 0, out)
        d = readings_on_disk()[0]
        self.assertEqual(d["names"], {room: "the switch hums unde"})
        self.assertEqual(d["model"], "codex:" + codex.MODEL)

    # ---- the story's name, and its chapter -----------------------------------------------------
    def test_the_sleeper_names_the_story_and_the_latest_wins(self):
        self.scene("1000", "a door in the corridor.")
        self.assertEqual(remember(self.fake())[0], 0)
        self.scene("1005", "and then the stairs.")
        self.assertEqual(remember(self.fake())[0], 0)
        v = dream_versions()
        self.assertEqual(v[0]["title"], "the night of 1")
        # renamed as it was rewritten, which is the point: a dream of four scenes is not the
        # dream its first scene looked like
        self.assertNotEqual(v[1]["title"], v[0]["title"])
        # one story, one chapter, and the verse is the turn
        self.assertEqual([x["chapter"] for x in v], [1, 1])
        self.assertEqual([x["turn"] for x in v], [1, 2])
        # and the api shows the LATEST title for the whole pack
        got = {p["room"]: p for p in call("/api/stream?n=5")[1]["pages"]}
        self.assertEqual(got["stream/2026-09-19/1000"]["story"]["title"], v[1]["title"])
        self.assertEqual(got["stream/2026-09-19/1000"]["verse"], "1:1")
        self.assertEqual(got["stream/2026-09-19/1005"]["verse"], "1:2")

    def test_a_story_with_no_title_is_still_a_story(self):
        self.scene("1000", "a door.")
        self.assertEqual(remember(self.fake("noname"))[0], 0)
        self.assertEqual(dream_versions()[0]["title"], "")
        self.assertTrue(dream_versions()[0]["text"])

    def test_chapters_count_up_and_never_reset(self):
        """A chapter is handed out once, when a story starts, and stored on every version of
        it. Never a count of what is on the shelf: pruning is coming, and an address that
        shifted under him would make every number he remembers a lie."""
        was = remembering.TURNS
        remembering.TURNS = 1                     # one scene a story, so three stories are quick
        self.addCleanup(setattr, remembering, "TURNS", was)
        for i, hhmm in enumerate(("1000", "1005", "1010")):
            self.scene(hhmm, f"scene {i}.")
            self.assertEqual(remember(self.fake())[0], 0)
        v = dream_versions()
        self.assertEqual([x["chapter"] for x in v], [1, 2, 3])
        self.assertEqual(len({x["dream"] for x in v}), 3)

        # and the oldest story is pruned away: the next one is still 4
        os.unlink(remembering.version_files()[0])
        self.scene("1015", "scene 3.")
        self.assertEqual(remember(self.fake())[0], 0)
        self.assertEqual(dream_versions()[-1]["chapter"], 4)

    def test_the_backfill_numbers_old_stories_in_order_and_is_idempotent(self):
        """`--number`, the one-off for the stories written before the numbering."""
        for i, hhmm in enumerate(("1000", "1005", "1010")):
            self.scene(hhmm, f"scene {i}.")
            self.assertEqual(remember(self.fake())[0], 0)
        # strip the chapters back off, as the shelf's own files have them
        for path in remembering.version_files():
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
            d.pop("chapter", None)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(d, fh)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(remembering.main(["remembering.py", "--number"]), 0)
        self.assertIn("versions numbered", out.getvalue())
        first = [(x["dream"], x["chapter"]) for x in dream_versions()]
        self.assertEqual(sorted({c for _d, c in first}), [1])   # one story of three scenes
        # again, and nothing changes
        out2 = io.StringIO()
        with redirect_stdout(out2):
            self.assertEqual(remembering.main(["remembering.py", "--number"]), 0)
        self.assertEqual([(x["dream"], x["chapter"]) for x in dream_versions()], first)
        self.assertIn("0 versions numbered", out2.getvalue())

    def scene(self, hhmm: str, text: str) -> str:
        name = f"stream/2026-09-19/{hhmm}"
        make_page(name, f"seed for {hhmm}\n", text)
        return name

    # ---- the api ------------------------------------------------------------------------------
    def test_the_api_carries_the_name_the_verse_and_the_story(self):
        room = self.page("1100", "the switch hums under the floor")
        self.assertEqual(interpret(self.fake())[0], 0)
        self.assertEqual(remember(self.fake())[0], 0)
        p = [x for x in call("/api/stream?n=5")[1]["pages"] if x["room"] == room][0]
        self.assertEqual(p["name"], "the switch hums under th")
        self.assertEqual(p["verse"], "1:1")            # first scene of the first story
        self.assertEqual(p["story"]["chapter"], 1)
        self.assertEqual(p["story"]["title"], "the night of 1")

    def test_a_dream_nobody_named_carries_nulls(self):
        room = self.page("1200", "nobody read this one")
        p = [x for x in call("/api/stream?n=5")[1]["pages"] if x["room"] == room][0]
        self.assertIsNone(p["name"])
        self.assertIsNone(p["verse"])


# ---- naming the back catalogue -----------------------------------------------------------------
# bekh, 2026-09-22: *i have basically infinite tokens for this… leave codex alone.* The ~150
# dreams dreamt before names existed are named by opus, in their own small store, and no note
# on the shelf is touched — a reading file is the whole reading, and the newest one for a room
# is what the page shows.

def name_them(fake: dict, *args) -> tuple[int, str]:
    return with_fake(fake, lambda: naming.main(["naming.py", *args]))


class Naming(unittest.TestCase):
    def setUp(self):
        wipe_stream()
        self.fakes = []

    def tearDown(self):
        for f in self.fakes:
            shutil.rmtree(f["dir"], ignore_errors=True)

    def fake(self, mode: str = "") -> dict:
        f = fake_claude(mode)
        self.fakes.append(f)
        return f

    def page(self, hhmm: str, text: str, day: str = "2026-09-19", flag=None) -> str:
        name = f"stream/{day}/{hhmm}"
        make_page(name, f"seed for {hhmm}\n", text, flag=flag)
        return name

    def store(self, day: str) -> dict:
        path = os.path.join(STREAM_DIR, "names", day + ".json")
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_the_prompt_is_bekhs_paragraph_and_the_dream_alone(self):
        room = self.page("1000", "a monster of the sea in the flat")
        f = self.fake()
        code, out = name_them(f, "--unnamed")
        self.assertEqual(code, 0, out)
        prompt = read_text(f["log"])
        with open(interpreter.PERSONA, encoding="utf-8") as fh:
            para = [p for p in fh.read().split("\n\n")
                    if p.strip().startswith("Last, name the dream.")][0].strip()
        self.assertIn(para, prompt)                     # verbatim, out of his own file
        self.assertIn("a monster of the sea in the flat", prompt)
        self.assertNotIn("seed for 1000", prompt)       # no seed, like every other voice
        self.assertNotIn("<reading>", prompt)           # names only: never a note
        self.assertEqual(self.store("2026-09-19"), {room: "a monster of the sea in"})
        row = [r for r in ledger_rows() if r.get("kind") == "name"][-1]
        self.assertEqual((row["rooms"], row["model"]), ([room], "opus"))
        self.assertTrue(row["usage"]["cache_read_input_tokens"])

    def test_it_never_touches_a_reading(self):
        """The dreams it names already have notes. A naming pass that wrote reading files
        would put an empty copy over every marked one on the page."""
        room = self.page("1005", "the switch hums")
        self.assertEqual(interpret(self.fake())[0], 0)
        before = {p: (os.path.getmtime(p), read_text(p))
                  for p in interpreter.reading_files()}
        # the reader already named it, so --unnamed passes it by and asks nobody
        f = self.fake()
        self.assertEqual(name_them(f, "--unnamed")[0], 0)
        self.assertFalse(os.path.exists(f["log"]), "opus was asked about a named dream")
        # and naming it by hand still writes no reading file
        self.assertEqual(name_them(self.fake(), "--room", room)[0], 0)
        after = {p: (os.path.getmtime(p), read_text(p))
                 for p in interpreter.reading_files()}
        self.assertEqual(after, before)
        # the note's own name still wins on the page
        p = [x for x in call("/api/stream?n=5")[1]["pages"] if x["room"] == room][0]
        self.assertEqual(p["name"], "the switch hums")

    def test_the_store_answers_a_dream_whose_note_has_no_name(self):
        room = self.page("1010", "an older dream from the first day")
        put_reading([room], "a note from before names existed", time.time() - 100)
        self.assertEqual(name_them(self.fake(), "--unnamed")[0], 0)
        p = [x for x in call("/api/stream?n=5")[1]["pages"] if x["room"] == room][0]
        self.assertEqual(p["name"], "an older dream from the")
        self.assertEqual(p["reading"]["text"], "a note from before names existed")

    def test_a_day_to_a_file_and_a_killed_run_keeps_what_it_did(self):
        a = self.page("2300", "the first night", day="2026-09-18")
        b = self.page("0100", "the second night", day="2026-09-19")
        self.assertEqual(name_them(self.fake(), "--unnamed", "--limit", "1")[0], 0)
        # oldest first, one only — and filed under the ROOM's date, not today's
        self.assertEqual(list(self.store("2026-09-18")), [a])
        self.assertFalse(os.path.exists(os.path.join(STREAM_DIR, "names", "2026-09-19.json")))
        # the next run picks up where it stopped and leaves the first name alone
        self.assertEqual(name_them(self.fake(), "--unnamed")[0], 0)
        self.assertEqual(list(self.store("2026-09-18")), [a])
        self.assertEqual(list(self.store("2026-09-19")), [b])

    def test_a_flagged_dream_and_an_unreadable_answer_cost_nothing(self):
        self.page("1015", "a licence footer", flag="copyright")
        good = self.page("1020", "a dream worth naming")
        self.assertEqual(name_them(self.fake("noname"), "--unnamed")[0], 0)
        self.assertFalse(os.path.exists(os.path.join(STREAM_DIR, "names", "2026-09-19.json")))
        code, out = name_them(self.fake(), "--unnamed")
        self.assertEqual(code, 0, out)
        self.assertEqual(list(self.store("2026-09-19")), [good])     # the flagged one, never


# ---- the sleeper remembering ----------------------------------------------------------------

class Remembering(unittest.TestCase):
    def setUp(self):
        wipe_stream()
        self.fakes = []

    def tearDown(self):
        for f in self.fakes:
            shutil.rmtree(f["dir"], ignore_errors=True)

    def fake(self, mode: str = "") -> dict:
        f = fake_claude(mode)
        self.fakes.append(f)
        return f

    def scene(self, hhmm: str, text: str, flag=None) -> str:
        name = f"stream/2026-09-19/{hhmm}"
        make_page(name, f"seed for {hhmm}\n", text, flag=flag)
        return name

    def test_the_first_scene_has_nothing_remembered_yet(self):
        room = self.scene("1000", "a door in the corridor.")
        f = self.fake()
        code, out = remember(f)
        self.assertEqual(code, 0, out)
        prompt = read_text(f["log"])
        self.assertIn(remembering.NOTHING_YET, prompt)
        self.assertIn("a door in the corridor.", prompt)
        with open(remembering.PERSONA, encoding="utf-8") as fh:
            self.assertIn(fh.read().rstrip("\n"), prompt)   # bekh's file, verbatim

        v = dream_versions()
        self.assertEqual(len(v), 1)
        self.assertEqual((v[0]["turn"], v[0]["of"], v[0]["room"]), (1, remembering.TURNS, room))
        self.assertEqual(v[0]["night" if False else "dream"], v[0]["dream"])
        self.assertTrue(v[0]["text"].startswith("I was in it again"))
        row = [r for r in ledger_rows() if r.get("kind") == "dream"][-1]
        self.assertEqual((row["turn"], row["room"]), (1, room))
        self.assertEqual(row["usage"]["cache_read_input_tokens"], 6642)

    def test_the_scene_goes_over_alone_with_its_ragged_edges(self):
        """Seedless by default: the passage as nemo left it, ragged at both ends, and nothing
        else — those edges are what the account makes its joints out of."""
        ragged = "stopped just before"
        self.scene("1000", ragged)
        f = self.fake()
        self.assertEqual(remember(f)[0], 0)
        prompt = read_text(f["log"])
        self.assertIn("--- the new scene ---\n\n" + ragged + "\n", prompt)
        self.assertNotIn("[scene]", prompt)
        self.assertNotIn("[seed]", prompt)
        self.assertNotIn("seed for 1000", prompt)       # the seed text itself, nowhere
        self.assertNotIn(remembering.SEEDED_NOTE, prompt)
        with open(remembering.PERSONA, encoding="utf-8") as fh:
            self.assertIn(fh.read().rstrip("\n"), prompt)   # bekh's file, verbatim

    def test_the_seeds_switch_puts_the_old_material_back(self):
        was = remembering.SEEDS
        remembering.SEEDS = True
        self.addCleanup(setattr, remembering, "SEEDS", was)
        self.scene("1000", "a door in the corridor.")
        f = self.fake()
        self.assertEqual(remember(f)[0], 0)
        prompt = read_text(f["log"])
        self.assertIn("[seed] seed for 1000", prompt)
        self.assertIn("[scene] a door in the corridor.", prompt)
        # the line explaining the labels is the CODE's, never bekh's file
        self.assertIn(remembering.SEEDED_NOTE, prompt)
        with open(remembering.PERSONA, encoding="utf-8") as fh:
            self.assertNotIn("[seed]", fh.read())

    def test_a_later_scene_carries_only_the_latest_version(self):
        self.scene("1000", "a door in the corridor.")
        self.assertEqual(remember(self.fake())[0], 0)
        first = dream_versions()[0]["text"]

        # a note from the OTHER voice exists on the shelf and must not reach this one
        self.assertEqual(interpret(self.fake())[0], 0)

        self.scene("1005", "the door was a lift.")
        f = self.fake()
        self.assertEqual(remember(f)[0], 0)
        prompt = read_text(f["log"])
        self.assertIn(first, prompt)                       # what he remembers, verbatim
        self.assertIn("--- the new scene ---\n\nthe door was a lift.", prompt)
        # exactly one scene is handed over: his account may quote the older one, the prompt
        # never hands it to him again
        self.assertEqual(prompt.count("--- the new scene ---"), 1)
        self.assertNotIn("the door was a lift.", first)   # the new scene is new
        self.assertNotIn("seed for 1000", prompt)
        self.assertNotIn("the switch keeps answering", prompt)  # the reader's note, never
        self.assertNotIn("<mark>", prompt)
        v = dream_versions()
        self.assertEqual([x["turn"] for x in v], [1, 2])
        self.assertEqual(v[1]["dream"], v[0]["dream"])     # the same dream, rewritten
        self.assertNotEqual(v[1]["text"], v[0]["text"])

    # ---- the seams (bekh, 2026-09-22) -------------------------------------------------------
    def test_the_shape_asks_for_the_seam_and_the_marks_are_kept_as_written(self):
        """One continuous telling, a `|` where each later scene comes in — stored exactly as he
        wrote it, and shown back to him with its marks so he sees where he put them."""
        self.scene("1000", "a door in the corridor.")
        f = self.fake("seams")
        self.assertEqual(remember(f)[0], 0)
        self.assertIn("Put a single | at the exact point", read_text(f["log"]))

        self.scene("1005", "the door was a lift.")
        f2 = self.fake("seams")
        self.assertEqual(remember(f2)[0], 0)
        v = dream_versions()
        self.assertIn("|", v[1]["text"])                       # never corrected out
        # his own memory carries the marks back to him, verbatim
        self.assertIn(v[0]["text"], read_text(f2["log"]))

    def test_the_parts_are_the_text_cut_at_its_seams(self):
        self.scene("1000", "one.")
        self.assertEqual(remember(self.fake("seams"))[0], 0)
        self.scene("1005", "two.")
        self.assertEqual(remember(self.fake("seams"))[0], 0)
        self.scene("1010", "three.")
        self.assertEqual(remember(self.fake("seams"))[0], 0)
        v = dream_versions()
        self.assertEqual([len(x["parts"]) for x in v], [1, 2, 3])
        self.assertEqual(v[2]["parts"], [p.strip() for p in v[2]["text"].split("|")])
        self.assertEqual("".join(v[2]["parts"]).count("|"), 0)
        # whitespace around a cut goes and nothing else
        self.assertEqual(remembering.split_parts(" a and then | it turned "),
                         ["a and then", "it turned"])

    def test_a_telling_with_no_marks_is_one_part(self):
        """Nothing is an error: the sleeper who marks nothing has a telling of one part, which
        is what every account written before the seams existed is."""
        self.scene("1000", "one.")
        self.assertEqual(remember(self.fake())[0], 0)
        v = dream_versions()[0]
        self.assertNotIn("|", v["text"])
        self.assertEqual(v["parts"], [v["text"]])

    def test_the_api_carries_the_parts_beside_the_text(self):
        a = self.scene("1000", "one.")
        self.assertEqual(remember(self.fake("seams"))[0], 0)
        b = self.scene("1005", "two.")
        self.assertEqual(remember(self.fake("seams"))[0], 0)
        by = {p["room"]: p for p in call("/api/stream?n=9")[1]["pages"]}
        latest = dream_versions()[-1]
        for room in (a, b):
            story = by[room]["story"]
            self.assertEqual(story["text"], latest["text"])    # the `|` stays in the text
            self.assertIn("|", story["text"])
            self.assertEqual(story["parts"], latest["parts"])
            self.assertEqual((story["turn"], story["of"]), (2, latest["of"]))

    def test_a_version_written_before_the_seams_still_has_parts_on_the_api(self):
        """The store is derived, so a file with no `parts` in it is split where it is read."""
        room = self.scene("1000", "one.")
        self.assertEqual(remember(self.fake("seams"))[0], 0)
        path = remembering.version_files()[0]
        with open(path, encoding="utf-8") as f:
            v = json.load(f)
        v.pop("parts")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(v, f)
        page = call("/api/stream?n=3")[1]["pages"][0]
        self.assertEqual(page["room"], room)
        self.assertEqual(page["story"]["parts"], [p.strip() for p in v["text"].split("|")])

    def test_a_flagged_scene_is_never_told(self):
        self.scene("1000", "a footer.", "copyright")
        self.assertEqual(remember(self.fake())[0], 0)
        self.assertEqual(dream_versions(), [])
        self.scene("1005", "a real one.")
        self.assertEqual(remember(self.fake())[0], 0)
        self.assertEqual([v["room"] for v in dream_versions()], ["stream/2026-09-19/1005"])

    def test_the_scene_cap_ends_a_dream_and_the_next_starts_fresh(self):
        was = remembering.TURNS
        remembering.TURNS = 2
        self.addCleanup(setattr, remembering, "TURNS", was)
        for i, hhmm in enumerate(("1000", "1005", "1010")):
            self.scene(hhmm, f"scene {i}.")
            self.assertEqual(remember(self.fake())[0], 0)
        v = dream_versions()
        self.assertEqual([x["turn"] for x in v], [1, 2, 1])
        self.assertEqual(v[0]["dream"], v[1]["dream"])
        self.assertNotEqual(v[2]["dream"], v[1]["dream"])
        # the third starts from nothing, as a new dream must
        self.assertTrue(dream_versions()[2]["text"].startswith("I was in it again;"))

    def test_a_long_silence_does_not_end_a_dream(self):
        """A stopped stream leaves the story waiting for its next scene: one passage tonight
        and three tomorrow are one story of four, not a stranded one and a fresh one."""
        self.scene("1000", "one.")
        self.assertEqual(remember(self.fake())[0], 0)
        v, path = dream_versions()[0], remembering.version_files()[0]
        v["ts"] = time.time() - 86400
        with open(path, "w", encoding="utf-8") as f:
            json.dump(v, f)
        self.scene("1005", "two.")
        self.assertEqual(remember(self.fake())[0], 0)
        later = dream_versions()
        self.assertEqual([x["turn"] for x in later], [1, 2])
        self.assertEqual(later[0]["dream"], later[1]["dream"])
        self.assertEqual(later[0]["chapter"], later[1]["chapter"])

    def test_retell_mends_a_stranded_story_and_everything_after_it(self):
        """What the gap left behind: a story of one scene that was ended by force, and the next
        one starting over. The retell bins chapter 2 on and tells those scenes again in order,
        so the stranded scene gets its company and the chapter numbers come out whole."""
        for hhmm in ("1000", "1005", "1010", "1015", "1020"):
            self.scene(hhmm, f"scene {hhmm}.")
            self.assertEqual(remember(self.fake())[0], 0)
        # strand 2:1 the way the gap did — ended after one scene
        def ts_of(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)["ts"]
        path = max(remembering.version_files(), key=ts_of)
        with open(path, encoding="utf-8") as f:
            v = json.load(f)
        self.assertEqual((v["chapter"], v["turn"]), (2, 1))
        v["of"] = 1
        with open(path, "w", encoding="utf-8") as f:
            json.dump(v, f)
        self.scene("1025", "scene 1025.")
        self.assertEqual(remember(self.fake())[0], 0)
        self.assertEqual([(x["chapter"], x["turn"]) for x in dream_versions()][-2:],
                         [(2, 1), (3, 1)])

        code, out = with_fake(self.fake(),
                              lambda: remembering.main(["remembering.py", "--retell", "2"]))
        self.assertEqual(code, 0, out)
        v = dream_versions()
        self.assertEqual([(x["chapter"], x["turn"]) for x in v],
                         [(1, 1), (1, 2), (1, 3), (1, 4), (2, 1), (2, 2)])
        self.assertEqual([x["room"] for x in v[4:]],
                         ["stream/2026-09-19/1020", "stream/2026-09-19/1025"])
        self.assertEqual(v[4]["dream"], v[5]["dream"])
        # the old versions are in the bin, not gone, and the live run carries on from here
        binned = [f for _, _, fs in os.walk(os.path.join(remembering.DREAMS, ".trash"))
                  for f in fs]
        self.assertEqual(len(binned), 2)
        self.assertIsNone(remembering.next_scene(remembering.versions()))

    def test_a_garbage_answer_is_a_ledger_row_and_exit_zero(self):
        room = self.scene("1000", "one.")
        code, out = remember(self.fake("garbage"))
        self.assertEqual(code, 0, out)
        self.assertEqual(dream_versions(), [])
        row = [r for r in ledger_rows() if r.get("kind") == "dream"][-1]
        self.assertIn("no <dream>", row["error"])
        self.assertEqual(row["room"], room)

    def test_nothing_new_asks_nobody(self):
        self.scene("1000", "one.")
        self.assertEqual(remember(self.fake())[0], 0)
        f = self.fake()
        self.assertEqual(remember(f)[0], 0)
        self.assertFalse(os.path.exists(f["log"]))

    # ---- what the api does with it ---------------------------------------------------------
    def test_every_room_of_a_pack_carries_its_story(self):
        """A story belongs to a pack of dreams: every room a dream's versions covered gets that
        dream's LATEST account, and rooms outside any dream get nothing."""
        a = self.scene("1000", "one.")
        self.assertEqual(remember(self.fake())[0], 0)
        b = self.scene("1005", "two.")
        self.assertEqual(remember(self.fake())[0], 0)
        make_page("stream/2026-09-19/0900", "seed\n", "a dream nobody remembered.")

        by = {p["room"]: p for p in call("/api/stream?n=9")[1]["pages"]}
        latest = dream_versions()[-1]
        for room in (a, b):
            self.assertEqual(by[room]["story"]["dream"], latest["dream"])
            self.assertEqual(by[room]["story"]["text"], latest["text"])   # the LATEST, both
            self.assertEqual(by[room]["story"]["turn"], 2)
        self.assertIsNone(by["stream/2026-09-19/0900"]["story"])
        # the top-level dream field and the in-feed dream_end are gone
        self.assertNotIn("dream", call("/api/stream?n=1")[1])
        self.assertNotIn("dream_end", by[a])

    def test_live_is_the_newest_pack_until_its_cap(self):
        room = self.scene("1000", "one.")
        self.assertEqual(remember(self.fake())[0], 0)
        self.assertIs(call("/api/stream?n=3")[1]["pages"][0]["story"]["live"], True)

        # a day old and still live: a stopped stream leaves the story waiting, not ended
        v, path = dream_versions()[0], remembering.version_files()[0]
        v["ts"] = time.time() - 86400
        with open(path, "w", encoding="utf-8") as f:
            json.dump(v, f)
        p = call("/api/stream?n=3")[1]["pages"][0]
        self.assertIs(p["story"]["live"], True)
        self.assertEqual(p["story"]["text"], v["text"])

        # and a pack that used up its scenes is not live either
        v["ts"], v["turn"] = time.time(), v["of"]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(v, f)
        self.assertIs(call("/api/stream?n=3")[1]["pages"][0]["story"]["live"], False)

    def test_usage_reaches_both_kinds_of_row(self):
        self.scene("1000", "one.")
        self.assertEqual(remember(self.fake())[0], 0)
        self.assertEqual(interpret(self.fake())[0], 0)
        rows = {r["kind"]: r for r in ledger_rows() if r.get("kind") in ("dream", "reading")}
        for kind in ("dream", "reading"):
            u = rows[kind]["usage"]
            self.assertEqual(u["input_tokens"], 12)
            self.assertEqual(u["cache_read_input_tokens"], 6642)
            self.assertEqual(u["output_tokens"], 301)
            self.assertAlmostEqual(u["cost_usd"], 0.002178, places=6)

    def test_the_counter_reads_the_cli_json_in_either_shape(self):
        one = json.dumps({"type": "result", "result": "hi", "usage": {"input_tokens": 3},
                          "total_cost_usd": 1.5})
        many = json.dumps([{"type": "system"}, json.loads(one)])
        for raw in (one, many):
            d = opus.result_of(raw)
            self.assertEqual(d["result"], "hi")
            u = opus.usage_of(d)
            self.assertEqual(u["input_tokens"], 3)
            self.assertEqual(u["output_tokens"], 0)        # missing is 0, never absent
            self.assertEqual(u["cost_usd"], 1.5)
        self.assertEqual(opus.add({"input_tokens": 1}, {"input_tokens": 2})["input_tokens"], 3)


# ---- the analyst ------------------------------------------------------------------------------

def analyse(fake: dict, *args) -> tuple[int, str]:
    return with_fake(fake, lambda: analyst.main(["analyst.py", *args]))


def argv_log(fake: dict) -> list[list[str]]:
    try:
        with open(fake["log"] + ".argv", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except OSError:
        return []


class Analyst(unittest.TestCase):
    """The fourth voice: one resumed session per seat, every dream verbatim, oldest first."""

    def setUp(self):
        wipe_stream()
        self.fakes = []
        self.persona = os.path.join(BOX, "analyst-persona-test.txt")
        with open(self.persona, "w", encoding="utf-8") as f:
            f.write("ANALYSTPERSONAMARK you read someone's dreams.\n")
        # six dreams, one flagged: 1000 1005 [1010 flagged] 1015 1020 1025
        self.rooms = []
        for hhmm in ("1000", "1005", "1010", "1015", "1020", "1025"):
            name = f"stream/2026-09-20/{hhmm}"
            make_page(name, f"ANALYSTSEEDMARK {hhmm}\n", f"ANALYSTDREAM {hhmm} and the  ragged",
                      flag="copyright" if hhmm == "1010" else None)
            self.rooms.append(name)
        # a reader's note on one of them, which must never reach the analyst
        put_reading(["stream/2026-09-20/1025"], "ANALYSTNOTEMARK a note.", time.time())

    def tearDown(self):
        for f in self.fakes:
            shutil.rmtree(f["dir"], ignore_errors=True)

    def fake(self, mode: str = "") -> dict:
        f = fake_claude(mode)
        self.fakes.append(f)
        return f

    def run_(self, *args, mode: str = "") -> tuple[int, str, dict]:
        f = self.fake(mode)
        code, out = analyse(f, "--once", "--persona", self.persona, *args)
        return code, out, f

    def rows(self) -> list[dict]:
        return [r for r in ledger_rows() if r.get("kind") == "portrait"]

    def session(self, seat: str = "analyst") -> dict:
        with open(os.path.join(analyst.PORTRAITS, seat, "session.json"), encoding="utf-8") as f:
            return json.load(f)

    def versions(self, seat: str = "analyst") -> list[dict]:
        out = []
        for path in analyst.version_files(seat):
            with open(path, encoding="utf-8") as f:
                out.append(json.load(f))
        return sorted(out, key=lambda d: d["ts"])

    def test_a_fresh_seat_reads_the_last_three_oldest_first(self):
        code, out, f = self.run_("--start", "last:3", "--n", "3")
        self.assertEqual(code, 0, out)
        prompt = read_text(f["log"])
        # the last three unflagged, oldest first, each under its date and minute
        want = ["1015", "1020", "1025"]
        at = [prompt.index(f"[2026-09-20 {h[:2]}:{h[2:]}]\nANALYSTDREAM {h} and the  ragged")
              for h in want]
        self.assertEqual(at, sorted(at))
        for h in ("1000", "1005", "1010"):
            self.assertNotIn(f"ANALYSTDREAM {h}", prompt)
        self.assertTrue(prompt.startswith("ANALYSTPERSONAMARK you read someone's dreams.\n\n"))
        self.assertIn("<portrait>", prompt)
        self.assertIn("--- the dreams ---", prompt)
        for never in ("ANALYSTSEEDMARK", "ANALYSTNOTEMARK", "<title>", "<name>"):
            self.assertNotIn(never, prompt)
        self.assertNotIn("--resume", argv_log(f)[0])
        self.assertIn("a dreamer of 3 more dreams.", out)            # printed for bekh

        s = self.session()
        self.assertTrue(s["session_id"])
        self.assertEqual((s["covered"], s["dreams"], s["persona"]),
                         ("stream/2026-09-20/1025", 3, self.persona))
        self.assertEqual(s["context"], 12 + 6642 + 3)                 # the three counters
        self.assertEqual(set(s), {"session_id", "door", "persona", "started", "covered", "dreams",
                                  "context", "model"})
        self.assertEqual(s["door"], "opus")
        v = self.versions()
        self.assertEqual(len(v), 1)
        self.assertEqual(set(v[0]), {"ts", "seat", "door", "session_id", "rooms", "dreams", "text",
                                     "line", "model", "seconds", "usage", "context"})
        self.assertEqual(v[0]["rooms"], [f"stream/2026-09-20/{h}" for h in want])
        self.assertEqual(v[0]["text"], "a dreamer of 3 more dreams.")   # inside the tag, stripped
        self.assertEqual((v[0]["dreams"], v[0]["context"], v[0]["session_id"]),
                         (3, 6657, s["session_id"]))
        path = analyst.version_files("analyst")[0]
        self.assertRegex(os.path.relpath(path, analyst.PORTRAITS),
                         r"^analyst/\d{4}-\d{2}-\d{2}/\d{4}(-\d+)?\.json$")
        row = self.rows()[-1]
        self.assertEqual((row["seat"], row["rooms"], row["dreams"], row["context"]),
                         ("analyst", 3, 3, 6657))
        self.assertEqual(row["usage"]["cache_read_input_tokens"], 6642)

    def test_the_second_run_resumes_with_only_the_new_dreams(self):
        self.assertEqual(self.run_("--start", "last:3", "--n", "3")[0], 0)
        sid = self.session()["session_id"]
        make_page("stream/2026-09-20/1030", "ANALYSTSEEDMARK\n", "ANALYSTDREAM 1030 new")
        make_page("stream/2026-09-20/1030-2", "ANALYSTSEEDMARK\n", "ANALYSTDREAM 1030b new")
        code, out, f = self.run_("--n", "2")
        self.assertEqual(code, 0, out)
        argv = argv_log(f)[0]
        self.assertEqual(argv[argv.index("--resume") + 1], sid)
        prompt = read_text(f["log"])
        self.assertTrue(prompt.startswith("--- 2 more dreams ---\n\n[2026-09-20 10:30]\n"
                                          "ANALYSTDREAM 1030 new\n\n[2026-09-20 10:30]\n"
                                          "ANALYSTDREAM 1030b new\n\n"))
        self.assertIn(analyst.AGAIN, prompt)
        for never in ("ANALYSTPERSONAMARK", "ANALYSTDREAM 1025", "a dreamer of", "ANALYSTSEEDMARK"):
            self.assertNotIn(never, prompt)
        s = self.session()
        self.assertEqual((s["session_id"], s["dreams"], s["covered"]),
                         (sid, 5, "stream/2026-09-20/1030-2"))
        self.assertEqual([v["dreams"] for v in self.versions()], [3, 5])

    def test_fewer_than_n_new_is_no_call_and_no_row_and_partial_takes_them(self):
        self.assertEqual(self.run_("--start", "last:3", "--n", "3")[0], 0)
        make_page("stream/2026-09-20/1030", "s\n", "ANALYSTDREAM 1030")
        before = len(self.rows())
        code, out, f = self.run_("--n", "3")
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(f["log"]))
        self.assertEqual(len(self.rows()), before)
        code, out, f = self.run_("--n", "3", "--partial")
        self.assertEqual(code, 0, out)
        self.assertIn("--- 1 more dreams ---", read_text(f["log"]))
        self.assertEqual(self.session()["dreams"], 4)

    def test_a_fresh_seat_starts_at_the_oldest_and_skips_the_flagged(self):
        code, out, f = self.run_("--n", "4")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.versions()[0]["rooms"],
                         [f"stream/2026-09-20/{h}" for h in ("1000", "1005", "1015", "1020")])
        self.assertNotIn("ANALYSTDREAM 1010", read_text(f["log"]))

    def test_start_at_a_named_room(self):
        code, out, f = self.run_("--start", "stream/2026-09-20/1005", "--n", "2")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.versions()[0]["rooms"],
                         ["stream/2026-09-20/1005", "stream/2026-09-20/1015"])

    def test_two_seats_keep_their_own_persona_and_session(self):
        other = os.path.join(BOX, "analyst-persona-other.txt")
        with open(other, "w", encoding="utf-8") as f:
            f.write("ANALYSTMACHINEMARK the dreamer is not a person.\n")
        self.assertEqual(self.run_("--start", "last:3", "--n", "3")[0], 0)
        f2 = self.fake()
        code, out = analyse(f2, "--once", "--seat", "told", "--persona", other,
                            "--start", "last:3", "--n", "3")
        self.assertEqual(code, 0, out)
        prompt = read_text(f2["log"])
        self.assertIn("ANALYSTMACHINEMARK", prompt)
        self.assertNotIn("ANALYSTPERSONAMARK", prompt)
        self.assertNotIn("--resume", argv_log(f2)[0])
        a, b = self.session("analyst"), self.session("told")
        self.assertNotEqual(a["session_id"], b["session_id"])
        self.assertEqual(b["persona"], other)
        self.assertEqual(len(self.versions("told")), 1)

    def test_the_ceiling_refuses_with_a_row_and_no_call(self):
        self.assertEqual(self.run_("--start", "last:3", "--n", "3")[0], 0)
        s = self.session()
        s["context"] = analyst.CONTEXT_MAX["opus"]
        with open(os.path.join(analyst.PORTRAITS, "analyst", "session.json"), "w") as fh:
            json.dump(s, fh)
        make_page("stream/2026-09-20/1030", "s\n", "ANALYSTDREAM 1030")
        code, out, f = self.run_("--n", "1")
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(f["log"]))
        self.assertIn("over the ceiling", out)
        self.assertIn(f"session at {analyst.CONTEXT_MAX["opus"]} tokens", self.rows()[-1]["error"])
        self.assertEqual(self.session()["covered"], "stream/2026-09-20/1025")

    def test_a_garbage_answer_is_a_row_and_exit_zero(self):
        code, out, f = self.run_("--start", "last:3", "--n", "3", mode="garbage")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.versions(), [])
        row = self.rows()[-1]
        self.assertIn("no <portrait>", row["error"])
        self.assertEqual(row["usage"]["input_tokens"], 12)
        # the cli answered, so the dreams are in the session: it moves on, and the next run
        # resumes it with only what is new — never the same three handed over twice
        s = self.session()
        self.assertTrue(s["session_id"])
        self.assertEqual((s["covered"], s["dreams"]), ("stream/2026-09-20/1025", 3))
        make_page("stream/2026-09-20/1030", "s\n", "ANALYSTDREAM 1030")
        code, out, f = self.run_("--n", "1")
        self.assertEqual(code, 0, out)
        argv = argv_log(f)[0]
        self.assertEqual(argv[argv.index("--resume") + 1], s["session_id"])
        self.assertNotIn("ANALYSTDREAM 1025", read_text(f["log"]))
        self.assertEqual(self.versions()[0]["dreams"], 4)

    def test_a_dead_cli_moves_nothing(self):
        self.assertEqual(self.run_("--start", "last:3", "--n", "3")[0], 0)
        before = self.session()
        make_page("stream/2026-09-20/1030", "s\n", "ANALYSTDREAM 1030")
        code, out, f = self.run_("--n", "1", mode="boom")
        self.assertEqual(code, 0, out)
        self.assertIn("exited 3", self.rows()[-1]["error"])
        self.assertEqual(self.session(), before)

    def test_no_session_id_is_a_row_not_a_portrait(self):
        code, out, f = self.run_("--n", "3", mode="nosession")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.versions(), [])
        self.assertIn("no session id", self.rows()[-1]["error"])

    def test_start_on_a_live_seat_is_refused_and_new_bins_it(self):
        self.assertEqual(self.run_("--start", "last:3", "--n", "3")[0], 0)
        old = self.session()["session_id"]
        code, out, f = self.run_("--start", "last:2", "--n", "2")
        self.assertEqual(code, 2)
        self.assertIn("--new", out)
        self.assertFalse(os.path.exists(f["log"]))
        code, out, f = self.run_("--start", "last:2", "--n", "2", "--new")
        self.assertEqual(code, 0, out)
        self.assertNotIn("--resume", argv_log(f)[0])
        self.assertNotEqual(self.session()["session_id"], old)
        self.assertEqual(len(self.versions()), 1)
        binned = [os.path.join(dp, fn) for dp, _, fs in
                  os.walk(os.path.join(analyst.PORTRAITS, ".trash")) for fn in fs]
        self.assertTrue(any(p.endswith(os.path.join("analyst", "session.json")) for p in binned))

    def test_show_prints_the_latest_and_calls_nobody(self):
        self.assertEqual(self.run_("--start", "last:3", "--n", "3")[0], 0)
        f = self.fake()
        code, out = analyse(f, "--show")
        self.assertEqual(code, 0)
        self.assertIn("a dreamer of 3 more dreams.", out)
        self.assertFalse(os.path.exists(f["log"]))

    def test_the_shape_asks_for_the_portrait_only_and_the_line_is_its_closing(self):
        code, out, f = self.run_("--start", "last:3", "--n", "3")
        self.assertEqual(code, 0, out)
        prompt = read_text(f["log"])
        # nothing about a remark, a card or a ribbon reaches him — the portrait is all he is asked
        self.assertIn("<portrait>", prompt)
        for never in ("remark", "ribbon", "card", "sentence"):
            self.assertNotIn(never, prompt)
        self.assertNotIn("remark", analyst.AGAIN)
        # a one-sentence portrait closes on itself: the line on the version and on the row
        want = "a dreamer of 3 more dreams."
        self.assertEqual(self.versions()[0]["line"], want)
        self.assertEqual(self.rows()[-1]["line"], want)
        self.assertEqual(self.versions()[0]["text"], want)
        make_page("stream/2026-09-20/1030", "s\n", "ANALYSTDREAM 1030")
        code, out, f = self.run_("--n", "1")
        self.assertIn(analyst.AGAIN, read_text(f["log"]))
        self.assertEqual(self.versions()[-1]["line"], "a dreamer of 1 more dreams.")

    def test_the_closing_is_the_last_two_sentences_as_one_line(self):
        text = ("the dreamer is a witness.\nit wants to ask “what does this\nmean?” yet fails. "
                "bread is “the best thing,” torn and swept. behind the dread is a wish: tea, "
                "toast, honey.")
        self.assertEqual(analyst.closing(text),
                         "bread is “the best thing,” torn and swept. behind the dread is a wish: "
                         "tea, toast, honey.")
        # a quote closing after the stop is a seam; a comma inside one is not
        self.assertEqual(analyst.closing("one. two.” three."), "two.” three.")
        self.assertEqual(analyst.closing("one. two, “three.”"), "one. two, “three.”")
        self.assertEqual(analyst.closing("alone."), "alone.")
        self.assertEqual(analyst.closing("   "), "")
        # the parser hands the closing back and ignores anything after the tag
        self.assertEqual(analyst.parse("<portrait>p. q. r.</portrait>\nand more"), ("p. q. r.", "q. r."))
        # a whole answer (the deepseek door's rethrow test) ends on the portrait's tag now
        self.assertTrue(analyst.whole_answer("<portrait>p.</portrait>\n"))
        self.assertFalse(analyst.whole_answer("<portrait>p. and then"))

    def test_the_header_never_says_who_wrote_the_page(self):
        self.assertEqual(analyst.header("stream/2026-09-23/1858"), "[2026-09-23 18:58]")
        self.assertEqual(analyst.header("stream/2026-09-23/1858-2"), "[2026-09-23 18:58]")
        make_page("stream/2026-09-20/1030", "s\n", "ANALYSTDREAM 1030", model="gpt2")
        make_page("stream/2026-09-20/1035", "s\n", "ANALYSTDREAM 1035",
                  model="Mistral-Nemo-Base-2407.Q5_K_M.gguf")
        code, out, f = self.run_("--start", "stream/2026-09-20/1025", "--n", "3")
        self.assertEqual(code, 0, out)
        prompt = read_text(f["log"])
        # a page with no stamp, one stamped gpt2, one stamped with nemo's file name: all bare
        self.assertIn("[2026-09-20 10:25]\nANALYSTDREAM 1025", prompt)
        self.assertIn("[2026-09-20 10:30]\nANALYSTDREAM 1030", prompt)
        self.assertIn("[2026-09-20 10:35]\nANALYSTDREAM 1035", prompt)
        for word in ("gpt2", "nemo", "Mistral", " · "):
            self.assertNotIn(word, prompt)
        self.assertEqual(self.versions()[0]["dreams"], 3)            # the fake counted all three

    def test_narration_says_the_remark_out_loud(self):
        import narrate
        self.assertEqual(narrate.line({"kind": "portrait", "seat": "analyst", "dreams": 40,
                                       "line": "he keeps a door", "seconds": 14.2}),
                         'the analyst · 40 dreams · "he keeps a door" · 14s')
        self.assertEqual(narrate.line({"kind": "portrait", "seat": "blind", "error": "x"}),
                         "the analyst (blind) · FAILED · x")

    def test_opus_resume_is_on_the_argv_and_the_old_callers_are_untouched(self):
        f = self.fake()
        def go():
            opus.ask("--- the dreams ---\n\n[2026-09-20 10:00]\nx\n", 30, resume="abc-123")
            return 0
        with_fake(f, go)
        self.assertEqual(opus.SESSION, "abc-123")
        argv = argv_log(f)[0]
        self.assertEqual(argv[-2:], ["--resume", "abc-123"])
        # a call with no resume carries no flag and reports no session from the plain fake
        f2 = self.fake()
        with_fake(f2, lambda: (opus.ask("hello", 30), 0)[1])
        self.assertNotIn("--resume", argv_log(f2)[0])
        self.assertEqual(opus.SESSION, "")


def put_portrait(seat: str, pid: str, rooms: list[str], ts: float, text: str,
                 line: str | None = None) -> str:
    """A portrait version straight onto disk, in analyst.py's shape — for the api tests, which
    are about which version hangs where, not about what the cli said. `line` None is a version
    written before the remark existed."""
    path = os.path.join(analyst.PORTRAITS, seat, pid + ".json")
    d = {"ts": ts, "seat": seat, "session_id": "s-1", "rooms": rooms, "dreams": len(rooms),
         "text": text, "model": "opus", "seconds": 1.0, "usage": {}, "context": 1}
    if line is not None:
        d["line"] = line
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f)
    return path


class AnalystApi(unittest.TestCase):
    """The portrait in the feed: on the page it was written after, the whole run of them, one by
    id — the public seat only — and its landing as a change on the held connection."""

    def setUp(self):
        wipe_stream()
        self.fakes = []
        for hhmm in ("1000", "1005", "1010", "1015"):
            make_page(f"stream/2026-09-21/{hhmm}", "s\n", f"PORTRAITAPIDREAM {hhmm}")

    def tearDown(self):
        for f in self.fakes:
            shutil.rmtree(f["dir"], ignore_errors=True)

    def pages(self) -> dict:
        code, d = call("/api/stream?n=20")
        self.assertEqual(code, 200, d)
        return {p["room"]: p for p in d["pages"]}

    def test_the_page_it_was_written_after_carries_it_and_no_other(self):
        f = fake_claude()
        self.fakes.append(f)
        code, out = analyse(f, "--once", "--start", "last:3", "--n", "3")
        self.assertEqual(code, 0, out)
        pages = self.pages()
        v = pages["stream/2026-09-21/1015"]["portrait"]
        self.assertEqual(set(v), {"id", "ts", "line", "text", "dreams", "rooms"})
        self.assertEqual((v["text"], v["line"], v["dreams"]),
                         ("a dreamer of 3 more dreams.", "a dreamer of 3 more dreams.", 3))
        self.assertEqual(v["rooms"], [f"stream/2026-09-21/{h}" for h in ("1005", "1010", "1015")])
        # the id is the version's path under the seat, and it asks for the same thing back
        path = analyst.version_files("analyst")[0]
        self.assertEqual(v["id"], os.path.relpath(path, os.path.join(analyst.PORTRAITS,
                                                                     "analyst"))[:-5])
        self.assertRegex(v["id"], r"^\d{4}-\d{2}-\d{2}/\d{4}(-\d+)?$")
        self.assertEqual(call("/api/stream/portrait?id=" + v["id"]), (200, v))
        for room in ("1000", "1005", "1010"):
            self.assertIsNone(pages[f"stream/2026-09-21/{room}"]["portrait"])

    def test_the_run_newest_first_and_one_by_id(self):
        now = time.time()
        put_portrait("analyst", "2026-09-21/1006", ["stream/2026-09-21/1000",
                                                    "stream/2026-09-21/1005"], now - 600,
                     "PORTRAITAPIOLD", "the old line")
        put_portrait("analyst", "2026-09-21/1016", ["stream/2026-09-21/1010",
                                                    "stream/2026-09-21/1015"], now, "PORTRAITAPINEW")
        code, d = call("/api/stream/portraits")
        self.assertEqual(code, 200, d)
        self.assertEqual([v["id"] for v in d["portraits"]], ["2026-09-21/1016", "2026-09-21/1006"])
        self.assertEqual(d["portraits"][0]["line"], "")        # written before the remark: ""
        code, v = call("/api/stream/portrait?id=2026-09-21/1006")
        self.assertEqual((code, v["text"], v["line"]), (200, "PORTRAITAPIOLD", "the old line"))
        self.assertEqual(call("/api/stream/portrait?id=2026-09-21/9999")[0], 404)
        self.assertEqual(call("/api/stream/portrait?id=session")[0], 404)   # bookkeeping, never a version
        for bad in ("", "../x", "2026-09-21/../1006", ".trash/1006", "a//b"):
            self.assertEqual(call("/api/stream/portrait?id=" + urllib.parse.quote(bad))[0], 400,
                             bad)
        # each version on its own last room; with two ending on one room, the newer wins
        pages = self.pages()
        self.assertEqual(pages["stream/2026-09-21/1005"]["portrait"]["id"], "2026-09-21/1006")
        self.assertEqual(pages["stream/2026-09-21/1015"]["portrait"]["id"], "2026-09-21/1016")
        put_portrait("analyst", "2026-09-21/1017", ["stream/2026-09-21/1015"], now + 60, "PORTRAITAPIREDO")
        self.assertEqual(self.pages()["stream/2026-09-21/1015"]["portrait"]["id"], "2026-09-21/1017")

    def test_a_seat_that_is_not_the_default_never_reaches_the_api(self):
        put_portrait("blind", "2026-09-21/1016", ["stream/2026-09-21/1015"], time.time(),
                     "PORTRAITAPIBLIND")
        self.assertEqual(call("/api/stream/portraits"), (200, {"portraits": []}))
        self.assertIsNone(self.pages()["stream/2026-09-21/1015"]["portrait"])
        self.assertEqual(call("/api/stream/portrait?id=2026-09-21/1016")[0], 404)
        # nor does a binned one of the public seat
        put_portrait("analyst", ".trash/2026-09-21/1016", ["stream/2026-09-21/1015"],
                     time.time(), "PORTRAITAPIBINNED")
        self.assertEqual(call("/api/stream/portraits"), (200, {"portraits": []}))

    def test_a_portrait_landing_changes_its_rooms_fingerprint_and_no_other(self):
        before = loom.stream_prints()
        put_portrait("analyst", "2026-09-21/1016", ["stream/2026-09-21/1010",
                                                    "stream/2026-09-21/1015"], time.time(), "x")
        after = loom.stream_prints()
        moved = sorted(r for r in after if after[r] != before.get(r))
        self.assertEqual(moved, ["stream/2026-09-21/1015"])


# ---- plates ----------------------------------------------------------------------------------
# A stub `codex` first on PATH that writes a tiny png where the real one would put a painting.
# No generation is ever spent from a test: every plate costs one off bekh's allowance.

FAKE_CODEX = r'''#!/usr/bin/env python3
import base64, os, sys
brief = sys.stdin.read()
with open(os.environ["FAKE_CODEX_LOG"], "w", encoding="utf-8") as f:
    f.write(brief)
if os.environ.get("FAKE_CODEX_MODE") == "nothing":
    print("i drew nothing"); raise SystemExit(0)
if os.environ.get("FAKE_CODEX_MODE") == "boom":
    raise SystemExit(4)
# a 2x2 png, enough for sips to convert
png = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGP8z4AKmBhQwagAuwAAAAD//wMAAsMBaKPxN"
    "5EAAAAASUVORK5CYII=")
with open(os.path.join(os.getcwd(), "plate.png"), "wb") as f:
    f.write(png)
print("saved plate.png")
# The cli's own shape: the label, and the number on the NEXT line. plate.py used to grep for
# the label alone and print a row with no number in it.
print("tokens used")
print("19123")
'''


def fake_codex(mode: str = "") -> dict:
    d = tempfile.mkdtemp(prefix="stream-codex-")
    binp = os.path.join(d, "bin")
    os.makedirs(binp)
    path = os.path.join(binp, "codex")
    with open(path, "w", encoding="utf-8") as f:
        f.write(FAKE_CODEX.replace("#!/usr/bin/env python3", "#!" + sys.executable))
    os.chmod(path, 0o755)
    return {"dir": d, "bin": binp, "log": os.path.join(d, "brief.txt"), "mode": mode}


def make_plate(fake: dict, *args) -> tuple[int, str]:
    was_path = os.environ.get("PATH", "")
    os.environ["PATH"] = fake["bin"] + os.pathsep + was_path
    os.environ["FAKE_CODEX_LOG"] = fake["log"]
    os.environ["FAKE_CODEX_MODE"] = fake["mode"]
    out = io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(out):
            code = plate.main(["plate.py", *args])
    finally:
        os.environ["PATH"] = was_path
        os.environ.pop("FAKE_CODEX_MODE", None)
    return code, out.getvalue()


class Plates(unittest.TestCase):
    def setUp(self):
        wipe_stream()
        self.fakes = []

    def tearDown(self):
        for f in self.fakes:
            shutil.rmtree(f["dir"], ignore_errors=True)

    def fake(self, mode: str = "") -> dict:
        f = fake_codex(mode)
        self.fakes.append(f)
        return f

    def reading_for(self, room: str, segments: list) -> None:
        day = os.path.join(STREAM_DIR, "readings", "2026-09-19")
        os.makedirs(day, exist_ok=True)
        with open(os.path.join(day, "0100.json"), "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "rooms": [room], "reading": "a note",
                       "marked": {room: "x"}, "segments": {room: segments},
                       "model": "opus", "seconds": 1.0}, f)

    def test_the_pieces_are_the_underlines_in_order(self):
        room = "stream/2026-09-19/1000"
        make_page(room, "seed\n", "the switch hums under the floor and nobody answers")
        self.reading_for(room, [{"t": "the ", "mark": False},
                                {"t": "switch", "mark": True},
                                {"t": " hums", "mark": True},      # adjacent runs are one piece
                                {"t": " under the floor and ", "mark": False},
                                {"t": "nobody answers", "mark": True}])
        self.assertEqual(plate.pieces_for(room), ["switch hums", "nobody answers"])

        f = self.fake()
        code, out = make_plate(f, "--room", room, "--prompt", "pieces",
                               "--hand", "A test hand.")
        self.assertEqual(code, 0, out)
        brief = read_text(f["log"])
        self.assertIn("switch hums\nnobody answers", brief)     # one per line, in order
        self.assertIn("A test hand.", brief)
        self.assertIn("plate.png", brief)                       # the plumbing, appended here
        with open(os.path.join(plate.PROMPTS, "prompt-pieces.txt"), encoding="utf-8") as fh:
            self.assertNotIn("plate.png", fh.read())            # and never in bekh's file

        jpg, png, meta = plate.plate_paths(room)
        for path in (jpg, png, meta):
            self.assertTrue(os.path.isfile(path), path)
        d = json.load(open(meta, encoding="utf-8"))
        self.assertEqual((d["prompt"], d["pieces"], d["fell_back"]),
                         ("pieces", ["switch hums", "nobody answers"], False))
        row = [r for r in ledger_rows() if r.get("kind") == "plate"][-1]
        self.assertEqual((row["room"], row["pieces"]), (room, 2))
        # the count is on the line after the label, and it used to be dropped on the floor
        self.assertIn("codex tokens used: 19123", out)
        self.assertEqual(plate.tokens_used("tokens used: 42"), "42")    # the older shape

    def test_no_underlines_falls_back_to_the_whole_text(self):
        room = "stream/2026-09-19/1005"
        make_page(room, "seed\n", "THE WHOLE DREAM TEXT")
        f = self.fake()
        code, out = make_plate(f, "--room", room, "--prompt", "pieces",
                               "--hand", "A test hand.")
        self.assertEqual(code, 0, out)
        self.assertIn("falling back", out)
        self.assertIn("THE WHOLE DREAM TEXT", read_text(f["log"]))
        d = json.load(open(plate.plate_paths(room)[2], encoding="utf-8"))
        self.assertEqual((d["prompt"], d["fell_back"]), ("bekh", True))

    def test_the_default_takes_turns_between_the_two_whole_dream_prompts(self):
        # Marks on the room on purpose: neither prompt may see them, only the dream verbatim.
        seen = []
        for hhmm in ("1006", "1007", "1008"):
            room = f"stream/2026-09-19/{hhmm}"
            make_page(room, "seed\n", f"THE WHOLE DREAM {hhmm}")
            f = self.fake()
            code, out = make_plate(f, "--room", room, "--hand", "A test hand.")
            self.assertEqual(code, 0, out)
            brief = read_text(f["log"])
            self.assertIn(f"THE WHOLE DREAM {hhmm}", brief)
            self.assertNotIn("{text}", brief)
            d = json.load(open(plate.plate_paths(room)[2], encoding="utf-8"))
            seen.append(d["prompt"])
            # the hand belongs to the attic's file alone; his has no slot for one
            self.assertEqual("A test hand." in brief, d["prompt"] == "attic")
        self.assertEqual(sorted(set(seen)), ["attic", "bekh"])
        self.assertNotEqual(seen[0], seen[1])
        self.assertNotEqual(seen[1], seen[2])

    def test_from_files_an_existing_png_without_asking_codex(self):
        room = "stream/2026-09-19/1010"
        make_page(room, "seed\n", "a dream.")
        src = os.path.join(BOX, "given.png")
        import base64
        with open(src, "wb") as f:
            f.write(base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGP8z4AKmBhQwagAuwAAAAD//"
                "wMAAsMBaKPxN5EAAAAASUVORK5CYII="))
        f = self.fake()
        code, out = make_plate(f, "--room", room, "--prompt", "bekh", "--from", src)
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(f["log"]), "codex was started for a --from")
        d = json.load(open(plate.plate_paths(room)[2], encoding="utf-8"))
        self.assertEqual(d["source_png"], src)
        self.assertEqual(d["seconds"], 0.0)

    def test_a_hand_tool_fails_loudly(self):
        room = "stream/2026-09-19/1015"
        make_page(room, "seed\n", "a dream.")
        code, out = make_plate(self.fake("nothing"), "--room", room)
        self.assertEqual(code, 1)                       # non-zero: this is not a daemon
        self.assertIn("no plate.png", out)
        self.assertFalse(os.path.exists(plate.plate_paths(room)[0]))
        self.assertEqual(make_plate(self.fake("boom"), "--room", room)[0], 1)
        # and a room nobody dreamt
        self.assertEqual(make_plate(self.fake(), "--room", "stream/2026-09-19/9999")[0], 1)
        self.assertEqual(make_plate(self.fake(), "--room", "../escape")[0], 2)

    def test_the_api_and_the_route_carry_the_plate(self):
        plated = "stream/2026-09-19/1020"
        bare = "stream/2026-09-19/1025"
        make_page(plated, "seed\n", "a plated dream.")
        make_page(bare, "seed\n", "a bare dream.")
        self.assertEqual(make_plate(self.fake(), "--room", plated, "--hand", "h")[0], 0)

        by = {p["room"]: p for p in call("/api/stream?n=5")[1]["pages"]}
        self.assertIsNone(by[bare]["plate"])
        url = by[plated]["plate"]
        self.assertTrue(url.startswith("/stream/plate/2026-09-19/1020.jpg?v="), url)

        code, body = call(url)
        self.assertEqual(code, 200)
        self.assertTrue(len(body) > 0)
        # the one route that hands back a file: it only ever builds a path from a room name
        self.assertEqual(call("/stream/plate/2026-09-19/9999.jpg")[0], 404)
        self.assertEqual(call("/stream/plate/../../etc/passwd.jpg")[0], 404)
        self.assertEqual(call("/stream/plate/.trash/1020.jpg")[0], 404)
        self.assertEqual(call("/stream/plate/2026-09-19/a/b.jpg")[0], 404)


# ---- plating: one plate a dream -----------------------------------------------------------------

def run_plating(fake: dict) -> tuple[int, str]:
    was_path = os.environ.get("PATH", "")
    os.environ["PATH"] = fake["bin"] + os.pathsep + was_path
    os.environ["FAKE_CODEX_LOG"] = fake["log"]
    os.environ["FAKE_CODEX_MODE"] = fake["mode"]
    out = io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(out):
            code = plating.main(["plating.py", "--once"])
    finally:
        os.environ["PATH"] = was_path
        os.environ.pop("FAKE_CODEX_MODE", None)
    return code, out.getvalue()


class Plating(unittest.TestCase):
    def setUp(self):
        wipe_stream()
        self.fakes = []

    def test_a_stub_is_painted_like_any_dream(self):
        # the painter had a 15-word minimum once; bekh threw it out (2026-09-22) — no voice skips a stub
        stub = self.room(40)
        f = self.fake()
        self.assertEqual(run_plating(f)[0], 0)
        self.assertTrue(os.path.isfile(plate.plate_paths(stub)[0]))
        # The rooms' names carry their own clock, so the tests stamp names from real offsets.

    def tearDown(self):
        for f in self.fakes:
            shutil.rmtree(f["dir"], ignore_errors=True)

    def fake(self, mode: str = "") -> dict:
        f = fake_codex(mode)
        self.fakes.append(f)
        return f

    def at(self, minutes_ago: float) -> str:
        """A room name that IS a timestamp that many minutes ago — plating reads the clock off
        the name, so a fixture has to be named honestly."""
        lt = time.localtime(time.time() - minutes_ago * 60)
        return time.strftime("%Y-%m-%d/%H%M", lt)

    def room(self, minutes_ago: float, flag=None) -> str:
        stamp = self.at(minutes_ago)
        name = "stream/" + stamp
        make_page(name, "seed\n", "a dream from %s." % stamp, flag=flag)
        return name

    def test_it_paints_the_oldest_dream_that_wants_one(self):
        old = self.room(60)
        mid = self.room(30)
        self.room(0.5)                      # too young: the reader has not been past it
        f = self.fake()
        code, out = run_plating(f)
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.isfile(plate.plate_paths(old)[0]), "the oldest one first")
        self.assertFalse(os.path.isfile(plate.plate_paths(mid)[0]), "one plate per run")

        # the next run takes the next oldest, and the young one is still left alone
        self.assertEqual(run_plating(self.fake())[0], 0)
        self.assertTrue(os.path.isfile(plate.plate_paths(mid)[0]))
        rows = [r for r in ledger_rows() if r.get("kind") == "plating"]
        self.assertEqual([r["room"] for r in rows], [old, mid])
        self.assertTrue(all(r["painted"] for r in rows))

    def test_what_it_leaves_alone(self):
        self.room(30, flag="copyright")     # flagged
        self.room(0.2)                      # younger than the settle
        self.room(60 * 9)                   # older than the window
        done = self.room(45)                # already plated
        self.assertEqual(run_plating(self.fake())[0], 0)
        self.assertTrue(os.path.isfile(plate.plate_paths(done)[0]))
        f = self.fake()
        self.assertEqual(run_plating(f)[0], 0)
        self.assertFalse(os.path.exists(f["log"]), "codex was started with nothing to paint")

    def test_the_writer_taps_every_voice(self):
        put_seed("k.txt", MARK + " and then\n")
        seen = []
        real = stream.subprocess.run

        def watch(cmd, **kw):
            seen.append(cmd[-1].rsplit("/", 1)[-1])
            if "remembering" in cmd[-1]:
                raise OSError("launchctl went away")     # one failing stops nothing
            return real([sys.executable, "-c", ""], **kw)

        stream.subprocess.run = watch
        stream.KICK = True
        try:
            code, out = run("--once")
        finally:
            stream.subprocess.run = real
            stream.KICK = False
        self.assertEqual(code, 0, out)
        self.assertEqual(seen, ["com.bekh.eva-stream-interpreter",
                                "com.bekh.eva-stream-remembering",
                                "com.bekh.eva-stream-plating",
                                "com.bekh.eva-stream-analyst"])
        self.assertIn("kick · com.bekh.eva-stream-remembering", out)


# ---- live writing: the dream on the page while nemo writes it -------------------------------

def start_loom(**extra) -> tuple[subprocess.Popen, str]:
    """A loom of its own, on its own port, over the same scratch shelf — for the switches a
    loom reads once at start (read-only, the stale age, an upstream) that the module's loom
    cannot be flipped into."""
    port = int(extra.pop("port", 0) or free_port())
    env = dict(os.environ, LOOM_HOST="127.0.0.1", LOOM_PORT=str(port), LOOM_SITTINGS=SHELF,
               LOOM_ARTIFACTS=ARTS, LOOM_LLAMA=STUB_BASE, STREAM_DIR=STREAM_DIR,
               STREAM_INTERVAL="300", **{k: str(v) for k, v in extra.items()})
    proc = subprocess.Popen([sys.executable, os.path.join(EVA, "server", "loom.py")],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 20
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("loom died on start")
        try:
            with urllib.request.urlopen(base + "/api/health", timeout=2) as r:
                if r.status == 200:
                    return proc, base
        except OSError:
            pass
        time.sleep(0.15)
    raise RuntimeError("loom never came up")


def stop_loom(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()                  # by handle, never by name
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def post_live(base: str, text: str, seed: str = "LIVESEEDMARK the seed", done: bool = False):
    req = urllib.request.Request(base + "/api/stream/live",
                                 data=json.dumps({"text": text, "seed": seed,
                                                  "done": done}).encode("utf-8"),
                                 method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


class Events:
    """One held `/api/stream/events` client, read on its own thread: every event as
    (name, data, arrival time), in order, and the raw lines for the comments."""

    def __init__(self, base: str) -> None:
        u = urllib.parse.urlparse(base)
        self.conn = http.client.HTTPConnection(u.hostname, u.port, timeout=60)
        self.conn.request("GET", "/api/stream/events")
        # Kept before getresponse: a `Connection: close` answer makes http.client drop its own
        # handle on the socket, and close() below needs one to shut down.
        self.sock = self.conn.sock
        self.resp = self.conn.getresponse()
        self.events: list[tuple[str, dict, float]] = []
        self.lines: list[str] = []
        self.opened = threading.Event()
        self.t = threading.Thread(target=self.run, daemon=True)
        self.t.start()
        if not self.opened.wait(10):
            raise RuntimeError("the events route never said it was open")

    def run(self) -> None:
        name = ""
        try:
            for raw in self.resp:
                line = raw.decode("utf-8").rstrip("\n")
                self.lines.append(line)
                if line == ": open":
                    self.opened.set()
                elif line.startswith("event: "):
                    name = line[len("event: "):]
                elif line.startswith("data: "):
                    self.events.append((name, json.loads(line[len("data: "):]), time.monotonic()))
                elif not line:
                    name = ""
        except (OSError, ValueError):
            pass

    def wait(self, pred, timeout: float = 10):
        """The first event `pred` accepts, or None when none came in time."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for ev in list(self.events):
                if pred(ev):
                    return ev
            time.sleep(0.02)
        return None

    def live(self) -> list[dict]:
        return [d for n, d, _ in self.events if n == "live"]

    def close(self) -> None:
        # The socket, shut down under the reader: closing the response instead waits for the
        # reading thread to let go of its buffer, which is the next keepalive, 20 seconds away.
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.t.join(5)
        self.resp.close()
        self.sock.close()


class FakeLoom:
    """A loom that only listens: every `/api/stream/live` body it is sent, in arrival order."""

    def __init__(self) -> None:
        got = self.posts = []

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                n = int(self.headers.get("Content-Length", "0") or 0)
                got.append((self.path, json.loads(self.rfile.read(n))))
                data = b'{"ok": true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def close(self) -> None:
        self.srv.shutdown()
        self.srv.server_close()


class LiveWriter(unittest.TestCase):
    """The writer streams nemo's answer, and what lands on the shelf is what landed before."""

    def setUp(self):
        wipe_stream()
        loom.LLAMA = STUB_BASE
        self.live, self.every = stream.LIVE, stream.LIVE_EVERY

    def tearDown(self):
        stream.LIVE, stream.LIVE_EVERY = self.live, self.every
        loom.LLAMA = STUB_BASE

    def test_the_streamed_answer_is_the_one_lump_answer(self):
        # Same server, same scripted line: everything but the tps (the stub draws it per call)
        # must be the same dict, probabilities trimmed and rounded the same way.
        params = stream.sampler(Rng(0.9))
        loom.LLAMA = CLEAN_BASE
        lump = loom.complete("LIVESEEDMARK the lamp", params)
        streamed = stream.eva.complete_stream("LIVESEEDMARK the lamp", params, lambda s: None,
                                              url=CLEAN_BASE)
        for d in (lump, streamed):
            d.pop("tps")
        self.assertEqual(streamed, lump)
        self.assertTrue(lump["probs"])
        # and the wire said stream: true for the one and false for the other
        wire = [b for b in STUB_CLEAN.seen if "LIVESEEDMARK" in (b.get("prompt") or "")]
        self.assertEqual(sorted(bool(b.get("stream")) for b in wire[-2:]), [False, True])

        # A whole run: the room and the row are what the one-lump call would have written.
        stream.LIVE = ""
        put_seed("live.txt", "LIVESEEDMARK the lamp\n")
        code, out = run("--once")
        self.assertEqual(code, 0, out)
        d = on_disk(rooms()[0])
        node = [n for n in d["nodes"].values() if n["kind"] == "model"][0]
        self.assertEqual(node["text"], lump["text"])
        self.assertEqual(node["meta"]["logprobs"], stream.logprobs_of(lump["probs"]))
        self.assertNotIn("probs", node["meta"])
        self.assertEqual(node["meta"]["tokens_predicted"], lump["tokens_predicted"])
        self.assertEqual(node["meta"]["stop_type"], lump["stop_type"])
        self.assertGreater(node["meta"]["tps"], 0)
        row = ledger_rows()[-1]
        self.assertEqual((row["room"], row["tokens"]), (rooms()[0], lump["tokens_predicted"]))
        self.assertGreater(row["tps"], 0)

    def test_the_text_so_far_goes_to_the_loom_growing_and_done_comes_last(self):
        slow = stub_llama.serve(0, lines=["the lamp in the hall was still warm at four and "
                                          "nobody had come down to turn it off yet"],
                                token_delay=0.05)
        threading.Thread(target=slow.serve_forever, daemon=True).start()
        fake = FakeLoom()
        try:
            loom.LLAMA = f"http://127.0.0.1:{slow.server_address[1]}"
            stream.LIVE, stream.LIVE_EVERY = fake.base, 0.1
            put_seed("grow.txt", "LIVESEEDMARK it was late\n")
            code, out = run("--once")
        finally:
            slow.shutdown()
            fake.close()
        self.assertEqual(code, 0, out)
        d = on_disk(rooms()[0])
        root = d["nodes"][d["root"]]["text"]
        text = [n for n in d["nodes"].values() if n["kind"] == "model"][0]["text"]
        self.assertTrue(all(p == "/api/stream/live" for p, _ in fake.posts))
        posts = [b for _, b in fake.posts]
        self.assertGreaterEqual(len(posts), 4, posts)
        # the seed first, before nemo's first word, so the page has something to show at once
        self.assertEqual(posts[0]["text"], "")
        self.assertTrue(all(b["seed"] == root for b in posts))
        # growing: each post is the whole text so far, so every one is a prefix of the next
        for a, b in zip(posts, posts[1:]):
            self.assertTrue(b["text"].startswith(a["text"]), (a, b))
        self.assertEqual([b["done"] for b in posts], [False] * (len(posts) - 1) + [True])
        self.assertEqual(posts[-1]["text"], text)          # done carries the whole page

    def test_a_dead_loom_costs_one_line_and_the_page_lands(self):
        stream.LIVE, stream.LIVE_EVERY = f"http://127.0.0.1:{free_port()}", 0.05
        put_seed("dead.txt", "LIVESEEDMARK nobody listening\n")
        code, out = run("--once")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(rooms()), 1)
        self.assertEqual(ledger_rows()[-1]["room"], rooms()[0])
        self.assertEqual(out.count("live · "), 1, out)     # one line, not one per post

    def test_a_scratch_shelf_posts_nowhere_by_default(self):
        # this module runs on a scratch shelf with LOOM_LIVE unset: a test never types onto
        # the real reader
        self.assertEqual(self.live, "")


class LiveRoute(unittest.TestCase):
    """`POST /api/stream/live` → `event: live` on every held client, at once."""

    def tearDown(self):
        post_live(BASE, "", done=True)        # leave no half-dream for the next test's client

    def test_a_post_reaches_a_held_client_before_the_next_tick(self):
        ev = Events(BASE)
        try:
            time.sleep(0.1)
            sent = time.monotonic()
            self.assertEqual(post_live(BASE, "the lamp in"), 200)
            got = ev.wait(lambda e: e[0] == "live" and e[1]["text"] == "the lamp in")
        finally:
            ev.close()
        self.assertIsNotNone(got, ev.lines)
        # the tick is 2s here: under a second means the post woke the loop, not the clock
        self.assertLess(got[2] - sent, 1.0)
        self.assertEqual((got[1]["seed"], got[1]["done"]), ("LIVESEEDMARK the seed", False))
        self.assertIsInstance(got[1]["ts"], float)

    def test_a_late_client_gets_the_dream_so_far_first(self):
        post_live(BASE, "half a dre")
        ev = Events(BASE)
        try:
            got = ev.wait(lambda e: e[0] == "live", timeout=1.5)
        finally:
            ev.close()
        self.assertIsNotNone(got, ev.lines)
        self.assertEqual(got[1]["text"], "half a dre")
        # first thing after the open comment, before any tick could have said anything
        self.assertEqual(ev.lines[0], ": open")
        self.assertEqual(ev.lines[1:3], ["", "event: live"])

    def test_a_finished_dream_is_not_handed_to_a_late_client(self):
        post_live(BASE, "all of it", done=True)
        ev = Events(BASE)
        try:
            self.assertIsNone(ev.wait(lambda e: e[0] == "live", timeout=1.0))
        finally:
            ev.close()

    def test_done_then_the_change_with_the_room(self):
        wipe_stream()
        ev = Events(BASE)
        try:
            post_live(BASE, "the whole page")
            post_live(BASE, "the whole page", done=True)
            make_page("stream/2099-02-02/0202", "LIVESEEDMARK seed\n", "the whole page")
            change = ev.wait(lambda e: e[0] == "change"
                             and "stream/2099-02-02/0202" in e[1]["rooms"], timeout=10)
        finally:
            ev.close()
        self.assertIsNotNone(change, ev.lines)
        names = [(n, d.get("done")) for n, d, _ in ev.events]
        done_at = names.index(("live", True))
        self.assertLess(done_at, ev.events.index(change))

    def test_a_bad_post_is_refused(self):
        for body in ({"text": 5}, {"text": "x", "done": "yes"}, {"seed": "no text"}):
            req = urllib.request.Request(BASE + "/api/stream/live",
                                         data=json.dumps(body).encode("utf-8"), method="POST",
                                         headers={"Content-Type": "application/json"})
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(req, timeout=10)
            self.assertEqual(cm.exception.code, 400, body)


# ---- two dreamers: nemo and gpt-2, turn and turn about -----------------------------------------
# bekh, 2026-09-23: no blindness, no coin — strictly alternating, and every page says who wrote
# it. The turn is read off the newest page on the shelf, so everything here is set up by what is
# on the shelf and nothing else.

DUO = "DUOSEEDMARK"            # not a substring of any other test file's marker


def stamped_page(name: str, model) -> None:
    """A stream room written by hand and stamped as `model` wrote it — the shelf a ration
    that stopped earlier left behind."""
    nid = make_page(name, DUO + " an older seed\n", "an older page")
    d = on_disk(name)
    d["nodes"][nid]["meta"]["model"] = model
    loom.write_sitting(d)


class Dreamers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Two stubs that answer differently and name different files on /props, so a page can
        # be traced to the server that wrote it by its text as well as by its stamp — the stamp
        # being right about the wrong server is the bug this guards.
        cls.a = stub_llama.serve(0, model_path="/m/stub-nemo.Q5_K_M.gguf",
                                 lines=["the nemo stub says the kettle is singing."])
        cls.b = stub_llama.serve(0, n_ctx=1024, model_path="/m/stub-gpt2.Q8_0.gguf",
                                 lines=["the gpt2 stub says the rain has a key."])
        # a gpt-2 whose window holds nothing like a page: 64 < seed + 170
        cls.tight = stub_llama.serve(0, n_ctx=64, model_path="/m/stub-gpt2.Q8_0.gguf",
                                     lines=["never asked"])
        for srv in (cls.a, cls.b, cls.tight):
            threading.Thread(target=srv.serve_forever, daemon=True).start()
        cls.A = f"http://127.0.0.1:{cls.a.server_address[1]}"
        cls.B = f"http://127.0.0.1:{cls.b.server_address[1]}"
        cls.TIGHT = f"http://127.0.0.1:{cls.tight.server_address[1]}"
        cls.DEAD = f"http://127.0.0.1:{free_port()}"

    @classmethod
    def tearDownClass(cls):
        for srv in (cls.a, cls.b, cls.tight):
            srv.shutdown()

    def setUp(self):
        wipe_stream()
        loom.LLAMA = STUB_BASE
        self.models, self.live = stream.MODELS, stream.LIVE
        stream.MODELS = f"nemo={self.A},gpt2={self.B}"
        stream.LIVE = ""
        put_seed("duo.txt", DUO + " the hall light was\n")
        for srv in (self.a, self.b, self.tight):
            srv.seen.clear()                  # what each was asked in THIS test, not the class

    def tearDown(self):
        stream.MODELS, stream.LIVE = self.models, self.live
        loom.LLAMA = STUB_BASE

    def pages(self) -> list[dict]:
        """(room, the page node) for every stream room, oldest first."""
        out = []
        for name in rooms():
            d = on_disk(name)
            out.append((name, [n for n in d["nodes"].values() if n["kind"] == "model"][0]))
        return out

    def page_rows(self) -> list[dict]:
        return [r for r in ledger_rows() if r.get("kind") == "page"]

    def test_three_runs_alternate_and_every_page_and_row_is_stamped(self):
        for _ in range(3):
            code, out = run("--once")
            self.assertEqual(code, 0, out)
        got = self.pages()
        self.assertEqual([n["meta"]["model"] for _, n in got], ["nemo", "gpt2", "nemo"])
        # the stamp is the server that really wrote it, not only a label
        self.assertEqual([n["text"].split()[1] for _, n in got], ["nemo", "gpt2", "nemo"])
        self.assertEqual([n["meta"]["model_file"] for _, n in got],
                         ["stub-nemo.Q5_K_M.gguf", "stub-gpt2.Q8_0.gguf", "stub-nemo.Q5_K_M.gguf"])
        rows = self.page_rows()
        self.assertEqual([r["model"] for r in rows], ["nemo", "gpt2", "nemo"])
        self.assertEqual([r["room"] for r in rows], [name for name, _ in got])
        self.assertTrue(all("skipped" not in r for r in rows), rows)
        # one sampler for both seats: the params differ only in the heat drawn by lot
        ps = [dict(n["meta"]["params"]) for _, n in got]
        for p in ps:
            p.pop("temperature")
        self.assertEqual(ps[0], ps[1])
        # and each seat was handed the seed and nothing else
        for srv in (self.a, self.b):
            wire = [b for b in srv.seen if DUO in (b.get("prompt") or "")]
            self.assertTrue(wire)
            self.assertEqual(wire[-1]["prompt"], DUO + " the hall light was\n")

    def test_a_fresh_shelf_starts_on_the_first_seat(self):
        stream.MODELS = f"gpt2={self.B},nemo={self.A}"        # the order IS the turn order
        self.assertEqual(run("--once")[0], 0)
        self.assertEqual(self.pages()[0][1]["meta"]["model"], "gpt2")

    def test_a_run_after_a_stop_resumes_the_turn_from_the_newest_page(self):
        # yesterday's ration ended on gpt2; an older nemo page must not decide it
        stamped_page("stream/2026-01-01/2300", "nemo")
        stamped_page("stream/2026-01-01/2305", "gpt2")
        self.assertEqual(run("--once")[0], 0)
        self.assertEqual(self.pages()[-1][1]["meta"]["model"], "nemo")
        self.assertEqual(run("--once")[0], 0)
        self.assertEqual(self.pages()[-1][1]["meta"]["model"], "gpt2")

    def test_a_page_stamped_with_a_file_name_is_known_by_its_servers_file(self):
        # every page from before the seats carries nemo's FILE name; the first two-seat page
        # after such a night belongs to the other dreamer
        stamped_page("stream/2026-01-01/2300", "stub-nemo.Q5_K_M.gguf")
        self.assertEqual(run("--once")[0], 0)
        self.assertEqual(self.pages()[-1][1]["meta"]["model"], "gpt2")
        # and a stamp nobody answers to is the first seat
        wipe_stream()
        put_seed("duo.txt", DUO + " the hall light was\n")
        stamped_page("stream/2026-01-01/2300", "pythia")
        self.assertEqual(run("--once")[0], 0)
        self.assertEqual(self.pages()[-1][1]["meta"]["model"], "nemo")

    def test_a_dead_seat_is_skipped_and_the_row_says_why(self):
        stream.MODELS = f"nemo={self.A},gpt2={self.DEAD}"
        stamped_page("stream/2026-01-01/2300", "nemo")          # gpt2's turn, and it is down
        code, out = run("--once")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.pages()[-1][1]["meta"]["model"], "nemo")
        row = self.page_rows()[-1]
        self.assertEqual(row["model"], "nemo")
        self.assertEqual(row["skipped"], [{"model": "gpt2", "why": "down"}])
        self.assertIn("gpt2 · down", out)

    def test_a_seat_whose_window_cannot_hold_the_page_is_skipped(self):
        stream.MODELS = f"nemo={self.A},gpt2={self.TIGHT}"
        stamped_page("stream/2026-01-01/2300", "nemo")
        code, out = run("--once")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.pages()[-1][1]["meta"]["model"], "nemo")
        row = self.page_rows()[-1]
        self.assertEqual(len(row["skipped"]), 1)
        self.assertEqual(row["skipped"][0]["model"], "gpt2")
        self.assertRegex(row["skipped"][0]["why"], r"^window: \d+ \+ 170 to write > 64$")
        # counted on ITS tokenizer, and never handed the document it could not hold
        self.assertTrue(any(DUO in (b.get("content") or "") for b in self.tight.seen))
        self.assertFalse(any(DUO in (b.get("prompt") or "") for b in self.tight.seen))

    def test_every_seat_out_is_an_error_row_and_exit_zero(self):
        stream.MODELS = f"nemo={self.DEAD},gpt2={self.TIGHT}"
        code, out = run("--once")
        self.assertEqual(code, 0, out)
        self.assertEqual(rooms(), [])
        row = self.page_rows()[-1]
        self.assertIsNone(row["room"])
        self.assertEqual(row["error"], "every seat is out")
        self.assertEqual([s["model"] for s in row["skipped"]], ["nemo", "gpt2"])
        self.assertEqual(row["skipped"][0]["why"], "down")
        self.assertFalse(heartbeat()["ok"])

    def test_a_malformed_list_writes_nothing_and_says_so(self):
        stream.MODELS = "nemo http://127.0.0.1:1"
        code, out = run("--once")
        self.assertEqual(code, 0, out)
        self.assertEqual(rooms(), [])
        self.assertIn("STREAM_MODELS", self.page_rows()[-1]["error"])

    def test_unset_is_the_old_single_server_path(self):
        stream.MODELS = ""
        loom.LLAMA = self.A
        self.assertEqual(run("--once")[0], 0)
        node = self.pages()[0][1]
        self.assertEqual(node["meta"]["model"], "stub-nemo.Q5_K_M.gguf")   # the file, as ever
        self.assertNotIn("model_file", node["meta"])
        row = self.page_rows()[-1]
        self.assertNotIn("model", row)
        self.assertNotIn("skipped", row)
        # and /props is never asked for a window it has no use for
        self.assertFalse(any(DUO in (b.get("content") or "") for b in self.a.seen))

    def test_the_live_posts_say_who_is_typing(self):
        fake = FakeLoom()
        try:
            stream.LIVE = fake.base
            stamped_page("stream/2026-01-01/2300", "nemo")
            self.assertEqual(run("--once")[0], 0)
            posts = [b for _, b in fake.posts]
            self.assertTrue(posts)
            self.assertTrue(all(b.get("model") == "gpt2" for b in posts), posts)
            self.assertTrue(posts[-1]["done"])
            # the one-server path posts exactly what it always posted
            fake.posts.clear()
            stream.MODELS = ""
            self.assertEqual(run("--once")[0], 0)
            self.assertTrue(fake.posts)
            self.assertTrue(all("model" not in b for _, b in fake.posts))
        finally:
            fake.close()

    def test_the_live_route_carries_the_model(self):
        ev = Events(BASE)
        try:
            req = urllib.request.Request(
                BASE + "/api/stream/live", method="POST",
                data=json.dumps({"text": "DUO typing", "seed": "s", "done": False,
                                 "model": "gpt2"}).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                self.assertEqual(r.status, 200)
            got = ev.wait(lambda e: e[0] == "live" and e[1]["text"] == "DUO typing")
        finally:
            ev.close()
            post_live(BASE, "", done=True)
        self.assertIsNotNone(got, ev.lines)
        self.assertEqual(got[1]["model"], "gpt2")
        # a model that is not a short string is refused like any other bad field
        req = urllib.request.Request(BASE + "/api/stream/live", method="POST",
                                     data=json.dumps({"text": "x", "model": 5}).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(cm.exception.code, 400)

    def test_the_api_carries_the_model(self):
        stamped_page("stream/2026-01-01/2300", "stub-nemo.Q5_K_M.gguf")   # before the seats
        stamped_page("stream/2026-01-01/2301", {"model_path": "/x/GPT2-XL.Q8_0.gguf"})
        # the newest stamp answers to no seat (neither name nor file) → the first seat
        self.assertEqual(run("--once")[0], 0)
        pages = {p["room"]: p for p in call("/api/stream?n=10")[1]["pages"]}
        self.assertEqual(pages["stream/2026-01-01/2300"]["model"], "stub-nemo")
        self.assertEqual(pages["stream/2026-01-01/2301"]["model"], "gpt2-xl")
        self.assertEqual(pages[self.pages()[-1][0]]["model"], "nemo")


class LiveLooms(unittest.TestCase):
    """The switches a loom reads at start: the stale age, read-only, and the upstream pull."""

    def test_a_stale_dream_is_dropped(self):
        proc, base = start_loom(STREAM_LIVE_STALE="0.5")
        try:
            post_live(base, "a writer that died here")
            time.sleep(1.0)
            ev = Events(base)
            try:
                self.assertIsNone(ev.wait(lambda e: e[0] == "live", timeout=1.0), ev.lines)
            finally:
                ev.close()
        finally:
            stop_loom(proc)

    def test_the_mirror_refuses_a_post(self):
        proc, base = start_loom(LOOM_READONLY="1")
        try:
            self.assertEqual(post_live(base, "not here"), 403)
        finally:
            stop_loom(proc)

    def test_the_mirror_pulls_live_from_upstream_and_survives_it_going(self):
        up_port = free_port()
        up, up_base = start_loom(port=up_port)
        mirror, mirror_base = start_loom(LOOM_LIVE_UPSTREAM=up_base, LOOM_LIVE_RETRY_MAX="0.3",
                                         LOOM_READONLY="1")
        ev = None
        try:
            ev = Events(mirror_base)
            # The mirror's own connection upstream comes up on its own thread; post until the
            # typing shows up downstream instead of guessing how long that takes.
            got, deadline = None, time.monotonic() + 10
            while got is None and time.monotonic() < deadline:
                post_live(up_base, "typed on the mac")
                got = ev.wait(lambda e: e[0] == "live" and e[1]["text"] == "typed on the mac",
                              timeout=0.5)
            self.assertIsNotNone(got, ev.lines)

            # The mac goes to sleep: the mirror keeps serving and keeps its readers.
            stop_loom(up)
            time.sleep(1.0)
            self.assertEqual(urllib.request.urlopen(mirror_base + "/api/health",
                                                    timeout=5).status, 200)
            self.assertIsNone(mirror.poll())
            self.assertTrue(ev.t.is_alive())

            # And wakes: the mirror finds it again by itself.
            up, _ = start_loom(port=up_port)
            got, deadline = None, time.monotonic() + 10
            while got is None and time.monotonic() < deadline:
                post_live(up_base, "typed after the nap")
                got = ev.wait(lambda e: e[0] == "live"
                              and e[1]["text"] == "typed after the nap", timeout=0.5)
            self.assertIsNotNone(got, ev.lines)
        finally:
            if ev:
                ev.close()
            stop_loom(mirror)
            stop_loom(up)


if __name__ == "__main__":
    unittest.main()
