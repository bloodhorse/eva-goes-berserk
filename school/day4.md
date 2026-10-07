# day4 — the recipe

A warm start from `day3`'s final save: short, dense, the new modern fiction as the main course,
the big old shelves on a maintenance dose. An experiment — a somewhat inflated character is
acceptable, and `day3`'s final save is the fallback. The hands are `night/day4-RUN.md`; this file
is the numbers and their reasons. Three marks run through it: **decided** (bekh with the session,
2026-10-07, not reopened here), **proposed** (the recipe writer's, waiting for his yes), **guess**
(nobody knows; the run measures it).

Nothing here has run. The sizes of the new shelves are from `shelves/day4/summary.json`
(sha256 `96f77d3346318ef0dac8eb8198fad6b422ac076301b1fcddb955f5672830c711`), made by `data/shelves.py build --deep` from the sieve's plan of
2026-10-07 21:05:06; the old shelves' are the `train_tokens` of their `.json` on ds-dev2.

## What a weight is

`train.py` builds every batch row by row: for each of the 6 rows of each of the 4 micro-batches
of a step it draws a shelf with probability *weight ÷ sum of weights*, then a random offset in
that shelf's token file, and reads 1,024 tokens from there. So a weight is a sampling
probability per row; a shelf's **share** of the run is its weight over the sum; its
**token-reads** are share × the run's tokens; its **reads** are token-reads ÷ its size. Three
things follow:

- **Document order does not matter.** Offsets are random, with replacement; nothing is read in
  sequence, so the shelves are not shuffled (a window does run across the end-of-document
  marker into whatever file sorts next — a sliver of the text).
- **One read is not one pass.** At 1.0 reads about 63% of a shelf's tokens have been seen at
  least once (1 − e⁻¹), at 2.5 about 92%, at 4 about 98%; the rest of the budget went to
  repeats.
- **A weight of zero is legal** and keeps the shelf's held-out number in the log (checked on
  torch 2.14.1, the host's version): fan fiction stays on the line at 0, so the run measures
  what a register does when it is fed nothing.

The weights below sum to 4,092, so **one weight point is 100,000 tokens read** and a weight
divided by ten is millions of tokens.

## The shelves

Old shelves, as `day3` reads them (`school/CLAUDE.md` has what each is): `bins/` and `bins2/` on
ds-dev2, sizes below. The new ones are text on the mac in `shelves/day4/<shelf>/`
(`train/` and `heldout/`, one work a file; `manifest.jsonl`, `heldout.txt`), to be tokenised into
`bins2/` by the runbook:

- **`modern`** — the magazines (Apex, Beneath Ceaseless Skies, Clarkesworld, The Dark, The
  Deadlands, Fantasy, Fireside, Infinity Plus, Lightspeed, Nightmare, Uncanny), the three
  podcasts' transcripts (Escape Pod, PodCastle, PseudoPod), GigaNotoSaurus, SCI FICTION and The
  Infinite Matrix out of the Wayback Machine, and Lewis Shiner's backlist. One story a file.
- **`anth`** — the anthologies and year's-bests, **cut into their stories** along the sieve's
  section boundaries (a book whose cuts do not rebuild the sieve's output byte for byte stays
  whole), with the essays kept in *Storming the Reality Studio* and *Digital Rapture* travelling
  with their books. Apart from `modern` on purpose: other editors' taste in bulk, print-magazine
  fiction of 1990–2016 and a tail of much older stories, a fifth of it already cut away as
  duplicates — a different population, and it gets its own held-out number. **proposed**
- **`serials`** — the web serials, a chapter a file (*Pact*, which arrived as one file, is cut at
  its chapter headings). Two authors: Wildbow 75% of the tokens (Worm, Ward, Twig,
  Pale, Pact), HY the rest (Katalepsis, Necroepilogos), two chapters of The Wandering Inn.
  **decided**: their own shelf, read about once. Katalepsis is the candidate for promotion into
  the new fiction — first-person, slow, strange, the nearest of the eight to the blend; not done
  here.
- **`verse2`** — the poems the sieve set aside (Apex, The Deadlands and three strays). **decided**:
  poems are in.
- **`anth-rough`** — the anthologies that exist only as text pulled out of a PDF, **at weight
  zero**; see *For bekh's decision* below.

| shelf | text | works | files | train tokens | held-out tokens | largest source or author |
|---|---|---:|---:|---:|---:|---|
| modern | `shelves/day4/modern/` | 9,894 | 9,787 + 107 | 70,694,476 | 656,391 | clarkesworld 17%; (unknown) 5% |
| anth | `shelves/day4/anth/` | 1,475 | 1,428 + 47 | 17,081,565 | 655,811 | anth 100%; Gardner Dozois 24% |
| serials | `shelves/day4/serials/` | 1,803 | 1,768 + 35 | 20,085,628 | 428,861 | pale 29%; Wildbow 68% |
| verse2 | `shelves/day4/verse2/` | 239 | 211 + 28 | 97,674 | 9,466 | apex 50%; (unknown) 49% |
| anth-rough | `shelves/day4/anth-rough/` | 15 | 15 + 0 | 6,442,951 | 0 | anth 100%; Ellen Datlow 69% |

**Tokens a word, measured.** The session had been multiplying words by 1.39. With her tokenizer
(GPT-2's, `models/bins/fantasy.tokenizer/`, every file counted whole, chunked and closed the way
`prep.py` does it):

| shelf | works | words | tokens | tokens a word | 1.39 was low by |
|---|---:|---:|---:|---:|---:|
| modern | 9,894 | 49,125,453 | 71,350,867 | 1.452 | 4.5% |
| anth | 1,475 | 12,220,408 | 17,737,376 | 1.452 | 4.4% |
| serials | 1,803 | 12,941,685 | 20,514,489 | 1.585 | 14.0% |
| verse2 | 239 | 69,500 | 107,140 | 1.542 | 10.9% |
| anth-rough | 15 | 4,463,218 | 6,442,951 | 1.444 | 3.9% |
| **all** | 13,426 | 78,820,264 | 116,152,823 | 1.474 | 6.0% |

By source, the spread inside `modern` and `serials`: infinityplus 1.35, wayback 1.37, pseudopod 1.42, thedark 1.43, nightmare 1.43, deadlands 1.43, released/shiner 1.44, lightspeed 1.45, fantasy 1.45, apex 1.46, clarkesworld 1.47, bcs 1.47, podcastle 1.47, uncanny 1.47, fireside 1.48, modern/giganotosaurus 1.49, escapepod 1.50, worm 1.53, twig 1.55, katalepsis 1.57, ward 1.58, necroepilogos 1.58, released/wildbow 1.60, pale 1.63.

The counter was checked against two shelves ds-dev2 has already tokenised: it gives 7,606,227
for the library and 6,793,597 for Strange Horizons, the host's train plus held-out to the token.
The 1.39 itself was a slip — the library's *training* tokens over all its words; the library is
1.406. Modern magazine prose runs higher than old books because more of its words are split
(invented names, coinages): 0.28 continuation tokens a word in Clarkesworld against 0.22 in the
library, 0.35–0.40 in the serials, which also break a paragraph every fifteen words.

## For bekh's decision: the rough anthologies

15 books, 4,463,218 words, **6,442,951 tokens**: the Datlow and Windling *Year's Best Fantasy and Horror* annuals and *Semiotext(e) SF*, picked out by their ledger line (`inbox/anth/ledger.jsonl`: format `pdf`, or the converter's PDF warning), not by name. One paragraph a page, running heads fused into sentences, letter-spaced OCR; `health.py` passes them (its glue alarm is a 20,000-character paragraph, a page is 3,000), and the sieve could not cut them into stories, so each still carries its Summation, its honorable mentions and every editor's note. They are whole books in `shelves/day4/anth-rough/`, with no held-out set, **on the `--data` line at weight 0**: nothing is read from them, and with the new trainer a yes is one line in `weights.json` at any eval.

