# the stream — what the front serves

The source is bekh's dream stream in eva (`https://eva.x/stream`, the loom on the mac, a read-only mirror on the mini). The front never writes to it.

## Shape

- A **passage** lands roughly every 5 minutes. A **dream** (story) is 4 passages ("turn n of 4").
- Three voices per passage, three columns:
  - **trickle** (bekh's word) — the dream so far, retold; grows each turn. One per dream, not per passage.
  - **text** — the passage itself.
  - **reading** — an interpreter's reading of the passage.
- Each passage should get a **plate** (picture), painted by ChatGPT via codex, usually minutes after its text. Codex budget limits how many get painted, so many passages have none yet.
- Pictures today: palette-knife oil paintings in bekh's house palette.

## API

`GET /api/stream?n=N[&before=<room>][&all=1]` → newest first:

```json
{ "pages": [ { "room": "stream/2026-09-21/1558", "text": "…", "seed": "…", "ts": 1789981106.3,
               "segments": [ { "t": "…", "mark": "touched" | "strange" | true | false } ],
               "reading": { "text": "…", "ts": 1789981200.1 },
               "story": { "dream": "2026-09-21-1547-57af", "text": "…", "turn": 3, "of": 4, "live": true },
               "plate": "/stream/plate/2026-09-21/1552.jpg?v=…" } ],
  "more": true,
  "status": { "state": "dreaming", "since": 1789981106.3, "room": "…", "interval": 300 } }
```

eva's own page loads `n=300` and polls `n=5` every 60s.

`seed` = the found fragment of old text the passage grew from. eva shows it in grey above the passage ("what the dream stood on"); the front hides it behind a button.

## Text rules (ported from eva's page — keep them identical)

- **Marks:** the reader marks at most two runs per passage. **Magenta (`touched`)** = what touched it most; **cyan (`strange`)** = what felt most mysterious and meaningful. Blended into the ink at 30% (`--lit-mix`). Old readings with `mark: true` → first run magenta, second cyan, the rest plain.
- **Trim:** display ends at the last sentence end (`. ! ? …` plus closing quotes), unless that would cut more than ~40%. The shelf keeps everything; this is display only.
- **`[dream]` label:** anything before the last `[dream]` in the segments is dropped.
- Everything goes through `textContent` — the text came back from a cli; none of it may become markup.

## Palette (bekh's house palette, used across his projects)

Violet ground, pink, cyan as highlight. From eva's stylesheet: `#232323` bg · `#d4e3fe` ink · `#7d8a9c` ghost · `#2e3547` line · `#f29bea` / `#f5c8fe` pink · `#7fe3f5` / `#c6f1fe` cyan.

eva's rule for readability over plates (bekh, 2026-09-20): **if text gets hard to read over a bright plate, raise the wash — don't add a text shadow.**
