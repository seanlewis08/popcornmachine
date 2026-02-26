# Popcorn Remake Design

## Summary

Popcorn Remake is a zero-cost, client-side web application for browsing NBA game statistics and player rotation timelines. The system comprises two components living in a single GitHub repository: a Python data pipeline that fetches post-game data from `nba_api` and commits structured JSON files on a scheduled basis, and a React single-page application (SPA) that reads those JSON files at runtime to render three core views—a home page listing game scores by date, a box score page showing full player statistics with per-stint breakdowns, and an interactive gameflow page visualizing player rotations across game quarters.

The implementation strategy is deliberate in its simplicity. Rather than maintaining a database or backend server, the pipeline pre-computes all derived metrics (rebound value, productivity, efficiency) and stores them alongside raw stats in JSON files, allowing the frontend to be entirely static and deployed via GitHub Pages. Data retention is automated monthly to keep the repository lean. This approach eliminates infrastructure costs while keeping deployment straightforward: updates to the main branch trigger an automatic rebuild and redeploy.

## Definition of Done

A working website shared with friends that provides three core views for NBA games:

1. **Home/Scores page** listing today's and recent days' NBA game scores with links to game details
2. **Box Score page** per game showing full player stats with per-stint breakdowns (minutes, FG, 3PT, FT, rebounds, assists, blocks, steals, turnovers, fouls, points, +/-, efficiency metrics)
3. **Modernized Gameflow page** showing player rotation timelines with play-by-play events — redesigned from PopcornMachine's horizontal bar style into an interactive, modern UI

Powered by a Python data pipeline (managed by `uv`) pulling from `nba_api` post-game, generating JSON files committed to a GitHub repo. Frontend is a Vite React SPA served from GitHub Pages. No database, no external hosting. Total cost: $0/month.

## Acceptance Criteria

### popcorn-remake.AC1: Home/Scores page shows game results
- **popcorn-remake.AC1.1 Success:** Page lists games grouped by date, most recent first
- **popcorn-remake.AC1.2 Success:** Each game shows both team names and final scores
- **popcorn-remake.AC1.3 Success:** Each game card links to box score and gameflow pages
- **popcorn-remake.AC1.4 Failure:** Missing date file shows graceful empty state (not a crash)

### popcorn-remake.AC2: Box Score page shows complete player stats
- **popcorn-remake.AC2.1 Success:** All stat columns render (Min, FG, 3PT, FT, Reb, Ast, Blk, Stl, TO, PF, Pts, +/-)
- **popcorn-remake.AC2.2 Success:** Derived metrics (hv, prod, eff) display correctly for each player
- **popcorn-remake.AC2.3 Success:** Per-stint breakdowns expand when clicking a player row
- **popcorn-remake.AC2.4 Success:** Team totals row shows aggregate stats
- **popcorn-remake.AC2.5 Success:** Period breakdown rows show per-quarter stats for each team
- **popcorn-remake.AC2.6 Failure:** Invalid game ID shows error state (not a crash)

### popcorn-remake.AC3: Gameflow page shows interactive rotation timeline
- **popcorn-remake.AC3.1 Success:** Each player has a horizontal timeline lane across four quarters
- **popcorn-remake.AC3.2 Success:** Stints are color-coded by team
- **popcorn-remake.AC3.3 Success:** Clicking/hovering a stint shows stats and play-by-play events
- **popcorn-remake.AC3.4 Success:** Timeline aligns correctly across players for the same time periods
- **popcorn-remake.AC3.5 Failure:** Game with no gameflow data shows graceful fallback

### popcorn-remake.AC4: Data pipeline maintains current-month data
- **popcorn-remake.AC4.1 Success:** Pipeline purges data from previous months
- **popcorn-remake.AC4.2 Success:** Re-running pipeline for same date produces identical JSON
- **popcorn-remake.AC4.3 Failure:** API unavailability doesn't corrupt existing data files

### popcorn-remake.AC5: Automated deployment via GitHub
- **popcorn-remake.AC5.1 Success:** Pipeline runs on cron schedule and commits new data
- **popcorn-remake.AC5.2 Success:** Site auto-deploys when main branch is updated
- **popcorn-remake.AC5.3 Success:** GitHub Pages serves both the app and JSON data files

## Glossary