What a yes would add at one read: 6.4 M tokens, a weight of 64, 1.6% on top of the run (262 steps, 9 minutes) or the same taken out of old fantasy — fourteen more years of late-eighties-to-2004 fantasy and horror, the one register of the pile that is closest to the old fantasy shelf, at the price of teaching her page-shaped paragraphs and running heads. The recipe writer's view: no for day4; they are worth an epub fetch or a de-paging pass, and then they are a third of the anthology shelf again.

*Digital Rapture* (also out of a PDF) is wanted for its essays and stays in `anth`, whole; the PDF copy of *The Big Book of Cyberpunk* is redundant beside the epub and is in no shelf (the sieve files it as non-fiction).

## The recipe, multiplied out

**decided**: the shape — new fiction about half at about 2.5 reads; library, Strange Horizons
and the released authors about 2 reads; the 1920–71 literary shelf and the serials about 1; the
net shelves and verse about 8%; old fantasy about 10%, down but not out; light novels about 3%;
pulp sci-fi and base about 4% together; fan fiction 0.
**proposed**: everything the shape leaves open, which is: the run's exact length (409 million tokens rather than 400 — at the measured sizes, and with the anthologies that arrived on the evening of 2026-10-07, the agreed reads and the agreed shares of the old shelves only fit together in a run that long; held to 400 million exactly, the new fiction would get 2.42 reads instead of 2.5);
the split inside the net group (the small ones at one read each — the visionary core, Lain, the
cyborg corpus and the Strange Horizons poems have four reads behind them from `day3` — the new
poems at two, the bulk taking the rest of the 8%); pulp sci-fi and base at 2% each; and where the
remainder went (nowhere: there is none, the shares are the agreed ones to the rounding of a weight point).

