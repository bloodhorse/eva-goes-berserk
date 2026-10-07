import json
import random
import unittest

import helpers
from helpers import (Tree, fake_interview, interview, letters, narrative, poem, prose_poem, review, text_of)

import planner
import reporter
import reviewer
import settings


class Kinds(Tree):
    def test_a_story_is_fiction(self):
        self.put("mag", "story.txt", narrative(1))
        record = self.plan()[("mag", "story.txt")]
        self.assertEqual(record["kind"], "fiction")
        self.assertEqual(record["cuts"], [])

    def test_an_interview_in_question_and_answer_form_is_nonfiction(self):
        self.put("mag", "talk.txt", interview(2), meta={"title": "Interview with Jane Roe", "authors": ["Sam Poe"]})
        record = self.plan()[("mag", "talk.txt")]
        self.assertEqual(record["kind"], "nonfiction")
        signals = {e["signal"] for e in record["evidence"]}
        self.assertIn("title", signals)
        self.assertIn("question-and-answer", signals)
        self.assertIn("talk-about-writing", signals)

    def test_an_interview_is_nonfiction_without_its_title(self):
        self.put("mag", "untitled.txt", interview(3), meta={"title": "The Long Dark"})
        self.assertEqual(self.plan()[("mag", "untitled.txt")]["kind"], "nonfiction")

    def test_a_review_is_nonfiction(self):
        self.put("mag", "review.txt", review(4), meta={"title": "Book Review: Twelve Doors"})
        self.assertEqual(self.plan()[("mag", "review.txt")]["kind"], "nonfiction")

    def test_a_poem_is_verse(self):
        self.put("mag", "poem.txt", poem(5))
        record = self.plan()[("mag", "poem.txt")]
        self.assertEqual(record["kind"], "verse")
        self.assertEqual(record["cuts"], [])

    def test_a_prose_poem_stays_fiction(self):
        self.put("mag", "prose-poem.txt", prose_poem(6))
        self.assertEqual(self.plan()[("mag", "prose-poem.txt")]["kind"], "fiction")

    def test_a_story_told_as_letters_stays_fiction(self):
        self.put("mag", "letters.txt", letters(7))
        self.assertEqual(self.plan()[("mag", "letters.txt")]["kind"], "fiction")

    def test_a_story_told_as_an_interview_stays_fiction(self):
        self.put("mag", "transcript.txt", fake_interview(8), meta={"title": "The Quarry: An Interview"})
        record = self.plan()[("mag", "transcript.txt")]
        self.assertIn(record["kind"], ("fiction", "unsure"))
        self.assertNotEqual(record["kind"], "nonfiction")
        self.put("mag", "transcript2.txt", fake_interview(9), meta={"title": "The Quarry"})
        self.assertEqual(self.plan()[("mag", "transcript2.txt")]["kind"], "fiction")

    def test_a_story_with_heavy_dialogue_is_fiction(self):
        self.put("mag", "talky.txt", narrative(10, speech=0.95))
        self.assertEqual(self.plan()[("mag", "talky.txt")]["kind"], "fiction")

    def test_a_tiny_file_is_a_stub(self):
        self.put("mag", "broken.txt", ["Mara looked at the lantern and then the page ended here for no reason at all."])
        self.assertEqual(self.plan()[("mag", "broken.txt")]["kind"], "stub")

    def test_a_short_podcast_page_is_a_stub_and_a_long_one_is_not(self):
        self.put("pod", "notes.txt", narrative(11, paragraphs=3))
        self.put("pod", "episode.txt", narrative(12))
        plan = self.plan()
        self.assertEqual(plan[("pod", "notes.txt")]["kind"], "stub")
        self.assertEqual(plan[("pod", "episode.txt")]["kind"], "fiction")

    def test_a_page_label_decides(self):
        self.put("mag", "labelled.txt", narrative(13), meta={"title": "Night Ferry", "classes": ["category-poetry"]})
        self.put("mag", "essay.txt", narrative(14), meta={"title": "Night Ferry", "classes": ["category-nonfiction"]})
        plan = self.plan()
        self.assertEqual(plan[("mag", "labelled.txt")]["kind"], "verse")
        self.assertEqual(plan[("mag", "essay.txt")]["kind"], "nonfiction")

    def test_a_read_shelf_is_never_touched(self):
        self.put("shelf", "book.txt", interview(15))
        self.put("mag", "story.txt", narrative(16))
        self.assertNotIn(("shelf", "book.txt"), self.plan())


