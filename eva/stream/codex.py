#!/usr/bin/env -S uv run --python 3.12
"""codex.py — the other family's door, and the one place the codex limit is read.

`opus.py` is Claude's door; this is GPT's, and the two are deliberately not one module: they
answer differently, they cost differently, and only one of them has a weekly ceiling that an
unattended job can eat at three in the morning.

bekh, 2026-09-21: *we use opus on the left and opus on the right… how about we use codex for
the summarization of the dreams, so they are two different families.* So the reader at the
bedside can be codex while the sleeper remembering stays opus — one voice from each house,
reading the same dreams.

**Two channels, and only one of them binds.** Codex arrives with a coding agent's system
prompt and a global `~/.codex/AGENTS.md`, and the friendship-is-magic project already paid for
learning how to get out from under them (`docs/decisions-timeline.md`, 2026-08-15, *Codex's
work doctrine is beaten in its own channel, not argued with*):

- `-c base_instructions=<a json-escaped string>` **replaces** the coding-agent system prompt
  outright. That is the weak channel — good for a standing frame, useless against a default —
  and it is also what keeps a three-line note from being billed as a full harness: a plate
  through the whole thing costs 17–36k tokens.
- The strong channel is an instruction document, and **no flag turns the global one off**
  (`--ignore-user-config` only skips `config.toml`). Instruction files stack, project after
  global, so the seat is a folder of ours — `reader-seat/` — whose `AGENTS.md` countermands
  the global one. Four rounds of prompt rewording lost to one countermand in the right file.

Everything else about the call: `--json` for the event stream (the final answer is an
`item.completed` carrying an `agent_message`, and `turn.completed` carries the token counts),
`--sandbox read-only` because a reader has nothing to write, `--skip-git-repo-check` because
the seat is not a repo, the prompt on stdin so quoting never mangles a dream.

Env: STREAM_CODEX_MODEL, STREAM_CODEX_EFFORT, STREAM_CODEX_USAGE, CODEX (the cli's name, for
the tests' stub — the same knob plate.py reads, so one fake serves both).
"""

from __future__ import annotations

import json
import os
import subprocess
import time

HERE = os.path.dirname(os.path.realpath(__file__))              # eva/stream
SEAT = os.path.join(HERE, "reader-seat")
CODEX = os.environ.get("CODEX", "codex")

# A current general model, pinned rather than inherited: bekh's own config.toml says
# `gpt-6-astra` at reasoning `high`, and a margin note is not a reasoning job — high effort
# would buy nothing here and be paid for out of the same weekly ceiling the plates draw on.
MODEL = os.environ.get("STREAM_CODEX_MODEL", "gpt-6-astra")
EFFORT = os.environ.get("STREAM_CODEX_EFFORT", "low")

# The standing frame, in the weak channel. The persona and the dream go in the PROMPT, so the
# opus path and this one send exactly the same words and a note can be read against a note.
BASE_INSTRUCTIONS = """You are a reader in a reading seat.

You are handed a piece of text and a description of how to read it, and you answer with your
reading. That is the whole job. There is no repository, no task, no code and no deliverable.

Do not use tools. Do not read, write or list files, and do not run commands. Do not ask
questions and do not announce what you are about to do.

Answer only in the shape the prompt asks for, and nothing else: no preamble, no summary of
your own answer, no notes about the process."""


def cmd(model: str = "", effort: str = "") -> list[str]:
    """The argv, built in one place so a test can read it and a reader can audit it.

    Exec options come before the prompt; `-` as the prompt means stdin. `-C` is the seat
    folder, which is the whole point of the folder existing: its AGENTS.md is loaded natively
    and stacks on top of the global one.
    """
    return [CODEX, "exec",
            "-c", "base_instructions=" + json.dumps(BASE_INSTRUCTIONS),
            "-c", "model_reasoning_effort=" + json.dumps(effort or EFFORT),
            "-m", model or MODEL,
            "--sandbox", "read-only",
            "--skip-git-repo-check",
            "-C", SEAT,
            "--json", "-"]


