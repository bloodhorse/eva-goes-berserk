## Where to get more text: ChatGPT's answer, and what came of it

The question was `docs/brief-text-sources.md` (2026-10-07), put to ChatGPT by bekh after
`text-sources-2026-10-06.md` had found no bulk source of modern strange prose. This is what its
answer added, what in it did not hold, and what each lead turned into by the end of the same day.
Token figures are from `school/dedupe/report.md` as it stood that evening (words × 1.39, after
deduplication, before the kind sieve); the report is the living number.

### What it added that held up

| lead | what it is | what it turned into |
|---|---|---|
| **Lewis Shiner, Fiction Liberation Front** (fictionliberationfront.net) | An author's whole backlist released by himself: seven novels (*Frontera*, *Deserted Cities of the Heart*, *Glimpses*, *Slam*, *Say Goodbye*, *Black & White*, *Dark Tangos*) and 68 stories, CC BY-NC-ND 3.0 by the site's manifesto. Robots open with a ten-second crawl delay. | `school/modern/released/shiner/`, 75 works, 1.35 M tokens. Novels are PDF only. |
| **Dead magazines through the Wayback Machine** | Ellen Datlow's SCI FICTION (scifi.com, 2000–2005), The Infinite Matrix (2001–2006), Subterranean Online (2007–2014). The sites are gone; the archive is the only copy. | `school/modern/wayback/`: SCI FICTION complete, 222 originals of 222 in its index plus 36 reprints first published after 1969 and a 118-piece series, 3.4 M tokens. The Infinite Matrix, 197 pieces of which 32 are full stories, 0.4 M. Subterranean enumerated, not fetched. |
| **GigaNotoSaurus** | One long story a month since 2010 (5,000–25,000 words). Robots open, a WordPress API. | `school/modern/giganotosaurus/`, 180 stories, 2.55 M tokens. Its archive carries injected spam in about sixty stories (`school/PITFALLS.md` 2.11). |
| **The reading of CC BY-NC-ND 4.0** | Section 2(a)(1) lets a licensee "produce and reproduce, but not Share, Adapted Material" for non-commercial purposes: private adaptation is permitted and only sharing the adapted material is not. This applies to 4.0 and is not to be read back into 3.0 releases. Relevant to Escape Pod, PodCastle and PseudoPod, whose site text is under 4.0. | The three podcasts' transcripts are in the pile: 9.3 M tokens surviving of 11.2 M, the rest being stories already held from the magazines. |
| **The anthology as the unit** | "One fat anthology" against one novel: a year's-best is about 300k words, edited, many writers. It named Dozois's *Year's Best Science Fiction*, Datlow and Windling's *Year's Best Fantasy and Horror*, the VanderMeers' retrospectives. | The fetch list `~/tower/ephemeral/booox/books.txt` (103 books) and the shelf `school/inbox/anth/`: 38 books converted that day, 11.2 M tokens surviving of 14.2 M, a fifth being stories also held as magazine pages. |
| **Two indexes** | Free Speculative Fiction Online (freesfonline.net) as a finder of authorised stories scattered over author sites; the ED SF Project's list of SCI FICTION's stories. | The second was used to tell SCI FICTION's originals from its reprints. |

### What did not hold

- **The headline number.** "Another 30–50M tokens of relevant professional fiction in magazine
  archives" was a sizing of Clarkesworld, Lightspeed, Uncanny, Nightmare and Beneath Ceaseless
  Skies — five of the sources the brief had listed as already known. The estimates themselves
  were close: those five came to 37.9 M tokens.
- **Infinity Plus as the first thing to look at.** Its content is as described (the site still
  states 2.1 million words of fiction; Harrison, Wolfe, Egan, VanderMeer, Swanwick), many
  entries being extracts from novels and some of the work older than 1970. Its robots.txt names
  the AI crawlers with `Disallow: /`, which the answer did not mention.
- **Beneath Ceaseless Skies' position.** Described as "training permission unestablished". Its
  robots.txt is open to `*`; every response carries `X-Robots-Tag: noai`; its submissions page
  has a paragraph against generative AI. About 1,011 stories in 467 issues.
- **Weightless Books as "a particularly good shop for this project".** Its FAQ states a position
  against AI in art and writing.
- **Offered and not wanted**: the SCP wiki (the brief had said so; the answer added the
  Wanderers' Library, CC BY-SA 3.0, a different and more fable-shaped site that nobody here has
  read), Baen's free library and old promotional discs (the answer itself calls them a weak
  fit), Created by Humans (licensing for companies; no price for a project this size).
- **Not followed up**: Small Beer Press's four Creative Commons collections (Link's *Stranger
  Things Happen*, McHugh, Kessel, Rosenbaum; about half a million tokens), Lightspeed's and
  Nightmare's yearly ebook bundles, StoryBundle.

### What the pile is, by kind

From the same evening's report, incoming text only, surviving deduplication:

| kind | sources | M tokens |
|---|---|---|
| magazines | Clarkesworld, Lightspeed, Beneath Ceaseless Skies, Apex, Uncanny, Nightmare, The Dark, Infinity Plus, Fantasy, Fireside, The Deadlands, GigaNotoSaurus | 55.8 |
| podcast transcripts | Escape Pod, PodCastle, PseudoPod | 9.3 |
| anthologies and annuals | 38 books | 11.2 |
| web serials | Worm, Ward, Pact, Pale, Twig (Wildbow); Katalepsis, Necroepilogos | 18.1 |
| released and recovered | Shiner, SCI FICTION, The Infinite Matrix | 4.7 |
| **all** | | **99.1** |

Against about 17 M tokens of modern edited prose on her shelves before it (the library, Strange
Horizons, the released authors). Twelve of the magazine and podcast folders, and the serials,
were gathered by bekh's collector in `shelf/gpt/` (its `README.md`); the rest by fetchers under
`school/modern/` and by hand.

Two measurements the survey of the day before could only guess at. Magazines duplicate each
other very little — about 1% — because they publish originals and reprint from print. The
duplication is in the podcasts (a sixth) and the anthologies (a fifth, rising as more magazines
are held). And part of every magazine folder is not fiction: roughly a quarter of Apex's files
are interviews and reviews, a third of The Deadlands' are poems.
