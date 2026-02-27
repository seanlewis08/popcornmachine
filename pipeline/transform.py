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


def _period_boundary_decisecs(period: int) -> int:
    """Return the ending decisecond timestamp for a given period.

    Regulation periods (1-4) are each 7200 deciseconds (720 seconds).
    OT periods (5+) are each 3000 deciseconds (300 seconds).
    """
    if period <= 4:
        return period * 7200
    else:
        return 4 * 7200 + (period - 4) * 3000


def _period_duration_secs(period: int) -> int:
    """Return the duration of a period in seconds (720 for regulation, 300 for OT)."""
    return 300 if period > 4 else 720


def _decisecs_to_period(decisecs: int) -> int:
    """Determine which period a decisecond timestamp falls in."""
    if decisecs < 4 * 7200:
        return decisecs // 7200 + 1
    else:
        return 5 + (decisecs - 4 * 7200) // 3000


def _split_rotation_stint(
    in_time_real: int, out_time_real: int
) -> list[tuple[int, str, str, int, int]]:
    """
    Split a rotation stint that may cross period boundaries into per-period segments.

    The NBA GameRotation API returns IN_TIME_REAL/OUT_TIME_REAL in deciseconds.
    When a player stays on court across a period boundary (e.g., Q2 into Q3),
    the API returns a single row spanning both periods. This function splits
    such stints at period boundaries.

    Args:
        in_time_real: In-time in deciseconds (elapsed from game start)
        out_time_real: Out-time in deciseconds (elapsed from game start)

    Returns:
        List of (period, in_clock, out_clock, segment_in_real, segment_out_real)
        tuples — one per period the stint covers. The last two values are the
        raw decisecond boundaries for the segment (used for PBP filtering and
        minutes calculation).
    """
    in_time_real = int(in_time_real)
    out_time_real = int(out_time_real)

    segments: list[tuple[int, str, str, int, int]] = []

    current = in_time_real
    while current < out_time_real:
        period = _decisecs_to_period(current)
        period_end = _period_boundary_decisecs(period)
        period_start_decisecs = period_end - _period_duration_secs(period) * 10
        period_dur_secs = _period_duration_secs(period)

        # This segment ends at the earlier of: the stint end, or the period end
        segment_end = min(out_time_real, period_end)

        # Convert to countdown clocks within this period
        in_elapsed_secs = (current - period_start_decisecs) // 10
        out_elapsed_secs = (segment_end - period_start_decisecs) // 10

        in_remaining = max(0, period_dur_secs - in_elapsed_secs)
        out_remaining = max(0, period_dur_secs - out_elapsed_secs)

        in_clock = _seconds_to_clock(in_remaining)
        out_clock = _seconds_to_clock(out_remaining)

        segments.append((period, in_clock, out_clock, current, segment_end))
        current = segment_end

    return segments


def _rotation_time_to_period_clock(
    in_time_real: int, out_time_real: int
) -> tuple[int, str, str]:
    """
    Convert rotation timestamps to (period, in_clock, out_clock) format.

    NOTE: This function does NOT split period-crossing stints. Use
    _split_rotation_stint() for correct multi-period handling. This
    function is kept for backward compatibility with tests.

    The NBA GameRotation API returns IN_TIME_REAL/OUT_TIME_REAL in
    deciseconds (tenths of a second) elapsed from game start.

    Uses countdown clock format (12:00 = start of quarter, 0:00 = end).
    Each regulation period is 720 seconds (12 minutes).
    Period 1 starts at t=0, Period 2 at t=7200 deciseconds, etc.

    Args:
        in_time_real: In-time in deciseconds (elapsed from game start)
        out_time_real: Out-time in deciseconds (elapsed from game start)

    Returns:
        Tuple of (period, in_clock_str, out_clock_str) in countdown format
    """
    segments = _split_rotation_stint(in_time_real, out_time_real)
    if segments:
        # Return just the first segment for backward compat
        return segments[0][0], segments[0][1], segments[0][2]
    # Fallback (should never happen)
    return 1, "12:00", "12:00"


