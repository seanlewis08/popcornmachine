"""Tests for the cleanup module."""

import json
import tempfile
from pathlib import Path

import pytest

from pipeline.cleanup import cleanup_old_data


class TestCleanupOldData:
    """Tests for cleanup_old_data function."""

    def test_cleanup_removes_old_score_files(self):
        """Test that cleanup removes score files older than keep_days."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scores_dir = Path(tmpdir) / "scores"
            scores_dir.mkdir(parents=True)

            # Old scores (>30 days before 2026-02-15 → before 2026-01-16)
            (scores_dir / "2026-01-10.json").write_text("[{}]")
            (scores_dir / "2026-01-15.json").write_text("[{}]")

            # Recent scores (within 30 days of 2026-02-15)
            (scores_dir / "2026-01-20.json").write_text("[{}]")
            (scores_dir / "2026-02-01.json").write_text("[{}]")
            (scores_dir / "2026-02-15.json").write_text("[{}]")

            # Create index
            index_data = {
                "dates": [
                    {"date": "2026-02-15", "games": []},
                    {"date": "2026-02-01", "games": []},
                    {"date": "2026-01-20", "games": []},
                    {"date": "2026-01-15", "games": []},
                    {"date": "2026-01-10", "games": []},
                ]
            }
            (Path(tmpdir) / "index.json").write_text(json.dumps(index_data))

            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15")

            # Old files deleted
            assert not (scores_dir / "2026-01-10.json").exists()
            assert not (scores_dir / "2026-01-15.json").exists()

            # Recent files kept
            assert (scores_dir / "2026-01-20.json").exists()
            assert (scores_dir / "2026-02-01.json").exists()
            assert (scores_dir / "2026-02-15.json").exists()

            assert any("2026-01-10.json" in path for path in deleted)
            assert any("2026-01-15.json" in path for path in deleted)

    def test_cleanup_removes_old_game_directories(self):
        """Test that cleanup removes game directories older than keep_days."""
        with tempfile.TemporaryDirectory() as tmpdir:
            games_dir = Path(tmpdir) / "games"
            games_dir.mkdir(parents=True)

            # Old game (before cutoff)
            old_game = games_dir / "0022500001"
            old_game.mkdir()
            (old_game / "boxscore.json").write_text(
                json.dumps({"gameId": "0022500001", "date": "2026-01-10"})
            )
            (old_game / "gameflow.json").write_text("{}")

            # Recent game (within window)
            new_game = games_dir / "0022500002"
            new_game.mkdir()
            (new_game / "boxscore.json").write_text(
                json.dumps({"gameId": "0022500002", "date": "2026-02-10"})
            )
            (new_game / "gameflow.json").write_text("{}")

            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15")

            assert not old_game.exists()
            assert new_game.exists()
            assert any("0022500001" in path for path in deleted)

    def test_cleanup_updates_index_json(self):
        """Test that cleanup updates index.json to remove old entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_data = {
                "dates": [
                    {"date": "2026-02-15", "games": []},
                    {"date": "2026-01-10", "games": []},
                ]
            }
            (Path(tmpdir) / "index.json").write_text(json.dumps(index_data))
            (Path(tmpdir) / "scores").mkdir(exist_ok=True)

            cleanup_old_data(tmpdir, reference_date="2026-02-15")

            with open(Path(tmpdir) / "index.json") as f:
                updated_index = json.load(f)

            dates = [d["date"] for d in updated_index["dates"]]
            assert "2026-02-15" in dates
            assert "2026-01-10" not in dates

    def test_cleanup_keeps_data_within_window(self):
        """Test that cleanup keeps all data within the rolling window."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scores_dir = Path(tmpdir) / "scores"
            scores_dir.mkdir(parents=True)

            # All within 30 days of 2026-02-15
            recent_dates = ["2026-01-20", "2026-01-25", "2026-02-01", "2026-02-10", "2026-02-15"]
            for d in recent_dates:
                (scores_dir / f"{d}.json").write_text("[{}]")

            games_dir = Path(tmpdir) / "games"
            games_dir.mkdir(parents=True)
            for i, d in enumerate(recent_dates):
                game_dir = games_dir / f"000250000{i}"
                game_dir.mkdir()
                (game_dir / "boxscore.json").write_text(
                    json.dumps({"gameId": f"000250000{i}", "date": d})
                )

            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15")

            # Nothing should be deleted
            assert deleted == []
            for d in recent_dates:
                assert (scores_dir / f"{d}.json").exists()
            for i in range(len(recent_dates)):
                assert (games_dir / f"000250000{i}").exists()

    def test_cleanup_first_day_of_month_keeps_previous_month(self):
        """Test the exact bug: cleanup on March 1 keeps February data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scores_dir = Path(tmpdir) / "scores"
            scores_dir.mkdir(parents=True)

            # February data (within 30 days of March 1)
            (scores_dir / "2026-02-15.json").write_text("[{}]")
            (scores_dir / "2026-02-28.json").write_text("[{}]")

            # Old January data (>30 days before March 1)
            (scores_dir / "2026-01-15.json").write_text("[{}]")

            deleted = cleanup_old_data(tmpdir, reference_date="2026-03-01")

            # February data kept (within 30-day window)
            assert (scores_dir / "2026-02-15.json").exists()
            assert (scores_dir / "2026-02-28.json").exists()

            # Old January data deleted
            assert not (scores_dir / "2026-01-15.json").exists()

    def test_cleanup_handles_empty_data_directory(self):
        """Test that cleanup handles empty data directory gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15")
            assert deleted == []

    def test_cleanup_handles_missing_index_file(self):
        """Test that cleanup handles missing index.json gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scores_dir = Path(tmpdir) / "scores"
            scores_dir.mkdir(parents=True)
            (scores_dir / "2026-02-15.json").write_text("[{}]")

            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15")
            assert isinstance(deleted, list)

    def test_cleanup_uses_today_as_default_reference_date(self):
        """Test that cleanup uses today's date when reference_date is None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from datetime import datetime, timedelta

            scores_dir = Path(tmpdir) / "scores"
            scores_dir.mkdir(parents=True)

            today = datetime.now()
            # 60 days ago — guaranteed to be outside 30-day window
            old_date = (today - timedelta(days=60)).strftime("%Y-%m-%d")
            # Today — guaranteed to be inside window
            today_str = today.strftime("%Y-%m-%d")

            (scores_dir / f"{old_date}.json").write_text("[{}]")
            (scores_dir / f"{today_str}.json").write_text("[{}]")

            deleted = cleanup_old_data(tmpdir, reference_date=None)

            assert not (scores_dir / f"{old_date}.json").exists()
            assert (scores_dir / f"{today_str}.json").exists()

    def test_cleanup_returns_list_of_deleted_paths(self):
        """Test that cleanup returns list of all deleted file paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scores_dir = Path(tmpdir) / "scores"
            scores_dir.mkdir(parents=True)
            (scores_dir / "2025-12-01.json").write_text("[{}]")
            (scores_dir / "2026-02-15.json").write_text("[{}]")

            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15")

            assert isinstance(deleted, list)
            assert len(deleted) > 0
            assert all(isinstance(path, str) for path in deleted)

    def test_cleanup_handles_boxscore_without_date_field(self):
        """Test that cleanup handles game directories with no date in boxscore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            games_dir = Path(tmpdir) / "games"
            games_dir.mkdir(parents=True)

            game_dir = games_dir / "0022500001"
            game_dir.mkdir()
            (game_dir / "boxscore.json").write_text(
                json.dumps({"gameId": "0022500001"})  # No date field
            )

            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15")
            assert isinstance(deleted, list)

    def test_cleanup_custom_keep_days(self):
        """Test that keep_days parameter controls the retention window."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scores_dir = Path(tmpdir) / "scores"
            scores_dir.mkdir(parents=True)

            # 10 days before reference → kept with keep_days=15, deleted with keep_days=7
            (scores_dir / "2026-02-05.json").write_text("[{}]")
            (scores_dir / "2026-02-15.json").write_text("[{}]")

            # With 15-day window: cutoff is 2026-01-31, so Feb 5 is kept
            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15", keep_days=15)
            assert (scores_dir / "2026-02-05.json").exists()
            assert deleted == []

            # With 7-day window: cutoff is 2026-02-08, so Feb 5 is deleted
            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15", keep_days=7)
            assert not (scores_dir / "2026-02-05.json").exists()
            assert len(deleted) == 1
