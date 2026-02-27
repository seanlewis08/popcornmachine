"""Tests for the main pipeline orchestrator."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.main import main


@patch("pipeline.main.fetch_game_rotation")
@patch("pipeline.main.fetch_playbyplay")
@patch("pipeline.main.fetch_boxscore")
@patch("pipeline.main.fetch_scoreboard")
def test_main_orchestrator_flow(
    mock_fetch_sb, mock_fetch_bs, mock_fetch_pbp, mock_fetch_rot,
    sample_scoreboard_data, sample_boxscore_data, sample_playbyplay_data,
    sample_rotation_data
):
    """Test that main orchestrator calls functions in correct order."""
    # Create scoreboard with only one game for this test
    import pandas as pd
    single_game_scoreboard = {
        "game_header": sample_scoreboard_data["game_header"].iloc[[0]].reset_index(drop=True),
        "line_score": sample_scoreboard_data["line_score"].iloc[[0, 1]].reset_index(drop=True),
    }

    # Setup mocks
    mock_fetch_sb.return_value = single_game_scoreboard
    mock_fetch_bs.return_value = sample_boxscore_data
    mock_fetch_pbp.return_value = sample_playbyplay_data
    mock_fetch_rot.return_value = sample_rotation_data

    with tempfile.TemporaryDirectory() as tmpdir:
        # Run pipeline
        main(date="2026-01-19", data_dir=tmpdir)

        # Verify files were created
        index_path = Path(tmpdir) / "index.json"
        assert index_path.exists()

        scores_path = Path(tmpdir) / "scores" / "2026-01-19.json"
        assert scores_path.exists()

        # Verify index content
        with open(index_path) as f:
            index = json.load(f)
        assert "dates" in index
        assert len(index["dates"]) > 0
        assert index["dates"][0]["date"] == "2026-01-19"


@patch("pipeline.main.fetch_scoreboard")
def test_main_handles_missing_scoreboard(mock_fetch_sb):
    """Test that main handles missing scoreboard data gracefully."""
    mock_fetch_sb.return_value = None

    with tempfile.TemporaryDirectory() as tmpdir:
        main(date="2026-01-19", data_dir=tmpdir)

        # Verify no files created
        index_path = Path(tmpdir) / "index.json"
        assert not index_path.exists()


@patch("pipeline.main.fetch_game_rotation")
@patch("pipeline.main.fetch_playbyplay")
@patch("pipeline.main.fetch_boxscore")
@patch("pipeline.main.fetch_scoreboard")
def test_main_skips_incomplete_game(
    mock_fetch_sb, mock_fetch_bs, mock_fetch_pbp, mock_fetch_rot,
    sample_scoreboard_data, sample_boxscore_data, sample_playbyplay_data,
    sample_rotation_data
):
    """Test that main skips games with incomplete data."""
    mock_fetch_sb.return_value = sample_scoreboard_data
    mock_fetch_bs.return_value = None  # Missing boxscore
    mock_fetch_pbp.return_value = sample_playbyplay_data
    mock_fetch_rot.return_value = sample_rotation_data

    with tempfile.TemporaryDirectory() as tmpdir:
        main(date="2026-01-19", data_dir=tmpdir)

        # Verify fetch functions were called
        assert mock_fetch_sb.called
        assert mock_fetch_bs.called

        # No game-specific files should be created (games skipped)
        games_dir = Path(tmpdir) / "games"
        if games_dir.exists():
            assert len(list(games_dir.iterdir())) == 0


@patch("pipeline.main.fetch_scoreboard")
def test_main_handles_no_games(mock_fetch_sb):
    """Test that main handles dates with no games."""
    # Return scoreboard with no games
    empty_scoreboard = {
        "game_header": MagicMock(shape=(0,)),
        "line_score": MagicMock(shape=(0,)),
    }
    empty_scoreboard["game_header"].iloc = MagicMock(return_value=[])
    empty_scoreboard["game_header"].values.tolist = lambda: []
    empty_scoreboard["game_header"]["GAME_ID"] = MagicMock()
    empty_scoreboard["game_header"]["GAME_ID"].unique = lambda: []

    mock_fetch_sb.return_value = empty_scoreboard

    with tempfile.TemporaryDirectory() as tmpdir:
        main(date="2026-01-19", data_dir=tmpdir)

        # Should return early, no index created
        index_path = Path(tmpdir) / "index.json"
        assert not index_path.exists()


@patch("pipeline.main.fetch_game_rotation")
@patch("pipeline.main.fetch_playbyplay")
@patch("pipeline.main.fetch_boxscore")
@patch("pipeline.main.fetch_scoreboard")
def test_main_creates_proper_directory_structure(
    mock_fetch_sb, mock_fetch_bs, mock_fetch_pbp, mock_fetch_rot,
    sample_scoreboard_data, sample_boxscore_data, sample_playbyplay_data,
    sample_rotation_data
):
    """Test that main creates proper directory structure."""
    # Create scoreboard with only one game for this test
    import pandas as pd
    single_game_scoreboard = {
        "game_header": sample_scoreboard_data["game_header"].iloc[[0]].reset_index(drop=True),
        "line_score": sample_scoreboard_data["line_score"].iloc[[0, 1]].reset_index(drop=True),
    }

    mock_fetch_sb.return_value = single_game_scoreboard
    mock_fetch_bs.return_value = sample_boxscore_data
    mock_fetch_pbp.return_value = sample_playbyplay_data
    mock_fetch_rot.return_value = sample_rotation_data

    with tempfile.TemporaryDirectory() as tmpdir:
        main(date="2026-01-19", data_dir=tmpdir)

        # Verify directory structure
        assert (Path(tmpdir) / "index.json").exists()
        assert (Path(tmpdir) / "scores").exists()
        assert (Path(tmpdir) / "games").exists()

        # Verify index has correct structure
        with open(Path(tmpdir) / "index.json") as f:
            index = json.load(f)
        assert isinstance(index, dict)
        assert "dates" in index
        assert isinstance(index["dates"], list)


@patch("pipeline.main.fetch_game_rotation")
@patch("pipeline.main.fetch_playbyplay")
@patch("pipeline.main.fetch_boxscore")
@patch("pipeline.main.fetch_scoreboard")
def test_main_protects_existing_data_on_failure(
    mock_fetch_sb, mock_fetch_bs, mock_fetch_pbp, mock_fetch_rot,
    sample_scoreboard_data, sample_boxscore_data, sample_playbyplay_data,
    sample_rotation_data
):
    """Test that existing data is not modified when API fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # First run: write initial data
        single_game_scoreboard = {
            "game_header": sample_scoreboard_data["game_header"].iloc[[0]].reset_index(drop=True),
            "line_score": sample_scoreboard_data["line_score"].iloc[[0, 1]].reset_index(drop=True),
        }

        mock_fetch_sb.return_value = single_game_scoreboard
        mock_fetch_bs.return_value = sample_boxscore_data
        mock_fetch_pbp.return_value = sample_playbyplay_data
        mock_fetch_rot.return_value = sample_rotation_data

        main(date="2026-01-19", data_dir=tmpdir)

        # Get hashes of initial files
        index_path = Path(tmpdir) / "index.json"
        with open(index_path, "rb") as f:
            initial_index_hash = __import__("hashlib").md5(f.read()).hexdigest()

        scores_path = Path(tmpdir) / "scores" / "2026-01-19.json"
        with open(scores_path, "rb") as f:
            initial_scores_hash = __import__("hashlib").md5(f.read()).hexdigest()

        # Second run: mock all fetches to return None (simulating API failure)
        mock_fetch_sb.return_value = None
        mock_fetch_bs.return_value = None
        mock_fetch_pbp.return_value = None
        mock_fetch_rot.return_value = None

        main(date="2026-01-19", data_dir=tmpdir)

        # Verify existing files are unchanged
        with open(index_path, "rb") as f:
            final_index_hash = __import__("hashlib").md5(f.read()).hexdigest()

        with open(scores_path, "rb") as f:
            final_scores_hash = __import__("hashlib").md5(f.read()).hexdigest()

        assert initial_index_hash == final_index_hash
        assert initial_scores_hash == final_scores_hash


