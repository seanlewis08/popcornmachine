# Popcorn Remake Implementation Plan

**Goal:** Build a zero-cost NBA game stats viewer with a Python data pipeline and Vite React SPA, deployed via GitHub Pages.

**Architecture:** Python pipeline fetches post-game data from `nba_api`, pre-computes derived metrics, and commits structured JSON files to the repo. A Vite React SPA reads those JSON files at runtime to render three views: home/scores, box score, and gameflow. GitHub Pages serves both the app and data files.

**Tech Stack:** Python 3.11+ (uv), nba_api, Vite, React 18, TypeScript, Tailwind CSS v4, shadcn/ui, React Router v7, Vitest, GitHub Actions, GitHub Pages

**Scope:** 7 phases from original design (phases 1-7)

**Codebase verified:** 2026-02-26 — greenfield project. Phase 1 creates pyproject.toml, pipeline/, web/, data/ fixtures.

---

## Acceptance Criteria Coverage

This phase implements and tests:

### popcorn-remake.AC1: Home/Scores page shows game results
- **popcorn-remake.AC1.1 Success:** Page lists games grouped by date, most recent first
- **popcorn-remake.AC1.2 Success:** Each game shows both team names and final scores

### popcorn-remake.AC2: Box Score page shows complete player stats
- **popcorn-remake.AC2.3 Success:** Per-stint breakdowns expand when clicking a player row

### popcorn-remake.AC3: Gameflow page shows interactive rotation timeline
- **popcorn-remake.AC3.3 Success:** Clicking/hovering a stint shows stats and play-by-play events

---

## Phase 2: Python Data Pipeline — Fetch & Transform

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->
<!-- START_TASK_1 -->
### Task 1: Fetch module — nba_api client with rate limiting

**Verifies:** popcorn-remake.AC1.1, popcorn-remake.AC1.2 (pipeline produces score data grouped by date with team names)

**Files:**
- Create: `pipeline/fetch.py`
- Create: `tests/conftest.py`

**Implementation:**

Create `pipeline/fetch.py` with functions that call `nba_api` endpoints and return raw DataFrames. Each function accepts an optional `delay` parameter (default 1.5 seconds) for rate limiting.

Functions to implement:
- `fetch_scoreboard(game_date: str, delay: float = 1.5) -> dict` — Calls `scoreboardv2.ScoreBoardV2(game_date=game_date, day_offset=0, league_id="00")`. Returns dict with `game_header` and `line_score` DataFrames. Key columns: `GAME_ID`, `HOME_TEAM_ID`, `VISITOR_TEAM_ID`, `GAME_STATUS_TEXT` from GameHeader; `TEAM_ID`, `TEAM_ABBREVIATION`, `TEAM_NAME`, `PTS` from LineScore.
- `fetch_boxscore(game_id: str, delay: float = 1.5) -> dict` — Calls `boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id, start_period=1, end_period=10, start_range=0, end_range=0, range_type=0)`. Returns dict with `player_stats` and `team_stats` DataFrames. Key columns: `PLAYER_ID`, `PLAYER_NAME`, `TEAM_ABBREVIATION`, `MIN`, `FGM`, `FGA`, `FG3M`, `FG3A`, `FTM`, `FTA`, `OREB`, `DREB`, `REB`, `AST`, `STL`, `BLK`, `TO`, `PF`, `PTS`, `PLUS_MINUS`.
- `fetch_playbyplay(game_id: str, delay: float = 1.5) -> pd.DataFrame` — Calls `playbyplayv2.PlayByPlayV2(game_id=game_id, start_period=1, end_period=10)`. Returns DataFrame. Key columns: `EVENTNUM`, `EVENTMSGTYPE`, `EVENTMSGACTIONTYPE`, `PERIOD`, `PCTIMESTRING`, `HOMEDESCRIPTION`, `VISITORDESCRIPTION`, `PLAYER1_ID`, `PLAYER1_TEAM_ABBREVIATION`, `SCORE`.
- `fetch_game_rotation(game_id: str, delay: float = 1.5) -> dict` — Calls `gamerotation.GameRotation(game_id=game_id, league_id="00")`. Returns dict with `away_team` and `home_team` DataFrames. Key columns: `PERSON_ID`, `PLAYER_FIRST`, `PLAYER_LAST`, `IN_TIME_REAL`, `OUT_TIME_REAL`, `PLAYER_PTS`, `PT_DIFF`.

