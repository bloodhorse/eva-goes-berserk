#!/usr/bin/env -S uv run --python 3.12
from __future__ import annotations

import json
import math
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
import urllib.request

TESTS = os.path.dirname(os.path.abspath(__file__))
EVA = os.path.dirname(TESTS)
for d in (TESTS, os.path.join(EVA, "server")):
    if d not in sys.path:
        sys.path.insert(0, d)
import stub_llama  # noqa: E402

SCRATCH = tempfile.mkdtemp(prefix="talk-test-")
ROOMS = os.path.join(SCRATCH, "rooms")
TALKS = os.path.join(SCRATCH, "talks")
NOROOMS = os.path.join(SCRATCH, "norooms")
LOG = os.path.join(SCRATCH, "loom.log")
for key, sub in (("LOOM_SITTINGS", "sittings"), ("LOOM_STORAGE", "storage"),
                 ("LOOM_ARTIFACTS", "artifacts"), ("LOOM_CANVASES", "canvases"),
                 ("STREAM_DIR", "stream")):
    os.environ.setdefault(key, os.path.join(SCRATCH, sub))
os.environ.setdefault("LOOM_LEDGER", os.path.join(SCRATCH, "ledger.jsonl"))
import loom  # noqa: E402

SEED = "SEEDMARK-QUARTZ once there was a house on a hill and two people in it.\n"
BEFORE = "\n@@BEFORE-OSPREY "
AFTER = " @@AFTER-HERON\n"
CLOSE = " @@CLOSE-WREN"
STOP = ["@@STOP-FINCH", "\nbekh:"]
SAMPLER = {"temperature": 0.9, "min_p": 0.08, "dry_multiplier": 0.8, "dry_base": 1.75,
           "dry_allowed_length": 2, "n_predict": 20}
SECRETS = ("SEEDMARK", "@@BEFORE", "@@AFTER", "@@CLOSE", "@@STOP", "after supper")

A = B = C = None
LOOM = None
LOOM_OUT = None
BASE = ""
DEAD = ""


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def url_of(srv) -> str:
    return f"http://127.0.0.1:{srv.server_address[1]}"


