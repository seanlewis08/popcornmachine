"""Tests for the transform module."""

import pandas as pd
import pytest

from pipeline.transform import (
    _aggregate_stint_stats,
    _compute_stint_minutes,
    _pbp_event_to_type,
    _rotation_time_to_period_clock,
    transform_boxscore,
    transform_gameflow,
    transform_scores,
)


class TestRotationTimeConversion:
    """Tests for time conversion utilities."""

    def test_rotation_time_to_period_clock_period_1(self):
        """Test conversion of period 1 time."""
        period, in_clock, out_clock = _rotation_time_to_period_clock(0, 606000)
        assert period == 1
        assert in_clock == "0:00"
        assert out_clock == "10:06"

    def test_rotation_time_to_period_clock_period_2(self):
        """Test conversion of period 2 time."""
        period, in_clock, out_clock = _rotation_time_to_period_clock(720000, 1200000)
        assert period == 2
        assert in_clock == "0:00"
        assert out_clock == "8:00"

    def test_compute_stint_minutes(self):
        """Test stint duration calculation."""
        minutes = _compute_stint_minutes(0, 606000)
        assert minutes == 10.1


class TestPBPEventType:
    """Tests for play-by-play event type mapping."""

    def test_pbp_event_make2(self):
        """Test 2-pointer made event."""
        event_type = _pbp_event_to_type(1, 1)
        assert event_type == "make2"

    def test_pbp_event_make3(self):
        """Test 3-pointer made event."""
        event_type = _pbp_event_to_type(1, 2)
        assert event_type == "make3"

    def test_pbp_event_miss2(self):
        """Test 2-pointer missed event."""
        event_type = _pbp_event_to_type(2, 1)
        assert event_type == "miss2"

    def test_pbp_event_miss3(self):
        """Test 3-pointer missed event."""
        event_type = _pbp_event_to_type(2, 2)
        assert event_type == "miss3"

    def test_pbp_event_fta(self):
        """Test free throw event."""
        event_type = _pbp_event_to_type(3, 0)
        assert event_type == "fta"

    def test_pbp_event_rebound(self):
        """Test rebound event."""
        event_type = _pbp_event_to_type(4, 0)
        assert event_type == "reb"

    def test_pbp_event_turnover(self):
        """Test turnover event."""
        event_type = _pbp_event_to_type(5, 0)
        assert event_type == "tov"

    def test_pbp_event_foul(self):
        """Test foul event."""
        event_type = _pbp_event_to_type(6, 0)
        assert event_type == "foul"


class TestAggregateStintStats:
    """Tests for aggregating stint statistics."""

    def test_aggregate_empty_events(self):
        """Test aggregating empty event set."""
        empty_df = pd.DataFrame({
            "EVENTMSGTYPE": [],
            "EVENTMSGACTIONTYPE": [],
            "HOMEDESCRIPTION": [],
            "VISITORDESCRIPTION": [],
        })
        stats = _aggregate_stint_stats(empty_df)
        assert all(v == 0 for v in stats.values())

    def test_aggregate_makes_and_misses(self):
        """Test aggregating made and missed field goals."""
        pbp = pd.DataFrame({
            "EVENTMSGTYPE": [1, 1, 2, 2],
            "EVENTMSGACTIONTYPE": [1, 2, 1, 2],
            "HOMEDESCRIPTION": ["make", "make", "miss", "miss"],
            "VISITORDESCRIPTION": [None, None, None, None],
        })
        stats = _aggregate_stint_stats(pbp)
        assert stats["fgm"] == 2
        assert stats["fga"] == 4
        assert stats["fg3m"] == 1
        assert stats["fg3a"] == 2
        assert stats["pts"] == 5  # 1x2 + 1x3


class TestTransformScores:
    """Tests for transform_scores function."""

    def test_transform_scores_groups_games(self, sample_scoreboard_data):
        """Test that transform_scores produces list of games."""
        result = transform_scores(sample_scoreboard_data)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all("gameId" in game for game in result)

    def test_transform_scores_includes_team_names(self, sample_scoreboard_data):
        """Test that games include team names and tricodes."""
        result = transform_scores(sample_scoreboard_data)
        assert len(result) > 0
        game = result[0]
        assert "homeTeam" in game
        assert "awayTeam" in game
        assert "tricode" in game["homeTeam"]
        assert "name" in game["homeTeam"]
        assert "score" in game["homeTeam"]

    def test_transform_scores_includes_final_score(self, sample_scoreboard_data):
        """Test that games include final scores."""
        result = transform_scores(sample_scoreboard_data)
        assert len(result) > 0
        game = result[0]
        assert isinstance(game["homeTeam"]["score"], int)
        assert isinstance(game["awayTeam"]["score"], int)
        assert game["homeTeam"]["score"] == 104
        assert game["awayTeam"]["score"] == 103


