"""Tests for the write module."""

import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from pipeline.write import write_game_data, write_index, write_scores


class TestWriteIndex:
    """Tests for write_index function."""

    def test_write_index_creates_file(self):
        """Test that write_index creates index.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dates_data = [
                {
                    "date": "2026-01-19",
                    "games": [
                        {
                            "gameId": "0022500001",
                            "home": "DET",
                            "away": "BOS",
                            "homeScore": 104,
                            "awayScore": 103,
                        }
                    ],
                }
            ]

            write_index(dates_data, tmpdir)

            index_path = Path(tmpdir) / "index.json"
            assert index_path.exists()

            with open(index_path) as f:
                index = json.load(f)

            assert "dates" in index
            assert len(index["dates"]) == 1
            assert index["dates"][0]["date"] == "2026-01-19"

    def test_write_index_sorts_dates_descending(self):
        """Test that write_index sorts dates most recent first."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dates_data = [
                {"date": "2026-01-17", "games": []},
                {"date": "2026-01-19", "games": []},
                {"date": "2026-01-18", "games": []},
            ]

            write_index(dates_data, tmpdir)

            index_path = Path(tmpdir) / "index.json"
            with open(index_path) as f:
                index = json.load(f)

            dates = [d["date"] for d in index["dates"]]
            assert dates == ["2026-01-19", "2026-01-18", "2026-01-17"]

    def test_write_index_merges_existing(self):
        """Test that write_index merges with existing index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write initial index
            initial = [{"date": "2026-01-18", "games": [{"gameId": "001"}]}]
            write_index(initial, tmpdir)

            # Merge new date
            new = [{"date": "2026-01-19", "games": [{"gameId": "002"}]}]
            write_index(new, tmpdir)

            # Verify both dates present and sorted
            index_path = Path(tmpdir) / "index.json"
            with open(index_path) as f:
                index = json.load(f)

            dates = [d["date"] for d in index["dates"]]
            assert dates == ["2026-01-19", "2026-01-18"]

    def test_write_index_replaces_same_date(self):
        """Test that write_index replaces entry for same date."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write initial
            initial = [{"date": "2026-01-19", "games": [{"gameId": "001"}]}]
            write_index(initial, tmpdir)

            # Replace with new games for same date
            updated = [{"date": "2026-01-19", "games": [{"gameId": "002"}]}]
            write_index(updated, tmpdir)

            # Verify replaced
            index_path = Path(tmpdir) / "index.json"
            with open(index_path) as f:
                index = json.load(f)

            assert len(index["dates"]) == 1
            assert index["dates"][0]["games"][0]["gameId"] == "002"


