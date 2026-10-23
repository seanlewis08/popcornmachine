"""Tests for the cleanup module.

Retention rule: keep every game from the season that `reference_date` falls
in (October → the following September); delete everything from earlier
seasons. See pipeline/season.py for the season boundary.
"""

import json
import tempfile
from pathlib import Path

from pipeline.cleanup import cleanup_old_data, is_stale


def _write_scores(tmpdir: str, dates: list[str]) -> Path:
    scores_dir = Path(tmpdir) / "scores"
    scores_dir.mkdir(parents=True, exist_ok=True)
    for d in dates:
        (scores_dir / f"{d}.json").write_text("[{}]")
    return scores_dir


def _write_game(tmpdir: str, game_id: str, date: str) -> Path:
    game_dir = Path(tmpdir) / "games" / game_id
    game_dir.mkdir(parents=True)
    (game_dir / "boxscore.json").write_text(json.dumps({"gameId": game_id, "date": date}))
    (game_dir / "gameflow.json").write_text("{}")
    return game_dir


def _write_index(tmpdir: str, dates: list[str]) -> Path:
    index_path = Path(tmpdir) / "index.json"
    index_path.write_text(json.dumps({"dates": [{"date": d, "games": []} for d in dates]}))
    return index_path


class TestIsStale:
    """Pure retention predicate."""

    def test_same_season_is_kept(self):
        assert is_stale("2026-10-21", reference_date="2027-04-10") is False

    def test_previous_season_is_stale(self):
        assert is_stale("2026-04-10", reference_date="2026-10-21") is True

    def test_offseason_reference_keeps_the_season_just_ended(self):
        # August 2027: the 2026-27 season is still "current".
        assert is_stale("2026-10-21", reference_date="2027-08-01") is False
        assert is_stale("2027-06-18", reference_date="2027-08-01") is False

    def test_first_game_day_of_new_season_drops_last_season(self):
        assert is_stale("2027-06-18", reference_date="2027-10-20") is True

    def test_unparseable_date_is_not_stale(self):
        # Never delete something we can't classify.
        assert is_stale("garbage", reference_date="2027-10-20") is False


class TestCleanupOldData:
    """Filesystem effects of the retention rule."""

    def test_cleanup_removes_previous_season_score_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scores_dir = _write_scores(
                tmpdir,
                ["2026-04-10", "2026-06-18", "2026-10-21", "2026-10-22"],
            )
            _write_index(tmpdir, ["2026-10-22", "2026-10-21", "2026-06-18", "2026-04-10"])

            deleted = cleanup_old_data(tmpdir, reference_date="2026-10-23")

            assert not (scores_dir / "2026-04-10.json").exists()
            assert not (scores_dir / "2026-06-18.json").exists()
            assert (scores_dir / "2026-10-21.json").exists()
            assert (scores_dir / "2026-10-22.json").exists()
            assert any("2026-04-10.json" in p for p in deleted)
            assert any("2026-06-18.json" in p for p in deleted)

    def test_cleanup_removes_previous_season_game_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_game = _write_game(tmpdir, "0042500405", "2026-06-18")
            new_game = _write_game(tmpdir, "0022600006", "2026-10-22")

            deleted = cleanup_old_data(tmpdir, reference_date="2026-10-23")

            assert not old_game.exists()
            assert new_game.exists()
            assert any("0042500405" in p for p in deleted)

    def test_cleanup_updates_index_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = _write_index(tmpdir, ["2026-10-22", "2026-06-18"])
            (Path(tmpdir) / "scores").mkdir()

            cleanup_old_data(tmpdir, reference_date="2026-10-23")

            dates = [d["date"] for d in json.loads(index_path.read_text())["dates"]]
            assert dates == ["2026-10-22"]

    def test_cleanup_keeps_whole_season_across_new_year(self):
        """January of a season must not drop October–December."""
        with tempfile.TemporaryDirectory() as tmpdir:
            season_dates = ["2026-10-21", "2026-11-15", "2026-12-25", "2027-01-10", "2027-03-01"]
            scores_dir = _write_scores(tmpdir, season_dates)
            _write_index(tmpdir, season_dates)

            deleted = cleanup_old_data(tmpdir, reference_date="2027-03-02")

            assert deleted == []
            for d in season_dates:
                assert (scores_dir / f"{d}.json").exists()

    def test_cleanup_in_offseason_keeps_finished_season(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scores_dir = _write_scores(tmpdir, ["2026-10-21", "2027-06-18"])
            _write_index(tmpdir, ["2027-06-18", "2026-10-21"])

            deleted = cleanup_old_data(tmpdir, reference_date="2027-08-15")

            assert deleted == []
            assert (scores_dir / "2026-10-21.json").exists()
            assert (scores_dir / "2027-06-18.json").exists()

    def test_cleanup_handles_empty_data_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert cleanup_old_data(tmpdir, reference_date="2026-10-23") == []

    def test_cleanup_handles_missing_data_directory(self):
        assert cleanup_old_data("/nonexistent/path", reference_date="2026-10-23") == []

    def test_cleanup_handles_missing_index_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_scores(tmpdir, ["2026-10-22"])
            assert isinstance(cleanup_old_data(tmpdir, reference_date="2026-10-23"), list)

    def test_cleanup_uses_today_as_default_reference_date(self):
        from datetime import datetime, timedelta

        with tempfile.TemporaryDirectory() as tmpdir:
            today = datetime.now().strftime("%Y-%m-%d")
            two_seasons_ago = (datetime.now() - timedelta(days=800)).strftime("%Y-%m-%d")
            scores_dir = _write_scores(tmpdir, [today, two_seasons_ago])

            cleanup_old_data(tmpdir)

            assert (scores_dir / f"{today}.json").exists()
            assert not (scores_dir / f"{two_seasons_ago}.json").exists()

    def test_cleanup_ignores_game_without_date_field(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            game_dir = Path(tmpdir) / "games" / "0022500001"
            game_dir.mkdir(parents=True)
            (game_dir / "boxscore.json").write_text(json.dumps({"gameId": "0022500001"}))

            deleted = cleanup_old_data(tmpdir, reference_date="2026-10-23")

            assert deleted == []
            assert game_dir.exists()

    def test_cleanup_ignores_non_date_score_filenames(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scores_dir = Path(tmpdir) / "scores"
            scores_dir.mkdir()
            (scores_dir / "notes.json").write_text("{}")

            deleted = cleanup_old_data(tmpdir, reference_date="2026-10-23")

            assert deleted == []
            assert (scores_dir / "notes.json").exists()
