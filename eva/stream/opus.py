#!/usr/bin/env -S uv run --python 3.12
"""opus.py — the one way the stream's two opus voices talk to the cli, and the one place
their cost is counted.

Both the reader at the bedside (`interpreter.py`) and the sleeper remembering
(`remembering.py`) are `claude -p --model opus` with a prompt on stdin, and both are on a
clock that fires every time a dream lands. bekh wants to see the budget, so the call is here
once, in `--output-format json`, and every caller gets the usage block back with its answer.

**What the numbers mean.** `input_tokens` is small and `cache_read_input_tokens` is large,
because the cli sends its own system prompt and tool preamble ahead of ours on every call and
that bulk is cached. Measuring is the point: our prompt is a few hundred tokens and the call
is several thousand, so the cost of a voice is mostly the cli's overhead and not the dream.

The cli's json is read leniently. With this build (2026-09-19) `--output-format json` answers
a LIST of events ending in `{"type": "result", "result": …, "usage": …, "total_cost_usd": …}`,
and older builds answer that object alone — both are accepted, and so is a bare string, which
is what `--output-format text` would give if somebody drops the flag.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile

# Every flag here was paid for. `--tools ""` and `--strict-mcp-config`: a reader with tools is
# a reader that will go and read the rest of the repo instead of the dream in front of it.
# `--setting-sources project`: without it bekh's global ~/.claude/CLAUDE.md — who he is, how he
# talks, what he is working on — is loaded into the head of somebody asked to read a dream.
CLAUDE = ["claude", "-p", "--model", "opus", "--output-format", "json",
          "--tools", "", "--strict-mcp-config", "--setting-sources", "project"]

# `opus` on the command line is an ALIAS for the latest opus, and it stays an alias: pinning an
# id here would freeze this seat on today's model and we would find out months late. What the
# ledger carries is what actually answered — the cli reports it as `modelUsage.<id>.canonicalModel`
# — so `MODEL` is rewritten by every call (bekh, 2026-09-23: "make sure the opus we're using is
# in fact the fresh one"). A caller reads it AFTER ask() returns, never at import. A cli that
# reports nothing leaves the alias standing, which is also what the fake claude in the tests does.
MODEL = "opus"
ALIAS = "opus"

# The four counters the cli reports and the one it prices. Named here so the ledger rows, the
# readers of the ledger all spell them the same way (counted, never shown: bekh asks, fable reads).
FIELDS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens",
          "output_tokens")


def result_of(raw: str) -> dict:
    """The cli's answer as one object, whichever shape it came in. Raises ValueError."""
    try:
        d = json.loads(raw)
    except ValueError:
        # Not json at all: `--output-format text`, or a wrapper that printed something first.
        return {"result": raw}
    if isinstance(d, list):
        rows = [x for x in d if isinstance(x, dict) and x.get("type") == "result"]
        if not rows:
            raise ValueError("no result event in the cli's json")
        return rows[-1]
    if isinstance(d, dict):
        return d
    raise ValueError("the cli answered json that is neither an object nor a list")


def usage_of(d: dict) -> dict:
    """The counters, flattened and always complete — a missing field is 0 and not absent, so a
    ledger row can be added up without asking whether the key is there."""
    u = d.get("usage") if isinstance(d.get("usage"), dict) else {}
    out = {k: int(u.get(k) or 0) for k in FIELDS}
    cost = d.get("total_cost_usd")
    if isinstance(cost, (int, float)):
        out["cost_usd"] = round(float(cost), 6)
    return out


def model_of(d: dict) -> str:
    """Who actually answered, as the cli reports it, or the alias when it doesn't say.

    `modelUsage` is `{<id>: {..., "canonicalModel": <id>}}` — one entry on an ordinary call, and
    more than one when the cli fell back mid-run, in which case the last one is what wrote the
    end of the answer.
    """
    mu = d.get("modelUsage")
    if not isinstance(mu, dict) or not mu:
        return ALIAS
    key = list(mu)[-1]
    row = mu[key] if isinstance(mu[key], dict) else {}
    name = row.get("canonicalModel") or key
    return name if isinstance(name, str) and name else ALIAS


def ask(prompt: str, timeout: int = 300) -> tuple[str, dict]:
    """One call. `(the text it wrote, the usage block)`. Raises ValueError on anything that is
    not a clean answer — every caller turns that into a ledger row and exit 0.

    CLAUDECODE and CLAUDE_CODE_ENTRYPOINT come out of the env because a claude started from
    inside a claude session refuses to start, and these may be run by hand from one. The cwd is
    a temp dir, so the repo's CLAUDE.md files are not auto-loaded in front of a dream.
    """
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(CLAUDE, input=prompt, capture_output=True, text=True,
                           timeout=timeout, env=env, cwd=tempfile.gettempdir())
    except FileNotFoundError:
        raise ValueError("no `claude` on PATH")
    except subprocess.TimeoutExpired:
        raise ValueError(f"claude timed out after {timeout}s")
    if r.returncode != 0:
        raise ValueError(f"claude exited {r.returncode}: {(r.stderr or '')[-300:]}")
    d = result_of(r.stdout or "")
    text = d.get("result")
    if not isinstance(text, str):
        raise ValueError("the cli's answer carries no result text")
    if d.get("is_error"):
        raise ValueError(f"the cli reported an error: {text[:200]}")
    global MODEL
    MODEL = model_of(d)
    return text, usage_of(d)


def add(into: dict, u: dict) -> dict:
    """Sum usage blocks. Used by the monitor and by usage.py, so the two agree on the total."""
    for k, v in (u or {}).items():
        if isinstance(v, (int, float)):
            into[k] = round(into.get(k, 0) + v, 6) if k == "cost_usd" else into.get(k, 0) + v
    return into


def line(u: dict) -> str:
    """One compact row for a terminal: what went in, what was cached, what came out."""
    cost = f" · ${u['cost_usd']:.4f}" if u.get("cost_usd") else ""
    return (f"in {u.get('input_tokens', 0)} · cache {u.get('cache_read_input_tokens', 0)}"
            f" · new {u.get('cache_creation_input_tokens', 0)}"
            f" · out {u.get('output_tokens', 0)}{cost}")
