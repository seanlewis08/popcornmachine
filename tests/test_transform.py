"""Tests for the transform module."""

import pandas as pd
import pytest

from pipeline.transform import (
    _shot_detail,
    shot_area,
    shot_area_detail,
    _aggregate_stint_stats,
    _compute_stint_minutes,
    _parse_minutes,
    _pbp_event_to_type,
    _rotation_time_to_period_clock,
    transform_boxscore,
    transform_gameflow,
    transform_scores,
)


class TestRotationTimeConversion:
    """Tests for time conversion utilities."""

    def test_rotation_time_to_period_clock_period_1(self):
        """Test period 1 (countdown clock). Rotation API uses deciseconds."""
        # 0 decisecs = game start, 6060 decisecs = 606 seconds elapsed
        period, in_clock, out_clock = _rotation_time_to_period_clock(0, 6060)
        assert period == 1
        assert in_clock == "12:00"  # 720-0 = 720s = 12:00
        assert out_clock == "1:54"  # 720-606 = 114s = 1:54

    def test_rotation_time_to_period_clock_period_2(self):
        """Test period 2 (countdown clock). 7200 decisecs = start of Q2."""
        # 7200 = 720s = start of Q2, 12000 = 1200s = 480s into Q2
        period, in_clock, out_clock = _rotation_time_to_period_clock(7200, 12000)
        assert period == 2
        assert in_clock == "12:00"  # 720-0 = 720s
        assert out_clock == "4:00"  # 720-480 = 240s = 4:00

    def test_compute_stint_minutes(self):
        """Test stint duration in deciseconds. 6060 decisecs = 10.1 min."""
        minutes = _compute_stint_minutes(0, 6060)
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

    # V3 string action type tests
    def test_pbp_event_v3_2pt_make(self):
        """Test V3 string '2pt' without miss in subtype."""
        assert _pbp_event_to_type("2pt", "driving") == "make2"

    def test_pbp_event_v3_2pt_miss(self):
        """Test V3 string '2pt' with miss in subtype."""
        assert _pbp_event_to_type("2pt", "Miss") == "miss2"

    def test_pbp_event_v3_3pt_make(self):
        """Test V3 string '3pt' make."""
        assert _pbp_event_to_type("3pt", "pullup") == "make3"

    def test_pbp_event_v3_3pt_miss(self):
        """Test V3 string '3pt' miss."""
        assert _pbp_event_to_type("3pt", "Miss") == "miss3"

    def test_pbp_event_v3_freethrow(self):
        """Test V3 string 'freethrow'."""
        assert _pbp_event_to_type("freethrow", "") == "fta"

    def test_pbp_event_v3_rebound(self):
        """Test V3 string 'rebound'."""
        assert _pbp_event_to_type("rebound", "") == "reb"

    def test_pbp_event_v3_turnover(self):
        """Test V3 string 'turnover'."""
        assert _pbp_event_to_type("turnover", "") == "tov"

    def test_pbp_event_v3_foul(self):
        """Test V3 string 'foul'."""
        assert _pbp_event_to_type("foul", "") == "foul"

    def test_pbp_event_v3_substitution(self):
        """Test V3 substitution string action type."""
        assert _pbp_event_to_type("substitution", "") == "sub"

    def test_pbp_event_v3_unknown(self):
        """Test V3 truly unknown string action type."""
        assert _pbp_event_to_type("xyzunknowntype", "") == "other"


