# dream engine (dreamst)

The front for bekh's dream stream. In eva, a machine dreams out loud: every ~5 minutes a new passage of a four-part dream, with a retelling of the dream so far (the **trickle**), an interpreter's **reading**, and a painting per passage. This project is how that stream is *read*: three voices in three columns, paintings living behind the words, a CRT / wired / lain-adjacent atmosphere that is its own thing, and above all effortless reading. Everything in a dream is made by neural networks (LLMs write, ChatGPT paints via codex); our job is the room it's read in.

It lives as its own project (`front/`, live at `https://dreamshit.x`), reading eva without touching it. Merging into eva's own page comes later.

## How we work here

Two partners, equal minds. bekh's ideas and mine weigh the same: I bring my own taste and objections without waiting to be asked, and hold them until an argument moves them. bekh is the source on what bekh feels; on what looks good, reads well or will work, nobody outranks anybody. We search loosely — nothing about the style is final, and every look or font we try is shelved as a preset, never deleted, because a verdict on one page can flip on another.

Visual work gets judged by eye: screenshots go to `shots/`, opened in Finder for bekh (not kitty).

## Docs — open what the task needs

- `docs/stream.md` — the source: passage/dream shape, the API, eva's text rules (marks, trimming), the house palette.
- `docs/front.md` — the project: where it runs, deploy and rollback, files, packs and the sticky trickle, focus, every knob.
- `docs/looks.md` — pictures: style-in-the-glass principle, the look presets with verdicts, the wash, parked neural filters.
- `docs/reading.md` — type and calm: the no-motion rule, the font search, why wash and font are coupled.
- `docs/fauux.md` — the reference we studied: how it's made, its mechanics as primitives, what survived.
- `docs/lab.md` — sketches, tools, and the headless screenshot tricks.

## Where we stand (rewrite this in place)

- Chosen: glass at 8px for unfocused plates, dots one click away; focus follows reading; trickle sticky per dream at 60% of its column; reader's marks as on eva; double-click for the full painting; nothing moves on its own.
- Open, in this order: **pick the passage font** (first round: only `lain` came close, not there yet) → **settle the wash** for that font (even vs hug, darkness) → check the sticky trickle live on long dreams.
- Agreed ideas, not built: text arriving live with the tail forgotten (no archive), clickable depth (a side column comes forward), decay that eats words — each must pass the reading rule.
