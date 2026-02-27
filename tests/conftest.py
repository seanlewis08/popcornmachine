"""Shared test fixtures for mocked NBA API responses."""

import pandas as pd
import pytest


@pytest.fixture
def sample_scoreboard_data() -> dict:
    """Sample ScoreBoardV2 response with game_header and line_score DataFrames."""
    game_header = pd.DataFrame({
        "GAME_ID": ["0022500001", "0022500002"],
        "HOME_TEAM_ID": [1610612765, 1610612738],
        "VISITOR_TEAM_ID": [1610612751, 1610612757],
        "GAME_STATUS_TEXT": ["Final", "Final"],
    })

    line_score = pd.DataFrame({
        "GAME_ID": ["0022500001", "0022500001", "0022500002", "0022500002"],
        "TEAM_ID": [1610612765, 1610612751, 1610612738, 1610612757],
        "TEAM_ABBREVIATION": ["DET", "BOS", "LAL", "GSW"],
        "TEAM_NAME": ["Detroit Pistons", "Boston Celtics", "Los Angeles Lakers", "Golden State Warriors"],
        "PTS": [104, 103, 110, 108],
    })

    return {"game_header": game_header, "line_score": line_score}


@pytest.fixture
def sample_boxscore_data() -> dict:
    """Sample BoxScoreTraditionalV2 response with player_stats and team_stats DataFrames."""
    player_stats = pd.DataFrame({
        "GAME_ID": ["0022500001", "0022500001", "0022500001"],
        "PLAYER_ID": [203507, 203999, 2544],
        "PLAYER_NAME": ["C Cunningham", "D Murray", "K Leonard"],
        "TEAM_ABBREVIATION": ["DET", "DET", "BOS"],
        "MIN": [40.3, 35.0, 38.5],
        "FGM": [4, 8, 10],
        "FGA": [17, 20, 22],
        "FG3M": [0, 2, 3],
        "FG3A": [4, 6, 9],
        "FTM": [8, 4, 5],
        "FTA": [10, 5, 6],
        "OREB": [1, 2, 0],
        "DREB": [2, 3, 5],
        "REB": [3, 5, 5],
        "AST": [14, 7, 4],
        "STL": [1, 2, 1],
        "BLK": [2, 0, 2],
        "TO": [0, 3, 2],
        "PF": [3, 2, 4],
        "PTS": [16, 22, 28],
        "PLUS_MINUS": [2, 5, -3],
    })

    team_stats = pd.DataFrame({
        "GAME_ID": ["0022500001", "0022500001"],
        "TEAM_ABBREVIATION": ["DET", "BOS"],
        "FGM": [38, 33],
        "FGA": [88, 83],
        "FG3M": [11, 13],
        "FG3A": [33, 41],
        "FTM": [17, 24],
        "FTA": [23, 30],
        "OREB": [9, 16],
        "DREB": [31, 31],
        "REB": [40, 47],
        "AST": [24, 13],
        "BLK": [9, 4],
        "STL": [9, 5],
        "TO": [5, 11],
        "PF": [26, 26],
        "PTS": [104, 103],
    })

    return {"player_stats": player_stats, "team_stats": team_stats}


@pytest.fixture
def sample_playbyplay_data() -> pd.DataFrame:
    """Sample PlayByPlayV2 response DataFrame."""
    return pd.DataFrame({
        "EVENTNUM": [1, 2, 3, 4, 5],
        "EVENTMSGTYPE": [1, 2, 3, 4, 5],
        "EVENTMSGACTIONTYPE": [1, 1, 10, 0, 1],
        "PERIOD": [1, 1, 1, 1, 1],
        "PCTIMESTRING": ["12:00", "11:30", "11:00", "10:30", "10:00"],
        "HOMEDESCRIPTION": ["C. Cunningham 2PT", None, None, None, "C. Cunningham TURNOVER"],
        "VISITORDESCRIPTION": [None, "K. Leonard 2PT", "K. Leonard FT", None, None],
        "PLAYER1_ID": [203507, 2544, 2544, 2544, 203507],
        "PLAYER1_TEAM_ABBREVIATION": ["DET", "BOS", "BOS", "BOS", "DET"],
        "SCORE": ["2-0", "2-2", "2-3", "2-3", "2-3"],
    })


@pytest.fixture
def sample_rotation_data() -> dict:
    """Sample GameRotation response with away_team and home_team DataFrames."""
    # Rotation API uses deciseconds (1/10 second)
    # 6060 decisecs = 606 seconds = ~10.1 min
    # 7200 decisecs = 720 seconds = end of Q1 / start of Q2
    home_team = pd.DataFrame({
        "GAME_ID": ["0022500001", "0022500001"],
        "PERSON_ID": [203507, 203999],
        "PLAYER_FIRST": ["Cade", "Danilo"],
        "PLAYER_LAST": ["Cunningham", "Gallinari"],
        "IN_TIME_REAL": [0, 0],
        "OUT_TIME_REAL": [6060, 12000],  # 6060 decisecs = ~10.1 min, 12000 = 20 min
        "PLAYER_PTS": [16, 22],
        "PT_DIFF": [2, 5],
    })

    away_team = pd.DataFrame({
        "GAME_ID": ["0022500001", "0022500001"],
        "PERSON_ID": [2544, 201939],
        "PLAYER_FIRST": ["Kawhi", "Jaylen"],
        "PLAYER_LAST": ["Leonard", "Brown"],
        "IN_TIME_REAL": [0, 6000],
        "OUT_TIME_REAL": [12000, 18000],
        "PLAYER_PTS": [28, 15],
        "PT_DIFF": [-3, 2],
    })

    return {"away_team": away_team, "home_team": home_team}
