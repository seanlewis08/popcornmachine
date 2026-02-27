"""Tests for the cleanup module."""

import json
import tempfile
from pathlib import Path

import pytest

from pipeline.cleanup import cleanup_old_data


class TestCleanupOldData:
    """Tests for cleanup_old_data function."""

    def test_cleanup_removes_score_files_from_previous_month(self):
        """Test that cleanup removes score files from previous months."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup: Create scores from two months
            scores_dir = Path(tmpdir) / "scores"
            scores_dir.mkdir(parents=True)

            # January scores (should be deleted)
            (scores_dir / "2026-01-15.json").write_text("[{}]")
            (scores_dir / "2026-01-20.json").write_text("[{}]")

            # February scores (should be kept)
            (scores_dir / "2026-02-01.json").write_text("[{}]")
            (scores_dir / "2026-02-15.json").write_text("[{}]")

            # Create index with entries from both months
            index_dir = Path(tmpdir)
            index_dir.mkdir(exist_ok=True)
            index_data = {
                "dates": [
                    {"date": "2026-02-15", "games": []},
                    {"date": "2026-02-01", "games": []},
                    {"date": "2026-01-20", "games": []},
                    {"date": "2026-01-15", "games": []},
                ]
            }
            (index_dir / "index.json").write_text(json.dumps(index_data))

            # Run cleanup with reference date in February
            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15")

            # Verify January files deleted
            assert not (scores_dir / "2026-01-15.json").exists()
            assert not (scores_dir / "2026-01-20.json").exists()

            # Verify February files kept
            assert (scores_dir / "2026-02-01.json").exists()
            assert (scores_dir / "2026-02-15.json").exists()

            # Verify deleted list contains deleted paths
            assert any("2026-01-15.json" in path for path in deleted)
            assert any("2026-01-20.json" in path for path in deleted)

    def test_cleanup_removes_game_directories_from_previous_month(self):
        """Test that cleanup removes game directories from previous months."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup: Create games from two months
            games_dir = Path(tmpdir) / "games"
            games_dir.mkdir(parents=True)

            # January game
            jan_game_dir = games_dir / "0022500001"
            jan_game_dir.mkdir()
            (jan_game_dir / "boxscore.json").write_text(
                json.dumps({"gameId": "0022500001", "date": "2026-01-15"})
            )
            (jan_game_dir / "gameflow.json").write_text("{}")

            # February game
            feb_game_dir = games_dir / "0022500002"
            feb_game_dir.mkdir()
            (feb_game_dir / "boxscore.json").write_text(
                json.dumps({"gameId": "0022500002", "date": "2026-02-15"})
            )
            (feb_game_dir / "gameflow.json").write_text("{}")

            # Run cleanup with reference date in February
            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15")

            # Verify January game directory deleted
            assert not jan_game_dir.exists()

            # Verify February game directory kept
            assert feb_game_dir.exists()

            # Verify deleted list contains deleted game
            assert any("0022500001" in path for path in deleted)

    def test_cleanup_updates_index_json(self):
        """Test that cleanup updates index.json to remove previous month entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup: Create index with entries from two months
            index_dir = Path(tmpdir)
            index_dir.mkdir(exist_ok=True)
            index_data = {
                "dates": [
                    {"date": "2026-02-15", "games": []},
                    {"date": "2026-01-15", "games": []},
                ]
            }
            (index_dir / "index.json").write_text(json.dumps(index_data))

            # Create scores directory (even if empty)
            (Path(tmpdir) / "scores").mkdir(exist_ok=True)

            # Run cleanup with reference date in February
            cleanup_old_data(tmpdir, reference_date="2026-02-15")

            # Verify index updated
            with open(index_dir / "index.json") as f:
                updated_index = json.load(f)

            dates = [d["date"] for d in updated_index["dates"]]
            assert "2026-02-15" in dates
            assert "2026-01-15" not in dates

    def test_cleanup_keeps_current_month_data(self):
        """Test that cleanup keeps all current month data intact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup: Create multiple files in February
            scores_dir = Path(tmpdir) / "scores"
            scores_dir.mkdir(parents=True)

            for day in [1, 10, 15, 20, 28]:
                (scores_dir / f"2026-02-{day:02d}.json").write_text("[{}]")

            games_dir = Path(tmpdir) / "games"
            games_dir.mkdir(parents=True)

            for i in range(3):
                game_dir = games_dir / f"000250000{i}"
                game_dir.mkdir()
                (game_dir / "boxscore.json").write_text(
                    json.dumps({"gameId": f"000250000{i}", "date": "2026-02-15"})
                )

            # Run cleanup with reference date in February
            cleanup_old_data(tmpdir, reference_date="2026-02-15")

            # Verify all February files still exist
            for day in [1, 10, 15, 20, 28]:
                assert (scores_dir / f"2026-02-{day:02d}.json").exists()

            for i in range(3):
                assert (games_dir / f"000250000{i}").exists()

    def test_cleanup_handles_empty_data_directory(self):
        """Test that cleanup handles empty data directory gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Call cleanup on empty directory
            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15")

            # Should return empty list, no errors
            assert deleted == []

    def test_cleanup_handles_missing_index_file(self):
        """Test that cleanup handles missing index.json gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create only scores directory without index
            scores_dir = Path(tmpdir) / "scores"
            scores_dir.mkdir(parents=True)
            (scores_dir / "2026-02-15.json").write_text("[{}]")

            # Call cleanup
            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15")

            # Should complete without error
            assert isinstance(deleted, list)

    def test_cleanup_uses_today_as_default_reference_date(self):
        """Test that cleanup uses today's date when reference_date is None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from datetime import datetime

            # Create scores from last month and this month
            scores_dir = Path(tmpdir) / "scores"
            scores_dir.mkdir(parents=True)

            today = datetime.now()
            current_month = today.strftime("%Y-%m")
            last_month = (
                datetime(today.year, today.month - 1 if today.month > 1 else 12, 1)
                .strftime("%Y-%m")
            )

            # Create score file from last month
            (scores_dir / f"{last_month}-01.json").write_text("[{}]")

            # Create score file from current month
            (scores_dir / f"{current_month}-01.json").write_text("[{}]")

            # Call cleanup without reference_date
            deleted = cleanup_old_data(tmpdir, reference_date=None)

            # Verify last month file deleted
            assert not (scores_dir / f"{last_month}-01.json").exists()

            # Verify current month file kept
            assert (scores_dir / f"{current_month}-01.json").exists()

    def test_cleanup_returns_list_of_deleted_paths(self):
        """Test that cleanup returns list of all deleted file paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup: Create files from two months
            scores_dir = Path(tmpdir) / "scores"
            scores_dir.mkdir(parents=True)
            (scores_dir / "2026-01-15.json").write_text("[{}]")
            (scores_dir / "2026-02-15.json").write_text("[{}]")

            # Run cleanup
            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15")

            # Verify deleted is a list
            assert isinstance(deleted, list)

            # Verify it contains paths
            assert len(deleted) > 0
            assert all(isinstance(path, str) for path in deleted)

    def test_cleanup_handles_boxscore_without_date_field(self):
        """Test that cleanup handles game directories with invalid boxscore.json gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup: Create game directory without date field in boxscore
            games_dir = Path(tmpdir) / "games"
            games_dir.mkdir(parents=True)

            game_dir = games_dir / "0022500001"
            game_dir.mkdir()
            (game_dir / "boxscore.json").write_text(
                json.dumps({"gameId": "0022500001"})  # No date field
            )

            # Run cleanup - should not crash
            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15")

            # Function should complete
            assert isinstance(deleted, list)

    def test_cleanup_checks_file_existence_before_delete(self):
        """Test that cleanup uses os.path.exists checks before delete."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup: Create data structure with some files
            scores_dir = Path(tmpdir) / "scores"
            scores_dir.mkdir(parents=True)
            (scores_dir / "2026-01-15.json").write_text("[{}]")

            # Create index referencing both existing and non-existing files
            index_dir = Path(tmpdir)
            index_data = {
                "dates": [
                    {"date": "2026-01-15", "games": []},
                    {"date": "2026-01-14", "games": []},  # This was never created
                ]
            }
            (index_dir / "index.json").write_text(json.dumps(index_data))

            # Run cleanup - should not crash on missing files
            deleted = cleanup_old_data(tmpdir, reference_date="2026-02-15")

            # Should complete successfully
            assert isinstance(deleted, list)