class TestParseMinutes:
    """Tests for _parse_minutes helper."""

    def test_float_value(self):
        assert _parse_minutes(34.5) == 34.5

    def test_int_value(self):
        assert _parse_minutes(34) == 34.0

    def test_mm_ss_string(self):
        assert _parse_minutes("34:20") == 34.3

    def test_string_float(self):
        assert _parse_minutes("34.5") == 34.5

    def test_nan(self):
        assert _parse_minutes(float("nan")) == 0.0

    def test_zero(self):
        assert _parse_minutes(0) == 0.0

    def test_empty_string(self):
        assert _parse_minutes("") == 0.0


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
        result = transform_scores(sample_scoreboard_data, "2026-01-19")
        assert isinstance(result, list)
        assert len(result) == 2
        assert all("gameId" in game for game in result)

    def test_transform_scores_includes_team_names(self, sample_scoreboard_data):
        """Test that games include team names and tricodes."""
        result = transform_scores(sample_scoreboard_data, "2026-01-19")
        assert len(result) > 0
        game = result[0]
        assert "homeTeam" in game
        assert "awayTeam" in game
        assert "tricode" in game["homeTeam"]
        assert "name" in game["homeTeam"]
        assert "score" in game["homeTeam"]

    def test_transform_scores_includes_final_score(self, sample_scoreboard_data):
        """Test that games include final scores."""
        result = transform_scores(sample_scoreboard_data, "2026-01-19")
        assert len(result) > 0
        game = result[0]
        assert isinstance(game["homeTeam"]["score"], int)
        assert isinstance(game["awayTeam"]["score"], int)
        assert game["homeTeam"]["score"] == 104
        assert game["awayTeam"]["score"] == 103

    def test_transform_scores_includes_correct_date(self, sample_scoreboard_data):
        """Test that games include the correct date parameter."""
        test_date = "2026-02-27"
        result = transform_scores(sample_scoreboard_data, test_date)
        assert len(result) > 0
        for game in result:
            assert game["date"] == test_date


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

    def test_transform_boxscore_stint_stats_populated(
        self, sample_scoreboard_data, sample_boxscore_data,
        sample_rotation_data, sample_playbyplay_data
    ):
        """Test that stint stats are populated from PBP events."""
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
        assert "stints" in player
        if len(player["stints"]) > 0:
            stint = player["stints"][0]
            # Verify stint stats have proper structure
            assert "fgm" in stint
            assert "fga" in stint
            assert "pts" in stint
            assert isinstance(stint["fgm"], int)
            assert isinstance(stint["fga"], int)
            assert isinstance(stint["pts"], int)

    def test_transform_boxscore_period_totals_use_team_stats(
        self, sample_scoreboard_data, sample_boxscore_data,
        sample_rotation_data, sample_playbyplay_data
    ):
        """Test that period totals are derived from actual team stats."""
        result = transform_boxscore(
            "0022500001",
            "2026-01-19",
            sample_scoreboard_data,
            sample_boxscore_data,
            sample_rotation_data,
            sample_playbyplay_data,
        )

        period_totals = result["periodTotals"]
        assert "home" in period_totals
        assert "away" in period_totals
        assert len(period_totals["home"]) > 0
        assert len(period_totals["away"]) > 0

        # Verify period totals match team totals
        home_period = period_totals["home"][0]
        away_period = period_totals["away"][0]
        assert home_period["fgm"] == 38  # From sample_boxscore_data
        assert home_period["fga"] == 88
        assert away_period["fgm"] == 33
        assert away_period["fga"] == 83


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


def _cdn_pbp_rows(rows: list[dict]) -> pd.DataFrame:
    """
    Build a play-by-play DataFrame shaped like fetch_playbyplay's CDN output.
    Every column fetch emits is present; rows only need to override what matters.
    """
    base = {
        "PERIOD": 1, "PLAYER1_ID": 0, "PCTIMESTRING": "12:00", "EVENTMSGTYPE": "",
        "EVENTMSGACTIONTYPE": "", "EVENTNUM": 0, "PLAYER1_TEAM_ID": 0,
        "PLAYER1_TEAM_ABBREVIATION": "", "PLAYER1_NAME": "", "HOMEDESCRIPTION": "",
        "VISITORDESCRIPTION": "", "SCORE_HOME": "0", "SCORE_AWAY": "0",
        "_CDN_CLOCK_RAW": "", "_CDN_PERSON_IDS_FILTER": [], "_CDN_QUALIFIERS": [],
        "_CDN_SHOT_RESULT": "", "_CDN_IS_FIELD_GOAL": 0,
        "isFieldGoal": 0, "shotResult": "", "shotValue": 0,
        "_CDN_X_LEGACY": None, "_CDN_Y_LEGACY": None, "_CDN_SHOT_DIST": None,
        "_CDN_AREA": "", "_CDN_AREA_DETAIL": "", "_CDN_SIDE": "", "_CDN_DESCRIPTOR": "",
        "_CDN_ASSIST_ID": None,
    }
    return pd.DataFrame([{**base, **r} for r in rows])


