# handoff — read once, then delete this file

Written 2026-10-07 (15:10 Vietnam, 08:10 UTC) by the session that started `day3`. **Disposable:
read it whole, `trash HANDOFF.md`, commit the removal, and work from `school/CLAUDE.md`,
`school/PITFALLS.md`, `school/library.md` and `BRIEF.md`.** Everything durable is in those; what is
only here is the point we are at this hour, the jobs bekh set, and the things the last session
wanted to build and didn't get to.

## 1. the point we are at

- **`day3` is training on ds-dev2**, a warm start from `ckpt-7896.pt` on fourteen shelves, two
  billion tokens in fifty hours, batch 6 × 4 at about 11.9k tok/s. Started 2026-10-06 19:22 UTC,
  stopped once at step 911 to add three seeds, resumed; at this writing step ~21,000 of 84,103
  (25%), ending around **2026-10-08 20:00 UTC** with a push to the phone. Where she is right now:
  `cd school && uv run -q --python 3.12 python night/mon.py day3 --once` (untested on ds-dev2 — see
  §3), the page `https://miniarch.tail004a72.ts.net:8446/school-day3.html`, or
  `night/turn.py day3` for the per-shelf verdicts. `night/day3/ledger.jsonl` is every status she
  has written.
- **The numbers so far**: overall held-out 3.400 at step 1,000 → 3.30 at 21,000, every shelf
  below where it started, anime under 2, fantasy under 3.03. The rhythm: two evals down, one a
  little back, the floor lower each time. No shelf has turned; fantasy reads `rising` (an outlier
  low at step 16,000 that it is climbing back from). `PITFALLS.md` §7.4 has the noise bands.
- **Five processes**: trainer, wrapper and guard on ds-dev2; `night/watch.sh day3` and
  `night/pull_ckpt.sh day3` on the mac under `caffeinate`. The guard keeps one snapshot
  (`runs/day3/model-<step>-q8_0.gguf`, hourly); the watcher pulls it to
  `school/models/day3/model-latest-q8_0.gguf`; the puller streams the 4.3 GB trainable save to the
  mini every six hours (`night/day3/pull.log`, MATCH). All of it has run for real at least once.
- **The twenty-minute look** was a session cron in the session that wrote this; it died with
  that session. Re-arm it: `/loop 20m` with the prompt in `school/CLAUDE.md` (watching and
  running), and add one line to it: run `night/turn.py day3` and push high only on `turned`.
- **The page** (`night/page.py`): house palette, her age in tokens, cards, a sparkline and a
  verdict per shelf, "the last thing she said", the seeds drawn through the loom's sampler from
  each new snapshot (`night/day3/loomed.jsonl`), the raw draws, the guard log. It rebuilds every
  two minutes while the mac is awake and on the VPN.
- **The loom** (`eva.x`) fans on her as of **step 911**: the mac's `llama-server` on 8086 was
  restarted on that snapshot for the first walk (`shelf/sittings/experiments/magdra-prophecy`
  and `-cut`), and it loads a file once. The restart line is in `school/CLAUDE.md`.
- **The library**: 55 books converted (`inbox/clean/`, 7.5 M tokens, `bins2/library.bin` on
  ds-dev2, read about twice in `day3`); the gaps, the dead files and the three lists are in
  `school/library.md`. bekh fetches by hand into `~/tower/ephemeral/booox/souls_lain_library/`;
  files that arrive after this go through `data/books.py <folder> --out inbox/clean` (it skips
  what is already in the ledger), then `data/health.py inbox/clean`, then upload and `prep.py` on
  ds-dev2 for the finishing school. Claude does not fetch from libgen or help drive a downloader;
  that line was tested twice and holds.
- **ds-dev2**: the work project's `llama-server.service` is stopped for the run (bekh's word);
  one line brings it back, a reboot would too. Per-command rule there except inside
  `/opt/llama/magdra/`. Test leftovers waiting for "delete for good": `runs/smoke`, `runs/smoke2`,
  `runs/.exporttest-20261006` (6 GB).
- **The mini**: `sheets.service` is a systemd user unit now; the archive
  `/srv/music/school-archive/` holds the re-cut Gutenberg text (`gutenberg-cut2-20261006.tar.gz`),
  `modern/`, and `models/day3/ckpt.pt`.
- **The mac** is at 97% disk. Nothing big lands there any more; if something must, ask.

## 2. the jobs bekh set, in order (2026-10-07, 15:00)

1. **The per-shelf turn, acted on.** The detector exists: `night/turn.py <run>` reads the
   ledger, compares each shelf's last three evals with the three before against the shelf's own
   swing (1.5 × its median eval-to-eval change, floor 0.004), and says `learning` / `flat` /
   `rising` / `turned` (`turned` = rising twice over); exit 2 on any `turned`; `--json` for the
   page, which shows the verdict column. What is left is the *action*. Two shapes, bekh to pick:
   - the detector pushes high and a human decides (what we have, minus the push — add it to the
     loop prompt);
   - the trainer acts by itself: `train.py` re-reads a small weights file every eval
     (`runs/<name>/weights.json`, written by the detector or by hand), so a turned shelf can be
     set to zero without a restart. Claude's pick: build the second for `day4` and the finishing
     school, keep the push either way. Stopping the run to keep a pre-turn snapshot is out —
     bekh dropped the history on purpose.
