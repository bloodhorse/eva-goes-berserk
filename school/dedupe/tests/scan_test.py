import json
import os
import subprocess
import sys
import time

import scan
import store
from helpers import HERE, Bench, Case, story, text_of, tree_digest


class BadFiles(Case):
    overrides = {"scan": {"max_file_bytes": 200000}}

    def test_one_bad_file_never_stops_the_run(self):
        self.bench.put("mag", "good.txt", story("a"))
        self.bench.put("mag", "latin1.txt", "Café au lait, naïve façade.\n".encode("latin-1") * 50)
        self.bench.put("mag", "empty.txt", b"")
        self.bench.put("mag", "blank.txt", "   \n\n\t\n")
        self.bench.put("mag", "binary.txt", b"\x00\x01\x02 words \x00" * 100)
        self.bench.put("mag", "huge.txt", text_of(story("big", 4000)))
        self.bench.put("mag", "symbols.txt", "* * *\n\n---\n")
        counts = self.bench.scan()
        self.assertEqual(counts["indexed"], 1)
        self.assertEqual(self.bench.skipped(), {
            ("mag", "latin1.txt"): "not utf-8", ("mag", "empty.txt"): "empty", ("mag", "blank.txt"): "empty",
            ("mag", "binary.txt"): "binary", ("mag", "huge.txt"): "too large", ("mag", "symbols.txt"): "no words"})
        records = self.bench.plan()
        self.assertEqual(set(records), {("mag", "good.txt")})
        self.assertIn("not utf-8: 1", self.bench.report())

    def test_known_bad_files_are_not_read_again_until_they_change(self):
        bad = self.bench.put("mag", "latin1.txt", "Café\n".encode("latin-1"))
        self.bench.scan()
        reads = []
        original = scan.read_settled
        scan.read_settled = lambda full, before: (reads.append(full), original(full, before))[1]
        try:
            self.bench.scan()
            self.assertEqual(reads, [])
            time.sleep(0.01)
            bad.write_text(text_of(story("fixed")), encoding="utf-8")
            self.bench.scan()
            self.assertEqual(len(reads), 1)
        finally:
            scan.read_settled = original
        self.assertEqual(self.bench.skipped(), {})
        self.assertEqual(set(self.bench.plan()), {("mag", "latin1.txt")})


class LiveRoots(Case):
    def test_recently_modified_files_wait_for_the_next_run(self):
        self.bench.overrides["scan"]["settle_seconds"] = 90
        self.bench.write_config()
        fresh = self.bench.put("mag", "fresh.txt", story("a"))
        old = self.bench.put("mag", "old.txt", story("b"))
        past = time.time() - 600
        os.utime(old, (past, past))
        self.assertEqual(self.bench.scan()["indexed"], 1)
        self.assertEqual(self.bench.skipped(), {("mag", "fresh.txt"): "settling"})
        os.utime(fresh, (past, past))
        self.assertEqual(self.bench.scan()["indexed"], 1)
        self.assertEqual(self.bench.skipped(), {})

    def test_file_vanishing_between_listing_and_reading(self):
        self.bench.put("mag", "stays.txt", story("a"))
        doomed = self.bench.put("mag", "doomed.txt", story("b"))
        original = scan.stat_of

        def vanish(path):
            if str(path).endswith("doomed.txt") and doomed.exists():
                found = original(path)
                doomed.unlink()
                return found
            return original(path)

        scan.stat_of = vanish
        try:
            counts = self.bench.scan()
        finally:
            scan.stat_of = original
        self.assertEqual(counts["indexed"], 1)
        self.assertEqual(self.bench.skipped(), {("mag", "doomed.txt"): "vanished"})
        self.bench.scan()
        self.assertEqual(self.bench.skipped(), {})

    def test_file_rewritten_while_being_read_is_left_alone(self):
        target = self.bench.put("mag", "moving.txt", story("a"))
        original = scan.read_settled

        def interrupt(full, before):
            with open(full, "a") as f:
                f.write("more words arriving right now\n")
            return original(full, before)

        scan.read_settled = interrupt
        try:
            self.assertEqual(self.bench.scan()["indexed"], 0)
        finally:
            scan.read_settled = original
        self.assertEqual(self.bench.skipped(), {("mag", "moving.txt"): "changed while reading"})
        self.assertEqual(self.bench.scan()["indexed"], 1)
        self.assertTrue(target.exists())

    def test_deleted_file_leaves_the_plan_and_missing_root_forgets_nothing(self):
        self.bench.put("mag", "a.txt", story("a"))
        gone = self.bench.put("mag", "b.txt", story("b"))
        self.bench.put("anth", "c.txt", story("c"))
        self.bench.scan()
        gone.unlink()
        os.rename(self.bench.dir / "roots" / "anth", self.bench.dir / "roots" / "anth-away")
        counts = self.bench.scan()
        self.assertEqual(counts["vanished"], 1)
        self.assertEqual(set(self.bench.plan()), {("mag", "a.txt"), ("anth", "c.txt")})

    def test_renamed_file_is_known_by_its_content(self):
        first = self.bench.put("mag", "before.txt", story("a"))
        self.bench.scan()
        os.rename(first, first.with_name("after.txt"))
        counts = self.bench.scan()
        self.assertEqual((counts["indexed"], counts["relinked"], counts["vanished"]), (0, 1, 1))
        self.assertEqual(set(self.bench.plan()), {("mag", "after.txt")})

    def test_sources_are_never_touched(self):
        shared = story("s")
        self.bench.put("mag", "s.txt", shared + ["Reprinted by permission of the author."])
        self.bench.put("mag", "twin.txt", shared)
        self.bench.put("anth", "book.txt", story("a") + shared + story("b"))
        self.bench.put("shelf", "bad.txt", b"\xff\xfe\x00")
        before = tree_digest(self.bench.dir / "roots")
        self.bench.go()
        self.bench.report()
        self.bench.lookup(" ".join(shared[3].split()[:20]))
        self.assertEqual(before, tree_digest(self.bench.dir / "roots"))