@patch("pipeline.main.fetch_game_rotation")
@patch("pipeline.main.fetch_playbyplay")
@patch("pipeline.main.fetch_boxscore")
@patch("pipeline.main.fetch_scoreboard")
def test_main_skips_failed_games_but_continues(
    mock_fetch_sb, mock_fetch_bs, mock_fetch_pbp, mock_fetch_rot,
    sample_scoreboard_data, sample_boxscore_data, sample_playbyplay_data,
    sample_rotation_data
):
    """Test that pipeline continues with other games when some fail."""
    import pandas as pd

    # Create scoreboard with two games
    mock_fetch_sb.return_value = sample_scoreboard_data

    # Mock so first game fails, second game succeeds
    mock_fetch_bs.side_effect = [None, sample_boxscore_data]
    mock_fetch_pbp.return_value = sample_playbyplay_data
    mock_fetch_rot.return_value = sample_rotation_data

    with tempfile.TemporaryDirectory() as tmpdir:
        main(date="2026-01-19", data_dir=tmpdir)

        # Scores should still be written for the date
        scores_path = Path(tmpdir) / "scores" / "2026-01-19.json"
        assert scores_path.exists()

        # Verify scores has data (not corrupted)
        with open(scores_path) as f:
            scores = json.load(f)
        assert len(scores) > 0
