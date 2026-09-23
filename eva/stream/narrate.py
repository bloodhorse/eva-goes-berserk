#!/usr/bin/env -S uv run --python 3.12 --script
"""narrate.py — the stream's ledger as a running commentary, one plain line per row.

`eva go` pipes `tail -F shelf/stream/ledger.jsonl` through this so the terminal says who is
doing what — nemo or gpt2 wrote a dream, codex read it, opus retold the story, codex painted,
the analyst rewrote his portrait — instead
of a bare "dream 3 of 5 landed" (bekh, 2026-09-22: say what is actually going on). Reads json
rows on stdin, writes lines on stdout, never touches the shelf. A half-written row is skipped.

    tail -n0 -F shelf/stream/ledger.jsonl | uv run --python 3.12 eva/stream/narrate.py
"""

from __future__ import annotations

import json
import sys
import time


def when(ts: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts))


def who(model: str | None, fallback: str) -> str:
    m = (model or "").lower()
    if m.startswith("codex"):
        return "codex"
    if m.startswith("opus") or m.startswith("claude"):
        return "opus"
    return m or fallback


def leaf(room: str | None) -> str:
    return (room or "").rsplit("/", 1)[-1]


def line(r: dict) -> str | None:
    k = r.get("kind")
    secs = r.get("seconds")
    t = f" · {secs:.0f}s" if isinstance(secs, (int, float)) else ""
    if k == "page":
        # Two dreamers since 2026-09-23: the row's `model` is the seat that wrote it, and a
        # seat passed over (down, or its window too small) is said too — a gpt-2 that never
        # gets a turn should be visible in the terminal, not only in the ledger.
        dreamer = r.get("model") or ("writer" if r.get("skipped") else "nemo")
        passed = "".join(f" · {s.get('model')} skipped ({s.get('why')})"
                         for s in r.get("skipped") or [] if isinstance(s, dict))
        if r.get("error"):
            return f"{dreamer} · FAILED · {r['error']}{passed}"
        flag = f" · flagged {r['flag']}" if r.get("flag") else ""
        return (f"{dreamer} · wrote {leaf(r.get('room'))} · {r.get('tokens', '?')} tok at heat "
                f"{r.get('temperature', 0):.2f}{t}{flag}{passed}")
    if k == "reading":
        rooms = ", ".join(leaf(x) for x in r.get("rooms") or [])
        if r.get("error"):
            return f"{who(r.get('model'), 'reader')} · reading {rooms} FAILED · {r['error']}"
        name = f' → "{r["name"]}"' if r.get("name") else ""
        return f"{who(r.get('model'), 'reader')} · read {rooms}{name} · {r.get('marked', 0)} marked{t}"
    if k == "dream":
        if r.get("error"):
            return f"opus · retelling FAILED · {r['error']}"
        title = f' "{r["title"]}"' if r.get("title") else ""
        return (f"{who(r.get('model'), 'opus')} · retold story {r.get('chapter', '?')}{title} · "
                f"scene {r.get('turn', '?')} of {r.get('of', '?')}{t}")
    if k == "plate":
        if r.get("error"):
            return f"codex · painting {leaf(r.get('room'))} FAILED · {r['error']}"
        hand = f" · {r['hand'][:40]}" if r.get("hand") else ""
        return f"codex · painted {leaf(r.get('room'))} · prompt {r.get('prompt', '?')}{hand}{t}"
    if k == "plating":
        if r.get("painted"):
            return None                                   # the plate row above already said it
        if r.get("held"):
            return (f"codex · painter holding · {r['held']} · week {r.get('week', '?')}% "
                    f"session {r.get('session', '?')}%")
        return f"codex · painter found nothing to paint"
    if k == "portrait":
        # The analyst, every ten dreams, and his remark said out loud — the line the feed's card
        # carries. A seat other than the public one is an experiment and says which.
        seat = r.get("seat")
        who_ = "the analyst" + (f" ({seat})" if seat and seat != "analyst" else "")
        if r.get("error"):
            return f"{who_} · FAILED · {r['error']}"
        said = f' · "{r["line"]}"' if r.get("line") else ""
        return f"{who_} · {r.get('dreams', '?')} dreams{said}{t}"
    if k == "name":
        return f"{who(r.get('model'), 'namer')} · named {leaf(r.get('room'))} \"{r.get('name', '')}\""
    return None


def main() -> int:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            r = json.loads(raw)
        except ValueError:
            continue
        s = line(r)
        if s:
            print(f"{when(r.get('ts', time.time()))} {s}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
