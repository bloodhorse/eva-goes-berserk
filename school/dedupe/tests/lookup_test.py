from helpers import Case, paragraphs, story


class Lookup(Case):
    def setUp(self):
        super().setUp()
        self.tale = story("tale", 40)
        self.bench.put("shelf", "tale.txt", self.tale + ["She said “the lamp-lighter’s naïve daughter went "
                                                         "down to the river at dusk and never came back,” and wept."])
        self.bench.put("mag", "other.txt", story("other", 40))
        self.bench.scan()

    def page(self, planted):
        filler = paragraphs("generated", 30)
        return "\n\n".join(filler[:15] + [planted] + filler[15:])

    def test_finds_a_planted_twelve_word_run(self):
        run = " ".join(self.tale[7].split()[5:17])
        found = self.bench.lookup(self.page(f"Then, {run} and so on."))
        self.assertEqual(len(found["runs"]), 1)
        hit = found["runs"][0]
        self.assertEqual(hit["words"], 12)
        self.assertEqual(hit["sources"][0]["source"], "shelf")
        self.assertEqual(hit["sources"][0]["path"], "tale.txt")
        self.assertTrue(hit["sources"][0]["verified"])
        self.assertIn(run.split()[3], hit["sources"][0]["sentence"])
        self.assertAlmostEqual(found["score"], 12 / found["words"], places=3)

    def test_does_not_find_a_six_word_run(self):
        run = " ".join(self.tale[7].split()[5:11])
        found = self.bench.lookup(self.page(f"Then, {run} and so on."))
        self.assertEqual(found["runs"], [])
        self.assertEqual(found["score"], 0.0)

    def test_run_survives_other_typography(self):
        found = self.bench.lookup(self.page('he muttered "The lamp lighter\'s naive daughter went down to the river '
                                            'at dusk and never came back" twice.'))
        self.assertEqual(len(found["runs"]), 1)
        self.assertEqual(found["runs"][0]["words"], 16)
        self.assertIn("naïve daughter", found["runs"][0]["sources"][0]["sentence"])

    def test_run_across_a_paragraph_break(self):
        run = " ".join(self.tale[3].split()[-6:] + self.tale[4].split()[:6])
        found = self.bench.lookup(self.page(run))
        self.assertEqual(found["runs"][0]["words"], 12)
        self.assertIn(" / ", found["runs"][0]["sources"][0]["sentence"])

    def test_empty_and_tiny_inputs(self):
        self.assertEqual(self.bench.lookup("")["runs"], [])
        self.assertEqual(self.bench.lookup("three words only")["score"], 0.0)

    def test_source_changed_after_the_scan_is_reported_not_trusted(self):
        run = " ".join(self.tale[7].split()[5:17])
        self.bench.put("shelf", "tale.txt", story("replaced", 40))
        found = self.bench.lookup(self.page(run))
        self.assertEqual(found["runs"], [])
        self.assertEqual(found["score"], 0.0)

    def test_lookup_after_more_scans_and_a_merge(self):
        self.bench.overrides["scan"]["segment_merge_count"] = 1
        self.bench.write_config()
        late = story("late", 40)
        self.bench.put("mag", "late.txt", late)
        self.bench.scan()
        self.bench.put("mag", "later.txt", story("later", 40))
        self.bench.scan()
        for source_story, name in ((self.tale, "tale.txt"), (late, "late.txt")):
            found = self.bench.lookup(self.page(" ".join(source_story[9].split()[2:16])))
            self.assertEqual(found["runs"][0]["sources"][0]["path"], name)