class Edges(Tree):
    def test_podcast_host_intro_and_outro_are_cut(self):
        body = narrative(20)
        parts = (["Welcome back to Escape Pod, the science fiction podcast. This week's episode is narrated by Sam Poe."]
                 + body + ["Our closing quotation this week comes from an old book. Thanks for listening, and have fun."])
        self.put("pod", "episode.txt", parts)
        record = self.plan()[("pod", "episode.txt")]
        self.assertEqual(record["kind"], "fiction")
        self.assertEqual(self.reasons(record), ["host-intro", "outro"])
        self.apply()
        self.assertEqual(self.out("fiction", "pod", "episode.txt"), text_of(body))

    def test_a_fictional_radio_host_is_not_cut(self):
        body = ["And we are back. This is hour two of the night show and I am your host, Mara. She looked at the lights."] \
            + narrative(21)
        self.put("pod", "radio.txt", body)
        self.assertEqual(self.plan()[("pod", "radio.txt")]["cuts"], [])

    def test_bio_credit_and_comments_are_cut_from_a_magazine_story(self):
        body = narrative(22)
        parts = (["Content warning: drowning."] + body + [
            "Originally published in Night Ferry Quarterly, 2014.",
            "About the Author",
            "Jane Roe is a writer living in Leeds. Her fiction has appeared in many magazines and she is the author of "
            "two novels. Find her online at www.example.org.",
            "3 Comments",
            "Sam says: I loved this one, it made me cry on the bus and I read it twice more that week.",
            "Lee says: Same here. Wonderful."])
        self.put("mag", "wrapped.txt", parts, meta={"title": "The Ferry", "authors": ["Jane Roe"]})
        record = self.plan()[("mag", "wrapped.txt")]
        self.assertEqual(record["kind"], "fiction")
        self.assertEqual(self.reasons(record), ["content-warning", "credit", "author-bio", "comments"])
        self.apply()
        self.assertEqual(self.out("fiction", "mag", "wrapped.txt"), text_of(body))

    def test_a_serial_chapter_loses_its_note_and_navigation(self):
        body = narrative(23)
        parts = (["There will be no chapter next week; see my Patreon post for why, and thank you for your patience."]
                 + ["Previous Chapter Next Chapter"] + body + ["Previous Chapter Next Chapter"]
                 + ["Well! That was a big one. Poor Mara.", "If you want more, please consider subscribing to the Patreon:",
                    "And thank you for reading my little story!"])
        self.put("serial", "ch-1.txt", parts)
        record = self.plan()[("serial", "ch-1.txt")]
        self.assertEqual(record["kind"], "fiction")
        self.assertEqual(set(self.reasons(record)), {"pitch", "nav", "author-note"})
        self.apply()
        self.assertEqual(self.out("fiction", "serial", "ch-1.txt"), text_of(body))

    def test_dialogue_that_looks_like_navigation_is_not_cut(self):
        body = narrative(24) + ["“Next.”", "“Like?”"] + narrative(25, paragraphs=8) + ["“Last page.”"]
        self.put("serial", "ch-2.txt", body)
        self.assertEqual(self.plan()[("serial", "ch-2.txt")]["cuts"], [])

    def test_cuts_never_leave_an_empty_story(self):
        parts = ["Originally published in Night Ferry Quarterly.", "Copyright 2014 by Jane Roe.",
                 "First published in 2014 by a small press."] + narrative(26, paragraphs=1)
        self.put("mag", "thin.txt", parts * 1)
        record = self.plan()[("mag", "thin.txt")]
        self.assertEqual(record["cuts"], [])