class TestGameflowShotDetail:
    """
    Field-goal events in gameflow.json carry a `shot` object with the CDN's
    court location and context, so downstream shot-zone analysis doesn't
    have to parse "24'" out of the description. Non-shot events don't get one.
    """

    CUNNINGHAM = 203507  # home starter in sample_rotation_data, on court 12:00 → ~1:54 of Q1

    def _events(self, sample_scoreboard_data, sample_rotation_data):
        pbp = _cdn_pbp_rows([
            {
                "EVENTNUM": 2, "PLAYER1_ID": self.CUNNINGHAM, "PCTIMESTRING": "11:30",
                "EVENTMSGTYPE": "2pt", "EVENTMSGACTIONTYPE": "Layup",
                "HOMEDESCRIPTION": "C. Cunningham driving Layup (2 PTS) (Ivey 1 AST)",
                "_CDN_IS_FIELD_GOAL": 1, "_CDN_SHOT_RESULT": "Made",
                "isFieldGoal": 1, "shotResult": "Made", "shotValue": 2,
                "_CDN_X_LEGACY": -12, "_CDN_Y_LEGACY": 31, "_CDN_SHOT_DIST": 3.3,
                "_CDN_AREA": "Restricted Area", "_CDN_AREA_DETAIL": "Center", "_CDN_SIDE": "center",
                "_CDN_DESCRIPTOR": "driving", "_CDN_ASSIST_ID": 1631093,
                "_CDN_QUALIFIERS": ["pointsinthepaint", "fastbreak"],
            },
            {
                "EVENTNUM": 3, "PLAYER1_ID": self.CUNNINGHAM, "PCTIMESTRING": "11:00",
                "EVENTMSGTYPE": "3pt", "EVENTMSGACTIONTYPE": "Jump Shot",
                "HOMEDESCRIPTION": "MISS C. Cunningham 26' step back 3PT",
                "_CDN_IS_FIELD_GOAL": 1, "_CDN_SHOT_RESULT": "Missed",
                "isFieldGoal": 1, "shotResult": "Missed", "shotValue": 3,
                "_CDN_X_LEGACY": 180, "_CDN_Y_LEGACY": 190, "_CDN_SHOT_DIST": float("nan"),
                "_CDN_AREA": "Above the Break 3", "_CDN_AREA_DETAIL": "Right Side Center", "_CDN_SIDE": "right",
                "_CDN_DESCRIPTOR": "step back", "_CDN_ASSIST_ID": float("nan"),
            },
            {
                "EVENTNUM": 4, "PLAYER1_ID": self.CUNNINGHAM, "PCTIMESTRING": "10:30",
                "EVENTMSGTYPE": "rebound", "HOMEDESCRIPTION": "C. Cunningham REBOUND (Off:0 Def:1)",
            },
        ])
        result = transform_gameflow("0022500001", sample_scoreboard_data, sample_rotation_data, pbp)
        player = next(p for p in result["players"] if p["playerId"] == str(self.CUNNINGHAM))
        return player["stints"][0]["events"]

    def test_made_shot_carries_full_shot_detail(self, sample_scoreboard_data, sample_rotation_data):
        events = self._events(sample_scoreboard_data, sample_rotation_data)
        make = next(e for e in events if "driving Layup" in e["description"])
        assert make["shot"] == {
            "x": -12, "y": 31, "dist": 3.3,
            "area": "Restricted Area", "areaDetail": "Center", "side": "center",
            "descriptor": "driving",
            "made": True, "assisted": True,
            "qualifiers": ["pointsinthepaint", "fastbreak"],
        }
        # The three original keys are untouched.
        assert make["clock"] == "11:30"
        assert make["description"] == "C. Cunningham driving Layup (2 PTS) (Ivey 1 AST)"
        assert "type" in make

    def test_missed_shot_reports_unknowns_as_null(self, sample_scoreboard_data, sample_rotation_data):
        events = self._events(sample_scoreboard_data, sample_rotation_data)
        miss = next(e for e in events if "step back 3PT" in e["description"])
        assert miss["shot"]["made"] is False
        assert miss["shot"]["assisted"] is False
        assert miss["shot"]["dist"] is None        # NaN from pandas → null, not 0 and not dropped
        assert miss["shot"]["x"] == 180 and miss["shot"]["y"] == 190
        assert miss["shot"]["qualifiers"] == []
        assert isinstance(miss["shot"]["x"], int)

    def test_non_shot_event_has_no_shot_key(self, sample_scoreboard_data, sample_rotation_data):
        events = self._events(sample_scoreboard_data, sample_rotation_data)
        reb = next(e for e in events if "REBOUND" in e["description"])
        assert "shot" not in reb
        assert set(reb) == {"clock", "type", "description"}

    def test_shot_detail_is_json_serialisable(self, sample_scoreboard_data, sample_rotation_data):
        import json
        events = self._events(sample_scoreboard_data, sample_rotation_data)
        text = json.dumps(events)
        assert "NaN" not in text and "nan" not in text


