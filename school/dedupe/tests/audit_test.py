import json

from helpers import Bench, Case, paragraphs, story, text_of


class ReadShelves(Case):
    sources = {"mag": ("incoming", 50), "anth": ("incoming", 10), "shelf": ("read", 80), "old": ("read", 60)}

    def test_identical_read_files_are_both_kept(self):
        tale = story("ra")
        self.bench.put("shelf", "tale.txt", tale)
        self.bench.put("old", "tale.txt", tale)
        self.bench.put("old", "again.txt", tale)
        records = self.bench.go()
        for key in (("shelf", "tale.txt"), ("old", "tale.txt"), ("old", "again.txt")):
            self.assertEqual(records[key]["action"], "keep")
            self.assertEqual(self.bench.out(*key), text_of(tale))

    def test_same_text_in_other_typography_on_two_read_shelves(self):
        tale = story("rb")
        self.bench.put("shelf", "tale.txt", tale)
        self.bench.put("old", "tale.txt", "\n\n\n".join(p.upper() for p in tale) + "\n")
        records = self.bench.go()
        self.assertEqual(records[("old", "tale.txt")]["action"], "keep")
        self.assertEqual(records[("shelf", "tale.txt")]["action"], "keep")

    def test_read_novel_keeps_the_story_it_grew_from(self):
        novel = story("rc", 200)
        self.bench.put("shelf", "story.txt", novel[:40])
        self.bench.put("shelf", "novel.txt", novel)
        self.bench.put("old", "volume.txt", story("rd", 50) + novel[60:120])
        records = self.bench.go()
        for key in (("shelf", "story.txt"), ("shelf", "novel.txt"), ("old", "volume.txt")):
            self.assertEqual(records[key]["action"], "keep")
        self.assertEqual(self.bench.out("shelf", "novel.txt"), text_of(novel))
        both = [p for p in self.bench.pairs() if p["both_read"]]
        self.assertEqual(len(both), 2)
        self.assertTrue(all(p["acted"] is None and not p["ambiguous"] for p in both))
        self.assertIn("## Read against read (left alone)", self.bench.report())

    def test_read_still_beats_incoming(self):
        novel = story("re", 120)
        self.bench.put("shelf", "novel.txt", novel)
        self.bench.put("old", "novel.txt", novel)
        self.bench.put("mag", "novel.txt", novel)
        self.bench.put("anth", "book.txt", story("rf") + novel[20:70] + story("rg"))
        records = self.bench.go()
        self.assertEqual(records[("mag", "novel.txt")]["action"], "drop")
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(story("rf") + story("rg")))
        self.assertEqual(records[("old", "novel.txt")]["action"], "keep")

    def test_read_boilerplate_stays_unless_the_root_asks(self):
        footer = ["Copyright the shelf, all rights reserved everywhere and always."]
        for i in range(8):
            self.bench.put("shelf", f"s{i}.txt", story(f"rh{i}", 12) + footer)
            self.bench.put("mag", f"m{i}.txt", story(f"ri{i}", 12) + footer)
        records = self.bench.go()
        self.assertEqual(records[("shelf", "s0.txt")]["action"], "keep")
        self.assertEqual(records[("mag", "m0.txt")]["action"], "edit")
        self.bench.sources["shelf"] = ("read", 80, {"boilerplate": True})
        self.bench.write_config()
        records = self.bench.go()
        self.assertEqual(records[("shelf", "s0.txt")]["action"], "edit")
        self.assertEqual(self.bench.out("shelf", "s0.txt"), text_of(story("rh0", 12)))


