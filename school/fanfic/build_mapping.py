import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "eva-olmo" / "school" / "fanfic"
TARGET_BYTES = 2.6e9
KEEP_RATIO = 0.62
TEMPER = 0.5

SOULS = {
    "Dark Souls": ("Dark Souls", 1),
    "Berserk": ("Berserk", 1),
    "Bloodborne": ("Bloodborne", 1),
    "Elden Ring": ("Elden Ring", 1),
    "Demon's Souls": ("Demon's Souls", 1),
    "Sekiro": ("Sekiro", 1),
    "Hollow Knight": ("Hollow Knight", 1),
    "Warhammer": ("Warhammer", 2),
    "Elder Scroll series": ("Elder Scrolls", 2),
    "Witcher": ("Witcher", 2),
    "Diablo": ("Diablo", 2),
    "Castlevania": ("Castlevania", 2),
    "Dragon Age": ("Dragon Age", 3),
    "A song of Ice and Fire": ("A Song of Ice and Fire", 3),
    "Game of Thrones": ("A Song of Ice and Fire", 3),
    "Legacy of Kain": ("Legacy of Kain", 3),
    "Darksiders": ("Darksiders", 3),
    "Legend of Grimrock": ("Legend of Grimrock", 3),
}
WIRED = {
    "Serial Experiments Lain": ("Serial Experiments Lain", 1),
    "Ghost in the Shell": ("Ghost in the Shell", 1),
    "Akira": ("Akira", 1),
    "Blade Runner": ("Blade Runner", 1),
    "Cyberpunk 2077": ("Cyberpunk", 1),
    "Deus Ex": ("Deus Ex", 1),
    "Matrix": ("Matrix", 1),
    "William Gibson": ("William Gibson / Sprawl", 1),
    "Neuromancer": ("William Gibson / Sprawl", 1),
    "Snow Crash": ("Snow Crash", 1),
    "Psycho-Pass/サイコパス": ("Psycho-Pass", 1),
    "Ergo Proxy": ("Ergo Proxy", 1),
    "Texhnolyze": ("Texhnolyze", 1),
    "Steins;Gate/シュタインズ ゲート": ("Steins;Gate", 1),
    ".hack/SIGN": (".hack", 1),
    "Sword Art Online/ソードアート・オンライン": ("Sword Art Online", 1),
    "Log Horizon/ログ・ホライズン": ("Log Horizon", 1),
    "Overlord": ("Overlord", 1),
    "Mega Man": ("Mega Man", 1),
    "Shadowrun": ("Shadowrun", 1),
    "Mass Effect": ("Mass Effect", 1),
    "Portal": ("Portal / Half-Life", 1),
    "Half-Life": ("Portal / Half-Life", 1),
    "Nier": ("NieR / Drakengard", 1),
    "Drakengard": ("NieR / Drakengard", 1),
    "Evangelion": ("Evangelion", 1),
    "Tron": ("Tron", 2),
    "Code Lyoko": ("Code Lyoko", 2),
    "Accel World/アクセル・ワールド": ("Accel World", 2),
    "Robotics;Notes/ロボティクス・ノーツ": ("Robotics;Notes", 2),
    "Summer Wars/サマーウォーズ": ("Summer Wars", 2),
    "System Shock": ("System Shock", 2),
    "Gunnm/Battle Angel": ("Battle Angel Alita", 2),
}
CJK = re.compile(r"[぀-ヿ㐀-鿿가-힯＀-￯]")
KANA = re.compile(r"[぀-ヿ]")
HANGUL = re.compile(r"[가-힯]")
CJK_ALLOW = {"ManHua/Chinese Comics/漫画", "Manhwa/Korean Comics/만화", "Qin's Moon/秦时明月", "Tai Chi Chasers/태극천자문"}
CJK_DENY = {
    "Mendol/メン☆ドル", "Koizora/恋空～切ナイ恋物語～", "Majisuka gakuen/マジスカ学園", "Etrian Odyssey/世界樹の迷宮",
    "Nazotoki wa Dinner no Ato de/謎解きはディナーのあとで", "Love Pistols/リブレ出版",
}