class TestCdnEventClassification:
    """
    With CDN play-by-play, every attempt used to be classified as a make and
    every rebound as offensive (published data 2026-10-24: FGM == FGA for all
    players, FTM always 0). Both the event labels and the stint stats must
    reflect the feed's shotResult and rebound subType.
    """

    CUNNINGHAM = 203507

    @staticmethod
    def _stint_rows() -> pd.DataFrame:
        pid = TestCdnEventClassification.CUNNINGHAM
        return _cdn_pbp_rows([
            {"EVENTNUM": 1, "PLAYER1_ID": pid, "PCTIMESTRING": "11:30", "EVENTMSGTYPE": "2pt",
             "EVENTMSGACTIONTYPE": "Layup", "HOMEDESCRIPTION": "C. Cunningham driving Layup (2 PTS)",
             "isFieldGoal": 1, "shotResult": "Made", "shotValue": 2, "_CDN_IS_FIELD_GOAL": 1, "_CDN_SHOT_RESULT": "Made"},
            {"EVENTNUM": 2, "PLAYER1_ID": pid, "PCTIMESTRING": "11:00", "EVENTMSGTYPE": "3pt",
             "EVENTMSGACTIONTYPE": "Jump Shot", "HOMEDESCRIPTION": "MISS C. Cunningham 26' 3PT",
             "isFieldGoal": 1, "shotResult": "Missed", "shotValue": 3, "_CDN_IS_FIELD_GOAL": 1, "_CDN_SHOT_RESULT": "Missed"},
            {"EVENTNUM": 3, "PLAYER1_ID": pid, "PCTIMESTRING": "10:30", "EVENTMSGTYPE": "freethrow",
             "EVENTMSGACTIONTYPE": "Free Throw 1 of 2", "HOMEDESCRIPTION": "C. Cunningham Free Throw 1 of 2 (3 PTS)",
             "shotResult": "Made", "shotValue": 1},
            {"EVENTNUM": 4, "PLAYER1_ID": pid, "PCTIMESTRING": "10:30", "EVENTMSGTYPE": "freethrow",
             "EVENTMSGACTIONTYPE": "Free Throw 2 of 2", "HOMEDESCRIPTION": "MISS C. Cunningham Free Throw 2 of 2",
             "shotResult": "Missed", "shotValue": 1},
            {"EVENTNUM": 5, "PLAYER1_ID": pid, "PCTIMESTRING": "10:00", "EVENTMSGTYPE": "rebound",
             "EVENTMSGACTIONTYPE": "offensive", "HOMEDESCRIPTION": "C. Cunningham REBOUND (Off:1 Def:0)"},
            # Running totals in the description still say Off:1 — this one is defensive.
            {"EVENTNUM": 6, "PLAYER1_ID": pid, "PCTIMESTRING": "9:00", "EVENTMSGTYPE": "rebound",
             "EVENTMSGACTIONTYPE": "defensive", "HOMEDESCRIPTION": "C. Cunningham REBOUND (Off:1 Def:1)"},
        ])

    def test_stint_stats_count_misses_as_misses(self):
        stats = _aggregate_stint_stats(self._stint_rows())
        assert (stats["fgm"], stats["fga"]) == (1, 2)
        assert (stats["fg3m"], stats["fg3a"]) == (0, 1)
        assert (stats["ftm"], stats["fta"]) == (1, 2)
        assert stats["pts"] == 3
        assert (stats["oreb"], stats["reb"]) == (1, 2)

    def test_event_types_distinguish_make_miss_and_rebound_kind(self, sample_scoreboard_data, sample_rotation_data):
        result = transform_gameflow("0022500001", sample_scoreboard_data, sample_rotation_data, self._stint_rows())
        player = next(p for p in result["players"] if p["playerId"] == str(self.CUNNINGHAM))
        types = [e["type"] for e in player["stints"][0]["events"]]
        assert types == ["Make2", "miss3", "MakeFT", "missFT", "OffReb", "DefReb"]


