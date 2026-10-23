# pattern: Functional Core
"""
NBA season arithmetic.

A season runs from October through June and is named by the calendar year
it starts in ("2026-27"). Any date from October 1 of year Y through
September 30 of year Y+1 belongs to season Y. The July–September offseason
is attributed to the season that just ended, which is what retention wants:
the finished season stays available all summer and is dropped on the first
game day of the next one.
"""

from datetime import date as _date

# A date on or after this month belongs to the season starting that year.
SEASON_START_MONTH = 10


def _parse_iso_date(date_str: str) -> _date:
    """Parse YYYY-MM-DD strictly; raises ValueError on anything else."""
    return _date.fromisoformat(date_str)


def _season_start_year(date_str: str) -> int:
    d = _parse_iso_date(date_str)
    return d.year if d.month >= SEASON_START_MONTH else d.year - 1


def season_for(date_str: str) -> str:
    """
    Return the season label for a YYYY-MM-DD date, e.g. "2026-27".

    Raises ValueError for a malformed or impossible date.
    """
    start = _season_start_year(date_str)
    return f"{start}-{(start + 1) % 100:02d}"


def season_start_date(date_str: str) -> str:
    """Return October 1 of the season containing `date_str`, as YYYY-MM-DD."""
    return f"{_season_start_year(date_str)}-{SEASON_START_MONTH:02d}-01"


if __name__ == "__main__":
    # Tiny CLI so the GitHub workflow (bash) can ask where the season starts.
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="NBA season arithmetic")
    parser.add_argument("--start-of", metavar="YYYY-MM-DD", required=True,
                        help="print the first day of the season containing this date")
    args = parser.parse_args()
    try:
        print(season_start_date(args.start_of))
    except ValueError as e:
        print(f"invalid date {args.start_of!r}: {e}", file=sys.stderr)
        sys.exit(1)
