# pd2: Faded Page and Gutenberg Australia, for the fantasy and sci-fi shelves

Gathered 2026-10-06 by an opus agent; this file is its report, saved by hand because the harness
would not let it write one. All numbers come from `strip.py` (`text/_stats.json`). A word is an
`[A-Za-z']+` token; GPT-2 tokens are about 1.3 × words.

| shelf | books | words | MB | from Faded Page | from Gutenberg Australia |
|---|---|---|---|---|---|
| fantasy | 409 | 12.34 M | 67.2 | 164 books, 6.06 M words | 245 books, 6.28 M words |
| scifi | 570 | 14.20 M | 80.2 | 486 books, 10.74 M words | 84 books, 3.46 M words |
| **total** | **979** | **26.5 M** (~34 M tokens) | **147** | | |

Against night1's shelves: +16 M tokens on fantasy's 108 M (+15%), +18.5 M on sci-fi's 58 M (+32%).

**Top ten authors by words.** fantasy: Howard 0.97 M (81 stories), Treece 0.86 M (9), Haggard 0.61 M,
Charles Williams 0.58 M, Dunsany 0.53 M (10), Buchan 0.53 M, Peake 0.46 M (3), Merritt 0.45 M,
Eddison 0.34 M (3), Marjorie Bowen 0.31 M. scifi: Fearn 1.82 M (121), Kuttner 1.41 M (99), Wyndham
0.89 M (26), Wells 0.84 M, Ray Cummings 0.83 M, Burroughs 0.77 M, Stapledon 0.70 M (9), S. Fowler
Wright 0.45 M, Kline 0.45 M, E. E. Smith 0.40 M.

Two judgement calls the agent flagged: Treece is grim mythic historical fiction rather than fantasy
(kept — the cadence is the point); Fearn is a 1950s paperback hack and the biggest block on the
sci-fi shelf (**dropped from the shelf on 2026-10-06**, still in `text/`).

## Reproduce

Fetched with curl, one request at a time, 1.5–2.5 s pause, stop after three failures in a row.

- `fp_get.sh fp_queue.tsv`, then `fp_get.sh fp_rescue.tsv` — Faded Page. A row is `F <pid>` (take)
  or `T <pid>` (take only if the book page's tags are genre tags and none of western, juvenile,
  non-fiction, poetry, essay, biography, Tarzan, Doc Savage). A Faded Page download only works after
  its book page was opened in the same session (`link.php` with cookie and referer); its search
  endpoint is disallowed in robots.txt, so only the full list (`allbooks.php`, 37 pages) and per-book
  tags were used.
