"""Tests for the fetch module."""

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from pipeline.fetch import (
    _parse_pbp_response,
    fetch_boxscore,
    fetch_game_rotation,
    fetch_playbyplay,
    fetch_scoreboard,
)


class TestFetchScoreboard:
    """Tests for fetch_scoreboard function."""

    def test_fetch_scoreboard_success(self, sample_scoreboard_data):
        """Test successful scoreboard fetch."""
        with patch("pipeline.fetch.ScoreboardV2") as mock_sb:
            mock_instance = MagicMock()
            mock_instance.get_data_frames.return_value = [
                sample_scoreboard_data["game_header"],
                sample_scoreboard_data["line_score"],
            ]
            mock_sb.return_value = mock_instance

            result = fetch_scoreboard("2026-01-19", delay=0)

            assert result is not None
            assert "game_header" in result
            assert "line_score" in result
            assert len(result["game_header"]) == 2
            assert len(result["line_score"]) == 4

    def test_fetch_scoreboard_has_required_columns(self, sample_scoreboard_data):
        """Test that scoreboard data includes required columns."""
        with patch("pipeline.fetch.ScoreboardV2") as mock_sb:
            mock_instance = MagicMock()
            mock_instance.get_data_frames.return_value = [
                sample_scoreboard_data["game_header"],
                sample_scoreboard_data["line_score"],
            ]
            mock_sb.return_value = mock_instance

            result = fetch_scoreboard("2026-01-19", delay=0)

            # Check game_header columns
            assert "GAME_ID" in result["game_header"].columns
            assert "HOME_TEAM_ID" in result["game_header"].columns
            assert "VISITOR_TEAM_ID" in result["game_header"].columns

            # Check line_score columns
            assert "TEAM_ID" in result["line_score"].columns
            assert "TEAM_ABBREVIATION" in result["line_score"].columns
            assert "TEAM_NAME" in result["line_score"].columns
            assert "PTS" in result["line_score"].columns

    def test_fetch_scoreboard_failure(self):
        """Test scoreboard fetch on API error."""
        with patch("pipeline.fetch.ScoreboardV2") as mock_sb:
            mock_sb.side_effect = requests.exceptions.RequestException("API Error")

            result = fetch_scoreboard("2026-01-19", delay=0)

            assert result is None

    def test_fetch_scoreboard_unexpected_error(self):
        """Test scoreboard fetch on unexpected error (e.g. KeyError)."""
        with patch("pipeline.fetch.ScoreboardV2") as mock_sb:
            mock_sb.side_effect = KeyError("resultSet")

            result = fetch_scoreboard("2026-01-19", delay=0)

            assert result is None


class TestFetchBoxscore:
    """Tests for fetch_boxscore function."""

    def test_fetch_boxscore_success(self, sample_boxscore_data):
        """Test successful box score fetch."""
        with patch("pipeline.fetch.BoxScoreTraditionalV2") as mock_bs:
            mock_instance = MagicMock()
            mock_instance.get_data_frames.return_value = [
                sample_boxscore_data["player_stats"],
                sample_boxscore_data["team_stats"],
            ]
            mock_bs.return_value = mock_instance

            result = fetch_boxscore("0022500001", delay=0)

            assert result is not None
            assert "player_stats" in result
            assert "team_stats" in result
            assert len(result["player_stats"]) == 3
            assert len(result["team_stats"]) == 2

    def test_fetch_boxscore_has_required_columns(self, sample_boxscore_data):
        """Test that box score data includes required columns."""
        with patch("pipeline.fetch.BoxScoreTraditionalV2") as mock_bs:
            mock_instance = MagicMock()
            mock_instance.get_data_frames.return_value = [
                sample_boxscore_data["player_stats"],
                sample_boxscore_data["team_stats"],
            ]
            mock_bs.return_value = mock_instance

            result = fetch_boxscore("0022500001", delay=0)

            # Check player_stats columns
            player_cols = result["player_stats"].columns
            required = ["PLAYER_ID", "PLAYER_NAME", "MIN", "FGM", "FGA", "PTS", "PLUS_MINUS"]
            for col in required:
                assert col in player_cols

    def test_fetch_boxscore_failure(self):
        """Test box score fetch on API error."""
        with patch("pipeline.fetch.BoxScoreTraditionalV2") as mock_bs:
            mock_bs.side_effect = requests.exceptions.RequestException("API Error")

            result = fetch_boxscore("0022500001", delay=0)

            assert result is None

    def test_fetch_boxscore_unexpected_error(self):
        """Test box score fetch on unexpected error."""
        with patch("pipeline.fetch.BoxScoreTraditionalV2") as mock_bs:
            mock_bs.side_effect = KeyError("resultSet")

            result = fetch_boxscore("0022500001", delay=0)

            assert result is None


