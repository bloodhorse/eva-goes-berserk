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

import loom  # noqa: E402
import stream  # noqa: E402

# Another test module in the same run may have imported loom first and pointed it at ITS
# scratch shelf; follow rather than argue (censustest carries the same knot). Either way it
# is never the real one — and the stream's own dirs are ours, set by name above.
if loom.SITTINGS != SHELF:
    SHELF = loom.SITTINGS
loom.STREAM_DIR = STREAM_DIR
loom.ARTIFACTS = ARTS

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
    """The stream's rooms, ledger and heartbeat, gone — so a test's pot B, its page count and
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
        self.assertEqual(p["n_predict"], 350)
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


if __name__ == "__main__":
    unittest.main()
