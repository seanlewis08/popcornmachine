"""Transform module mapping NBA API data to JSON contracts."""

import re
from typing import Optional

import pandas as pd


def _safe_int(val) -> int:
    """Safely convert a value to int, handling NaN and string types."""
    if pd.isna(val):
        return 0
    return int(val)


def _parse_minutes(min_val) -> float:
    """
    Parse a minutes value that may be numeric or 'MM:SS' string format.

    BoxScoreTraditionalV2 returns MIN as either a float (e.g. 34.5)
    or a string like '34:20' depending on the API version.
    """
    if pd.isna(min_val) or min_val == 0:
        return 0.0
    if isinstance(min_val, (int, float)):
        return float(min_val)
    s = str(min_val)
    if ":" in s:
        parts = s.split(":")
        try:
            return round(int(parts[0]) + int(parts[1]) / 60, 1)
        except (ValueError, IndexError):
            return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _coerce_id(val) -> str:
    """Coerce an ID value to string for safe comparison."""
    if pd.isna(val):
        return ""
    return str(int(val)) if isinstance(val, float) else str(val)


def _rotation_time_to_period_clock(
    in_time_real: int, out_time_real: int
) -> tuple[int, str, str]:
    """
    Convert millisecond timestamps to (period, in_clock, out_clock) format.

    Each regulation period is 720 seconds (12 minutes).
    Period 1 starts at t=0, Period 2 at t=720000ms, etc.

    Args:
        in_time_real: In-time in milliseconds
        out_time_real: Out-time in milliseconds

    Returns:
        Tuple of (period, in_clock_str, out_clock_str)
    """
    ms_per_period = 720000  # 12 minutes in milliseconds
    period = (in_time_real // ms_per_period) + 1
    period_start_ms = (period - 1) * ms_per_period

    # Convert to seconds within the period
    in_seconds = (in_time_real - period_start_ms) // 1000
    out_seconds = (out_time_real - period_start_ms) // 1000

    in_clock = _seconds_to_clock(in_seconds)
    out_clock = _seconds_to_clock(out_seconds)

    return int(period), in_clock, out_clock


def _seconds_to_clock(seconds: int) -> str:
    """Convert seconds to MM:SS clock format."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def _compute_stint_minutes(in_time_real: int, out_time_real: int) -> float:
    """Compute stint duration in minutes."""
    duration_ms = out_time_real - in_time_real
    return round(duration_ms / 60000, 1)


def _filter_pbp_for_stint(
    pbp_df: pd.DataFrame, player_id, period: int, in_clock: str, out_clock: str
) -> pd.DataFrame:
    """
    Filter PBP events by player and time window within a period.

    Args:
        pbp_df: Play-by-play DataFrame
        player_id: Player ID to filter by
        period: Period number
        in_clock: In-time as MM:SS string
        out_clock: Out-time as MM:SS string

    Returns:
        Filtered DataFrame
    """
    if pbp_df.empty:
        return pbp_df

    # Coerce types for safe comparison (API may return int or str)
    pid_str = str(int(player_id)) if not pd.isna(player_id) else ""

    # Filter by period and player, handling type mismatches
    filtered = pbp_df[
        (pbp_df["PERIOD"].astype(str) == str(period))
        & (pbp_df["PLAYER1_ID"].astype(str) == pid_str)
    ].copy()

    # Convert clock strings to seconds for comparison
    def clock_to_seconds(clock_str: str) -> int:
        # Handle potential NaN values in case of malformed data
        if pd.isna(clock_str):
            return 0
        parts = str(clock_str).split(":")
        return int(parts[0]) * 60 + int(parts[1])

    in_sec = clock_to_seconds(in_clock)
    out_sec = clock_to_seconds(out_clock)

    # Filter by time within period (note: clock counts down)
    filtered = filtered[
        (filtered["PCTIMESTRING"].apply(clock_to_seconds) >= out_sec)
        & (filtered["PCTIMESTRING"].apply(clock_to_seconds) <= in_sec)
    ]

    return filtered


def _pbp_event_to_type(event_msg_type, event_msg_action_type) -> str:
    """
    Map EVENTMSGTYPE codes to human-readable event types.

    Handles both V2 integer codes (1=make, 2=miss, etc.) and V3 string
    types (\"2pt\", \"3pt\", \"freethrow\", etc.) since PlayByPlayV3 returns
    string actionType values that get mapped to EVENTMSGTYPE.

    Args:
        event_msg_type: Event message type code (int for V2, str for V3)
        event_msg_action_type: Event message action type code

    Returns:
        Human-readable event type string
    """
    # Handle V3 string action types first
    if isinstance(event_msg_type, str):
        emt_lower = event_msg_type.lower()
        if emt_lower == "2pt":
            desc = str(event_msg_action_type).lower() if event_msg_action_type else ""
            if "miss" in desc:
                return "miss2"
            return "make2"
        elif emt_lower == "3pt":
            desc = str(event_msg_action_type).lower() if event_msg_action_type else ""
            if "miss" in desc:
                return "miss3"
            return "make3"
        elif emt_lower in ("freethrow", "free throw", "ft"):
            return "fta"
        elif emt_lower == "rebound":
            return "reb"
        elif emt_lower == "turnover":
            return "tov"
        elif emt_lower == "foul":
            return "foul"
        elif emt_lower == "steal":
            return "stl"
        elif emt_lower == "block":
            return "blk"
        elif emt_lower == "assist":
            return "ast"
        else:
            # Try to convert string to int for backward compatibility
            try:
                event_msg_type = int(event_msg_type)
            except (ValueError, TypeError):
                return "other"

    # V2 integer codes (or converted from string above)
    try:
        emt = int(event_msg_type)
    except (ValueError, TypeError):
        return "other"

    if emt == 1:  # Make
        try:
            emat = int(event_msg_action_type) if event_msg_action_type else 0
        except (ValueError, TypeError):
            emat = 0
        if emat == 1:
            return "make2"
        elif emat in [2, 3]:
            return "make3"
        else:
            return "make"
    elif emt == 2:  # Miss
        try:
            emat = int(event_msg_action_type) if event_msg_action_type else 0
        except (ValueError, TypeError):
            emat = 0
        if emat == 1:
            return "miss2"
        elif emat in [2, 3]:
            return "miss3"
        else:
            return "miss"
    elif emt == 3:  # Free throw
        return "fta"
    elif emt == 4:  # Rebound
        return "reb"
    elif emt == 5:  # Turnover
        return "tov"
    elif emt == 6:  # Foul
        return "foul"
    else:
        return "other"


def _aggregate_stint_stats(pbp_events: pd.DataFrame) -> dict[str, int]:
    """
    Count stat categories from PBP event types.

    Args:
        pbp_events: Filtered play-by-play events for a stint

    Returns:
        Dict with aggregated stat counts
    """
    stats = {
        "fgm": 0,
        "fga": 0,
        "fg3m": 0,
        "fg3a": 0,
        "ftm": 0,
        "fta": 0,
        "oreb": 0,
        "reb": 0,
        "ast": 0,
        "blk": 0,
        "stl": 0,
        "tov": 0,
        "pf": 0,
        "pts": 0,
    }

    for _, event in pbp_events.iterrows():
        event_type = _pbp_event_to_type(
            event.get("EVENTMSGTYPE", 0), event.get("EVENTMSGACTIONTYPE", 0)
        )

        if event_type == "make2":
            stats["fgm"] += 1
            stats["fga"] += 1
            stats["pts"] += 2
        elif event_type == "make3":
            stats["fgm"] += 1
            stats["fga"] += 1
            stats["fg3m"] += 1
            stats["fg3a"] += 1
            stats["pts"] += 3
        elif event_type == "miss2":
            stats["fga"] += 1
        elif event_type == "miss3":
            stats["fga"] += 1
            stats["fg3a"] += 1
        elif event_type == "fta":
            stats["fta"] += 1
            # PBP doesn't distinguish made/missed FTs, so we count conservatively
            if "MADE" in str(event.get("HOMEDESCRIPTION", "")) or \
               "MADE" in str(event.get("VISITORDESCRIPTION", "")):
                stats["ftm"] += 1
                stats["pts"] += 1
        elif event_type == "reb":
            stats["reb"] += 1
        elif event_type == "tov":
            stats["tov"] += 1
        elif event_type == "foul":
            stats["pf"] += 1

    return stats


def transform_scores(scoreboard_data: dict, date: str) -> list[dict]:
    """
    Transform ScoreBoardV2 response into scores/YYYY-MM-DD.json contract.

    Maps team info and pairs home/away by GAME_ID.

    Args:
        scoreboard_data: Dict with 'game_header' and 'line_score' DataFrames
        date: Game date as YYYY-MM-DD string

    Returns:
        List of game dicts with team names, tricodes, and scores
    """
    game_header = scoreboard_data["game_header"]
    line_score = scoreboard_data["line_score"]

    # Get date from first game (all games are same date in scoreboard)
    if len(game_header) == 0:
        return []

    # Coerce ID columns to string for safe comparison
    game_header["GAME_ID"] = game_header["GAME_ID"].astype(str)
    line_score["GAME_ID"] = line_score["GAME_ID"].astype(str)
    line_score["TEAM_ID"] = line_score["TEAM_ID"].astype(str)
    game_header["HOME_TEAM_ID"] = game_header["HOME_TEAM_ID"].astype(str)
    game_header["VISITOR_TEAM_ID"] = game_header["VISITOR_TEAM_ID"].astype(str)

    # Group line_score by game
    games = []
    for game_id in game_header["GAME_ID"].unique():
        game_teams = line_score[line_score["GAME_ID"] == game_id]

        if len(game_teams) < 2:
            continue

        # Find home and away teams
        game_info = game_header[game_header["GAME_ID"] == game_id].iloc[0]
        home_team_id = game_info["HOME_TEAM_ID"]
        away_team_id = game_info["VISITOR_TEAM_ID"]

        home_row = game_teams[game_teams["TEAM_ID"] == home_team_id]
        away_row = game_teams[game_teams["TEAM_ID"] == away_team_id]

        if len(home_row) == 0 or len(away_row) == 0:
            continue

        home_team = home_row.iloc[0]
        away_team = away_row.iloc[0]

        game = {
            "gameId": str(game_id),
            "date": date,
            "homeTeam": {
                "tricode": home_team["TEAM_ABBREVIATION"],
                "name": home_team["TEAM_NAME"],
                "score": int(home_team["PTS"]),
            },
            "awayTeam": {
                "tricode": away_team["TEAM_ABBREVIATION"],
                "name": away_team["TEAM_NAME"],
                "score": int(away_team["PTS"]),
            },
            "status": game_info.get("GAME_STATUS_TEXT", "Final"),
        }
        games.append(game)

    return games


def transform_boxscore(
    game_id: str,
    date: str,
    scoreboard_data: dict,
    boxscore_data: dict,
    rotation_data: dict,
    pbp_data: pd.DataFrame,
) -> dict:
    """
    Transform into boxscore.json contract.

    For each player:
    - Extract full-game totals from BoxScoreTraditionalV2
    - Compute derived metrics (hv, prod, eff)
    - Build per-stint breakdowns from GameRotation + PlayByPlayV2

    Args:
        game_id: Game ID
        date: Game date as YYYY-MM-DD
        scoreboard_data: Scoreboard dict
        boxscore_data: BoxScore dict with player_stats and team_stats
        rotation_data: Rotation dict with away_team and home_team
        pbp_data: Play-by-play DataFrame

    Returns:
        Boxscore dict matching JSON contract
    """
    line_score = scoreboard_data["line_score"].copy()
    game_header = scoreboard_data["game_header"].copy()
    player_stats = boxscore_data["player_stats"]
    team_stats = boxscore_data["team_stats"]

    # Validate required data is not empty
    if len(game_header) == 0:
        raise ValueError(f"Game header is empty for game {game_id}")
    if len(line_score) == 0:
        raise ValueError(f"Line score is empty for game {game_id}")

    # Coerce ID columns to string for safe comparison
    gid = str(game_id)
    game_header["GAME_ID"] = game_header["GAME_ID"].astype(str)
    game_header["HOME_TEAM_ID"] = game_header["HOME_TEAM_ID"].astype(str)
    line_score["GAME_ID"] = line_score["GAME_ID"].astype(str)
    line_score["TEAM_ID"] = line_score["TEAM_ID"].astype(str)

    # Get home/away team info
    game_info = game_header[game_header["GAME_ID"] == gid]
    if len(game_info) == 0:
        raise ValueError(f"Game info not found for game {game_id}")
    game_info = game_info.iloc[0]
    home_team_id = game_info["HOME_TEAM_ID"]

    home_line = line_score[
        (line_score["GAME_ID"] == gid) & (line_score["TEAM_ID"] == home_team_id)
    ]
    away_line = line_score[
        (line_score["GAME_ID"] == gid) & (line_score["TEAM_ID"] != home_team_id)
    ]
    if len(home_line) == 0 or len(away_line) == 0:
        raise ValueError(f"Home or away line score not found for game {game_id}")
    home_line = home_line.iloc[0]
    away_line = away_line.iloc[0]

    # Build player list
    players = []
    for _, player in player_stats.iterrows():
        player_id = player["PLAYER_ID"]

        # Skip DNPs
        if pd.isna(player["MIN"]) or player["MIN"] == 0 or str(player["MIN"]).strip() == "":
            continue

        minutes = _parse_minutes(player["MIN"])

        # Compute derived metrics
        pts = int(player["PTS"]) if not pd.isna(player["PTS"]) else 0
        reb = int(player["REB"]) if not pd.isna(player["REB"]) else 0
        ast = int(player["AST"]) if not pd.isna(player["AST"]) else 0
        blk = int(player["BLK"]) if not pd.isna(player["BLK"]) else 0
        stl = int(player["STL"]) if not pd.isna(player["STL"]) else 0
        tov = int(player["TO"]) if not pd.isna(player["TO"]) else 0

        hv = reb + ast + blk + stl - tov
        prod = (pts + hv) / minutes if minutes > 0 else 0
        prod = round(prod, 2)

        fga = int(player["FGA"]) if not pd.isna(player["FGA"]) else 0
        fgm = int(player["FGM"]) if not pd.isna(player["FGM"]) else 0
        fta = int(player["FTA"]) if not pd.isna(player["FTA"]) else 0
        ftm = int(player["FTM"]) if not pd.isna(player["FTM"]) else 0

        eff = pts + reb + ast + stl + blk - (fga - fgm) - (fta - ftm) - tov

        # Get stints from rotation
        team_rotation = (
            rotation_data["home_team"]
            if player["TEAM_ABBREVIATION"] == home_line["TEAM_ABBREVIATION"]
            else rotation_data["away_team"]
        )

        player_rotation = team_rotation[
            team_rotation["PERSON_ID"].astype(str) == str(int(player_id))
        ]
        stints = []

        for _, stint in player_rotation.iterrows():
            period, in_clock, out_clock = _rotation_time_to_period_clock(
                stint["IN_TIME_REAL"], stint["OUT_TIME_REAL"]
            )
            minutes_stint = _compute_stint_minutes(
                stint["IN_TIME_REAL"], stint["OUT_TIME_REAL"]
            )

            # Filter PBP events for this stint and aggregate stats
            pbp_stint = _filter_pbp_for_stint(pbp_data, player_id, period, in_clock, out_clock)
            stint_stats = _aggregate_stint_stats(pbp_stint)

            stint_dict = {
                "period": int(period),
                "inTime": in_clock,
                "outTime": out_clock,
                "minutes": minutes_stint,
                "plusMinus": int(stint.get("PT_DIFF", 0)),
                "fgm": stint_stats["fgm"],
                "fga": stint_stats["fga"],
                "fg3m": stint_stats["fg3m"],
                "fg3a": stint_stats["fg3a"],
                "ftm": stint_stats["ftm"],
                "fta": stint_stats["fta"],
                "oreb": stint_stats["oreb"],
                "reb": stint_stats["reb"],
                "ast": stint_stats["ast"],
                "blk": stint_stats["blk"],
                "stl": stint_stats["stl"],
                "tov": stint_stats["tov"],
                "pf": stint_stats["pf"],
                "pts": stint_stats["pts"],
            }
            stints.append(stint_dict)

        player_dict = {
            "playerId": str(player_id),
            "name": player["PLAYER_NAME"],
            "team": player["TEAM_ABBREVIATION"],
            "totals": {
                "min": round(minutes, 1),
                "fgm": int(player["FGM"]) if not pd.isna(player["FGM"]) else 0,
                "fga": int(player["FGA"]) if not pd.isna(player["FGA"]) else 0,
                "fg3m": int(player["FG3M"]) if not pd.isna(player["FG3M"]) else 0,
                "fg3a": int(player["FG3A"]) if not pd.isna(player["FG3A"]) else 0,
                "ftm": int(player["FTM"]) if not pd.isna(player["FTM"]) else 0,
                "fta": int(player["FTA"]) if not pd.isna(player["FTA"]) else 0,
                "oreb": int(player["OREB"]) if not pd.isna(player["OREB"]) else 0,
                "reb": int(player["REB"]) if not pd.isna(player["REB"]) else 0,
                "ast": int(player["AST"]) if not pd.isna(player["AST"]) else 0,
                "blk": int(player["BLK"]) if not pd.isna(player["BLK"]) else 0,
                "stl": int(player["STL"]) if not pd.isna(player["STL"]) else 0,
                "tov": int(player["TO"]) if not pd.isna(player["TO"]) else 0,
                "pf": int(player["PF"]) if not pd.isna(player["PF"]) else 0,
                "pts": pts,
                "plusMinus": int(player["PLUS_MINUS"])
                if not pd.isna(player["PLUS_MINUS"])
                else 0,
                "hv": hv,
                "prod": prod,
                "eff": eff,
            },
            "stints": stints,
        }
        players.append(player_dict)

    # Build team totals
    # team_stats may be empty if BoxScoreTraditionalV2 returns no team-level data.
    # Also handle TEAM_ID-based matching as fallback for abbreviation mismatches.
    if team_stats.empty:
        # Aggregate from player_stats as last resort
        home_players = player_stats[
            player_stats["TEAM_ABBREVIATION"] == home_line["TEAM_ABBREVIATION"]
        ]
        away_players = player_stats[
            player_stats["TEAM_ABBREVIATION"] == away_line["TEAM_ABBREVIATION"]
        ]
        _stat_cols = ["FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA",
                      "OREB", "REB", "AST", "BLK", "STL", "TO", "PF", "PTS"]

        def _sum_stats(df: pd.DataFrame) -> dict:
            result = {}
            for col in _stat_cols:
                if col in df.columns:
                    result[col] = int(df[col].fillna(0).sum())
                else:
                    result[col] = 0
            return result

        home_team_stats_dict = _sum_stats(home_players)
        away_team_stats_dict = _sum_stats(away_players)
    else:
        # Try matching by TEAM_ABBREVIATION first
        home_team_match = team_stats[
            team_stats["TEAM_ABBREVIATION"] == home_line["TEAM_ABBREVIATION"]
        ]
        away_team_match = team_stats[
            team_stats["TEAM_ABBREVIATION"] == away_line["TEAM_ABBREVIATION"]
        ]

        if home_team_match.empty or away_team_match.empty:
            # Try matching by TEAM_ID if abbreviation didn't work
            if "TEAM_ID" in team_stats.columns:
                team_stats["TEAM_ID"] = team_stats["TEAM_ID"].astype(str)
                home_team_match = team_stats[team_stats["TEAM_ID"] == home_team_id]
                away_team_match = team_stats[team_stats["TEAM_ID"] != home_team_id]

            if home_team_match.empty or away_team_match.empty:
                # Last fallback: use positional index if we have exactly 2 rows
                if len(team_stats) >= 2:
                    home_team_match = team_stats.iloc[[0]]
                    away_team_match = team_stats.iloc[[1]]
                else:
                    raise ValueError(
                        f"Cannot match team stats for game {game_id}. "
                        f"team_stats has {len(team_stats)} rows, "
                        f"columns: {list(team_stats.columns)}"
                    )

        home_team_stats_row = home_team_match.iloc[0]
        away_team_stats_row = away_team_match.iloc[0]
        home_team_stats_dict = {
            col: int(home_team_stats_row[col]) if col in home_team_stats_row.index
            else 0 for col in ["FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA",
                               "OREB", "REB", "AST", "BLK", "STL", "TO", "PF", "PTS"]
        }
        away_team_stats_dict = {
            col: int(away_team_stats_row[col]) if col in away_team_stats_row.index
            else 0 for col in ["FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA",
                               "OREB", "REB", "AST", "BLK", "STL", "TO", "PF", "PTS"]
        }

    # Use the dict we built above (works for both empty-team_stats and normal paths)
    h = home_team_stats_dict
    a = away_team_stats_dict

    team_totals = {
        "home": {
            "fgm": h["FGM"], "fga": h["FGA"],
            "fg3m": h["FG3M"], "fg3a": h["FG3A"],
            "ftm": h["FTM"], "fta": h["FTA"],
            "oreb": h["OREB"], "reb": h["REB"],
            "ast": h["AST"], "blk": h["BLK"],
            "stl": h["STL"], "tov": h["TO"],
            "pf": h["PF"], "pts": h["PTS"],
        },
        "away": {
            "fgm": a["FGM"], "fga": a["FGA"],
            "fg3m": a["FG3M"], "fg3a": a["FG3A"],
            "ftm": a["FTM"], "fta": a["FTA"],
            "oreb": a["OREB"], "reb": a["REB"],
            "ast": a["AST"], "blk": a["BLK"],
            "stl": a["STL"], "tov": a["TO"],
            "pf": a["PF"], "pts": a["PTS"],
        },
    }

    # Build period totals using game-level team stats
    # Since BoxScoreTraditionalV2 doesn't provide per-period data,
    # we use a single "Game" entry with actual team totals (phase 2 limitation)
    period_totals = {
        "home": [
            {
                "period": "Game",
                "fgm": h["FGM"], "fga": h["FGA"],
                "fg3m": h["FG3M"], "fg3a": h["FG3A"],
                "ftm": h["FTM"], "fta": h["FTA"],
                "pts": h["PTS"],
            }
        ],
        "away": [
            {
                "period": "Game",
                "fgm": a["FGM"], "fga": a["FGA"],
                "fg3m": a["FG3M"], "fg3a": a["FG3A"],
                "ftm": a["FTM"], "fta": a["FTA"],
                "pts": a["PTS"],
            }
        ],
    }

    return {
        "gameId": str(game_id),
        "date": date,
        "homeTeam": {
            "tricode": home_line["TEAM_ABBREVIATION"],
            "name": home_line["TEAM_NAME"],
            "score": int(home_line["PTS"]),
        },
        "awayTeam": {
            "tricode": away_line["TEAM_ABBREVIATION"],
            "name": away_line["TEAM_NAME"],
            "score": int(away_line["PTS"]),
        },
        "players": players,
        "teamTotals": team_totals,
        "periodTotals": period_totals,
    }


def transform_gameflow(
    game_id: str, scoreboard_data: dict, rotation_data: dict, pbp_data: pd.DataFrame
) -> dict:
    """
    Transform into gameflow.json contract.

    For each player stint from rotation data, attach filtered PBP events
    and per-stint stat summaries.

    Args:
        game_id: Game ID
        scoreboard_data: Scoreboard dict
        rotation_data: Rotation dict with away_team and home_team
        pbp_data: Play-by-play DataFrame

    Returns:
        Gameflow dict matching JSON contract
    """
    line_score = scoreboard_data["line_score"].copy()
    game_header = scoreboard_data["game_header"].copy()

    # Coerce ID columns to string for safe comparison
    gid = str(game_id)
    game_header["GAME_ID"] = game_header["GAME_ID"].astype(str)
    game_header["HOME_TEAM_ID"] = game_header["HOME_TEAM_ID"].astype(str)
    line_score["GAME_ID"] = line_score["GAME_ID"].astype(str)
    line_score["TEAM_ID"] = line_score["TEAM_ID"].astype(str)

    game_info_df = game_header[game_header["GAME_ID"] == gid]
    if game_info_df.empty:
        raise ValueError(f"Game info not found for game {game_id}")
    game_info = game_info_df.iloc[0]
    home_team_id = game_info["HOME_TEAM_ID"]

    home_line_df = line_score[
        (line_score["GAME_ID"] == gid) & (line_score["TEAM_ID"] == home_team_id)
    ]
    away_line_df = line_score[
        (line_score["GAME_ID"] == gid) & (line_score["TEAM_ID"] != home_team_id)
    ]
    if home_line_df.empty or away_line_df.empty:
        raise ValueError(f"Home or away line score not found for game {game_id}")
    home_line = home_line_df.iloc[0]
    away_line = away_line_df.iloc[0]

    players = []

    # Process home team
    for _, player_stint in rotation_data["home_team"].iterrows():
        player_id = player_stint["PERSON_ID"]
        period, in_clock, out_clock = _rotation_time_to_period_clock(
            player_stint["IN_TIME_REAL"], player_stint["OUT_TIME_REAL"]
        )
        minutes = _compute_stint_minutes(
            player_stint["IN_TIME_REAL"], player_stint["OUT_TIME_REAL"]
        )

        # Filter PBP for this player and stint
        pbp_stint = _filter_pbp_for_stint(pbp_data, player_id, period, in_clock, out_clock)

        # Convert PBP events to simple format
        events = []
        for _, event in pbp_stint.iterrows():
            event_dict = {
                "clock": event.get("PCTIMESTRING", ""),
                "type": _pbp_event_to_type(
                    event.get("EVENTMSGTYPE", 0), event.get("EVENTMSGACTIONTYPE", 0)
                ),
                "description": event.get("HOMEDESCRIPTION", "")
                or event.get("VISITORDESCRIPTION", ""),
            }
            events.append(event_dict)

        # Aggregate stint stats
        stint_stats = _aggregate_stint_stats(pbp_stint)

        player_dict = {
            "playerId": str(player_id),
            "name": f"{player_stint.get('PLAYER_FIRST', '')} {player_stint.get('PLAYER_LAST', '')}",
            "team": home_line["TEAM_ABBREVIATION"],
            "stints": [
                {
                    "period": int(period),
                    "inTime": in_clock,
                    "outTime": out_clock,
                    "minutes": minutes,
                    "plusMinus": int(player_stint.get("PT_DIFF", 0)),
                    "stats": stint_stats,
                    "events": events,
                }
            ],
        }
        players.append(player_dict)

    # Process away team
    for _, player_stint in rotation_data["away_team"].iterrows():
        player_id = player_stint["PERSON_ID"]
        period, in_clock, out_clock = _rotation_time_to_period_clock(
            player_stint["IN_TIME_REAL"], player_stint["OUT_TIME_REAL"]
        )
        minutes = _compute_stint_minutes(
            player_stint["IN_TIME_REAL"], player_stint["OUT_TIME_REAL"]
        )

        pbp_stint = _filter_pbp_for_stint(pbp_data, player_id, period, in_clock, out_clock)

        events = []
        for _, event in pbp_stint.iterrows():
            event_dict = {
                "clock": event.get("PCTIMESTRING", ""),
                "type": _pbp_event_to_type(
                    event.get("EVENTMSGTYPE", 0), event.get("EVENTMSGACTIONTYPE", 0)
                ),
                "description": event.get("HOMEDESCRIPTION", "")
                or event.get("VISITORDESCRIPTION", ""),
            }
            events.append(event_dict)

        stint_stats = _aggregate_stint_stats(pbp_stint)

        player_dict = {
            "playerId": str(player_id),
            "name": f"{player_stint.get('PLAYER_FIRST', '')} {player_stint.get('PLAYER_LAST', '')}",
            "team": away_line["TEAM_ABBREVIATION"],
            "stints": [
                {
                    "period": int(period),
                    "inTime": in_clock,
                    "outTime": out_clock,
                    "minutes": minutes,
                    "plusMinus": int(player_stint.get("PT_DIFF", 0)),
                    "stats": stint_stats,
                    "events": events,
                }
            ],
        }
        players.append(player_dict)

    return {
        "gameId": str(game_id),
        "homeTeam": {
            "tricode": home_line["TEAM_ABBREVIATION"],
            "name": home_line["TEAM_NAME"],
        },
        "awayTeam": {
            "tricode": away_line["TEAM_ABBREVIATION"],
            "name": away_line["TEAM_NAME"],
        },
        "players": players,
    }
