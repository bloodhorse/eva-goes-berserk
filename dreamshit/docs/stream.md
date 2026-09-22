# the stream — what the front serves

The source is bekh's dream stream in eva (`https://eva.x/stream`, the loom on the mac, a read-only mirror on the mini). The front never writes to it. **How it's made lives once, in `../eva/stream/CLAUDE.md`** — the writer (top), the interpreter ("The interpreter"), the sleeper who retells the story ("The sleeper remembering"), the plates ("Plates"); the root `CLAUDE.md` map says how the names and numbers work. This file keeps only the front's side: what arrives, and how it must be shown.

## Shape, as the front uses it

A **passage** every ~5 minutes; a **dream** (story) is 4 of them. Three voices, three columns: the **trickle** (bekh's word — the sleeper's retelling of the story so far, one per dream, growing each turn) on the left, the **text** in the centre, the **reading** (the interpreter's note) on the right. A **plate** (painting) arrives minutes after its text, or never — the painter runs under a codex budget.

## API

`GET /api/stream?n=N[&before=<room>][&all=1]` → newest first:

```json
{ "pages": [ { "room": "stream/2026-09-21/1558", "text": "…", "seed": "…", "name": "the body man", "verse": "10:4", "ts": 1789981106.3,
               "segments": [ { "t": "…", "mark": "touched" | "strange" | true | false } ],
               "reading": { "text": "…", "ts": 1789981200.1 },
               "story": { "dream": "2026-09-21-1547-57af", "text": "…", "title": null, "chapter": 10, "turn": 3, "of": 4, "live": true },
               "plate": "/stream/plate/2026-09-21/1552.jpg?v=…" } ],
  "more": true,
  "status": { "state": "dreaming", "since": 1789981106.3, "room": "…", "interval": 300 } }
```

`GET /api/stream/events` → the same stream, pushed. `text/event-stream`, held open, `Cache-Control: no-cache`, `X-Accel-Buffering: no`:

```
: open

event: change
data: {"rooms": ["stream/2026-09-21/1753"], "status": {"state": "dreaming", "since": …, "room": …, "interval": 300}}

: keepalive
```

One `change` within ~2s of anything landing, carrying the rooms whose fingerprint moved or appeared (the room file, its reading, its story, its name, its plate — whatever `/api/stream` would show differently) and the same `status` object. A status-only change (the writer fell asleep) comes with `"rooms": []`. A `: keepalive` comment every 20s keeps cloudflare and caddy from closing a quiet connection. It's a GET, so the read-only mirror serves it exactly as the mac does — which is where this front reads it from.

eva's own page loads `n=300` and still polls `n=5` every 60s; this front listens instead.

**Names** (eva's convention, mirrored by the front): each passage has a `name` and a `verse` (`chapter:turn`), shown at the top of its text as `10:4 · the body man` — number grey, name ink; the name is the first thing read and what a dream is chosen by. Each dream has a `chapter` and a `title` (still null as of 2026-09-21), shown heading its trickle, a size bigger.

`seed` = the found fragment of old text the passage grew from. eva shows it in grey above the passage ("what the dream stood on"); the front hides it behind a button.

## Text rules (ported from eva's page — keep them identical)

- **Marks:** the reader marks at most two runs per passage. **Magenta (`touched`)** = what touched it most; **cyan (`strange`)** = what felt most mysterious and meaningful. Blended into the ink at 30% (`--lit-mix`). Old readings with `mark: true` → first run magenta, second cyan, the rest plain.
- **Trim:** display ends at the last sentence end (`. ! ? …` plus closing quotes), unless that would cut more than ~40%. The shelf keeps everything; this is display only.
- **`[dream]` label:** anything before the last `[dream]` in the segments is dropped.
- **Lowercase on display** (bekh, 2026-09-22): every voice is shown lowercase by one CSS rule (`text-transform`); the shelf keeps its capitals — a starred passage becomes a seed, and a capital there is text nemo sees.
- Everything goes through `textContent` — the text came back from a cli; none of it may become markup.

## Palette (bekh's house palette, used across his projects)

Violet ground, pink, cyan as highlight. From eva's stylesheet: `#232323` bg · `#d4e3fe` ink · `#7d8a9c` ghost · `#2e3547` line · `#f29bea` / `#f5c8fe` pink · `#7fe3f5` / `#c6f1fe` cyan.

eva's rule for readability over plates (bekh, 2026-09-20): **if text gets hard to read over a bright plate, raise the wash — don't add a text shadow.**