class CleanCopy(Case):
    sources = {"mag": ("incoming", 50), "anth": ("incoming", 10, {"ledger": "roots/anth/ledger.jsonl"})}

    def ledger(self, rows):
        path = self.bench.dir / "roots" / "anth" / "ledger.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))

    def test_pdf_copy_loses_to_a_clean_copy_though_it_is_longer(self):
        shared = story("ca")
        self.bench.put("anth", "scan.txt", story("cb", 60) + shared + story("cc", 60))
        self.bench.put("anth", "book.txt", story("cd") + shared + story("ce"))
        self.ledger([{"slug": "scan", "title": "Scan", "format": "pdf"}, {"slug": "book", "title": "Book", "format": "epub"}])
        records = self.bench.go()
        self.assertEqual(records[("anth", "book.txt")]["action"], "keep")
        self.assertEqual(self.bench.out("anth", "scan.txt"), text_of(story("cb", 60) + story("cc", 60)))

    def test_without_a_ledger_word_the_longer_keeps_it(self):
        shared = story("cf")
        self.bench.put("anth", "scan.txt", story("cg", 60) + shared + story("ch", 60))
        self.bench.put("anth", "book.txt", story("ci") + shared + story("cj"))
        self.ledger([{"slug": "scan", "title": "Scan", "format": "epub"}])
        records = self.bench.go()
        self.assertEqual(records[("anth", "scan.txt")]["action"], "keep")

    def test_priority_still_outranks_cleanliness(self):
        tale = story("ck")
        self.bench.put("mag", "tale.txt", tale)
        self.bench.put("anth", "tale.txt", tale + ["The end of it."])
        self.ledger([{"slug": "tale", "title": "Tale", "format": "epub"}])
        records = self.bench.go()
        self.assertEqual(records[("mag", "tale.txt")]["action"], "keep")
        self.assertEqual(records[("anth", "tale.txt")]["action"], "drop")


class AroundACut(Case):
    def book(self, *parts):
        self.bench.put("anth", "book.txt", [p for part in parts for p in part])
        return self.bench.go()[("anth", "book.txt")]

    def test_introduction_that_does_not_name_the_heading_stays(self):
        before, inside, after = story("aa"), story("ab"), story("ac")
        piece = paragraphs("a flash piece of its own", 2)
        self.bench.put("mag", "inside.txt", inside)
        self.book(before, ["The Brass Head"], piece, inside, after)
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(before + ["The Brass Head"] + piece + after))

    def test_second_heading_block_must_repeat_the_first(self):
        before, inside, after = story("ad"), story("ae"), story("af")
        excerpt = paragraphs("another author's short excerpt", 3)
        self.bench.put("mag", "inside.txt", inside)
        self.book(before, ["Thomas Roe", "From The Lot"], excerpt, ["Jane Doe", "The Brass Head"], inside, after)
        self.assertEqual(self.bench.out("anth", "book.txt"),
                         text_of(before + ["Thomas Roe", "From The Lot"] + excerpt + after))

    def test_contributor_list_and_dedication_stay(self):
        inside, after = story("ag"), story("ah")
        names = ["STEPHEN BAXTER", "ALASTAIR REYNOLDS", "AN OWOMOYELA"]
        dedication = ["For my friend and colleague, some pure quill."]
        self.bench.put("mag", "inside.txt", inside)
        self.book(names, dedication, ["THE GIRL THING", "Pat Cadigan"], inside, after)
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(names + dedication + after))

    def test_contents_page_directly_above_the_first_story_stays(self):
        inside, after = story("ai"), story("aj")
        contents = ["The Brass Head", "Jane Doe", "Another Story", "John Roe", "A Third One", "Mary Major"]
        self.bench.put("mag", "inside.txt", inside)
        self.book(contents, inside, after)
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(contents + after))

    def test_signature_of_the_piece_above_is_not_a_heading(self):
        before, inside, after = story("ak"), story("al"), story("am")
        self.bench.put("mag", "inside.txt", inside)
        self.book(before, ["—John Kessel"], ["The Brass Head", "Jane Doe Jr."], inside, after)
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(before + ["—John Kessel"] + after))

    def test_year_line_under_the_heading_goes_with_it(self):
        before, inside, after = story("an"), story("ao"), story("ap")
        self.bench.put("mag", "inside.txt", inside)
        self.book(before, ["JANE DOE: THE BRASS HEAD", "(2001)"], inside, after)
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(before + after))

    def test_heading_stranded_at_the_edge_goes_and_a_last_line_stays(self):
        one, two = story("aq"), story("ar")
        self.bench.put("mag", "one.txt", one)
        self.bench.put("mag", "two.txt", two)
        record = self.book(one, ["But she does not mind, and she will not be going back there."], two, ["About the Authors"])
        self.assertEqual(self.bench.out("anth", "book.txt"),
                         text_of(["But she does not mind, and she will not be going back there."]))
        self.assertIn("stranded heading", {c["why"] for c in record["cuts"]})