| shelf | what | bin | train tokens | weight | share | token-reads | reads | read in day3 | lifetime |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| fantasy | old fantasy, horror, gothic, myth | `bins2/fantasy.bin` | 126,216,244 | 409 | 10.00% | 40.9 M | 0.32 | 3.26 | 3.58 |
| scifi | pulp sci-fi | `bins2/scifi.bin` | 76,909,682 | 82 | 2.00% | 8.2 M | 0.11 | 4.01 | 4.12 |
| anime | light novels | `bins/anime.bin` | 241,196,917 | 123 | 3.01% | 12.3 M | 0.05 | 1.79 | 1.84 |
| fanfic | anime fan fiction | `bins/fanfic.bin` | 550,111,074 | 0 | 0.00% | 0.0 M | 0.00 | 0.52 | 0.52 |
| base | plain Gutenberg fiction | `bins2/base.bin` | 371,690,264 | 82 | 2.00% | 8.2 M | 0.02 | 0.86 | 0.88 |
| wired-core | the visionary net | `bins/wired-core.bin` | 7,858,741 | 79 | 1.93% | 7.9 M | 1.01 | 4.19 | 5.19 |
| wired-bulk | the lists, zines, BBS | `bins/wired-bulk.bin` | 107,067,581 | 228 | 5.57% | 22.8 M | 0.21 | 0.77 | 0.98 |
| literary | 1920–71 literary | `bins2/literary.bin` | 30,892,390 | 309 | 7.55% | 30.9 M | 1.00 | 4.13 | 5.13 |
| horizons | Strange Horizons stories | `bins2/horizons.bin` | 6,732,435 | 135 | 3.30% | 13.5 M | 2.01 | 4.12 | 6.13 |
| released | author-released fiction | `bins2/released.bin` | 3,953,465 | 79 | 1.93% | 7.9 M | 2.00 | 4.16 | 6.16 |
| library | bekh's library | `bins2/library.bin` | 7,530,165 | 151 | 3.69% | 15.1 M | 2.01 | 1.97 | 3.97 |
| lain | everything Lain | `bins/lain.bin` | 955,926 | 10 | 0.24% | 1.0 M | 1.05 | 4.30 | 5.35 |
| cyborg | the finishing corpus | `bins/cyborg.bin` | 182,957 | 2 | 0.05% | 0.2 M | 1.09 | 4.50 | 5.59 |
| horizons-verse | Strange Horizons poems | `bins2/horizons-verse.bin` | 610,810 | 6 | 0.15% | 0.6 M | 0.98 | 4.04 | 5.02 |
| modern | new: magazines, podcasts, small shelves | `bins2/modern.bin` | 70,694,476 | 1767 | 43.18% | 176.7 M | 2.50 | 0.00 | 2.50 |
| anth | new: anthologies, by story | `bins2/anth.bin` | 17,081,565 | 427 | 10.43% | 42.7 M | 2.50 | 0.00 | 2.50 |
| serials | new: web serials, by chapter | `bins2/serials.bin` | 20,085,628 | 201 | 4.91% | 20.1 M | 1.00 | 0.00 | 1.00 |
| verse2 | new: the sieve's poems | `bins2/verse2.bin` | 97,674 | 2 | 0.05% | 0.2 M | 2.05 | 0.00 | 2.05 |
| anth-rough | new: PDF-derived anthologies, out | `bins2/anth-rough.bin` | 6,442,951 | 0 | 0.00% | 0.0 M | 0.00 | 0.00 | 0.00 |
| **all** | | | 1,646,310,945 | **4092** | **100.00%** | **409.2 M** | | | |

