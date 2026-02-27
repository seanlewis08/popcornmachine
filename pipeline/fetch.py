"""NBA API fetch module with rate limiting."""

import sys
import time
from datetime import datetime
from typing import Optional

import pandas as pd
import requests
from nba_api.stats.endpoints import BoxScoreTraditionalV3
from nba_api.stats.endpoints.gamerotation import GameRotation
from nba_api.stats.endpoints.playbyplayv3 import PlayByPlayV3
from nba_api.stats.endpoints.scoreboardv2 import ScoreboardV2


def _log_error(msg: str) -> None:
    """Log timestamped error to stderr."""
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] {msg}", file=sys.stderr, flush=True)


def fetch_scoreboard(game_date: str, delay: float = 1.5) -> Optional[dict]:
    """
    Fetch scoreboard data for a given date with retry logic.

    Args:
        game_date: Date string in YYYY-MM-DD format
        delay: Delay in seconds before making the API call (default 1.5)

    Returns:
        Dict with 'game_header' and 'line_score' DataFrames, or None on failure
    """
    max_retries = 1
    for attempt in range(max_retries + 1):
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
            _log_error(f"Error fetching scoreboard for {game_date}: {e}")

            if attempt < max_retries:
                time.sleep(5)
            else:
                return None
        except Exception as e:
            _log_error(f"Unexpected error fetching scoreboard for {game_date}: {e}")
            return None


def _map_v3_boxscore_player_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map BoxScoreTraditionalV3 player stats (DataFrame[0]) to V2 column names.

    V3 uses camelCase columns; transform.py expects V2 UPPER_SNAKE_CASE names.
    """
    # Synthesize PLAYER_NAME from firstName + familyName
    if "firstName" in df.columns and "familyName" in df.columns:
        df["PLAYER_NAME"] = df["firstName"] + " " + df["familyName"]

    column_map = {
        "personId": "PLAYER_ID",
        "teamTricode": "TEAM_ABBREVIATION",
        "teamId": "TEAM_ID",
        "teamName": "TEAM_NAME",
        "gameId": "GAME_ID",
        "minutes": "MIN",
        "fieldGoalsMade": "FGM",
        "fieldGoalsAttempted": "FGA",
        "threePointersMade": "FG3M",
        "threePointersAttempted": "FG3A",
        "freeThrowsMade": "FTM",
        "freeThrowsAttempted": "FTA",
        "reboundsOffensive": "OREB",
        "reboundsDefensive": "DREB",
        "reboundsTotal": "REB",
        "assists": "AST",
        "steals": "STL",
        "blocks": "BLK",
        "turnovers": "TO",
        "foulsPersonal": "PF",
        "points": "PTS",
        "plusMinusPoints": "PLUS_MINUS",
    }
    df = df.rename(columns=column_map)
    return df


def _map_v3_boxscore_team_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map BoxScoreTraditionalV3 team stats (DataFrame[2]) to V2 column names.

    V3 uses camelCase columns; transform.py expects V2 UPPER_SNAKE_CASE names.
    """
    column_map = {
        "teamTricode": "TEAM_ABBREVIATION",
        "teamId": "TEAM_ID",
        "teamName": "TEAM_NAME",
        "gameId": "GAME_ID",
        "minutes": "MIN",
        "fieldGoalsMade": "FGM",
        "fieldGoalsAttempted": "FGA",
        "threePointersMade": "FG3M",
        "threePointersAttempted": "FG3A",
        "freeThrowsMade": "FTM",
        "freeThrowsAttempted": "FTA",
        "reboundsOffensive": "OREB",
        "reboundsDefensive": "DREB",
        "reboundsTotal": "REB",
        "assists": "AST",
        "steals": "STL",
        "blocks": "BLK",
        "turnovers": "TO",
        "foulsPersonal": "PF",
        "points": "PTS",
        "plusMinusPoints": "PLUS_MINUS",
    }
    df = df.rename(columns=column_map)
    return df


def fetch_boxscore(game_id: str, delay: float = 1.5) -> Optional[dict]:
    """
    Fetch box score data for a given game with retry logic.

    Uses BoxScoreTraditionalV3 (V2 is deprecated and returns empty DataFrames
    as of the 2025-26 NBA season) and maps V3 camelCase column names to V2
    UPPER_SNAKE_CASE format so transform.py works unchanged.

    Args:
        game_id: Game ID string
        delay: Delay in seconds before making the API call (default 1.5)

    Returns:
        Dict with 'player_stats' and 'team_stats' DataFrames, or None on failure
    """
    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            time.sleep(delay)
            response = BoxScoreTraditionalV3(game_id=game_id)
            dfs = response.get_data_frames()
            # V3 returns: [0] player stats, [1] starter/bench splits, [2] team stats
            player_stats = _map_v3_boxscore_player_stats(dfs[0])
            team_stats = _map_v3_boxscore_team_stats(dfs[2])
            return {
                "player_stats": player_stats,
                "team_stats": team_stats,
            }
        except requests.exceptions.RequestException as e:
            _log_error(f"Error fetching box score for {game_id}: {e}")

            if attempt < max_retries:
                time.sleep(5)
            else:
                return None
        except Exception as e:
            _log_error(f"Unexpected error fetching box score for {game_id}: {e}")
            return None