class Crashes(Case):
    overrides = {"scan": {"batch_words": 1500}}

    def fill(self, bench):
        shared = story("shared")
        for i in range(12):
            bench.put("mag", f"m{i:02d}.txt", story(f"m{i}"))
        bench.put("mag", "shared.txt", shared)
        bench.put("anth", "book.txt", story("x") + shared + story("y"))

    def run_cli(self, bench, command, crash=None):
        env = dict(os.environ)
        env.pop("DEDUPE_CRASH_AT", None)
        if crash:
            env["DEDUPE_CRASH_AT"] = crash
        return subprocess.run([sys.executable, str(HERE / "dedupe.py"), "--config", str(bench.dir / "sources.toml"),
                               command], env=env, capture_output=True, text=True)

    def reference(self):
        clean = Bench(self.sources, self.overrides)
        self.addCleanup(clean.close)
        self.fill(clean)
        clean.scan()
        clean.plan()
        return clean.state_bytes()

    def test_kill_mid_scan_then_clean_resume(self):
        for point in ("commit:3", "segment:2", "batch:4"):
            with self.subTest(point=point):
                bench = Bench(self.sources, self.overrides)
                self.addCleanup(bench.close)
                self.fill(bench)
                killed = self.run_cli(bench, "scan", crash=point)
                self.assertEqual(killed.returncode, -9, killed.stderr)
                self.assertTrue((bench.dir / "state" / "lock").exists())
                index = store.sqlite3.connect(bench.dir / "state" / "index.sqlite")
                done = index.execute("select count(*) from files").fetchone()[0]
                segments = index.execute("select count(*) from segments").fetchone()[0]
                docs = index.execute("select count(*) from docs").fetchone()[0]
                coded = index.execute("select count(*) from doc_codes").fetchone()[0]
                index.close()
                self.assertGreater(done, 0)
                self.assertLess(done, 14)
                self.assertEqual(docs, coded)
                self.assertEqual(docs, done)
                self.assertGreater(segments, 0)
                resumed = self.run_cli(bench, "scan")
                self.assertEqual(resumed.returncode, 0, resumed.stderr)
                self.assertIn("stale lock", resumed.stderr)
                self.assertIn(f"{done} unchanged", resumed.stdout)
                self.assertFalse((bench.dir / "state" / "lock").exists())
                on_disk = sorted(p.name for p in (bench.dir / "state" / "segments").iterdir())
                index = store.sqlite3.connect(bench.dir / "state" / "index.sqlite")
                known = sorted(f"{r[0]:06d}.{ext}" for r in index.execute("select id from segments") for ext in ("doc", "hash"))
                index.close()
                self.assertEqual(on_disk, known)
                bench.plan()
                self.assertEqual(bench.state_bytes(), self.reference())

    def test_kill_during_segment_merge(self):
        bench = Bench(self.sources, {"scan": {"batch_words": 1500, "segment_merge_count": 2}})
        self.addCleanup(bench.close)
        self.fill(bench)
        killed = self.run_cli(bench, "scan", crash="merge")
        self.assertEqual(killed.returncode, -9, killed.stderr)
        self.assertEqual(self.run_cli(bench, "scan").returncode, 0)
        bench.plan()
        self.assertEqual(bench.state_bytes(), self.reference())
        found = bench.lookup(" ".join(story("shared")[5].split()[:15]))
        self.assertEqual(len(found["runs"]), 1)

    def test_live_lock_refuses_a_second_run_and_a_dead_one_is_cleared(self):
        self.fill(self.bench)
        lock = self.bench.dir / "state" / "lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(f"{os.getppid()} 0\n")
        refused = self.run_cli(self.bench, "scan")
        self.assertEqual(refused.returncode, 2)
        self.assertIn("another run holds", refused.stderr)
        self.assertTrue(lock.exists())
        sleeper = subprocess.Popen([sys.executable, "-c", "pass"])
        sleeper.wait()
        lock.write_text(f"{sleeper.pid} 0\n")
        self.assertEqual(self.run_cli(self.bench, "scan").returncode, 0)
        self.assertFalse(lock.exists())

    def test_plan_and_report_leave_no_half_written_files(self):
        self.fill(self.bench)
        self.bench.scan()
        self.bench.plan()
        self.bench.apply()
        self.bench.report()
        leftovers = [p for p in self.bench.dir.rglob("*") if p.name.endswith(".tmp")]
        self.assertEqual(leftovers, [])
        for line in (self.bench.dir / "state" / "plan.jsonl").read_text().splitlines():
            json.loads(line)

    def test_changed_structure_is_refused_until_rebuild(self):
        self.fill(self.bench)
        self.bench.scan()
        self.bench.overrides["structure"] = {"sample_modulus": 4}
        self.bench.write_config()
        refused = self.run_cli(self.bench, "scan")
        self.assertEqual(refused.returncode, 2)
        self.assertIn("rebuild", refused.stderr)
        self.assertEqual(self.run_cli(self.bench, "rebuild").returncode, 0)
        self.assertEqual(self.run_cli(self.bench, "plan").returncode, 0)


