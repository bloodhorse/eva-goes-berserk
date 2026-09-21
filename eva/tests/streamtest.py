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

import interpreter  # noqa: E402
import plate  # noqa: E402
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
               STREAM_INTERVAL="300")
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

        put_seed("long.txt", MARK + " " + long)
        code, out = run("--once")
        self.assertEqual(code, 0, out)
        d = on_disk(rooms()[0])
        root = d["nodes"][d["root"]]["text"]
        self.assertLessEqual(len(root.split()), 45)          # what is stored is what nemo saw
        self.assertTrue(root.endswith("until the doors had"))

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
            # both other voices, each tapped on its own
            self.assertEqual(seen, [["launchctl", "kickstart",
                                     f"gui/{os.getuid()}/com.bekh.eva-stream-interpreter"],
                                    ["launchctl", "kickstart",
                                     f"gui/{os.getuid()}/com.bekh.eva-stream-remembering"]])
        finally:
            stream.subprocess.run = real
            stream.KICK = False

    def test_one_voice_failing_to_start_does_not_stop_the_other(self):
        put_seed("k.txt", MARK + " and then\n")
        seen = []
        real = stream.subprocess.run

        def half(cmd, **kw):
            seen.append(cmd[-1])
            if "interpreter" in cmd[-1]:
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
        self.assertEqual([j.rsplit("/", 1)[-1] for j in seen],
                         ["com.bekh.eva-stream-interpreter", "com.bekh.eva-stream-remembering"])
        self.assertIn("kick · com.bekh.eva-stream-interpreter", out)

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

def make_page(name: str, seed: str, text: str, flag=None, ts=None) -> str:
    """A stream room written by hand, so the api tests do not depend on what a stub said."""
    import eva as eva_mod
    s = eva_mod.blank(name, is_bare=True, root_text=seed)
    nid = "n" + name.replace("/", "").replace("-", "")[-8:]
    s["nodes"][nid] = {"id": nid, "parent": s["root"], "kind": "model", "text": text,
                       "ts": ts or time.time(), "pruned": False, "posed": False,
                       "meta": {"logprobs": [-0.1, -2.0], "flag": flag,
                                "params": {"temperature": 2.0}, "seed": "seeds/x.txt"}}
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
import io, json, os, re, sys
prompt = sys.stdin.read()
with open(os.environ["FAKE_CLAUDE_LOG"], "a", encoding="utf-8") as f:
    f.write(prompt + "\n=====\n")
mode = os.environ.get("FAKE_MODE", "")

USAGE = {"input_tokens": 12, "cache_read_input_tokens": 6642,
         "cache_creation_input_tokens": 3, "output_tokens": 301}

def answer(text, error=False):
    # The cli's own --output-format json shape: one result event with the usage block on it.
    json.dump({"type": "result", "subtype": "success", "is_error": error, "result": text,
               "usage": USAGE, "total_cost_usd": 0.0021782}, sys.stdout)
    raise SystemExit(0)

if mode == "boom":
    raise SystemExit(3)

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
    n = 1 if first else held.count(";") + 2
    answer("<dream>I was in it again" + ("" if first else " and before that " + held.split(";")[0])
           + "; then " + scene[:40] + " (" + str(n) + ")</dream>")

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

    def test_a_long_silence_starts_a_new_dream(self):
        self.scene("1000", "one.")
        self.assertEqual(remember(self.fake())[0], 0)
        first = dream_versions()[0]
        # `current` decides it off the versions and the clock, with no state file in between
        self.assertIsNotNone(remembering.current([first], first["ts"] + 10))
        self.assertIsNone(remembering.current([first], first["ts"] + remembering.GAP + 1))

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

    def test_live_is_the_newest_pack_inside_its_gap_and_cap(self):
        room = self.scene("1000", "one.")
        self.assertEqual(remember(self.fake())[0], 0)
        self.assertIs(call("/api/stream?n=3")[1]["pages"][0]["story"]["live"], True)

        # older than the gap: the pack is still shown, it is simply not live any more
        v, path = dream_versions()[0], remembering.version_files()[0]
        v["ts"] = time.time() - remembering.GAP - 10
        with open(path, "w", encoding="utf-8") as f:
            json.dump(v, f)
        p = call("/api/stream?n=3")[1]["pages"][0]
        self.assertIs(p["story"]["live"], False)
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
print("tokens used: 19123")
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
        code, out = make_plate(f, "--room", room, "--hand", "A test hand.")
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

    def test_no_underlines_falls_back_to_the_whole_text(self):
        room = "stream/2026-09-19/1005"
        make_page(room, "seed\n", "THE WHOLE DREAM TEXT")
        f = self.fake()
        code, out = make_plate(f, "--room", room, "--hand", "A test hand.")
        self.assertEqual(code, 0, out)
        self.assertIn("falling back", out)
        self.assertIn("THE WHOLE DREAM TEXT", read_text(f["log"]))
        d = json.load(open(plate.plate_paths(room)[2], encoding="utf-8"))
        self.assertEqual((d["prompt"], d["fell_back"]), ("bekh", True))

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


if __name__ == "__main__":
    unittest.main()
