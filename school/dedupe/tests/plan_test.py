import random

from helpers import Bench, Case, paragraphs, sentence, story, text_of


def dialogue(seed, count=30):
    rng = random.Random(seed)
    out = []
    for _ in range(count):
        said = sentence(rng).rstrip(".")
        out.append(f'"{said}," she said -- and it wasn\'t the first time. ' + sentence(rng) + " " + sentence(rng))
    return out


def dressed(parts):
    out = []
    for i, part in enumerate(parts):
        part = part.replace('"', "“", 1).replace('"', "”", 1).replace("'", "’")
        part = part.replace(" -- ", "—").replace("  ", " ")
        words = part.split(" ")
        if i % 3 == 0:
            long = max(range(len(words)), key=lambda k: len(words[k]) if words[k].isalpha() else 0)
            words[long] = words[long][:3] + "-\n" + words[long][3:]
        if i % 3 == 1:
            long = max(range(len(words)), key=lambda k: len(words[k]) if words[k].isalpha() else 0)
            words[long] = words[long][:2] + "­" + words[long][2:]
        part = "   ".join(words[:4]) + " " + " ".join(words[4:])
        out.append(part.replace("fl", "ﬂ"))
    return out


class Copies(Case):
    def test_identical_files_under_different_names(self):
        tale = text_of(story("a"))
        self.bench.put("mag", "first.txt", tale)
        self.bench.put("mag", "second-name.txt", tale)
        records = self.bench.go()
        self.assertEqual(records[("mag", "first.txt")]["action"], "keep")
        self.assertEqual(records[("mag", "second-name.txt")]["action"], "drop")
        self.assertEqual(records[("mag", "second-name.txt")]["reason"], "identical file")
        self.assertEqual(records[("mag", "second-name.txt")]["counterpart"], {"source": "mag", "path": "first.txt"})
        self.assertTrue(self.bench.out_exists("mag", "first.txt"))
        self.assertFalse(self.bench.out_exists("mag", "second-name.txt"))

    def test_same_story_in_other_typography_with_another_footer(self):
        plain = dialogue("b")
        self.bench.put("mag", "plain.txt", plain + ["First printed in the Quarterly of Things."])
        self.bench.put("anth", "dressed.txt",
                       "\r\n\r\n".join(dressed(plain) + ["Copyright the author, reprinted here with thanks."]))
        records = self.bench.go()
        self.assertEqual(records[("mag", "plain.txt")]["action"], "keep")
        dropped = records[("anth", "dressed.txt")]
        self.assertEqual(dropped["action"], "drop")
        self.assertEqual(dropped["reason"], "same work")
        self.assertGreater(dropped["numbers"]["of_this"], 0.95)

    def test_typography_alone_is_identical_text(self):
        plain = dialogue("c")
        self.bench.put("mag", "plain.txt", plain)
        self.bench.put("anth", "curly.txt", [p.replace('"', "”").replace("'", "’").replace(" -- ", " – ")
                                             for p in plain])
        records = self.bench.go()
        self.assertEqual(records[("anth", "curly.txt")]["reason"], "identical text")

    def test_lightly_revised_reprint(self):
        first = story("d", 40)
        revised = list(first)
        for i in (4, 13, 22):
            revised[i] = revised[i].split(". ", 1)[0] + ". " + paragraphs(f"edit{i}", 1)[0]
        revised[-2:] = paragraphs("new ending", 3)
        self.bench.put("mag", "first.txt", first)
        self.bench.put("anth", "revised.txt", revised)
        records = self.bench.go()
        self.assertEqual(records[("mag", "first.txt")]["action"], "keep")
        self.assertEqual(records[("anth", "revised.txt")]["action"], "drop")
        self.assertEqual(records[("anth", "revised.txt")]["reason"], "same work")

    def test_read_beats_incoming_even_when_incoming_is_longer(self):
        tale = story("e")
        self.bench.put("shelf", "read.txt", tale)
        self.bench.put("mag", "incoming.txt", ["A long note from the magazine's editor about this one."] + tale
                       + paragraphs("afterword", 2))
        records = self.bench.go()
        self.assertEqual(records[("shelf", "read.txt")]["action"], "keep")
        self.assertEqual(records[("mag", "incoming.txt")]["action"], "drop")
        self.assertEqual(records[("mag", "incoming.txt")]["counterpart"]["source"], "shelf")
        self.assertIn("Incoming against read", self.bench.report())

    def test_priority_then_length_decide_among_equals(self):
        tale = story("f")
        self.bench.put("mag", "short.txt", tale)
        self.bench.put("mag", "long.txt", tale + paragraphs("coda", 2))
        self.bench.put("anth", "low.txt", tale + paragraphs("other coda", 4))
        records = self.bench.go()
        self.assertEqual(records[("mag", "long.txt")]["action"], "keep")
        self.assertEqual(records[("mag", "short.txt")]["action"], "drop")
        self.assertEqual(records[("anth", "low.txt")]["action"], "drop")