class TestWriteScores:
    """Tests for write_scores function."""

    def test_write_scores_creates_file(self):
        """Test that write_scores creates date-specific scores file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scores = [
                {
                    "gameId": "0022500001",
                    "date": "2026-01-19",
                    "homeTeam": {"tricode": "DET", "name": "Pistons", "score": 104},
                    "awayTeam": {"tricode": "BOS", "name": "Celtics", "score": 103},
                    "status": "Final",
                }
            ]

            write_scores("2026-01-19", scores, tmpdir)

            scores_path = Path(tmpdir) / "scores" / "2026-01-19.json"
            assert scores_path.exists()

            with open(scores_path) as f:
                data = json.load(f)

            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["gameId"] == "0022500001"

    def test_write_scores_creates_directory(self):
        """Test that write_scores creates scores directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scores = []
            write_scores("2026-01-19", scores, tmpdir)

            scores_dir = Path(tmpdir) / "scores"
            assert scores_dir.exists()
            assert scores_dir.is_dir()

    def test_write_scores_valid_json(self):
        """Test that written JSON is valid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scores = [
                {
                    "gameId": "0022500001",
                    "homeTeam": {"tricode": "DET", "score": 104},
                    "awayTeam": {"tricode": "BOS", "score": 103},
                }
            ]

            write_scores("2026-01-19", scores, tmpdir)

            scores_path = Path(tmpdir) / "scores" / "2026-01-19.json"
            with open(scores_path) as f:
                # Will raise exception if invalid JSON
                data = json.load(f)
                assert len(data) == 1


class TestWriteGameData:
    """Tests for write_game_data function."""

    def test_write_game_data_creates_files(self):
        """Test that write_game_data creates both boxscore and gameflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            boxscore = {
                "gameId": "0022500001",
                "players": [],
                "teamTotals": {},
            }
            gameflow = {
                "gameId": "0022500001",
                "players": [],
            }

            write_game_data("0022500001", boxscore, gameflow, tmpdir)

            game_dir = Path(tmpdir) / "games" / "0022500001"
            assert (game_dir / "boxscore.json").exists()
            assert (game_dir / "gameflow.json").exists()

    def test_write_game_data_creates_directory_structure(self):
        """Test that write_game_data creates nested directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            boxscore = {"gameId": "0022500001"}
            gameflow = {"gameId": "0022500001"}

            write_game_data("0022500001", boxscore, gameflow, tmpdir)

            game_dir = Path(tmpdir) / "games" / "0022500001"
            assert game_dir.exists()
            assert game_dir.is_dir()

    def test_write_game_data_json_content(self):
        """Test that written JSON files have correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            boxscore = {
                "gameId": "0022500001",
                "date": "2026-01-19",
                "players": [{"playerId": "123", "name": "Test"}],
            }
            gameflow = {
                "gameId": "0022500001",
                "players": [],
            }

            write_game_data("0022500001", boxscore, gameflow, tmpdir)

            # Verify boxscore
            boxscore_path = Path(tmpdir) / "games" / "0022500001" / "boxscore.json"
            with open(boxscore_path) as f:
                data = json.load(f)
            assert data["gameId"] == "0022500001"
            assert len(data["players"]) == 1

            # Verify gameflow
            gameflow_path = Path(tmpdir) / "games" / "0022500001" / "gameflow.json"
            with open(gameflow_path) as f:
                data = json.load(f)
            assert data["gameId"] == "0022500001"

    def test_write_game_data_overwrites_existing(self):
        """Test that write_game_data overwrites existing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write initial
            write_game_data(
                "0022500001",
                {"gameId": "0022500001", "version": 1},
                {"gameId": "0022500001"},
                tmpdir,
            )

            # Overwrite
            write_game_data(
                "0022500001",
                {"gameId": "0022500001", "version": 2},
                {"gameId": "0022500001"},
                tmpdir,
            )

            # Verify overwritten
            boxscore_path = Path(tmpdir) / "games" / "0022500001" / "boxscore.json"
            with open(boxscore_path) as f:
                data = json.load(f)
            assert data["version"] == 2


class TestIdempotentWrites:
    """Tests for idempotent JSON writes."""

    def test_write_scores_produces_deterministic_output(self):
        """Test that writing same scores twice produces byte-identical JSON."""
        scores = [
            {
                "gameId": "0022500001",
                "date": "2026-01-19",
                "homeTeam": {
                    "tricode": "DET",
                    "name": "Pistons",
                    "score": 104,
                },
                "awayTeam": {
                    "tricode": "BOS",
                    "name": "Celtics",
                    "score": 103,
                },
                "status": "Final",
            },
            {
                "gameId": "0022500002",
                "date": "2026-01-19",
                "homeTeam": {
                    "tricode": "LAL",
                    "name": "Lakers",
                    "score": 110,
                },
                "awayTeam": {
                    "tricode": "GSW",
                    "name": "Warriors",
                    "score": 108,
                },
                "status": "Final",
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write first time
            write_scores("2026-01-19", scores, tmpdir)
            scores_path = Path(tmpdir) / "scores" / "2026-01-19.json"

            with open(scores_path, "rb") as f:
                first_bytes = f.read()
            first_hash = hashlib.md5(first_bytes).hexdigest()

            # Write second time with same data
            write_scores("2026-01-19", scores, tmpdir)
            with open(scores_path, "rb") as f:
                second_bytes = f.read()
            second_hash = hashlib.md5(second_bytes).hexdigest()

            # Verify byte-identical
            assert first_hash == second_hash
            assert first_bytes == second_bytes

    def test_write_index_produces_deterministic_output(self):
        """Test that writing same index twice produces byte-identical JSON."""
        dates_data = [
            {
                "date": "2026-01-19",
                "games": [
                    {
                        "gameId": "0022500001",
                        "home": "DET",
                        "away": "BOS",
                        "homeScore": 104,
                        "awayScore": 103,
                    }
                ],
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write first time
            write_index(dates_data, tmpdir)
            index_path = Path(tmpdir) / "index.json"

            with open(index_path, "rb") as f:
                first_bytes = f.read()
            first_hash = hashlib.md5(first_bytes).hexdigest()

            # Write second time with same data
            write_index(dates_data, tmpdir)
            with open(index_path, "rb") as f:
                second_bytes = f.read()
            second_hash = hashlib.md5(second_bytes).hexdigest()

            # Verify byte-identical
            assert first_hash == second_hash
            assert first_bytes == second_bytes

    def test_write_game_data_produces_deterministic_output(self):
        """Test that writing same game data twice produces byte-identical JSON."""
        boxscore = {
            "gameId": "0022500001",
            "date": "2026-01-19",
            "homeTeam": {"tricode": "DET", "name": "Pistons", "score": 104},
            "awayTeam": {"tricode": "BOS", "name": "Celtics", "score": 103},
            "players": [
                {
                    "playerId": "203507",
                    "name": "Cade Cunningham",
                    "team": "DET",
                    "totals": {
                        "min": 40.3,
                        "fgm": 4,
                        "fga": 17,
                    },
                }
            ],
            "teamTotals": {
                "home": {"fgm": 38, "fga": 88},
                "away": {"fgm": 33, "fga": 83},
            },
            "periodTotals": {},
        }

        gameflow = {
            "gameId": "0022500001",
            "homeTeam": {"tricode": "DET", "name": "Pistons"},
            "awayTeam": {"tricode": "BOS", "name": "Celtics"},
            "players": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write first time
            write_game_data("0022500001", boxscore, gameflow, tmpdir)

            boxscore_path = Path(tmpdir) / "games" / "0022500001" / "boxscore.json"
            gameflow_path = Path(tmpdir) / "games" / "0022500001" / "gameflow.json"

            with open(boxscore_path, "rb") as f:
                boxscore_first = f.read()
            with open(gameflow_path, "rb") as f:
                gameflow_first = f.read()

            boxscore_hash_1 = hashlib.md5(boxscore_first).hexdigest()
            gameflow_hash_1 = hashlib.md5(gameflow_first).hexdigest()

            # Write second time
            write_game_data("0022500001", boxscore, gameflow, tmpdir)

            with open(boxscore_path, "rb") as f:
                boxscore_second = f.read()
            with open(gameflow_path, "rb") as f:
                gameflow_second = f.read()

            boxscore_hash_2 = hashlib.md5(boxscore_second).hexdigest()
            gameflow_hash_2 = hashlib.md5(gameflow_second).hexdigest()

            # Verify byte-identical
            assert boxscore_hash_1 == boxscore_hash_2
            assert gameflow_hash_1 == gameflow_hash_2

    def test_json_uses_sort_keys(self):
        """Test that JSON output uses sorted keys."""
        # Create a dict with keys that would be in different order
        test_data = {"zebra": 1, "apple": 2, "middle": 3}

        with tempfile.TemporaryDirectory() as tmpdir:
            write_scores("2026-01-19", [test_data], tmpdir)

            scores_path = Path(tmpdir) / "scores" / "2026-01-19.json"
            with open(scores_path) as f:
                content = f.read()

            # The keys should appear in alphabetical order in the raw JSON
            apple_pos = content.find('"apple"')
            middle_pos = content.find('"middle"')
            zebra_pos = content.find('"zebra"')

            assert apple_pos < middle_pos < zebra_pos
