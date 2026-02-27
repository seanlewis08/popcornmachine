"""Write module for outputting transformed data to JSON files."""

import json
import os
import tempfile
from pathlib import Path


def write_index(dates_data: list[dict], data_dir: str = "data") -> None:
    """
    Write/update data/index.json with dates and games.

    Reads existing index if present, merges new dates (replacing existing
    entries for same date), sorts dates descending (most recent first),
    writes atomically.

    Args:
        dates_data: List of dicts with 'date' and 'games' keys
        data_dir: Base data directory (default "data")
    """
    index_path = Path(data_dir) / "index.json"

    # Read existing index if present
    existing_dates = {}
    if index_path.exists():
        with open(index_path) as f:
            existing_index = json.load(f)
            existing_dates = {d["date"]: d for d in existing_index.get("dates", [])}

    # Merge new dates
    for date_entry in dates_data:
        existing_dates[date_entry["date"]] = date_entry

    # Sort dates descending (most recent first)
    sorted_dates = sorted(existing_dates.values(), key=lambda d: d["date"], reverse=True)

    # Write atomically
    index_data = {"dates": sorted_dates}
    _write_json_atomic(index_path, index_data)


def write_scores(date: str, scores: list[dict], data_dir: str = "data") -> None:
    """
    Write data/scores/YYYY-MM-DD.json with game scores for a date.

    Creates directory if needed.

    Args:
        date: Date string in YYYY-MM-DD format
        scores: List of game dicts
        data_dir: Base data directory (default "data")
    """
    scores_dir = Path(data_dir) / "scores"
    scores_dir.mkdir(parents=True, exist_ok=True)

    scores_path = scores_dir / f"{date}.json"
    _write_json_atomic(scores_path, scores)


def write_game_data(
    game_id: str, boxscore: dict, gameflow: dict, data_dir: str = "data"
) -> None:
    """
    Write data/games/{gameId}/boxscore.json and gameflow.json.

    Creates directory if needed. Writes both files atomically.

    Args:
        game_id: Game ID string
        boxscore: Boxscore dict
        gameflow: Gameflow dict
        data_dir: Base data directory (default "data")
    """
    game_dir = Path(data_dir) / "games" / game_id
    game_dir.mkdir(parents=True, exist_ok=True)

    boxscore_path = game_dir / "boxscore.json"
    gameflow_path = game_dir / "gameflow.json"

    _write_json_atomic(boxscore_path, boxscore)
    _write_json_atomic(gameflow_path, gameflow)


def _write_json_atomic(file_path: Path, data: dict | list) -> None:
    """
    Write JSON to file atomically using temp file + rename.

    Args:
        file_path: Target file path
        data: Data to write
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory
    temp_fd, temp_path = tempfile.mkstemp(
        dir=file_path.parent, prefix=".tmp_", suffix=".json"
    )

    try:
        with os.fdopen(temp_fd, "w") as f:
            json.dump(data, f, indent=2)

        # Atomic rename
        os.replace(temp_path, file_path)
    except (OSError, IOError):
        # Clean up temp file on error
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise
