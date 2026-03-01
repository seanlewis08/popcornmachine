"""NBA CDN fetch module with rate limiting.

Uses cdn.nba.com endpoints instead of stats.nba.com to avoid
cloud IP blocking in CI environments (GitHub Actions, etc.).

CDN endpoints used:
- Schedule: scheduleLeagueV2.json (game lookup by date)
- Boxscore: boxscore_{game_id}.json (player/team stats)
- PlayByPlay: playbyplay_{game_id}.json (play events)
- Rotation: Derived from play-by-play substitution events
"""

import sys
import time
from datetime import datetime
from typing import Optional

import pandas as pd
import requests

_CDN_BASE = "https://cdn.nba.com/static/json"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}

# Module-level caches to avoid redundant fetches within a pipeline run
_schedule_cache: Optional[dict] = None
_pbp_cache: dict[str, pd.DataFrame] = {}
_boxscore_raw_cache: dict[str, dict] = {}


def _log_error(msg: str) -> None:
    """Log timestamped error to stderr."""
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] {msg}", file=sys.stderr, flush=True)


def _fetch_json(url: str, delay: float = 1.0, max_retries: int = 2) -> Optional[dict]:
    """Fetch JSON from a URL with retry logic."""
    for attempt in range(max_retries + 1):
        try:
            time.sleep(delay)
            resp = requests.get(url, headers=_HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            _log_error(f"Error fetching {url}: {e}")
            if attempt < max_retries:
                time.sleep(5)
            else:
                return None
        except Exception as e:
            _log_error(f"Unexpected error fetching {url}: {e}")
            return None


# ---------------------------------------------------------------------------
# Clock / time helpers
# ---------------------------------------------------------------------------

def _parse_v3_clock(clock_str: str) -> str:
    """Convert CDN/V3 clock format 'PT04M30.00S' to V2 format '4:30'."""
    if not isinstance(clock_str, str) or not clock_str.startswith("PT"):
        return str(clock_str)
    try:
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


def _cdn_minutes_to_mmss(minutes_str: str) -> str:
    """Convert CDN minutes 'PT34M20.00S' to 'MM:SS' format for _parse_minutes."""
    return _parse_v3_clock(minutes_str)


def _clock_str_to_seconds(clock_str: str) -> float:
    """Convert 'M:SS' or 'MM:SS' clock string to seconds remaining."""
    try:
        parts = str(clock_str).split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return 0.0


def _clock_to_decisecs(period: int, clock_str: str) -> int:
    """Convert period + V2 clock string ('M:SS') to deciseconds from game start."""
    remaining_secs = _clock_str_to_seconds(clock_str)
    period_duration = 720 if period <= 4 else 300
    elapsed_in_period = period_duration - remaining_secs

    if period <= 4:
        base = (period - 1) * 7200
    else:
        base = 4 * 7200 + (period - 5) * 3000

    return int(base + elapsed_in_period * 10)


# ---------------------------------------------------------------------------
# Schedule helpers
# ---------------------------------------------------------------------------

def _normalize_schedule_date(date_str: str) -> str:
    """Normalize CDN schedule date to YYYY-MM-DD format."""
    if not date_str:
        return ""
    # Format 1: "MM/DD/YYYY HH:MM:SS"
    try:
        dt = datetime.strptime(date_str.split(" ")[0], "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    # Format 2: ISO "YYYY-MM-DDTHH:MM:SS" or "YYYY-MM-DD ..."
    try:
        return date_str[:10]
    except (IndexError, TypeError):
        return ""


def _get_schedule() -> Optional[dict]:
    """Download and cache the full season schedule."""
    global _schedule_cache
    if _schedule_cache is not None:
        return _schedule_cache

    data = _fetch_json(f"{_CDN_BASE}/staticData/scheduleLeagueV2.json", delay=0.5)
    if data:
        _schedule_cache = data
    return _schedule_cache


# ---------------------------------------------------------------------------
# Public fetch functions (same signatures as before)
# ---------------------------------------------------------------------------

def fetch_scoreboard(game_date: str, delay: float = 1.5) -> Optional[dict]:
    """
    Fetch scoreboard data for a given date using CDN schedule endpoint.

    Args:
        game_date: Date string in YYYY-MM-DD format
        delay: Delay in seconds before making the API call (default 1.5)

    Returns:
        Dict with 'game_header' and 'line_score' DataFrames, or None on failure
    """
    schedule = _get_schedule()
    if schedule is None:
        return None

    league_schedule = schedule.get("leagueSchedule", {})
    game_dates = league_schedule.get("gameDates", [])

    # Find games for the requested date
    matching_games = []
    for gd in game_dates:
        normalized = _normalize_schedule_date(gd.get("gameDate", ""))
        if normalized == game_date:
            matching_games = gd.get("games", [])
            break

    # No games on this date — return empty DataFrames (not None)
    # Empty DataFrames signal "API responded, no games" vs None = "API error"
    if not matching_games:
        return {
            "game_header": pd.DataFrame(
                columns=["GAME_ID", "HOME_TEAM_ID", "VISITOR_TEAM_ID", "GAME_STATUS_TEXT"]
            ),
            "line_score": pd.DataFrame(
                columns=["GAME_ID", "TEAM_ID", "TEAM_ABBREVIATION", "TEAM_NAME", "PTS"]
            ),
        }

    # Build DataFrames matching ScoreboardV2 format
    game_header_rows = []
    line_score_rows = []

    for game in matching_games:
        game_id = str(game.get("gameId", ""))
        home = game.get("homeTeam", {})
        away = game.get("awayTeam", {})

        # Only include completed games (gameStatus 3 = Final)
        game_status = game.get("gameStatus", 0)
        if game_status != 3:
            continue

        game_header_rows.append({
            "GAME_ID": game_id,
            "HOME_TEAM_ID": str(home.get("teamId", "")),
            "VISITOR_TEAM_ID": str(away.get("teamId", "")),
            "GAME_STATUS_TEXT": game.get("gameStatusText", "Final"),
        })

        # Home team line score entry
        line_score_rows.append({
            "GAME_ID": game_id,
            "TEAM_ID": str(home.get("teamId", "")),
            "TEAM_ABBREVIATION": home.get("teamTricode", ""),
            "TEAM_NAME": home.get("teamName", ""),
            "PTS": home.get("score", 0),
        })

        # Away team line score entry
        line_score_rows.append({
            "GAME_ID": game_id,
            "TEAM_ID": str(away.get("teamId", "")),
            "TEAM_ABBREVIATION": away.get("teamTricode", ""),
            "TEAM_NAME": away.get("teamName", ""),
            "PTS": away.get("score", 0),
        })

    return {
        "game_header": pd.DataFrame(game_header_rows),
        "line_score": pd.DataFrame(line_score_rows),
    }


def fetch_boxscore(game_id: str, delay: float = 1.5) -> Optional[dict]:
    """
    Fetch box score from CDN endpoint.

    Args:
        game_id: Game ID string
        delay: Delay in seconds before making the API call (default 1.5)

    Returns:
        Dict with 'player_stats' and 'team_stats' DataFrames, or None on failure
    """
    url = f"{_CDN_BASE}/liveData/boxscore/boxscore_{game_id}.json"
    data = _fetch_json(url, delay=delay)
    if data is None:
        return None

    game = data.get("game", {})
    # Cache raw game data for rotation derivation and roster lookup
    _boxscore_raw_cache[game_id] = game

    home_team = game.get("homeTeam", {})
    away_team = game.get("awayTeam", {})

    # Build player_stats DataFrame
    player_rows = []
    for team_data in [home_team, away_team]:
        team_tricode = team_data.get("teamTricode", "")
        team_id = team_data.get("teamId", 0)
        team_name = team_data.get("teamName", "")

        for player in team_data.get("players", []):
            stats = player.get("statistics", {})
            if not stats or player.get("played", "") != "1":
                continue

            # Convert CDN minutes "PT34M20.00S" to "34:20" for _parse_minutes
            minutes_raw = stats.get("minutes", "PT00M00.00S")
            minutes_str = _cdn_minutes_to_mmss(minutes_raw)

            first = player.get("firstName", "")
            family = player.get("familyName", "")
            name = player.get("name", f"{first} {family}".strip())

            player_rows.append({
                "PLAYER_ID": player.get("personId", 0),
                "PLAYER_NAME": name,
                "TEAM_ABBREVIATION": team_tricode,
                "TEAM_ID": team_id,
                "TEAM_NAME": team_name,
                "GAME_ID": game_id,
                "POSITION": player.get("position", ""),
                "MIN": minutes_str,
                "FGM": stats.get("fieldGoalsMade", 0),
                "FGA": stats.get("fieldGoalsAttempted", 0),
                "FG3M": stats.get("threePointersMade", 0),
                "FG3A": stats.get("threePointersAttempted", 0),
                "FTM": stats.get("freeThrowsMade", 0),
                "FTA": stats.get("freeThrowsAttempted", 0),
                "OREB": stats.get("reboundsOffensive", 0),
                "DREB": stats.get("reboundsDefensive", 0),
                "REB": stats.get("reboundsTotal", 0),
                "AST": stats.get("assists", 0),
                "STL": stats.get("steals", 0),
                "BLK": stats.get("blocks", 0),
                "TO": stats.get("turnovers", 0),
                "PF": stats.get("foulsPersonal", 0),
                "PTS": stats.get("points", 0),
                "PLUS_MINUS": stats.get("plusMinusPoints", 0),
                # CDN boxscore includes position — used as ROSTER_POSITION later
                "ROSTER_POSITION": player.get("position", ""),
            })

    # Build team_stats DataFrame
    team_rows = []
    for team_data in [home_team, away_team]:
        stats = team_data.get("statistics", {})
        if not stats:
            continue
        team_rows.append({
            "TEAM_ABBREVIATION": team_data.get("teamTricode", ""),
            "TEAM_ID": team_data.get("teamId", 0),
            "TEAM_NAME": team_data.get("teamName", ""),
            "GAME_ID": game_id,
            "MIN": "",
            "FGM": stats.get("fieldGoalsMade", 0),
            "FGA": stats.get("fieldGoalsAttempted", 0),
            "FG3M": stats.get("threePointersMade", 0),
            "FG3A": stats.get("threePointersAttempted", 0),
            "FTM": stats.get("freeThrowsMade", 0),
            "FTA": stats.get("freeThrowsAttempted", 0),
            "OREB": stats.get("reboundsOffensive", 0),
            "DREB": stats.get("reboundsDefensive", 0),
            "REB": stats.get("reboundsTotal", 0),
            "AST": stats.get("assists", 0),
            "STL": stats.get("steals", 0),
            "BLK": stats.get("blocks", 0),
            "TO": stats.get("turnovers", 0),
            "PF": stats.get("foulsPersonal", 0),
            "PTS": stats.get("points", 0),
            "PLUS_MINUS": stats.get("plusMinusPoints", 0),
        })

    return {
        "player_stats": pd.DataFrame(player_rows),
        "team_stats": pd.DataFrame(team_rows),
    }


def fetch_playbyplay(game_id: str, delay: float = 1.5) -> Optional[pd.DataFrame]:
    """
    Fetch play-by-play from CDN endpoint.

    Maps CDN field names to V2-compatible column names so transform.py
    works unchanged.

    Args:
        game_id: Game ID string
        delay: Delay in seconds before making the API call (default 1.5)

    Returns:
        DataFrame with play-by-play events, or None on failure
    """
    # Return cached if available
    if game_id in _pbp_cache:
        return _pbp_cache[game_id]

    url = f"{_CDN_BASE}/liveData/playbyplay/playbyplay_{game_id}.json"
    data = _fetch_json(url, delay=delay)
    if data is None:
        return None

    actions = data.get("game", {}).get("actions", [])
    if not actions:
        df = pd.DataFrame()
        _pbp_cache[game_id] = df
        return df

    rows = []
    for action in actions:
        clock_raw = action.get("clock", "")
        clock_v2 = _parse_v3_clock(clock_raw)

        rows.append({
            "PERIOD": action.get("period", 0),
            "PLAYER1_ID": action.get("personId", 0),
            "PCTIMESTRING": clock_v2,
            "EVENTMSGTYPE": action.get("actionType", ""),
            "EVENTMSGACTIONTYPE": action.get("subType", ""),
            "EVENTNUM": action.get("actionNumber", 0),
            "PLAYER1_TEAM_ID": action.get("teamId", 0),
            "PLAYER1_TEAM_ABBREVIATION": action.get("teamTricode", ""),
            "PLAYER1_NAME": action.get("playerNameI", action.get("playerName", "")),
            "HOMEDESCRIPTION": action.get("description", ""),
            "VISITORDESCRIPTION": action.get("description", ""),
            "SCORE_HOME": action.get("scoreHome", "0"),
            "SCORE_AWAY": action.get("scoreAway", "0"),
            # Preserve raw CDN fields needed for rotation derivation
            "_CDN_CLOCK_RAW": clock_raw,
            "_CDN_PERSON_IDS_FILTER": action.get("personIdsFilter", []),
            "_CDN_QUALIFIERS": action.get("qualifiers", []),
            "_CDN_SHOT_RESULT": action.get("shotResult", ""),
            "_CDN_IS_FIELD_GOAL": action.get("isFieldGoal", 0),
        })

    df = pd.DataFrame(rows)
    _pbp_cache[game_id] = df
    return df


def _derive_rotation_from_pbp(game_id: str, pbp_df: pd.DataFrame) -> Optional[dict]:
    """
    Derive rotation (stint) data from play-by-play substitution events.

    Since the CDN doesn't have a GameRotation endpoint, we reconstruct
    player stints from substitution events in the play-by-play data.

    Returns dict with 'away_team' and 'home_team' DataFrames matching
    the GameRotation format (PERSON_ID, IN_TIME_REAL, OUT_TIME_REAL, PT_DIFF).
    """
    if pbp_df is None or pbp_df.empty:
        return None

    # Get cached boxscore for starter/team info
    game_data = _boxscore_raw_cache.get(game_id)
    if game_data is None:
        return None

    home_team = game_data.get("homeTeam", {})
    away_team = game_data.get("awayTeam", {})
    home_team_id = int(home_team.get("teamId", 0))
    away_team_id = int(away_team.get("teamId", 0))

    # Identify starters from boxscore
    home_starters = set()
    away_starters = set()
    for player in home_team.get("players", []):
        if player.get("starter") == "1":
            home_starters.add(int(player.get("personId", 0)))
    for player in away_team.get("players", []):
        if player.get("starter") == "1":
            away_starters.add(int(player.get("personId", 0)))

    # on_court tracks {player_id: (in_decisecs, home_score_str, away_score_str)}
    home_on_court: dict[int, tuple[int, str, str]] = {}
    away_on_court: dict[int, tuple[int, str, str]] = {}

    # Initialize starters at game start (0 deciseconds)
    for pid in home_starters:
        home_on_court[pid] = (0, "0", "0")
    for pid in away_starters:
        away_on_court[pid] = (0, "0", "0")

    home_rotation_rows: list[dict] = []
    away_rotation_rows: list[dict] = []

    # Process substitution events
    for _, event in pbp_df.iterrows():
        event_type = str(event.get("EVENTMSGTYPE", "")).lower()
        if event_type != "substitution":
            continue

        person_id = int(event.get("PLAYER1_ID", 0))
        team_id = int(event.get("PLAYER1_TEAM_ID", 0))
        period = int(event.get("PERIOD", 1))
        clock_str = str(event.get("PCTIMESTRING", "0:00"))

        # Convert clock to deciseconds from game start
        decisecs = _clock_to_decisecs(period, clock_str)

        score_home = str(event.get("SCORE_HOME", "0"))
        score_away = str(event.get("SCORE_AWAY", "0"))

        is_home = (team_id == home_team_id)
        on_court = home_on_court if is_home else away_on_court
        rotation_rows = home_rotation_rows if is_home else away_rotation_rows

        if person_id in on_court:
            # Player going OUT — close their stint
            in_decisecs, in_home_score, in_away_score = on_court.pop(person_id)
            try:
                home_diff = int(score_home) - int(in_home_score)
                away_diff = int(score_away) - int(in_away_score)
                pt_diff = home_diff - away_diff if is_home else away_diff - home_diff
            except (ValueError, TypeError):
                pt_diff = 0

            rotation_rows.append({
                "PERSON_ID": person_id,
                "IN_TIME_REAL": in_decisecs,
                "OUT_TIME_REAL": decisecs,
                "PT_DIFF": pt_diff,
                "TEAM_ID": team_id,
            })
        else:
            # Player coming IN — start a new stint
            on_court[person_id] = (decisecs, score_home, score_away)

    # Close remaining stints at end of game
    if not pbp_df.empty:
        last_event = pbp_df.iloc[-1]
        last_period = int(last_event.get("PERIOD", 4))
        last_score_home = str(last_event.get("SCORE_HOME", "0"))
        last_score_away = str(last_event.get("SCORE_AWAY", "0"))

        # End of last period in deciseconds
        if last_period <= 4:
            end_decisecs = last_period * 7200
        else:
            end_decisecs = 4 * 7200 + (last_period - 4) * 3000

        for on_court, rotation_rows, is_home, team_id in [
            (home_on_court, home_rotation_rows, True, home_team_id),
            (away_on_court, away_rotation_rows, False, away_team_id),
        ]:
            for pid, (in_decisecs, in_home_score, in_away_score) in on_court.items():
                try:
                    home_diff = int(last_score_home) - int(in_home_score)
                    away_diff = int(last_score_away) - int(in_away_score)
                    pt_diff = home_diff - away_diff if is_home else away_diff - home_diff
                except (ValueError, TypeError):
                    pt_diff = 0

                rotation_rows.append({
                    "PERSON_ID": pid,
                    "IN_TIME_REAL": in_decisecs,
                    "OUT_TIME_REAL": end_decisecs,
                    "PT_DIFF": pt_diff,
                    "TEAM_ID": team_id,
                })

    empty_cols = ["PERSON_ID", "IN_TIME_REAL", "OUT_TIME_REAL", "PT_DIFF", "TEAM_ID"]
    return {
        "away_team": pd.DataFrame(away_rotation_rows) if away_rotation_rows else pd.DataFrame(columns=empty_cols),
        "home_team": pd.DataFrame(home_rotation_rows) if home_rotation_rows else pd.DataFrame(columns=empty_cols),
    }


def fetch_game_rotation(game_id: str, delay: float = 1.5) -> Optional[dict]:
    """
    Derive game rotation data from play-by-play substitution events.

    The CDN doesn't have a GameRotation endpoint, so we reconstruct
    player stints from substitution events in the play-by-play.

    Args:
        game_id: Game ID string
        delay: Delay in seconds before making the API call (default 1.5)

    Returns:
        Dict with 'away_team' and 'home_team' DataFrames, or None on failure
    """
    # Get PBP data (uses cache if already fetched)
    pbp_df = fetch_playbyplay(game_id, delay=delay)
    if pbp_df is None:
        return None

    return _derive_rotation_from_pbp(game_id, pbp_df)


def fetch_roster(team_id: str, season: str, delay: float = 1.5) -> Optional[pd.DataFrame]:
    """
    Return player positions from cached CDN boxscore data.

    The CDN boxscore includes player positions, so we don't need a
    separate roster endpoint.

    Args:
        team_id: NBA team ID string
        season: Season string (unused for CDN, kept for API compatibility)
        delay: Delay in seconds (unused for CDN, kept for API compatibility)

    Returns:
        DataFrame with PLAYER_ID and POSITION columns, or None
    """
    # Search cached boxscore data for this team
    for _game_id, game_data in _boxscore_raw_cache.items():
        for team_key in ["homeTeam", "awayTeam"]:
            team = game_data.get(team_key, {})
            if str(team.get("teamId", "")) == str(team_id):
                rows = []
                for player in team.get("players", []):
                    rows.append({
                        "PLAYER_ID": player.get("personId", 0),
                        "POSITION": player.get("position", ""),
                    })
                if rows:
                    return pd.DataFrame(rows)
    return None
