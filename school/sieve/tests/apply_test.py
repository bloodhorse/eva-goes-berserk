import json
import unittest

import helpers
from helpers import Tree, interview, narrative, poem, text_of, tree_digest


class Apply(Tree):
    def fill(self):
        body = narrative(1)
        self.body = body
        self.put("mag", "story.txt", body + ["Originally published in Night Ferry Quarterly, 2014."])
        self.put("mag", "talk.txt", interview(2), meta={"title": "Interview with Jane Roe"})
        self.put("mag", "poem.txt", poem(3))
        self.put("mag", "broken.txt", ["Too short to be anything."])
        self.put("pod", "sub/episode.txt", narrative(4))

    def test_each_kind_goes_to_its_own_tree(self):
        self.fill()
        self.plan()
        self.apply()
        self.assertEqual(self.out("fiction", "mag", "story.txt"), text_of(self.body))
        self.assertEqual(self.out("nonfiction", "mag", "talk.txt"), text_of(interview(2)))
        self.assertEqual(self.out("verse", "mag", "poem.txt"), text_of(poem(3)))
        self.assertEqual(self.out("stub", "mag", "broken.txt"), "Too short to be anything.\n")
        self.assertEqual(self.out("fiction", "pod", "sub/episode.txt"), text_of(narrative(4)))
        ledger = [json.loads(line) for line in (self.root / "sieve" / "out" / "ledger.jsonl").read_text().splitlines()]
        story = next(e for e in ledger if e["path"] == "story.txt")
        self.assertEqual(story["kind"], "fiction")
        self.assertEqual(story["words_in"] - story["words_out"], sum(c["words"] for c in story["cuts"]))
        self.assertEqual(story["cuts"][0]["reason"], "credit")

    def test_apply_converges(self):
        self.fill()
        self.plan()
        first = self.apply()
        out = self.root / "sieve" / "out"
        digest = tree_digest(out)
        second = self.apply()
        self.assertEqual(first["written"], 5)
        self.assertEqual(second["written"], 0)
        self.assertEqual(second["untouched"], 5)
        self.assertEqual(tree_digest(out), digest)
        self.assertFalse((out / ".trash").exists())
        self.plan()
        self.apply()
        self.assertEqual(tree_digest(out), digest)

    def test_sources_are_never_changed(self):
        self.fill()
        before = tree_digest(self.root / "dedupe")
        self.plan()
        self.apply()
        self.assertEqual(tree_digest(self.root / "dedupe"), before)

    def test_outputs_no_longer_wanted_go_to_the_trash(self):
        self.fill()
        self.plan()
        self.apply()
        out = self.root / "sieve" / "out"
        (self.root / "dedupe" / "out" / "mag" / "poem.txt").unlink()
        self.overrides('[[override]]\npath = "mag/talk.txt"\nkind = "fiction"\nreason = "read"\n')
        self.plan()
        tally = self.apply()
        self.assertFalse((out / "verse" / "mag" / "poem.txt").exists())
        self.assertFalse((out / "nonfiction" / "mag" / "talk.txt").exists())
        self.assertTrue((out / "fiction" / "mag" / "talk.txt").exists())
        trashed = sorted(p.name for p in (out / ".trash").rglob("*.txt"))
        self.assertEqual(trashed, ["poem.txt", "talk.txt"])
        self.assertFalse((out / "verse").exists())

    def test_a_damaged_output_is_rewritten(self):
        self.fill()
        self.plan()
        self.apply()
        target = self.root / "sieve" / "out" / "fiction" / "mag" / "story.txt"
        target.write_text("scribbled over\n")
        tally = self.apply()
        self.assertEqual(tally["written"], 1)
        self.assertEqual(target.read_text(encoding="utf-8"), text_of(self.body))

    def test_apply_without_a_plan_says_so(self):
        import writer
        with self.assertRaises(writer.NoPlan):
            self.apply()


if __name__ == "__main__":
    unittest.main()
