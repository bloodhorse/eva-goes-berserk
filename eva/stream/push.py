#!/usr/bin/env -S uv run --python 3.12
"""push.py — tap the mirror the moment something lands, instead of letting it wait for a timer.

The mac pushes the shelf to the mini every 60 seconds (`com.bekh.eva-mirror`, running
`eva/mirror/push.sh`), and the mini is what `dreamshit.net` and the phone read. Everything the
stream writes therefore reached a reader somewhere between nought and sixty seconds after it was
written, for no reason but the length of a timer. So every landing calls `now()` here and the
push leaves at once: a passage, a note, a rewritten story, a plate, a name.

**The timer stays.** It is still the path home for marks made on the mirror — push.sh takes the
mirror's journal before it rsyncs — so the minute is what carries a star back to the mac. This
only stops a landing from waiting for it.

**No `-k`.** launchd will not start a second instance of a job that is already running, so a kick
that arrives mid-push is simply dropped and the next minute's timer carries that change over. A
`-k` would kill an rsync halfway instead, which is the one outcome worth avoiding. Nothing here
retries and nothing here is ever an error the caller sees: a failed kick costs one landing up to
sixty seconds, which is exactly what we had before.

**Where this lives, and why it is its own file.** None of the stream's existing shared doors is
imported by all five writers — `opus.py` is the opus cli (the painter and the worker never call
it), `codex.py` is the other family's, `loom.py` is the shelf and knows nothing about launchd
jobs, and `stream.py`, which already taps the three voices, is imported by nobody. One function
with no dependencies is the smallest honest home, and it keeps the job's name in one place.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

JOB = "com.bekh.eva-mirror"
TIMEOUT = 15

# A run against a scratch shelf is a test or a hand experiment, and neither has anything to do
# with what the mini serves — pushing the real shelf because a test wrote a fake room would be
# a surprise with a network in it. Production sets none of these (the plists carry PATH, HOME
# and their own dials and nothing else), so the rule is: any override at all, no push.
SCRATCH = ("STREAM_DIR", "LOOM_SITTINGS", "LOOM_STORAGE", "LOOM_ARTIFACTS", "LOOM_LEDGER",
           "LOOM_CANVASES", "LOOM_PAGE", "LOOM_STREAM_PAGE")


def wanted() -> bool:
    """Whether a push is this machine's business at all.

    Off when the shelf is a scratch one, off when `STREAM_PUSH=0`, and off wherever there is no
    `launchctl` — the voices run under launchd on the mac and nowhere else, so on the mini or in
    a container this is not a failure, it is a no-op.
    """
    if os.environ.get("STREAM_PUSH") == "0":
        return False
    if any(os.environ.get(k) for k in SCRATCH):
        return False
    return shutil.which("launchctl") is not None


def now() -> bool:
    """Kick the push job. True if launchctl took it. Never raises, never exits non-zero."""
    if not wanted():
        return False
    cmd = ["launchctl", "kickstart", f"gui/{os.getuid()}/{JOB}"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"push · {exc}", file=sys.stderr, flush=True)
        return False
    if r.returncode != 0:
        print(f"push · launchctl said {r.returncode}: {(r.stderr or '').strip()[:120]}",
              file=sys.stderr, flush=True)
        return False
    return True


if __name__ == "__main__":
    sys.exit(0 if now() else 1)