class TestTransformBoxscore:
    """Tests for transform_boxscore function."""

    def test_transform_boxscore_structure(
        self, sample_scoreboard_data, sample_boxscore_data,
        sample_rotation_data, sample_playbyplay_data
    ):
        """Test that boxscore transformation produces correct structure."""
        result = transform_boxscore(
            "0022500001",
            "2026-01-19",
            sample_scoreboard_data,
            sample_boxscore_data,
            sample_rotation_data,
            sample_playbyplay_data,
        )

        assert "gameId" in result
        assert "date" in result
        assert "homeTeam" in result
        assert "awayTeam" in result
        assert "players" in result
        assert "teamTotals" in result
        assert "periodTotals" in result

    def test_transform_boxscore_team_totals(
        self, sample_scoreboard_data, sample_boxscore_data,
        sample_rotation_data, sample_playbyplay_data
    ):
        """Test that team totals are computed correctly."""
        result = transform_boxscore(
            "0022500001",
            "2026-01-19",
            sample_scoreboard_data,
            sample_boxscore_data,
            sample_rotation_data,
            sample_playbyplay_data,
        )

        team_totals = result["teamTotals"]
        assert "home" in team_totals
        assert "away" in team_totals
        assert team_totals["home"]["pts"] == 104
        assert team_totals["away"]["pts"] == 103

    def test_transform_boxscore_derived_metrics(
        self, sample_scoreboard_data, sample_boxscore_data,
        sample_rotation_data, sample_playbyplay_data
    ):
        """Test that derived metrics are calculated."""
        result = transform_boxscore(
            "0022500001",
            "2026-01-19",
            sample_scoreboard_data,
            sample_boxscore_data,
            sample_rotation_data,
            sample_playbyplay_data,
        )

        assert len(result["players"]) > 0
        player = result["players"][0]
        assert "totals" in player
        totals = player["totals"]
        assert "hv" in totals
        assert "prod" in totals
        assert "eff" in totals


class TestTransformGameflow:
    """Tests for transform_gameflow function."""

    def test_transform_gameflow_structure(
        self, sample_scoreboard_data, sample_rotation_data, sample_playbyplay_data
    ):
        """Test that gameflow transformation produces correct structure."""
        result = transform_gameflow(
            "0022500001",
            sample_scoreboard_data,
            sample_rotation_data,
            sample_playbyplay_data,
        )

        assert "gameId" in result
        assert "homeTeam" in result
        assert "awayTeam" in result
        assert "players" in result

    def test_transform_gameflow_includes_stints(
        self, sample_scoreboard_data, sample_rotation_data, sample_playbyplay_data
    ):
        """Test that players have stint information."""
        result = transform_gameflow(
            "0022500001",
            sample_scoreboard_data,
            sample_rotation_data,
            sample_playbyplay_data,
        )

        assert len(result["players"]) > 0
        player = result["players"][0]
        assert "stints" in player
        if len(player["stints"]) > 0:
            stint = player["stints"][0]
            assert "period" in stint
            assert "inTime" in stint
            assert "outTime" in stint
            assert "minutes" in stint
            assert "stats" in stint
            assert "events" in stint

    def test_transform_gameflow_stint_stats(
        self, sample_scoreboard_data, sample_rotation_data, sample_playbyplay_data
    ):
        """Test that stint stats are included."""
        result = transform_gameflow(
            "0022500001",
            sample_scoreboard_data,
            sample_rotation_data,
            sample_playbyplay_data,
        )

        assert len(result["players"]) > 0
        player = result["players"][0]
        if len(player["stints"]) > 0:
            stint = player["stints"][0]
            stats = stint["stats"]
            # Check required stat keys
            required_keys = ["fgm", "fga", "pts", "reb", "ast"]
            for key in required_keys:
                assert key in stats