- **nba_api**: A Python library providing HTTP client methods to fetch NBA game data from NBA.com endpoints (Scoreboard, BoxScoreV2, PlayByPlayV2, GameRotation).
- **Vite**: A modern JavaScript build tool and dev server used to bundle and optimize the React application for production.
- **React Router**: A library providing client-side navigation and URL routing for the three pages (home, box score, gameflow).
- **Hash routing**: A URL pattern (`/#/game/:gameId/boxscore`) that routes entirely in the browser without server-side rewriting, required because GitHub Pages serves static files only.
- **GitHub Actions**: An automation platform that runs the Python pipeline on a schedule and rebuilds/redeploys the React app when code is pushed.
- **GitHub Pages**: A static hosting service that serves both the built React application and the `data/` directory of JSON files.
- **shadcn/ui**: A component library built on Radix UI and Tailwind CSS, providing pre-styled UI elements for React.
- **Tailwind CSS**: A utility-first CSS framework used for styling the React application.
- **Stints**: Periods during which a single player remains on the court; each stint has an in-time, out-time, and associated statistics.
- **Box Score**: A tabular display of individual player and team statistics for a completed game.
- **Gameflow**: A visual timeline representation of player rotations and play-by-play events across the four quarters of a game.
- **Derived metrics**: Statistics computed from raw box score data—hv (helper value: Reb+Ast+Blk+Stl-TO), prod (productivity: (Pts+hv)/Min), and eff (efficiency: standard NBA calculation).
- **Rate limiting**: A technique to prevent server overload by spacing out HTTP requests; the pipeline uses 1-2 second delays between `nba_api` calls.
- **Idempotent**: A property of the pipeline ensuring that running it multiple times for the same date produces identical JSON output.
- **Monorepo**: A single repository containing both the Python pipeline and React application code.

## Architecture

Two components in a single GitHub repository:

**Python Data Pipeline** — A standalone script managed by `uv`. Runs on a GitHub Actions cron schedule (6 AM and 2 PM UTC). Calls `nba_api` endpoints (Scoreboard, BoxScoreV2, PlayByPlayV2, GameRotation) with 1-2 second delays between calls to respect NBA.com rate limits. Transforms responses into structured JSON files, pre-computes derived metrics (hv, prod, eff), and commits updated files to the repo. Cleans up data from previous months.

**Vite React SPA** — A client-side React app built with Vite, styled with Tailwind CSS and shadcn/ui. Three routes via React Router (hash routing for GitHub Pages compatibility): home/scores, box score, and gameflow. Reads committed JSON files as static assets at runtime. No API routes, no server-side rendering, no database.

**Data flow:** `nba_api` → Python pipeline → JSON files in repo → GitHub Actions commit & push → GitHub Pages redeploys → React app fetches JSON in browser.

### Data Storage: JSON File Structure

```
data/
  index.json                          # manifest of available dates and game IDs
  scores/
    YYYY-MM-DD.json                   # array of game scores for that date
  games/
    {gameId}/
      boxscore.json                   # both teams' player stats + per-stint breakdowns
      gameflow.json                   # player stint timelines + play-by-play events per stint
```

Derived metrics (hv = Reb+Ast+Blk+Stl-TO, prod = (Pts+hv)/Min, eff = standard NBA efficiency) are pre-computed by the pipeline and embedded in JSON.

### API Contracts

**`data/index.json`:**
```json
{
  "dates": [
    {
      "date": "2026-01-19",
      "games": [
        { "gameId": "0022500001", "home": "DET", "away": "BOS", "homeScore": 104, "awayScore": 103 }
      ]
    }
  ]
}
```

**`data/scores/YYYY-MM-DD.json`:**
```json
[
  {
    "gameId": "0022500001",
    "date": "2026-01-19",
    "homeTeam": { "tricode": "DET", "name": "Detroit Pistons", "score": 104 },
    "awayTeam": { "tricode": "BOS", "name": "Boston Celtics", "score": 103 },
    "status": "Final"
  }
]
```