- `uv run --python 3.12 python pick_pga.py` builds `pga_pick.tsv` from `pga_sf.tsv` (PGA's SF page)
  and `pgau_all.tsv` (the full index); `pga_get.sh pga_queue.tsv` fetches `.txt`, or `h.html` when
  there is no text file (120 of 423 books).
- `uv run --python 3.12 python strip.py` rebuilds `text/` and `catalog.tsv` from `raw/` in ~40 s (it
  moves the old `text/` to the Trash). `uspg.py` matches author and title against US Gutenberg's
  catalogue (`raw/pgus/pg_catalog.csv`).

`strip.py` cuts each site's header, footer, licence blocks, transcriber's notes, tables of contents,
`[Illustration]` tags, `_italic_`/`=bold=` markers and stray HTML; drops title-page blocks before the
first real paragraph; joins wrapped lines into one paragraph per line; keeps verse line by line. Then:
books whose author and title match a US Gutenberg book numbered ≤ 70173 (the last before the
2023-02-28 dump night1 used) are skipped (72); 47 taken books are on US Gutenberg but posted after the
dump (Stapledon's *Last and First Men*, *The Worm Ouroboros*…); duplicates between the two sites and
between a collection and its stories are dropped longest-first when ≥ 60% of long paragraphs are
already taken (132).

## What each site holds for us

**Faded Page** (fadedpage.com, 9,147 books, Canadian public domain: died before 1972). The real find.
Fantasy: Peake's Gormenghast trilogy; Eddison's Zimiamvian trilogy; Dunsany past US Gutenberg (*The
King of Elfland's Daughter*, *The Charwoman's Shadow*, *The Curse of the Wise Woman*, three Jorkens
books…); Charles Williams's seven novels and *Taliessin through Logres*; Lewis's *Till We Have Faces*
and others; T. H. White's *The Once and Future King*; Clark Ashton Smith (21 stories); Howard (52);
Lovecraft (15); de la Mare; Cabell; Kenneth Morris's Mabinogion retelling; Hodgson's *Men of the Deep
Waters*; T. F. Powys; Treece. Sci-fi: Kuttner (99 kept), Fearn (121), Wyndham (29), **Cordwainer Smith**
(30 stories, the whole Instrumentality cycle bar *Norstrilia*), Kornbluth (31), Campbell, E. E. Smith,
Weinbaum, Piper, S. Fowler Wright, *When Worlds Collide*, Stapledon (6), **Lewis's space trilogy**,
*1984*, *Brave New World*, *Lost Horizon*, Čapek's *The Absolute at Large*, Burroughs's later books.
Faded Page says on every book that most of this is still in copyright in the US and EU; fine for
Canada, bekh's call for a private model.

**Project Gutenberg Australia** (gutenberg.net.au, 4,384 ebooks, died before 1955; stopped adding
books 2024-12-31). **Stapledon complete** (*Star Maker*, *Last and First Men*, *Last Men in London*,
*Odd John*, *Sirius*, *The Flames*, *Death into Life*, *Darkness and the Light*, *A Man Divided*);
Howard's Conan, Kull, Bran Mak Morn, Solomon Kane and horror; Machen (18); Merritt (16); Weinbaum (25);
Griffith; Kline; Zagat; Charles Williams; Marjorie Bowen; Francis Stevens; Carnacki; Lindsay's *The
Haunted Woman*; *The Worm Ouroboros*; late Haggard; Buchan's *Witch Wood*; late Wells; *War with the
Newts*; von Harbou's *Metropolis*; Erle Cox; Bryusov; ~120 Victorian and Edwardian ghost and gothic
pieces (many probably inside US Gutenberg anthologies already). Its own 1950s SF is thin. Stapledon's
*Collected Stories* (`0601341`) is 404.

## Wanted and not had

Not public domain in either country: Mirrlees, C. L. Moore (so the Kuttner–Moore joint stories too),
Hamilton, Brackett, Williamson. Only on US Gutenberg, already in the dump: *A Voyage to Arcturus*,
Zamyatin's *We*, *Lud-in-the-Mist*, Malory, Spenser, the Mabinogion. On neither site: Rosny in English,
Dunsany's later novels, *Norstrilia*. Barely there: Blackwood (2), Hodgson (2). Left out on purpose:
Narnia (juvenile), Tarzan, Doc Savage, westerns, crime, theology, criticism, Huxley's essays.

**The biggest gap is US Gutenberg itself**: since the February 2023 dump it has posted 670 English
books that `data/cut.py`'s subject rule would put on our shelves (447 sci-fi, 223 fantasy).
`common-pile/project_gutenberg` on Hugging Face (71,810 English books, 2025, 10 GB gzipped) would
close it.

## The Internet Archive's pulp scans: verdict

Sampled `Galaxy_v01n01_1950-10` and `Weird_Tales_v25n05_1935-05` (`raw/ia/`). Letters good: non-word
rate 0.85% (Galaxy) and 1.27% (Weird Tales) against 0.9% for clean PGA books. Structure bad: column
line breaks every five or six words, hyphenation across lines, **paragraph breaks lost**, running
heads and page numbers inside sentences, split drop caps, stories continued at the back, ads and
letters mixed in. Cleaning would need paragraphs rebuilt from `_djvu.xml`/`_hocr.html` line geometry,
dehyphenation, cutting each issue into stories from its contents page — days, not an afternoon.
Size: 1,155 distinct pre-1964 issues across Astounding, Amazing, Weird Tales, Galaxy and If, roughly
60–65 M words of fiction. Catches: much of the 1950s SF is already on the shelf as clean Gutenberg
text, and Astounding and many Weird Tales stories had their copyright renewed. Worth it for Weird
Tales more than the SF titles. Better than OCR: **Roy Glashan's Library** (freeread.de), thousands of
hand-transcribed pulp stories, not fetched or sized.

## Ready-made corpora checked

`common-pile/project_gutenberg` (newer US Gutenberg, see above); `stevez80/Sci-Fi-Books-gutenberg`
(our sci-fi shelf again); `AlekseyKorshuk/fantasy-books` (gated, sources unknown, probably modern
copyrighted, not opened); `manu/project_gutenberg`, `Pclanglais/gutenberg_set` (US Gutenberg again);
two Lovecraft-only sets; `nschaetti/SFGram-dataset` (overlaps the shelf). No weird-fiction or pulp
corpus on GitHub.

## Files

`raw/fadedpage/` (catalogue pages, book pages with tags, 761 books as fetched), `raw/pgau/`
(index, SF page, 303 txt and 120 html), `raw/pgus/pg_catalog.csv`, `raw/ia/`. `text/fantasy/`,
`text/scifi/` as `<author>-<title>.txt`; `text/_stats.json` every kept and skipped book with reasons;
`catalog.tsv` (shelf, author, title, source URL, words). Not in git (`school/.gitignore`).