Each function sleeps `delay` seconds before making the API call. Each wraps the call in try/except for `requests.exceptions.RequestException` and returns None on failure (logged to stderr).

Also create `tests/conftest.py` with sample DataFrames that mirror the nba_api response structures — these fixtures will be reused across all test files.

**Testing:**
Tests must verify:
- popcorn-remake.AC1.1: fetch_scoreboard returns data with date-grouped game records
- popcorn-remake.AC1.2: fetch_scoreboard response includes team abbreviations and scores in LineScore

Follow project testing patterns. Test with mocked nba_api calls (monkeypatch the endpoint class constructors to return fixture DataFrames).

**Verification:**
Run: `uv run pytest tests/ -v`
Expected: All tests pass

**Commit:** `feat: add nba_api fetch module with rate limiting`
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Transform module — map API data to JSON contracts

**Verifies:** popcorn-remake.AC1.1, popcorn-remake.AC1.2, popcorn-remake.AC2.3, popcorn-remake.AC3.3

**Files:**
- Create: `pipeline/transform.py`

**Implementation:**

Create `pipeline/transform.py` with functions that transform raw nba_api DataFrames into the JSON contract structures defined in the design plan.

Functions to implement:

`transform_scores(scoreboard_data: dict) -> list[dict]` — Transforms ScoreBoardV2 response into the `scores/YYYY-MM-DD.json` contract. Maps `TEAM_ABBREVIATION` to `tricode`, `TEAM_NAME` to `name`, `PTS` to `score`. Pairs home and away teams by `GAME_ID`.

`transform_boxscore(game_id: str, date: str, scoreboard_data: dict, boxscore_data: dict, rotation_data: dict, pbp_data: pd.DataFrame) -> dict` — Transforms into the `boxscore.json` contract. For each player:
  - Extracts full-game totals from BoxScoreTraditionalV2 player stats
  - Computes derived metrics: `hv = REB + AST + BLK + STL - TO`, `prod = (PTS + hv) / MIN` (0 if MIN is 0), `eff = (PTS + REB + AST + STL + BLK - (FGA - FGM) - (FTA - FTM) - TO)`
  - Builds per-stint breakdowns by cross-referencing GameRotation stint windows with PlayByPlayV2 events:
    - For each stint (defined by `IN_TIME_REAL`/`OUT_TIME_REAL` from rotation data), filter PBP events that fall within that stint's time window and involve this player
    - Aggregate PBP events into per-stint stats (FGM, FGA, FG3M, etc.) using EVENTMSGTYPE codes: 1=made FG, 2=missed FG, 3=free throw, 4=rebound, 5=turnover, 6=foul, etc.
    - Convert rotation timestamps to period + clock format for the JSON contract
  - Builds team totals and period totals from the BoxScoreTraditionalV2 team stats DataFrame

`transform_gameflow(game_id: str, scoreboard_data: dict, rotation_data: dict, pbp_data: pd.DataFrame) -> dict` — Transforms into the `gameflow.json` contract. For each player stint from rotation data, attaches filtered PBP events and per-stint stat summaries. Converts timestamps to period + clock format.

Helper functions:
- `_rotation_time_to_period_clock(in_time_real: int, out_time_real: int) -> tuple[int, str, str]` — Converts millisecond timestamps to (period, in_clock, out_clock) format. Each regulation period is 720 seconds (12 minutes). Period 1 starts at t=0, Period 2 at t=720000ms, etc.
- `_compute_stint_minutes(in_time_real: int, out_time_real: int) -> float` — Computes stint duration in minutes.
- `_filter_pbp_for_stint(pbp_df: pd.DataFrame, player_id: int, period: int, in_clock: str, out_clock: str) -> pd.DataFrame` — Filters PBP events by player and time window.
- `_aggregate_stint_stats(pbp_events: pd.DataFrame) -> dict` — Counts stat categories from PBP event types.
- `_pbp_event_to_type(event_msg_type: int, event_msg_action_type: int) -> str` — Maps EVENTMSGTYPE codes to human-readable event types (e.g., "make2", "miss3", "fta", "reb", "tov", "foul").

