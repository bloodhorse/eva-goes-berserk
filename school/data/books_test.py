import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import books

SENTENCES = [
    "She walked to the edge of the water and said that it was not the sea she had been told of.",
    "He had waited for them all night by the gate, and when they came out he was not there.",
    "There was a light in the tower that no one would own to, and it burned from dusk to morning.",
    "They said the road would be open by spring, but the snow was still on it when we set out.",
    "I have been in that house, and I would not go into it again for all the silver in the north.",
]


def prose(tag, words):
    out, n, k = [], 0, 0
    while n < words:
        s = f"{SENTENCES[k % len(SENTENCES)]} The {tag} of it was {k} and no more."
        out.append(f"<p>{s} {s}</p>")
        n += 2 * len(s.split())
        k += 1
    return "\n".join(out)


def page(body, attrs=""):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
            f'xmlns:epub="http://www.idpf.org/2007/ops"><head><title>x</title></head><body{attrs}>{body}</body></html>')


def make_epub(path, title, author, pages):
    items = "".join(f'<item id="i{k}" href="{name}" media-type="application/xhtml+xml"/>' for k, (name, _) in enumerate(pages))
    refs = "".join(f'<itemref idref="i{k}"/>' for k in range(len(pages)))
    opf = ('<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f'<dc:title>{title}</dc:title><dc:creator>{author}</dc:creator><dc:language>en</dc:language></metadata>'
           f'<manifest>{items}</manifest><spine>{refs}</spine></package>')
    container = ('<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">'
                 '<rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", container)
        z.writestr("content.opf", opf)
        for name, html in pages:
            z.writestr(name, html)


def story_with_notes(tag, words):
    return page(f'<h1>{tag.upper()} STORY</h1>{prose(tag, words)}'
                f'<p>The {tag} word<a epub:type="noteref" href="#n1">*1</a> stood alone in the line.</p>'
                '<div epub:type="footnotes"><p>Skip Notes</p>'
                f'<div epub:type="footnote" id="n1"><p>marginalia{tag} is the gloss of a translator and not the tale.</p></div></div>')


def convert(src_dir, out_dir, *flags):
    with mock.patch.object(sys, "argv", ["books.py", str(src_dir), "--out", str(out_dir), *flags]), \
            mock.patch("builtins.print"):
        books.main()
    return {r["source"]: r for r in books.load_ledger(Path(out_dir) / "ledger.jsonl")}


class FootnoteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src = Path(self.tmp.name) / "src"
        self.out = Path(self.tmp.name) / "out"
        self.src.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def book(self):
        make_epub(self.src / "Some Editor - The Wide Anthology.epub", "The Wide Anthology", "Some Editor", [
            ("c01.xhtml", page(f"<h1>PLAIN STORY</h1>{prose('plain', 900)}")),
            ("c02.xhtml", story_with_notes("glossed", 900)),
            ("c03.xhtml", page(f"<h1>LAST STORY</h1>{prose('last', 900)}")),
            ("notes.xhtml", page('<section epub:type="endnotes" role="doc-endnotes"><h1>Sources</h1>'
                                 f'{prose("apparatus", 400)}</section>')),
        ])
        return convert(self.src, self.out)["Some Editor - The Wide Anthology.epub"]

    def test_story_with_a_footnote_block_is_kept(self):
        rec = self.book()
        text = (self.out / f"{rec['slug']}.txt").read_text()
        self.assertIn("GLOSSED STORY", text)
        self.assertIn("The glossed of it was 3 and no more.", text)
        self.assertIn("c02.xhtml", [k["file"] for k in rec["sections_kept"]])
        self.assertFalse([d for d in rec["sections_dropped"] if d["file"] == "c02.xhtml"])

    def test_the_notes_themselves_go(self):
        rec = self.book()
        text = (self.out / f"{rec['slug']}.txt").read_text()
        self.assertNotIn("marginaliaglossed", text)
        self.assertNotIn("Skip Notes", text)
        self.assertNotIn("*1", text)
        self.assertIn("The glossed word stood alone in the line.", text)

    def test_a_section_that_is_all_notes_goes_whole(self):
        rec = self.book()
        text = (self.out / f"{rec['slug']}.txt").read_text()
        self.assertNotIn("apparatus", text)
        dropped = {d["file"]: d["reason"] for d in rec["sections_dropped"]}
        self.assertIn("endnotes", dropped["notes.xhtml"])

    def test_types_come_from_what_holds_the_section(self):
        soup = books.BeautifulSoup(story_with_notes("glossed", 300), "lxml")
        self.assertFalse(books.epub_types(soup) & books.NOTE_TYPES)
        whole = books.BeautifulSoup(page('<section epub:type="backmatter endnotes"><p>one note and another</p></section>'), "lxml")
        self.assertIn("endnotes", books.epub_types(whole))
        cover = books.BeautifulSoup(page('<div epub:type="cover"><img src="c.jpg"/></div>'), "lxml")
        self.assertIn("cover", books.epub_types(cover))

    def test_note_types_match_whole_tokens(self):
        soup = books.BeautifulSoup(page('<section epub:type="bodymatter chapter"><p role="doc-footnote">gone</p>'
                                        '<p epub:type="z3998:verse">stays here</p>'
                                        '<span role="doc-pagebreak">12</span><p>and this stays too</p></section>'), "lxml")
        books.preclean(soup)
        text = soup.get_text(" ")
        self.assertNotIn("gone", text)
        self.assertNotIn("12", text)
        self.assertIn("stays here", text)
        self.assertIn("and this stays too", text)

    def test_a_first_line_cannot_drop_a_long_file(self):
        make_epub(self.src / "Some Writer - The Long Night.epub", "The Long Night", "Some Writer", [
            ("p1.xhtml", page(f"<h1>Acknowledgements</h1><p>Thanks to all of them.</p>{prose('opening', 6000)}")),
            ("p2.xhtml", page(prose("middle", 3000))),
            ("p3.xhtml", page(f"<h1>Acknowledgements</h1>{prose('thanked', 300)}")),
        ])
        rec = convert(self.src, self.out)["Some Writer - The Long Night.epub"]
        text = (self.out / f"{rec['slug']}.txt").read_text()
        self.assertIn("The opening of it was 5 and no more.", text)
        self.assertNotIn("thanked", text)
        self.assertTrue(any("reads as acknowledgements" in w for w in rec["warnings"]))


class SlugTest(unittest.TestCase):
    def test_library_slugs_stand(self):
        for title, author, slug in [
            ("Night's Master", "Tanith Lee", "lee-night-s-master"),
            ("Cugel's Saga", "Jack Vance", "vance-cugel-s-saga"),
            ("Books of Blood Volume Three", "Barker, Clive", "barker-books-of-blood-volume"),
            ("The Tombs of Atuan", "Ursula K. Le Guin", "le-guin-tombs-of-atuan"),
            ("Do Androids Dream of Electric Sheep?", "Dick, Philip K.", "dick-do-androids-dream-of"),
            ("The Dancers at the End of Time 03.azw3", "Michael Moorcock", "moorcock-dancers-at-the-end"),
            ("THE FALL OF HYPERION", "Dan Simmons", "simmons-fall-of-hyperion"),
        ]:
            self.assertEqual(books.book_slug(title, author), slug)

    def test_library_ledger_slugs_stand(self):
        ledger = Path(__file__).resolve().parent.parent / "inbox" / "clean" / "ledger.jsonl"
        if not ledger.exists():
            self.skipTest("no library ledger here")
        for r in books.load_ledger(ledger):
            if r.get("status") in ("ok", "duplicate"):
                self.assertEqual(books.book_slug(r["title"], r["author"]), r["slug"])

    def test_an_annual_carries_its_year(self):
        a = books.book_slug("The Year's Best Science Fiction: Eighth Annual Collection", "Gardner Dozois", 1990)
        b = books.book_slug("The Year’s Best Science Fiction", "Dozois, Gardner", 1990)
        self.assertEqual(a, "dozois-year-s-best-science-1990")
        self.assertEqual(a, b)

    def test_an_annual_without_a_summation_carries_its_number(self):
        self.assertEqual(books.book_slug("The Year's Best Science Fiction: Twenty-Third Annual Collection", "Gardner Dozois"),
                         "dozois-year-s-best-science-23")

    def test_annual_number(self):
        for s, n in [("Eighth Annual Collection", 8), ("twenty fourth annual collection", 24),
                     ("Twenty-First Annual Collection", 21), ("THIRTIETH ANNUAL COLLECTION", 30),
                     ("15th Annual Collection", 15), ("Nineteenth Annual Collection", 19),
                     ("the second annual meeting of the lodge", None), ("Ubik", None)]:
            self.assertEqual(books.annual_number(s), n)

    def test_summation_year(self):
        self.assertEqual(books.summation_year(["cover", "SUMMATION:\n1995\nNineteen ninety-five seemed"]), 1995)
        self.assertEqual(books.summation_year(["Introduction -\nSummation: 2002"]), 2002)
        self.assertEqual(books.summation_year(["Summation 2008"]), 2008)
        self.assertIsNone(books.summation_year(["in summation: 12 of them were lost", "Impulse-summation"]))

    def test_the_year_reaches_the_slug_and_the_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / "src", Path(tmp) / "out"
            src.mkdir()
            name = "Some Editor - The Year's Best Odd Fiction_ Fourth Annual Collection.epub"
            make_epub(src / name, "The Year's Best Odd Fiction: Ninth Annual Collection", "Some Editor", [
                ("s.xhtml", page(f"<h1>SUMMATION: 1991</h1>{prose('year', 500)}")),
                ("c01.xhtml", page(f"<h1>FIRST STORY</h1>{prose('first', 2500)}")),
                ("c02.xhtml", page(f"<h1>SECOND STORY</h1>{prose('second', 2500)}")),
            ])
            rec = convert(src, out)[name]
            self.assertEqual(rec["slug"], "editor-year-s-best-odd-1991")
            self.assertEqual(rec["year"], 1991)
            self.assertTrue((out / "editor-year-s-best-odd-1991.txt").exists())
            self.assertTrue(any("file name says annual 4" in w for w in rec["warnings"]))
            again = convert(src, out, "--force")[name]
            self.assertEqual(again["slug"], rec["slug"])
            self.assertEqual(len(books.load_ledger(out / "ledger.jsonl")), 1)

    def test_one_page_repeated_is_called_broken(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / "src", Path(tmp) / "out"
            src.mkdir()
            sorry = page("<p>sorry something went wrong loading your content, check the table of contents</p>")
            make_epub(src / "Some Editor - Broken.epub", "Broken Book", "Some Editor",
                      [("c00.xhtml", page(f"<h1>ONLY STORY</h1>{prose('only', 6000)}"))]
                      + [(f"c{k:02d}.xhtml", sorry) for k in range(1, 8)])
            rec = convert(src, out)["Some Editor - Broken.epub"]
            self.assertTrue(any("a broken file" in w for w in rec["warnings"]))


if __name__ == "__main__":
    unittest.main()
