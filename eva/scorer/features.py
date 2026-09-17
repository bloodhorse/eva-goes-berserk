# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
"""Cards in, vectors out.

Reads rooms from the shelf, turns every model node into one feature vector per
(source, variant), and caches the vectors on disk keyed by the text itself — so a
rerun next month only pays for the cards that are new.

Not part of the loom. The loom is stdlib-only; this is an analysis tool and may
have numpy under it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SHELF = Path(os.environ.get("EVA_SHELF", ROOT / "shelf"))
SITTINGS = SHELF / "sittings"
CACHE = SHELF / "scorer" / "cache"

# Where each source lives while it is up. Nothing is started automatically: these
# servers are hand-started and killed by pid (see CLAUDE.md), because two of them
# are big enough to matter on a 16 GB box.
SOURCES = {
    # nomic-embed-text-v1.5, mean-pooled, 768 dims. A sentence embedder: it knows
    # what a card is about. Wants its task prefix or the vectors drift off the
    # manifold it was trained on.
    "nomic": {"url": "http://127.0.0.1:8085/embedding", "prefix": "search_document: "},
    # GPT-2 XL's last hidden state at the last token, 1600 dims. Not trained to be
    # an embedding at all — it is the state a base model is in when it has just
    # read the card.
    "gpt2": {"url": "http://127.0.0.1:8086/embedding", "prefix": ""},
    # Nemo's own last hidden state, 5120 dims. The writer's own read of the card.
    "nemo": {"url": "http://127.0.0.1:8087/embedding", "prefix": ""},
}

VARIANTS = ("card", "seedcard")
SEED_TAIL_WORDS = 100  # ~100 tokens of seed; cut back to a sentence boundary

# --- config, not math -------------------------------------------------------
# The two marks do not mean the same thing: `●` is "i liked it", `★` is "it made
# me feel something". But `●` did not exist yet when bekh read these three rooms,
# so there he used `★` for everything he liked — 28 of the 39 stars on the shelf.
# In these rooms a star is demoted to grade 1 and star-only metrics are skipped.
# DELETE A ROOM FROM THIS LIST once bekh has re-read it with both marks; nothing
# else needs changing, the math reads this.
STAR_MEANS_MARKED = {
    "experiments/three-models/07-the-green-book",
    "experiments/three-models/10-madmans-diary",
    "experiments/three-models/11-scotts-diary",
}


@dataclass
class Card:
    room: str  # path relative to shelf/sittings, without .json
    node: str
    text: str
    seed: str  # the room's root text (the document every card continues)
    model: str | None
    temperature: float | None
    good: bool
    kept: bool

    @property
    def marked(self) -> bool:
        return self.good or self.kept

    @property
    def true_star(self) -> bool:
        """A star that means what a star means now. See STAR_MEANS_MARKED."""
        return self.kept and self.room not in STAR_MEANS_MARKED

    @property
    def grade(self) -> int:
        """0 unmarked, 1 liked, 2 felt something. The target for everything ranked."""
        return 2 if self.true_star else (1 if self.marked else 0)

    @property
    def star_room(self) -> bool:
        """Was this room read in the two-mark era? Star metrics only count there."""
        return self.room not in STAR_MEANS_MARKED

    @property
    def key(self) -> str:
        """Cache key: which card, and which exact text. If bekh edits a card's text
        the hash changes and it gets re-embedded instead of silently reusing a stale
        vector."""
        h = hashlib.sha1(self.text.encode("utf-8")).hexdigest()[:16]
        return f"{self.room}|{self.node}|{h}"


def seed_tail(seed: str, words: int = SEED_TAIL_WORDS) -> str:
    """The last ~`words` words of the document, forwarded to a sentence start.

    Cutting mid-sentence would hand the embedder a fragment that starts nowhere;
    the seam matters in this project, so the tail begins where a sentence does
    when one is close enough."""
    toks = seed.split()
    if len(toks) <= words:
        return seed.strip()
    tail = " ".join(toks[-words:])
    m = re.search(r"[.!?][\"'’”)]?\s+", tail[: len(tail) // 2])
    return (tail[m.end():] if m else tail).strip()


def text_for(card: Card, variant: str) -> str:
    if variant == "card":
        t = card.text
    elif variant == "seedcard":
        t = seed_tail(card.seed) + "\n" + card.text
    else:
        raise ValueError(f"unknown variant {variant!r}")
    # One card in the three-model run is empty. llama-server refuses empty content,
    # and an empty card is still a card bekh looked at and did not mark.
    return t if t.strip() else "\n"


def load_rooms(folders: list[str]) -> list[Card]:
    """Every model node in every room under the given folders (relative to
    shelf/sittings). Folders, not files, so next month's rooms are picked up by
    naming their folder."""
    cards: list[Card] = []
    for folder in folders:
        base = SITTINGS / folder
        # A folder means every room under it; a room may also be named directly,
        # with or without the .json — blind_view names single rooms.
        if base.is_dir():
            paths = sorted(base.rglob("*.json"))
        else:
            paths = [p for p in (base, base.with_suffix(".json")) if p.is_file()]
            if not paths:
                print(f"  nothing at {base}", file=sys.stderr)
        for p in paths:
            if ".trash" in p.parts:
                continue
            try:
                d = json.loads(p.read_text())
            except (json.JSONDecodeError, OSError) as e:
                print(f"  skipped {p}: {e}", file=sys.stderr)
                continue
            nodes = d.get("nodes") or {}
            root = nodes.get(d.get("root"), {})
            seed = root.get("text") or ""
            room = str(p.relative_to(SITTINGS).with_suffix(""))
            for nid, n in nodes.items():
                if n.get("kind") != "model" or n.get("pruned"):
                    continue
                meta = n.get("meta") or {}
                params = meta.get("params") or {}
                cards.append(Card(
                    room=room, node=nid, text=n.get("text") or "", seed=seed,
                    model=meta.get("model"),
                    temperature=params.get("temperature"),
                    good=bool(n.get("good")), kept=bool(n.get("kept")),
                ))
    return cards


def drop_unmarked_rooms(cards: list[Card]) -> list[Card]:
    """A room with no marks is not a room of dislikes — it may be a room bekh never
    read. Training on it would teach the scorer that every card in it is bad."""
    rooms: dict[str, list[Card]] = {}
    for c in cards:
        rooms.setdefault(c.room, []).append(c)
    keep: list[Card] = []
    for room, cs in sorted(rooms.items()):
        if any(c.marked for c in cs):
            keep.extend(cs)
        else:
            print(f"  room with no marks, skipped: {room} ({len(cs)} cards)", file=sys.stderr)
    return keep


# ---------------------------------------------------------------- embedding


def _post(url: str, payload: dict, timeout: int = 180) -> object:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _vector(out: object) -> np.ndarray:
    """llama-server's /embedding answers [{index, embedding: [[...]]}] with pooling
    on and [[tok, tok, ...]] with pooling none. Accept both shapes and mean any
    leftover token axis, so a server started without --pooling still gives a vector
    rather than a crash three hours in."""
    if isinstance(out, dict):
        out = out.get("data", out.get("embedding"))
    if isinstance(out, list) and out and isinstance(out[0], dict):
        out = out[0].get("embedding")
    a = np.asarray(out, dtype=np.float32)
    while a.ndim > 1:
        a = a.mean(axis=0)
    return a


def embed_many(texts: list[str], url: str, workers: int = 4) -> np.ndarray:
    """One request per text. llama-server has four slots, so four in flight keeps
    it busy without queueing; larger batches gain nothing and lose the ability to
    name which text blew up."""
    def one(t: str) -> np.ndarray:
        for attempt in range(3):
            try:
                return _vector(_post(url, {"content": t}))
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                if attempt == 2:
                    raise
        raise RuntimeError("unreachable")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return np.vstack(list(pool.map(one, texts)))


def cache_path(source: str, variant: str) -> Path:
    return CACHE / f"{source}-{variant}.npz"


def load_cache(source: str, variant: str) -> dict[str, np.ndarray]:
    p = cache_path(source, variant)
    if not p.exists():
        return {}
    z = np.load(p, allow_pickle=False)
    return {k: v for k, v in zip(z["keys"].tolist(), z["vecs"])}


def save_cache(source: str, variant: str, store: dict[str, np.ndarray]) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    keys = sorted(store)
    np.savez_compressed(cache_path(source, variant),
                        keys=np.array(keys), vecs=np.vstack([store[k] for k in keys]))


def features(cards: list[Card], source: str, variant: str,
             url: str | None = None, quiet: bool = False) -> np.ndarray:
    """The matrix for these cards, in their order. Hits the server only for keys the
    cache does not already hold."""
    spec = SOURCES[source]
    url = url or spec["url"]
    store = load_cache(source, variant)
    wanted = [(c.key, spec["prefix"] + text_for(c, variant)) for c in cards]
    missing = [(k, t) for k, t in wanted if k not in store]
    if missing:
        if not quiet:
            print(f"  {source}/{variant}: embedding {len(missing)} new "
                  f"({len(wanted) - len(missing)} cached)", file=sys.stderr)
        vecs = embed_many([t for _, t in missing], url)
        for (k, _), v in zip(missing, vecs):
            store[k] = v
        save_cache(source, variant, store)
    elif not quiet:
        print(f"  {source}/{variant}: all {len(wanted)} cached", file=sys.stderr)
    return np.vstack([store[k] for k, _ in wanted])


def l2(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.where(n == 0, 1.0, n)


# ------------------------------------------------------------------- checks


def sanity(source: str, url: str | None = None) -> str:
    """Prove the pooling is what we think it is before trusting a whole run:
    same text twice is the same vector, two texts differ, the norm is finite."""
    url = url or SOURCES[source]["url"]
    pre = SOURCES[source]["prefix"]
    a1 = _vector(_post(url, {"content": pre + "the moon is a door"}))
    a2 = _vector(_post(url, {"content": pre + "the moon is a door"}))
    b = _vector(_post(url, {"content": pre + "a telephone hums in an empty hall"}))
    same = float(np.abs(a1 - a2).max())
    cos = float(a1 @ b / (np.linalg.norm(a1) * np.linalg.norm(b) + 1e-9))
    return (f"{source}: dim={a1.shape[0]} norm={np.linalg.norm(a1):.3f} "
            f"repeat-max-diff={same:.2e} cos(other)={cos:.3f} "
            f"{'OK' if same < 1e-4 and abs(cos) < 0.999 and np.isfinite(a1).all() else 'SUSPECT'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="embed cards and fill the cache")
    ap.add_argument("--folders", nargs="+", default=["experiments/three-models"])
    ap.add_argument("--sources", default="nomic")
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--sanity", action="store_true", help="probe the servers only")
    a = ap.parse_args()
    sources = a.sources.split(",")
    if a.sanity:
        for s in sources:
            print(sanity(s))
        return
    cards = drop_unmarked_rooms(load_rooms(a.folders))
    print(f"{len(cards)} cards, {sum(c.marked for c in cards)} marked, "
          f"{sum(c.kept for c in cards)} kept", file=sys.stderr)
    for s in sources:
        for v in a.variants.split(","):
            x = features(cards, s, v)
            print(f"{s}/{v}: {x.shape}")


if __name__ == "__main__":
    main()