**Testing:**
Tests must verify each AC:
- popcorn-remake.AC1.1: transform_scores groups games by date correctly
- popcorn-remake.AC1.2: transform_scores output includes team names (tricode + full name) and final scores for each game
- popcorn-remake.AC2.3: transform_boxscore produces per-stint breakdowns with correct stats for each player stint
- popcorn-remake.AC3.3: transform_gameflow produces stint entries with stats summaries and play-by-play events attached

Additional test: derived metric calculations (hv, prod, eff) produce correct values for known inputs.

**Verification:**
Run: `uv run pytest tests/ -v`
Expected: All tests pass

**Commit:** `feat: add transform module mapping nba_api data to JSON contracts`
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Write module and main orchestrator

**Verifies:** popcorn-remake.AC1.1, popcorn-remake.AC1.2

**Files:**
- Create: `pipeline/write.py`
- Modify: `pipeline/main.py` (replace placeholder)

**Implementation:**

Create `pipeline/write.py` with functions that write transformed data to the JSON file structure:

`write_index(dates_data: list[dict], data_dir: str = "data") -> None` — Writes/updates `data/index.json`. Reads existing index if present, merges new dates (replacing existing entries for same date), sorts dates descending (most recent first), writes atomically.

`write_scores(date: str, scores: list[dict], data_dir: str = "data") -> None` — Writes `data/scores/YYYY-MM-DD.json`. Creates directory if needed.

`write_game_data(game_id: str, boxscore: dict, gameflow: dict, data_dir: str = "data") -> None` — Writes `data/games/{gameId}/boxscore.json` and `data/games/{gameId}/gameflow.json`. Creates directory if needed.

All write functions use `json.dump` with `indent=2` for readability and write to a temp file first, then rename (atomic write).

Update `pipeline/main.py` to orchestrate the full pipeline:

```python
def main(date: str | None = None, data_dir: str = "data") -> None:
    """Run the pipeline for a given date (defaults to yesterday)."""
    if date is None:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # 1. Fetch scoreboard for the date
    scoreboard = fetch_scoreboard(date)
    if scoreboard is None:
        print(f"No scoreboard data for {date}")
        return

    # 2. Transform scores
    scores = transform_scores(scoreboard)
    if not scores:
        print(f"No games found for {date}")
        return

    # 3. For each game, fetch detailed data and transform
    for game in scores:
        game_id = game["gameId"]
        boxscore_raw = fetch_boxscore(game_id)
        pbp_raw = fetch_playbyplay(game_id)
        rotation_raw = fetch_game_rotation(game_id)

        if any(d is None for d in [boxscore_raw, pbp_raw, rotation_raw]):
            print(f"Skipping game {game_id}: incomplete data")
            continue

        boxscore = transform_boxscore(game_id, date, scoreboard, boxscore_raw, rotation_raw, pbp_raw)
        gameflow = transform_gameflow(game_id, scoreboard, rotation_raw, pbp_raw)

        write_game_data(game_id, boxscore, gameflow, data_dir)

    # 4. Write scores and index
    write_scores(date, scores, data_dir)
    # Build index entry
    index_entry = {
        "date": date,
        "games": [{"gameId": g["gameId"], "home": g["homeTeam"]["tricode"],
                    "away": g["awayTeam"]["tricode"], "homeScore": g["homeTeam"]["score"],
                    "awayScore": g["awayTeam"]["score"]} for g in scores]
    }
    write_index([index_entry], data_dir)
```

Accept `--date YYYY-MM-DD` and `--data-dir` CLI arguments via `argparse`.

**Testing:**
Tests must verify:
- popcorn-remake.AC1.1: write_index produces index.json with dates sorted most-recent-first
- popcorn-remake.AC1.2: write_scores produces valid JSON with team names and scores
- write_game_data creates correct directory structure and valid JSON files
- main orchestrator calls fetch/transform/write in correct order (integration test with mocked fetch functions)

**Verification:**
Run: `uv run pytest tests/ -v`
Expected: All tests pass

**Commit:** `feat: add write module and main pipeline orchestrator`
<!-- END_TASK_3 -->
<!-- END_SUBCOMPONENT_A -->