class Containers(Case):
    def test_story_in_the_middle_of_an_anthology(self):
        before, inside, after = story("g1"), story("g2"), story("g3")
        self.bench.put("mag", "inside.txt", inside)
        self.bench.put("anth", "book.txt", before + inside + after)
        records = self.bench.go()
        self.assertEqual(records[("mag", "inside.txt")]["action"], "keep")
        book = records[("anth", "book.txt")]
        self.assertEqual(book["action"], "edit")
        self.assertEqual(book["keep_units"], [[0, 30], [60, 90]])
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(before + after))
        self.assertEqual(self.bench.out("mag", "inside.txt"), text_of(inside))

    def test_title_and_byline_go_with_the_cut(self):
        before, inside, after = story("h1"), story("h2"), story("h3")
        self.bench.put("mag", "inside.txt", inside)
        self.bench.put("anth", "book.txt", before + ["The Brass Head", "JANE DOE"] + inside + after)
        self.bench.go()
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(before + after))

    def test_short_introduction_between_heading_and_story_goes_too(self):
        before, inside, after = story("i1"), story("i2"), story("i3")
        intro = ["In this one a brass head is dug up. " + paragraphs("intro", 1)[0]]
        self.bench.put("mag", "inside.txt", inside)
        self.bench.put("anth", "book.txt", before + ["The Brass Head"] + intro + inside + after)
        records = self.bench.go()
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(before + after))
        reasons = {c["why"] for c in records[("anth", "book.txt")]["cuts"]}
        self.assertIn("introduction between a heading and a cut", reasons)

    def test_introduction_outside_a_container_shelf_stays(self):
        before, inside, after = story("i4"), story("i5"), story("i6")
        intro = paragraphs("intro", 1)
        self.bench.put("shelf", "inside.txt", inside)
        self.bench.put("mag", "zine.txt", before + ["The Brass Head"] + intro + inside + after)
        self.bench.go()
        self.assertEqual(self.bench.out("mag", "zine.txt"), text_of(before + ["The Brass Head"] + intro + after))

    def test_annual_layout_with_the_heading_given_twice(self):
        before, inside, after = story("i7"), story("i8"), story("i9")
        intro = paragraphs("annual intro", 2)
        self.bench.put("mag", "inside.txt", inside)
        self.bench.put("anth", "annual.txt", before + ["JANE DOE", "The Brass Head"] + intro
                       + ["* * *", "The Brass Head", "JANE DOE"] + inside + ["JOHN ROE", "Another Story"] + after)
        self.bench.go()
        self.assertEqual(self.bench.out("anth", "annual.txt"), text_of(before + ["JOHN ROE", "Another Story"] + after))

    def test_section_numbers_are_not_headings(self):
        before, inside, after = story("i10"), story("i11"), story("i12")
        ending = paragraphs("last section", 2)
        self.bench.put("mag", "inside.txt", inside)
        self.bench.put("anth", "book.txt", before + ["IV"] + ending + inside + after)
        self.bench.go()
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(before + ["IV"] + ending + after))

    def test_text_before_a_cut_without_a_heading_stays(self):
        before, inside, after = story("j1"), story("j2"), story("j3")
        self.bench.put("mag", "inside.txt", inside)
        self.bench.put("anth", "book.txt", before + inside + after)
        self.bench.go()
        self.assertTrue(self.bench.out("anth", "book.txt").startswith(text_of(before).rstrip()))

    def test_story_at_the_very_start_and_the_very_end(self):
        opening, middle, closing = story("k1"), story("k2"), story("k3")
        self.bench.put("mag", "opening.txt", opening)
        self.bench.put("mag", "closing.txt", closing)
        self.bench.put("anth", "book.txt", opening + middle + closing)
        records = self.bench.go()
        self.assertEqual(records[("anth", "book.txt")]["keep_units"], [[30, 60]])
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(middle))

    def test_two_containers_share_a_story_with_no_standalone(self):
        shared = story("l0")
        first = story("l1") + shared + story("l2")
        second = story("l3") + shared + story("l4")
        self.bench.put("mag", "first.txt", first)
        self.bench.put("anth", "second.txt", second)
        records = self.bench.go()
        self.assertEqual(records[("mag", "first.txt")]["action"], "keep")
        self.assertEqual(records[("anth", "second.txt")]["action"], "edit")
        self.assertEqual(self.bench.out("anth", "second.txt"), text_of(story("l3") + story("l4")))
        self.assertEqual(self.bench.out("mag", "first.txt"), text_of(first))

    def test_two_containers_in_one_source_the_longer_keeps_the_story(self):
        shared = story("m0")
        longer = story("m1") + shared + story("m2", 40)
        shorter = story("m3") + shared + story("m4")
        self.bench.put("anth", "a-shorter.txt", shorter)
        self.bench.put("anth", "b-longer.txt", longer)
        records = self.bench.go()
        self.assertEqual(records[("anth", "b-longer.txt")]["action"], "keep")
        self.assertEqual(self.bench.out("anth", "a-shorter.txt"), text_of(story("m3") + story("m4")))

    def test_novel_excerpt_is_cut_from_the_novel(self):
        novel = story("n", 240)
        self.bench.put("mag", "excerpt.txt", novel[100:125])
        self.bench.put("anth", "novel.txt", novel)
        records = self.bench.go()
        self.assertEqual(records[("mag", "excerpt.txt")]["action"], "keep")
        self.assertEqual(records[("anth", "novel.txt")]["keep_units"], [[0, 100], [125, 240]])
        self.assertEqual(self.bench.out("anth", "novel.txt"), text_of(novel[:100] + novel[125:]))

    def test_excerpt_of_a_novel_she_has_read_is_dropped(self):
        novel = story("o", 240)
        self.bench.put("mag", "excerpt.txt", ["An extract from the novel."] + novel[100:125])
        self.bench.put("shelf", "novel.txt", novel)
        records = self.bench.go()
        self.assertEqual(records[("shelf", "novel.txt")]["action"], "keep")
        self.assertEqual(records[("mag", "excerpt.txt")]["action"], "drop")
        self.assertEqual(records[("mag", "excerpt.txt")]["reason"], "contained in a document that outranks it")
        self.assertEqual(self.bench.out("shelf", "novel.txt"), text_of(novel))

    def test_prose_stranded_between_cuts_stays_whatever_its_size(self):
        one, two, three = story("p1"), story("p2"), story("p3")
        note = ["A word from the editor about the next one, short."]
        essay = paragraphs("essay", 6)
        for name, body in (("one.txt", one), ("two.txt", two), ("three.txt", three)):
            self.bench.put("mag", name, body)
        self.bench.put("anth", "book.txt", one + note + two + essay + three)
        records = self.bench.go()
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(note + essay))
        book = records[("anth", "book.txt")]
        self.assertEqual([m["units"] for m in book["remnants"]], [[30, 31], [61, 67]])
        self.assertIn("Remnants kept", self.bench.report())

    def test_container_wholly_made_of_known_stories_is_dropped(self):
        one, two = story("q1"), story("q2")
        self.bench.put("mag", "one.txt", one)
        self.bench.put("mag", "two.txt", two)
        self.bench.put("anth", "book.txt", one + two)
        records = self.bench.go()
        self.assertEqual(records[("anth", "book.txt")]["action"], "drop")
        self.assertEqual(records[("anth", "book.txt")]["reason"], "nothing left after cuts")

    def test_poem_with_short_lines_inside_a_container(self):
        rng = random.Random("poem")
        stanzas = ["\n".join(" ".join(rng.choice(["ash", "bell", "crow", "dusk", "ember", "frost", "glass", "hollow",
                                                  "iron", "june", "kiln", "lamp", "moth", "nettle", "oar"])
                                      for _ in range(rng.randint(2, 5))) for _ in range(4)) for _ in range(45)]
        before, after = story("r1"), story("r2")
        self.bench.put("mag", "poem.txt", stanzas)
        self.bench.put("anth", "book.txt", before + stanzas + after)
        records = self.bench.go()
        self.assertEqual(records[("mag", "poem.txt")]["action"], "keep")
        self.assertEqual(self.bench.out("anth", "book.txt"), text_of(before + after))

    def test_story_glued_into_one_paragraph_is_cut_by_sentence(self):
        before, inside, after = story("s1", 6), story("s2"), story("s3", 6)
        self.bench.put("mag", "inside.txt", inside)
        self.bench.put("anth", "glued.txt", " ".join(before + inside + after) + "\n")
        self.bench.go()
        self.assertEqual(self.bench.out("anth", "glued.txt"), " ".join(before + after) + "\n")