class TestParsePbpResponse:
    """Tests for _parse_pbp_response helper."""

    def test_parses_resultSets_format(self):
        """Test parsing response with 'resultSets' (plural) key."""
        raw = {
            "resultSets": [
                {
                    "headers": ["EVENTNUM", "PERIOD", "PCTIMESTRING"],
                    "rowSet": [[1, 1, "12:00"], [2, 1, "11:30"]],
                }
            ]
        }
        df = _parse_pbp_response(raw)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["EVENTNUM", "PERIOD", "PCTIMESTRING"]

    def test_parses_resultSet_format(self):
        """Test parsing response with 'resultSet' (singular) key."""
        raw = {
            "resultSet": {
                "headers": ["EVENTNUM", "PERIOD"],
                "rowSet": [[1, 1]],
            }
        }
        df = _parse_pbp_response(raw)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_raises_on_missing_key(self):
        """Test that missing both keys raises KeyError."""
        with pytest.raises(KeyError, match="neither"):
            _parse_pbp_response({"something_else": []})


class TestFetchPlaybyplay:
    """Tests for fetch_playbyplay function."""

    def test_fetch_playbyplay_success(self, sample_playbyplay_data):
        """Test successful play-by-play fetch."""
        # Build a raw JSON response matching what the NBA API would return
        raw_response = json.dumps({
            "resultSets": [
                {
                    "headers": list(sample_playbyplay_data.columns),
                    "rowSet": sample_playbyplay_data.values.tolist(),
                }
            ]
        })

        with patch("pipeline.fetch.NBAStatsHTTP") as mock_http_cls:
            mock_http = MagicMock()
            mock_http.send_api_request.return_value = raw_response
            mock_http_cls.return_value = mock_http

            result = fetch_playbyplay("0022500001", delay=0)

            assert result is not None
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 5

    def test_fetch_playbyplay_has_required_columns(self, sample_playbyplay_data):
        """Test that play-by-play data includes required columns."""
        raw_response = json.dumps({
            "resultSets": [
                {
                    "headers": list(sample_playbyplay_data.columns),
                    "rowSet": sample_playbyplay_data.values.tolist(),
                }
            ]
        })

        with patch("pipeline.fetch.NBAStatsHTTP") as mock_http_cls:
            mock_http = MagicMock()
            mock_http.send_api_request.return_value = raw_response
            mock_http_cls.return_value = mock_http

            result = fetch_playbyplay("0022500001", delay=0)

            required_cols = ["EVENTNUM", "EVENTMSGTYPE", "PERIOD", "PCTIMESTRING"]
            for col in required_cols:
                assert col in result.columns

    def test_fetch_playbyplay_failure(self):
        """Test play-by-play fetch on API error."""
        with patch("pipeline.fetch.NBAStatsHTTP") as mock_http_cls:
            mock_http = MagicMock()
            mock_http.send_api_request.side_effect = requests.exceptions.RequestException("API Error")
            mock_http_cls.return_value = mock_http

            result = fetch_playbyplay("0022500001", delay=0)

            assert result is None

    def test_fetch_playbyplay_unexpected_error(self):
        """Test play-by-play fetch on unexpected error."""
        with patch("pipeline.fetch.NBAStatsHTTP") as mock_http_cls:
            mock_http = MagicMock()
            mock_http.send_api_request.return_value = '{"bad_key": []}'
            mock_http_cls.return_value = mock_http

            result = fetch_playbyplay("0022500001", delay=0)

            assert result is None


class TestFetchGameRotation:
    """Tests for fetch_game_rotation function."""

    def test_fetch_game_rotation_success(self, sample_rotation_data):
        """Test successful game rotation fetch."""
        with patch("pipeline.fetch.GameRotation") as mock_gr:
            mock_instance = MagicMock()
            mock_instance.get_data_frames.return_value = [
                sample_rotation_data["away_team"],
                sample_rotation_data["home_team"],
            ]
            mock_gr.return_value = mock_instance

            result = fetch_game_rotation("0022500001", delay=0)

            assert result is not None
            assert "away_team" in result
            assert "home_team" in result
            assert len(result["away_team"]) == 2
            assert len(result["home_team"]) == 2

    def test_fetch_game_rotation_has_required_columns(self, sample_rotation_data):
        """Test that rotation data includes required columns."""
        with patch("pipeline.fetch.GameRotation") as mock_gr:
            mock_instance = MagicMock()
            mock_instance.get_data_frames.return_value = [
                sample_rotation_data["away_team"],
                sample_rotation_data["home_team"],
            ]
            mock_gr.return_value = mock_instance

            result = fetch_game_rotation("0022500001", delay=0)

            required_cols = ["PERSON_ID", "PLAYER_FIRST", "PLAYER_LAST", "IN_TIME_REAL", "OUT_TIME_REAL"]
            for col in required_cols:
                assert col in result["home_team"].columns
                assert col in result["away_team"].columns

    def test_fetch_game_rotation_failure(self):
        """Test game rotation fetch on API error."""
        with patch("pipeline.fetch.GameRotation") as mock_gr:
            mock_gr.side_effect = requests.exceptions.RequestException("API Error")

            result = fetch_game_rotation("0022500001", delay=0)

            assert result is None

    def test_fetch_game_rotation_unexpected_error(self):
        """Test game rotation fetch on unexpected error."""
        with patch("pipeline.fetch.GameRotation") as mock_gr:
            mock_gr.side_effect = KeyError("resultSet")

            result = fetch_game_rotation("0022500001", delay=0)

            assert result is None