class Stamps(Case):
    def test_content_replaced_under_the_same_name_size_and_mtime_is_seen(self):
        first, second = text_of(story("st1")), text_of(story("st2"))
        second = (second + " " * len(first))[:len(first)]
        path = self.bench.put("mag", "a.txt", first)
        before = os.stat(path)
        self.bench.go()
        time.sleep(0.02)
        path.write_text(second, encoding="utf-8")
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(os.stat(path).st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(os.stat(path).st_size, before.st_size)
        self.assertEqual(self.bench.scan()["indexed"], 1)
        self.bench.plan()
        self.bench.apply()
        self.assertEqual(self.bench.out("mag", "a.txt"), second)


class ReadOnlyState(Case):
    def test_commands_refuse_cleanly_and_lookup_still_answers(self):
        import dedupe
        tale = story("ro")
        self.bench.put("mag", "a.txt", tale)
        self.bench.go()
        plan_before = (self.bench.dir / "state" / "plan.jsonl").read_bytes()
        state = self.bench.dir / "state"
        locked = [state] + [p for p in state.rglob("*")]
        for p in locked:
            os.chmod(p, 0o500 if p.is_dir() else 0o400)
        try:
            config = str(self.bench.dir / "sources.toml")
            for command in ("scan", "plan", "apply", "daily", "compact"):
                self.assertEqual(dedupe.main(["--config", config, command]), 2, command)
            found = self.bench.lookup(" ".join(tale[3].split()[:14]))
            self.assertEqual(len(found["runs"]), 1)
        finally:
            for p in locked:
                os.chmod(p, 0o700 if p.is_dir() else 0o600)
        self.assertEqual((state / "plan.jsonl").read_bytes(), plan_before)
