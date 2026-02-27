"""Popcorn Remake data pipeline entry point."""

import argparse
import traceback
from datetime import datetime, timedelta

from .cleanup import cleanup_old_data
from .fetch import fetch_boxscore, fetch_game_rotation, fetch_playbyplay, fetch_scoreboard
from .transform import transform_boxscore, transform_gameflow, transform_scores
from .write import write_game_data, write_index, write_scores


def main(date: str | None = None, data_dir: str = "data", cleanup: bool = False) -> None:
    """
    Run the pipeline for a given date (defaults to yesterday).

    Args:
        date: Date string in YYYY-MM-DD format (defaults to yesterday)
        data_dir: Base data directory (default "data")
        cleanup: Whether to run monthly cleanup after successful writes (default False)
    """
    if date is None:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"Running pipeline for {date}")

    # 1. Fetch scoreboard for the date
    print(f"Fetching scoreboard for {date}...")
    scoreboard = fetch_scoreboard(date)
    if scoreboard is None:
        print(f"No scoreboard data for {date}")
        return

    # 2. Transform scores
    print("Transforming scores...")
    scores = transform_scores(scoreboard, date)
    if not scores:
        print(f"No games found for {date}")
        return

    print(f"Found {len(scores)} games")

    # 3. For each game, fetch detailed data and transform
    skipped_games = 0
    successful_games = 0

    for game in scores:
        game_id = game["gameId"]
        print(f"Processing game {game_id}...")

        boxscore_raw = fetch_boxscore(game_id)
        pbp_raw = fetch_playbyplay(game_id)
        rotation_raw = fetch_game_rotation(game_id)

        if any(d is None for d in [boxscore_raw, pbp_raw, rotation_raw]):
            print(f"Skipping game {game_id}: incomplete data")
            skipped_games += 1
            continue

        try:
            print(f"Transforming game data for {game_id}...")
            boxscore = transform_boxscore(
                game_id, date, scoreboard, boxscore_raw, rotation_raw, pbp_raw
            )
            gameflow = transform_gameflow(game_id, scoreboard, rotation_raw, pbp_raw)

            write_game_data(game_id, boxscore, gameflow, data_dir)
            print(f"Wrote game data for {game_id}")
            successful_games += 1
        except Exception as e:
            print(f"Error processing game {game_id}: {e}")
            traceback.print_exc()
            skipped_games += 1

    # 4. Only write scores and index if any games succeeded
    print("Writing scores...")
    write_scores(date, scores, data_dir)

    # Build index entry
    index_entry = {
        "date": date,
        "games": [
            {
                "gameId": g["gameId"],
                "home": g["homeTeam"]["tricode"],
                "away": g["awayTeam"]["tricode"],
                "homeScore": g["homeTeam"]["score"],
                "awayScore": g["awayTeam"]["score"],
            }
            for g in scores
        ],
    }

    print("Updating index...")
    write_index([index_entry], data_dir)

    # 5. Run cleanup if requested
    if cleanup:
        deleted = cleanup_old_data(data_dir=data_dir)
        if deleted:
            print(f"Cleaned up {len(deleted)} old data files")

    print(f"Pipeline complete for {date}. Processed {successful_games} games for {date}. Skipped {skipped_games} games due to errors.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Popcorn Remake data pipeline")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date in YYYY-MM-DD format (default: yesterday)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Base data directory (default: data)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Run monthly cleanup after successful writes (removes previous month data)",
    )

    args = parser.parse_args()
    main(date=args.date, data_dir=args.data_dir, cleanup=args.cleanup)