def _map_v3_to_v2_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map PlayByPlayV3 column names to V2 names so transform.py works unchanged.

    V3 merged home/away descriptions into a single 'description' field and
    uses different column naming conventions. This function renames columns
    and synthesizes the HOMEDESCRIPTION/VISITORDESCRIPTION fields.
    """
    column_map = {
        "period": "PERIOD",
        "personId": "PLAYER1_ID",
        "clock": "PCTIMESTRING",
        "actionType": "EVENTMSGTYPE",
        "subType": "EVENTMSGACTIONTYPE",
        "actionNumber": "EVENTNUM",
        "teamId": "PLAYER1_TEAM_ID",
        "teamTricode": "PLAYER1_TEAM_ABBREVIATION",
        "playerName": "PLAYER1_NAME",
        "description": "HOMEDESCRIPTION",
        "scoreHome": "SCORE_HOME",
        "scoreAway": "SCORE_AWAY",
    }
    df = df.rename(columns=column_map)

    # V3 has a single 'description' field; V2 had separate home/away fields.
    # Set VISITORDESCRIPTION to same value so transform.py's fallback works.
    if "VISITORDESCRIPTION" not in df.columns:
        df["VISITORDESCRIPTION"] = df.get("HOMEDESCRIPTION", "")

    # Strip clock format: V3 uses "PT04M30.00S", transform.py expects "4:30"
    if "PCTIMESTRING" in df.columns:
        df["PCTIMESTRING"] = df["PCTIMESTRING"].apply(_parse_v3_clock)

    return df


def _parse_v3_clock(clock_str: str) -> str:
    """Convert V3 clock format 'PT04M30.00S' to V2 format '4:30'."""
    if not isinstance(clock_str, str) or not clock_str.startswith("PT"):
        return str(clock_str)
    try:
        # Remove PT prefix and S suffix
        time_part = clock_str[2:].rstrip("S")
        if "M" in time_part:
            minutes_str, seconds_str = time_part.split("M")
            minutes = int(minutes_str)
            seconds = int(float(seconds_str))
        else:
            minutes = 0
            seconds = int(float(time_part))
        return f"{minutes}:{seconds:02d}"
    except (ValueError, IndexError):
        return str(clock_str)


def fetch_playbyplay(game_id: str, delay: float = 1.5) -> Optional[pd.DataFrame]:
    """
    Fetch play-by-play data for a given game with retry logic.

    Uses PlayByPlayV3 (V2 is deprecated and returns empty JSON) and maps
    the V3 column names to V2 format so transform.py works unchanged.

    Args:
        game_id: Game ID string
        delay: Delay in seconds before making the API call (default 1.5)

    Returns:
        DataFrame with play-by-play events (V2-compatible columns), or None on failure
    """
    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            time.sleep(delay)
            response = PlayByPlayV3(
                game_id=game_id, start_period=1, end_period=10
            )
            df = response.play_by_play.get_data_frame()
            return _map_v3_to_v2_columns(df)
        except requests.exceptions.RequestException as e:
            _log_error(f"Error fetching play-by-play for {game_id}: {e}")

            if attempt < max_retries:
                time.sleep(5)
            else:
                return None
        except Exception as e:
            _log_error(f"Unexpected error fetching play-by-play for {game_id}: {e}")
            return None


def fetch_game_rotation(game_id: str, delay: float = 1.5) -> Optional[dict]:
    """
    Fetch game rotation data for a given game with retry logic.

    Args:
        game_id: Game ID string
        delay: Delay in seconds before making the API call (default 1.5)

    Returns:
        Dict with 'away_team' and 'home_team' DataFrames, or None on failure
    """
    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            time.sleep(delay)
            response = GameRotation(game_id=game_id, league_id="00")
            return {
                "away_team": response.get_data_frames()[0],
                "home_team": response.get_data_frames()[1],
            }
        except requests.exceptions.RequestException as e:
            _log_error(f"Error fetching game rotation for {game_id}: {e}")

            if attempt < max_retries:
                time.sleep(5)
            else:
                return None
        except Exception as e:
            _log_error(f"Unexpected error fetching game rotation for {game_id}: {e}")
            return None
