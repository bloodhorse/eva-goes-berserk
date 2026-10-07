import re
import tomllib
from pathlib import Path

KINDS = ("read", "incoming", "reference")
KIND_RANK = {"read": 2, "incoming": 1, "reference": 0}
REQUIRED = {
    "structure": ("shingle_words", "sample_modulus", "long_paragraph_words", "heading_max_words"),
    "scan": ("settle_seconds", "max_file_bytes", "batch_words", "segment_merge_count"),
    "boilerplate": ("edge_units", "min_docs", "min_share", "edge_share", "min_words", "template_min_share",
                    "template_min_docs", "template_edge_share", "template_max_words", "sandwich_max_words", "sandwich_unit_max_words", "head_sandwich_unit_max_words"),
    "candidates": ("common_shingle_docs", "min_shared", "min_est_words", "min_est_containment"),
    "relations": ("min_match_words", "same_work_min", "contained_min", "unit_match_min", "gap_max_words", "edge_unit_min", "edge_unit_max_words",
                  "shared_block_min_words", "shared_block_purity_min", "shared_block_clean_min",
                  "shares_max_containment", "unique_block_words", "container_clean_min", "spare_min_words", "same_work_cover_min", "rough_unique_block_words"),
    "remnants": ("remnant_max_words", "heading_min_cut_words", "heading_max_units", "intro_max_words", "intro_max_units"),
    "ambiguous": ("min_containment", "min_words"),
    "lookup": ("max_docs_per_run", "context_chars"),
    "report": ("tokens_per_word", "clusters", "boilerplate_rows", "read_pairs", "apparatus", "long_apparatus", "long_apparatus_min_words"),
    "crosscheck": ("container_min_bytes", "heading_max_words", "author_reach_lines", "title_reach_lines",
                   "pair_reach_lines", "title_only_min_words", "shared_heading_max_spots", "region_words",
                   "same_min_sentences", "same_min_share", "same_sure_sentences", "partial_min_sentences",
                   "caught_max_survival", "missed_min_survival", "same_spot_lines",
                   "text_sentence_words", "text_max_files", "text_min_sentences", "loss_examples", "loss_rows", "loss_run_sentences"),
}


class ConfigError(Exception):
    pass


class Section:
    def __init__(self, values):
        self.__dict__.update(values)


class Source:
    def __init__(self, base, raw):
        missing = [k for k in ("name", "path", "kind") if k not in raw]
        if missing:
            raise ConfigError(f"source {raw.get('name', '?')}: missing {', '.join(missing)}")
        self.name = raw["name"]
        self.path = (base / raw["path"]).resolve()
        self.glob = raw.get("glob", "*.txt")
        self.kind = raw["kind"]
        self.priority = int(raw.get("priority", 0))
        self.container = bool(raw.get("container", False))
        self.strip = bool(raw.get("boilerplate", raw["kind"] != "read"))
        self.rough = bool(raw.get("rough", False))
        self.format = raw.get("format", "txt")
        self.text_field = raw.get("text_field", "text")
        self.id_field = raw.get("id_field", "id")
        self.metadata = (base / raw["metadata"]).resolve() if raw.get("metadata") else None
        self.ledger = (base / raw["ledger"]).resolve() if raw.get("ledger") else None
        if self.kind not in KINDS:
            raise ConfigError(f"source {self.name}: kind must be one of {', '.join(KINDS)}")
        if self.format not in ("txt", "jsonl"):
            raise ConfigError(f"source {self.name}: format must be txt or jsonl")
        self.pattern = glob_pattern(self.glob)

    @property
    def rank(self):
        return (KIND_RANK[self.kind], self.priority)


def glob_pattern(glob):
    out = []
    i = 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def shelf_sources(base, raw):
    missing = [k for k in ("path", "kind") if k not in raw]
    if missing:
        raise ConfigError(f"shelf {raw.get('path', '?')}: missing {', '.join(missing)}")
    root = (base / raw["path"]).resolve()
    skip = set(raw.get("skip", []))
    priorities = raw.get("priorities", {})
    try:
        folders = sorted(e.name for e in root.iterdir() if e.is_dir() and not e.name.startswith("."))
    except OSError:
        folders = sorted(priorities)
    out = []
    for folder in sorted(set(folders) | set(priorities)):
        if folder in skip:
            continue
        one = {k: v for k, v in raw.items()
               if k not in ("path", "metadata", "priorities", "skip", "prefix", "rough")}
        one["rough"] = folder in raw.get("rough", [])
        one["name"] = raw.get("prefix", "") + folder
        one["path"] = str(root / folder)
        one["priority"] = priorities.get(folder, raw.get("priority", 0))
        if raw.get("metadata"):
            one["metadata"] = str((base / raw["metadata"]).resolve() / folder)
        out.append(Source(base, one))
    return out


class Config:
    def __init__(self, path):
        self.file = Path(path).resolve()
        base = self.file.parent
        with open(self.file, "rb") as f:
            raw = tomllib.load(f)
        self.state = (base / raw.get("state", "state")).resolve()
        self.out = (base / raw.get("out", "out")).resolve()
        self.report_file = (base / raw.get("report", "report.md")).resolve()
        thresholds_file = (base / raw.get("thresholds", "thresholds.toml")).resolve()
        with open(thresholds_file, "rb") as f:
            tables = tomllib.load(f)
        for table, patch in raw.get("override", {}).items():
            tables.setdefault(table, {}).update(patch)
        for table, keys in REQUIRED.items():
            absent = [k for k in keys if k not in tables.get(table, {})]
            if absent:
                raise ConfigError(f"{thresholds_file}: [{table}] lacks {', '.join(absent)}")
            setattr(self, table, Section(tables[table]))
        found = [Source(base, s) for s in raw.get("source", [])]
        for shelf in raw.get("shelf", []):
            found.extend(shelf_sources(base, shelf))
        self.sources = sorted(found, key=lambda s: s.name)
        names = [s.name for s in self.sources]
        if len(set(names)) != len(names):
            twice = sorted({n for n in names if names.count(n) > 1})
            raise ConfigError(f"two sources share a name: {', '.join(twice)} (give a shelf a prefix, or rename one)")
        self.by_name = {s.name: s for s in self.sources}

    def structure_key(self):
        from words import NORMALISER_VERSION
        s = self.structure
        return f"{NORMALISER_VERSION}/{s.shingle_words}/{s.sample_modulus}/{s.long_paragraph_words}/{s.heading_max_words}"
