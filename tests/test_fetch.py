"""Tests for the fetch module."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from pipeline.fetch import (
    _map_v3_to_v2_columns,
    _parse_v3_clock,
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

            assert "GAME_ID" in result["game_header"].columns
            assert "HOME_TEAM_ID" in result["game_header"].columns
            assert "VISITOR_TEAM_ID" in result["game_header"].columns

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


class TestParseV3Clock:
    """Tests for _parse_v3_clock helper."""

    def test_standard_clock(self):
        assert _parse_v3_clock("PT04M30.00S") == "4:30"

    def test_zero_minutes(self):
        assert _parse_v3_clock("PT00M05.00S") == "0:05"

    def test_full_quarter(self):
        assert _parse_v3_clock("PT12M00.00S") == "12:00"

    def test_seconds_only(self):
        assert _parse_v3_clock("PT45.00S") == "0:45"

    def test_non_string_passthrough(self):
        assert _parse_v3_clock(None) == "None"

    def test_already_v2_format(self):
        assert _parse_v3_clock("4:30") == "4:30"


class TestMapV3ToV2Columns:
    """Tests for _map_v3_to_v2_columns helper."""

    def test_renames_columns(self):
        df = pd.DataFrame({
            "period": [1],
            "personId": [12345],
            "clock": ["PT04M30.00S"],
            "actionType": ["2pt"],
            "subType": ["driving"],
            "actionNumber": [1],
            "description": ["Layup Made"],
        })
        result = _map_v3_to_v2_columns(df)

        assert "PERIOD" in result.columns
        assert "PLAYER1_ID" in result.columns
        assert "PCTIMESTRING" in result.columns
        assert "EVENTMSGTYPE" in result.columns
        assert "EVENTMSGACTIONTYPE" in result.columns
        assert "EVENTNUM" in result.columns
        assert "HOMEDESCRIPTION" in result.columns
        assert "VISITORDESCRIPTION" in result.columns

    def test_converts_clock_format(self):
        df = pd.DataFrame({
            "period": [1],
            "personId": [12345],
            "clock": ["PT04M30.00S"],
            "actionType": ["2pt"],
            "subType": ["driving"],
            "actionNumber": [1],
            "description": ["Layup Made"],
        })
        result = _map_v3_to_v2_columns(df)
        assert result["PCTIMESTRING"].iloc[0] == "4:30"

    def test_visitor_description_synthesized(self):
        df = pd.DataFrame({
            "period": [1],
            "personId": [12345],
            "clock": ["PT04M30.00S"],
            "actionType": ["2pt"],
            "subType": ["driving"],
            "actionNumber": [1],
            "description": ["Layup Made"],
        })
        result = _map_v3_to_v2_columns(df)
        assert result["VISITORDESCRIPTION"].iloc[0] == "Layup Made"


class TestFetchPlaybyplay:
    """Tests for fetch_playbyplay function."""

    def _make_v3_mock(self, sample_playbyplay_data):
        """Create a mock PlayByPlayV3 that returns V3-format data."""
        # Convert V2 sample data column names to V3 format for the mock
        v3_df = sample_playbyplay_data.rename(columns={
            "PERIOD": "period",
            "PLAYER1_ID": "personId",
            "PCTIMESTRING": "clock",
            "EVENTMSGTYPE": "actionType",
            "EVENTMSGACTIONTYPE": "subType",
            "EVENTNUM": "actionNumber",
        })
        # Add description column (V3 merges home/away)
        if "HOMEDESCRIPTION" in sample_playbyplay_data.columns:
            v3_df["description"] = sample_playbyplay_data["HOMEDESCRIPTION"]
        else:
            v3_df["description"] = ""

        # Convert clock to V3 format (V2 "4:30" -> V3 "PT04M30.00S")
        def to_v3_clock(v2_clock):
            if ":" in str(v2_clock):
                parts = str(v2_clock).split(":")
                return f"PT{int(parts[0]):02d}M{int(parts[1]):02d}.00S"
            return v2_clock
        v3_df["clock"] = v3_df["clock"].apply(to_v3_clock)

        mock_instance = MagicMock()
        mock_instance.play_by_play.get_data_frame.return_value = v3_df
        return mock_instance

    def test_fetch_playbyplay_success(self, sample_playbyplay_data):
        """Test successful play-by-play fetch via V3."""
        with patch("pipeline.fetch.PlayByPlayV3") as mock_pbp_cls:
            mock_pbp_cls.return_value = self._make_v3_mock(sample_playbyplay_data)

            result = fetch_playbyplay("0022500001", delay=0)

            assert result is not None
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 5

    def test_fetch_playbyplay_returns_v2_columns(self, sample_playbyplay_data):
        """Test that V3 data is mapped to V2 column names."""
        with patch("pipeline.fetch.PlayByPlayV3") as mock_pbp_cls:
            mock_pbp_cls.return_value = self._make_v3_mock(sample_playbyplay_data)

            result = fetch_playbyplay("0022500001", delay=0)

            # These V2 columns should exist after mapping
            required_cols = ["EVENTNUM", "EVENTMSGTYPE", "PERIOD", "PCTIMESTRING"]
            for col in required_cols:
                assert col in result.columns

    def test_fetch_playbyplay_failure(self):
        """Test play-by-play fetch on API error."""
        with patch("pipeline.fetch.PlayByPlayV3") as mock_pbp_cls:
            mock_pbp_cls.side_effect = requests.exceptions.RequestException("API Error")

            result = fetch_playbyplay("0022500001", delay=0)

            assert result is None

    def test_fetch_playbyplay_unexpected_error(self):
        """Test play-by-play fetch on unexpected error."""
        with patch("pipeline.fetch.PlayByPlayV3") as mock_pbp_cls:
            mock_pbp_cls.side_effect = RuntimeError("Something broke")

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
