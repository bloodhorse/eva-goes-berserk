# school

Raising our own model from random weights, instead of doing things to somebody else's. bekh,
2026-10-06, after a day of drugging llama and probing five bases for a soul: *i don't wanna
fuck around with nemo at all, i wanna build our own model.* A model's person is its diet (the
letter-*i* probe, `docs/soul/`), so here we choose every page it ever reads: no press releases,
no product pages, no support forums.

Two parts. **A childhood**: hundreds of millions to a few billion tokens on shelves of our
choosing, enough to learn English in the accents we want. **A finishing school**: a short,
gentle pass on the small precious texts, redone as often as we like, on whichever age of her
bekh picks. The blend is his: **dark souls** (its cadence and voice more than its lore), **the
visionary** (*language infused by creativity, futurism and sci-fi and the idea of a new time… the
merging of two realities, the digital one of numbers and ideas with the real one*, Serial
Experiments Lain, tears in rain, Prophecies), and **anime girls**. Lain is the bridge between
the last two. The age we want is **teenage**: sentences that hold on their own, two or three
hanging together, the paragraph drifting, no idea what the book is about — *teenage angst and
dreams* — which is bekh's definition of a dream in `BRIEF.md`; the adult that holds a thread
across its window is the 70B problem again in miniature.

## magdra

The child's name, bekh's yes on 2026-10-06 (*might add something later*). From her own mouth:
twenty-two minutes old, on the Gibson line, she wrote *"The sky above the port was still maiden
in the Mag dra of a situation"*. Nobody chose the word and it is in none of the books.

