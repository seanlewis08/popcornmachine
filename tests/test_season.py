"""Tests for season derivation."""

import pytest

from pipeline.season import season_for, season_start_date


class TestSeasonFor:
    """An NBA season runs October → June and is named by its start year."""

    @pytest.mark.parametrize(
        "date, expected",
        [
            ("2026-10-01", "2026-27"),  # first day of the new season window
            ("2026-10-21", "2026-27"),  # opening night
            ("2026-12-25", "2026-27"),
            ("2027-01-01", "2026-27"),  # calendar year rolls over, season does not
            ("2027-06-18", "2026-27"),  # Finals
            ("2027-07-15", "2026-27"),  # offseason still belongs to the season just ended
            ("2027-09-30", "2026-27"),  # last day before the next season window
            ("2027-10-01", "2027-28"),
            ("1999-10-01", "1999-00"),  # two-digit suffix wraps across the century
        ],
    )
    def test_season_for(self, date, expected):
        assert season_for(date) == expected

    def test_rejects_malformed_date(self):
        with pytest.raises(ValueError):
            season_for("2026/10/21")

    def test_rejects_impossible_month(self):
        with pytest.raises(ValueError):
            season_for("2026-13-01")


class TestSeasonStartDate:
    def test_october_first_of_start_year(self):
        assert season_start_date("2027-02-14") == "2026-10-01"

    def test_date_in_october_is_its_own_season(self):
        assert season_start_date("2026-10-21") == "2026-10-01"


class TestCli:
    """`python -m pipeline.season --start-of DATE` is what the workflow calls."""

    def _run(self, *args: str):
        import subprocess
        import sys
        from pathlib import Path

        return subprocess.run(
            [sys.executable, "-m", "pipeline.season", *args],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )

    def test_prints_season_start_date(self):
        result = self._run("--start-of", "2027-02-14")
        assert result.returncode == 0
        assert result.stdout.strip() == "2026-10-01"

    def test_bad_date_exits_nonzero(self):
        result = self._run("--start-of", "not-a-date")
        assert result.returncode != 0