def year_book():
    summation = ["SUMMATION: 1991"] + [
        f"The year 19{90 + i % 2} saw {3 + i} new magazines and the collapse of two publishers. The anthology market was "
        f"flat; the best original anthology was edited by a newcomer and published by a small press, and the Hugo and "
        f"Nebula awards went to novels reviewed in these pages last year." for i in range(12)]
    first = ["THE NIGHT FERRY", "Jane Roe",
             "New writer Jane Roe made her first sale in 1988, and her stories have appeared in several magazines. "
             "She lives in Leeds with her family.",
             "In the quiet story that follows, she takes us across a river that is wider than it looks."] + narrative(30, 30)
    second = ["SALT", "Corwin Vane",
              "Corwin Vane is the author of two novels and a collection. His most recent book was a finalist for the "
              "Nebula award in 1990. He lives in Hull."] + narrative(31, 30)
    mentions = ["HONORABLE MENTIONS"] + [f"Author {i}, “A Story Called {i},” Night Ferry Quarterly, Spring 1991."
                                         for i in range(20)]
    return summation, first, second, mentions


class Books(Tree):
    def test_an_anthology_loses_summation_headnotes_and_mentions(self):
        summation, first, second, mentions = year_book()
        self.put("anth", "best-1991.txt", summation + first + second + mentions)
        self.ledger([{"slug": "best-1991", "title": "Best of 1991", "author": "An Editor", "sections_kept": [
            {"start": "SUMMATION: 1991", "words": 500}, {"start": "THE NIGHT FERRY", "words": 2000},
            {"start": "SALT", "words": 2000}, {"start": "HONORABLE MENTIONS", "words": 200}]}])
        record = self.plan()[("anth", "best-1991.txt")]
        self.assertEqual(record["kind"], "fiction")
        self.assertEqual(self.reasons(record), ["summation", "editor-note", "editor-note", "honorable-mentions"])
        self.assertEqual([s["kind"] for s in record["sections"]], ["apparatus", "story", "story", "apparatus"])
        self.apply()
        kept = self.out("fiction", "anth", "best-1991.txt")
        self.assertEqual(kept, text_of(first[:2] + first[4:] + second[:2] + second[3:]))

    def test_headnotes_are_found_without_a_ledger(self):
        summation, first, second, mentions = year_book()
        self.put("anth", "plain.txt", summation + first + second + mentions)
        record = self.plan()[("anth", "plain.txt")]
        self.assertEqual(self.reasons(record), ["summation", "editor-note", "editor-note", "honorable-mentions"])

    def test_a_summation_does_not_swallow_a_story_without_a_heading(self):
        summation, first, second, mentions = year_book()
        story = narrative(32, 40)
        self.put("anth", "headless.txt", summation + story)
        record = self.plan()[("anth", "headless.txt")]
        self.apply()
        kept = self.out("fiction", "anth", "headless.txt")
        self.assertIn(story[3], kept)
        self.assertIn(story[-1], kept)
        self.assertNotIn(summation[2], kept)

    def test_an_essay_keeping_book_keeps_its_essays(self):
        summation, first, second, mentions = year_book()
        essay = ["INTRODUCTION"] + review(33, 10)
        self.put("anth", "essay-book.txt", essay + first + second + mentions)
        record = self.plan()[("anth", "essay-book.txt")]
        self.assertEqual(record["kind"], "mixed")
        self.assertEqual(self.reasons(record), ["honorable-mentions"])
        self.assertIn("nonfiction-kept", [s["kind"] for s in record["sections"]])
        self.assertGreater(record["words_nonfiction_kept"], 500)
        self.apply()
        kept = self.out("mixed", "anth", "essay-book.txt")
        self.assertIn(essay[3], kept)
        self.assertIn(first[2], kept)

    def test_the_same_book_without_the_switch_loses_them(self):
        summation, first, second, mentions = year_book()
        essay = ["INTRODUCTION"] + review(34, 10)
        self.put("anth", "other-book.txt", essay + first + second + mentions)
        record = self.plan()[("anth", "other-book.txt")]
        self.assertEqual(record["kind"], "fiction")
        self.assertEqual(self.reasons(record)[0], "introduction")
        self.assertIn("editor-note", self.reasons(record))

    def test_a_story_opening_that_names_a_place_in_its_title_is_not_a_headnote(self):
        story = ["IN OLD ROMARTH", "Mara Quinc was a grandee of Old Romarth and enjoyed a life of quiet routine."] \
            + narrative(35, 30)
        self.put("anth", "romarth.txt", narrative(36, 30) + story)
        self.assertEqual(self.plan()[("anth", "romarth.txt")]["cuts"], [])


