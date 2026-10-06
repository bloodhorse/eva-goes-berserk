import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path.home() / "eva-olmo" / "school" / "fanfic"
TMP = ROOT / "tmp"
REPO = "marianna13/fanfics"
HF = "/opt/llama/tools/hf/bin/hf"
MIN_FREE = 25 * 1024**3
SHARD_ROOM = 2 * 1024**3


def free_bytes():
    return shutil.disk_usage("/").free


def wait_for_room(log):
    while free_bytes() < MIN_FREE + SHARD_ROOM:
        log(f"low disk {free_bytes() / 1e9:.1f} GB free, waiting")
        time.sleep(60)


def download(name, log):
    wait_for_room(log)
    d = TMP / key(name)
    d.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["HF_HOME"] = str(Path.home() / "eva-olmo" / "hf-home")
    env["HF_XET_HIGH_PERFORMANCE"] = "1"
    for attempt in range(6):
        r = subprocess.run(
            [HF, "download", REPO, name, "--repo-type", "dataset", "--local-dir", str(d)],
            env=env, capture_output=True, text=True, timeout=900,
        )
        p = d / name
        if r.returncode == 0 and p.exists():
            return d, p
        log(f"download failed {name} attempt {attempt}: {r.stderr[-300:]}")
        time.sleep(20 * (attempt + 1))
    raise RuntimeError(f"download failed {name}")


def cleanup(d):
    shutil.rmtree(d, ignore_errors=True)


def key(name):
    parts = name.split("-")
    return f"{parts[1]}-{parts[2]}"