| group | weight | share | token-reads | reads |
|---|---:|---:|---:|---:|
| new fiction (`modern` + `anth`) | 2194 | 53.6% | 219.4 M | 2.50 |
| library + Strange Horizons + released | 365 | 8.9% | 36.5 M | 2.00 |
| 1920–71 literary | 309 | 7.6% | 30.9 M | 1.00 |
| serials | 201 | 4.9% | 20.1 M | 1.00 |
| net shelves + verse | 327 | 8.0% | 32.7 M | 0.28 |
| old fantasy | 409 | 10.0% | 40.9 M | 0.32 |
| light novels | 123 | 3.0% | 12.3 M | 0.05 |
| pulp sci-fi + base | 164 | 4.0% | 16.4 M | 0.04 |
| fan fiction | 0 | 0.0% | 0.0 M | 0.00 |
| **sum** | **4092** | **100.0%** | **409.2 M** | |

```
MIX="bins2/fantasy.bin:409 bins2/scifi.bin:82 bins/anime.bin:123 bins/fanfic.bin:0 bins2/base.bin:82 bins/wired-core.bin:79 bins/wired-bulk.bin:228 bins2/literary.bin:309 bins2/horizons.bin:135 bins2/released.bin:79 bins2/library.bin:151 bins/lain.bin:10 bins/cyborg.bin:2 bins2/horizons-verse.bin:6 bins2/modern.bin:1767 bins2/anth.bin:427 bins2/serials.bin:201 bins2/verse2.bin:2 bins2/anth-rough.bin:0"
STEPS=16650
```

*read in day3* is the same arithmetic on `run3.sh`'s weights over its 84,103 steps; *lifetime*
adds the two (and leaves out `night1` and `day2`, which read fantasy, sci-fi and the light novels
a further one to three times and the net shelves under one).

**The variant at 4 reads of the new fiction** — every other shelf reads exactly the tokens it
reads in the main plan, only `modern` and `anth` grow, and the run grows with them:

| shelf | what | bin | train tokens | weight | share | token-reads | reads | read in day3 | lifetime |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| fantasy | old fantasy, horror, gothic, myth | `bins2/fantasy.bin` | 126,216,244 | 409 | 7.56% | 40.9 M | 0.32 | 3.26 | 3.58 |
| scifi | pulp sci-fi | `bins2/scifi.bin` | 76,909,682 | 82 | 1.52% | 8.2 M | 0.11 | 4.01 | 4.12 |
| anime | light novels | `bins/anime.bin` | 241,196,917 | 123 | 2.27% | 12.3 M | 0.05 | 1.79 | 1.84 |
| fanfic | anime fan fiction | `bins/fanfic.bin` | 550,111,074 | 0 | 0.00% | 0.0 M | 0.00 | 0.52 | 0.52 |
| base | plain Gutenberg fiction | `bins2/base.bin` | 371,690,264 | 82 | 1.52% | 8.2 M | 0.02 | 0.86 | 0.88 |
| wired-core | the visionary net | `bins/wired-core.bin` | 7,858,741 | 79 | 1.46% | 7.9 M | 1.01 | 4.19 | 5.19 |
| wired-bulk | the lists, zines, BBS | `bins/wired-bulk.bin` | 107,067,581 | 228 | 4.22% | 22.8 M | 0.21 | 0.77 | 0.98 |
| literary | 1920–71 literary | `bins2/literary.bin` | 30,892,390 | 309 | 5.71% | 30.9 M | 1.00 | 4.13 | 5.13 |
| horizons | Strange Horizons stories | `bins2/horizons.bin` | 6,732,435 | 135 | 2.50% | 13.5 M | 2.01 | 4.12 | 6.13 |
| released | author-released fiction | `bins2/released.bin` | 3,953,465 | 79 | 1.46% | 7.9 M | 2.00 | 4.16 | 6.16 |
| library | bekh's library | `bins2/library.bin` | 7,530,165 | 151 | 2.79% | 15.1 M | 2.01 | 1.97 | 3.97 |
| lain | everything Lain | `bins/lain.bin` | 955,926 | 10 | 0.18% | 1.0 M | 1.05 | 4.30 | 5.35 |
| cyborg | the finishing corpus | `bins/cyborg.bin` | 182,957 | 2 | 0.04% | 0.2 M | 1.09 | 4.50 | 5.59 |
| horizons-verse | Strange Horizons poems | `bins2/horizons-verse.bin` | 610,810 | 6 | 0.11% | 0.6 M | 0.98 | 4.04 | 5.02 |
| modern | new: magazines, podcasts, small shelves | `bins2/modern.bin` | 70,694,476 | 2828 | 52.28% | 282.8 M | 4.00 | 0.00 | 4.00 |
| anth | new: anthologies, by story | `bins2/anth.bin` | 17,081,565 | 683 | 12.63% | 68.3 M | 4.00 | 0.00 | 4.00 |
| serials | new: web serials, by chapter | `bins2/serials.bin` | 20,085,628 | 201 | 3.72% | 20.1 M | 1.00 | 0.00 | 1.00 |
| verse2 | new: the sieve's poems | `bins2/verse2.bin` | 97,674 | 2 | 0.04% | 0.2 M | 2.05 | 0.00 | 2.05 |
| anth-rough | new: PDF-derived anthologies, out | `bins2/anth-rough.bin` | 6,442,951 | 0 | 0.00% | 0.0 M | 0.00 | 0.00 | 0.00 |
| **all** | | | 1,646,310,945 | **5409** | **100.00%** | **540.9 M** | | | |

