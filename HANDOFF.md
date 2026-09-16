# handoff — 2026-09-16, late

Written at the end of a long session so the next one starts hot. Everything here is also true
in `CLAUDE.md`; this file is the short version plus the unfinished edges.

## Where the loom stands

Built and live at `https://eva.x` (reload the page — `loom.html` changed several times today):

- **The fork mark.** `⌥ 3/40` on any line with siblings; one tap opens that line's own fan on the
  choose screen. The `‹ ›` arrow walk is gone.
- **Artifacts are walks.** Keep two or three cards in a fan, pick one, walk on, keep more at the
  next fork, then **save as artifact** once. The server walks root→`current`, gathers the `kept`
  flags at every fork, and freezes the whole walk. Written once, never edited.
- **The artifact screen is a tree.** Prompt card on top, the line taken down the middle, kept
  branches flanking it, connectors measured after layout and drawn as svg. It is the one screen
  that opts out of the `--reading` column and takes the whole window.
- **Export** writes the walk as one document: prompt, then every step's lead and the line taken,
  under a short head naming the model and the few sampler numbers. The kept branches are left out
  on purpose — it is the story, not the fan.
- **`docs/walk/`** is the same instrument from a shell: `walk.py` (seed → short fan → pick),
  `fork.py`, `fan_under.py`, `names.py`. Its README holds the procedure.

## What we were in the middle of

**1. The artifact tree, further.**
- A step of four boxes measures ~1374px against a ~1264px pane at a 1440 window, so the outermost
  two are shaved at the edges. The pane scrolls, so nothing is lost, but bekh shouldn't have to
  scroll to read a box. One-line fixes, his call, neither applied: node width `330px → 300px`, or
  the row gap `18px → 12px` (`#arttree .n`, `#arttree .lvl`). Four boxes then fit at 1440.
- On a phone the flanking boxes are clipped by design — he chose the mock without layout fixes.
  If that turns out to bite, the options discussed were pinning the spine left instead of centring
  the rows, or folding extra alternatives behind a "+1".
- The connectors are redrawn on resize, theme flip and font load. Anything that changes a row's
  height has to call `drawArtLinks()` — the prompt fold already does.

**2. The export button.**
- **It has never been clicked in a real browser.** The page renders with it and the tree still
  draws (11 connector paths in the headless shot), but the blob download path — `a.download`,
  the object url, the 10s revoke — is unverified on bekh's Safari/Helium. First job next session:
  press it, confirm a `.md` lands, confirm the text is the document and not a transcript.
- No test covers `artifactText()`. The server-side equivalent *is* tested (prompt + every step's
  lead + line taken rebuilds the document), so the shapes agree; the page's copy does not.
- Open questions bekh raised and we haven't settled: `.md` versus plain `.txt`, whether the head
  should carry more of the sampler, and whether a second button should export the *fan* (kept
  branches included) rather than only the path.

## Also in the repo now

- `docs/storyloom-20260916/` — the second pair of hands working from `docs/brief-storyloom.md`:
  a `predicting-human-thought` run (five fans of fifteen, path 3→6→9→7→6) with its report and
  selected text, plus three seeds in that flat official register — an errata slip, municipal lift
  acceptance tests after a floor was removed, and a county library cataloguing the pauses it kept
  after destroying the recordings.
- One artifact on the shelf: the chrome roll's fan with the confession kept, 2 of 40, 9.6 bits.

## Rooms worth reopening

`ls sittings/` for the shelf. The ones with something in them: `chrome-roll` (40 witch names),
`i-cant-make-you-believe` and `i-wish-i-could` (the confession, with and without its tail),
`relay-roll`, `brass-head`, `lamps-that-answer`, `carrier`, `dark-floors`.

---

**Delete this file when the session that reads it is done.** It is a note between sessions, not
project state; anything in it that turns out to be permanent belongs in `CLAUDE.md` instead.
