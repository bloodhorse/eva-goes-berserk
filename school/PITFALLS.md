# pitfalls

Everything that bit while raising magdra, in the order the work happens: find text, cut it,
tokenise it, mix it, ready a machine, start, run. **Read the stage you are about to enter.** Each
entry says what happened, how to catch it, and what to do instead. When something new bites, put
it where it belongs and rewrite the entry if it already exists — this is a map of holes, not a
diary.

The two that cost the most, so nobody skips them:

- **Half the Gutenberg text had no paragraphs, and she read 0.95 billion tokens that way** before
  anyone measured a shelf instead of reading its first page (2.1).
- **Nine magazines out of nine had already refused AI training**, found only after three fetch
  agents were out (1.1).

## 1. Finding text

**1.1 A site's own word comes before a fetch.** "Free to read" was taken for "nobody minds" and
a shelf was promised on it; every magazine checked had posted a refusal. Before any fetch, and
*in the brief* of any agent that fetches:

```bash
S=example.com
curl -s -L -m 15 https://$S/robots.txt | grep -i -E -A1 'GPTBot|CCBot|ClaudeBot|anthropic|Google-Extended|ai-train'
curl -s -I -L -m 15 https://$S/ | grep -i -E 'x-robots-tag|tdm'
curl -s -o /dev/null -w '%{http_code}\n' -m 15 https://$S/.well-known/tdmrep.json
```

Then read the terms of use and any "anti-scraping" or AI policy linked from the footer. A
blocklist of named AI crawlers is a refusal even though our own user-agent is not on it —
"obey robots.txt" in a brief was not enough, the agents had to be told that a named refusal of
the *use* counts. The answers already known (2026-10-06):