def cjk_label(name):
    if "/" in name:
        head = name.split("/")[0].strip()
        if head and not CJK.search(head):
            return head
    return name


def single(name, anime):
    if name in SOULS:
        lab, tier = SOULS[name]
        return {"shelf": "souls", "label": lab, "tier": tier}
    if name in WIRED:
        lab, tier = WIRED[name]
        return {"shelf": "wired", "label": lab, "tier": tier}
    if name in anime:
        return {"shelf": "anime", "label": anime[name], "tier": 1}
    if CJK.search(name) and ", " not in name:
        if name in CJK_DENY:
            return None
        if name in CJK_ALLOW or (KANA.search(name) and not HANGUL.search(name)):
            return {"shelf": "anime", "label": cjk_label(name), "tier": 1}
    return None


def main():
    fandoms = json.loads((ROOT / "fandoms.json").read_text())
    anime = json.loads((ROOT / "anime_noncjk.json").read_text())
    extra = anime.pop("__wired_or_souls__", {})
    for k, lab in extra.items():
        if k not in SOULS and k not in WIRED:
            anime[k] = lab
    names = {r["fandom"] for r in fandoms if "," not in r["fandom"]}
    mapping = {}
    crossover_stats = collections.Counter()
    for r in fandoms:
        f = r["fandom"]
        if not f:
            continue
        f0 = f
        f = f.replace("Rosario, Rosario + Vampire, Vampire", "Rosario + Vampire")
        m = single(f, anime)
        if m:
            mapping[f0] = m
            continue
        if "," not in f:
            continue
        pieces = [p.strip() for p in f.split(",")]
        ms = []
        ok = True
        i = 0
        while i < len(pieces):
            hit = None
            for j in range(len(pieces), i, -1):
                cand = ", ".join(pieces[i:j])
                if cand in names or j == i + 1:
                    mm = single(cand, anime)
                    if mm:
                        hit = (j, mm)
                        break
            if hit is None:
                ok = False
                break
            i = hit[0]
            ms.append(hit[1])
        if not ok:
            crossover_stats["dropped_western_or_unknown"] += r["works"]
            continue
        labels = []
        for mm in ms:
            if mm["label"] not in labels:
                labels.append(mm["label"])
        order = {"souls": 0, "wired": 1, "anime": 2}
        best = min(ms, key=lambda mm: (order[mm["shelf"]], mm["tier"]))
        if len(labels) == 1:
            mapping[f0] = dict(best)
        else:
            mapping[f0] = {"shelf": best["shelf"], "label": " x ".join(labels), "tier": best["tier"], "crossover": True}
        crossover_stats["kept_" + best["shelf"]] += r["works"]
    per = collections.defaultdict(lambda: collections.Counter())
    for r in fandoms:
        m = mapping.get(r["fandom"])
        if m:
            per[m["shelf"]][m["label"]] += r["chars"]
    fractions = {}
    target_chars = TARGET_BYTES / KEEP_RATIO
    for shelf, labs in per.items():
        total = sum(labs.values())
        if total <= target_chars:
            continue
        lo, hi = 0.0, float(total)
        for _ in range(80):
            mid = (lo + hi) / 2
            if sum(min(v, mid * v ** TEMPER) for v in labs.values()) > target_chars:
                hi = mid
            else:
                lo = mid
        for lab, v in labs.items():
            if lo * v ** TEMPER < v:
                fractions[f"{shelf}|{lab}"] = lo * v ** TEMPER / v
        print(shelf, "temper scale", lo)
    (ROOT / "mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=0))
    (ROOT / "fractions.json").write_text(json.dumps(fractions, ensure_ascii=False, indent=1))
    for shelf, labs in per.items():
        print(shelf, "labels", len(labs), "raw chars", round(sum(labs.values()) / 1e9, 2), "G")
        for lab, v in labs.most_common(25):
            print("   ", lab, round(v / 1e6, 1), "M", round(fractions.get(f"{shelf}|{lab}", 1.0), 3))
    print(crossover_stats)
    print("fractions", len(fractions))


if __name__ == "__main__":
    main()