class UniqueProse(Case):
    def test_passage_only_the_cut_copy_has_is_spared(self):
        before, inside, after = story("ua"), story("ub", 40), story("uc")
        passage = paragraphs("only the book has this", 3, 4, 5)
        self.bench.put("mag", "inside.txt", inside)
        self.bench.put("anth", "book.txt", before + inside[:20] + passage + inside[20:] + after)
        self.bench.go()
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(before + passage + after))

    def test_reworded_line_inside_a_cut_story_still_goes(self):
        before, inside, after = story("ud"), story("ue", 40), story("uf")
        varied = list(inside)
        varied[20] = paragraphs("a reworded paragraph", 1, 1, 1)[0]
        self.bench.put("mag", "inside.txt", inside)
        self.bench.put("anth", "book.txt", before + varied + after)
        self.bench.go()
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(before + after))

    def test_copy_with_an_afterword_is_not_dropped_whole(self):
        tale = story("ug", 40)
        afterword = ["Afterword"] + paragraphs("the author on how it was written", 6, 4, 5)
        self.bench.put("mag", "tale.txt", tale)
        self.bench.put("anth", "tale.txt", tale + afterword)
        records = self.bench.go()
        self.assertEqual(records[("anth", "tale.txt")]["action"], "edit")
        self.assertEqual(self.bench.out("anth", "tale.txt"), text_of(afterword))

    def test_casebook_quoting_the_work_it_excerpts(self):
        novel = story("uh", 200)
        quotes = []
        for i in range(8):
            quotes += paragraphs(f"essay {i}", 2) + [novel[150 + i * 3]]
        book = story("ui") + novel[30:70] + story("uj") + quotes + story("uk")
        self.bench.sources["shelf"] = ("read", 80)
        self.bench.put("shelf", "novel.txt", novel)
        self.bench.put("anth", "casebook.txt", book)
        theirs = []
        for i in range(8):
            theirs += paragraphs(f"zine essay {i}", 2) + [novel[150 + i * 3]]
        other = story("ul") + novel[30:70] + story("um") + theirs + story("un")
        self.bench.put("mag", "zine.txt", other)
        records = self.bench.go()
        self.assertEqual(self.bench.out("anth", "casebook.txt"),
                         text_of(story("ui") + story("uj") + quotes + story("uk")))
        self.assertEqual(records[("mag", "zine.txt")]["action"], "keep")
        self.assertTrue(any(p["ambiguous"] for p in self.bench.pairs()))


class Shelves(Case):
    def test_a_shelf_block_discovers_its_folders(self):
        bench = self.bench
        tale = story("sa")
        for folder, body in (("alpha", tale), ("beta", tale + ["One line more for beta."]), ("gamma", story("sb"))):
            path = bench.dir / "pile" / folder / "t.txt"
            path.parent.mkdir(parents=True)
            path.write_text(text_of(body))
        (bench.dir / "pile" / ".hidden").mkdir()
        bench.extra = ["[[shelf]]", 'path = "pile"', 'glob = "*.txt"', 'kind = "incoming"', "priority = 20",
                       'skip = ["gamma"]', "[shelf.priorities]", "beta = 30", ""]
        bench.write_config()
        names = {s.name: s.priority for s in bench.cfg.sources}
        self.assertEqual({k: names[k] for k in ("alpha", "beta")}, {"alpha": 20, "beta": 30})
        self.assertNotIn("gamma", names)
        records = bench.go()
        self.assertEqual(records[("beta", "t.txt")]["action"], "keep")
        self.assertEqual(records[("alpha", "t.txt")]["action"], "drop")
        (bench.dir / "pile" / "delta").mkdir()
        (bench.dir / "pile" / "delta" / "t.txt").write_text(text_of(story("sc")))
        self.assertEqual(bench.go()[("delta", "t.txt")]["action"], "keep")

    def test_a_shelf_folder_named_like_a_source_is_refused(self):
        (self.bench.dir / "pile" / "mag").mkdir(parents=True)
        self.bench.extra = ["[[shelf]]", 'path = "pile"', 'kind = "incoming"', ""]
        self.bench.write_config()
        from config import ConfigError
        with self.assertRaises(ConfigError):
            self.bench.cfg