def fetch(path: str, body=None, base: str = "", timeout: float = 30):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request((base or BASE) + path, data=data,
                                 method="POST" if data else "GET",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw, status, ctype = r.read(), r.status, r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raw, status, ctype = e.read(), e.code, e.headers.get("Content-Type", "")
    text = raw.decode("utf-8", "replace")
    for secret in SECRETS:
        if secret in text:
            raise AssertionError(f"{path} let {secret} out of the server")
    if "json" in ctype:
        return status, json.loads(text)
    return status, text


def events(text: str) -> list[tuple[str, dict]]:
    out = []
    for block in text.split("\n\n"):
        kind, data = "", ""
        for row in block.split("\n"):
            if row.startswith("event:"):
                kind = row[6:].strip()
            elif row.startswith("data:"):
                data += row[5:].strip()
        if kind:
            out.append((kind, json.loads(data or "{}")))
    return out


def write_room(name: str, seed: str = SEED, seed_file: str = "seed.txt", **over) -> None:
    folder = os.path.join(ROOMS, name)
    os.makedirs(folder, exist_ok=True)
    room = {"title": f"the {name} room", "seed": seed_file,
            "turn": {"before": BEFORE, "after": AFTER}, "close": CLOSE, "stop": STOP,
            "sampler": SAMPLER, "window": 1024}
    room.update(over)
    with open(os.path.join(folder, "seed.txt"), "w", encoding="utf-8", newline="") as f:
        f.write(seed)
    with open(os.path.join(folder, "room.json"), "w", encoding="utf-8") as f:
        json.dump(room, f)


def script(srv, lines) -> None:
    srv.lines = lines
    srv._line_i = 0


def prompts(srv, since: int = 0) -> list[dict]:
    return [b for b in srv.seen[since:] if "prompt" in b]


def record(room: str) -> list[dict]:
    path = os.path.join(TALKS, room, time.strftime("%Y-%m-%d") + ".jsonl")
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return []
    for secret in SECRETS:
        if secret in raw:
            raise AssertionError(f"the record of {room} holds {secret}")
    return [json.loads(row) for row in raw.splitlines() if row.strip()]


def start_loom(port: int, out, **extra) -> subprocess.Popen:
    env = dict(os.environ, LOOM_HOST="127.0.0.1", LOOM_PORT=str(port),
               LOOM_SITTINGS=os.path.join(SCRATCH, "sittings"),
               LOOM_STORAGE=os.path.join(SCRATCH, "storage"),
               LOOM_ARTIFACTS=os.path.join(SCRATCH, "artifacts"),
               LOOM_CANVASES=os.path.join(SCRATCH, "canvases"),
               LOOM_LEDGER=os.path.join(SCRATCH, "ledger.jsonl"),
               STREAM_DIR=os.path.join(SCRATCH, "stream"),
               LOOM_ROOMS=ROOMS, LOOM_TALKS=TALKS, LOOM_LLAMA=url_of(A))
    env.pop("LOOM_READONLY", None)
    env.pop("LOOM_PAGE", None)
    env.pop("LOOM_TALK_PAGE", None)
    env.update(extra)
    proc = subprocess.Popen([sys.executable, os.path.join(EVA, "server", "loom.py")],
                            env=env, stdout=out, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 20
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("loom died on start")
        try:
            if fetch("/api/rooms", base=base)[0] == 200:
                return proc
        except OSError:
            pass
        time.sleep(0.15)
    proc.terminate()
    raise RuntimeError("loom never came up")


def setUpModule() -> None:
    global A, B, C, LOOM, LOOM_OUT, BASE, DEAD
    os.makedirs(ROOMS, exist_ok=True)
    os.makedirs(NOROOMS, exist_ok=True)
    A, B, C = stub_llama.serve(0), stub_llama.serve(0), stub_llama.serve(0)
    C.no_tokenize = True
    for srv in (A, B, C):
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    DEAD = f"http://127.0.0.1:{free_port()}"
    write_room("glass")
    write_room("pair", models={"one": url_of(A), "two": url_of(B)})
    write_room("dead", models={"gone": DEAD})
    port = free_port()
    BASE = f"http://127.0.0.1:{port}"
    LOOM_OUT = open(LOG, "wb")
    LOOM = start_loom(port, LOOM_OUT)


def tearDownModule() -> None:
    if LOOM and LOOM.poll() is None:
        LOOM.terminate()
        try:
            LOOM.wait(timeout=5)
        except subprocess.TimeoutExpired:
            LOOM.kill()
    if LOOM_OUT:
        LOOM_OUT.close()
    for srv in (A, B, C):
        if srv:
            srv.shutdown()
            srv.server_close()
    shutil.rmtree(SCRATCH, ignore_errors=True)


class Prompt(unittest.TestCase):
    def ask(self, history, line, **more):
        script(A, [" the lamp is lit"])
        mark = len(A.seen)
        st, d = fetch("/api/talk", dict({"room": "glass", "history": history, "line": line},
                                        **more))
        self.assertEqual(st, 200, d)
        sent = prompts(A, mark)
        self.assertEqual(len(sent), 1)
        return d, sent[0]

    def test_no_exchanges(self):
        d, body = self.ask([], "is anyone home")
        self.assertEqual(body["prompt"], SEED + BEFORE + "is anyone home" + AFTER)
        self.assertEqual(d["her"], "the lamp is lit")
        self.assertEqual(d["line"], "is anyone home")
        self.assertNotIn("dropped", d)

    def test_one_exchange(self):
        d, body = self.ask([{"me": "hello", "her": "come in"}], "where do i sit")
        self.assertEqual(body["prompt"], SEED + BEFORE + "hello" + AFTER + "come in" + CLOSE
                         + BEFORE + "where do i sit" + AFTER)

    def test_several_exchanges(self):
        history = [{"me": "one", "her": "first"}, {"me": "two", "her": "second"},
                   {"me": "three", "her": ""}]
        d, body = self.ask(history, "four")
        want = SEED
        for ex in history:
            want += BEFORE + ex["me"] + AFTER + ex["her"] + CLOSE
        self.assertEqual(body["prompt"], want + BEFORE + "four" + AFTER)

    def test_sampler_goes_through_with_the_stops(self):
        d, body = self.ask([], "what is the weather")
        for k, v in SAMPLER.items():
            self.assertEqual(body[k], v)
        self.assertEqual(body["stop"], STOP)
        self.assertIsInstance(body["seed"], int)
        self.assertEqual(d["seed"], body["seed"])

    def test_the_tokens_are_counted_on_the_model(self):
        d, body = self.ask([], "count me")
        words = len((SEED + BEFORE + "count me" + AFTER).split())
        self.assertEqual(d["tokens"], 1 + words)


class Trim(unittest.TestCase):
    HISTORY = [{"me": f"m{i} x y", "her": f"h{i} p q"} for i in range(5)]

    def narrow(self, name: str, window: int, **over) -> None:
        write_room(name, seed="SEEDMARK-NARROW a b c d", window=window,
                   turn={"before": "\nhe ", "after": "\nshe "}, close="",
                   stop=["\nbekh:"], sampler={"n_predict": 10}, **over)

    def test_oldest_go_first_and_the_seed_stays(self):
        self.narrow("narrow", 40 + 10 + loom.TALK_MARGIN)
        script(A, [" fine"])
        mark = len(A.seen)
        st, d = fetch("/api/talk", {"room": "narrow", "history": self.HISTORY, "line": "and now"})
        self.assertEqual(st, 200, d)
        self.assertEqual(d["dropped"], 2)
        self.assertEqual(d["tokens"], 34)
        want = "SEEDMARK-NARROW a b c d"
        for ex in self.HISTORY[2:]:
            want += "\nhe " + ex["me"] + "\nshe " + ex["her"]
        self.assertEqual(prompts(A, mark)[0]["prompt"], want + "\nhe and now\nshe ")
        self.assertEqual(record("narrow")[-1]["dropped"], 2)
        self.assertEqual(record("narrow")[-1]["tokens"], 34)

    def test_a_window_too_small_for_any_of_it_still_sends_the_seed(self):
        self.narrow("tiny", 8 + 10 + loom.TALK_MARGIN)
        script(A, [" fine"])
        mark = len(A.seen)
        st, d = fetch("/api/talk", {"room": "tiny", "history": self.HISTORY, "line": "and now"})
        self.assertEqual(st, 200, d)
        self.assertEqual(d["dropped"], 5)
        self.assertEqual(prompts(A, mark)[0]["prompt"],
                         "SEEDMARK-NARROW a b c d\nhe and now\nshe ")

    def test_nothing_dropped_when_it_fits(self):
        self.narrow("roomy", 1024)
        script(A, [" fine"])
        st, d = fetch("/api/talk", {"room": "roomy", "history": self.HISTORY, "line": "and now"})
        self.assertEqual(st, 200, d)
        self.assertNotIn("dropped", d)
        self.assertEqual(d["tokens"], 1 + 5 + 8 * 5 + 4)

    def test_no_tokenize_falls_back_to_an_estimate(self):
        seed = "SEEDMARK-NARROW a b c d"
        history = self.HISTORY[:2]

        def rest(h):
            return "".join("\nhe " + e["me"] + "\nshe " + e["her"] for e in h) + "\nhe and now\nshe "

        def guess(h):
            return 1 + math.ceil(len(seed) / 3.5) + math.ceil(len(rest(h)) / 3.5)

        self.assertGreater(guess(history), guess(history[1:]))
        self.narrow("guess", guess(history[1:]) + 10 + loom.TALK_MARGIN, models={"c": url_of(C)})
        script(C, [" fine"])
        mark = len(C.seen)
        st, d = fetch("/api/talk", {"room": "guess", "history": history, "line": "and now"})
        self.assertEqual(st, 200, d)
        self.assertEqual(d["dropped"], 1)
        self.assertEqual(d["tokens"], guess(history[1:]))
        self.assertEqual(prompts(C, mark)[0]["prompt"], seed + rest(history[1:]))


class Reply(unittest.TestCase):
    def test_the_stop_string_is_cut_and_the_edges_trimmed(self):
        script(A, ["  \n the hill is quiet  @@STOP-FINCH and then more"])
        st, d = fetch("/api/talk", {"room": "glass", "history": [], "line": "how is the hill"})
        self.assertEqual((st, d["her"]), (200, "the hill is quiet"))

    def test_an_empty_reply_is_asked_once_more_with_another_seed(self):
        script(A, ["", " there you are"])
        mark = len(A.seen)
        st, d = fetch("/api/talk", {"room": "glass", "history": [], "line": "are you there"})
        self.assertEqual((st, d["her"]), (200, "there you are"))
        sent = prompts(A, mark)
        self.assertEqual(len(sent), 2)
        self.assertEqual(sent[0]["prompt"], sent[1]["prompt"])
        self.assertNotEqual(sent[0]["seed"], sent[1]["seed"])
        row = record("glass")[-1]
        self.assertEqual((row["tries"], row["seed"], row["her"]),
                         (2, sent[1]["seed"], "there you are"))

    def test_two_empty_replies_are_silence(self):
        script(A, ["", "   "])
        mark = len(A.seen)
        st, d = fetch("/api/talk", {"room": "glass", "history": [], "line": "say nothing"})
        self.assertEqual((st, d["her"]), (200, ""))
        self.assertEqual(len(prompts(A, mark)), 2)
        self.assertEqual(record("glass")[-1]["her"], "")

    def test_a_pinned_seed_is_used_first(self):
        write_room("pinned", sampler=dict(SAMPLER, seed=4242))
        script(A, ["", " again"])
        mark = len(A.seen)
        st, d = fetch("/api/talk", {"room": "pinned", "history": [], "line": "pin"})
        sent = prompts(A, mark)
        self.assertEqual(sent[0]["seed"], 4242)
        self.assertNotEqual(sent[1]["seed"], 4242)

    def test_streamed(self):
        script(A, [" one two three four"])
        st, raw = fetch("/api/talk", {"room": "glass", "history": [], "line": "count",
                                      "stream": True})
        self.assertEqual(st, 200)
        evs = events(raw)
        kinds = [k for k, _ in evs]
        self.assertEqual(kinds[0], "start")
        self.assertEqual(kinds[-1], "done")
        self.assertGreater(kinds.count("piece"), 2)
        said = "".join(d["text"] for k, d in evs if k == "piece")
        self.assertEqual(said.strip(), "one two three four")
        self.assertEqual(evs[-1][1]["her"], "one two three four")
        self.assertEqual(evs[0][1]["line"], "count")
        self.assertEqual(record("glass")[-1]["her"], "one two three four")

    def test_streamed_empty_then_again(self):
        script(A, ["", " second go"])
        st, raw = fetch("/api/talk", {"room": "glass", "history": [], "line": "retry",
                                      "stream": True})
        evs = events(raw)
        self.assertIn("again", [k for k, _ in evs])
        self.assertEqual(evs[-1], ("done", evs[-1][1]))
        self.assertEqual(evs[-1][1]["her"], "second go")


class Line(unittest.TestCase):
    def test_too_long_is_refused_with_the_cap(self):
        mark = len(A.seen)
        st, d = fetch("/api/talk", {"room": "glass", "history": [],
                                    "line": "x" * (loom.TALK_LINE_MAX + 1)})
        self.assertEqual(st, 400)
        self.assertEqual(d["max"], loom.TALK_LINE_MAX)
        self.assertIn("too long", d["error"])
        self.assertEqual(prompts(A, mark), [])
        st, d = fetch("/api/rooms")
        self.assertEqual(d["line_max"], loom.TALK_LINE_MAX)

    def test_a_stop_string_and_newlines_are_taken_out_and_the_page_is_told(self):
        script(A, [" heard"])
        mark = len(A.seen)
        st, d = fetch("/api/talk", {"room": "glass", "history": [],
                                    "line": "  first@@STOP-FINCH part\n\nsecond  part "})
        self.assertEqual(st, 200, d)
        self.assertEqual(d["line"], "first part second part")
        self.assertEqual(prompts(A, mark)[0]["prompt"],
                         SEED + BEFORE + "first part second part" + AFTER)
        self.assertEqual(record("glass")[-1]["me"], "first part second part")

    def test_empty_missing_and_misshapen(self):
        for body in ({"room": "glass", "history": [], "line": "   "},
                     {"room": "glass", "history": []},
                     {"room": "glass", "history": [], "line": 7},
                     {"room": "glass", "history": "no", "line": "hi"},
                     {"room": "glass", "history": [{"me": 1, "her": "x"}], "line": "hi"},
                     {"room": "glass", "history": [], "line": "hi", "model": "nobody"}):
            st, d = fetch("/api/talk", body)
            self.assertEqual(st, 400, body)
            self.assertIn("error", d)


class Rooms(unittest.TestCase):
    def test_listing_names_titles_and_models_only(self):
        st, d = fetch("/api/rooms")
        self.assertEqual(st, 200)
        by = {r["name"]: r for r in d["rooms"]}
        self.assertEqual(by["glass"], {"name": "glass", "title": "the glass room", "models": []})
        self.assertEqual(by["pair"]["models"], ["one", "two"])
        self.assertNotIn(loom.TALK_BUILTIN_NAME, by)
        for r in d["rooms"]:
            self.assertEqual(sorted(r), ["models", "name", "title"])

    def test_unknown_room(self):
        for name in ("nowhere", "../glass", ".hidden", "", None, "glass/seed.txt"):
            st, d = fetch("/api/talk", {"room": name, "history": [], "line": "hi"})
            self.assertEqual((st, d["error"]), (404, "no such room"), name)

    def test_a_malformed_room_is_not_listed_and_is_logged_once(self):
        os.makedirs(os.path.join(ROOMS, "broken"), exist_ok=True)
        with open(os.path.join(ROOMS, "broken", "room.json"), "w") as f:
            f.write("{nope")
        with open(os.path.join(ROOMS, "broken", "seed.txt"), "w") as f:
            f.write("SEEDMARK-BROKEN")
        write_room("seedless", seed="SEEDMARK-SEEDLESS", seed_file="missing.txt")
        write_room("turnless", turn={"before": "x"})
        write_room("climber", seed_file="../glass/seed.txt")
        os.makedirs(os.path.join(ROOMS, "halfmade"), exist_ok=True)
        for _ in range(3):
            st, d = fetch("/api/rooms")
            names = [r["name"] for r in d["rooms"]]
            for bad in ("broken", "seedless", "turnless", "climber", "halfmade"):
                self.assertNotIn(bad, names)
            self.assertIn("glass", names)
        st, d = fetch("/api/talk", {"room": "broken", "history": [], "line": "hi"})
        self.assertEqual(st, 404)
        time.sleep(0.2)
        with open(LOG, encoding="utf-8") as f:
            log = f.read()
        for bad in ("broken", "seedless", "turnless", "climber"):
            self.assertEqual(log.count(f"room {bad} is malformed"), 1, log)
        self.assertNotIn("halfmade", log)
        self.assertNotIn("SEEDMARK", log)

    def test_the_page_is_served_and_holds_nothing_of_a_room(self):
        for path in ("/talk", "/talk/glass", "/talk/pair", "/talk.html"):
            st, page = fetch(path)
            self.assertEqual(st, 200)
            self.assertIn("<title>talk</title>", page)
        low = page.lower()
        for word in ("assistant", "user"):
            self.assertNotIn(word, low)
        self.assertEqual(fetch("/")[0], 200)
        self.assertEqual(fetch("/api/health")[0], 200)


class Models(unittest.TestCase):
    def test_the_map_is_honoured(self):
        script(A, [" from the first"])
        script(B, [" from the second"])
        a, b = len(A.seen), len(B.seen)
        st, d = fetch("/api/talk", {"room": "pair", "history": [], "line": "who is it"})
        self.assertEqual((st, d["her"], d["model"]), (200, "from the first", "one"))
        st, d = fetch("/api/talk", {"room": "pair", "model": "two", "history": [],
                                    "line": "who is it"})
        self.assertEqual((st, d["her"], d["model"]), (200, "from the second", "two"))
        self.assertEqual(len(prompts(A, a)), 1)
        self.assertEqual(len(prompts(B, b)), 1)
        self.assertEqual([r["model"] for r in record("pair")[-2:]], ["one", "two"])

    def test_no_map_is_the_looms_own_model_and_the_built_in_room_answers(self):
        script(A, [" on the step\" he"])
        mark = len(A.seen)
        st, d = fetch("/api/talk", {"room": loom.TALK_BUILTIN_NAME, "history":
                                    [{"me": "evening", "her": "evening"}],
                                    "line": "where \"are\" you"})
        self.assertEqual((st, d["her"], d["model"]), (200, "on the step", loom.TALK_LOOM_MODEL))
        self.assertEqual(d["line"], "where are you")
        r = loom.TALK_BUILTIN
        body = prompts(A, mark)[0]
        self.assertEqual(body["prompt"], r["seed"] + r["before"] + "evening" + r["after"]
                         + "evening" + r["close"] + r["before"] + "where are you" + r["after"])
        self.assertEqual(body["stop"], r["stop"])
        self.assertEqual(record(loom.TALK_BUILTIN_NAME)[-1]["model"], loom.TALK_LOOM_MODEL)

    def test_the_model_down_is_a_clear_error(self):
        for stream in (False, True):
            st, d = fetch("/api/talk", {"room": "dead", "history": [], "line": "hello",
                                        "stream": stream})
            self.assertEqual(st, 502)
            self.assertEqual(d["error"], "she is not answering")
        self.assertEqual(record("dead"), [])


class Record(unittest.TestCase):
    def test_one_line_per_exchange_and_a_regenerate(self):
        write_room("ledger")
        script(A, [" first answer", " second answer", " third answer"])
        mark = len(A.seen)
        st, one = fetch("/api/talk", {"room": "ledger", "history": [], "line": "open"})
        history = [{"me": "open", "her": one["her"]}]
        st, two = fetch("/api/talk", {"room": "ledger", "history": history, "line": "go on"})
        st, three = fetch("/api/talk", {"room": "ledger", "history": history, "line": "go on",
                                        "again": True})
        self.assertEqual([one["her"], two["her"], three["her"]],
                         ["first answer", "second answer", "third answer"])
        sent = prompts(A, mark)
        self.assertEqual(len(sent), 3)
        self.assertEqual(sent[1]["prompt"], sent[2]["prompt"])
        self.assertEqual(sent[2]["prompt"], SEED + BEFORE + "open" + AFTER + "first answer"
                         + CLOSE + BEFORE + "go on" + AFTER)
        rows = record("ledger")
        self.assertEqual(len(rows), 3)
        self.assertEqual([(r["me"], r["her"]) for r in rows],
                         [("open", "first answer"), ("go on", "second answer"),
                          ("go on", "third answer")])
        self.assertEqual([r.get("again", False) for r in rows], [False, False, True])
        for r, sent_body in zip(rows, sent):
            self.assertEqual(r["model"], loom.TALK_LOOM_MODEL)
            self.assertEqual(r["seed"], sent_body["seed"])
            self.assertEqual(r["dropped"], 0)
            self.assertGreater(r["tokens"], 0)
            self.assertIn("ts", r)
            self.assertEqual(r["time"][:10], time.strftime("%Y-%m-%d"))


class Mirror(unittest.TestCase):
    def setUp(self):
        port = free_port()
        self.base = f"http://127.0.0.1:{port}"
        self.proc = start_loom(port, subprocess.DEVNULL, LOOM_READONLY="1", LOOM_ROOMS=NOROOMS)

    def tearDown(self):
        self.proc.terminate()
        self.proc.wait(timeout=5)

    def test_read_only_refuses_and_an_empty_shelf_lists_the_built_in_room(self):
        st, d = fetch("/api/rooms", base=self.base)
        self.assertEqual(d["rooms"], [{"name": loom.TALK_BUILTIN_NAME,
                                       "title": loom.TALK_BUILTIN["title"], "models": []}])
        self.assertEqual(fetch("/talk", base=self.base)[0], 200)
        mark = len(A.seen)
        st, d = fetch("/api/talk", {"room": loom.TALK_BUILTIN_NAME, "history": [],
                                    "line": "hello"}, base=self.base)
        other = fetch("/api/delete", {"name": "x"}, base=self.base)
        self.assertEqual((st, d), other)
        self.assertEqual(st, 403)
        self.assertEqual(prompts(A, mark), [])


if __name__ == "__main__":
    unittest.main()
