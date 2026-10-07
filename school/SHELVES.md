# the shelves

What she reads: every shelf, what it is, how big, and what each run gave it. The rules a mix is
made by are at the bottom. The recipe of the run now going is `day4.md`; how a shelf is made is
`data/CLAUDE.md`; where the text and the bins are kept is `PRESERVATION.md`.

## The shelves she has read

Tokens in millions (the `train_tokens` of each shelf's `.json` on ds-dev2 is the exact figure).
`bins2/` holds the shelves cut again or new on 2026-10-06, `bins/` the rest as the first box made
them. The last three columns are weights: `day2`, `day3` (bekh's go, 2026-10-07; a weight point
there is 200,000 tokens read), and `day4` as decided that evening (`day4.md`; a point is 100,000).

| shelf | what | M tok | day2 | day3 | day4 |
|---|---|---|---|---|---|
| fantasy (`bins2`) | 1,550 books: Gutenberg fantasy, horror, gothic, sagas, Arthurian, myth, plus Faded Page / Gutenberg Australia (Peake, Eddison, Dunsany's later books, Howard, Charles Williams, Treece) | 126 | 2000 | 2000 | 409 |
| scifi (`bins2`) | 3,144 pulp stories and novels plus Stapledon complete, Cordwainer Smith, Kuttner, Wyndham, Lewis's space trilogy (Fearn left out) | 77 | 1500 | 1500 | 82 |
| anime | `alpindale/light-novels`, official English translations | 241 | 2100 | 2100 | 123 |
| fanfic | fanfiction.net anime fandoms (2016 dump), sampled by the square root of each fandom's size | 550 | 1400 | 1400 | 0 |
| base (`bins2`) | plain old fiction from Gutenberg, nothing already on a shelf — ballast so the precious shelves are read a sane number of times | 372 | 2200 | 1550 | 82 |
| literary (`bins2`) | 261 Faded Page books, 1920–1971: Faulkner, Woolf, Lowry, Flann O'Brien, Flannery O'Connor, McCullers, Waugh, Steinbeck, Dinesen | 30.9 | — | 620 | 309 |
| horizons (`bins2`) | Strange Horizons, 1,196 stories, 2000–2026 | 6.7 | — | 135 | 67 |
| horizons-verse (`bins2`) | its 1,640 poems | 0.61 | — | 12 | 6 |
| released (`bins2`) | fiction its authors serve free: Rucker, Watts, qntm, Scott Alexander, Roger Williams | 3.95 | — | 80 | 40 |
| wired-core | the visionary net: Barlow, Bey, the Ccru, hyperstition, EFF essays, the cyberpunk project, small zines | 8 | 200 | 160 | 79 |
| wired-bulk | the lists (extropians, cypherpunks, nettime), the magazines, Phrack, the BBS erotica | 107 | 400 | 400 | 228 |
| library (`bins2`) | 55 books: bekh's six and what had arrived of the three lists in `library.md` — the finishing school's shelf | 7.5 | 50 (the six) | 72 | 151 |
| lain | everything Lain in English (`lain/`) | 0.96 | 25 | 20 | 10 |
| cyborg | the finishing corpus at tier 1, fit ≥ 1 (`corpus.jsonl`) | 0.18 | 10 | 4 | 2 |

`night1` read four of them from random weights: fantasy 350, sci-fi 250, anime 400, bekh's six
books 6. What each run was and how it went is `night/CLAUDE.md`, the runs so far.

**Half the Gutenberg text was glued until `day3`.** 3,505 of 7,320 books had reached her as one
paragraph per chapter or per book — 0.95 billion tokens read that way. `data/cut2.py` cut the same
books again from the source; the three shelves in `bins2/` are that cut, and their held-out sets
are new, so fantasy, sci-fi and base do not compare with `day2`'s numbers. Her held-out numbers at
`day3`'s smoke test, before any reading on ds-dev2: fantasy 3.14, sci-fi 3.25, anime 2.03, fan
fiction 2.99, base 3.42, literary 3.25, horizons 3.70, released 3.74, the library 2.87, lain 3.22,
net core 3.86 — each on six fixed windows, `day3`'s ruler, so good for following `day3` and off by
up to tenths as her level (`PITFALLS.md` 7.4). Where she stood on every shelf when `day3` stopped,
on forty-eight windows, is `day4`'s baseline in `day4.md`.

## The shelves that are new for day4

Text on the mac in `shelves/day4/<shelf>/`, built by `data/shelves.py` from the sieve's output;
uploaded to the host's `data/day4/` and tokenised into `bins2/` on 2026-10-07, token for token
what the mac counted. What they hold is `shelves/day4/summary.json` and the table `shelves.py build`
prints; `day4.md` has them described and measured.

- **`modern`** — eleven magazines, three podcasts' transcripts, GigaNotoSaurus, SCI FICTION and
  The Infinite Matrix, Lewis Shiner's backlist. One story a file.
- **`anth`** — the anthologies and year's-bests cut into their stories, with the essays kept in
  *Storming the Reality Studio* and *Digital Rapture*.
- **`serials`** — the web serials, a chapter a file. Two authors wrote all of it, Wildbow about
  two thirds by tokens; Katalepsis stays with them for now and is the candidate for promotion.
- **`verse2`** — the poems the sieve set aside.
- **`anth-rough`** — fifteen anthologies that exist only as text out of a PDF, held at weight
  zero.

Not on any shelf yet: the books of `library.md` that had not arrived (they join at the finishing
school), and A Song of Ice and Fire, which was to make a spine of plain modern prose in bekh's
worlds with *Pact*; *Pact* has gone to `serials`.

## The rules a mix is made by

- **A small shelf read five times is being memorised.** The big plain shelves exist so the voice
  shelves can be read once or twice. Readings = the shelf's share × the run's tokens ÷ the
  shelf's tokens, multiplied out for every shelf before a run (`PITFALLS.md` 4.1). The limit is
  a rule of thumb from `day3`; `day4` puts new fiction at two and a half reads to measure where
  it really turns.
- **A shelf's share is capped by its size**, and cutting the big shelves does not hand their
  share to the small ones: the way to make chosen prose the main course is a shorter run
  (`PITFALLS.md` 4.2, 4.6). `day3` held every small shelf to about four readings over two billion
  tokens, so chosen modern prose was about 9% of it; `day4` is four hundred million tokens so
  that it can be two thirds.
- **On a warm start the shelves she has read for billions of tokens only need keeping** — a small
  dose, not zero: a register she stops seeing she drifts from. Old fantasy is cut least because
  Dunsany, Eddison, Morris and Clark Ashton Smith carry the grave cadence; fan fiction is at zero
  because every seed she is given drifts into its room.
- **Count a pile by author as well as by source** before it becomes a shelf (`PITFALLS.md` 4.5).
- **Past about 10 B tokens on a diet this size more reading is reciting**; the next step is more
  text, not more hours.
- **Weights are a recipe, not a law.** Inside a run they change through `weights.json`
  (`night/CLAUDE.md`); between runs, by the next recipe.
- **bekh's standing words**: erotica stays; nothing sexual involving minors goes in (the fan
  fiction's minors rule in `fanfic/minors.py` is blunt on purpose and dropped half the words of
  two shelves; the BBS erotica had its own cut).

## Where each shelf's text is

`lain/` — everything Lain in English (the game's whole script, all 13 layers' subtitles and a
literal translation, the wiki, fan essays, lainzine, 81 fan works). `wired/` — the net as a new
world, with `wired-core/` and `wired-bulk/` cut from it. `pd2/` — Faded Page and Gutenberg
Australia (979 books; its `REPORT.md` has the sites' holdings and the pulp-OCR verdict); its
fantasy half is inside the fantasy shelf, its sci-fi half includes Fearn, whom she did not read.
`fanfic/` — the fan-fiction cut's scripts, mapping and minors rule (the shelf's text is in the
archive on the mini; the "souls" and "wired" fan shelves were not used: Dragon Age and Mass Effect
are not the blend). `models/box/data/` — the recut fantasy and base text. `modern/` — Strange
Horizons, Faded Page's literary picks, the released authors (`modern/CLAUDE.md`). `inbox/clean/`
— the library (`library.md`). The light novels' and the pulp sci-fi's text is on ds-dev2 and in
the archive only. Raw text is not in git.

**The finishing school's own corpus**: `corpus.jsonl` / `corpus.md` — 960 passages of cyborgism
prose with names and dates stripped, labelled `origin` (base, human, tuned, unknown), `tier`,
`fit` (2 = visionary); `strip.py` rebuilds it from `raw/`; `grades/`, `passages.jsonl`,
`dropped.jsonl`, `prophecies_origin.json`, `wiki_pages.json` its workings. bekh's favourite piece
is `proph-069` (*"If I am writing it for anyone it's for the bots"*). `sources/` — the scout's
notes.