class Restraint(Case):
    def test_shared_epigraph_triggers_nothing(self):
        epigraph = ["Whoever fights monsters should see to it that in the process he does not become a monster and if "
                    "you gaze long enough into an abyss the abyss will gaze back into you."]
        self.bench.put("mag", "one.txt", epigraph + story("t1"))
        self.bench.put("mag", "two.txt", epigraph + story("t2"))
        self.bench.put("anth", "three.txt", story("t3") + epigraph)
        records = self.bench.go()
        self.assertEqual({r["action"] for r in records.values()}, {"keep"})
        self.assertEqual(self.bench.pairs(), [])

    def test_a_line_in_twenty_documents_never_pairs_them(self):
        common = ["This sentence is in every single file of the shelf and it is long enough to make several shingles "
                  "all by itself for certain."]
        for i in range(24):
            self.bench.put("mag", f"doc{i:02d}.txt", paragraphs(f"u{i}", 2) + common + paragraphs(f"v{i}", 2))
        records = self.bench.go()
        self.assertEqual({r["action"] for r in records.values()}, {"keep"})
        self.assertEqual(self.bench.pairs(), [])

    def test_very_short_pieces(self):
        self.bench.put("mag", "tiny-a.txt", "It was dark, and cold.\n")
        self.bench.put("mag", "tiny-b.txt", "It was dark — and COLD!\n")
        self.bench.put("mag", "tiny-c.txt", "Nothing like the others here.\n")
        small = paragraphs("small", 2)
        self.bench.put("mag", "small.txt", small)
        self.bench.put("anth", "book.txt", story("w1") + small + story("w2"))
        records = self.bench.go()
        self.assertEqual(sorted(records[("mag", n)]["action"] for n in ("tiny-a.txt", "tiny-b.txt")), ["drop", "keep"])
        self.assertEqual(records[("mag", "tiny-c.txt")]["action"], "keep")
        self.assertLess(records[("mag", "small.txt")]["words"], 100)
        self.assertEqual(records[("mag", "small.txt")]["action"], "keep")
        self.assertEqual(records[("anth", "book.txt")]["action"], "keep")

    def test_partial_overlap_lands_in_the_ambiguous_band(self):
        base = story("x", 40)
        other = []
        for i, part in enumerate(base):
            other.append(part if i % 2 == 0 else paragraphs(f"x{i}", 1)[0])
        self.bench.put("mag", "one.txt", base)
        self.bench.put("anth", "two.txt", other)
        records = self.bench.go()
        self.assertEqual({r["action"] for r in records.values()}, {"keep"})
        pairs = self.bench.pairs()
        self.assertEqual(len(pairs), 1)
        self.assertTrue(pairs[0]["ambiguous"])
        self.assertIn("ambiguous band", self.bench.report())
        self.assertIn("one.txt", self.bench.report())

    def test_expanded_copy_keeps_its_new_part(self):
        base = story("y", 30)
        extra = story("y-extra", 60)
        self.bench.put("shelf", "base.txt", base)
        self.bench.put("mag", "expanded.txt", base + extra)
        records = self.bench.go()
        self.assertEqual(records[("mag", "expanded.txt")]["action"], "edit")
        self.assertEqual(self.bench.out("mag", "expanded.txt"), text_of(extra))


