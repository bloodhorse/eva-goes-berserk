# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scikit-learn"]
# ///
"""The one command. Re-embeds what is new, retrains, rewrites the report.

    uv run --python 3.12 eva/scorer/curve.py --folders experiments/three-models

The whole question this answers: does a small scorer trained on bekh's marks get
better as it gets more of them. Everything here is leave-one-room-out, always,
because room identity is the big confound — mark rates run from 13% to 47% by
room, so a scorer tested on a room it trained on can look brilliant by learning
"this is the madman room".
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import features as F  # noqa: E402

N_GRID = (50, 100, 150, 200, 270)
DRAWS = 30
PERMUTATIONS = 200
FIXED_BUDGET = 6  # 20% of a thirty-card fan — "if i only read six, how many land"

# The five rooms the reviewing model read blind of bekh's marks as well as of the
# model names. The other five it read after seeing his marks, so its score there
# is not a clean comparison.
FABLE_CLEAN = {
    "experiments/three-models/07-the-green-book",
    "experiments/three-models/10-madmans-diary",
    "experiments/three-models/11-scotts-diary",
    "experiments/three-models/12-blue-boar",
    "experiments/three-models/07-all-ive-got-are-names",
}

CANDIDATE_C = (0.03, 0.3, 3.0)
CANDIDATE_PCA = (None, 16, 32, 64)
CANDIDATE_CENTRE = (False, True)


# ------------------------------------------------------------------ metrics


def precision_at(scores: np.ndarray, hits: np.ndarray, k: int) -> float | None:
    """Of the k cards the scorer would show, how many did bekh mark."""
    if k <= 0 or k > len(scores):
        return None
    top = np.argsort(-scores, kind="stable")[:k]
    return float(hits[top].sum()) / k


def mean_rank(scores: np.ndarray, hits: np.ndarray) -> float | None:
    """Average position of the marked cards in the ranking, 1 = top. Chance is
    (n+1)/2, so 15.5 in a thirty-card fan."""
    if not hits.any():
        return None
    order = np.argsort(-scores, kind="stable")
    ranks = np.empty(len(scores))
    ranks[order] = np.arange(1, len(scores) + 1)
    return float(ranks[hits].mean())


def ndcg(scores: np.ndarray, grades: np.ndarray) -> float | None:
    """How well the whole ranking respects ★ > ● > nothing."""
    if grades.max() <= 0:
        return None

    def dcg(g: np.ndarray) -> float:
        return float((g / np.log2(np.arange(2, len(g) + 2))).sum())

    got = grades[np.argsort(-scores, kind="stable")]
    return dcg(got) / dcg(np.sort(grades)[::-1])


def auc(scores: np.ndarray, hits: np.ndarray) -> float | None:
    if hits.all() or not hits.any():
        return None
    return float(roc_auc_score(hits, scores))


def room_metrics(scores: np.ndarray, marked: np.ndarray, grades: np.ndarray,
                 stars: np.ndarray, star_room: bool) -> dict[str, float | None]:
    """Everything one held-out fan can say about one ranking of it."""
    m = {
        "p_at_k": precision_at(scores, marked, int(marked.sum())),
        "p_at_6": precision_at(scores, marked, FIXED_BUDGET),
        "auc": auc(scores, marked),
        "mean_rank": mean_rank(scores, marked),
        "ndcg": ndcg(scores, grades),
    }
    # Star metrics only where the two marks both existed when bekh read the room.
    if star_room and stars.any():
        m["star_p_at_k"] = precision_at(scores, stars, int(stars.sum()))
        m["star_auc"] = auc(scores, stars)
        m["star_mean_rank"] = mean_rank(scores, stars)
    else:
        m["star_p_at_k"] = m["star_auc"] = m["star_mean_rank"] = None
    return m


def agg(rows: list[dict[str, float | None]]) -> dict[str, tuple[float, float, int]]:
    """mean, spread, n — over rooms and draws. The spread is what decides whether
    any of this is distinguishable from chance, so it never gets dropped."""
    out = {}
    for key in ("p_at_k", "p_at_6", "auc", "mean_rank", "ndcg",
                "star_p_at_k", "star_auc", "star_mean_rank"):
        vals = [r[key] for r in rows if r.get(key) is not None]
        if vals:
            out[key] = (float(np.mean(vals)), float(np.std(vals)), len(vals))
    return out


# ------------------------------------------------------------------- models


def fit_score(xtr: np.ndarray, ytr: np.ndarray, xte: np.ndarray,
              c: float, n_pca: int | None, sample_weight: np.ndarray | None = None
              ) -> np.ndarray:
    """Standardise, optionally shrink, then L2 logistic regression. Tiny on
    purpose: 300 points can be memorised by anything bigger."""
    sc = StandardScaler().fit(xtr)
    a, b = sc.transform(xtr), sc.transform(xte)
    if n_pca:
        k = min(n_pca, a.shape[0] - 1, a.shape[1])
        if k >= 2:
            p = PCA(n_components=k, random_state=0).fit(a)
            a, b = p.transform(a), p.transform(b)
    clf = LogisticRegression(C=c, max_iter=2000, class_weight="balanced")
    clf.fit(a, ytr, sample_weight=sample_weight)
    return clf.decision_function(b)


def fit_rank(xtr: np.ndarray, gtr: np.ndarray, rooms_tr: np.ndarray,
             xte: np.ndarray, c: float, n_pca: int | None) -> np.ndarray:
    """A pairwise ranker on the graded target. Every within-room pair where one
    card outranks the other becomes a difference vector; a logistic regression
    through the origin on those differences is a ranking direction.

    Within-room only, on purpose: it can never learn "the madman room is good",
    only what separates two cards of the same fan. ★ over ● is a pair too, so
    stars pull harder than circles without any hand-set weight."""
    sc = StandardScaler().fit(xtr)
    a, b = sc.transform(xtr), sc.transform(xte)
    if n_pca:
        k = min(n_pca, a.shape[0] - 1, a.shape[1])
        if k >= 2:
            p = PCA(n_components=k, random_state=0).fit(a)
            a, b = p.transform(a), p.transform(b)
    diffs, labels = [], []
    for room in np.unique(rooms_tr):
        idx = np.flatnonzero(rooms_tr == room)
        for i in idx:
            for j in idx:
                if gtr[i] > gtr[j]:
                    diffs.append(a[i] - a[j])
                    labels.append(1)
                    diffs.append(a[j] - a[i])
                    labels.append(0)
    if len(set(labels)) < 2:
        return np.zeros(len(b))
    clf = LogisticRegression(C=c, max_iter=2000, fit_intercept=False)
    clf.fit(np.vstack(diffs), np.array(labels))
    return b @ clf.coef_[0]


# The candidate family. One name per (track, centring, pca, C); the winner is
# picked by inner cross-validation on training rooms only, never on a test room.
def candidates(track: str) -> list[dict]:
    return [{"track": track, "centre": ce, "pca": p, "C": c}
            for ce in CANDIDATE_CENTRE for p in CANDIDATE_PCA for c in CANDIDATE_C]


def name_of(cfg: dict) -> str:
    return (f"{cfg['track']}{'/centred' if cfg['centre'] else '/raw'}"
            f"{'/pca' + str(cfg['pca']) if cfg['pca'] else ''}/C={cfg['C']}")


# --------------------------------------------------------------------- data


class Deck:
    """The cards, their labels, and one feature matrix — raw and room-centred."""

    def __init__(self, cards: list[F.Card], x: np.ndarray):
        self.cards = cards
        self.rooms = np.array([c.room for c in cards])
        self.marked = np.array([c.marked for c in cards])
        self.stars = np.array([c.true_star for c in cards])
        self.grades = np.array([c.grade for c in cards])
        self.star_room = {c.room: c.star_room for c in cards}
        x = F.l2(x.astype(np.float64))
        self.raw = x
        centred = x.copy()
        for room in np.unique(self.rooms):
            m = self.rooms == room
            centred[m] -= x[m].mean(axis=0)
        self.centred = centred

    def matrix(self, centre: bool) -> np.ndarray:
        return self.centred if centre else self.raw

    def room_list(self) -> list[str]:
        return sorted(set(self.rooms.tolist()))


def draw(deck: Deck, train_rooms: list[str], n: int, rng: random.Random) -> np.ndarray:
    """n training cards, stratified by room, so a draw is not accidentally eight
    rooms out of nine."""
    per = {r: np.flatnonzero(deck.rooms == r).tolist() for r in train_rooms}
    for v in per.values():
        rng.shuffle(v)
    picked: list[int] = []
    i = 0
    while len(picked) < n:
        added = False
        for r in train_rooms:
            if i < len(per[r]) and len(picked) < n:
                picked.append(per[r][i])
                added = True
        if not added:
            break
        i += 1
    return np.array(sorted(picked))


def run_cfg(deck: Deck, cfg: dict, tr: np.ndarray, te: np.ndarray) -> np.ndarray:
    x = deck.matrix(cfg["centre"])
    if cfg["track"] == "rank":
        return fit_rank(x[tr], deck.grades[tr], deck.rooms[tr], x[te],
                        cfg["C"], cfg["pca"])
    y = deck.marked[tr]
    if len(set(y.tolist())) < 2:
        return np.zeros(len(te))
    # A star is worth three circles when the target is binary — the amendment's
    # weighting, so "made me feel something" outweighs "liked it" even here.
    w = np.where(deck.grades[tr] == 2, 3.0, 1.0)
    return fit_score(x[tr], y, x[te], cfg["C"], cfg["pca"], sample_weight=w)


def select(deck: Deck, track: str, train_rooms: list[str], n: int,
           rng: random.Random) -> dict:
    """Inner cross-validation: the nine training rooms split three ways by room,
    every candidate scored on rooms it did not see. Test rooms are never involved."""
    groups = [train_rooms[i::3] for i in range(3)]
    best, best_score = None, -1.0
    for cfg in candidates(track):
        vals = []
        for g in groups:
            inner_tr_rooms = [r for r in train_rooms if r not in g]
            tr = draw(deck, inner_tr_rooms, min(n, sum(deck.rooms == r for r in inner_tr_rooms).sum()), rng)
            te = np.flatnonzero(np.isin(deck.rooms, g))
            if len(tr) < 8:
                continue
            s = run_cfg(deck, cfg, tr, te)
            # Score the candidate room by room, the way it will be judged outside.
            for r in g:
                m = deck.rooms[te] == r
                v = (ndcg(s[m], deck.grades[te][m]) if track == "rank"
                     else auc(s[m], deck.marked[te][m]))
                if v is not None:
                    vals.append(v)
        if vals and np.mean(vals) > best_score:
            best, best_score = cfg, float(np.mean(vals))
    return best or candidates(track)[0]


def evaluate(deck: Deck, track: str, n_grid=N_GRID, draws=DRAWS,
             seed=0, verbose=True) -> dict[int, dict]:
    """Leave one room out, n training cards from the other nine, `draws` random
    draws each. Returns the aggregate per n plus which config kept winning."""
    out: dict[int, dict] = {}
    rooms = deck.room_list()
    for n in n_grid:
        rows, chosen = [], []
        for held in rooms:
            train_rooms = [r for r in rooms if r != held]
            pool = int(np.isin(deck.rooms, train_rooms).sum())
            n_eff = min(n, pool)
            rng = random.Random(hash((seed, held, n)) & 0xFFFFFFFF)
            cfg = select(deck, track, train_rooms, n_eff, rng)
            chosen.append(name_of(cfg))
            te = np.flatnonzero(deck.rooms == held)
            # At n = the whole pool the draw is not random any more, so one draw
            # is the whole story; spending thirty on it would only fake precision.
            n_draws = 1 if n_eff >= pool else draws
            for d in range(n_draws):
                tr = draw(deck, train_rooms, n_eff, random.Random(hash((seed, held, n, d)) & 0xFFFFFFFF))
                s = run_cfg(deck, cfg, tr, te)
                rows.append(room_metrics(s, deck.marked[te], deck.grades[te],
                                         deck.stars[te], deck.star_room[held]))
        out[n] = {"metrics": agg(rows), "configs": chosen, "rows": rows}
        if verbose:
            m = out[n]["metrics"]
            print(f"    n={n:3d}  P@k={m['p_at_k'][0]:.3f}  AUC={m.get('auc', (float('nan'),))[0]:.3f}",
                  file=sys.stderr)
    return out


def permutation_test(deck: Deck, track: str, cfg: dict, n_perm=PERMUTATIONS,
                     seed=0) -> dict:
    """Shuffle the labels inside each room and run the same pipeline. Anything the
    real pipeline scores that the shuffled one also scores is room structure, not
    taste."""
    rooms = deck.room_list()

    def one_pass(marked: np.ndarray, grades: np.ndarray, stars: np.ndarray) -> float:
        vals = []
        for held in rooms:
            tr = np.flatnonzero(deck.rooms != held)
            te = np.flatnonzero(deck.rooms == held)
            x = deck.matrix(cfg["centre"])
            if cfg["track"] == "rank":
                s = fit_rank(x[tr], grades[tr], deck.rooms[tr], x[te], cfg["C"], cfg["pca"])
            else:
                w = np.where(grades[tr] == 2, 3.0, 1.0)
                s = fit_score(x[tr], marked[tr], x[te], cfg["C"], cfg["pca"], sample_weight=w)
            p = precision_at(s, marked[te], int(marked[te].sum()))
            if p is not None:
                vals.append(p)
        return float(np.mean(vals))

    real = one_pass(deck.marked, deck.grades, deck.stars)
    rng = np.random.default_rng(seed)
    null = []
    for _ in range(n_perm):
        marked, grades, stars = deck.marked.copy(), deck.grades.copy(), deck.stars.copy()
        for r in rooms:
            idx = np.flatnonzero(deck.rooms == r)
            perm = rng.permutation(idx)
            marked[idx], grades[idx], stars[idx] = deck.marked[perm], deck.grades[perm], deck.stars[perm]
        null.append(one_pass(marked, grades, stars))
    null = np.array(null)
    return {"real": real, "null_mean": float(null.mean()), "null_sd": float(null.std()),
            "p": float(((null >= real).sum() + 1) / (n_perm + 1)), "n_perm": n_perm}


# ------------------------------------------------------- the other contestants


def meta_matrix(cards: list[F.Card]) -> np.ndarray:
    """The cheap facts: which model wrote it, how hot, how long. If this does as
    well as the embeddings, the embeddings have learned nothing."""
    models = sorted({c.model for c in cards if c.model})
    rows = []
    for c in cards:
        one_hot = [1.0 if c.model == m else 0.0 for m in models]
        rows.append(one_hot + [float(c.temperature or 0.0),
                               math.log1p(len(c.text)),
                               math.log1p(len(c.text.split()))])
    return np.array(rows)


def fable_ledger(path: Path) -> dict[str, set[str]]:
    """The reviewing model's blind picks, room -> node ids, out of its ledger."""
    picks: dict[str, set[str]] = {}
    room = None
    for line in path.read_text().splitlines():
        h = re.match(r"^##\s+(\S+)", line)
        if h:
            room = f"experiments/three-models/{h.group(1)}"
            picks[room] = set()
        elif room and (m := re.match(r"^-\s+`([0-9a-f]+)`", line)):
            picks[room].add(m.group(1))
    return picks


