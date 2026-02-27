"""Monthly data cleanup module for retaining only current-month data."""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from pipeline.write import _write_json_atomic


def cleanup_old_data(data_dir: str = "data", reference_date: str | None = None) -> list[str]:
    """
    Remove data from previous months, keeping only current month data.

    Args:
        data_dir: Base data directory (default "data")
        reference_date: Reference date as YYYY-MM-DD (defaults to today)

    Returns:
        List of deleted paths for logging
    """
    # Determine current month from reference date
    if reference_date is None:
        reference_date = datetime.now().strftime("%Y-%m-%d")

    current_month = reference_date[:7]  # Extract YYYY-MM
    deleted_paths = []

    data_path = Path(data_dir)
    if not data_path.exists():
        return deleted_paths

    # Clean up score files from previous months
    scores_dir = data_path / "scores"
    if scores_dir.exists():
        for score_file in scores_dir.glob("*.json"):
            file_date = score_file.stem  # Get filename without extension
            file_month = file_date[:7]  # Extract YYYY-MM

            if file_month != current_month and file_month < current_month:
                if os.path.exists(score_file):
                    os.remove(score_file)
                    deleted_paths.append(str(score_file))

    # Clean up game directories from previous months
    games_dir = data_path / "games"
    if games_dir.exists():
        for game_dir in games_dir.iterdir():
            if not game_dir.is_dir():
                continue

            # Read date from boxscore.json
            boxscore_path = game_dir / "boxscore.json"
            if os.path.exists(boxscore_path):
                try:
                    with open(boxscore_path) as f:
                        boxscore_data = json.load(f)
                        game_date = boxscore_data.get("date")

                        if game_date:
                            game_month = game_date[:7]

                            if game_month != current_month and game_month < current_month:
                                # Delete game directory
                                if os.path.exists(game_dir):
                                    shutil.rmtree(game_dir)
                                    deleted_paths.append(str(game_dir))
                except (json.JSONDecodeError, IOError):
                    # Skip games with invalid boxscore
                    pass

    # Update index.json - remove entries from previous months
    index_path = data_path / "index.json"
    if os.path.exists(index_path):
        try:
            with open(index_path) as f:
                index_data = json.load(f)

            # Filter dates to keep only current month
            dates = index_data.get("dates", [])
            filtered_dates = [
                d
                for d in dates
                if d.get("date", "") >= current_month
            ]

            # Write updated index
            index_data["dates"] = filtered_dates
            _write_json_atomic(index_path, index_data)
        except (json.JSONDecodeError, IOError) as e:
            timestamp = datetime.now().isoformat()
            print(f"[{timestamp}] Warning: Could not update index.json during cleanup: {e}", file=sys.stderr, flush=True)

    return deleted_paths