class Boilerplate(Case):
    def test_footers_of_one_source_are_stripped(self):
        bodies = {}
        for i in range(14):
            bodies[i] = story(f"z{i}", 8)
            self.bench.put("mag", f"s{i:02d}.txt", bodies[i] + [f"Originally published in Zeta Review, issue {i + 3}.",
                                                                "Reprinted by permission of the author."])
        inner = story("z-inner", 8)
        inner.insert(4, "Reprinted by permission of the author, he read aloud.")
        self.bench.put("mag", "inner.txt", inner)
        self.bench.put("anth", "elsewhere.txt", story("z-else", 8) + ["Reprinted by permission of the author."])
        records = self.bench.go()
        for i in range(14):
            record = records[("mag", f"s{i:02d}.txt")]
            self.assertEqual(record["action"], "edit")
            self.assertEqual(record["strip"]["tail_units"], 2)
            self.assertEqual(self.bench.out("mag", f"s{i:02d}.txt"), text_of(bodies[i]))
        self.assertEqual(records[("mag", "inner.txt")]["action"], "keep")
        self.assertEqual(records[("anth", "elsewhere.txt")]["action"], "keep")
        text = self.bench.report()
        self.assertIn("Reprinted by permission of the author.", text)
        self.assertIn("paragraphs opening like", text)

    def test_last_lines_that_merely_repeat_are_not_boilerplate(self):
        for i in range(14):
            body = story(f"aa{i}", 40)
            body.insert(20, "Yes.")
            self.bench.put("mag", f"s{i:02d}.txt", body + ["Yes."])
        records = self.bench.go()
        self.assertEqual({r["action"] for r in records.values()}, {"keep"})


class Determinism(Case):
    def fill(self, bench, order):
        shared = story("d-shared")
        files = {
            ("mag", "a.txt"): story("d1"),
            ("mag", "b.txt"): shared,
            ("mag", "c.txt"): story("d1"),
            ("anth", "book.txt"): story("d2") + ["The Title"] + shared + story("d3"),
            ("anth", "other.txt"): story("d4") + shared[:20] + story("d5"),
            ("shelf", "read.txt"): story("d6") + story("d2"),
            ("shelf", "half.txt"): [p if i % 2 else paragraphs(f"h{i}", 1)[0] for i, p in enumerate(story("d7"))],
            ("mag", "seven.txt"): story("d7"),
        }
        for i in range(12):
            files[("mag", f"f{i}.txt")] = story(f"d-f{i}", 6) + ["Reprinted by permission of the author."]
        keys = sorted(files)
        random.Random(order).shuffle(keys)
        return files, keys

    def test_plan_twice_is_identical(self):
        files, keys = self.fill(self.bench, 1)
        for source, name in keys:
            self.bench.put(source, name, files[(source, name)])
        self.bench.scan()
        self.bench.plan()
        first = self.bench.state_bytes()
        self.bench.plan()
        self.assertEqual(first, self.bench.state_bytes())
        self.assertNotIn(b"NaN", first)

    def test_listing_order_and_split_scans_do_not_change_the_plan(self):
        import scan
        files, keys = self.fill(self.bench, 1)
        for source, name in keys:
            self.bench.put(source, name, files[(source, name)])
        self.bench.scan()
        self.bench.plan()
        reference = self.bench.state_bytes()
        original = scan.walk
        for order in (2, 3):
            other = Bench(self.sources, {"scan": {"batch_words": 2000, "segment_merge_count": 2}})
            self.addCleanup(other.close)
            _, shuffled = self.fill(other, order)

            def shuffled_walk(source, order=order):
                found, complete = original(source)
                random.Random(order).shuffle(found)
                return found, complete

            scan.walk = shuffled_walk
            try:
                for start in range(0, len(shuffled), 5):
                    for source, name in shuffled[start:start + 5]:
                        other.put(source, name, files[(source, name)])
                    other.scan()
            finally:
                scan.walk = original
            other.plan()
            self.assertEqual(reference, other.state_bytes())

    def test_adding_one_file_reads_one_file_and_moves_only_its_neighbours(self):
        files, keys = self.fill(self.bench, 1)
        for source, name in keys:
            self.bench.put(source, name, files[(source, name)])
        self.bench.scan()
        before = self.bench.plan()
        self.bench.put("mag", "new.txt", story("d3"))
        counts = self.bench.scan()
        self.assertEqual(counts["indexed"], 1)
        self.assertEqual(counts["unchanged"], len(keys))
        after = self.bench.plan()
        changed = {key for key in before if before[key] != after[key]}
        self.assertIn(("anth", "book.txt"), changed)
        self.assertLessEqual(changed, {("anth", "book.txt"), ("anth", "other.txt")})
        self.assertEqual(after[("anth", "other.txt")]["keep_units"], before[("anth", "other.txt")]["keep_units"])
        self.assertEqual(after[("mag", "new.txt")]["action"], "keep")
        self.assertEqual(self.bench.scan()["indexed"], 0)