class Overrides(Tree):
    def test_an_override_wins_and_is_recorded(self):
        self.put("mag", "talk.txt", interview(40), meta={"title": "Interview with Jane Roe"})
        self.put("mag", "story.txt", narrative(41), meta={"title": "Salt"})
        self.overrides('[[override]]\npath = "mag/talk.txt"\nkind = "fiction"\nreason = "a story in costume"\n\n'
                       '[[override]]\ntitle = "^salt$"\nsource = "mag"\nkind = "nonfiction"\nreason = "an essay"\n')
        plan = self.plan()
        self.assertEqual(plan[("mag", "talk.txt")]["kind"], "fiction")
        self.assertEqual(plan[("mag", "talk.txt")]["overrides"][0]["was"], "nonfiction")
        self.assertEqual(plan[("mag", "story.txt")]["kind"], "nonfiction")
        cfg = self.cfg()
        reporter.run(cfg, say=self.said.append)
        report = cfg.report_file.read_text(encoding="utf-8")
        self.assertIn("2 changed a kind", report)

    def test_forced_cut_and_forced_keep(self):
        body = narrative(42)
        parts = body[:10] + ["An advertisement nobody could have recognised.", "It ran for two paragraphs."] + body[10:] \
            + ["Originally published in Night Ferry Quarterly, 2014."]
        self.put("mag", "ad.txt", parts)
        self.overrides('[[override]]\npath = "mag/ad.txt"\ncut = { from = "An advertisement nobody", to = "It ran for" }\n'
                       'as = "pitch"\nreason = "read"\n\n'
                       '[[override]]\npath = "mag/ad.txt"\nkeep = { from = "Originally published in" }\nreason = "part of the story"\n')
        record = self.plan()[("mag", "ad.txt")]
        self.assertEqual(record["cuts"], [{"paragraphs": [10, 12], "reason": "pitch", "words": 11}])
        self.apply()
        self.assertEqual(self.out("fiction", "mag", "ad.txt"), text_of(body + parts[-1:]))

    def test_an_override_that_finds_nothing_is_reported(self):
        self.put("mag", "story.txt", narrative(43))
        self.overrides('[[override]]\npath = "mag/story.txt"\ncut = { from = "No such words" }\nreason = "x"\n\n'
                       '[[override]]\npath = "mag/gone.txt"\nkind = "stub"\nreason = "y"\n')
        record = self.plan()[("mag", "story.txt")]
        self.assertTrue(record["override_problems"])
        info = json.loads((self.root / "sieve" / "state" / "run.json").read_text())
        self.assertEqual(len(info["overrides_unused"]), 1)

    def test_a_bad_override_file_stops_the_run(self):
        self.overrides('[[override]]\nkind = "fiction"\n')
        with self.assertRaises(settings.ConfigError):
            self.cfg()


