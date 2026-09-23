#!/usr/bin/env -S uv run --python 3.12
"""deepseek.py — the analyst's second door: deepseek v3.2 over openrouter, the wire that sits
in the third chair at friendship-is-magic's couch (`fim.py`, ENDPOINT_SEATS[ASH]), carried here.

bekh, 2026-09-23: *fresh blood* — he has read too much of one family's prose, and the analyst
is the voice he reads most. So the seat can be deepseek instead of opus, same prompts to the
byte; what differs is only the door.

**There is no session on the far side.** `/chat/completions` is stateless, so the caller
carries the whole conversation and sends it every time — `analyst.py` keeps it as
`messages.json` in the seat, which is the resumed session done honestly: the transcript on disk
IS the memory, and the router caches the prefix on its side.

**The pin is the seat.** No lab hosts v3.2 on openrouter, so an unpinned route serves whatever
quant the cheapest host loaded that hour; `provider.order` + `allow_fallbacks: false` is what
makes tomorrow's portrait the same model as yesterday's. `reasoning.effort: none` — a
step-by-step dump is not a margin voice. Two throws bought on the couch and kept: a backend
behind that pin sometimes answers with no `finish_reason` and half a sentence, so a reasonless
reply is rethrown (three throws at most), and a reply the caller says is not whole is rethrown
once.

**The key never enters the environment.** Read from the login keychain at the moment of the
call (`security find-generic-password -s OPENROUTER_API_KEY -w`), into a local that dies with
the frame, never logged, never written. On the mini the same key is a 0600 file; this door runs
on the mac, where the analyst's job is.

Env: OPENROUTER_URL, OPENROUTER_KEYCHAIN (the keychain service name), STREAM_DEEPSEEK_MODEL,
STREAM_DEEPSEEK_PROVIDER, STREAM_DEEPSEEK_MAX_TOKENS.
"""

from __future__ import annotations

import http.client
import json
import os
import subprocess
import urllib.parse
from collections.abc import Callable

URL = os.environ.get("OPENROUTER_URL", "https://openrouter.ai/api")
KEYCHAIN = os.environ.get("OPENROUTER_KEYCHAIN", "OPENROUTER_API_KEY")
ASKED = os.environ.get("STREAM_DEEPSEEK_MODEL", "deepseek/deepseek-v3.2")
PROVIDER = os.environ.get("STREAM_DEEPSEEK_PROVIDER", "GMICloud")
# A portrait is two paragraphs and a remark, ~600 tokens; this is a ceiling, not a target.
MAX_TOKENS = int(os.environ.get("STREAM_DEEPSEEK_MAX_TOKENS", "2000"))
TRIES = 3

# Who answered, as the gateway reports it, and which host served — rewritten by every call,
# read by the caller after ask() returns (the opus door's MODEL rule).
MODEL = ASKED
SERVED = ""

FIELDS = ("prompt_tokens", "completion_tokens", "cached_tokens")


def key() -> str:
    r = subprocess.run(["security", "find-generic-password", "-a", os.environ.get("USER", ""),
                        "-s", KEYCHAIN, "-w"], capture_output=True, text=True)
    k = (r.stdout or "").strip()
    if not k:
        raise ValueError(f"no key in the login keychain under {KEYCHAIN}")
    return k


def usage_of(d: dict) -> dict:
    """The counters, flattened and always complete, in openrouter's names. `cached_tokens` is
    what the router served from its prefix cache; `cost` is openrouter's own price in dollars."""
    u = d.get("usage") if isinstance(d.get("usage"), dict) else {}
    det = u.get("prompt_tokens_details") if isinstance(u.get("prompt_tokens_details"), dict) else {}
    out = {"prompt_tokens": int(u.get("prompt_tokens") or 0),
           "completion_tokens": int(u.get("completion_tokens") or 0),
           "cached_tokens": int(det.get("cached_tokens") or 0)}
    cost = u.get("cost")
    if isinstance(cost, (int, float)):
        out["cost_usd"] = round(float(cost), 6)
    return out


def error_of(payload: bytes) -> str:
    try:
        d = json.loads(payload)
    except ValueError:
        return payload[:300].decode("utf-8", "replace")
    e = d.get("error") if isinstance(d, dict) else None
    if isinstance(e, dict):
        return str(e.get("message") or e)[:300]
    return str(e or d)[:300]


def ask(messages: list[dict], timeout: int = 600,
        whole: Callable[[str], bool] | None = None) -> tuple[str, dict]:
    """One call over the whole conversation. `(the text, the usage)`. Raises ValueError on
    anything that is not a clean answer — the caller turns that into a ledger row and exit 0.

    `whole(text)` says whether a reply is complete (the analyst's: it ends on `</remark>`); a
    reply that is not gets one more throw, a reply with no finish reason gets up to three.
    """
    body = {"model": ASKED, "messages": messages, "max_tokens": MAX_TOKENS,
            "provider": {"order": [PROVIDER], "allow_fallbacks": False},
            "reasoning": {"effort": "none"},
            "usage": {"include": True}}
    raw = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + key()}
    parts = urllib.parse.urlsplit(URL.rstrip("/"))
    opener = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection

    def post() -> tuple[int, bytes]:
        conn = opener(parts.hostname or "127.0.0.1", parts.port, timeout=timeout)
        try:
            conn.request("POST", (parts.path or "") + "/v1/chat/completions", body=raw,
                         headers=headers)
            resp = conn.getresponse()
            return resp.status, resp.read()
        except TimeoutError:
            raise ValueError(f"openrouter timed out after {timeout}s")
        except (OSError, http.client.HTTPException) as exc:
            raise ValueError(f"openrouter at {URL}: {exc}")
        finally:
            conn.close()

    tries, cut_throw = 0, False
    while True:
        tries += 1
        status, payload = post()
        if status != 200:
            raise ValueError(f"openrouter answered {status}: {error_of(payload)}")
        try:
            d = json.loads(payload)
        except ValueError as exc:
            raise ValueError(f"could not read openrouter's answer: {exc}")
        choice = (d.get("choices") or [{}])[0]
        choice = choice if isinstance(choice, dict) else {}
        text = (choice.get("message") or {}).get("content") or ""
        finish = choice.get("finish_reason")
        if tries >= TRIES:
            break
        if not isinstance(finish, str) or not finish.strip():
            continue                      # the truncating backend's tell: another throw
        if whole is not None and text.strip() and not cut_throw and not whole(text):
            cut_throw = True
            continue
        break
    if not text.strip():
        raise ValueError(error_of(payload) or "openrouter returned an empty reply")
    global MODEL, SERVED
    m = d.get("model")
    MODEL = m if isinstance(m, str) and m else ASKED
    s = d.get("provider")
    SERVED = s.strip() if isinstance(s, str) else ""
    return text, usage_of(d)


def line(u: dict) -> str:
    cost = f" · ${u['cost_usd']:.4f}" if u.get("cost_usd") else ""
    return (f"in {u.get('prompt_tokens', 0)} · cached {u.get('cached_tokens', 0)}"
            f" · out {u.get('completion_tokens', 0)}{cost}")