class Damage(Case):
    sources = {"mag": ("incoming", 50), "anth": ("incoming", 10), "pile": ("incoming", 20, {"rough": True})}

    def said(self, seed, count=40):
        return [p.replace(". ", ". I don’t think she’s sure it isn’t. ", 1) for p in story(seed, count)]

    def test_broken_apostrophes_do_not_hide_a_copy(self):
        tale = self.said("da")
        self.bench.put("mag", "tale.txt", tale)
        self.bench.put("anth", "moji.txt", [p.replace("’", "?™") for p in tale])
        self.bench.put("anth", "lost.txt", [p.replace("’", "�") for p in tale])
        records = self.bench.go()
        self.assertEqual(records[("anth", "moji.txt")]["reason"], "identical text")
        self.assertEqual(records[("anth", "lost.txt")]["reason"], "identical text")

    def test_a_word_changed_in_every_other_sentence_is_still_the_same_work(self):
        tale = story("db", 40)
        worn = []
        for p in tale:
            parts = p.split(". ")
            for i in range(0, len(parts), 2):
                bits = parts[i].split(" ")
                bits[len(bits) // 2] = "zzz"
                parts[i] = " ".join(bits)
            worn.append(". ".join(parts))
        self.bench.put("mag", "tale.txt", tale)
        self.bench.put("anth", "worn.txt", worn)
        records = self.bench.go()
        self.assertEqual(records[("anth", "worn.txt")]["action"], "drop")
        self.assertEqual(records[("anth", "worn.txt")]["reason"], "same work")
        self.assertLess(records[("anth", "worn.txt")]["numbers"]["of_this"], 0.75)

    def test_half_the_paragraphs_rewritten_is_not_the_same_work(self):
        tale = story("dc", 40)
        other = story("dd", 40)
        self.bench.put("mag", "tale.txt", tale)
        self.bench.put("anth", "mixed.txt", [tale[i] if i % 2 else other[i] for i in range(40)])
        records = self.bench.go()
        self.assertNotEqual(records[("anth", "mixed.txt")]["action"], "drop")

    def test_rough_twin_is_dropped_whole_with_its_spam(self):
        tale = story("de", 40)
        spam = ["Buy quality boat parts at prices nobody else will offer you today or ever. " * 12]
        self.bench.put("mag", "tale.txt", tale)
        self.bench.put("pile", "tale.txt", tale[:20] + spam + tale[20:] + spam)
        self.bench.put("anth", "tale.txt", tale[:20] + spam + tale[20:])
        records = self.bench.go()
        self.assertEqual(records[("pile", "tale.txt")]["action"], "drop")
        self.assertEqual(records[("anth", "tale.txt")]["action"], "edit")

    def test_rough_root_loses_to_a_clean_one_of_lower_priority_only_by_priority(self):
        tale = story("df")
        self.bench.put("pile", "tale.txt", tale)
        self.bench.put("anth", "tale.txt", tale + ["One more line here."])
        records = self.bench.go()
        self.assertEqual(records[("pile", "tale.txt")]["action"], "keep")


class Templates(Case):
    def test_a_root_of_one_paragraph_texts_opening_alike_is_not_boilerplate(self):
        for i in range(40):
            self.bench.put("mag", f"t{i}.txt", [f"Tiny file number {i} says {story(f't{i}', 1)[0]}"])
        records = self.bench.go()
        self.assertEqual({r["action"] for r in records.values()}, {"keep"})


class Teasers(Case):
    def test_within_one_root_the_whole_story_is_kept_and_its_teaser_dropped(self):
        tale = story("te", 60)
        self.bench.put("mag", "full.txt", ["Episode 523"] + tale + ["Host comments on the story that went before."])
        self.bench.put("mag", "rerun.txt", ["From the vaults"] + tale[:25])
        records = self.bench.go()
        self.assertEqual(records[("mag", "full.txt")]["action"], "keep")
        self.assertEqual(records[("mag", "rerun.txt")]["action"], "drop")

    def test_a_higher_root_still_takes_its_story_out_of_a_lower_container(self):
        tale = story("tf")
        self.bench.put("mag", "tale.txt", tale)
        self.bench.put("anth", "double.txt", tale + ["***"] + story("tg"))
        self.bench.go()
        self.assertEqual(self.bench.out("anth", "double.txt"), text_of(["***"] + story("tg")))