def score_picks(deck: Deck, picks: dict[str, set[str]], rooms: list[str]) -> dict:
    """Precision, recall and star catch of a reader's picks over a set of rooms."""
    tp = n_picks = n_marks = star_tp = n_stars = 0
    for room in rooms:
        idx = np.flatnonzero(deck.rooms == room)
        chosen = picks.get(room, set())
        for i in idx:
            c = deck.cards[i]
            in_pick = c.node in chosen
            n_picks += in_pick
            n_marks += c.marked
            tp += in_pick and c.marked
            if deck.star_room[room]:
                n_stars += c.true_star
                star_tp += in_pick and c.true_star
    return {
        "precision": tp / n_picks if n_picks else None,
        "recall": tp / n_marks if n_marks else None,
        "picks": n_picks, "marks": n_marks,
        "star_recall": star_tp / n_stars if n_stars else None,
        "stars": n_stars, "star_hits": star_tp,
    }


# ------------------------------------------------------------------ selftest


def selftest() -> None:
    """A bug that flatters us is worse than no scorer at all. Synthetic labels
    that depend on one feature dimension must come out near AUC 1; random labels
    near 0.5. If this ever fails, no number in the report means anything."""
    rng = np.random.default_rng(7)
    cards, mats = [], []
    for r in range(10):
        for i in range(30):
            v = rng.normal(size=32)
            good = v[0] > 0.9
            cards.append(F.Card(room=f"synthetic/room{r}", node=f"n{r}_{i}",
                                text="x", seed="s", model="nemo", temperature=1.4,
                                good=bool(good), kept=False))
            mats.append(v)
    deck = Deck(cards, np.array(mats))
    cfg = {"track": "logreg", "centre": False, "pca": None, "C": 1.0}
    aucs = []
    for held in deck.room_list():
        tr = np.flatnonzero(deck.rooms != held)
        te = np.flatnonzero(deck.rooms == held)
        s = run_cfg(deck, cfg, tr, te)
        a = auc(s, deck.marked[te])
        if a is not None:
            aucs.append(a)
    signal = float(np.mean(aucs))

    shuffled = list(cards)
    lab = rng.permutation([c.good for c in cards])
    noise_cards = [F.Card(room=c.room, node=c.node, text="x", seed="s", model="nemo",
                          temperature=1.4, good=bool(l), kept=False)
                   for c, l in zip(shuffled, lab)]
    deck2 = Deck(noise_cards, np.array(mats))
    aucs = []
    for held in deck2.room_list():
        tr = np.flatnonzero(deck2.rooms != held)
        te = np.flatnonzero(deck2.rooms == held)
        s = run_cfg(deck2, cfg, tr, te)
        a = auc(s, deck2.marked[te])
        if a is not None:
            aucs.append(a)
    noise = float(np.mean(aucs))

    print(f"selftest: signal AUC={signal:.3f} (want >0.9), noise AUC={noise:.3f} (want ~0.5)")
    assert signal > 0.9, f"signal AUC {signal} — the pipeline cannot see a planted feature"
    assert 0.35 < noise < 0.65, f"noise AUC {noise} — the pipeline scores random labels"
    print("selftest: PASS")