| group | weight | share | token-reads | reads |
|---|---:|---:|---:|---:|
| new fiction (`modern` + `anth`) | 3511 | 64.9% | 351.1 M | 4.00 |
| library + Strange Horizons + released | 365 | 6.7% | 36.5 M | 2.00 |
| 1920–71 literary | 309 | 5.7% | 30.9 M | 1.00 |
| serials | 201 | 3.7% | 20.1 M | 1.00 |
| net shelves + verse | 327 | 6.0% | 32.7 M | 0.28 |
| old fantasy | 409 | 7.6% | 40.9 M | 0.32 |
| light novels | 123 | 2.3% | 12.3 M | 0.05 |
| pulp sci-fi + base | 164 | 3.0% | 16.4 M | 0.04 |
| fan fiction | 0 | 0.0% | 0.0 M | 0.00 |
| **sum** | **5409** | **100.0%** | **540.9 M** | |

```
MIX="bins2/fantasy.bin:409 bins2/scifi.bin:82 bins/anime.bin:123 bins/fanfic.bin:0 bins2/base.bin:82 bins/wired-core.bin:79 bins/wired-bulk.bin:228 bins2/literary.bin:309 bins2/horizons.bin:135 bins2/released.bin:79 bins2/library.bin:151 bins/lain.bin:10 bins/cyborg.bin:2 bins2/horizons-verse.bin:6 bins2/modern.bin:2828 bins2/anth.bin:683 bins2/serials.bin:201 bins2/verse2.bin:2 bins2/anth-rough.bin:0"
STEPS=22009
```

## Length

Batch 6 × accum 4 × 1,024 = 24,576 tokens a step, as `day3` (batch 8 dies at the first eval).
`day3` measures 2.074 s a step over its first 30,050 steps (11,848 tok/s; the trainer's own plan
said 2.073), and its wall clock runs 3% over that for evals, saves and samples; with the larger evals proposed
below, 5% is assumed here.

- main plan: **16,650 steps**, 409,190,400 tokens, 9.6 h of training,
  about 10.1 h on the wall.
- 4-read variant: **22,009 steps**, 540,893,184 tokens, 12.7 h of
  training, about 13.3 h on the wall.

The length is given to the trainer as `--steps`, not `--hours`, so the table above is exact
rather than whatever the forty-step calibration makes of the budget. **proposed**

## The learning rate

What is known, all of it from this model:

- `night1` ran to a peak of 3e-4 and ended annealed at 3e-5. `day2` restarted from that at 2e-4
  — **6.7 times the rate she had ended on** — and every held-out number went up a quarter point.
  The second attempt at 8e-5 got half of it back in twenty-five minutes.
- `day3` restarted at 8e-5 with 300 warm-up steps from a save that had been *stopped* at about
  7e-5 — one times what she was on — and nothing moved: the smoke test read 3.399 overall and
  the first eval 3.400.
- `day3` is a cosine from 8e-5 to a tenth of it. At step 29,950 its log line says `lr 6.00e-05`
  with every shelf still falling; it ends at **8e-6**.

So the knock is not about the old run's peak but about the rate she was last living at. `day4`
starts from an annealed model, like `day2` did: whatever its peak, the first evals give back
some of what `day3`'s last third bought by cooling, and `day4`'s own cosine cools it again at
its end. A fresh optimizer needs the warm-up for the same reason as before (Adam's first steps
are full-size whatever the gradient).

**proposed: peak 5e-5, 300 warm-up steps, cosine to a tenth (5e-6).** Six times the rate she ends
`day3` on, a quarter of the rate that hurt her, five eighths of `day3`'s peak. The reasoning: the
run is short (16,650 steps against 84,103) and half its diet is a kind of text she has
barely met, so a rate near `day3`'s end would leave the new shelves half learned; and she is
digesting calmly at 6e-5 right now. **guess**: the old shelves read 0.03–0.08 worse at the first
eval than at their baseline and are back by the end, except where the cut in diet, not the rate,
is the cause.