def _seconds_to_clock(seconds) -> str:
    """Convert seconds to MM:SS clock format."""
    seconds = int(seconds)
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def _compute_stint_minutes(in_time_real, out_time_real) -> float:
    """Compute stint duration in minutes from decisecond timestamps."""
    duration_decisecs = int(out_time_real) - int(in_time_real)
    return round(duration_decisecs / 600, 1)  # 600 deciseconds per minute


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

    # Clock counts down: inTime >= event clock >= outTime
    # e.g., player enters at 10:30 (630s), exits at 6:15 (375s)
    # Events happen between 630s and 375s on the countdown clock
    filtered = filtered[
        (filtered["PCTIMESTRING"].apply(clock_to_seconds) <= in_sec)
        & (filtered["PCTIMESTRING"].apply(clock_to_seconds) >= out_sec)
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
        emt_lower = event_msg_type.lower().strip()
        if emt_lower == "2pt":
            # V3: use shotResult if available (passed as extra_info),
            # otherwise check description for MISS prefix
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
        elif emt_lower in ("foul", "personalfoul", "shootingfoul",
                           "offensivefoul", "technicalfoul", "flagrantfoul",
                           "looseball foul", "personal foul"):
            return "foul"
        elif emt_lower == "steal":
            return "stl"
        elif emt_lower == "block":
            return "blk"
        elif emt_lower == "assist":
            return "ast"
        elif emt_lower in ("substitution", "timeout", "period",
                           "game", "jumpball", "violation", "ejection",
                           "instantreplay", "stoppage"):
            return "other"
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
    Count stat categories from PBP events.

    Uses V3-specific columns (isFieldGoal, shotResult, shotValue) when
    available for reliable field goal detection, with fallback to
    actionType/description parsing for non-shot events (rebounds, etc.).

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

    has_v3_fields = "isFieldGoal" in pbp_events.columns

    for _, event in pbp_events.iterrows():
        # --- V3 path: use isFieldGoal + shotResult + shotValue ---
        if has_v3_fields:
            is_fg = event.get("isFieldGoal", False)
            if is_fg is True or is_fg == 1:
                shot_result = str(event.get("shotResult", "")).strip()
                shot_value = event.get("shotValue", 0)
                try:
                    shot_value = int(shot_value) if not pd.isna(shot_value) else 0
                except (ValueError, TypeError):
                    shot_value = 0

                is_three = shot_value == 3
                is_made = shot_result.lower() == "made"

                stats["fga"] += 1
                if is_three:
                    stats["fg3a"] += 1

                if is_made:
                    stats["fgm"] += 1
                    stats["pts"] += shot_value if shot_value else 2
                    if is_three:
                        stats["fg3m"] += 1
                continue

            # Free throws: check actionType or EVENTMSGTYPE
            action_type = str(event.get("EVENTMSGTYPE", "")).lower()
            if action_type in ("freethrow", "free throw", "ft") or \
               (action_type == "3" and not has_v3_fields):
                stats["fta"] += 1
                shot_result = str(event.get("shotResult", "")).strip().lower()
                desc = str(event.get("HOMEDESCRIPTION", "") or "")
                if shot_result == "made" or "(1 PTS)" in desc or \
                   "PTS)" in desc or "MADE" in desc.upper():
                    stats["ftm"] += 1
                    stats["pts"] += 1
                continue

        else:
            # --- V2 fallback path ---
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
                if "MADE" in str(event.get("HOMEDESCRIPTION", "")) or \
                   "MADE" in str(event.get("VISITORDESCRIPTION", "")):
                    stats["ftm"] += 1
                    stats["pts"] += 1
                continue
            elif event_type in ("make", "miss"):
                # Generic make/miss without 2/3 distinction
                stats["fga"] += 1
                if event_type == "make":
                    stats["fgm"] += 1
                    stats["pts"] += 2
                continue
            else:
                pass  # Fall through to non-shot event handling below

            if event_type not in ("reb", "tov", "foul", "stl", "blk", "ast"):
                continue

        # --- Non-shot events (common to both V3 and V2 paths) ---
        action_type = str(event.get("EVENTMSGTYPE", "")).lower()
        if action_type == "rebound" or (not has_v3_fields and _pbp_event_to_type(
                event.get("EVENTMSGTYPE", 0), event.get("EVENTMSGACTIONTYPE", 0)) == "reb"):
            stats["reb"] += 1
            # Check for offensive rebound
            desc = str(event.get("HOMEDESCRIPTION", "") or
                       event.get("VISITORDESCRIPTION", "") or "")
            if "Off:" in desc:
                # Parse "Off:1" from description
                try:
                    off_part = desc.split("Off:")[1].split(")")[0].split(" ")[0]
                    if int(off_part) > 0:
                        stats["oreb"] += 1
                except (IndexError, ValueError):
                    pass
        elif action_type == "turnover":
            stats["tov"] += 1
        elif action_type == "foul":
            stats["pf"] += 1
        elif action_type == "steal":
            stats["stl"] += 1
        elif action_type == "block":
            stats["blk"] += 1
        elif action_type == "assist":
            stats["ast"] += 1
        elif not has_v3_fields:
            # V2 fallback for non-shot events
            event_type = _pbp_event_to_type(
                event.get("EVENTMSGTYPE", 0), event.get("EVENTMSGACTIONTYPE", 0)
            )
            if event_type == "reb":
                stats["reb"] += 1
            elif event_type == "tov":
                stats["tov"] += 1
            elif event_type == "foul":
                stats["pf"] += 1

    return stats


def _build_score_changes(pbp_data: pd.DataFrame) -> list[dict]:
    """
    Extract score changes from PBP data for the momentum line.

    Returns a list of {ts, homeScore, awayScore} dicts where ts is
    elapsed game minutes (0 = start of Q1, 12 = start of Q2, etc.).

    Args:
        pbp_data: Play-by-play DataFrame with SCORE_HOME, SCORE_AWAY,
                  PERIOD, PCTIMESTRING columns

    Returns:
        List of score change points in chronological order
    """
    changes = [{"ts": 0.0, "homeScore": 0, "awayScore": 0}]

    if pbp_data.empty:
        return changes

    # Check for V3 score columns
    has_score_cols = "SCORE_HOME" in pbp_data.columns and "SCORE_AWAY" in pbp_data.columns

    if not has_score_cols:
        # V2 fallback: try parsing SCORE column "away-home" format
        if "SCORE" in pbp_data.columns:
            prev_home, prev_away = 0, 0
            for _, row in pbp_data.iterrows():
                score_str = str(row.get("SCORE", ""))
                if "-" not in score_str or pd.isna(row.get("SCORE")):
                    continue
                try:
                    parts = score_str.split("-")
                    away_score = int(parts[0].strip())
                    home_score = int(parts[1].strip())
                except (ValueError, IndexError):
                    continue
                if home_score != prev_home or away_score != prev_away:
                    period = int(row.get("PERIOD", 1))
                    clock_str = str(row.get("PCTIMESTRING", "12:00"))
                    ts = _clock_to_elapsed_minutes(period, clock_str)
                    changes.append({
                        "ts": round(ts, 2),
                        "homeScore": home_score,
                        "awayScore": away_score,
                    })
                    prev_home, prev_away = home_score, away_score
        return changes

    # V3 path: use SCORE_HOME and SCORE_AWAY columns
    prev_home, prev_away = 0, 0
    for _, row in pbp_data.iterrows():
        try:
            home_score = int(row["SCORE_HOME"]) if not pd.isna(row.get("SCORE_HOME")) else prev_home
            away_score = int(row["SCORE_AWAY"]) if not pd.isna(row.get("SCORE_AWAY")) else prev_away
        except (ValueError, TypeError):
            continue

        if home_score != prev_home or away_score != prev_away:
            period = int(row.get("PERIOD", 1))
            clock_str = str(row.get("PCTIMESTRING", "12:00"))
            ts = _clock_to_elapsed_minutes(period, clock_str)
            changes.append({
                "ts": round(ts, 2),
                "homeScore": home_score,
                "awayScore": away_score,
            })
            prev_home, prev_away = home_score, away_score

    return changes


def _clock_to_elapsed_minutes(period: int, clock_str: str) -> float:
    """Convert period + countdown clock to elapsed game minutes."""
    try:
        parts = clock_str.split(":")
        remaining_secs = int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        remaining_secs = 0

    period_duration = 720 if period <= 4 else 300
    elapsed_in_period = period_duration - remaining_secs

    # Add elapsed minutes from completed periods
    if period <= 4:
        base_minutes = (period - 1) * 12
    else:
        base_minutes = 48 + (period - 5) * 5

    return base_minutes + (elapsed_in_period / 60)


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
            # Split stints that cross period boundaries into per-period segments
            segments = _split_rotation_stint(
                stint["IN_TIME_REAL"], stint["OUT_TIME_REAL"]
            )
            raw_pt_diff = _safe_int(stint.get("PT_DIFF", 0))

            for period, in_clock, out_clock, seg_in, seg_out in segments:
                minutes_stint = _compute_stint_minutes(seg_in, seg_out)

                # Filter PBP events for this segment
                pbp_stint = _filter_pbp_for_stint(
                    pbp_data, player_id, period, in_clock, out_clock
                )
                stint_stats = _aggregate_stint_stats(pbp_stint)

                stint_dict = {
                    "period": int(period),
                    "inTime": in_clock,
                    "outTime": out_clock,
                    "minutes": minutes_stint,
                    "plusMinus": raw_pt_diff if len(segments) == 1 else 0,
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

    # Group stints by player using dict keyed by player_id
    player_map: dict[str, dict] = {}

    def _process_rotation(rotation_df: pd.DataFrame, team_tricode: str) -> None:
        """Process rotation data for one team, grouping stints by player.

        Splits stints that cross period boundaries into per-period segments
        so every period where a player is on court gets its own stint entry.
        """
        for _, player_stint in rotation_df.iterrows():
            player_id = str(int(player_stint["PERSON_ID"]))
            raw_pt_diff = _safe_int(player_stint.get("PT_DIFF", 0))

            # Split period-crossing stints
            segments = _split_rotation_stint(
                player_stint["IN_TIME_REAL"], player_stint["OUT_TIME_REAL"]
            )

            for period, in_clock, out_clock, seg_in, seg_out in segments:
                minutes = _compute_stint_minutes(seg_in, seg_out)

                # Filter PBP for this player and segment
                pbp_stint = _filter_pbp_for_stint(
                    pbp_data, player_stint["PERSON_ID"], period, in_clock, out_clock
                )

                # Convert PBP events to simple format
                events = []
                for _, event in pbp_stint.iterrows():
                    # Determine event type using V3 fields when available
                    evt_type = _pbp_event_to_type(
                        event.get("EVENTMSGTYPE", 0),
                        event.get("EVENTMSGACTIONTYPE", 0),
                    )
                    # V3: override make/miss detection using isFieldGoal + shotResult
                    if "isFieldGoal" in pbp_stint.columns:
                        is_fg = event.get("isFieldGoal", False)
                        if is_fg is True or is_fg == 1:
                            shot_result = str(event.get("shotResult", "")).lower()
                            shot_value = event.get("shotValue", 0)
                            try:
                                shot_value = int(shot_value) if not pd.isna(shot_value) else 2
                            except (ValueError, TypeError):
                                shot_value = 2
                            if shot_result == "made":
                                evt_type = "Make3" if shot_value == 3 else "Make2"
                            else:
                                evt_type = "miss3" if shot_value == 3 else "miss2"
                        else:
                            action = str(event.get("EVENTMSGTYPE", "")).lower()
                            if action in ("freethrow", "free throw", "ft"):
                                shot_result = str(event.get("shotResult", "")).lower()
                                evt_type = "MakeFT" if shot_result == "made" else "missFT"
                            elif action == "rebound":
                                desc = str(event.get("HOMEDESCRIPTION", "") or "")
                                evt_type = "OffReb" if "Off:" in desc else "DefReb"
                            elif action == "steal":
                                evt_type = "Steal"
                            elif action == "block":
                                evt_type = "Block"
                            elif action == "assist":
                                evt_type = "Assist"
                            elif action == "turnover":
                                evt_type = "TO"
                            elif action in ("foul",):
                                evt_type = "PF"

                    event_dict = {
                        "clock": event.get("PCTIMESTRING", ""),
                        "type": evt_type,
                        "description": event.get("HOMEDESCRIPTION", "")
                        or event.get("VISITORDESCRIPTION", ""),
                    }
                    events.append(event_dict)

                # Aggregate stint stats
                stint_stats = _aggregate_stint_stats(pbp_stint)

                stint_dict = {
                    "period": int(period),
                    "inTime": in_clock,
                    "outTime": out_clock,
                    "minutes": minutes,
                    "plusMinus": raw_pt_diff if len(segments) == 1 else 0,
                    "stats": stint_stats,
                    "events": events,
                }

                # Group under existing player entry or create new one
                if player_id in player_map:
                    player_map[player_id]["stints"].append(stint_dict)
                else:
                    player_map[player_id] = {
                        "playerId": player_id,
                        "name": f"{player_stint.get('PLAYER_FIRST', '')} {player_stint.get('PLAYER_LAST', '')}",
                        "team": team_tricode,
                        "stints": [stint_dict],
                }

    _process_rotation(rotation_data["home_team"], home_line["TEAM_ABBREVIATION"])
    _process_rotation(rotation_data["away_team"], away_line["TEAM_ABBREVIATION"])

    players = list(player_map.values())

    # Build score changes for momentum line
    score_changes = _build_score_changes(pbp_data)

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
        "scoreChanges": score_changes,
    }
