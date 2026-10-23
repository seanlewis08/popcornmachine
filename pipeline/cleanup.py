# pattern: Imperative Shell
"""
Retention: keep the current season, drop everything older.

"Current season" is the season `reference_date` falls in (see
pipeline/season.py), so the finished season survives the summer and is
dropped on the first game day of the next one. main() only runs cleanup
after a day with games, which is what makes that timing work.
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from pipeline.season import season_for
from pipeline.write import _write_json_atomic


def is_stale(date_str: str, reference_date: str) -> bool:
    """
    Pure retention predicate: True if `date_str` belongs to an earlier
    season than `reference_date`. Unparseable dates are never stale —
    we don't delete what we can't classify.
    """
    try:
        return season_for(date_str) != season_for(reference_date)
    except ValueError:
        return False


def cleanup_old_data(data_dir: str = "data", reference_date: str | None = None) -> list[str]:
    """
    Delete score files, game directories, and index entries from seasons
    before the one containing `reference_date` (default: today).

    Returns the list of deleted paths for logging.
    """
    if reference_date is None:
        reference_date = datetime.now().strftime("%Y-%m-%d")

    deleted_paths: list[str] = []

    data_path = Path(data_dir)
    if not data_path.exists():
        return deleted_paths

    scores_dir = data_path / "scores"
    if scores_dir.exists():
        for score_file in scores_dir.glob("*.json"):
            if is_stale(score_file.stem, reference_date):
                os.remove(score_file)
                deleted_paths.append(str(score_file))

    games_dir = data_path / "games"
    if games_dir.exists():
        for game_dir in games_dir.iterdir():
            if not game_dir.is_dir():
                continue
            game_date = _read_game_date(game_dir / "boxscore.json")
            if game_date is not None and is_stale(game_date, reference_date):
                shutil.rmtree(game_dir)
                deleted_paths.append(str(game_dir))

    index_path = data_path / "index.json"
    if index_path.exists():
        try:
            with open(index_path) as f:
                index_data = json.load(f)
            dates = index_data.get("dates", [])
            index_data["dates"] = [
                d for d in dates if not is_stale(d.get("date", ""), reference_date)
            ]
            _write_json_atomic(index_path, index_data)
        except (json.JSONDecodeError, IOError) as e:
            timestamp = datetime.now().isoformat()
            print(
                f"[{timestamp}] Warning: Could not update index.json during cleanup: {e}",
                file=sys.stderr,
                flush=True,
            )

    return deleted_paths


def _read_game_date(boxscore_path: Path) -> str | None:
    """Return the "date" field of a boxscore file, or None if unreadable/absent."""
    if not boxscore_path.exists():
        return None
    try:
        with open(boxscore_path) as f:
            return json.load(f).get("date")
    except (json.JSONDecodeError, IOError):
        return None
