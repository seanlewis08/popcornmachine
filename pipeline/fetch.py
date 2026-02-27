"""NBA API fetch module with rate limiting."""

import time
from typing import Optional

import pandas as pd
import requests
from nba_api.stats.endpoints.boxscoretraditionalv2 import BoxScoreTraditionalV2
from nba_api.stats.endpoints.gamerotation import GameRotation
from nba_api.stats.endpoints.playbyplayv2 import PlayByPlayV2
from nba_api.stats.endpoints.scoreboardv2 import ScoreboardV2


def fetch_scoreboard(game_date: str, delay: float = 1.5) -> Optional[dict]:
    """
    Fetch scoreboard data for a given date.

    Args:
        game_date: Date string in YYYY-MM-DD format
        delay: Delay in seconds before making the API call (default 1.5)

    Returns:
        Dict with 'game_header' and 'line_score' DataFrames, or None on failure
    """
    try:
        time.sleep(delay)
        response = ScoreboardV2(
            game_date=game_date, day_offset=0, league_id="00"
        )
        return {
            "game_header": response.get_data_frames()[0],
            "line_score": response.get_data_frames()[1],
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching scoreboard for {game_date}: {e}", flush=True)
        return None


def fetch_boxscore(game_id: str, delay: float = 1.5) -> Optional[dict]:
    """
    Fetch box score data for a given game.

    Args:
        game_id: Game ID string
        delay: Delay in seconds before making the API call (default 1.5)

    Returns:
        Dict with 'player_stats' and 'team_stats' DataFrames, or None on failure
    """
    try:
        time.sleep(delay)
        response = BoxScoreTraditionalV2(
            game_id=game_id, start_period=1, end_period=10,
            start_range=0, end_range=0, range_type=0
        )
        return {
            "player_stats": response.get_data_frames()[0],
            "team_stats": response.get_data_frames()[1],
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching box score for {game_id}: {e}", flush=True)
        return None


def fetch_playbyplay(game_id: str, delay: float = 1.5) -> Optional[pd.DataFrame]:
    """
    Fetch play-by-play data for a given game.

    Args:
        game_id: Game ID string
        delay: Delay in seconds before making the API call (default 1.5)

    Returns:
        DataFrame with play-by-play events, or None on failure
    """
    try:
        time.sleep(delay)
        response = PlayByPlayV2(
            game_id=game_id, start_period=1, end_period=10
        )
        return response.get_data_frames()[0]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching play-by-play for {game_id}: {e}", flush=True)
        return None


def fetch_game_rotation(game_id: str, delay: float = 1.5) -> Optional[dict]:
    """
    Fetch game rotation data for a given game.

    Args:
        game_id: Game ID string
        delay: Delay in seconds before making the API call (default 1.5)

    Returns:
        Dict with 'away_team' and 'home_team' DataFrames, or None on failure
    """
    try:
        time.sleep(delay)
        response = GameRotation(game_id=game_id, league_id="00")
        return {
            "away_team": response.get_data_frames()[0],
            "home_team": response.get_data_frames()[1],
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching game rotation for {game_id}: {e}", flush=True)
        return None
