import json
import time

from helpers import Case, paragraphs, story, text_of


class Apply(Case):
    def fill(self):
        self.shared = story("shared")
        self.bench.put("mag", "shared.txt", self.shared)
        self.bench.put("mag", "twin.txt", self.shared)
        self.bench.put("mag", "alone.txt", story("alone"))
        self.bench.put("anth", "book.txt", story("x") + self.shared + story("y"))

    def test_ledger_says_what_happened_to_every_file(self):
        self.fill()
        self.bench.go()
        ledger = self.bench.ledger()
        self.assertEqual({k: v["action"] for k, v in ledger.items()}, {
            ("mag", "shared.txt"): "kept", ("mag", "twin.txt"): "dropped", ("mag", "alone.txt"): "kept",
            ("anth", "book.txt"): "edited"})
        book = ledger[("anth", "book.txt")]
        self.assertEqual(book["words_in"], len(text_of(story("x") + self.shared + story("y")).split()))
        self.assertEqual(book["words_out"], len(text_of(story("x") + story("y")).split()))
        self.assertEqual(ledger[("mag", "twin.txt")]["counterpart"], "mag:shared.txt")
        self.assertEqual(ledger[("mag", "twin.txt")]["words_out"], 0)
        self.assertTrue(book["file"].endswith("roots/anth/book.txt"))

    def test_second_apply_writes_nothing(self):
        self.fill()
        self.bench.go()
        again = self.bench.apply()
        self.assertEqual(again["written"], 0)
        self.assertEqual(again["untouched"], 3)

    def test_apply_converges_after_a_new_plan(self):
        self.fill()
        self.bench.go()
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(story("x") + story("y")))
        (self.bench.dir / "roots" / "mag" / "shared.txt").unlink()
        (self.bench.dir / "roots" / "mag" / "twin.txt").unlink()
        (self.bench.dir / "roots" / "mag" / "alone.txt").unlink()
        self.bench.put("mag", "y.txt", story("y"))
        stray = self.bench.dir / "out" / "mag" / "stray.txt"
        stray.write_text("left by hand\n")
        self.bench.go()
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(story("x") + self.shared))
        self.assertFalse(self.bench.out_exists("mag", "shared.txt"))
        self.assertFalse(self.bench.out_exists("mag", "alone.txt"))
        self.assertFalse(stray.exists())
        trashed = sorted(p.name for p in (self.bench.dir / "out" / ".trash").rglob("*.txt"))
        self.assertEqual(trashed, ["alone.txt", "shared.txt", "stray.txt"])
        self.assertEqual(set(self.bench.ledger()), {("mag", "y.txt"), ("anth", "book.txt")})

    def test_file_changed_between_scan_and_apply(self):
        self.fill()
        self.bench.scan()
        self.bench.plan()
        time.sleep(0.01)
        self.bench.put("anth", "book.txt", story("x") + paragraphs("rewritten", 30) + story("y"))
        self.bench.put("mag", "alone.txt", story("alone") + ["One more line."])
        tally = self.bench.apply()
        self.assertEqual(tally["stale"], 2)
        ledger = self.bench.ledger()
        self.assertEqual(ledger[("anth", "book.txt")]["action"], "stale")
        self.assertEqual(ledger[("mag", "alone.txt")]["action"], "stale")
        self.assertFalse(self.bench.out_exists("anth", "book.txt"))
        self.assertFalse(self.bench.out_exists("mag", "alone.txt"))
        self.assertTrue(self.bench.out_exists("mag", "shared.txt"))
        self.bench.go()
        self.assertEqual(self.bench.ledger()[("anth", "book.txt")]["action"], "kept")

    def test_file_gone_between_scan_and_apply(self):
        self.fill()
        self.bench.go()
        (self.bench.dir / "roots" / "mag" / "alone.txt").unlink()
        tally = self.bench.apply()
        self.assertEqual(tally["missing"], 1)
        self.assertFalse(self.bench.out_exists("mag", "alone.txt"))

    def test_output_damaged_by_hand_is_rewritten(self):
        self.fill()
        self.bench.go()
        (self.bench.dir / "out" / "anth" / "book.txt").write_text("scribble\n")
        self.assertEqual(self.bench.apply()["written"], 1)
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(story("x") + story("y")))

    def test_kept_files_are_byte_copies(self):
        raw = ("Line one of a paragraph\r\nwrapped by hand.\r\n\r\n\r\n" + text_of(story("raw"))).encode("utf-8")
        self.bench.put("mag", "raw.txt", raw)
        self.bench.go()
        self.assertEqual((self.bench.dir / "out" / "mag" / "raw.txt").read_bytes(), raw)

    def test_report_numbers_add_up(self):
        self.fill()
        self.bench.go()
        text = self.bench.report()
        plan = [json.loads(l) for l in (self.bench.dir / "state" / "plan.jsonl").read_text().splitlines()]
        words_in = sum(r["words"] for r in plan)
        words_out = sum(r["words_out"] for r in plan)
        self.assertIn(f"- words in: {words_in:,}", text)
        self.assertIn(f"- surviving: {words_out:,}", text)
        ledger = self.bench.ledger()
        self.assertEqual(words_out, sum(e["words_out"] for e in ledger.values()))
        self.assertIn("| anth | incoming | 1 |", text)