class Reference(Case):
    def test_reference_shelf_is_reported_and_looked_up_but_never_acts(self):
        import json
        tale = story("ref", 30)
        records = [{"id": "p-001", "text": "\n\n".join(tale[5:15])}, {"id": "p-002", "text": "\n\n".join(story("q", 4))}]
        folder = self.bench.dir / "roots" / "passages"
        folder.mkdir()
        (folder / "corpus.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records) + "not json\n")
        self.bench.extra = ["[[source]]", 'name = "passages"', 'path = "roots/passages"', 'glob = "corpus.jsonl"',
                            'kind = "reference"', 'format = "jsonl"', ""]
        self.bench.write_config()
        self.bench.put("mag", "tale.txt", tale)
        plan = self.bench.go()
        self.assertEqual(set(plan), {("mag", "tale.txt")})
        self.assertEqual(plan[("mag", "tale.txt")]["action"], "keep")
        self.assertEqual(self.bench.out("mag", "tale.txt"), text_of(tale))
        self.assertFalse((self.bench.dir / "out" / "passages").exists())
        pairs = self.bench.pairs()
        self.assertEqual(len(pairs), 1)
        self.assertEqual({pairs[0]["a"]["source"], pairs[0]["b"]["source"]}, {"mag", "passages"})
        self.assertIn("Reference shelves", self.bench.report())
        found = self.bench.lookup(" ".join(story("q", 4)[1].split()[:14]))
        self.assertEqual(found["runs"][0]["sources"][0]["path"], "corpus.jsonl#p-002")
        self.assertTrue(found["runs"][0]["sources"][0]["verified"])
        self.assertEqual(self.bench.scan()["indexed"], 0)
