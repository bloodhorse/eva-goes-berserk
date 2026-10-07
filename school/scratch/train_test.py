import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import unittest

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
SCHOOL = os.path.dirname(HERE)
OLD_TRAIN_BLOB = "ca4d2cd59701bc4328aea07dbba131f8aaa6681d"
OLD_TRAIN_MD5 = "58f2535007728bb4b78ad490411dfc8c"
OLD_TURN_BLOB = "d6cf62b3f36bfef8db505ac9454e401bfbe7a681"
NEW_TRAIN = os.environ.get("TRAIN_NEW", os.path.join(HERE, "train.py"))
NEW_TURN = os.environ.get("TURN_NEW", os.path.join(SCHOOL, "night", "turn.py"))
RUN4 = os.environ.get("RUN4", os.path.join(SCHOOL, "night", "run4.sh"))
PAGE = os.path.join(SCHOOL, "night", "page.py")
DAY3 = os.path.join(SCHOOL, "night", "day3")
HOLD = tempfile.TemporaryDirectory(prefix="train_test_")
TMP = os.environ.get("TRAIN_TEST_TMP") or HOLD.name
MIX = ["bins/easy.bin:3", "bins/markov.bin:2", "bins/zipf.bin:2", "bins/hard.bin:1"]
SHELVES = ["easy", "markov", "zipf", "hard"]
SMALL = ["--layers", "2", "--heads", "2", "--width", "32", "--ctx", "64", "--batch", "16", "--accum", "2", "--lr", "2e-3", "--warmup", "5",
         "--log-every", "1", "--eval-every", "10", "--eval-iters", "4", "--ckpt-minutes", "1000", "--seed", "7"]
STEP = re.compile(r"^step (\d+)/(\S+) \| loss (\S+) \| eval (.*?) \| lr (\S+) \|.*?(?: \| train (.*))?$")
CACHE = {}


def read(path, mode="r"):
    with open(path, mode, encoding=None if "b" in mode else "utf-8") as f:
        return f.read()


def blob(sha, name, env):
    if os.environ.get(env):
        return os.environ[env]
    path = os.path.join(TMP, "old", name)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(subprocess.run(["git", "-C", SCHOOL, "cat-file", "-p", sha], capture_output=True, check=True).stdout)
    return path


def old_train():
    path = blob(OLD_TRAIN_BLOB, "train.py", "TRAIN_OLD")
    assert hashlib.md5(read(path, "rb")).hexdigest() == OLD_TRAIN_MD5, "the frozen old trainer is not the one on the host"
    return path


def old_turn():
    return blob(OLD_TURN_BLOB, "turn.py", "TURN_OLD")