How much she changes is roughly the sum of the rate over the steps. `day3` in full is about 3.7
on that scale (84,103 steps at a mean of 4.4e-5):

| peak | sum of rate | against day3 | what it does |
|---|---:|---:|---|
| 2.5e-5 | 0.23 | 6% | an accent, not a change: the new shelves fall slowly, the old ones barely notice; the safe one and the dull one |
| **5e-5** | **0.46** | **12%** | the proposal |
| 8e-5 | 0.73 | 20% | `day3`'s peak again, ten times her resting rate: a real knock at the start (**guess** 0.10 or more), the new fiction learned fastest and memorised soonest, the old registers coming back on a 10–12% diet or not at all; the inflated one |

## Watching it

**Evals every 500 steps** (about eighteen minutes; 34 of them), not `day3`'s 1,000:
the detector needs six evals to say anything and nine to say `turned`, and at 1,000 that would be
more than half of this run gone. **proposed**

What an eval is, which matters for reading it: the trainer draws each shelf's held-out windows
once at the start (seed 0) and reads the same ones at every eval, `--eval-iters` batches shared
over every shelf on the line. `day3` ran on the default of 20 over fourteen shelves: **one batch
each, six windows of 1,024 tokens** — a hundred held-out stories watched through six thousand
tokens. **proposed: `--eval-iters 152`**, eight batches for each of the 19 shelves
on the line (48 windows, 49 thousand tokens a shelf; the verse shelves' held-out sets are smaller
than that and are simply read several times over). The cost: 136 forward batches an
eval instead of 13, by the trainer's own rule of thumb (a forward batch is a third of a training
one) about 24 seconds, 2.3% of the run at an eval every 500 steps —
**guess** until the smoke test's clock says so. Two things it changes: the old shelves' numbers
**do not continue `day3`'s curves** (other windows; a shelf can sit a tenth higher or lower for
no reason but the draw), and so the smoke test's eval at step 40 is the baseline for every shelf,
old and new (`night/day4-RUN.md`, step 6). `run4.sh` is assumed to pass the environment variable
**`EVAL_ITERS`** through as `--eval-iters`; the runbook checks that it does before anything starts.

One read of the new fiction passes every 6,662 steps (step ÷ 6,662 is
`modern`'s and `anth`'s reads so far).

**If it goes right**

- `modern`, `anth` and `serials` fall from their baseline at every eval mean through at least the
  first read, fastest in the first two thousand steps; the detector says `learning`. **guess**:
  `modern` starts near where Strange Horizons stands (3.6) and ends 0.15–0.25 under its baseline.
- With the new trainer, each of them has a training loss beside its held-out number and the gap
  between the two stays flat.
- Old fantasy, the library, the literary shelf: within 0.08 of their baseline at the first eval,
  then flat or falling, back to within 0.03 by the end.
- The light novels, pulp sci-fi, base and fan fiction drift **up**, a few hundredths, and stay
  there. That is the plan, not an alarm: the detector will call them `rising` or `turned`, and
  for a shelf read under a tenth of once that word means *forgetting*, never reciting. Fan
  fiction at zero is the measure of how fast.
- Through the loom's sampler, by the second hourly snapshot: present-day sentences, a scene that
  starts in the middle, names that are not Victorian — and the firekeepers' bell seed still
  answering in its own cadence.

**If it goes wrong**

- *The rate is too high*: at steps 500 and 1,000 the old shelves are all 0.15 or more over
  their baseline and the overall number is not coming down by 2,000.
- *The new fiction is being memorised*: `modern` or `anth` `turned … confirmed` with the gap to
  its training loss widening (the detector prints `memorising`), while it has been read more
  than once. That is the measurement the 2.5 was a guess at — write down step ÷
  6,662.
- *A small shelf with a long past turns*: Strange Horizons and the released authors go past six
  lifetime reads in this run, the visionary core and Lain past five. They are the likeliest to
  turn and the cheapest to act on.
- *The cadence is going*: old fantasy climbs all run and is more than 0.10 over its baseline at
  the halfway eval, and the bell seed on the page has gone flat and modern.
- *Nothing happens*: the new shelves fall under 0.05 by halfway. The rate was too low; the run
  is harmless and tells little.

## Stop conditions

**proposed**; each is a thing to do, in the runbook's steps:

1. The trainer dies and the wrapper does not bring it back, the guard reports a failed snapshot
   twice, or the loss is not a number: stop (step 9), read the log.
2. Rate too high, as above, at step 2,000: stop; start again under a new name at 2.5e-5 from
   `ckpt-day3-final.pt`. Do not ride it out — thirty-five minutes are cheaper than nine hours.
