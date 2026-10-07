import fnmatch
import re
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEDUPE = HERE.parent / "dedupe"
if str(DEDUPE) not in sys.path:
    sys.path.append(str(DEDUPE))

from config import Config as DedupeConfig
from config import ConfigError

KINDS = ("fiction", "nonfiction", "verse", "stub", "mixed", "unsure")
WHOLE_KINDS = ("nonfiction", "verse", "stub")
PROFILES = ("magazine", "podcast", "serial", "anthology", "plain")
REQUIRED = {
    "shape": ("verse_line_max_words", "min_words_for_rates", "label_max_words", "window_paragraphs"),
    "stub": ("tiny_words", "podcast_words", "remnant_share", "remnant_words",
             "teaser_words", "notice_words"),
    "verse": ("stanza_share_min", "short_line_share_min", "max_line_words_mean", "min_lines",
              "unsure_stanza_share", "unsure_line_words_mean", "unsure_max_words"),
    "nonfiction": ("decide_min", "unsure_min", "meta_high", "meta_mid", "biblio_high", "qa_share_min",
                   "qa_min_turns", "narrative_low", "narrative_high", "speech_share_high", "meta_low",
                   "address_high", "long_fiction_words"),
    "weights": ("title_strong", "title_weak", "label", "url", "qa", "meta_high", "meta_mid", "biblio_high",
                "address", "columnist", "fiction_index", "fiction_class", "narrative_high", "speech", "narrative_low",
                "meta_low", "long_fiction", "ledger_story"),
    "edges": ("zone_paragraphs", "head_max_words", "tail_max_share", "tail_max_words", "note_max_words",
              "sandwich_words", "bio_max_words", "bio_min_score", "marker_max_words", "comments_min_words",
              "serial_note_max_share", "min_body_words", "tail_marker_zone_share"),
    "books": ("start_probe_chars", "start_min_chars", "headnote_max_words", "headnote_max_paragraphs",
              "headnote_min_score", "editorial_min_words", "editorial_meta_min", "editorial_narrative_max", "narrative_speech_min",
              "editorial_short_words", "editorial_short_meta_min", "headnote_named_score", "editorial_inner_meta_min",
              "apparatus_window_paragraphs", "apparatus_window_words", "story_min_words",
              "heading_run_max", "list_line_share_min", "front_matter_max_words", "essay_min_words",
              "name_max_tokens", "orphan_max_words"),
    "review": ("sample_per_stratum", "head_words", "tail_words", "cut_edge_words", "context_words", "seed",
               "cut_samples_per_reason"),
    "report": ("tokens_per_word", "unsure_rows", "override_rows"),
}
PATTERN_KEYS = ("title_nonfiction_strong", "title_nonfiction_weak", "title_notice", "url_nonfiction",
                "label_verse", "label_nonfiction", "label_fiction", "class_fiction", "class_nonfiction", "class_verse",
                "meta_words", "biblio_words", "narrative_words", "address_words", "speaker_label",
                "nav", "pitch", "credit", "host", "warning", "note_marker", "bio_marker", "comments_marker",
                "bio_verbs", "teaser", "chapter_nav", "pitch_address", "apparatus_titles", "headnote_phrases", "headnote_presenting", "list_line",
                "byline", "end_marker", "translator")
WORD_KEYS = ("meta_words", "biblio_words", "narrative_words", "address_words")


class Section:
    def __init__(self, values):
        self.__dict__.update(values)


class Override:
    def __init__(self, number, raw):
        self.number = number
        self.path = raw.get("path")
        self.title = raw.get("title")
        self.source = raw.get("source")
        self.kind = raw.get("kind")
        self.cut = raw.get("cut")
        self.keep = raw.get("keep")
        self.section = raw.get("section")
        self.reason = raw.get("reason", "")
        self.cut_reason = raw.get("as", "override")
        if not (self.path or self.title):
            raise ConfigError(f"override {number}: needs path or title")
        if self.kind is not None and self.kind not in KINDS:
            raise ConfigError(f"override {number}: kind must be one of {', '.join(KINDS)}")
        if self.kind is None and self.cut is None and self.keep is None:
            raise ConfigError(f"override {number}: needs kind, cut or keep")
        for span in (self.cut, self.keep):
            if span is not None and not (isinstance(span, dict) and span.get("from")):
                raise ConfigError(f"override {number}: cut and keep are tables with from (and to)")
        try:
            self.title_pattern = re.compile(self.title, re.I) if self.title else None
        except re.error as error:
            raise ConfigError(f"override {number}: bad title pattern ({error})")

    def matches(self, source, path, title):
        if self.source and self.source != source:
            return False
        if self.path and not fnmatch.fnmatchcase(f"{source}/{path}", self.path):
            return False
        if self.title_pattern and not self.title_pattern.search(title or ""):
            return False
        return True

    def describe(self):
        target = self.path or f"title /{self.title}/" + (f" in {self.source}" if self.source else "")
        if self.kind:
            what = f"kind {self.kind}"
        elif self.cut:
            what = f"cut from “{self.cut['from'][:40]}”"
        else:
            what = f"keep from “{self.keep['from'][:40]}”"
        return f"{target}: {what}"