class TestShotZones:
    """
    The CDN play-by-play leaves `area`/`areaDetail` blank (observed on every
    shot of 0022600001, 2026-10-24), so they're derived from x/y/distance
    using the NBA's shot-chart zone definitions. Coordinates are legacy
    tenths of a foot, basket at the origin, y into the court.
    """

    def test_restricted_area_covers_layups_and_dunks(self):
        assert shot_area(x=10, y=20, dist=2.2, shot_value=2, side="center") == "Restricted Area"
        # The feed reports dunks and layups at 4.1–4.8 ft (0022600001: "J. Duren DUNK" at
        # 4.6 ft, x=46 y=7), so the cutoff is 5 ft, not the shot chart's nominal 4.
        assert shot_area(x=46, y=7, dist=4.6, shot_value=2, side="right") == "Restricted Area"
        assert shot_area(x=-2, y=60, dist=6.0, shot_value=2, side="center") == "In The Paint (Non-RA)"

    def test_putbacks_slightly_behind_the_basket_are_restricted_area(self):
        assert shot_area(x=-21, y=-12, dist=2.5, shot_value=2, side="left") == "Restricted Area"

    def test_paint_outside_restricted_area(self):
        # Paint is 16 ft wide (±8 ft) and runs to the free-throw line, 13.75 ft from the basket.
        assert shot_area(x=60, y=110, dist=12.5, shot_value=2, side="right") == "In The Paint (Non-RA)"

    def test_two_pointer_outside_paint_is_mid_range(self):
        assert shot_area(x=150, y=100, dist=18.0, shot_value=2, side="right") == "Mid-Range"
        assert shot_area(x=0, y=200, dist=20.0, shot_value=2, side="center") == "Mid-Range"

    def test_corner_threes_come_from_x_sign_not_the_feed_side(self):
        """
        The feed's `side` is which end of the floor the team is attacking that
        half (same value for every shot a team takes in Q1–Q2, mirrored in
        Q3–Q4; verified on 0022600001/2/3). xLegacy is measured from the
        basket being attacked and does not flip, and the NBA convention is
        x < 0 = Left Corner 3, x > 0 = Right Corner 3.
        """
        assert shot_area(x=230, y=10, dist=23.0, shot_value=3, side="left") == "Right Corner 3"
        assert shot_area(x=-230, y=10, dist=23.0, shot_value=3, side="right") == "Left Corner 3"
        # D. Robinson 24' 3PT in 0022600001: x=241 y=53 (side happened to agree).
        assert shot_area(x=241, y=53, dist=24.661, shot_value=3, side="right") == "Right Corner 3"
        assert shot_area(x=-235, y=40, dist=23.8, shot_value=3, side="") == "Left Corner 3"

    def test_corner_labels_within_a_game_are_not_determined_by_period(self, sample_scoreboard_data, sample_rotation_data):
        """
        A team shoots from both corners in the same half. If the label leaked
        from `side`, every corner three in a half would carry the same label.
        """
        pid = TestCdnEventClassification.CUNNINGHAM  # on court all of Q1 in the fixture
        def corner(num, clock, x):
            return {"EVENTNUM": num, "PLAYER1_ID": pid, "PERIOD": 1, "PCTIMESTRING": clock,
                    "EVENTMSGTYPE": "3pt", "HOMEDESCRIPTION": "C. Cunningham 23' 3PT (3 PTS)",
                    "isFieldGoal": 1, "shotResult": "Made", "shotValue": 3,
                    "_CDN_IS_FIELD_GOAL": 1, "_CDN_SHOT_RESULT": "Made",
                    "_CDN_X_LEGACY": x, "_CDN_Y_LEGACY": 20, "_CDN_SHOT_DIST": 23.1, "_CDN_SIDE": "right"}
        pbp = _cdn_pbp_rows([corner(1, "11:00", 230), corner(2, "10:00", -230), corner(3, "9:00", 225)])
        result = transform_gameflow("0022500001", sample_scoreboard_data, sample_rotation_data, pbp)
        player = next(p for p in result["players"] if p["playerId"] == str(pid))
        labels = {e["shot"]["area"] for e in player["stints"][0]["events"] if "shot" in e}
        assert labels == {"Left Corner 3", "Right Corner 3"}

    def test_threes_above_the_corner_are_above_the_break(self):
        # x=100 y=242 (the pullup 26' 3PT in the same game).
        assert shot_area(x=100, y=242, dist=26.167, shot_value=3, side="right") == "Above the Break 3"
        assert shot_area(x=0, y=260, dist=26.0, shot_value=3, side="center") == "Above the Break 3"

    def test_heaves_are_backcourt(self):
        assert shot_area(x=50, y=520, dist=52.0, shot_value=3, side="center") == "Backcourt"

    def test_unknown_when_location_missing(self):
        assert shot_area(x=None, y=None, dist=None, shot_value=3, side="") == ""

    def test_distance_bands(self):
        assert shot_area_detail(dist=2.0) == "<8 ft"
        assert shot_area_detail(dist=8.0) == "8-16 ft"
        assert shot_area_detail(dist=15.9) == "8-16 ft"
        assert shot_area_detail(dist=16.0) == "16-24 ft"
        assert shot_area_detail(dist=24.0) == "24+ ft"
        assert shot_area_detail(dist=48.0) == "Backcourt"
        assert shot_area_detail(dist=None) == ""

    def test_shot_detail_uses_feed_values_when_present_and_derives_otherwise(self):
        base = {"_CDN_IS_FIELD_GOAL": 1, "_CDN_SHOT_RESULT": "Made", "shotValue": 3,
                "_CDN_X_LEGACY": 241, "_CDN_Y_LEGACY": 53, "_CDN_SHOT_DIST": 24.661, "_CDN_SIDE": "right"}
        derived = _shot_detail(pd.Series({**base, "_CDN_AREA": "", "_CDN_AREA_DETAIL": ""}))
        assert (derived["area"], derived["areaDetail"]) == ("Right Corner 3", "24+ ft")
        from_feed = _shot_detail(pd.Series({**base, "_CDN_AREA": "Feed Zone", "_CDN_AREA_DETAIL": "Feed Range"}))
        assert (from_feed["area"], from_feed["areaDetail"]) == ("Feed Zone", "Feed Range")