3. A small old shelf `turned … confirmed` (`night/turn.py day4` exits 3): its weight to zero
   through `weights.json` (step 8), the run goes on. With the old trainer there is no such lever:
   leave it and note the step.
4. `modern` or `anth` `turned … confirmed` and reading `memorising`: **stop the run there** — the
   guard keeps only the newest snapshot, so the age just before the turn exists only while it is
   the newest. That stop is a result, not a failure: it is the read limit, measured.
5. Old fantasy as in *the cadence is going*: bekh's call at the halfway look, nobody else's — the
   run is allowed to cost some of it.
6. Otherwise it ends by itself at step 16,650 and is judged through the loom, beside
   `day3`'s final snapshot, before any number is believed.

## Held-out sets

**Cut by whole works, before anything else, and written down.** A work is a story, a chapter, a
poem — never a slice of one. Which works are held out is decided by a hash of the work's name
with a fixed seed (`magdra-day4-heldout-1`), so the choice does not depend on what else is on the
shelf: new text arriving later adds works to both sides and moves none. The list is
`shelves/day4/<shelf>/heldout.txt`; a later build keeps every work on it held out whatever the
rule says then. Novels and novellas over 40,000 words, works under 300 (1,000 in `anth`), and
anything that is not a story (the kept essays, a book left whole) are never held out.

| shelf | rule | held-out works | held-out tokens | share of the shelf | sources in it |
|---|---|---:|---:|---:|---|
| modern | 1% of works | 107 | 656,391 | 0.92% | apex 20, bcs 10, clarkesworld 12, escapepod 5, fantasy 2, fireside 6, infinityplus 5, lightspeed 12, modern/giganotosaurus 3, nightmare 3, podcastle 7, pseudopod 1, released/shiner 1, thedark 6, uncanny 6, wayback 8 |
| anth | 4% of stories | 47 | 655,811 | 3.70% | anth 47 |
| serials | 2% of chapters | 35 | 428,861 | 2.09% | katalepsis 8, necroepilogos 1, pale 9, released/wildbow 1, twig 7, ward 6, worm 3 |
| verse2 | 10% of poems | 28 | 9,466 | 8.84% | apex 13, deadlands 14, fireside 1 |

`prep.py` holds out every hundredth *document or 4 MB piece*, in file order, or a tail slice of a
shelf with under a hundred files — it cannot take a list. It does not need to: with `--val-frac 0`
it writes everything it is given into one file, so each shelf is two folders and `prep.py` runs
twice, the second time with `--out bins2/<shelf>.val.bin`, which lands the held-out tokens exactly
where the trainer looks (`night/day4-RUN.md`, step 2). **No change to the kit.** The end-of-document
marker is `prep.py`'s own, GPT-2's `<|endoftext|>` appended after each file, as on every shelf
before; cutting the anthologies into stories is what puts one between two stories of a book.

**No held-out work shares text with anything she trains on or has read.** Checked two ways:

- `data/shelves.py build --deep` hashes every run of eight words of every held-out work and
  looks for them in every training file of the new shelves (the rough anthologies too) and in the text of the shelves
  she has read (library, literary, Strange Horizons and its poems, the released authors, Lain,
  both net shelves, old fantasy, base, and the sci-fi shelf streamed from ds-dev2 for this). A
  held-out work sharing five or more sampled runs with one file goes to training instead and is
  written into `heldout-rejected.txt` with the file it matched. 10 works went that way: 5 against another work of the new shelves; 3 against old fantasy; 1 against the net lists; 1 against the net core. After that:
  **CLEAN — no held-out work shares five sampled runs with any of 36,233 files (633 million words); the 1,889 lesser pairs are one to four chance phrases each**. Not checked: the light novels and the fan fiction, whose text is
  only on ds-dev2 and whose overlap with magazine fiction would be a surprise.
- `dedupe.py lookup` on each held-out work (the index of everything scanned, sources and not
  the clean copy): 217 looked up, 217 found as themselves; 14 also have a run of fifty words or more in some other document, 14 in an incoming source. Each of those is a second copy the dedupe's plan dropped or cut out of the clean copy (a podcast's reading of a magazine story, the collector's twin of GigaNotoSaurus and of *Pact*, a story inside an annual, the PDF twin of *The Big Book of Cyberpunk*); none of that text is in a training folder — the first check is the proof.

## Paragraph health

`data/health.py` on each folder, as built. Nothing was fixed; this is the report.