class Settings:
    def __init__(self, path):
        self.file = Path(path).resolve()
        base = self.file.parent
        try:
            with open(self.file, "rb") as f:
                raw = tomllib.load(f)
        except tomllib.TOMLDecodeError as error:
            raise ConfigError(f"{self.file}: {error}")
        self.dedupe = DedupeConfig((base / raw.get("dedupe", "../dedupe/sources.toml")).resolve())
        self.state = (base / raw.get("state", "state")).resolve()
        self.out = (base / raw.get("out", "out")).resolve()
        self.review_file = (base / raw.get("review", "review.md")).resolve()
        self.report_file = (base / raw.get("report", "report.md")).resolve()
        self.thresholds_file = (base / raw.get("thresholds", "thresholds.toml")).resolve()
        self.overrides_file = (base / raw.get("overrides", "overrides.toml")).resolve()
        try:
            with open(self.thresholds_file, "rb") as f:
                tables = tomllib.load(f)
        except tomllib.TOMLDecodeError as error:
            raise ConfigError(f"{self.thresholds_file}: {error}")
        for table, patch in raw.get("override", {}).items():
            tables.setdefault(table, {}).update(patch)
        for table, keys in REQUIRED.items():
            absent = [k for k in keys if k not in tables.get(table, {})]
            if absent:
                raise ConfigError(f"{self.thresholds_file}: [{table}] lacks {', '.join(absent)}")
            setattr(self, table, Section(tables[table]))
        found = tables.get("patterns", {})
        absent = [k for k in PATTERN_KEYS if k not in found]
        if absent:
            raise ConfigError(f"{self.thresholds_file}: [patterns] lacks {', '.join(absent)}")
        self.patterns = {}
        for key in PATTERN_KEYS:
            try:
                joined = "|".join(f"(?:{p})" for p in found[key])
                if key in WORD_KEYS:
                    joined = rf"\b(?:{joined})\b"
                self.patterns[key] = re.compile(joined, re.I)
            except re.error as error:
                raise ConfigError(f"{self.thresholds_file}: [patterns] {key}: {error}")
        self.thresholds_raw = tables
        self.jobs = int(raw.get("jobs", 0))
        self.profiles = raw.get("profiles", {})
        for name, profile in self.profiles.items():
            if profile not in PROFILES:
                raise ConfigError(f"{self.file}: profile of {name} must be one of {', '.join(PROFILES)}")
        self.fiction_index = set(raw.get("fiction_index", []))
        self.groups = raw.get("groups", {})
        self.book_switches = raw.get("books", {})
        self.html_labels = {}
        for name, rule in raw.get("html_labels", {}).items():
            try:
                self.html_labels[name] = [re.compile(p, re.I | re.S) for p in rule["patterns"]]
            except (re.error, KeyError, TypeError) as error:
                raise ConfigError(f"{self.file}: html_labels.{name}: {error}")
        self.sources = [s for s in self.dedupe.sources if s.kind == "incoming"]
        self.by_name = {s.name: s for s in self.sources}
        self.overrides = self.load_overrides()

    def load_overrides(self):
        try:
            with open(self.overrides_file, "rb") as f:
                raw = tomllib.load(f)
        except FileNotFoundError:
            return []
        except tomllib.TOMLDecodeError as error:
            raise ConfigError(f"{self.overrides_file}: {error}")
        return [Override(i + 1, one) for i, one in enumerate(raw.get("override", []))]

    def profile(self, source_name):
        if source_name in self.profiles:
            return self.profiles[source_name]
        source = self.by_name.get(source_name)
        return "anthology" if source is not None and source.container else "magazine"

    def group(self, source_name):
        for group, names in self.groups.items():
            if source_name in names:
                return group
        return "other"

    def book(self, slug):
        if slug in self.book_switches:
            return self.book_switches[slug]
        for pattern, switches in sorted(self.book_switches.items()):
            if fnmatch.fnmatchcase(slug, pattern):
                return switches
        return {}
