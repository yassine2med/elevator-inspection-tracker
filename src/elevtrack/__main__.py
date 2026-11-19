"""Command line: python -m elevtrack units.csv [--today YYYY-MM-DD] [--within DAYS]."""
from __future__ import annotations

import argparse
import sys
from datetime import date

from .tracker import TrackerError, format_report, load_units, needs_action


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="elevtrack", description=__doc__)
    parser.add_argument("csv_file")
    parser.add_argument("--today", help="YYYY-MM-DD, default is today")
    parser.add_argument("--within", type=int, help="show only units expiring within this many days")
    args = parser.parse_args(argv)
    try:
        today = date.fromisoformat(args.today) if args.today else date.today()
        units = load_units(args.csv_file, today)
    except (TrackerError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.within is not None:
        units = needs_action(units, args.within)
    print(format_report(units))
    flagged = len(needs_action(units, 90))
    print(f"\n{len(units)} units shown, {flagged} expired or due within 90 days")
    return 2 if any(u.band == "EXPIRED" for u in units) else 0


if __name__ == "__main__":
    sys.exit(main())