2. **The recitation meter** ("does she talk like it or quote it"). Cut her samples (the loomed
   draws and the raw ones) into eight-word runs and count how many appear verbatim in the text
   she has read. Build it against the small shelves exactly, since that is where recitation
   happens: `inbox/clean/`, `lain/`, the cyborg corpus, `wired-core/`, `modern/released/*/text`,
   `modern/strangehorizons/text` — about 60 M words, a set of 64-bit hashes of eight-grams fits
   in memory on the mac. For the big shelves (`models/box/data/…`, the fan fiction on the mini)
   spot-check a few long runs with `rg -F`. Output: a score per snapshot and a list of the
   quoted runs with their source; a column on the page next to the sampled draws; run it in
   `page.py` when a new snapshot lands, like the loomed draws. Expect near zero now; the
   finishing school is where it earns its keep.
3. **The loom follows her.** When `models/day3/latest` changes, restart the 8086 server on the
   new snapshot (kill the listener by pid, start the same command). Smallest home: a few lines in
   `page.py` next to `loomed()`, since it already runs every two minutes and already notices the
   change. Then `eva.x` is always her newest hour and bekh can read and mark at any time.
4. **Ask ChatGPT about text sources** — the prompt was written in that session's chat
   (casual, the dead ends and the open leads from `docs/research/text-sources-2026-10-06.md`);
   bekh pastes it, the answer gets folded into `docs/research/` and `library.md`'s gaps, not
   kept as a transcript.

## 3. what the last session wanted to build and didn't

- **Per-shelf training loss.** `train.py` logs one training loss for the mix. A per-shelf
  training loss beside the per-shelf held-out one makes the memorising gap visible directly
  (training falling, held-out flat), which is the real detector; the turn detector is a proxy
  for it. One tensor of running means per shelf in the training loop.
- **Held-out hygiene.** The held-out one percent is only unseen if nothing on another shelf
  duplicates it. Check the library against the fan fiction and the fantasy shelf, and the
  released authors against the net shelves, with the same eight-gram hashes as the meter.
- **`mon.py` against ds-dev2.** Adapted (host, dir, key from the environment) but never run in
  that session; the page and the ssh one-liners were used instead. Run it once.
- **The finishing school, designed and scripted.** The talk has not been had. Claude's view,
  held loosely: a short pass, not an adapter; from `day3`'s final save; the library and the
  cyborg corpus at roughly equal weight, Lain under them, the poems out; one to two reads of
  the whole set at about a quarter of `day3`'s rate; the turn detector and the meter both
  watching; read through the loom before any number is believed. A `night/run4.sh` in the shape
  of `run3.sh`.
- **The spine shelf**: A Song of Ice and Fire (when it arrives) plus Wildbow's Pact
  (`modern/released/wildbow/`), tokenised as `bins2/spine.bin`, in the long run, not the
  finishing school.
- **Seeds in bekh's register.** The seven seeds are four paragraphs from the first session and
  three one-liners from night1. bekh wanted seeds of his own (a couple of sentences in his
  voice, no prose from Claude, no web markers); none exist yet. `night/prompts.txt`; a change
  needs the stop-and-resume dance (`PITFALLS.md` 7.1).
- **The page's small things**: pin the life bar's labels to their segments; show the turn
  verdict in the top cards when any shelf is `turned`; the heartbeat card should read the
  save-window speed as such (`PITFALLS.md` 7.4b).
- **Housekeeping**: `inbox/preview/` and `inbox/preview2/` are converter test runs (Trash);
  `night/day3/page-preview*.png` are screenshots (Trash); the ds-dev2 leftovers above.
- **When the run ends**: `school/CLAUDE.md`, Next, "when it ends".

## 4. bekh, this day

- He was up until about five and back at ten. He reads the page on the phone and judges her by
  what he sees there; the raw draws made him say *her spittin still shit*, the sampled draws and
  the walked prophecy changed that, and by the afternoon he called the newest draws *nothing
  short of a breakthrough*. Claude's read, given to him: real but modest, five of nine pairs
  better, no step in the numbers; the likely reason is that she is reading paragraphs for the
  first time. Hold that line; don't oversell her and don't let the page oversell her.
- *Fuck the history, I don't need it; we'll train another model in half a year.* One snapshot,
  decided. Don't reopen.
- His key for the library: *visionary optimistic cyberpunk … the nonchalant attitude toward
  the huge structures … the Prophecies are close to the ideal.* Burning Chrome is back in on it.
- He asked, more than once, to be a partner and not a client: think aloud, argue, bring your own
  list. He also asked for the letter of a rule once (the push on a rise) and then accepted the
  rule being tightened to each shelf's own noise. Say what changed your mind when it changes.
- He gets the books by hand and would like a loophole for automating it; there isn't one, and he
  took that without a fight.