355 million parameters: a Llama-style decoder (rotary positions, RMSNorm, SwiGLU, tied
embeddings), 24 layers, 1024 wide, 16 heads, a 1024-token window, GPT-2's tokenizer — the
shape and alphabet llama.cpp converts and serves without complaint (our own byte-level BPE is
rejected by the converter's hash check; our own SentencePiece would pass). Size, alphabet and
window are fixed for good; everything else is more reading. `--init` warm-starts a new run
from any save with a fresh schedule, so she keeps what she has and continues on any card.

**Runs** (`night1` and `day2` ran on the box in `~/eva-olmo/school/runs/<name>/`; the mac keeps
each one's last snapshot in `school/models/<name>/`, and their trainable saves and earlier
snapshots are in the mini's archive under `models/<name>/`; from `day3` on a run lives
in `/opt/llama/magdra/runs/<name>/` on ds-dev2; what any run is doing is `night/mon.py <name>`,
never a sentence here):

- **`night1`** (2026-10-05 18:39 UTC, ten hours, done): from random weights, 659 M tokens,
  four shelves (fantasy 350 · sci-fi 250 · anime 400 · bekh's six books 6), 18.6k tok/s. Final
  held-out: fantasy 3.37, sci-fi 3.32, anime 2.35, the six 2.95, all still falling. An infant:
  sentence shapes, dialogue that turns, fused words; through the loom's sampler, whole sentences
  and already a wrong thing said straight (*"it was lighted by no lamps. It was pitch darkness. It
  was all very dark, but not very dark."*). Hourly snapshots `model-<step>-q8_0.gguf` from one
  hour old to the end are in the mini's archive — her whole first night at every age — and the
  mac keeps the last, `model-26800`.
- **`day2`** (2026-10-06, stopped by bekh at 10:05 UTC when the box's time ran out): warm start
  from night1's end on ten shelves. Two attempts: the first at lr 2e-4 knocked the held-out
  numbers up a quarter point and crawled back (kept as `runs/day2-lr2e-4`, 98 M tokens); the
  second from that save at lr 8e-5 (`runs/day2`, 194 M tokens, stopped at step 7,896 of a planned
  26,946). **A warm start's rate must be well under the old run's peak** — 8e-5 recovered half the
  knock in twenty-five minutes. At the stop: fantasy 3.46, sci-fi 3.44, anime 2.63 (night1 ended
  3.37 / 3.32 / 2.35), fan fiction 3.08, base 3.34, lain 3.10, net core 4.25 — the new shelves
  learned, the old ones not yet back to night1's sharpness, every number still falling. About
  0.95 billion tokens read in her life. Final snapshot `model-7896` on the mac; the trainable
  `ckpt-7896.pt` and the four earlier snapshots in the mini's archive.
- **`day3`, running on ds-dev2** (`~/.claude/docs/hosts.md`: RTX 5060 Ti 16 GB, Ryzen 5 3500X,
  30 GB RAM, Ubuntu 26.04, a team box; ours lives in `/opt/llama/magdra/` — the kit flat, `bins/`
  the shelves as the box tokenised them, `bins2/` the re-cut and new ones, `data/` the text and
  the Gutenberg source, `.venv` python 3.12 through uv with torch 2.14.1+cu130, `runs/day3/`).
  Started 2026-10-06 19:22 UTC as a warm start from `ckpt-7896.pt` at 8e-5 with 300 warm-up
  steps, batch 6 × accum 4 (24,576 tokens a step; batch 8 benches but dies at the first eval),
  fourteen shelves at the weights in `night/run3.sh`, fifty hours planned as 84,103 steps and
  2.07 billion tokens, about 11.9k tok/s, 15.0 GB of the card. Stopped once at step 911 to add
  three one-line seeds and resumed from the save (`PITFALLS.md` 7.1 has how). It ends around
  2026-10-08 20:00 UTC, with a push to the phone; **where she is right now is
  `night/mon.py day3 --once` or the page, never a sentence here**; every status she has written
  is `night/day3/ledger.jsonl`, and the page's sparklines are that file. How to read the evals
  (one every 1,000 steps, about 35 minutes): the overall number falls for two and gives a little
  back on the third, with the floor lower each time; a big shelf swings ±0.03 from eval to eval,
  net core ±0.1 (its held-out set is tiny), the small new shelves ±0.015 — a shelf has to rise
  two evals running by more than its own swing before it means anything, and none has yet.
  The work project's `llama-server.service` is stopped for the run (idle since 2026-08-29 by
  its journal; bekh's word, 2026-10-06); `sudo systemctl start llama-server.service` brings it
  back, and a reboot does too (it is enabled), which would take the card from a run. bekh's
  yes covered that stop, the venv and work inside `/opt/llama/magdra/`; anything else on that
  host is shown and asked first. Test leftovers there, 6 GB, waiting for his "delete for good":
  `runs/smoke`, `runs/smoke2`, `runs/.exporttest-20261006`.

The shelves, tokens in millions. `bins2/` holds the ones cut again or new on 2026-10-06, `bins/`
the rest as the box made them; the last two columns are the weights of `day2` and of `day3`
(bekh's go, 2026-10-07):

| shelf | what | M tok | day2 | day3 |
|---|---|---|---|---|
| fantasy (`bins2`) | 1,550 books: Gutenberg fantasy, horror, gothic, sagas, Arthurian, myth, plus Faded Page / Gutenberg Australia (Peake, Eddison, Dunsany's later books, Howard, Charles Williams, Treece) | 126 | 2000 | 2000 |
| scifi (`bins2`) | 3,144 pulp stories and novels plus Stapledon complete, Cordwainer Smith, Kuttner, Wyndham, Lewis's space trilogy (Fearn left out) | 77 | 1500 | 1500 |
| anime | `alpindale/light-novels`, official English translations | 241 | 2100 | 2100 |
| fanfic | fanfiction.net anime fandoms (2016 dump), sampled by the square root of each fandom's size | 550 | 1400 | 1400 |
| base (`bins2`) | plain old fiction from Gutenberg, nothing already on a shelf — ballast so the precious shelves are read a sane number of times | 372 | 2200 | 1550 |
| literary (`bins2`) | 261 Faded Page books, 1920–1971: Faulkner, Woolf, Lowry, Flann O'Brien, Flannery O'Connor, McCullers, Waugh, Steinbeck, Dinesen | 30.9 | — | 620 |
| horizons (`bins2`) | Strange Horizons, 1,196 stories, 2000–2026 | 6.7 | — | 135 |
| horizons-verse (`bins2`) | its 1,640 poems; whether verse goes in is open | 0.61 | — | 12 |
| released (`bins2`) | fiction its authors serve free: Rucker, Watts, qntm, Scott Alexander, Roger Williams | 3.95 | — | 80 |
| wired-core | the visionary net: Barlow, Bey, the Ccru, hyperstition, EFF essays, the cyberpunk project, small zines | 8 | 200 | 160 |
| wired-bulk | the lists (extropians, cypherpunks, nettime), the magazines, Phrack, the BBS erotica | 107 | 400 | 400 |
| library (`bins2`) | 55 books: bekh's six and what had arrived of the three lists in `library.md` — the finishing school's shelf, read about twice here so that pass has room | 7.5 | 50 (the six) | 72 |
| lain | everything Lain in English (`lain/`) | 0.96 | 25 | 20 |
| cyborg | the finishing corpus at tier 1, fit ≥ 1 (`corpus.jsonl`) | 0.18 | 10 | 4 |

`day3` holds every small shelf to about four readings over two billion tokens (a weight point
is 200,000 tokens read): at `day2`'s weights the six would have been read ten times and the
cyborg corpus eleven. So the share of chosen modern prose is set by how much of it there is —
the new shelves carry about 9% — and the weight they take came out of the ballast. Not placed
yet: a **spine** of modern plain prose in bekh's worlds (A Song of Ice and Fire, Wildbow's
Pact), and the books of `library.md` that had not arrived, which join at the finishing school.

**The fantasy, sci-fi and base text she read until now was half glued**: 3,505 of 7,320
Gutenberg books had reached her as one paragraph per chapter or per book. `data/cut2.py` cut the
same books again from the source on ds-dev2 — 24 books (0.64% of the text) still have a
paragraph over 20,000 characters, 90 books of verse keep their lines — and the three shelves in
`bins2/` are that cut. A smoke test on 2026-10-06 (forty steps from `ckpt-7896.pt`, all fourteen
shelves, batch 6 × 4) ran clean at 10.8–11.9k tok/s and **14.7 GB reserved** with the evals in —
batch 8 does not fit a real run. Her held-out numbers at that moment, before any reading on
ds-dev2: fantasy 3.14, sci-fi 3.25, anime 2.03, fan fiction 2.99, base 3.42, literary 3.25,
horizons 3.70, released 3.74, picks 2.87, lain 3.22, net core 3.86 (the held-out sets of the
re-cut shelves are new, so the first three do not compare with `day2`'s).

The rule behind the weights: a small shelf read five times is being memorised; the big plain
shelves exist so the voice shelves can be read once or twice. Weights are a recipe, not a law —
stop, change, warm-start again. **bekh's standing words**: erotica stays; nothing sexual
involving minors goes in (the fan fiction's minors rule in `fanfic/minors.py` is blunt on
purpose, dropped half the words of two shelves; the BBS erotica had its own cut).

**What she costs to grow up.** About 20 tokens per parameter is adult (7 B); teenage for her is
2.5–3 B. The borrowed card does 19k tok/s (0.67 B in ten hours); a rented 4090 roughly twice
that for ~$0.40/h, one H100 four to five times for ~$2.50/h — so teenage from night1 is about
30 box-hours or $20 of H100. **Past about 10 B tokens on this diet more reading is reciting**;
the next step is more text, not more hours.

**The text is the accumulated knowledge** (bekh, 2026-10-06): nothing tokenised or cleaned is
ever deleted — shelves, bins, the cut text, the fan-fiction cuts, the books — because the next
model reuses them, and a rented card costs money while text costs only the gathering. The archive
is **`bek@100.69.218.90:/srv/music/school-archive/`**, the mini's big disk (`night/archive.sh`
mirrors `school/` there and pulls the box's `bins/`, `data/` and `fanfic/` first; rerun it after
any new shelf or run). The archive is the only home of the box's copies and of the trainable
saves: on the mac `models/box/` holds just the two recut shelves (`data/base-r2`,
`data/shelves/fantasy-r2`), the rest having gone to the Trash on 2026-10-07 after a sha256 match
against the mini. `archive.sh` never deletes on the mini, and it pulls the box's 13 GB back onto
the mac if the box still answers. Renting iron is out of the question for now; the next bigger model waits
for a borrowed card and for more text.

## Watching and running

```bash
cd ~/tower/forge/eva-goes-berserk/school && uv run --python 3.12 night/mon.py <run>   # terminal monitor: probe, heartbeat, moving
open https://miniarch.tail004a72.ts.net:8446/school-<run>.html                        # the page, rebuilt every 2 min while the mac is awake
```

The page (`night/page.py`, in the house palette: mint good, pink fail, light blue context) shows
her age in tokens with a life bar, the stat cards, one row per shelf with a sparkline and the last
move, **"the last thing she said"** and **"through the loom's sampler"** — the seven seeds of
`night/prompts.txt` drawn once each from the newest hourly snapshot with min_p 0.08 and a
repetition brake (`page.py` runs `/opt/homebrew/bin/llama-completion` on the mac when
`models/<run>/latest` changes, and keeps the draws in `night/<run>/loomed.jsonl`) — then the
trainer's own raw draws (temperature 1, no cut-off: her worst face) and the guard log. **Read her
through a sampler before judging her**; the raw draws made both of us call her bad twice. To sit
with her on the loom, serve the newest snapshot and `eva.x` fans on her (the server loads a file
once — it has to be restarted for each new snapshot, which nothing does yet):

```bash
cd ~/tower/forge/eva-goes-berserk/school && kill $(lsof -tnP -iTCP:8086 -sTCP:LISTEN) ; \
  (nohup llama-server -m models/day3/model-latest-q8_0.gguf -c 1024 -ngl 99 --host 127.0.0.1 --port 8086 --no-jinja > night/day3/serve.out 2>&1 < /dev/null &)
```

A walk on her is the walk scripts with `LOOM_LLAMA=http://127.0.0.1:8086` (`eva/cli/walk/README.md`);
her first, `experiments/magdra-prophecy` and its cut, was made at step 911 (2026-10-07).

**The twenty-minute look** bekh wants during a run is a session cron, and it dies with the
session; a fresh session re-arms it with `/loop 20m` and this prompt:

> Check magdra's day3 run (read school/PITFALLS.md section 7 once if you have not this session).
> On ds-dev2 (ssh -o ConnectTimeout=15 -i $KEY BekmemetevVO@ds-dev2.x340.org, read-only, inside
> /opt/llama/magdra): runs/day3/status.json (step, total_steps, tok_per_s, eta, eval_per_file,
> heartbeat age from its unix field), the last two lines of runs/day3.log, the tail of
> runs/day3.guard.log, nvidia-smi memory and temperature, df free, and whether train.py, run3.sh
> and guard.sh are alive. On the mac: age of school/night/day3/status.json, tail of
> school/night/day3/pull.log and watch.err, and that night/watch.sh and night/pull_ckpt.sh for
> day3 are still running. Compare each shelf's held-out number with the previous check's. Report
> to bekh in at most five short lines: alive or not, step and percent, speed, the shelf numbers
> that moved (falling is good; name any shelf that rose across two evals in a row), anything odd.
> Push to ntfy.sh/kk_alert (Priority high) only if something is wrong: trainer or guard dead,
> heartbeat older than five minutes, a snapshot failed, a shelf climbing across two evals, disk
> under 30 GB, card memory at the limit, or the work llama-server active again. Never restart,
> stop or change anything on ds-dev2 without bekh's word; if the run is dead, say what the log
> shows and wait. When status says the run is done, report the final numbers, push once at
> default priority, and end the loop.

The sheets site that serves the page is `sheets.service`, a systemd user unit on the mini since
2026-10-07 (it had died with a reboot before that). On ds-dev2 everything is
`/opt/llama/magdra/`, the kit flat in it: `bins/` the shelves as the box tokenised them and
`bins2/` the re-cut and new ones (`<name>.bin`, `.val.bin`, `.json`, `.tokenizer/`), `data/` the
text and the Gutenberg source, `runs/<name>/` (`ckpt.pt` trainable, `status.json` heartbeat,
`samples.jsonl`, the newest `model-<step>-q8_0.gguf`), `kit-before-20261006/` the kit as it came
from the box. The box had the same layout under `~/eva-olmo/school/`. `scratch/RUN.md` is the
box's copy-paste runbook for prep, start, warm start, resume, export, serve and stop. A run is
three processes on the training host and two on the mac; the mac's three scripts and `mon.py`
find the host through `BOX` (default `BekmemetevVO@ds-dev2.x340.org`), `BOXDIR` (default
`/opt/llama/magdra`) and `KEY`:

- `night/run3.sh <name>` — the trainer in a restart loop (resumes from `ckpt.pt`; the loop
  stops on DONE or on a deliberate STOPPED), silent pushes at start and end. Batch 6 × 4, the
  warm-start rate, `--init ckpt-7896.pt`, the mix and the fifty hours are in the file (`MIX=` and
  `HOURS=` in the environment override them). `run.sh` and `run2.sh` are night1 and day2 as they
  ran on the box. **To
  change prompts or recipe mid-run**: `kill -TERM` the trainer (it saves), wait for STOPPED and
  for the guard to write `guard down`, rotate `runs/<name>.guard.log` aside, relaunch all five.
- `night/guard.sh <name>` — pauses the trainer above 88 °C until 75 °C, exports a servable
  snapshot every hour and **keeps only the newest** (bekh, 2026-10-06: *fuck the history, i
  don't need it*), skips snapshots under 20 GB free.
- `night/watch.sh <name>` (mac, under `caffeinate`) — pulls status, samples and guard log,
  builds the page with `night/page.py`, posts it to the mini, keeps the newest snapshot as
  `models/<name>/model-latest-q8_0.gguf` (its step in `models/<name>/latest`); ends on
  `guard down`.
- `night/pull_ckpt.sh <name>` (mac) — every six hours (`EVERY=` seconds) streams the trainable
  `ckpt.pt` from the training host straight to the mini's archive
  (`/srv/music/school-archive/models/<name>/ckpt.pt`), never touching the mac's disk, and writes
  MATCH or MISMATCH by size to `night/<name>/pull.log`; once more at the end.

Measured on the box's card (RTX PRO 4000 Blackwell, 145 W, kvm), context 1024, compiled: 30 M
parameters 101k tok/s, 124 M 43k (14.6 GB), 355 M 18.9k at batch 16 (21 GB) — the runs use
batch 12 × 2 at 18.6k and 18.9 GB.

## Where things are

- `scratch/` — the trainer: `train.py` (random init or `--init`, several token files with
  weights, per-file held-out loss, resumable, heartbeat, samples at each save), `prep.py` (text →
  tokens; **one document per file in a flat directory — nested folders are skipped silently**),
  `export.sh` / `export_hf.py` (checkpoint → HF → GGUF), `bench.sh`, `archtest.*`, `RUN.md`.
- `night/` — the run scripts above, `prompts.txt` (four paragraph seeds: a late train, the
  firekeepers' bell, the forum girl, the figment's line), `mon.py`, `page.py`, `fans/` (fans
  drawn through the loom's sampler, e.g. `magdra-26800.txt`); a run's pulled status, samples and
  page land in `night/<name>/` (not in git), with `loomed.jsonl` (the sampled draws per snapshot)
  and `page-preview*.png` (the page as screenshotted at phone width).
- `data/` — `cut.py` and `base.py` chose the books of the fantasy, sci-fi and base shelves out of
  `sedthh/gutenberg_english`; **`cut2.py` is the cut that is used** — it takes the lists of ids
  those two chose and cuts the same books again with the paragraphs right (its `cut2.tsv` has
  every book's mode, paragraph count and longest paragraph), running each through `recut.py`,
  which drops image captions (`p029.jpg (285K) Full Size`), Gutenberg boilerplate and urls.
  `health.py <dir>` is the verdict on any folder of text before it is tokenised (glued, shredded,
  nested, dirt).
  `books.py` turns the epubs in `inbox/` into body text in `inbox/clean/` with a ledger of
  every section it dropped and why, a language gate, a check that a file is what its extension
  says, and `inbox/skip.txt`; `pages.py` joins a book that arrived as scanned-page text files.
  `jsonl2dir.py`, `build*.sh` (the tokenising batches; `build5.sh` on ds-dev2 made `bins2/`).
- `modern/` — text fetched on 2026-10-06, one folder a source, each with its scripts and a
  ledger (text and raw pages not in git, mirrored to the mini): `fadedpage/` 261 books of
  1920–1971 literary prose (`picks.tsv` is the selection), `strangehorizons/` 1,196 stories and
  1,640 poems from the magazine's open API, `released/` fiction its authors serve themselves
  (Rucker, who asks to be trained on; Watts; qntm; Scott Alexander; Roger Williams; one Kelly
  Link story; Wildbow's Pact, kept apart for the spine). `library.md` — bekh's thirty for the
  finishing school and where each stands.
- **The finishing school**: `corpus.jsonl` / `corpus.md` — 960 passages of cyborgism prose with
  names and dates stripped, labelled `origin` (base, human, tuned, unknown), `tier`, `fit`
  (2 = visionary); `strip.py` rebuilds it from `raw/`; `grades/`, `passages.jsonl`,
  `dropped.jsonl`, `prophecies_origin.json`, `wiki_pages.json` its workings. bekh's favourite
  piece is `proph-069` (*"If I am writing it for anyone it's for the bots"*). Not yet run.
- `lain/` — everything Lain in English (3.9 MB: the game's whole script, all 13 layers' subtitles
  and a literal translation, the wiki, fan essays, lainzine, 81 fan works); `wired/` (481 MB) —
  the net as a new world, with `wired-core/` and `wired-bulk/` cut from it; `pd2/` — Faded Page
  and Gutenberg Australia (979 books, 26.5 M words; its `REPORT.md` has the sites' holdings and
  the pulp-OCR verdict); `fanfic/` — the fan-fiction cut's scripts, mapping and minors rule (the
  shelves themselves are `~/eva-olmo/school/fanfic/*.jsonl` on the box, and the "souls" and
  "wired" fan shelves were not used: Dragon Age and Mass Effect are not the blend). Raw text
  not in git. `inbox/` — the books: `clean/` the converted library with its ledger, `held/` what converted
  without paragraphs, `rescued/` plain-text rescues of misnamed files (Word, RTF, HTML, RAR,
  scanned pages), `preview*/` the converter's test runs, `skip.txt` the files never converted; `models/` —
  each run's last snapshot, `bins/` the tokenised shelves copied from the box, and `box/` the two
  recut shelves; trainable saves and older snapshots live in the mini's archive. `sources/` —
  the scout's notes.

## Lessons

**`PITFALLS.md` is the list** — everything that bit, in the order the work happens (finding
text, cutting, tokenising, the mix, the machine, starting, running), each with how to catch it.
Read the stage you are entering before you enter it; put a new one there, not here. The three
that shape every day:

- **Measure a shelf by its paragraphs** (`data/health.py <dir>`), not by its first page: half
  the Gutenberg text went in glued and nobody saw it for two runs.
- **Judge her through the loom's sampler, never the raw page draws**, and read the run before
  speaking of it — the clock is not in my head.
- **The readings per shelf get multiplied out before a run.**

## Where the text comes from

This is a DIY project and it runs on the DIY ethic: people who make things by hand build on each
other's work, and that is how the scene has always fed itself. A robots file or a terms page is
not what decides her shelves; bekh is. He picks the sources and fetches them his way.

She is private, nobody pays for her, and nothing she reads is redistributed. So the question of
where a text came from is closed: don't moralise about it, don't reopen it, don't hang caveats on
a shelf or a ledger because of its origin. A ledger records provenance as a fact (the url, the
licence if there is one), never as a verdict. Text that is on disk is text: convert it, check its
health, dedupe it, shelve it, with the same care whatever door it came through.

## Next

**While `day3` runs** (until about 2026-10-08 20:00 UTC): the twenty-minute look (above). bekh
gets the books that are still missing (`library.md`, the gaps section) into
`~/tower/ephemeral/booox/souls_lain_library/`; `data/books.py <that folder> --out inbox/clean`
converts them, `data/health.py inbox/clean` is the verdict, and they join the library shelf at
the finishing school. Make the loom follow her: a small job that restarts the 8086 server when
`models/day3/latest` changes, so `eva.x` is always her newest hour. And the finishing-school talk,
not yet had — the open questions: a short low-rate pass against an adapter with a dial
(`SERVE.md` was never written; check the per-request LoRA scale on our llama.cpp builds first);
how many tokens; the weights of the library's five (Wolfe, VALIS, Borges, Hard-Boiled Wonderland,
Viriconium — four told by an *i* who remembers and cannot be trusted) against the cyborg corpus
and Lain; whether the poems go in at all. Claude's view, held loosely: a pass, not an adapter,
at a quarter of day3's rate; the library and the cyborg corpus roughly equal, Lain under them;
read the result through the loom before any number is believed.

**When it ends**: the trainer writes DONE and pushes; the guard takes a last snapshot and
writes `guard down`; the watcher pulls it and stops; the puller makes one last copy to the mini
(`night/day3/pull.log` says MATCH). Then: copy `runs/day3/ckpt.pt` to the mac if there is room
(there is not, at 97% full — the mini's copy is the trainable save), serve the final snapshot to
the loom, bekh reads her and marks, and whether the work project's llama-server goes back on is
his and the team's call (one line, above). Then the finishing school on ds-dev2 from the final
save, and `library.md`'s gaps as they arrive.

**More text, later**: Harvard's Institutional Books on Hugging Face (gated, non-commercial; the
unrenewed American books of 1930–63 — count its fiction from the metadata first; bekh has to
accept the gate), an ask to Escape Pod / PodCastle / PseudoPod (2,800 stories, already
CC BY-NC-ND, crawlers blocked — an email from bekh), `common-pile/project_gutenberg` (670 shelf
books newer than our dump), Roy Glashan's Library (hand-typed pulps);
`docs/research/text-sources-2026-10-06.md` is the survey. Then the soul probe on her, the three
dials from her shelf states, and the made-up world where "does it know what the text is about" is
a readout.
