"""Data cleanup module for retaining a rolling window of recent data."""

import json
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

from pipeline.write import _write_json_atomic


def cleanup_old_data(data_dir: str = "data", reference_date: str | None = None, keep_days: int = 30) -> list[str]:
    """
    Remove data older than `keep_days` days from `reference_date`.

    Uses a rolling window instead of calendar-month boundaries so that
    data is never wiped on the first day of a new month.

    Args:
        data_dir: Base data directory (default "data")
        reference_date: Reference date as YYYY-MM-DD (defaults to today)
        keep_days: Number of days of data to retain (default 30)

    Returns:
        List of deleted paths for logging
    """
    if reference_date is None:
        reference_date = datetime.now().strftime("%Y-%m-%d")

    cutoff_date = (
        datetime.strptime(reference_date, "%Y-%m-%d") - timedelta(days=keep_days)
    ).strftime("%Y-%m-%d")

    deleted_paths = []

    data_path = Path(data_dir)
    if not data_path.exists():
        return deleted_paths

    # Clean up score files older than cutoff
    scores_dir = data_path / "scores"
    if scores_dir.exists():
        for score_file in scores_dir.glob("*.json"):
            file_date = score_file.stem  # YYYY-MM-DD
            if file_date < cutoff_date:
                os.remove(score_file)
                deleted_paths.append(str(score_file))

    # Clean up game directories older than cutoff
    games_dir = data_path / "games"
    if games_dir.exists():
        for game_dir in games_dir.iterdir():
            if not game_dir.is_dir():
                continue

            boxscore_path = game_dir / "boxscore.json"
            if os.path.exists(boxscore_path):
                try:
                    with open(boxscore_path) as f:
                        boxscore_data = json.load(f)
                        game_date = boxscore_data.get("date")

                        if game_date and game_date < cutoff_date:
                            shutil.rmtree(game_dir)
                            deleted_paths.append(str(game_dir))
                except (json.JSONDecodeError, IOError):
                    pass

    # Update index.json — remove entries older than cutoff
    index_path = data_path / "index.json"
    if os.path.exists(index_path):
        try:
            with open(index_path) as f:
                index_data = json.load(f)

            dates = index_data.get("dates", [])
            filtered_dates = [
                d for d in dates if d.get("date", "") >= cutoff_date
            ]

            index_data["dates"] = filtered_dates
            _write_json_atomic(index_path, index_data)
        except (json.JSONDecodeError, IOError) as e:
            timestamp = datetime.now().isoformat()
            print(f"[{timestamp}] Warning: Could not update index.json during cleanup: {e}", file=sys.stderr, flush=True)

    return deleted_paths