**`data/games/{gameId}/boxscore.json`:**
```json
{
  "gameId": "0022500001",
  "date": "2026-01-19",
  "homeTeam": { "tricode": "DET", "name": "Detroit Pistons", "score": 104 },
  "awayTeam": { "tricode": "BOS", "name": "Boston Celtics", "score": 103 },
  "players": [
    {
      "playerId": "1234",
      "name": "C Cunningham",
      "team": "DET",
      "totals": {
        "min": 40.3, "fgm": 4, "fga": 17, "fg3m": 0, "fg3a": 4,
        "ftm": 8, "fta": 10, "oreb": 1, "reb": 3, "ast": 14,
        "blk": 2, "stl": 1, "tov": 0, "pf": 3, "pts": 16,
        "plusMinus": 2, "hv": 20, "prod": 0.89, "eff": 21
      },
      "stints": [
        {
          "period": 1, "inTime": "12:00", "outTime": "1:54",
          "minutes": 10.1, "plusMinus": -4,
          "fgm": 0, "fga": 4, "fg3m": 0, "fg3a": 1,
          "ftm": 3, "fta": 4, "oreb": 1, "reb": 1,
          "ast": 3, "blk": 0, "stl": 0, "tov": 0, "pf": 1, "pts": 3
        }
      ]
    }
  ],
  "teamTotals": {
    "home": { "fgm": 38, "fga": 88, "fg3m": 11, "fg3a": 33, "ftm": 17, "fta": 23, "oreb": 9, "reb": 40, "ast": 24, "blk": 9, "stl": 9, "tov": 5, "pf": 26, "pts": 104 },
    "away": { "fgm": 33, "fga": 83, "fg3m": 13, "fg3a": 41, "ftm": 24, "fta": 30, "oreb": 16, "reb": 47, "ast": 13, "blk": 4, "stl": 5, "tov": 11, "pf": 26, "pts": 103 }
  },
  "periodTotals": {
    "home": [
      { "period": 1, "fgm": 8, "fga": 24, "fg3m": 1, "fg3a": 7, "ftm": 9, "fta": 12, "pts": 26 }
    ],
    "away": [
      { "period": 1, "fgm": 9, "fga": 25, "fg3m": 4, "fg3a": 12, "ftm": 7, "fta": 8, "pts": 29 }
    ]
  }
}
```

**`data/games/{gameId}/gameflow.json`:**
```json
{
  "gameId": "0022500001",
  "homeTeam": { "tricode": "DET", "name": "Detroit Pistons" },
  "awayTeam": { "tricode": "BOS", "name": "Boston Celtics" },
  "players": [
    {
      "playerId": "1234",
      "name": "C Cunningham",
      "team": "DET",
      "stints": [
        {
          "period": 1, "inTime": "12:00", "outTime": "1:54",
          "minutes": 10.1, "plusMinus": -4,
          "stats": { "fgm": 0, "fga": 4, "fg3m": 0, "fg3a": 1, "ftm": 3, "fta": 4, "pts": 3, "ast": 3, "reb": 1, "stl": 0, "blk": 0, "tov": 0, "pf": 1 },
          "events": [
            { "clock": "10:30", "type": "miss2", "description": "Missed 2PT" },
            { "clock": "08:15", "type": "fta", "description": "Free Throw Made" }
          ]
        }
      ]
    }
  ]
}
```

## Existing Patterns

This is a greenfield project — no existing codebase. The design draws from PopcornMachine.net's data model (game scores, box scores with stint breakdowns, gameflow rotation timelines) but reimplements the presentation layer entirely.

The JSON file structure mirrors the three HTML pages from the reference site: `home.html` maps to `scores/`, `box_score.html` maps to `boxscore.json`, and `gameflow.html` maps to `gameflow.json`.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Project Scaffolding
**Goal:** Initialize the monorepo with Python pipeline and Vite React app side by side.

**Components:**
- Root `pyproject.toml` with `uv` configuration and `nba_api` dependency
- Vite + React + TypeScript project in `web/`
- Tailwind CSS and shadcn/ui setup in `web/`
- React Router with hash routing in `web/src/`
- `data/` directory with sample JSON fixtures for development
- GitHub Actions workflow stubs (pipeline + deploy)

**Dependencies:** None (first phase)

**Done when:** `uv sync` installs Python dependencies, `npm run dev` serves the React app, `npm run build` produces a `dist/` folder, sample JSON loads in the browser
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Python Data Pipeline — Fetch & Transform
**Goal:** Python script that pulls NBA game data and writes structured JSON files.

**Components:**
- Pipeline script in `pipeline/` — orchestrates fetch, transform, and write stages
- Fetch module — calls `nba_api` Scoreboard, BoxScoreV2, PlayByPlayV2, GameRotation with rate-limiting delays
- Transform module — maps `nba_api` response formats to the JSON contracts defined above, pre-computes derived metrics (hv, prod, eff), associates play-by-play events with stints
- Write module — generates `data/index.json`, `data/scores/YYYY-MM-DD.json`, `data/games/{gameId}/boxscore.json`, `data/games/{gameId}/gameflow.json`

**Dependencies:** Phase 1 (project setup, `uv` configured)

**Done when:** Running `uv run pipeline/main.py` fetches real NBA game data and produces valid JSON files matching the contracts above. Tests verify JSON structure and derived metric calculations.

**Covers:** popcorn-remake.AC1.1, popcorn-remake.AC1.2, popcorn-remake.AC2.3, popcorn-remake.AC3.3
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Home/Scores Page
**Goal:** React page displaying game scores grouped by date.

**Components:**
- Scores page component in `web/src/pages/` — fetches `index.json` and date-specific score files
- Game card component — displays team names, scores, final status, links to box score and gameflow
- Date grouping layout — most recent date first

