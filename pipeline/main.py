"""Popcorn Remake data pipeline entry point."""

import argparse
import traceback
from datetime import datetime, timedelta

from .cleanup import cleanup_old_data
from .fetch import fetch_boxscore, fetch_game_rotation, fetch_playbyplay, fetch_roster, fetch_scoreboard
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
        # Write empty scores file so backfill doesn't retry this date
        write_scores(date, [], data_dir)
        return

    # 2. Transform scores
    print("Transforming scores...")
    scores = transform_scores(scoreboard, date)
    if not scores:
        print(f"No games found for {date}")
        # Write empty scores file so backfill doesn't retry this date
        write_scores(date, [], data_dir)
        return

    print(f"Found {len(scores)} games")

    # 3. Derive season string from date (e.g., "2025-26" for Oct 2025 onward)
    year = int(date[:4])
    month = int(date[5:7])
    season_start = year if month >= 10 else year - 1
    season_str = f"{season_start}-{str(season_start + 1)[-2:]}"
    print(f"Using season: {season_str}")

    # Cache rosters by team_id to avoid re-fetching
    roster_cache: dict = {}

    # 3b. For each game, fetch detailed data and transform
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

        # Fetch rosters for both teams to get specific positions (PG, SG, SF, PF, C)
        try:
            import pandas as pd

            player_stats = boxscore_raw["player_stats"]
            team_ids = player_stats["TEAM_ID"].astype(str).unique()
            for tid in team_ids:
                if tid not in roster_cache:
                    print(f"  Fetching roster for team {tid}...")
                    roster_df = fetch_roster(tid, season_str)
                    if roster_df is not None:
                        # Build player_id → position map
                        roster_cache[tid] = {
                            str(int(row["PLAYER_ID"])): row.get("POSITION", "")
                            for _, row in roster_df.iterrows()
                        }
                    else:
                        roster_cache[tid] = {}

            # Merge specific positions into player_stats
            def _get_roster_position(row):
                tid = str(int(row["TEAM_ID"]))
                pid = str(int(row["PLAYER_ID"]))
                return roster_cache.get(tid, {}).get(pid, "")

            boxscore_raw["player_stats"] = player_stats.copy()
            boxscore_raw["player_stats"]["ROSTER_POSITION"] = player_stats.apply(
                _get_roster_position, axis=1
            )
        except Exception as e:
            print(f"  Warning: could not fetch roster positions: {e}")

        try:
            print(f"Transforming game data for {game_id}...")
            boxscore = transform_boxscore(
                game_id, date, scoreboard, boxscore_raw, rotation_raw, pbp_raw
            )
            gameflow = transform_gameflow(
                game_id, scoreboard, rotation_raw, pbp_raw,
                boxscore_data=boxscore_raw,
            )

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