def make_bins():
    root = os.path.join(TMP, "bins")
    if os.path.isdir(root):
        return
    os.makedirs(root)
    r = np.random.default_rng(11)
    vocab = 256
    nxt = r.integers(3, vocab, size=(vocab, 2))
    p = 1 / np.arange(1, vocab - 2)
    p /= p.sum()

    def easy(n):
        return np.tile(np.array([5, 9, 17, 33, 65, 129, 200, 250]), n // 8 + 1)[:n]

    def markov(n):
        out, t = np.empty(n, dtype=np.int64), 7
        for i, c in enumerate(r.integers(0, 2, size=n)):
            out[i] = t
            t = nxt[t, c]
        return out

    def zipf(n):
        return r.choice(np.arange(3, vocab), size=n, p=p)

    def hard(n):
        return r.integers(3, vocab, size=n)

    for name, fn in (("easy", easy), ("markov", markov), ("zipf", zipf), ("hard", hard)):
        fn(60000).astype(np.uint16).tofile(f"{root}/{name}.bin")
        fn(8000).astype(np.uint16).tofile(f"{root}/{name}.val.bin")
        with open(f"{root}/{name}.json", "w") as f:
            json.dump({"dtype": "uint16", "vocab": vocab, "bos": 1, "eos": 2}, f)


def command(trainer, out, steps=None, shape=SMALL, fresh=True):
    cmd = [sys.executable, trainer, "--data", *MIX, "--out", out]
    if fresh:
        cmd += [*shape, "--steps", str(steps)]
    return cmd


def train(trainer, out, steps=None, shape=SMALL, fresh=True):
    p = subprocess.run(command(trainer, out, steps, shape, fresh), cwd=TMP, capture_output=True, text=True)
    if p.returncode != 0:
        raise AssertionError(f"trainer exit {p.returncode}\n{p.stdout[-2000:]}\n{p.stderr[-3000:]}")
    return p.stdout


def steps_of(log):
    out = []
    for line in log.splitlines():
        m = STEP.match(line)
        if m:
            out.append((int(m.group(1)), m.group(2), m.group(3), m.group(4), m.group(5)))
    return out


def train_lines(log):
    out = {}
    for line in log.splitlines():
        m = STEP.match(line)
        if m and m.group(6):
            parts = m.group(6).split()
            out[int(m.group(1))] = dict(zip(parts[::2], map(float, parts[1::2])))
    return out


def mix_lines(log):
    return [l for l in log.splitlines() if l.startswith("MIX ")]


def status(out):
    with open(os.path.join(TMP, out, "status.json")) as f:
        return json.load(f)


def ckpt(out):
    return torch.load(os.path.join(TMP, out, "ckpt.pt"), map_location="cpu", weights_only=False)


def same(a, b):
    if isinstance(a, torch.Tensor):
        return isinstance(b, torch.Tensor) and a.dtype == b.dtype and torch.equal(a, b)
    if isinstance(a, dict):
        return isinstance(b, dict) and list(a) == list(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return isinstance(b, (list, tuple)) and len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def differs(a, b):
    x, y = ckpt(a), ckpt(b)
    return [k for k in ("model", "opt", "rng", "step", "total_steps", "tokens", "last_eval", "last_eval_step") if not same(x[k], y[k])]


def stretch(out, total):
    path = os.path.join(TMP, out, "ckpt.pt")
    c = torch.load(path, map_location="cpu", weights_only=False)
    c["total_steps"] = total
    torch.save(c, path)


def clone(src, dst):
    shutil.copytree(os.path.join(TMP, src), os.path.join(TMP, dst))
    return dst


def put(out, text):
    os.makedirs(os.path.join(TMP, out), exist_ok=True)
    path = os.path.join(TMP, out, "weights.json")
    with open(path + ".new", "w") as f:
        f.write(text)
    os.replace(path + ".new", path)


def reference():
    if "ref" not in CACHE:
        CACHE["ref"] = train(NEW_TRAIN, "runs/ref", 30)
    return CACHE["ref"]


def module(path, name):
    if name not in CACHE:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        CACHE[name] = mod
    return CACHE[name]


def setUpModule():
    os.makedirs(TMP, exist_ok=True)
    make_bins()


def tearDownModule():
    HOLD.cleanup()


class Identity(unittest.TestCase):
    def test_no_weights_file_no_change(self):
        two_chunks = SMALL[:SMALL.index("--batch") + 1] + ["66"] + SMALL[SMALL.index("--batch") + 2:]
        for tag, shape in (("one-chunk", SMALL), ("two-chunks", two_chunks)):
            with self.subTest(tag):
                a = train(old_train(), f"runs/id-old-{tag}", 30, shape)
                b = train(NEW_TRAIN, f"runs/id-new-{tag}", 30, shape)
                self.assertEqual(len(steps_of(a)), 30)
                self.assertEqual(steps_of(a), steps_of(b))
                self.assertEqual(differs(f"runs/id-old-{tag}", f"runs/id-new-{tag}"), [])
                sa, sb = status(f"runs/id-old-{tag}"), status(f"runs/id-new-{tag}")
                self.assertEqual(sa["eval_loss"], sb["eval_loss"])
                self.assertEqual(sa["eval_per_file"], sb["eval_per_file"])
                self.assertEqual(mix_lines(b), [])
                self.assertEqual([l for l in a.splitlines() if l.startswith(("DATA", "MODEL"))], [l for l in b.splitlines() if l.startswith(("DATA", "MODEL"))])

    def test_per_shelf_training_loss(self):
        log = reference()
        st = status("runs/ref")
        self.assertEqual(list(st["train_per_file"]), SHELVES)
        self.assertEqual(st["weights"], {"easy": 3.0, "markov": 2.0, "zipf": 2.0, "hard": 1.0})
        self.assertEqual(sum(st["train_rows"].values()), 10 * 16 * 2)
        self.assertLess(st["train_per_file"]["easy"], st["train_per_file"]["hard"] - 1.0)
        self.assertLess(st["eval_per_file"]["easy"], st["eval_per_file"]["hard"] - 1.0)
        self.assertLess(abs(st["train_per_file"]["hard"] - 5.54), 0.25)
        lines = train_lines(log)
        self.assertEqual(sorted(lines), [10, 20, 30])
        self.assertLess(abs(lines[30]["easy"] - st["train_per_file"]["easy"]), 0.001)
        whole = sum(st["train_per_file"][k] * st["train_rows"][k] for k in SHELVES) / sum(st["train_rows"].values())
        logged = statistics.mean(float(s[2]) for s in steps_of(log) if s[0] > 20)
        self.assertLess(abs(whole - logged), 0.0005)
        self.assertEqual(ckpt("runs/ref")["weights"], st["weights"])

    def test_draws_match_the_old_sampler(self):
        old, new = module(old_train(), "train_old"), module(NEW_TRAIN, "train_new")
        parts = [(os.path.join(TMP, s.split(":")[0]), "uint16", float(s.split(":")[1])) for s in MIX]
        a, b = old.Mix(parts, 64), new.Mix(parts, 64)
        ga, gb = torch.Generator().manual_seed(5), torch.Generator().manual_seed(5)
        for i in range(40):
            if i == 20:
                b.set([3, 2, 2, 1])
            xa, ya = a.random(16, ga)
            xb, yb = b.random(16, gb)
            self.assertTrue(torch.equal(xa, xb) and torch.equal(ya, yb))
            self.assertEqual(sum(b.last), 16)


class Resume(unittest.TestCase):
    def test_old_checkpoint_under_new_trainer(self):
        train(old_train(), "runs/res-base", 20)
        stretch("runs/res-base", 40)
        a = train(old_train(), clone("runs/res-base", "runs/res-old"), fresh=False)
        b = train(NEW_TRAIN, clone("runs/res-base", "runs/res-new"), fresh=False)
        self.assertIn("RESUME from", b)
        self.assertEqual([s[0] for s in steps_of(a)], list(range(21, 41)))
        self.assertEqual(steps_of(a), steps_of(b))
        self.assertEqual(differs("runs/res-old", "runs/res-new"), [])
        self.assertEqual(mix_lines(b), [])
        self.assertEqual(status("runs/res-new")["weights"], {"easy": 3.0, "markov": 2.0, "zipf": 2.0, "hard": 1.0})

    def test_new_checkpoint_carries_the_weights(self):
        put("runs/car-base", '{"hard": 0, "markov": 4}')
        first = train(NEW_TRAIN, "runs/car-base", 20)
        self.assertEqual(mix_lines(first), ["MIX step=10 markov 2->4 hard 1->0"])
        self.assertEqual(ckpt("runs/car-base")["weights"], {"easy": 3.0, "markov": 4.0, "zipf": 2.0, "hard": 0.0})
        stretch("runs/car-base", 40)
        for tag in ("a", "b"):
            clone("runs/car-base", f"runs/car-{tag}")
            os.remove(os.path.join(TMP, f"runs/car-{tag}", "weights.json"))
        a = train(NEW_TRAIN, "runs/car-a", fresh=False)
        b = train(NEW_TRAIN, "runs/car-b", fresh=False)
        self.assertEqual(mix_lines(a), ["MIX step=20 from checkpoint: markov 2->4 hard 1->0"])
        self.assertEqual(status("runs/car-a")["weights"], {"easy": 3.0, "markov": 4.0, "zipf": 2.0, "hard": 0.0})
        for step, seen in train_lines(a).items():
            self.assertNotIn("hard", seen, step)
        self.assertNotIn("hard", status("runs/car-a")["train_rows"])
        self.assertEqual(steps_of(a), steps_of(b))
        self.assertEqual(differs("runs/car-a", "runs/car-b"), [])

    def test_file_wins_over_checkpoint(self):
        put("runs/win-base", '{"hard": 0}')
        train(NEW_TRAIN, "runs/win-base", 20)
        stretch("runs/win-base", 40)
        put("runs/win-base", '{"hard": 5}')
        log = train(NEW_TRAIN, "runs/win-base", fresh=False)
        self.assertEqual(mix_lines(log), ["MIX step=20 from checkpoint: hard 1->0", "MIX step=30 hard 0->5"])
        seen = train_lines(log)
        self.assertNotIn("hard", seen[30])
        self.assertIn("hard", seen[40])
        self.assertEqual(status("runs/win-base")["weights"]["hard"], 5.0)

    def test_old_trainer_still_reads_a_new_checkpoint(self):
        train(NEW_TRAIN, "runs/back", 20)
        stretch("runs/back", 30)
        log = train(old_train(), "runs/back", fresh=False)
        self.assertIn("DONE step=30", log)


class Weights(unittest.TestCase):
    def test_file_waits_for_the_eval(self):
        put("runs/wait", '{"easy": 0}')
        log = train(NEW_TRAIN, "runs/wait", 30)
        self.assertEqual(mix_lines(log), ["MIX step=10 easy 3->0"])
        self.assertEqual(steps_of(log)[:10], steps_of(reference())[:10])
        self.assertNotEqual([s[2] for s in steps_of(log)[10:20]], [s[2] for s in steps_of(reference())[10:20]])
        seen = train_lines(log)
        self.assertEqual(list(seen[10]), SHELVES)
        for step in (20, 30):
            self.assertEqual(list(seen[step]), ["markov", "zipf", "hard"])
        st = status("runs/wait")
        self.assertEqual(st["weights"], {"easy": 0.0, "markov": 2.0, "zipf": 2.0, "hard": 1.0})
        self.assertNotIn("easy", st["train_rows"])
        self.assertEqual(sum(st["train_rows"].values()), 320)
        self.assertIn("DONE step=30", log)

    def test_dropped_mid_run_then_removed(self):
        out = "runs/drop"
        shape = SMALL[:SMALL.index("--eval-every") + 1] + ["20"] + SMALL[SMALL.index("--eval-every") + 2:]
        p = subprocess.Popen(command(NEW_TRAIN, out, 160, shape), cwd=TMP, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        self.addCleanup(p.stdout.close)
        lines, dropped_at, removed_at, last = [], None, None, 0
        for line in p.stdout:
            lines.append(line.rstrip("\n"))
            m = STEP.match(line)
            if m:
                last = int(m.group(1))
            if dropped_at is None and last >= 25:
                put(out, '{"zipf": 0}')
                dropped_at = last
            if removed_at is None and line.startswith("MIX "):
                os.remove(os.path.join(TMP, out, "weights.json"))
                removed_at = last
        self.assertEqual(p.wait(), 0)
        log = "\n".join(lines)
        mixes = mix_lines(log)
        self.assertEqual(len(mixes), 1, mixes)
        at = int(re.match(r"MIX step=(\d+) zipf 2->0$", mixes[0]).group(1))
        self.assertEqual(at % 20, 0)
        self.assertGreater(at, dropped_at)
        self.assertLess(at, 160)
        seen = train_lines(log)
        for step, shelves in seen.items():
            if step <= at:
                self.assertIn("zipf", shelves, step)
            else:
                self.assertNotIn("zipf", shelves, step)
        self.assertGreaterEqual(len([s for s in seen if s > at]), 1)
        self.assertEqual(status(out)["weights"]["zipf"], 0.0)
        self.assertEqual(ckpt(out)["weights"]["zipf"], 0.0)

    def test_zero_is_never_drawn_and_the_rest_keep_their_shares(self):
        new = module(NEW_TRAIN, "train_new")
        parts = [(os.path.join(TMP, s.split(":")[0]), "uint16", float(s.split(":")[1])) for s in MIX]
        mix = new.Mix(parts, 64)
        gen = torch.Generator().manual_seed(3)
        before = [0, 0, 0, 0]
        for _ in range(500):
            mix.random(32, gen)
            before = [a + b for a, b in zip(before, mix.last)]
        mix.set([3, 0, 2, 1])
        after = [0, 0, 0, 0]
        for _ in range(500):
            x, _ = mix.random(32, gen)
            self.assertEqual(x.shape[0], 32)
            after = [a + b for a, b in zip(after, mix.last)]
        self.assertEqual(after[1], 0)
        self.assertEqual(sum(after), 16000)
        for got, want in zip(before, (3 / 8, 2 / 8, 2 / 8, 1 / 8)):
            self.assertLess(abs(got / 16000 - want), 0.015)
        for got, want in zip(after, (3 / 6, 0, 2 / 6, 1 / 6)):
            self.assertLess(abs(got / 16000 - want), 0.015)
        self.assertLess(abs(after[0] / after[3] - 3), 0.25)
        self.assertEqual(mix.weights(), {"easy": 3.0, "markov": 0.0, "zipf": 2.0, "hard": 1.0})

    def test_same_weights_say_nothing(self):
        put("runs/same", '{"easy": 3, "hard": 1.0}')
        log = train(NEW_TRAIN, "runs/same", 30)
        reference()
        self.assertEqual(mix_lines(log), [])
        self.assertEqual(differs("runs/same", "runs/ref"), [])


BAD = {
    "broken-json": '{"easy": 0',
    "empty": "",
    "a-list": '["easy", 0]',
    "unknown-shelf": '{"fantasy": 0}',
    "negative": '{"easy": -1}',
    "a-string": '{"easy": "0"}',
    "a-boolean": '{"easy": true}',
    "null": '{"easy": null}',
    "not-finite": '{"easy": NaN}',
    "infinite": '{"easy": Infinity}',
    "all-zero": '{"easy": 0, "markov": 0, "zipf": 0, "hard": 0}',
    "one-good-one-bad": '{"easy": 0, "hard": -2}',
}


class BadFiles(unittest.TestCase):
    def test_each_is_refused(self):
        new = module(NEW_TRAIN, "train_new")
        current = [3.0, 2.0, 2.0, 1.0]
        folder = os.path.join(TMP, "bad")
        os.makedirs(folder, exist_ok=True)
        for tag, text in BAD.items():
            with self.subTest(tag):
                path = os.path.join(folder, tag + ".json")
                with open(path, "w") as f:
                    f.write(text)
                raw, weights, err = new.read_weights(path, SHELVES, current)
                self.assertIsNone(weights)
                self.assertTrue(err)
                self.assertNotIn("\n", err)
                self.assertEqual(current, [3.0, 2.0, 2.0, 1.0])
        with open(os.path.join(folder, "bytes.json"), "wb") as f:
            f.write(b'{"easy": \xff\xfe}')
        self.assertTrue(new.read_weights(os.path.join(folder, "bytes.json"), SHELVES, current)[2])
        os.makedirs(os.path.join(folder, "dir.json"), exist_ok=True)
        self.assertTrue(new.read_weights(os.path.join(folder, "dir.json"), SHELVES, current)[2])
        self.assertEqual(new.read_weights(os.path.join(folder, "absent.json"), SHELVES, current), (None, None, None))

    def test_good_ones_are_read(self):
        new = module(NEW_TRAIN, "train_new")
        folder = os.path.join(TMP, "good")
        os.makedirs(folder, exist_ok=True)
        for text, want in (("{}", [3.0, 2.0, 2.0, 1.0]), ('{"hard": 0}', [3.0, 2.0, 2.0, 0.0]), ('{"easy": 0, "markov": 0, "zipf": 0}', [0.0, 0.0, 0.0, 1.0]), ('{"zipf": 2.5, "easy": 7}', [7.0, 2.0, 2.5, 1.0])):
            path = os.path.join(folder, "w.json")
            with open(path, "w") as f:
                f.write(text)
            self.assertEqual(new.read_weights(path, SHELVES, [3.0, 2.0, 2.0, 1.0])[1:], (want, None))

    def test_run_goes_on_untouched(self):
        reference()
        cases = dict(BAD)
        cases["a-directory"] = None
        for tag, text in cases.items():
            with self.subTest(tag):
                out = f"runs/bad-{tag}"
                if text is None:
                    os.makedirs(os.path.join(TMP, out, "weights.json"))
                else:
                    put(out, text)
                log = train(NEW_TRAIN, out, 30)
                mixes = mix_lines(log)
                self.assertEqual(len(mixes), 1, mixes)
                self.assertTrue(mixes[0].startswith("MIX step=10 weights.json ignored, mix unchanged: "), mixes[0])
                self.assertIn("DONE step=30", log)
                self.assertEqual(status(out)["weights"], {"easy": 3.0, "markov": 2.0, "zipf": 2.0, "hard": 1.0})
                self.assertEqual(differs(out, "runs/ref"), [])

    def test_a_bad_file_does_not_undo_a_good_one(self):
        out = "runs/bad-after-good"
        shape = SMALL[:SMALL.index("--eval-every") + 1] + ["20"] + SMALL[SMALL.index("--eval-every") + 2:]
        put(out, '{"hard": 0}')
        p = subprocess.Popen(command(NEW_TRAIN, out, 120, shape), cwd=TMP, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        self.addCleanup(p.stdout.close)
        lines, swapped = [], False
        for line in p.stdout:
            lines.append(line.rstrip("\n"))
            if not swapped and line.startswith("MIX "):
                put(out, '{"hard": 3, "nosuch": 1}')
                swapped = True
        self.assertEqual(p.wait(), 0)
        mixes = mix_lines("\n".join(lines))
        self.assertEqual(len(mixes), 2, mixes)
        self.assertEqual(mixes[0], "MIX step=20 hard 1->0")
        self.assertIn("ignored, mix unchanged: unknown shelf 'nosuch'", mixes[1])
        self.assertEqual(status(out)["weights"]["hard"], 0.0)
        self.assertNotIn("hard", status(out)["train_rows"])


def ledger(name, evals, trains=None, weights=None):
    folder = os.path.join(TMP, "night", name)
    os.makedirs(folder, exist_ok=True)
    n = len(next(iter(evals.values())))
    with open(os.path.join(folder, "ledger.jsonl"), "w") as f:
        for i in range(n):
            row = {"step": 1000 * (i + 1), "eval_step": 1000 * (i + 1), "eval_per_file": {k: v[i] for k, v in evals.items()}}
            if trains is not None:
                row["train_per_file"] = {k: v[i] for k, v in trains.items()}
            if weights is not None:
                row["weights"] = weights
            for _ in range(2):
                f.write(json.dumps(row) + "\n")
    return name


def turn(script, name, *flags):
    p = subprocess.run([sys.executable, script, name, *flags], cwd=TMP, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


SPIKE = [3.00, 3.00, 3.00, 3.00, 3.01, 3.01, 3.01, 3.01, 3.04]
CLIMB = [3.00, 3.00, 3.00, 3.02, 3.02, 3.02, 3.04, 3.05, 3.06, 3.07]
CALM = [2.50, 2.49, 2.48, 2.47, 2.46, 2.45, 2.44, 2.43, 2.42, 2.41]
ADDED = {"turned_evals", "confirmed", "train", "gap", "gap_prev3", "gap_last3", "gap_band", "gap_trend", "reading"}


class Turn(unittest.TestCase):
    def both(self, name):
        old, new = turn(old_turn(), name), turn(NEW_TURN, name)
        oj, nj = json.loads(turn(old_turn(), name, "--json")[1]), json.loads(turn(NEW_TURN, name, "--json")[1])
        self.assertEqual(set(nj) - set(oj), {"turned", "confirmed"})
        self.assertEqual({k: nj[k] for k in oj if k != "shelves"}, {k: oj[k] for k in oj if k != "shelves"})
        self.assertEqual(list(oj["shelves"]), list(nj["shelves"]))
        for k, v in oj["shelves"].items():
            self.assertEqual(v, {a: b for a, b in nj["shelves"][k].items() if a not in ADDED}, k)
            self.assertEqual(list(v), list(nj["shelves"][k])[:len(v)], k)
        return old, new, nj

    def test_spike_that_recovers_is_not_confirmed(self):
        old, new, j = self.both(ledger("spike", {"a": SPIKE, "b": CALM[:9]}))
        self.assertEqual(old[0], 2)
        self.assertEqual(new[0], 2)
        self.assertEqual(j["shelves"]["a"]["verdict"], "turned")
        self.assertEqual((j["shelves"]["a"]["turned_evals"], j["shelves"]["a"]["confirmed"]), (1, False))
        self.assertEqual((j["turned"], j["confirmed"]), (["a"], []))
        self.assertIn("TURNED on this eval only", new[1])
        self.assertEqual(new[1].replace(" on this eval only", ""), old[1])
        self.assertIn("nothing to write", turn(NEW_TURN, "spike", "--weights")[1])
        old, new, j = self.both(ledger("spike-after", {"a": SPIKE + [2.99], "b": CALM}))
        self.assertEqual((old[0], new[0]), (0, 0))
        self.assertEqual(old[1], new[1])
        self.assertNotEqual(j["shelves"]["a"]["verdict"], "turned")
        self.assertEqual((j["turned"], j["confirmed"]), ([], []))

    def test_two_evals_running_is_confirmed(self):
        old, new, j = self.both(ledger("climb", {"a": CLIMB, "b": CALM}))
        self.assertEqual(old[0], 2)
        self.assertEqual(new[0], 3)
        self.assertEqual(j["shelves"]["a"]["verdict"], "turned")
        self.assertTrue(j["shelves"]["a"]["confirmed"])
        self.assertGreaterEqual(j["shelves"]["a"]["turned_evals"], 2)
        self.assertEqual((j["turned"], j["confirmed"]), (["a"], ["a"]))
        self.assertIn("TURNED confirmed, 2 evals running", new[1])
        self.assertEqual(j["shelves"]["b"]["verdict"], "learning")
        self.assertNotIn("gap", j["shelves"]["a"])
        self.assertEqual(turn(NEW_TURN, "climb", "--json")[0], 0)

    def test_gap_tells_memorising_from_drift(self):
        falling = [v - 0.30 - 0.02 * i for i, v in enumerate(CLIMB)]
        along = [v - 0.30 for v in CLIMB]
        calm = [v - 0.10 for v in CALM]
        code, text, _ = turn(NEW_TURN, ledger("wide", {"a": CLIMB, "b": CALM}, {"a": falling, "b": calm}))
        j = json.loads(turn(NEW_TURN, "wide", "--json")[1])
        self.assertEqual(code, 3)
        self.assertEqual((j["shelves"]["a"]["gap_trend"], j["shelves"]["a"]["reading"]), ("widening", "memorising"))
        self.assertAlmostEqual(j["shelves"]["a"]["gap"], 0.48, places=3)
        self.assertEqual(j["shelves"]["b"]["gap_trend"], "flat")
        self.assertNotIn("reading", j["shelves"]["b"])
        self.assertRegex(text, r"a +3\.070 .* TURNED confirmed, 2 evals running  gap \+0\.480 \(\+0\.\d+ -> \+0\.\d+ widening\)  memorising")
        self.assertRegex(text, r"b +2\.410 .* learning  gap \+0\.100 \(\+0\.100 -> \+0\.100 flat\)")
        code, text, _ = turn(NEW_TURN, ledger("level", {"a": CLIMB, "b": CALM}, {"a": along, "b": calm}))
        j = json.loads(turn(NEW_TURN, "level", "--json")[1])
        self.assertEqual(code, 3)
        self.assertEqual((j["shelves"]["a"]["gap_trend"], j["shelves"]["a"]["reading"]), ("flat", "drift"))
        self.assertIn("drift or noise", text)
        self.assertNotIn("memorising:", text)
        self.both("wide")
        self.both("level")

    def test_gap_waits_for_enough_evals(self):
        trains = {"a": [None] * 7 + [2.7, 2.7, 2.7], "b": [None] * 10}
        folder = os.path.join(TMP, "night", ledger("young", {"a": CLIMB, "b": CALM}, trains))
        rows = [json.loads(l) for l in read(os.path.join(folder, "ledger.jsonl")).splitlines()]
        with open(os.path.join(folder, "ledger.jsonl"), "w") as f:
            for r in rows:
                r["train_per_file"] = {k: v for k, v in r["train_per_file"].items() if v is not None}
                f.write(json.dumps(r) + "\n")
        j = json.loads(turn(NEW_TURN, "young", "--json")[1])
        self.assertAlmostEqual(j["shelves"]["a"]["gap"], 0.37, places=3)
        self.assertNotIn("gap_trend", j["shelves"]["a"])
        self.assertNotIn("reading", j["shelves"]["a"])
        self.assertNotIn("gap", j["shelves"]["b"])
        self.assertEqual(turn(NEW_TURN, "young")[0], 3)

    def test_weights_prints_and_writes_nothing(self):
        ledger("zero", {"a": CLIMB, "b": CALM, "c": CALM}, {"a": [v - 0.3 - 0.02 * i for i, v in enumerate(CLIMB)], "b": CALM, "c": CALM}, {"a": 5.0, "b": 2.0, "c": 0.0, "d": 1.0})
        before = sorted(os.listdir(os.path.join(TMP, "night", "zero")))
        code, text, _ = turn(NEW_TURN, "zero", "--weights")
        self.assertEqual(code, 0)
        lines = text.splitlines()
        self.assertEqual(json.loads(lines[0]), {"a": 0, "c": 0})
        self.assertEqual(lines[1], "printf '%s\\n' '{\"a\": 0, \"c\": 0}' | ssh -i \"$KEY\" BekmemetevVO@ds-dev2.x340.org 'cat > /opt/llama/magdra/runs/zero/weights.json.new && mv /opt/llama/magdra/runs/zero/weights.json.new /opt/llama/magdra/runs/zero/weights.json'")
        self.assertTrue(lines[2].startswith("# a: turned confirmed"))
        self.assertIn("memorising", lines[2])
        self.assertEqual(sorted(os.listdir(os.path.join(TMP, "night", "zero"))), before)
        new = module(NEW_TRAIN, "train_new")
        path = os.path.join(TMP, "printed.json")
        with open(path, "w") as f:
            f.write(lines[0])
        self.assertEqual(new.read_weights(path, ["a", "b", "c", "d"], [5.0, 2.0, 0.0, 1.0])[1:], ([0.0, 2.0, 0.0, 1.0], None))
        sent = subprocess.run(["bash", "-c", lines[1].split(" | ")[0]], capture_output=True, text=True).stdout
        self.assertEqual(json.loads(sent), {"a": 0, "c": 0})

    def test_ledger_flag(self):
        ledger("elsewhere", {"a": CLIMB, "b": CALM})
        code, text, _ = turn(NEW_TURN, "named", "--ledger", os.path.join(TMP, "night", "elsewhere", "ledger.jsonl"))
        self.assertEqual(code, 3)
        self.assertTrue(text.startswith("named: 10 evals"))

    @unittest.skipUnless(os.path.exists(os.path.join(DAY3, "ledger.jsonl")), "no day3 ledger on this machine")
    def test_day3_reads_as_before(self):
        rows = [l for l in read(os.path.join(DAY3, "ledger.jsonl")).splitlines(keepends=True) if l.strip()]
        os.makedirs(os.path.join(TMP, "night", "day3"), exist_ok=True)
        with open(os.path.join(TMP, "night", "day3", "ledger.jsonl"), "w", encoding="utf-8") as f:
            f.writelines(rows)
        old, new, j = self.both("day3")
        if not j["turned"]:
            self.assertEqual(old, new)
        self.assertEqual(old[1].splitlines()[0], new[1].splitlines()[0])
        if not j["turned"]:
            self.assertEqual(turn(NEW_TURN, "day3", "--json")[1].strip(), turn(old_turn(), "day3", "--json")[1].strip()[:-1] + ', "turned": [], "confirmed": []}')
        os.makedirs(os.path.join(TMP, "night", "day3-25000"), exist_ok=True)
        with open(os.path.join(TMP, "night", "day3-25000", "ledger.jsonl"), "w", encoding="utf-8") as f:
            f.writelines(l for l in rows if (json.loads(l).get("eval_step") or 0) <= 25000)
        old, new, j = self.both("day3-25000")
        self.assertEqual((old[0], new[0]), (2, 2))
        self.assertEqual((j["turned"], j["confirmed"]), (["fantasy"], []))
        self.assertEqual(new[1].replace(" on this eval only", ""), old[1])

    @unittest.skipUnless(os.path.exists(os.path.join(DAY3, "ledger.jsonl")), "no day3 folder on this machine")
    def test_page_still_reads_the_json(self):
        root = os.path.join(TMP, "pagecheck")
        os.makedirs(os.path.join(root, "night", "day3"), exist_ok=True)
        shutil.copy(PAGE, os.path.join(root, "night", "page.py"))
        shutil.copy(NEW_TURN, os.path.join(root, "night", "turn.py"))
        for name in os.listdir(DAY3):
            src = os.path.join(DAY3, name)
            if os.path.isfile(src) and os.path.getsize(src) < 50_000_000 and not name.endswith((".png", ".html")):
                shutil.copy(src, os.path.join(root, "night", "day3", name))
        p = subprocess.run([sys.executable, "night/page.py", "day3"], cwd=root, capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr[-2000:])
        self.assertNotIn("turn:", p.stderr)
        self.assertIn("held-out loss, shelf by shelf", p.stdout)
        for shelf in ("fantasy", "scifi", "library"):
            self.assertRegex(p.stdout, rf"<td>{shelf}</td>.*?(learning|flat|rising|turned)")


def wait_for(test, seconds=90):
    end = time.time() + seconds
    while time.time() < end:
        got = test()
        if got:
            return got
        time.sleep(0.2)
    raise AssertionError("timed out waiting")


class Run4(unittest.TestCase):
    def home(self, name):
        root = os.path.join(TMP, name)
        os.makedirs(os.path.join(root, "night", "toy"), exist_ok=True)
        os.makedirs(os.path.join(root, "runs"), exist_ok=True)
        shutil.copy(NEW_TRAIN, os.path.join(root, "train.py"))
        if not os.path.exists(os.path.join(root, "bins")):
            os.symlink(os.path.join(TMP, "bins"), os.path.join(root, "bins"))
        with open(os.path.join(root, "night", "toy", "mix.txt"), "w") as f:
            f.write("bins/easy.bin:3\nbins/markov.bin:2   # the chain\n\nbins/zipf.bin:2\nbins/hard.bin:1.5\n")
        if "init" not in CACHE:
            train(NEW_TRAIN, "runs/init", 5)
            CACHE["init"] = os.path.join(TMP, "runs", "init", "ckpt.pt")
        shutil.copy(CACHE["init"], os.path.join(root, "init.pt"))
        env = dict(os.environ, SCHOOL=root, PY=sys.executable, NTFY="", PROMPTS="", COMPILE="0", BATCH="16", ACCUM="1", LR="1e-3", WARMUP="5",
                   LOG_EVERY="5", EVAL_EVERY="20", CKPT_MINUTES="0.02", STEPS="1000000", PAUSE="1", TRIES="5")
        for k in ("MIX", "MIXFILE", "INIT", "HOURS", "DRY"):
            env.pop(k, None)
        return root, env

    def test_syntax(self):
        self.assertEqual(subprocess.run(["bash", "-n", RUN4]).returncode, 0)

    def test_dry_run_builds_the_commands(self):
        root, env = self.home("r4-dry")
        p = subprocess.run(["bash", RUN4, "toy", "init.pt"], env=dict(env, DRY="1"), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        start, resume = p.stdout.splitlines()
        data = "train.py --data bins/easy.bin:3 bins/markov.bin:2 bins/zipf.bin:2 bins/hard.bin:1.5 --out runs/toy"
        self.assertEqual(start, f"start:  {sys.executable} {data} --init init.pt --batch 16 --accum 1 --lr 1e-3 --warmup 5 --steps 1000000 --log-every 5 --eval-every 20 --ckpt-minutes 0.02 >> runs/toy.log")
        self.assertEqual(resume, f"resume: {sys.executable} {data} >> runs/toy.log")
        self.assertFalse(os.path.exists(os.path.join(root, "runs", "toy")))
        bare = {k: v for k, v in env.items() if k not in ("BATCH", "ACCUM", "LR", "WARMUP", "LOG_EVERY", "EVAL_EVERY", "CKPT_MINUTES", "STEPS", "PROMPTS", "COMPILE")}
        p = subprocess.run(["bash", RUN4, "toy", "init.pt", "50"], env=dict(bare, DRY="1"), capture_output=True, text=True)
        self.assertIn("--init init.pt --batch 6 --accum 4 --lr 8e-5 --warmup 300 --hours 50 --log-every 50 --eval-every 1000 --ckpt-minutes 20 --prompts prompts.txt --compile >> runs/toy.log", p.stdout.splitlines()[0])
        p = subprocess.run(["bash", RUN4, "toy", "init.pt", "50"], env=dict(bare, DRY="1", MIX="bins/hard.bin:9"), capture_output=True, text=True)
        self.assertIn("--data bins/hard.bin:9 --out runs/toy", p.stdout.splitlines()[0])

    def test_refuses_a_bad_start(self):
        root, env = self.home("r4-bad")
        cases = {
            "no run name": ([], {}),
            "no init": (["toy"], {}),
            "missing init": (["toy", "nosuch.pt"], {}),
            "no budget": (["toy", "init.pt"], {"STEPS": ""}),
            "bad entry": (["toy", "init.pt"], {"MIX": "bins/easy.bin"}),
            "missing bin": (["toy", "init.pt"], {"MIX": "bins/nosuch.bin:3"}),
            "no mix file": (["other", "init.pt"], {}),
        }
        for tag, (args, more) in cases.items():
            with self.subTest(tag):
                p = subprocess.run(["bash", RUN4, *args], env=dict(env, **more), capture_output=True, text=True)
                self.assertEqual(p.returncode, 1)
                self.assertTrue(p.stderr.startswith("run4: "), p.stderr)
        self.assertEqual(os.listdir(os.path.join(root, "runs")), [])

    def test_restarts_a_killed_trainer_and_stops_on_term(self):
        root, env = self.home("r4-live")
        log_path, guard_path, status_path = (os.path.join(root, "runs", n) for n in ("toy.log", "toy.guard.log", "toy/status.json"))
        wrapper = subprocess.Popen(["bash", RUN4, "toy", "init.pt"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        def text(path):
            return read(path) if os.path.exists(path) else ""

        def pid():
            try:
                return json.loads(read(status_path))["pid"]
            except (OSError, ValueError, KeyError):
                return None

        try:
            wait_for(lambda: "CKPT step=" in text(log_path))
            first = pid()
            self.assertIn("INIT weights from", text(log_path))
            os.kill(first, signal.SIGKILL)
            wait_for(lambda: "restart 1" in text(guard_path))
            wait_for(lambda: "RESUME from" in text(log_path))
            second = wait_for(lambda: pid() not in (None, first) and pid())
            self.assertIsNone(wrapper.poll())
            os.kill(second, signal.SIGTERM)
            self.assertEqual(wrapper.wait(timeout=90), 0)
        finally:
            if wrapper.poll() is None:
                for p in (pid(), wrapper.pid):
                    if p:
                        try:
                            os.kill(p, signal.SIGKILL)
                        except OSError:
                            pass
        log, guard = text(log_path), text(guard_path)
        self.assertIn("STOP signal: checkpointing and exiting", log)
        self.assertRegex(log.splitlines()[-1], r"^STOPPED step=\d+ ")
        self.assertEqual(guard.count("restart"), 1)
        self.assertRegex(guard.splitlines()[-1], r"wrapper exit: STOPPED step=\d+ tokens=[\d,]+ eval_loss=[\d.]+$")
        self.assertEqual(log.count("INIT weights from"), 1)
        self.assertEqual(log.count("RESUME from"), 1)
        self.assertEqual(json.loads(read(status_path))["phase"], "stopped")
        self.assertEqual(json.loads(read(status_path))["weights"]["hard"], 1.5)


@unittest.skipUnless(os.environ.get("BENCH"), "set BENCH=1 to time old against new")
class Bench(unittest.TestCase):
    def test_overhead(self):
        shape = ["--layers", "2", "--heads", "2", "--width", "32", "--ctx", "64", "--batch", "16", "--accum", "2", "--lr", "2e-3", "--warmup", "5",
                 "--log-every", "100", "--eval-every", "100000", "--eval-iters", "4", "--ckpt-minutes", "1000", "--seed", "7"]
        times = {"old": [], "new": []}
        for i in range(int(os.environ.get("BENCH"))):
            for tag, trainer in (("old", old_train()), ("new", NEW_TRAIN)) if i % 2 == 0 else (("new", NEW_TRAIN), ("old", old_train())):
                train(trainer, f"runs/bench-{tag}-{i}", 300, shape)
                times[tag].append(status(f"runs/bench-{tag}-{i}")["elapsed_s"] / 300 * 1000)
        for tag, ts in times.items():
            print(f"\n{tag}: median {statistics.median(ts):.2f} ms/step, min {min(ts):.2f}, max {max(ts):.2f}, runs {len(ts)}", file=sys.stderr)
        print(f"new/old by median: {statistics.median(times['new']) / statistics.median(times['old']):.4f}, by min: {min(times['new']) / min(times['old']):.4f}", file=sys.stderr)


if __name__ == "__main__":
    unittest.main()