# ------------------------------------------------------------------- report


def bar(v: float, lo: float, hi: float, width: int = 28) -> str:
    frac = 0.0 if hi <= lo else max(0.0, min(1.0, (v - lo) / (hi - lo)))
    n = int(round(frac * width))
    return "#" * n + "." * (width - n)


def fmt(m: dict, key: str) -> str:
    if key not in m:
        return "  —  "
    mean, sd, _ = m[key]
    return f"{mean:.3f}±{sd:.2f}"


def main() -> None:
    ap = argparse.ArgumentParser(description="the scorer's learning curve")
    ap.add_argument("--folders", nargs="+", default=["experiments/three-models"])
    ap.add_argument("--sources", default="nomic,gpt2,nemo,meta")
    ap.add_argument("--variants", default="card,seedcard")
    ap.add_argument("--out", default=None)
    ap.add_argument("--draws", type=int, default=DRAWS)
    ap.add_argument("--perm", type=int, default=PERMUTATIONS)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        selftest()
        return

    cards = F.drop_unmarked_rooms(F.load_rooms(a.folders))
    print(f"{len(cards)} cards in {len(set(c.room for c in cards))} rooms; "
          f"{sum(c.marked for c in cards)} marked, {sum(c.kept for c in cards)} ★ raw, "
          f"{sum(c.true_star for c in cards)} ★ counted", file=sys.stderr)

    decks: dict[str, Deck] = {}
    for src in a.sources.split(","):
        if src == "meta":
            decks["meta/facts"] = Deck(cards, meta_matrix(cards))
            continue
        for var in a.variants.split(","):
            try:
                decks[f"{src}/{var}"] = Deck(cards, F.features(cards, src, var))
            except Exception as e:  # a source whose server never came up
                print(f"  {src}/{var} unavailable: {e}", file=sys.stderr)

    any_deck = next(iter(decks.values()))
    rooms = any_deck.room_list()

    results: dict[str, dict[str, dict]] = {}
    for name, deck in decks.items():
        results[name] = {}
        for track in ("logreg", "rank"):
            print(f"  {name} [{track}]", file=sys.stderr)
            results[name][track] = evaluate(deck, track, draws=a.draws)

    # The permutation test rides on the best source×variant by P@k at the top n.
    best_name = max(results, key=lambda n: max(
        results[n][t][N_GRID[-1]]["metrics"]["p_at_k"][0] for t in results[n]))
    best_track = max(results[best_name],
                     key=lambda t: results[best_name][t][N_GRID[-1]]["metrics"]["p_at_k"][0])
    modal = max(set(results[best_name][best_track][N_GRID[-1]]["configs"]),
                key=results[best_name][best_track][N_GRID[-1]]["configs"].count)
    cfg = next(c for c in candidates(best_track) if name_of(c) == modal)
    print(f"  permutation test on {best_name} [{modal}]", file=sys.stderr)
    perm = permutation_test(decks[best_name], best_track, cfg, n_perm=a.perm)

    # The other reader.
    ledger = fable_ledger(F.ROOT / "docs" / "ledgers" / "three-models.md")
    fable_all = score_picks(any_deck, ledger, rooms)
    fable_clean = score_picks(any_deck, ledger, [r for r in rooms if r in FABLE_CLEAN])

    # Chance, and the cheap facts.
    base = {}
    for r in rooms:
        idx = np.flatnonzero(any_deck.rooms == r)
        base[r] = float(any_deck.marked[idx].mean())
    chance = float(np.mean(list(base.values())))

    by_model: dict[str, list] = defaultdict(list)
    by_temp: dict[float, list] = defaultdict(list)
    for c in cards:
        by_model[c.model or "?"].append(c)
        by_temp[c.temperature or 0].append(c)

    out = Path(a.out or (F.ROOT / "docs" / "scorer" / f"curve-{date.today().isoformat()}.md"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(cards, rooms, base, chance, results, perm, best_name,
                          best_track, modal, fable_all, fable_clean, by_model,
                          by_temp, any_deck, a))
    print(f"wrote {out}", file=sys.stderr)
    json.dump({k: {t: {n: v["metrics"] for n, v in tv.items()} for t, tv in kv.items()}
               for k, kv in results.items()},
              open(out.with_suffix(".json"), "w"), indent=1, default=str)


def render(cards, rooms, base, chance, results, perm, best_name, best_track, modal,
           fable_all, fable_clean, by_model, by_temp, deck, args) -> str:
    L: list[str] = []
    w = L.append
    n_top = N_GRID[-1]
    w(f"# the scorer's curve — {date.today().isoformat()}")
    w("")
    w("A side road, run once on the marks that exist. No strong claims: two readers, "
      f"{len(cards)} cards, ten rooms. Everything below is leave-one-room-out — every "
      "number is a room the scorer had never seen.")
    w("")
    w("Made by `eva/scorer/curve.py`; what the numbers mean and how to rerun is in "
      "`eva/scorer/CLAUDE.md`.")
    w("")
    w("## the data")
    w("")
    w("| room | cards | marked | rate | ★ counted |")
    w("|---|---|---|---|---|")
    for r in rooms:
        idx = np.flatnonzero(deck.rooms == r)
        note = "" if deck.star_room[r] else " *(★=marked era)*"
        w(f"| `{r.split('/')[-1]}`{note} | {len(idx)} | {int(deck.marked[idx].sum())} | "
          f"{deck.marked[idx].mean():.0%} | {int(deck.stars[idx].sum())} |")
    w(f"| **all ten** | {len(cards)} | {int(deck.marked.sum())} | {deck.marked.mean():.0%} | "
      f"{int(deck.stars.sum())} |")
    w("")
    w(f"Mark rate by room runs {min(base.values()):.0%}–{max(base.values()):.0%}. That spread "
      "is the confound the whole design is built around.")
    w("")
    w("**The star caveat.** `●` did not exist when bekh read "
      + ", ".join(f"`{r.split('/')[-1]}`" for r in sorted(F.STAR_MEANS_MARKED))
      + " — there `★` meant \"i liked it\", which is 28 of the 39 stars on the shelf. Those "
      "stars are counted as grade 1 and star-only metrics skip those rooms, leaving "
      f"**{int(deck.stars.sum())} true stars in {sum(1 for r in rooms if deck.star_room[r])} rooms**. "
      "Far too few to train on or to conclude anything from; the star columns below are "
      "printed because they were asked for, not because they carry weight.")
    w("")
    w("## the scoreboard")
    w("")
    w("`P@k` — of the k cards a reader shows, how many bekh marked, where k is the number he "
      "marked in that room; recall at that k is equal to it by construction. `P@6` — a fixed "
      "20% budget. `±` is the spread across rooms and draws, not a standard error.")
    w("")
    w("| contestant | P@k | P@6 | AUC | ★ P@k | ★ mean rank | NDCG |")
    w("|---|---|---|---|---|---|---|")
    w(f"| **chance** | {chance:.3f} | {chance:.3f} | 0.500 | — | 15.5 | — |")
    w(f"| fable reading blind, ten rooms | {fable_all['precision']:.3f} | — | — | — | — | — |")
    w(f"| fable, five rooms blind of his marks | {fable_clean['precision']:.3f} | — | — | — | — | — |")
    for name in results:
        for track in results[name]:
            for n in (100, 200, n_top):
                m = results[name][track][n]["metrics"]
                w(f"| {name} · {track} · n={n} | {fmt(m,'p_at_k')} | {fmt(m,'p_at_6')} | "
                  f"{fmt(m,'auc')} | {fmt(m,'star_p_at_k')} | {fmt(m,'star_mean_rank')} | "
                  f"{fmt(m,'ndcg')} |")
    w("")
    w(f"fable, ten rooms: {fable_all['picks']} picks, {fable_all['precision']:.0%} of them "
      f"bekh's, caught {fable_all['recall']:.0%} of his {fable_all['marks']} marks"
      + (f"; of the {fable_all['stars']} true stars it caught {fable_all['star_hits']} "
         f"({fable_all['star_recall']:.0%})" if fable_all['star_recall'] is not None else "")
      + ".")
    w(f"fable, the five rooms it read blind of his marks: {fable_clean['picks']} picks, "
      f"{fable_clean['precision']:.0%} his, caught {fable_clean['recall']:.0%} of "
      f"{fable_clean['marks']} marks.")
    w("")
    w("## the curves")
    w("")
    w("P@k against the number of training cards. Chance is the floor; the bar is scaled "
      f"{chance - 0.1:.2f}–{chance + 0.25:.2f}.")
    w("")
    for name in results:
        for track in results[name]:
            w(f"```")
            w(f"{name} · {track}")
            for n in N_GRID:
                m = results[name][track][n]["metrics"]["p_at_k"]
                w(f"  n={n:3d}  {m[0]:.3f} ±{m[1]:.2f}  {bar(m[0], chance - 0.1, chance + 0.25)}")
            w(f"  chance {chance:.3f}        {bar(chance, chance - 0.1, chance + 0.25)}")
            w("```")
            w("")
    w("## the permutation test")
    w("")
    w(f"Best contestant by P@k at n={n_top}: **{best_name} · {modal}**. Labels shuffled "
      f"inside each room {perm['n_perm']} times, same pipeline, same folds.")
    w("")
    w(f"- real P@k: **{perm['real']:.3f}**")
    w(f"- shuffled: {perm['null_mean']:.3f} ± {perm['null_sd']:.3f}")
    w(f"- p = {perm['p']:.3f} ({perm['n_perm']} permutations)")
    w("")
    w("## the cheap facts")
    w("")
    w("| | cards | marked | rate | ★ counted |")
    w("|---|---|---|---|---|")
    for k in sorted(by_model):
        cs = by_model[k]
        w(f"| model `{k}` | {len(cs)} | {sum(c.marked for c in cs)} | "
          f"{sum(c.marked for c in cs)/len(cs):.0%} | {sum(c.true_star for c in cs)} |")
    for k in sorted(by_temp):
        cs = by_temp[k]
        w(f"| temperature {k} | {len(cs)} | {sum(c.marked for c in cs)} | "
          f"{sum(c.marked for c in cs)/len(cs):.0%} | {sum(c.true_star for c in cs)} |")
    w("")
    w("`meta/facts` in the scoreboard is a scorer given only those two facts plus card "
      "length. If it keeps up with the embeddings, the embeddings have learned nothing "
      "a lookup table doesn't already know.")
    w("")
    w("## verdict")
    w("")
    w("<!-- written by hand after reading the numbers -->")
    w("")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