```
shelves/day4/modern/train: 9787 files, 270.9 MB, paragraph median 131 p90 432 chars, glued 2 books (0.02% of text), under 300 words 133
   left: image file 8, url 59, Project Gutenberg 1, copyright page 21
   LOOK: DIRT
shelves/day4/modern/heldout: 107 files, 2.5 MB, paragraph median 122 p90 405 chars, glued 0 books (0.00% of text), under 300 words 0
   left: nothing
   OK
shelves/day4/anth/train: 1428 files, 66.2 MB, paragraph median 136 p90 500 chars, glued 1 books (0.05% of text), under 300 words 0
   left: copyright page 2
   LOOK: DIRT
shelves/day4/anth/heldout: 47 files, 2.5 MB, paragraph median 136 p90 469 chars, glued 0 books (0.00% of text), under 300 words 0
   left: nothing
   OK
shelves/day4/serials/train: 1768 files, 71.1 MB, paragraph median 90 p90 298 chars, glued 0 books (0.00% of text), under 300 words 0
   left: url 12
   LOOK: DIRT
shelves/day4/serials/heldout: 35 files, 1.5 MB, paragraph median 91 p90 301 chars, glued 0 books (0.00% of text), under 300 words 0
   left: url 1
   LOOK: DIRT
shelves/day4/verse2/train: 211 files, 0.4 MB, paragraph median 63 p90 236 chars, glued 0 books (0.00% of text), under 300 words 143
   left: nothing
   OK
shelves/day4/verse2/heldout: 28 files, 0.0 MB, paragraph median 52 p90 230 chars, glued 0 books (0.00% of text), under 300 words 23
   left: nothing
   LOOK: SHREDDED-OR-VERSE
shelves/day4/anth-rough/train: 15 files, 25.1 MB, paragraph median 3126 p90 6243 chars, glued 0 books (0.00% of text), under 300 words 0
   left: image file 11, copyright page 733
   LOOK: DIRT
shelves/day4/anth-rough/heldout: 0 files, 0.0 MB, paragraph median 0 p90 0 chars, glued 0 books (0.00% of text), under 300 words 0
   left: nothing
   LOOK: EMPTY
```

## What is decided, proposed, guessed

- **Decided**: warm start from `day3`'s final save; short and dense; the shape of the mix; poems
  in; serials their own shelf at about one read; fan fiction at zero; the fallback; the rough anthologies out of the mix.
- **Proposed** (needs bekh's yes with the table in front of him — `PITFALLS.md` 6.5): the exact
  weights and the length; `anth` as its own shelf; the split of the net group; 5e-5 with 300
  warm-up steps; evals every 500 on 48 windows a shelf; `--steps` instead of `--hours`; the stop conditions; fan fiction
  kept on the line at zero.
- **Guessed**: that about 2.5 reads is where new fiction turns; the size of the knock at the
  start; every number under *if it goes right*.

## What the recipe writer thinks is wrong or thin

- **Strange Horizons and the released authors at two more reads end past six in their life**,
  and the rule of thumb in `PITFALLS.md` 4.1 is five. One read each would hold the line at five.
  It is in the table as decided; `day3`'s last verdicts on those two shelves
  (`night/turn.py day3`, after it ends) are the evidence to look at before the start.
- **Forty-eight windows instead of six costs the thread back to `day3`.** With the default the
  fourteen old shelves, first on the line in `day3`'s order, would keep exactly the windows `day3`
  watched (checked: the draws are identical), and "did she lose fantasy" would be one curve
  across both runs. The proposal gives that up for a number that means more; the smoke baseline
  is the bridge, and it is forty steps wide.
- **Part of `anth` is not new to her.** Of the fifty stories first drawn for its held-out set,
  three turned out to be on shelves she has read (an E. Nesbit story and one other on the old
  fantasy shelf, a piece that also sits in the net core), and one of PseudoPod's was a Buchan
  story from the same shelf. They went back to training, where they are re-reads; about the same
  share of the rest of `anth` — one story in seventeen, on this small sample — is presumably
  re-reads too, and the dedupe's new reference roots are the tool that can size it.
- **A stop and relaunch cannot change the mix**: a resume takes every setting from the save, the
  `--data` line included, and ignores the command line. `CLAUDE.md` says otherwise for `run3.sh`.
  The only lever inside a run is `runs/day4/weights.json`, read at each eval, and only the new
  trainer has it; `night/turn.py day4` exits 3 when a turn has stood for two evals (2 for this
  eval only) and prints the file with `--weights`.
- **The mix lives here.** `run4.sh` reads `night/<run>/mix.txt`, which git ignores; the tracked
  copies are the `MIX=` lines above and the same lines in the runbook's step 3, which writes the
  file on the host.