class Hardening(Tree):
    def fill(self):
        summation, first, second, mentions = year_book()
        self.put("anth", "best-1991.txt", summation + first + second + mentions)
        self.put("mag", "talk.txt", interview(50), meta={"title": "Interview with Jane Roe"})
        self.put("mag", "poem.txt", poem(51))
        for i in range(12):
            self.put("mag", f"story-{i}.txt", narrative(60 + i))
        self.put("pod", "notes.txt", narrative(52, paragraphs=2))
        self.put("serial", "deep/ch-1.txt", narrative(53) + ["Previous Chapter Next Chapter", "Thank you for reading!"])

    def test_the_plan_is_the_same_bytes_again_and_under_shuffled_order(self):
        self.fill()
        self.plan()
        plan_file = self.root / "sieve" / "state" / "plan.jsonl"
        first = plan_file.read_bytes()
        self.plan()
        self.assertEqual(plan_file.read_bytes(), first)
        cfg = self.cfg()
        rng = random.Random(3)
        records, skipped = planner.build(cfg, shuffle=rng.shuffle)
        again = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records).encode("utf-8")
        self.assertEqual(again, first)

    def test_worker_processes_give_the_same_plan(self):
        self.fill()
        for i in range(70):
            self.put("mag", f"more-{i}.txt", narrative(100 + i, paragraphs=6))
        self.plan()
        plan_file = self.root / "sieve" / "state" / "plan.jsonl"
        first = plan_file.read_bytes()
        config = self.root / "sieve" / "sieve.toml"
        config.write_text(config.read_text().replace("jobs = 1", "jobs = 2"))
        self.plan()
        self.assertEqual(plan_file.read_bytes(), first)

    def test_bad_and_vanished_files_are_recorded_not_fatal(self):
        self.fill()
        self.put("mag", "binary.txt", None, raw=b"\xff\xfe\x00bad")
        self.put("mag", "empty.txt", None, raw=b"\n\n")
        plan = self.plan()
        self.assertNotIn(("mag", "binary.txt"), plan)
        skipped = [json.loads(line) for line in
                   (self.root / "sieve" / "state" / "skipped.jsonl").read_text().splitlines()]
        self.assertEqual({s["path"] for s in skipped}, {"binary.txt", "empty.txt"})
        (self.root / "dedupe" / "out" / "mag" / "story-3.txt").unlink()
        (self.root / "dedupe" / "out" / "mag" / "story-4.txt").write_text("rewritten by a dedupe run\n")
        tally = self.apply()
        self.assertEqual(tally["missing"], 1)
        self.assertEqual(tally["stale"], 1)
        self.assertFalse((self.root / "sieve" / "out" / "fiction" / "mag" / "story-4.txt").exists())

    def test_a_second_run_is_refused_while_one_holds_the_lock(self):
        import os
        from store import Busy
        self.fill()
        state = self.root / "sieve" / "state"
        state.mkdir(parents=True, exist_ok=True)
        (state / "lock").write_text(f"{os.getppid()} 0\n")
        with self.assertRaises(Busy):
            self.plan()
        (state / "lock").write_text("999999 0\n")
        self.plan()

    def test_report_and_review_are_written(self):
        self.fill()
        self.plan()
        self.apply()
        cfg = self.cfg()
        reporter.run(cfg, say=self.said.append)
        reviewer.run(cfg, say=self.said.append)
        report = cfg.report_file.read_text(encoding="utf-8")
        self.assertIn("| anth | anthologies |", report)
        self.assertIn("summation", report)
        self.assertIn("best-1991.txt", report)
        review = cfg.review_file.read_text(encoding="utf-8")
        self.assertIn("cut opens:", review)
        self.assertIn("mag/talk.txt", review)
        first = cfg.review_file.read_bytes()
        reviewer.run(cfg, say=self.said.append)
        self.assertEqual(cfg.review_file.read_bytes(), first)

    def test_the_report_counts_fiction_words_exactly(self):
        self.fill()
        plan = self.plan()
        self.apply()
        cfg = self.cfg()
        expected = 0
        for (source, path), record in plan.items():
            if record["kind"] == "fiction":
                expected += len(self.out("fiction", source, path).split())
        by_source = reporter.tally(list(plan.values()))
        self.assertEqual(sum(s["fiction"] for s in by_source.values()), expected)


if __name__ == "__main__":
    unittest.main()
