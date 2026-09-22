# dreamshit — the dream stream's published face

The front for bekh's dream stream. In eva, a machine dreams out loud: every ~5 minutes a new passage of a four-part dream, with a retelling of the dream so far (the **trickle**), an interpreter's **reading**, and a painting per passage. This project is how that stream is *read*: three voices in three columns, paintings living behind the words, a CRT / wired / lain-adjacent atmosphere that is its own thing, and above all effortless reading. Everything in a dream is made by neural networks (LLMs write, ChatGPT paints via codex); our job is the room it's read in.

It lives in eva-goes-berserk as `dreamshit/`, beside `eva/`, `shelf/` and `docs/` — not the instrument (`eva/` is the lab bench) and not text for us, but the published face, named after the door: `https://dreamshit.net`, bekh's domain, public since 2026-09-22 through a Cloudflare tunnel from the mini (`https://dreamshit.x` on the tailnet is the same files, the private twin; `docs/front.md` has where and how). It reads eva's stream over its api and never writes to it. Moved in from its own repo `~/tower/forge/dreamst` on 2026-09-22 by `git subtree`, history kept. A session here doesn't need the root `BRIEF.md`; the root `CLAUDE.md` map is worth having — the front should know what a room, a mark and a plate are. eva's own `/stream` page stays as the placeholder until this front does everything it does.

## How we work here

Two partners, equal minds. bekh's ideas and mine weigh the same: I bring my own taste and objections without waiting to be asked, and hold them until an argument moves them. bekh is the source on what bekh feels; on what looks good, reads well or will work, nobody outranks anybody. We search loosely — nothing about the style is final, and every look or font we try is shelved as a preset, never deleted, because a verdict on one page can flip on another.

Visual work gets judged by eye: screenshots go to `shots/`, opened in Finder for bekh (not kitty).

## Docs — open what the task needs

- `docs/stream.md` — the source as the front sees it: the API shape, the display rules (marks, trimming), the house palette; pointers into eva for the producer side.
- `docs/front.md` — the project: where it runs, deploy and rollback, files, packs and the trickle, focus, every knob.
- `docs/looks.md` — pictures: style-in-the-glass principle, the look presets with verdicts, the wash, parked neural filters.
- `docs/reading.md` — type and calm: the no-motion rule, the font search, why wash and font are coupled.
- `docs/fauux.md` — the reference we studied: how it's made, its mechanics as primitives, what survived.
- `docs/lab.md` — sketches, tools, and the headless screenshot tricks.

## Where we stand (rewrite this in place)

- Chosen: newsreader for the passage (labels in spaced Courier); glass at 8px for unfocused plates, dots one click away; focus follows reading; trickle pinned at its dream's start, 60% of its column; quiet voices in `#aab5c7`; a quiet `pic` next to `seed` opens the painting; reader's marks and names as on eva; seed behind a button; the full painting by `pic` only (double-click let go); one plain arrow cursor everywhere; nothing moves on its own.
- **The trickle runs beside its dreams, in parts (2026-09-22, bekh's ideal, now built):** one continuous telling, the sleeper marking his seams with `|`, cut there and laid out part n beside passage n — the part that belongs to a dream is always on that dream's left. `docs/front.md` has the layout and the mismatch rules, `docs/stream.md` the api. Beside it, as a fallback and not the default: **stretch** (bekh's idea the same day, built, verdict pending) — the seams ignored, the whole telling as one thread stretched to reach the bottom of the dream's last passage, by three dials in order: narrow the column, then one word to a line, then open the leading. A 45-word telling beside four scenes comes out as single words paced down the whole dream. `?trickle=stretch` or key `g`; `shots/stretch/` is what it looks like.
- Open, in this order: **bekh's size for newsreader** (now 19px; `,`/`.` live, then bake it in) → **the wash**: my proposal on the table is an auto wash that reads each plate's brightness behind the words and washes only as much as it needs (`w`/`W` would tune the target contrast), built as a preset beside the fixed `--wa` and judged side by side — the single global number is a compromise between dark and bright plates → name the rest of the font shortlist ("some others").
- **Public, done (2026-09-22): `dreamshit.net` is this front, live, reading eva through the same two api paths `dreamshit.x` uses**, via the mirror on the mini. The old line "fed by a pushed feed, never the loom exposed" was not bekh's phrasing and is out — his: the front is connected to eva via the api, that is the site, and it may expand from there. The one open item is in `docs/front.md`: Cloudflare's browser-cache TTL switch.
- **Push, not poll (2026-09-22, bekh's call):** every landing on the mac taps the mirror push, and the page holds `/api/stream/events` open instead of polling every minute (`docs/stream.md`).
- Agreed ideas, not built: text arriving live with the tail forgotten (no archive), clickable depth (a side column comes forward), decay that eats words — each must pass the reading rule.
