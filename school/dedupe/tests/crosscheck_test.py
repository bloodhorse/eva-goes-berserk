import json

import crosscheck
from helpers import Case, paragraphs, story, text_of


class Audit(Case):
    sources = {"mag": ("incoming", 50, {"metadata": "meta/mag"}), "anth": ("incoming", 10),
               "pile": ("incoming", 20, {"rough": True}), "shelf": ("read", 80), "old": ("read", 60)}
    overrides = {"crosscheck": {"container_min_bytes": 2000, "same_min_sentences": 5, "text_min_sentences": 8,
                                "text_sentence_words": 8}}

    def work(self, name, title, authors, body):
        self.bench.put("mag", name + ".txt", body)
        meta = self.bench.dir / "meta" / "mag"
        meta.mkdir(parents=True, exist_ok=True)
        (meta / (name + ".json")).write_text(json.dumps({"title": title, "authors": authors}))

    def rows(self, run):
        return run(self.bench.cfg, say=lambda *a: None)

    def book(self):
        tale, other = story("xa"), story("xb")
        self.work("tale", "The Brass Head - Mag", ["Jane Doe 750"], tale)
        self.work("other", "Mag 12: A Quiet Year", ["John Roe"], other)
        self.bench.put("anth", "book.txt", story("xc") + ["THE BRASS HEAD", "Jane Doe"] + tale
                       + ["John Roe"] + ["John Roe wrote “A Quiet Year” in a cold winter. " + paragraphs("bio", 1)[0]]
                       + other + ["A QUIET YEAR", "Somebody Else"] + story("xd"))

    def test_works_found_in_two_places_and_caught(self):
        self.book()
        self.bench.go()
        rows = self.rows(crosscheck.run)
        same = sorted((r["title"], r["outcome"]) for r in rows if r["verdict"] == "same text")
        self.assertEqual(same, [("Mag 12: A Quiet Year", "caught"), ("The Brass Head - Mag", "caught")])
        self.assertEqual({r["outcome"] for r in self.rows(crosscheck.by_text)}, {"caught"})

    def test_a_copy_the_plan_leaves_is_reported_missed(self):
        self.bench.overrides["relations"] = {"min_match_words": 10 ** 9}
        self.bench.write_config()
        self.book()
        self.bench.go()
        outcomes = sorted(r["outcome"] for r in self.rows(crosscheck.run) if r["verdict"] == "same text")
        self.assertEqual(outcomes, ["missed", "missed"])
        self.assertEqual({r["outcome"] for r in self.rows(crosscheck.by_text)}, {"missed"})

    def test_same_title_and_author_over_another_text_is_different(self):
        self.work("tale", "The Brass Head", ["Jane Doe"], story("xe"))
        self.bench.put("anth", "book.txt", story("xf") + ["The Brass Head", "Jane Doe"] + story("xg"))
        self.bench.go()
        self.assertEqual([r["outcome"] for r in self.rows(crosscheck.run)], ["different"])

    def test_read_twins_are_named_read_read(self):
        tale = story("xh")
        self.bench.put("shelf", "a.txt", tale)
        self.bench.put("old", "b.txt", tale + ["One more line."])
        self.bench.go()
        self.assertEqual([r["outcome"] for r in self.rows(crosscheck.by_text)], ["read-read"])

    def test_losses_names_a_passage_nobody_kept(self):
        tale = story("xi", 40)
        only_here = paragraphs("a passage in the rough copy alone", 3, 4, 5)
        self.work("tale", "A Tale", ["Jane Doe"], tale)
        self.bench.put("pile", "tale.txt", tale[:20] + only_here + tale[20:])
        self.bench.put("anth", "tale.txt", tale[:20] + only_here + tale[20:] + ["A last line."])
        self.bench.go()
        rows = {r["source"]: r for r in self.rows(crosscheck.losses)}
        self.assertNotIn("pile", rows)
        self.bench.sources["anth"] = ("incoming", 10, {"rough": True})
        self.bench.write_config()
        self.bench.go()
        rows = {r["source"]: r for r in self.rows(crosscheck.losses)}
        self.assertEqual(rows["pile"]["passages"], 1)
        self.assertGreaterEqual(rows["pile"]["passage_words"], 100)