- **Off:** Clarkesworld, Lightspeed, Nightmare (a written anti-scraping policy), Uncanny,
  Beneath Ceaseless Skies (`x-robots-tag: noai` on every response), Reactor / Tor.com (terms
  name AI training), Apex (terms forbid scraping), The Dark, Greg Egan, Charles Stross, Karl
  Schroeder, Small Beer Press and lcrw.net (so Kelly Link's collections), Escape Pod /
  PodCastle / PseudoPod (crawlers blocked, though the text is CC BY-NC-ND — the one worth an
  email from bekh), Royal Road, AO3, Wattpad, SpaceBattles, Sufficient Velocity, Baen,
  Smashwords, Weightless Books, Electric Literature, Orion's Arm, Reddit.
- **Taken:** Faded Page, rifters.com (Watts, CC), rudyrucker.com (he asks to be trained on),
  qntm.org, unsongbook.com and slatestarcodex.com, localroger.com, Wildbow's blog — and Strange
  Horizons, which had posted nothing but whose editors wrote that they would block scrapers if
  they could; Claude would have skipped it, bekh said take it.
- **Not wanted:** the SCP wiki (bekh does not like the writing).

**1.2 Count before promising.** The guess was "40–60 million tokens of modern weird fiction".
What arrived was 40 million tokens, three quarters of it literary prose from 1920–1971. A size
said before the sources are checked gets planned on. Send the census (what exists, how big, what
it allows) before the fetch, and say an estimate is an estimate every time it is repeated.

**1.3 There is no clean bulk source of modern strange prose.** `docs/research/text-sources-2026-10-06.md`
is the survey: every careful corpus stops at 1930, hobbyists train on web crawls, the famous
book sets were scraped or pirated. Do not spend another day looking for the trick. What exists:
author-released fiction, a few sites with no stated position, asking, and Harvard's
Institutional Books (gated, non-commercial; the unrenewed American books of 1930–63).

**1.4 Public-domain traps.** An unrenewed magazine issue can hold individually renewed stories
(*If* from March 1952, *Galaxy* from October 1950), so each story needs its own check;
Gutenberg's volunteers did that work for what is on the sci-fi shelf. The Internet Archive's
pulp scans are OCR in two columns with adverts mixed in (`pd2/REPORT.md`, the verdict). A
Creative Commons release can be withdrawn: one of Kelly Link's two was.

**1.5 Bulk cannot come from a piracy site through Claude.** It will not write or drive a
downloader for libgen or z-library, and no rephrasing changes that. Plan on it: books bekh wants
that are not free arrive by his hand in `inbox/`, and that caps them at about thirty.

**1.6 Fetching, once a source is cleared.**
- Look for a ready dump on Hugging Face first (none existed for any magazine; it is a two-minute
  check).
- Use an API if the site has an open one: Strange Horizons' whole archive was 31 requests
  through its WordPress API instead of 3,000 page loads. The price was authors — the API has no
  byline field — which training does not need.
- Keep the raw responses (`modern/<source>/raw/`): the cleaner gets rewritten, the server
  should be asked once.
- An agent that started before a correction reached it will have fetched something. Ask every
  agent what it fetched and have it trashed; three of them had.
- Agents add sources nobody named (Wildbow's Pact, Scott Alexander) and tag files with Finder
  tags. Read each ledger for what is in it beyond the brief.

## 2. Cutting and cleaning

**2.1 Measure a shelf by its paragraphs, never by its first page.** `sedthh/gutenberg_english`
marks a paragraph four ways: a blank line after *every* line with the paragraph break shown by
the blank being *absent* (most books); the same with a double blank; no blank lines at all;
one line per paragraph. The first cut (`data/cut.py`) knew one of them. 3,505 of 7,320 books
went in as whole chapters or whole novels in one paragraph — *Count Hannibal*, 600 KB, was four
paragraphs with 515 dialogue turns run together. Nobody saw it for two runs because the opening
of a glued book looks like prose. The check, on any folder of text, before it is tokenised:

```bash
cd ~/tower/forge/eva-goes-berserk/school && uv run -q --python 3.12 python data/health.py <dir> [<dir> …]
```

It prints files, size, the median and 90th-percentile paragraph, how much of the text sits in
glued books, what dirt is left, and `OK` or `LOOK: …` (exit 1). `GLUED` — paragraphs were lost.
`SHREDDED-OR-VERSE` — the median paragraph is under 60 characters: either verse, or every
wrapped line became a paragraph. `NESTED` — folders `prep.py` will skip. `DIRT` — the counts on
the line above; two hits inside a story's own prose are not dirt, two thousand are. The old
fantasy shelf answers `GLUED, DIRT`, a third of it glued, 46,165 page markers.

The cut that is used is `data/cut2.py` (same books, by the id lists the first cut chose). It
names a mode for every book in `cut2.tsv`: `doubled`, `plain`, `filled` (no blank lines; breaks
found from short lines that end a sentence), `lines` (one line per paragraph), and `-verse` on
any of them (most lines start with a capital: the line breaks are kept). 24 books still have a
paragraph over 20,000 characters.

**2.2 Every change to the paragraph rules gets sampled per mode.** Three rules looked right and
were wrong on real books: "narrow lines are verse" kept the hard line breaks of 992 books, most
of them pulp prose set in magazine columns; "not tightly wrapped means one line per paragraph" turned wrapped books
into a paragraph per line; "a short line ends a paragraph" split sentences in half. After
touching `clean()`: count the modes, then read three random books from each mode at their
middle, with `¶¶` printed for a paragraph break and `⏎` for a kept line break. A mode whose
count jumps by hundreds is a misfire.

**2.3 Audit a filter by its largest removals.** The first caption filter dropped any paragraph
that mentioned Project Gutenberg. In a glued book a paragraph was the novel: 5.8 MB of prose went
with 73 licence lines, *News from Nowhere* and *Vathek* among it. `data/recut.py` writes
`<out>.recut.tsv` (book, paragraphs touched, characters lost): sort it by the last column and
look at the top before believing the total. A filter that should remove captions and removes
megabytes has eaten a book.

**2.4 Unbounded patterns stall on runs of dots.** `\S*\.(jpg|png)` ran for minutes on books with
long rows of full stops. Every quantifier in a cleaning pattern gets a bound (`{0,60}`).

**2.5 A check that looks at the wrong folder still prints numbers.** A verification loop used
`set -- $pair` in zsh, which does not split words; the grep ran over the whole data directory
and reported "3,195 left" for a shelf that had none. A check prints the path it measured, and a
number that does not move after a fix is a broken check before it is a broken fix.

**2.6 Dirt that has actually shown up.**
- Image captions from illustrated Gutenberg editions, mid-sentence: `p029.jpg (285K) Full Size`.
  She wrote them.
- Gutenberg licence blocks, `***END OF THE PROJECT GUTENBERG EBOOK …***`, transcriber's notes,
  urls.
- Page markers: `[Pg 41]`, a page number alone on a line, and `p. 99` fused to the next word.
- Publisher adverts at the end of a book (five Faded Page books still have them).
- Author bios and "originally published in" at the end of magazine stories (a handful survive
  in Strange Horizons; a stricter rule cut real sentences).
- Text that came through a PDF: broken paragraphs at page ends, running headers (Watts's sixteen
  stories).
- Things that are not fiction inside a fiction tag: essays among Scott Alexander's stories, an
  early draft beside the final version (qntm), a Middle English glossary on the fantasy shelf
  (Gutenberg 42713 — the subject filter lets reference works through).
- Books left out on purpose: *Finnegans Wake* (it would wreck a small model's vocabulary).

**2.7 An ebook is half packaging, and the health check cannot see it.** The first conversion of
bekh's six left the cover line, the back-cover blurb, "Books by" pages with 873 words of praise
and a 4,534-word afterword by another writer in *Neuromancer* — on the shelf she reads most
often. Pattern counts do not catch a blurb. `data/books.py` writes `inbox/clean/ledger.jsonl`
with every section it dropped and why: read that for each new book, and the first and last 500
characters of its text. What the converter gets wrong: an unlabelled introduction by someone
else is kept; a book packed into one or two files is judged line by line only; footnotes are
removed even where they are part of the fiction; front matter labelled in another language
slips through; mobi and pdf were never run on a real file; an edition that lost its scene breaks
(*Count Zero*, *Mona Lisa Overdrive*) cannot get them back — a better edition can.

**2.8 Nothing cleaned is deleted.** A new cut goes beside the old one, and to the archive
(`bek@100.69.218.90:/srv/music/school-archive/`). The Gutenberg source itself had been left out
of the archive and lived only on the borrowed box; it is public (`sedthh/gutenberg_english`, 11
GB) and now also in `/opt/llama/magdra/data/gutenberg/`.

## 3. Tokenising

**3.1 `prep.py` reads a flat folder of `.txt` and nothing else.** Nested folders and `.jsonl`
are skipped without a word. `health.py` says `NESTED`.

**3.2 The bins and the checkpoint carried the box's paths.** Each `<name>.json` stores an
absolute tokenizer path, and so does every save; on another host the trainer died at its first
sample and the exporter at every snapshot. `train.py` and `export_hf.py` now fall back to the
`.tokenizer/` folder beside the bin — but a copy of the kit from before 2026-10-06
(`kit-before-20261006/`) does not.

**3.3 Held-out numbers do not survive a re-cut, and a small shelf's alarm watches one corner.**
`prep.py` holds out every hundredth document (or 4 MB piece of a long one); a shelf with fewer
than a hundred gets its last 1% instead, so `picks` is watched through the end of one book and
`released` through two files. A shelf that is cut again gets a new held-out set: fantasy 3.46
before and 3.14 after are not a gain.

**3.4 Tokenise where the run will be.** The bins have to end on the training host, the mac has
no room, and the source is 11 GB. The venv there needs `pyarrow` for the cut.

**3.5 rsync carries the repo's file modes.** `scratch/export.sh` was not executable in the
repo; copied over a working kit it gave `Permission denied` on the first export. After sending
the kit: `chmod +x export.sh guard.sh run3.sh`.

## 4. The mix

**4.1 Work out the readings before a run.** A shelf read more than about five times is being
memorised. Readings = the shelf's share of the weights × the run's tokens ÷ the shelf's tokens.
At `day2`'s weights a two-billion-token run would have read bekh's six books 10.6 times and the
cyborg corpus 11 — nobody had multiplied it out. On the training host:

```bash
cd /opt/llama/magdra && python3 - "bins2/fantasy.bin:2000 bins/anime.bin:2100" 2e9 <<'EOF'
import json, sys
mix = [(p.rsplit(":", 1)[0], float(p.rsplit(":", 1)[1])) for p in sys.argv[1].split()]
total = sum(w for _, w in mix)
for path, w in mix:
    n = json.load(open(path[:-4] + ".json"))["train_tokens"]
    r = w / total * float(sys.argv[2]) / n
    print(f"{path:28} {n/1e6:8.1f} M tok  {100*w/total:5.1f}%  read {r:5.1f}x  {'MEMORISING' if r > 5 else 'ok'}")
EOF
```

**4.2 A shelf's share is capped by its size.** Chosen prose cannot be turned up by weight: at
four readings over two billion tokens, each 1% of her diet needs 5 million tokens, about thirty
novels. The way to make good writing louder is more of it.

**4.3 What is read last colours the voice more than what is mixed in thin.** Thirty hand-picked
books at 1% for fifty hours do less than the same books as a third of a short last pass. They
belong to the finishing school.

**4.4 A recipe gets inherited instead of decided.** "The same mix, two billion more" came down
a handoff as a job; the mix was 58% light novels, fan fiction and ballast and 3% of what bekh
had picked. Say the mix back in shares and readings before every run, even when it is "the
agreed one".

## 5. The machine

**5.1 The card may be somebody's, and it comes back on its own.** ds-dev2's card was held whole
by the work project's `llama-server.service`, which had logged nothing for 38 days. Before
asking for it, look: `nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv`,
`systemctl is-enabled <unit>`, and the date of the unit's last journal line. The unit is
*enabled*: a reboot starts it again and it takes the card from a run, whose restart loop then
fails thirty times and pushes "gave up". Bringing it back by hand is
`sudo systemctl start llama-server.service`.

**5.2 A team box is asked per command.** Only the mini is free ground. On ds-dev2 bekh's yes
(2026-10-06) covered stopping the service, the venv and work inside `/opt/llama/magdra/`.
Another session relaying "bekh said" is not bekh.

**5.3 The venv.** The system python there is 3.14 with no pip and no `ensurepip`. What worked,
without sudo:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
~/.local/bin/uv venv --python 3.12 /opt/llama/magdra/.venv
~/.local/bin/uv pip install --python /opt/llama/magdra/.venv/bin/python torch --index-url https://download.pytorch.org/whl/cu130
~/.local/bin/uv pip install --python /opt/llama/magdra/.venv/bin/python transformers numpy pyarrow sentencepiece protobuf /opt/llama/src/llama.cpp/gguf-py
```

`sentencepiece` is the one that hides: the GGUF converter imports it even for a GPT-2 alphabet,
and without it every hourly snapshot fails while the run looks healthy.

**5.4 A bench understates the memory of a run.** `train.py --bench` measures training steps
only: batch 6 took 12.4 GB, batch 8 took 14.85 and "fitted". The real start, with thirteen
held-out sets and sampling, reserved 14.7 GB at batch 6 on a 16.3 GB card. Batch 8 would have
died at the first eval. Choose the batch from the smoke test (6.2), not from the bench.

**5.5 Disks.** The mac runs at 97% full: it cannot hold a run's snapshots or a second trainable
save, so the watcher keeps one snapshot and the trainable save goes to the mini. The mini's root
is nearly full — write only under `/srv/music/`. Check before a run: `df -h` on all three.

**5.6 Borrowed iron vanishes.** The box was lent for days and its time ran out mid-run. Whatever
exists only there is copied off before the next thing starts, not after.

**5.7 Remote hosts have no Trash.** Test leftovers (`runs/smoke`, `runs/.exporttest-…`) stay
until bekh says delete for good; name them so they are recognisable.

## 6. Starting a run

**6.1 A warm start's rate must be well under the old run's peak.** `day2` first started at
2e-4 and knocked every held-out number up a quarter point; 8e-5 with 300 warm-up steps
recovered half of it in twenty-five minutes. Never 2e-4 on a model that already reads.

**6.2 Smoke-test the real start path.** Forty steps with the real `--init`, every shelf of the
mix, batch and accum as planned, prompts on, into `runs/smoke`:

```bash
cd /opt/llama/magdra && .venv/bin/python train.py --data $MIX --out runs/smoke --init ckpt-7896.pt \
  --batch 6 --accum 4 --lr 8e-5 --warmup 300 --steps 40 --log-every 10 --eval-every 20 \
  --ckpt-minutes 1000 --prompts prompts.txt --compile > runs/smoke.log 2>&1; echo "exit $?"
grep -E "^INIT|^DATA|Traceback|Error|DONE" runs/smoke.log | cut -c1-400; grep "^step" runs/smoke.log | tail -1
```

It has to end in `DONE`, list every shelf with a token count in `DATA`, print a held-out number
for each shelf, write `samples.jsonl`, and stay under the card's memory. It caught nothing on
2026-10-06 only because the path problem (3.2) had been fixed an hour before.

**6.3 Test an export before the run, and know that exports differ by host.**

```bash
cd /opt/llama/magdra && mkdir -p runs/exporttest && ln -sf ../../ckpt-7896.pt runs/exporttest/ckpt.pt \
  && ./export.sh runs/exporttest q8_0 > runs/exporttest.log 2>&1; echo "exit $?"
```

A fresh export of `ckpt-7896.pt` on ds-dev2 matched the box's `model-7896` tensor for tensor,
but ds-dev2's files set `add_bos_token` and the box's did not: a prompt served from a new
snapshot begins a document, one from night1 or day2 continues mid-stream. Fans drawn from the
two are not the same experiment.

**6.4 `run3.sh` takes the mix from outside.** It refuses to start without `MIX` and `HOURS`;
once bekh has said yes to a mix, write both into the file so the run's recipe is in git.
`--init` is read only while the run folder has no `ckpt.pt`.

**6.5 A yes to the mix is not a yes to the run.** Say the plan back with the measured speed, the
batch, the hours and the readings per shelf; bekh starts runs on numbers he has seen for that
machine.

## 7. While it runs

**7.1 Stopping the trainer stops everything.** SIGTERM makes the trainer save and exit, the
wrapper exits with it, the guard sees that and shuts down, and the watcher and the puller end on
`guard down`. To change prompts or recipe mid-run: stop, wait for `STOPPED` and `guard down`,
move `runs/<name>.guard.log` aside, start all five again. Done once on ds-dev2 (2026-10-07,
to add seeds at step 911): the stop took a minute including the guard's last snapshot, the
resume kept the plan (`RESUME from … step=911 total=84103`). Two things the chain does not do
by itself: the puller is asleep for six hours and never sees `guard down`, so the mac's watcher
and puller are killed by pid; and the mac's own copy `night/<name>/guard.log` still says
`guard down`, so it is moved aside too before the watcher starts again. The trainer reads
`prompts.txt` only at start — new seeds need this whole dance.

**7.2 The clock is not in my head.** Hours pass between bekh's messages. Read the run
(`night/mon.py <run> --once`) before saying anything about it; two wrong statements in one day
came from assuming no time had passed.

**7.3 The page shows her worst face.** The run page's samples are drawn at temperature 1 from
all 50,000 tokens. bekh and Claude both called her bad from those; the same snapshot through the
loom's sampler wrote whole sentences. Judge from the loom, and do not oversell her either.

**7.4 Each shelf's held-out number is the memorising alarm.** A shelf that turns and climbs
while the others fall is being recited. Watch them separately; the average hides it.

**7.5 Only the newest snapshot exists.** By bekh's word the guard deletes the older ones. An age
worth keeping has to be copied aside while it is the newest.

**7.6 The mac's half needs the mac.** `watch.sh` and `pull_ckpt.sh` run under `caffeinate`, need
the VPN up and `KEY` in the environment they are started from; when the mac sleeps the page
goes stale while the run is fine. The trainable save crosses the VPN at 4.3 GB a time —
that is why it goes every six hours and not every hour.

**7.7 The twenty-minute look is part of the run.** The bad learning rate was caught by bekh
asking, not by a monitor. He wants a check every twenty minutes while a run is on.

## 8. Hands and tools

- **zsh does not split unquoted variables.** `$S host cmd` with `S="ssh -i …"` is one word and
  fails; `set -- $pair` leaves `$2` empty; `$B:path` is a modifier — write `"${B}:path"`. Use
  arrays, or write the command out.
- **`pkill -f` kills the shell that runs it** when the pattern is in its own command line. Kill
  by pid.
- **A foreground command gets about five minutes.** Anything longer on a remote host starts
  under `nohup` with a log that ends in a marker (`BUILD5-DONE`), and is waited for with
  `timeout 420 tail -n +1 -f <log> | grep -m1 <marker>`.
- **Agents**: every spawn names `model: 'opus'`; each has about 100,000 tokens, so a fetch that
  will outlast it runs detached with a ledger and a heartbeat; they could not write `.md` into
  the shared checkout, so reports come back as text (the untracked `.claude/settings.json` with
  `worktree.bgIsolation: none` is what lets the main session write in the checkout at all); the brief carries the refusal rule (1.1),
  "no git", "no code comments" and "write only under …".
- **Count what an agent reports.** `wc -w` over its folder agreed with every report to within
  3%; that is the cost of knowing.