def parse(stdout: str) -> tuple[str, dict]:
    """(the agent's final message, the token counts). Raises ValueError.

    The stream is JSONL and a line that is not an event is ignored rather than fatal — codex
    prints its own notices into the same pipe. An `error` event is REMEMBERED and not raised:
    it puts its retries in there mid-stream (*Reconnecting… 2/5*) and then finishes the turn
    perfectly well, which fim.py learned by losing whole answers to the first one.
    """
    text, usage, err = "", {}, ""
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if not isinstance(ev, dict):
            continue
        kind = ev.get("type")
        if kind in ("item.completed", "item_completed"):
            item = ev.get("item") if isinstance(ev.get("item"), dict) else {}
            if str(item.get("type", "")).lower() in ("agent_message", "agentmessage"):
                text = item.get("text") or text
        elif kind in ("turn.completed", "turn_completed"):
            u = ev.get("usage")
            if isinstance(u, dict):
                usage = u
        elif kind == "error":
            err = str(ev.get("message") or "codex reported an error")
    if not text:
        raise ValueError(err or "codex answered no agent message")
    return text, tokens_of(usage)


TOKENS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens",
          "output_tokens", "reasoning_output_tokens")


def tokens_of(u: dict) -> dict:
    """The counters flattened, plus `tokens` — the one number bekh's `cu` limit is spent in.

    Always complete, a missing field being 0 and not absent, so a ledger row of codex rows can
    be added up without asking whether the key is there. Same contract as `opus.usage_of`.
    """
    out = {k: int((u or {}).get(k) or 0) for k in TOKENS}
    total = (u or {}).get("total_tokens")
    out["tokens"] = int(total) if isinstance(total, (int, float)) else \
        out["input_tokens"] + out["output_tokens"]
    return out


def ask(prompt: str, timeout: int = 120) -> tuple[str, dict]:
    """One call. `(the text it wrote, the token counts)`. Raises ValueError on anything that is
    not a clean answer — every caller turns that into a fallback and a ledger row.

    The cwd is the seat, like `-C`: codex resolves its instruction files from the working root
    and there is no reason for the two to disagree.
    """
    try:
        r = subprocess.run(cmd(), input=prompt, capture_output=True, text=True,
                           timeout=timeout, cwd=SEAT)
    except FileNotFoundError:
        raise ValueError(f"no `{CODEX}` on PATH")
    except subprocess.TimeoutExpired:
        raise ValueError(f"codex timed out after {timeout}s")
    if r.returncode != 0:
        raise ValueError(f"codex exited {r.returncode}: {(r.stderr or '')[-300:]}")
    return parse(r.stdout or "")


def line(u: dict) -> str:
    """One compact row for a terminal, the shape `opus.line` has."""
    return (f"in {u.get('input_tokens', 0)} · cached {u.get('cached_input_tokens', 0)}"
            f" · out {u.get('output_tokens', 0)} · {u.get('tokens', 0)} tokens")


# ---- the limit, read by everything that spends it ----------------------------------------------
# One implementation for the painter and the reader both. Two jobs drawing on one weekly
# ceiling must agree on what the ceiling is and on what a missing number means, or the one
# that guesses wrong is the one that eats the week.

# The cache `cu` keeps, refreshed by its own daemon every few minutes. Read here and never
# written: this process is a consumer of that number, not a second source of it.
USAGE = os.environ.get("STREAM_CODEX_USAGE",
                       os.path.expanduser("~/.cache/claude-usage/codex.json"))
# Past this the cache is not a reading of anything. Six of its refresh intervals.
USAGE_STALE = 1800


def usage() -> tuple[dict | None, str]:
    """(the numbers, why they cannot be used). One of the two is always empty."""
    try:
        st = os.stat(USAGE)
    except OSError:
        return None, "no usage cache"
    if time.time() - st.st_mtime > USAGE_STALE:
        return None, f"usage cache {int((time.time() - st.st_mtime) // 60)} min stale"
    try:
        with open(USAGE, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None, "usage cache unreadable"
    if not isinstance(d, dict):
        return None, "usage cache is not an object"
    out = {}
    for k in ("week", "session"):
        v = (d.get(k) or {}).get("utilization") if isinstance(d.get(k), dict) else None
        if not isinstance(v, (int, float)):
            return None, f"usage cache has no {k} utilization"
        out[k] = float(v)
    return out, ""


def held_for(u: dict | None, why: str, week_max: float, session_max: float) -> str:
    """Why this run must not spend anything, or "" to go ahead.

    **No numbers is not a green light** — the failure that matters is an unattended job eating
    a week of the limit at three in the morning, and a cache that has gone missing is exactly
    when nobody is watching. And the SESSION window is the real ceiling, measured 2026-09-21:
    22 plates in 90 minutes tripped the five-hour window at 80% while the week stood at 19%.
    """
    if u is None:
        return why
    if u["week"] >= week_max:
        return f"week at {u['week']:g}%"
    if u["session"] >= session_max:
        return f"session at {u['session']:g}%"
    return ""
