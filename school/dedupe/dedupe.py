import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lookup
import materialise
import plan
import report
import scan
from config import Config, ConfigError
from store import Busy, Index, StructureChanged, lock


def rebuild(cfg, say=print):
    with lock(cfg.state):
        stamp = __import__("time").strftime("%Y%m%d-%H%M%S")
        aside = cfg.state / f"before-rebuild-{stamp}"
        moved = 0
        for name in ("index.sqlite", "index.sqlite-wal", "index.sqlite-shm", "segments"):
            if (cfg.state / name).exists():
                aside.mkdir(parents=True, exist_ok=True)
                (cfg.state / name).rename(aside / name)
                moved += 1
    say(f"rebuild: the old index is in {aside}" if moved else "rebuild: there was no index")
    return scan.run(cfg, say)


def compact(cfg, say=print):
    with lock(cfg.state):
        index = Index(cfg)
        try:
            done = index.merge_segments(force=True)
        finally:
            index.close()
    say("compact: segments merged, forgotten texts dropped" if done else "compact: nothing to do")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="dedupe.py", description="find and cut repeated text across the shelves")
    parser.add_argument("--config", default=str(HERE / "sources.toml"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("scan", help="read new and changed files into the index")
    commands.add_parser("plan", help="decide what is kept, cut and dropped; writes state/plan.jsonl")
    commands.add_parser("apply", help="write the deduplicated copy into out/")
    commands.add_parser("report", help="write report.md from the plan")
    commands.add_parser("daily", help="scan, plan, apply, report")
    commands.add_parser("rebuild", help="set the index aside and scan from nothing")
    commands.add_parser("compact", help="merge lookup segments and forget texts no file holds")
    finder = commands.add_parser("lookup", help="find runs of 8+ words of a text in the corpus")
    finder.add_argument("file", help="a text file, or - for stdin")
    finder.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        cfg = Config(args.config)
        if args.command == "scan":
            scan.run(cfg)
        elif args.command == "plan":
            plan.run(cfg)
        elif args.command == "apply":
            materialise.run(cfg)
        elif args.command == "report":
            report.run(cfg)
        elif args.command == "daily":
            scan.run(cfg)
            plan.run(cfg)
            materialise.run(cfg)
            report.run(cfg)
        elif args.command == "rebuild":
            rebuild(cfg)
        elif args.command == "compact":
            compact(cfg)
        elif args.command == "lookup":
            lookup.run(cfg, args.file, args.json)
    except (Busy, ConfigError, StructureChanged, materialise.NoPlan, FileNotFoundError) as error:
        print(f"dedupe: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
