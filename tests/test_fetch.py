"""Tests for the CDN fetch module."""

import re
from unittest.mock import patch

import pandas as pd
import pytest

from pipeline.fetch import (
    _parse_v3_clock,
    _cdn_minutes_to_mmss,
    _clock_to_decisecs,
    _normalize_schedule_date,
    fetch_boxscore,
    fetch_game_rotation,
    fetch_playbyplay,
    fetch_scoreboard,
)
import pipeline.fetch as fetch_module


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear module-level caches before each test."""
    fetch_module._schedule_cache = None
    fetch_module._pbp_cache.clear()
    fetch_module._boxscore_raw_cache.clear()
    yield
    fetch_module._schedule_cache = None
    fetch_module._pbp_cache.clear()
    fetch_module._boxscore_raw_cache.clear()


def _make_schedule_response(games=None, game_date="02/27/2026 00:00:00"):
    """Build a mock CDN scheduleLeagueV2 response."""
    if games is None:
        games = [
            {
                "gameId": "0022500803",
                "gameStatus": 3,
                "gameStatusText": "Final",
                "homeTeam": {
                    "teamId": 1610612765,
                    "teamName": "Pistons",
                    "teamCity": "Detroit",
                    "teamTricode": "DET",
                    "score": 104,
                },
                "awayTeam": {
                    "teamId": 1610612738,
                    "teamName": "Celtics",
                    "teamCity": "Boston",
                    "teamTricode": "BOS",
                    "score": 103,
                },
            },
        ]
    return {
        "leagueSchedule": {
            "seasonYear": "2025-26",
            "gameDates": [
                {"gameDate": game_date, "games": games},
            ],
        }
    }


def _make_boxscore_response():
    """Build a mock CDN boxscore response."""
    return {
        "game": {
            "gameId": "0022500803",
            "homeTeam": {
                "teamId": 1610612765,
                "teamName": "Pistons",
                "teamCity": "Detroit",
                "teamTricode": "DET",
                "score": 104,
                "players": [
                    {
                        "personId": 203507,
                        "firstName": "Cade",
                        "familyName": "Cunningham",
                        "name": "Cade Cunningham",
                        "nameI": "C. Cunningham",
                        "position": "G",
                        "starter": "1",
                        "played": "1",
                        "statistics": {
                            "minutes": "PT40M18.00S",
                            "fieldGoalsMade": 4,
                            "fieldGoalsAttempted": 17,
                            "threePointersMade": 0,
                            "threePointersAttempted": 4,
                            "freeThrowsMade": 8,
                            "freeThrowsAttempted": 10,
                            "reboundsOffensive": 1,
                            "reboundsDefensive": 2,
                            "reboundsTotal": 3,
                            "assists": 14,
                            "steals": 1,
                            "blocks": 2,
                            "turnovers": 0,
                            "foulsPersonal": 3,
                            "points": 16,
                            "plusMinusPoints": 2.0,
                        },
                    },
                ],
                "statistics": {
                    "fieldGoalsMade": 38,
                    "fieldGoalsAttempted": 88,
                    "threePointersMade": 11,
                    "threePointersAttempted": 33,
                    "freeThrowsMade": 17,
                    "freeThrowsAttempted": 23,
                    "reboundsOffensive": 9,
                    "reboundsDefensive": 31,
                    "reboundsTotal": 40,
                    "assists": 24,
                    "steals": 9,
                    "blocks": 9,
                    "turnovers": 5,
                    "foulsPersonal": 26,
                    "points": 104,
                    "plusMinusPoints": 0.0,
                },
            },
            "awayTeam": {
                "teamId": 1610612738,
                "teamName": "Celtics",
                "teamCity": "Boston",
                "teamTricode": "BOS",
                "score": 103,
                "players": [
                    {
                        "personId": 2544,
                        "firstName": "Kawhi",
                        "familyName": "Leonard",
                        "name": "Kawhi Leonard",
                        "nameI": "K. Leonard",
                        "position": "F",
                        "starter": "1",
                        "played": "1",
                        "statistics": {
                            "minutes": "PT38M30.00S",
                            "fieldGoalsMade": 10,
                            "fieldGoalsAttempted": 22,
                            "threePointersMade": 3,
                            "threePointersAttempted": 9,
                            "freeThrowsMade": 5,
                            "freeThrowsAttempted": 6,
                            "reboundsOffensive": 0,
                            "reboundsDefensive": 5,
                            "reboundsTotal": 5,
                            "assists": 4,
                            "steals": 1,
                            "blocks": 2,
                            "turnovers": 2,
                            "foulsPersonal": 4,
                            "points": 28,
                            "plusMinusPoints": -3.0,
                        },
                    },
                ],
                "statistics": {
                    "fieldGoalsMade": 33,
                    "fieldGoalsAttempted": 83,
                    "threePointersMade": 13,
                    "threePointersAttempted": 41,
                    "freeThrowsMade": 24,
                    "freeThrowsAttempted": 30,
                    "reboundsOffensive": 16,
                    "reboundsDefensive": 31,
                    "reboundsTotal": 47,
                    "assists": 13,
                    "steals": 5,
                    "blocks": 4,
                    "turnovers": 11,
                    "foulsPersonal": 26,
                    "points": 103,
                    "plusMinusPoints": 0.0,
                },
            },
        }
    }


def _make_pbp_response():
    """Build a mock CDN play-by-play response."""
    return {
        "game": {
            "gameId": "0022500803",
            "actions": [
                {
                    "actionNumber": 1,
                    "clock": "PT12M00.00S",
                    "period": 1,
                    "actionType": "jumpball",
                    "subType": "",
                    "personId": 203507,
                    "teamId": 1610612765,
                    "teamTricode": "DET",
                    "playerNameI": "C. Cunningham",
                    "description": "Jump Ball",
                    "scoreHome": "0",
                    "scoreAway": "0",
                    "isFieldGoal": 0,
                    "personIdsFilter": [203507],
                    "qualifiers": [],
                    "shotResult": "",
                },
                {
                    "actionNumber": 2,
                    "clock": "PT11M30.00S",
                    "period": 1,
                    "actionType": "2pt",
                    "subType": "driving",
                    "personId": 203507,
                    "teamId": 1610612765,
                    "teamTricode": "DET",
                    "playerNameI": "C. Cunningham",
                    "description": "C. Cunningham Driving Layup (2 PTS)",
                    "scoreHome": "2",
                    "scoreAway": "0",
                    "isFieldGoal": 1,
                    "personIdsFilter": [203507],
                    "qualifiers": [],
                    "shotResult": "Made",
                },
                {
                    "actionNumber": 3,
                    "clock": "PT11M00.00S",
                    "period": 1,
                    "actionType": "2pt",
                    "subType": "pullup",
                    "personId": 2544,
                    "teamId": 1610612738,
                    "teamTricode": "BOS",
                    "playerNameI": "K. Leonard",
                    "description": "K. Leonard Pullup Jumper (2 PTS)",
                    "scoreHome": "2",
                    "scoreAway": "2",
                    "isFieldGoal": 1,
                    "personIdsFilter": [2544],
                    "qualifiers": [],
                    "shotResult": "Made",
                },
                {
                    "actionNumber": 10,
                    "clock": "PT06M00.00S",
                    "period": 1,
                    "actionType": "substitution",
                    "subType": "",
                    "personId": 203507,
                    "teamId": 1610612765,
                    "teamTricode": "DET",
                    "playerNameI": "C. Cunningham",
                    "description": "C. Cunningham substitution replaced by D. Murray",
                    "scoreHome": "20",
                    "scoreAway": "18",
                    "isFieldGoal": 0,
                    "personIdsFilter": [203507, 203999],
                    "qualifiers": [],
                    "shotResult": "",
                },
                {
                    "actionNumber": 11,
                    "clock": "PT06M00.00S",
                    "period": 1,
                    "actionType": "substitution",
                    "subType": "",
                    "personId": 203999,
                    "teamId": 1610612765,
                    "teamTricode": "DET",
                    "playerNameI": "D. Murray",
                    "description": "D. Murray substitution replaced C. Cunningham",
                    "scoreHome": "20",
                    "scoreAway": "18",
                    "isFieldGoal": 0,
                    "personIdsFilter": [203507, 203999],
                    "qualifiers": [],
                    "shotResult": "",
                },
            ],
        }
    }


class TestCdnHeaders:
    """
    cdn.nba.com sits behind Akamai Bot Manager. Since mid-June 2026 it
    returns 403 "Access Denied" to anything that doesn't look like the XHR
    nba.com's own page makes. Headers alone got through from a residential
    IP but not from GitHub Actions (2026-10-23), so every request goes out
    through curl_cffi impersonating a real Chrome: the library supplies the
    TLS handshake and the matching identity headers (User-Agent, sec-ch-ua*);
    we add only the request context nba.com would send.
    """

    CONTEXT_HEADERS = ["Accept", "Origin", "Referer", "Sec-Fetch-Site", "Sec-Fetch-Mode", "Sec-Fetch-Dest"]
    IDENTITY_HEADERS = ["User-Agent", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform"]

    def test_context_headers_match_nba_com_xhr(self):
        for name in self.CONTEXT_HEADERS:
            assert name in fetch_module._HEADERS, f"missing header: {name}"
        assert fetch_module._HEADERS["Sec-Fetch-Site"] == "same-site"
        assert fetch_module._HEADERS["Sec-Fetch-Mode"] == "cors"
        assert fetch_module._HEADERS["Sec-Fetch-Dest"] == "empty"
        assert fetch_module._HEADERS["Origin"] == "https://www.nba.com"
        assert fetch_module._HEADERS["Referer"] == "https://www.nba.com/"

    def test_identity_headers_are_left_to_the_impersonation(self):
        """Overriding them would let the headers drift from the TLS fingerprint."""
        for name in self.IDENTITY_HEADERS:
            assert name.lower() not in {k.lower() for k in fetch_module._HEADERS}, name

    def test_impersonation_target_is_a_chrome_release(self):
        assert re.fullmatch(r"chrome\d+", fetch_module.IMPERSONATE), fetch_module.IMPERSONATE

    def test_fetch_json_passes_headers_impersonation_and_timeout(self):
        with patch("pipeline.fetch.http.get") as mock_get, patch("pipeline.fetch.time.sleep"):
            mock_get.return_value.json.return_value = {"ok": True}
            mock_get.return_value.raise_for_status.return_value = None
            assert fetch_module._fetch_json("https://cdn.nba.com/x.json", delay=0) == {"ok": True}
            _, kwargs = mock_get.call_args
            assert kwargs["headers"] is fetch_module._HEADERS
            assert kwargs["impersonate"] == fetch_module.IMPERSONATE
            assert kwargs["timeout"] == 30

    def test_fetch_json_retries_then_gives_up_on_curl_cffi_errors(self):
        from curl_cffi.requests.exceptions import HTTPError

        with patch("pipeline.fetch.http.get", side_effect=HTTPError("403")) as mock_get, patch(
            "pipeline.fetch.time.sleep"
        ):
            assert fetch_module._fetch_json("https://cdn.nba.com/x.json", delay=0) is None
            assert mock_get.call_count == 3  # 1 try + 2 retries

    def test_real_request_carries_consistent_chrome_identity(self):
        """
        End to end through curl_cffi against a local echo server: the wire
        request must carry a Chrome User-Agent whose major version matches
        the sec-ch-ua brands and the impersonation target, plus our context
        headers. No mocks — this is what Akamai sees.
        """
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        seen: dict[str, str] = {}

        class Echo(BaseHTTPRequestHandler):
            def do_GET(self):
                seen.update({k.lower(): v for k, v in self.headers.items()})
                body = b'{"ok": true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Echo)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            with patch("pipeline.fetch.time.sleep"):
                assert fetch_module._fetch_json(f"http://127.0.0.1:{port}/x.json", delay=0) == {"ok": True}
        finally:
            server.shutdown()

        major = re.fullmatch(r"chrome(\d+)", fetch_module.IMPERSONATE).group(1)
        assert f"Chrome/{major}." in seen["user-agent"]
        assert f'"Chromium";v="{major}"' in seen["sec-ch-ua"]
        assert f'"Google Chrome";v="{major}"' in seen["sec-ch-ua"]
        assert seen["sec-ch-ua-mobile"] == "?0"
        assert seen["origin"] == "https://www.nba.com"
        assert seen["referer"] == "https://www.nba.com/"
        assert seen["sec-fetch-mode"] == "cors"
        assert "accept-encoding" in seen  # the CDN refuses requests without it


class TestFetchScoreboard:
    """Tests for fetch_scoreboard function."""

    def test_fetch_scoreboard_success(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = _make_schedule_response()
            result = fetch_scoreboard("2026-02-27", delay=0)

            assert result is not None
            assert "game_header" in result
            assert "line_score" in result
            assert len(result["game_header"]) == 1
            assert len(result["line_score"]) == 2

    def test_fetch_scoreboard_has_required_columns(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = _make_schedule_response()
            result = fetch_scoreboard("2026-02-27", delay=0)

            assert "GAME_ID" in result["game_header"].columns
            assert "HOME_TEAM_ID" in result["game_header"].columns
            assert "VISITOR_TEAM_ID" in result["game_header"].columns
            assert "TEAM_ID" in result["line_score"].columns
            assert "TEAM_ABBREVIATION" in result["line_score"].columns
            assert "TEAM_NAME" in result["line_score"].columns
            assert "PTS" in result["line_score"].columns

    def test_fetch_scoreboard_no_games(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = _make_schedule_response(game_date="01/01/2026 00:00:00")
            result = fetch_scoreboard("2026-02-27", delay=0)

            assert result is not None
            assert len(result["game_header"]) == 0

    def test_fetch_scoreboard_api_failure(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = None
            result = fetch_scoreboard("2026-02-27", delay=0)
            assert result is None

    def test_fetch_scoreboard_skips_non_final_games(self):
        games = [{
            "gameId": "0022500803",
            "gameStatus": 1,
            "gameStatusText": "7:00 pm ET",
            "homeTeam": {"teamId": 1, "teamName": "A", "teamCity": "X", "teamTricode": "AAA", "score": 0},
            "awayTeam": {"teamId": 2, "teamName": "B", "teamCity": "Y", "teamTricode": "BBB", "score": 0},
        }]
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = _make_schedule_response(games=games)
            result = fetch_scoreboard("2026-02-27", delay=0)
            assert len(result["game_header"]) == 0

    @staticmethod
    def _final_game(game_id: str) -> dict:
        return {
            "gameId": game_id,
            "gameStatus": 3,
            "gameStatusText": "Final",
            "homeTeam": {"teamId": 1, "teamName": "A", "teamCity": "X", "teamTricode": "AAA", "score": 100},
            "awayTeam": {"teamId": 2, "teamName": "B", "teamCity": "Y", "teamTricode": "BBB", "score": 99},
        }

    def test_fetch_scoreboard_keeps_regular_season_playoff_and_play_in_games(self):
        """Game-ID prefix encodes type: 002 regular season, 004 playoffs, 005 play-in."""
        games = [self._final_game(g) for g in ("0022600006", "0042600101", "0052600001")]
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = _make_schedule_response(games=games)
            result = fetch_scoreboard("2026-02-27", delay=0)
            assert sorted(result["game_header"]["GAME_ID"]) == ["0022600006", "0042600101", "0052600001"]

    def test_fetch_scoreboard_skips_preseason_and_all_star_games(self):
        """001 = preseason, 003 = All-Star: stat lines are noise for this site."""
        games = [self._final_game(g) for g in ("0012600012", "0032600001", "0022600006")]
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = _make_schedule_response(games=games)
            result = fetch_scoreboard("2026-02-27", delay=0)
            assert list(result["game_header"]["GAME_ID"]) == ["0022600006"]
            assert list(result["line_score"]["GAME_ID"]) == ["0022600006", "0022600006"]


class TestFetchBoxscore:
    """Tests for fetch_boxscore function."""

    def test_fetch_boxscore_success(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = _make_boxscore_response()
            result = fetch_boxscore("0022500803", delay=0)

            assert result is not None
            assert "player_stats" in result
            assert "team_stats" in result
            assert len(result["player_stats"]) == 2
            assert len(result["team_stats"]) == 2

    def test_fetch_boxscore_has_required_columns(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = _make_boxscore_response()
            result = fetch_boxscore("0022500803", delay=0)

            required = ["PLAYER_ID", "PLAYER_NAME", "MIN", "FGM", "FGA", "PTS", "PLUS_MINUS"]
            for col in required:
                assert col in result["player_stats"].columns

    def test_fetch_boxscore_has_roster_position(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = _make_boxscore_response()
            result = fetch_boxscore("0022500803", delay=0)
            assert "ROSTER_POSITION" in result["player_stats"].columns

    def test_fetch_boxscore_minutes_format(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = _make_boxscore_response()
            result = fetch_boxscore("0022500803", delay=0)
            assert result["player_stats"].iloc[0]["MIN"] == "40:18"

    def test_fetch_boxscore_failure(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = None
            result = fetch_boxscore("0022500803", delay=0)
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


class TestCdnMinutesToMmss:
    """Tests for _cdn_minutes_to_mmss helper."""

    def test_standard_minutes(self):
        assert _cdn_minutes_to_mmss("PT34M20.00S") == "34:20"

    def test_zero_minutes(self):
        assert _cdn_minutes_to_mmss("PT00M00.00S") == "0:00"


class TestClockToDecisecs:
    """Tests for _clock_to_decisecs helper."""

    def test_start_of_game(self):
        assert _clock_to_decisecs(1, "12:00") == 0

    def test_end_of_q1(self):
        assert _clock_to_decisecs(1, "0:00") == 7200

    def test_mid_q2(self):
        assert _clock_to_decisecs(2, "6:00") == 10800


class TestNormalizeScheduleDate:
    """Tests for _normalize_schedule_date helper."""

    def test_mm_dd_yyyy_format(self):
        assert _normalize_schedule_date("02/27/2026 00:00:00") == "2026-02-27"

    def test_iso_format(self):
        assert _normalize_schedule_date("2026-02-27T00:00:00") == "2026-02-27"

    def test_empty_string(self):
        assert _normalize_schedule_date("") == ""


class TestFetchPlaybyplay:
    """Tests for fetch_playbyplay function."""

    def test_fetch_playbyplay_success(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = _make_pbp_response()
            result = fetch_playbyplay("0022500803", delay=0)

            assert result is not None
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 5

    def test_fetch_playbyplay_has_v2_columns(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = _make_pbp_response()
            result = fetch_playbyplay("0022500803", delay=0)

            required = ["PERIOD", "PLAYER1_ID", "PCTIMESTRING", "EVENTMSGTYPE",
                        "EVENTNUM", "HOMEDESCRIPTION", "SCORE_HOME", "SCORE_AWAY"]
            for col in required:
                assert col in result.columns

    def test_fetch_playbyplay_clock_conversion(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = _make_pbp_response()
            result = fetch_playbyplay("0022500803", delay=0)
            assert result.iloc[0]["PCTIMESTRING"] == "12:00"
            assert result.iloc[1]["PCTIMESTRING"] == "11:30"

    def test_fetch_playbyplay_failure(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = None
            result = fetch_playbyplay("0022500803", delay=0)
            assert result is None

    def test_fetch_playbyplay_caching(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = _make_pbp_response()
            result1 = fetch_playbyplay("0022500803", delay=0)
            result2 = fetch_playbyplay("0022500803", delay=0)
            assert mock_fetch.call_count == 1
            assert result1 is result2


class TestFetchGameRotation:
    """Tests for fetch_game_rotation (derived from PBP)."""

    def test_fetch_game_rotation_success(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.side_effect = [
                _make_boxscore_response(),
                _make_pbp_response(),
            ]
            fetch_boxscore("0022500803", delay=0)
            result = fetch_game_rotation("0022500803", delay=0)

            assert result is not None
            assert "away_team" in result
            assert "home_team" in result

    def test_fetch_game_rotation_has_required_columns(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.side_effect = [
                _make_boxscore_response(),
                _make_pbp_response(),
            ]
            fetch_boxscore("0022500803", delay=0)
            result = fetch_game_rotation("0022500803", delay=0)

            required = ["PERSON_ID", "IN_TIME_REAL", "OUT_TIME_REAL", "PT_DIFF"]
            for col in required:
                assert col in result["home_team"].columns
                assert col in result["away_team"].columns

    def test_fetch_game_rotation_starters_have_stints(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.side_effect = [
                _make_boxscore_response(),
                _make_pbp_response(),
            ]
            fetch_boxscore("0022500803", delay=0)
            result = fetch_game_rotation("0022500803", delay=0)

            home_pids = result["home_team"]["PERSON_ID"].tolist()
            assert 203507 in home_pids

    def test_fetch_game_rotation_pbp_failure(self):
        with patch("pipeline.fetch._fetch_json") as mock_fetch:
            mock_fetch.return_value = None
            result = fetch_game_rotation("0022500803", delay=0)
            assert result is None
