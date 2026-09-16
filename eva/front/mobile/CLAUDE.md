# mobile

Know-how for making the pages we build — the loom at `eva.x`, anything on the sheets site, any
self-hosted page — actually work on a phone, and for **checking that from the mac without
holding a phone**. Born from the loom's mobile pass (2026-09-15, `~/tower/forge/eva-goes-berserk`,
commit `2e1b434`): the page was "mostly fine" on the iPhone, with the edit button sitting on top
of the text, and it took one real review rig to find the other seven problems.

The rule this folder exists for: **judge a phone layout from screenshots at true phone sizes,
never from reading CSS.** Every bug below was invisible in the code and obvious in a shot.

## The shot rig

`rig/shoot.sh` + `rig/seed.py` are the loom's working copies — loom-shaped (its routes, its
mock sitting), kept as the reference to adapt, not a generic tool. The recipe inside them is
general, and every line of it was paid for:

1. **Desktop Helium won't make a window narrower than ~500px.** Ask for 390 and it silently lays
   out at ~500 and crops, so text looks cut mid-word at the right edge and you chase a fake
   overflow bug. Fix: put the page in an **iframe of the exact phone size** (media queries follow
   the frame's width), centre it in a wider window, crop the centre back out with `sips`:
   ```bash
   printf '<!doctype html><style>html,body{margin:0;height:100%%}body{display:flex;justify-content:center}iframe{border:0;width:390px;height:844px}</style><iframe src="http://127.0.0.1:PORT/#STATE"></iframe>' > wrap.html
   /Applications/Helium.app/Contents/MacOS/Helium --headless=new --disable-gpu --hide-scrollbars \
     --no-first-run --user-data-dir=/tmp/prof-$RANDOM --enable-logging=stderr --v=0 \
     --window-size=600,844 --virtual-time-budget=5000 --screenshot=out.png "file://$PWD/wrap.html"
   sips -c 844 390 out.png
   ```
2. **One `--user-data-dir` per browser.** Two headless instances on one profile deadlock on the
   profile lock; the second one hung for 35 minutes before anyone noticed.
3. **Shoot one at a time.** Four headless browsers in parallel starve each other's virtual time
   and hand back half-loaded frames — the page with no state applied, or blank.
4. **The state to shoot rides in the URL hash** as js, and one script appended to a *copy* of the
   page waits for the app to be ready and evals it. One page serves every shot.
5. **No timers in that script.** Headless virtual time stops before a 1.2 s `setTimeout` fires
   (the log said "ready after 1 poll", then nothing). Poll every 50 ms for a real readiness
   condition — the data loaded *and* the DOM rendered — and apply the state in that same tick.
6. **No async state.** A state that fetches (open a note) lands after the screenshot. Load it with
   a **synchronous XHR** in the injected helper instead.
7. **Headless Helium often hangs on exit after writing the screenshot, and ignores SIGTERM.**
   Poll for the png, then `kill -9` the pid. Never `pkill -f` (see the global CLAUDE.md).
8. **`wait` on the shot pids only.** A bare `wait` also waits on the page server and the stub
   started in the background, which never exit — the loop froze after one batch.
9. **Log, don't guess.** The injected script `console.log`s a `DBG` line — whether the state ran,
   `documentElement.scrollWidth` vs `innerWidth` — and `--enable-logging=stderr` puts it in the
   browser's stderr. `scrollWidth == innerWidth` in every shot is the proof nothing scrolls
   sideways; a png alone can't show that.
10. **Contact sheets, not twenty files:** `magick a.png b.png c.png -background '#000' -splice 8x0 +append sheet.png`
    (plain append needs no fonts — `magick montage` died looking for one). Then `kkmosaic` the
    sheets into kitty for bekh.
11. **Serve a scratch copy** of the app against a stub backend and a seeded mock (never the real
    data dir), on its own port, and check the ports are free afterwards with
    `lsof -ti tcp:PORT -sTCP:LISTEN`.

**What to shoot** — every screen in every state, not just the home screen: the main view at
the bottom and scrolled to the top, every menu and panel open, every confirm, every in-place
editor, a long input growing, an error notice, each secondary screen (view, edit, new), long
unbroken strings (urls, tokens) in every text surface. Sizes: **390×844** (iPhone), **360×740**
(small Android), **844×390** (phone on its side), **768×1024** (tablet portrait).

## What headless can't prove

Headless desktop is a mouse browser at a small size. It **can't** show: `(hover:none)` and
`(pointer:coarse)` rules, iOS's zoom into small fields, what the return key does, safe-area
insets, the on-screen keyboard eating `dvh`. Those get reasoned from platform facts, written
down in the commit, and **one tap-through on the real phone** — say plainly which ones weren't
seen.

## Phone bugs we've actually hit, and the fix

- **Controls in a side margin overlap text once the margin shrinks.** The loom's "edit" word
  and `‹ 2/3 ›` walk lived in 36px margins and were wider than them. Fix: below ~900px, make each
  block a small grid — text, tags, then one row with the controls — so they're in the flow:
  `grid-template-areas:"body body" "foot foot" "gut swipe"`. Nothing absolutely positioned near
  text on a phone.
- **Hover-only controls don't exist on touch.** `opacity:0` until `:hover` means never on an
  iPhone — and an iPad in landscape is wider than any width breakpoint. Key it on the input, not
  the width: `@media (hover:none){ .controls{opacity:1} }`, and give tap targets room there.
- **iOS Safari zooms the whole page into any field under 16px** on focus. `@media (hover:none){ input, select, textarea{font-size:16px} }`.
  Check every field, including selects and ones generated by js.
- **iOS inflates text in landscape.** `html{-webkit-text-size-adjust:100%; text-size-adjust:100%}`.
- **Return-to-send makes line breaks impossible on a phone** (no shift key). On touch, let return
  insert the newline and let the button send:
  `const TOUCH = matchMedia('(hover: none) and (pointer: coarse)')` and bail from the keydown
  handler when `TOUCH.matches`.
- **Anything `position:fixed` at the bottom covers the composer.** A notice pinned bottom-centre
  sat on the text box and the send button. On phones put it at the top, full width, under the
  corner button.
- **Negative margins for optical alignment clip at a 12px phone margin** — the back arrow's
  focus ring was cut by the screen edge. Zero them in the small-screen block.
- **A phone on its side is ~390px tall.** Portrait top padding plus a composer left 214px to
  read. `@media (max-height:500px)` trims the chrome.
- **Long unbroken strings push the page sideways**: `overflow-wrap:anywhere` on every text
  surface, `min-width:0` on flex children.
- **Safe areas**: `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`,
  then `env(safe-area-inset-*)` in `max()` on anything fixed to an edge.