**Dependencies:** Phase 1 (React app), Phase 2 (JSON data files)

**Done when:** Home page loads, shows game scores grouped by date, each game links to `/game/:gameId/boxscore` and `/game/:gameId/gameflow`. Tests verify rendering with fixture data.

**Covers:** popcorn-remake.AC1.1, popcorn-remake.AC1.2, popcorn-remake.AC1.3
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Box Score Page
**Goal:** React page showing full player stats with expandable per-stint breakdowns.

**Components:**
- Box score page component in `web/src/pages/` — fetches `boxscore.json` for the game
- Player stats table component — renders all stat columns (Min, FG, 3PT, FT, Reb, Ast, Blk, Stl, TO, PF, Pts, hv, prod, eff, +/-)
- Expandable stint rows — click a player to reveal per-stint stat breakdown
- Team totals and period breakdown rows
- Two tables (one per team) with team headers

**Dependencies:** Phase 1 (React app), Phase 2 (JSON data)

**Done when:** Box score page renders both teams' stats, per-stint rows expand/collapse, team totals and period breakdowns display correctly. Tests verify stat rendering and interaction.

**Covers:** popcorn-remake.AC2.1, popcorn-remake.AC2.2, popcorn-remake.AC2.3, popcorn-remake.AC2.4, popcorn-remake.AC2.5
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Gameflow Page
**Goal:** Interactive modernized gameflow visualization showing player rotation timelines.

**Components:**
- Gameflow page component in `web/src/pages/` — fetches `gameflow.json` for the game
- Timeline visualization — horizontal lanes per player, divided by quarter, stint segments color-coded by team
- Stint detail card — hover or click a stint to show stats summary and play-by-play events
- Player name labels along the left axis, quarter dividers along the top

**Dependencies:** Phase 1 (React app), Phase 2 (JSON data)

**Done when:** Gameflow page renders player rotation timelines across four quarters, stints are visually distinct, clicking a stint shows its stats and play-by-play. Tests verify timeline rendering and interaction.

**Covers:** popcorn-remake.AC3.1, popcorn-remake.AC3.2, popcorn-remake.AC3.3, popcorn-remake.AC3.4
<!-- END_PHASE_5 -->

<!-- START_PHASE_6 -->
### Phase 6: Monthly Cleanup & Pipeline Hardening
**Goal:** Automated data retention and pipeline resilience.

**Components:**
- Cleanup logic in pipeline — deletes `data/scores/` and `data/games/` entries for dates outside current month, updates `data/index.json`
- Idempotent writes — pipeline overwrites existing JSON files safely on re-run
- Error handling — graceful failure when `nba_api` is unavailable or rate-limited, logging of failures

**Dependencies:** Phase 2 (pipeline)

**Done when:** Pipeline purges old data, re-running for the same date produces identical output, API failures don't corrupt existing data. Tests verify cleanup logic and idempotency.

**Covers:** popcorn-remake.AC4.1, popcorn-remake.AC4.2, popcorn-remake.AC4.3
<!-- END_PHASE_6 -->

<!-- START_PHASE_7 -->
### Phase 7: GitHub Actions & Deployment
**Goal:** Automated data pipeline scheduling and GitHub Pages deployment.

**Components:**
- GitHub Actions workflow for pipeline — cron at 6 AM and 2 PM UTC, installs `uv`, runs pipeline, commits and pushes changes if data updated
- GitHub Actions workflow for deployment — triggered on push to main, builds Vite app, copies `data/` into `dist/data/`, deploys to GitHub Pages
- Environment configuration — `uv.lock` committed for reproducible Python builds

**Dependencies:** Phase 2 (pipeline), Phase 1 (React app build)

**Done when:** Pipeline runs on schedule and commits new data, site auto-deploys when data is pushed, GitHub Pages serves the app and JSON files.

**Covers:** popcorn-remake.AC5.1, popcorn-remake.AC5.2, popcorn-remake.AC5.3
<!-- END_PHASE_7 -->

## Additional Considerations

**Rate limiting:** The NBA.com API (used by `nba_api`) has no published rate limits but uses Cloudflare protection. The pipeline adds 1-2 second delays between requests and runs from GitHub Actions (not a cloud provider IP). If rate-limited, the pipeline logs the failure and retries on the next scheduled run.

**Hash routing:** GitHub Pages doesn't support server-side URL rewriting, so React Router uses hash-based routing (`/#/game/:gameId/boxscore`). All navigation is client-side.

**Offline NBA season:** During the offseason (roughly July–September), the pipeline will find no new games and make no commits. The site will show the last month of regular season or playoff data until it ages out.
