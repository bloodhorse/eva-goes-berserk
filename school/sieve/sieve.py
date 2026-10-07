import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import settings
import planner
import reporter
import reviewer
import writer
from store import Busy


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sieve.py", description="sort the deduplicated text by kind and cut the apparatus")
    parser.add_argument("--config", default=str(HERE / "sieve.toml"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan", help="decide the kind and the cuts of every file; writes state/plan.jsonl")
    commands.add_parser("review", help="write review.md: the unsure band and a sample of every other decision")
    commands.add_parser("apply", help="write out/<kind>/<source>/ from the plan")
    commands.add_parser("report", help="write report.md from the plan")
    commands.add_parser("overrides", help="check overrides.toml and list what each entry matched in the plan")
    commands.add_parser("daily", help="plan, apply, report, review")
    args = parser.parse_args(argv)
    try:
        cfg = settings.Settings(args.config)
        if args.command == "plan":
            planner.run(cfg)
        elif args.command == "review":
            reviewer.run(cfg)
        elif args.command == "apply":
            writer.run(cfg)
        elif args.command == "report":
            reporter.run(cfg)
        elif args.command == "overrides":
            reporter.overrides(cfg)
        elif args.command == "daily":
            planner.run(cfg)
            writer.run(cfg)
            reporter.run(cfg)
            reviewer.run(cfg)
    except (Busy, settings.ConfigError, writer.NoPlan, FileNotFoundError) as error:
        print(f"sieve: {error}", file=sys.stderr)
        return 2
    except PermissionError as error:
        print(f"sieve: cannot write the state or the output ({error}); nothing was changed by this command",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
