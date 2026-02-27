"""Transform module mapping NBA API data to JSON contracts."""

from typing import Optional

import pandas as pd


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
    pbp_df: pd.DataFrame, player_id: int, period: int, in_clock: str, out_clock: str
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
    # Filter by period and player
    filtered = pbp_df[
        (pbp_df["PERIOD"] == period)
        & (pbp_df["PLAYER1_ID"] == player_id)
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


def _pbp_event_to_type(event_msg_type: int, event_msg_action_type: int) -> str:
    """
    Map EVENTMSGTYPE codes to human-readable event types.

    Args:
        event_msg_type: Event message type code
        event_msg_action_type: Event message action type code

    Returns:
        Human-readable event type string
    """
    # Event type codes (simplified for phase 2)
    if event_msg_type == 1:  # Make
        if event_msg_action_type == 1:
            return "make2"
        elif event_msg_action_type in [2, 3]:
            return "make3"
        else:
            return "make"
    elif event_msg_type == 2:  # Miss
        if event_msg_action_type == 1:
            return "miss2"
        elif event_msg_action_type in [2, 3]:
            return "miss3"
        else:
            return "miss"
    elif event_msg_type == 3:  # Free throw
        return "fta"
    elif event_msg_type == 4:  # Rebound
        return "reb"
    elif event_msg_type == 5:  # Turnover
        return "tov"
    elif event_msg_type == 6:  # Foul
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
    line_score = scoreboard_data["line_score"]
    player_stats = boxscore_data["player_stats"]
    team_stats = boxscore_data["team_stats"]

    # Validate required data is not empty
    if len(scoreboard_data["game_header"]) == 0:
        raise ValueError(f"Game header is empty for game {game_id}")
    if len(line_score) == 0:
        raise ValueError(f"Line score is empty for game {game_id}")

    # Get home/away team info
    game_info = scoreboard_data["game_header"][
        scoreboard_data["game_header"]["GAME_ID"] == game_id
    ]
    if len(game_info) == 0:
        raise ValueError(f"Game info not found for game {game_id}")
    game_info = game_info.iloc[0]
    home_team_id = game_info["HOME_TEAM_ID"]

    home_line = line_score[
        (line_score["GAME_ID"] == game_id) & (line_score["TEAM_ID"] == home_team_id)
    ]
    away_line = line_score[
        (line_score["GAME_ID"] == game_id) & (line_score["TEAM_ID"] != home_team_id)
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
        if pd.isna(player["MIN"]) or player["MIN"] == 0:
            continue

        minutes = float(player["MIN"]) if not pd.isna(player["MIN"]) else 0

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

        player_rotation = team_rotation[team_rotation["PERSON_ID"] == player_id]
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
    home_team_match = team_stats[team_stats["TEAM_ABBREVIATION"] == home_line["TEAM_ABBREVIATION"]]
    away_team_match = team_stats[team_stats["TEAM_ABBREVIATION"] == away_line["TEAM_ABBREVIATION"]]

    if len(home_team_match) == 0 or len(away_team_match) == 0:
        # Handle case where team stats don't match
        # Use the first two rows as home and away fallback
        home_team_stats = team_stats.iloc[0]
        away_team_stats = team_stats.iloc[1] if len(team_stats) > 1 else team_stats.iloc[0]
    else:
        home_team_stats = home_team_match.iloc[0]
        away_team_stats = away_team_match.iloc[0]

    team_totals = {
        "home": {
            "fgm": int(home_team_stats["FGM"]),
            "fga": int(home_team_stats["FGA"]),
            "fg3m": int(home_team_stats["FG3M"]),
            "fg3a": int(home_team_stats["FG3A"]),
            "ftm": int(home_team_stats["FTM"]),
            "fta": int(home_team_stats["FTA"]),
            "oreb": int(home_team_stats["OREB"]),
            "reb": int(home_team_stats["REB"]),
            "ast": int(home_team_stats["AST"]),
            "blk": int(home_team_stats["BLK"]),
            "stl": int(home_team_stats["STL"]),
            "tov": int(home_team_stats["TO"]),
            "pf": int(home_team_stats["PF"]),
            "pts": int(home_team_stats["PTS"]),
        },
        "away": {
            "fgm": int(away_team_stats["FGM"]),
            "fga": int(away_team_stats["FGA"]),
            "fg3m": int(away_team_stats["FG3M"]),
            "fg3a": int(away_team_stats["FG3A"]),
            "ftm": int(away_team_stats["FTM"]),
            "fta": int(away_team_stats["FTA"]),
            "oreb": int(away_team_stats["OREB"]),
            "reb": int(away_team_stats["REB"]),
            "ast": int(away_team_stats["AST"]),
            "blk": int(away_team_stats["BLK"]),
            "stl": int(away_team_stats["STL"]),
            "tov": int(away_team_stats["TO"]),
            "pf": int(away_team_stats["PF"]),
            "pts": int(away_team_stats["PTS"]),
        },
    }

    # Build period totals using game-level team stats
    # Since BoxScoreTraditionalV2 doesn't provide per-period data,
    # we use a single "Game" entry with actual team totals (phase 2 limitation)
    period_totals = {
        "home": [
            {
                "period": "Game",
                "fgm": int(home_team_stats["FGM"]),
                "fga": int(home_team_stats["FGA"]),
                "fg3m": int(home_team_stats["FG3M"]),
                "fg3a": int(home_team_stats["FG3A"]),
                "ftm": int(home_team_stats["FTM"]),
                "fta": int(home_team_stats["FTA"]),
                "pts": int(home_team_stats["PTS"]),
            }
        ],
        "away": [
            {
                "period": "Game",
                "fgm": int(away_team_stats["FGM"]),
                "fga": int(away_team_stats["FGA"]),
                "fg3m": int(away_team_stats["FG3M"]),
                "fg3a": int(away_team_stats["FG3A"]),
                "ftm": int(away_team_stats["FTM"]),
                "fta": int(away_team_stats["FTA"]),
                "pts": int(away_team_stats["PTS"]),
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
    line_score = scoreboard_data["line_score"]
    game_info = scoreboard_data["game_header"][
        scoreboard_data["game_header"]["GAME_ID"] == game_id
    ].iloc[0]
    home_team_id = game_info["HOME_TEAM_ID"]

    home_line = line_score[
        (line_score["GAME_ID"] == game_id) & (line_score["TEAM_ID"] == home_team_id)
    ].iloc[0]
    away_line = line_score[
        (line_score["GAME_ID"] == game_id) & (line_score["TEAM_ID"] != home_team_id)
    ].iloc[0]

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
