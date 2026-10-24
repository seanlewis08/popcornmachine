# Popcorn Remake: NBA Game Stats Viewer

**Last Updated:** 2026-10-23

## Purpose

Popcorn Remake is a greenfield web application that provides detailed NBA game statistics with a focus on player stint-level analytics. It fetches live NBA game data via the NBA CDN (`cdn.nba.com`), transforms it into structured JSON contracts, and displays it through an interactive React single-page application deployed on GitHub Pages.

## Architecture Overview

### Three-Tier System

1. **Data Pipeline** (Python)
   - Fetches raw NBA data from NBA CDN (`cdn.nba.com`) endpoints
   - Transforms and validates data according to contracts
   - Writes JSON files to `data/` directory
   - Scheduled via GitHub Actions

2. **Data Layer** (JSON files in `data/`)
   - Index: `data/index.json`
   - Daily scores: `data/scores/YYYY-MM-DD.json`
   - Game details: `data/games/{gameId}/boxscore.json`, `gameflow.json`

3. **Frontend** (React + TypeScript)
   - Vite-based SPA with React 19
   - Reads JSON data from `data/` folder
   - Renders game statistics with stint-level breakdown
   - Deployed to GitHub Pages via Actions

## Contracts & Data Specifications

### Index Contract (`data/index.json`)

```typescript
interface IndexData {
  dates: DateEntry[];
}

interface DateEntry {
  date: string;  // YYYY-MM-DD format
  games: GameSummary[];
}

interface GameSummary {
  gameId: string;        // 10-digit ID (e.g., "0022500001")
  home: string;          // Home team tricode (3 letters)
  away: string;          // Away team tricode (3 letters)
  homeScore: number;
  awayScore: number;
}
```

### Daily Scores Contract (`data/scores/YYYY-MM-DD.json`)

```typescript
interface ScoreEntry {
  gameId: string;
  date: string;          // YYYY-MM-DD
  homeTeam: TeamInfo;
  awayTeam: TeamInfo;
  status: string;        // Game status (e.g., "Final", "In Progress")
}

interface TeamInfo {
  tricode: string;       // 3-letter team code
  name: string;          // Full team name
  score: number;
}
```

### Box Score Contract (`data/games/{gameId}/boxscore.json`)

```typescript
interface BoxScoreData {
  gameId: string;
  date: string;
  homeTeam: TeamInfo;
  awayTeam: TeamInfo;
  players: PlayerData[];         // Both teams' players
  teamTotals: {
    home: TeamTotals;
    away: TeamTotals;
  };
  periodTotals: {
    home: PeriodTotals[];        // 4 regulation periods + OT
    away: PeriodTotals[];
  };
}

interface PlayerData {
  playerId: string;              // Unique player ID from NBA API
  name: string;
  team: string;                  // Team tricode
  totals: PlayerTotals;          // Game-wide totals
  stints: StintData[];           // Stint-level breakdown
}

interface PlayerTotals {
  min: number;                   // Total minutes
  fgm: number; fga: number;      // Field goals made/attempted
  fg3m: number; fg3a: number;    // 3-pointers made/attempted
  ftm: number; fta: number;      // Free throws made/attempted
  oreb: number; reb: number;     // Offensive/total rebounds
  ast: number; blk: number;      // Assists/blocks
  stl: number; tov: number;      // Steals/turnovers
  pf: number;                    // Personal fouls
  pts: number;                   // Total points
  plusMinus: number;             // +/- differential
  hv: number;                    // (Computed from PBP events)
  prod: number;                  // (Computed stat)
  eff: number;                   // (Computed efficiency)
}

interface StintData {
  period: number;                // 1-4 for regulation, 5+ for OT
  inTime: string;                // Clock format MM:SS
  outTime: string;               // Clock format MM:SS
  minutes: number;               // Duration of stint
  plusMinus: number;             // +/- during this stint
  fgm: number; fga: number;      // Per-stint shooting stats
  fg3m: number; fg3a: number;
  ftm: number; fta: number;
  oreb: number; reb: number;
  ast: number; blk: number;
  stl: number; tov: number;
  pf: number;
  pts: number;
}

interface TeamTotals {
  fgm: number; fga: number;
  fg3m: number; fg3a: number;
  ftm: number; fta: number;
  oreb: number; reb: number;
  ast: number; blk: number;
  stl: number; tov: number;
  pf: number;
  pts: number;
}

interface PeriodTotals {
  period: number;
  fgm: number; fga: number;
  fg3m: number; fg3a: number;
  ftm: number; fta: number;
  pts: number;
}
```

### Gameflow Contract (`data/games/{gameId}/gameflow.json`)

```typescript
interface GameflowData {
  gameId: string;
  homeTeam: { tricode: string; name: string };
  awayTeam: { tricode: string; name: string };
  players: GameflowPlayer[];
}

interface GameflowPlayer {
  playerId: string;
  name: string;
  team: string;                  // Team tricode
  stints: GameflowStint[];
}

interface GameflowStint {
  period: number;
  inTime: string;                // MM:SS
  outTime: string;               // MM:SS
  minutes: number;
  plusMinus: number;
  stats: StintStats;             // Per-stint shooting only
  events: PlayByPlayEvent[];      // PBP events for this stint
}

interface StintStats {
  fgm: number; fga: number;
  fg3m: number; fg3a: number;
  ftm: number; fta: number;
  pts: number; ast: number;
  reb: number; stl: number;
  blk: number; tov: number;
  pf: number;
}

interface PlayByPlayEvent {
  clock: string;                 // MM:SS
  type: string;                  // One of: Make2 Make3 miss2 miss3 MakeFT missFT OffReb DefReb
                                 //   Steal Block Assist TO PF (lowercase V2 names like "make2"/"fta"/"reb"
                                 //   only appear on legacy stats.nba.com-shaped input)
  description: string;           // Human-readable event description
  shot?: ShotDetail;             // Present on field-goal events only (never on FTs, rebounds, etc.)
}

// Court location and context for a field goal, straight from the NBA CDN
// play-by-play action. Consumed by external shot-zone analysis
// (crysterbaters.com); keep it additive.
interface ShotDetail {
  x: number | null;              // NBA legacy court coords, tenths of a foot, basket at the origin
  y: number | null;              //   (x: left/right of the basket, y: distance out from the baseline)
  dist: number | null;           // Shot distance in feet
  area: string;                  // "Restricted Area", "In The Paint (Non-RA)", "Mid-Range",
                                 //   "Left Corner 3", "Right Corner 3", "Above the Break 3", … ("" if absent)
  areaDetail: string;            // "Center", "Left Side Center", "8-16 ft", "24+ ft", … ("" if absent)
  side: string;                  // "left" | "right" | "center" ("" if absent)
  descriptor: string;            // "driving", "pullup", "step back", "cutting", … ("" if absent)
  made: boolean;                 // From the feed's shotResult (falls back to the "MISS" description prefix)
  assisted: boolean;             // Feed tagged an assister. Reliable for makes only — misses are never tagged
  qualifiers: string[];          // e.g. ["fastbreak", "pointsinthepaint", "2ndchance"]
}
```

Absent values inside `shot` are written as `null` (numbers) or `""` (strings), never dropped and never coerced to `0`, so a consumer can tell "unknown" from "zero". Adds roughly 150 bytes per shot, ~30 KB per game.

## Python Data Pipeline

### Module Structure

- `pipeline/fetch.py` - NBA CDN data fetching via `curl_cffi` Chrome impersonation, with retry logic (2 retries, 5s backoff); derives rotation from PBP substitution events
- `pipeline/transform.py` - Contract mapping: CDN data → JSON schemas (receives V2-compatible DataFrames from fetch)
- `pipeline/write.py` - JSON file writing with atomic operations
- `pipeline/season.py` - Season arithmetic: `season_for("2027-01-10") == "2026-27"`, `season_start_date(...)`; also a CLI (`python -m pipeline.season --start-of DATE`) the workflow uses to find the backfill start
- `pipeline/cleanup.py` - Season retention: deletes score files, game dirs, and index entries from seasons before the one containing the reference date (today). The pure predicate is `is_stale(date, reference_date)`
- `pipeline/main.py` - Orchestrator with error handling

### Pipeline Contract

**Signature:** `main(date: str | None = None, data_dir: str = "data", cleanup: bool = False) -> bool`

**Behavior:**
1. Defaults to yesterday's date if not specified
2. Fetches scoreboard → transforms scores → validates game list
3. For each game: fetch boxscore + playbyplay + rotation → validate → transform
4. Skips games with incomplete data (logs error, continues)
5. On success: writes scores and index to `data/`
6. Optionally runs cleanup (drops every season before the current one — see Scheduling & Cleanup)

**Return value:** `True` if the schedule/scoreboard API responded (including with zero games — an off day writes an empty `[]` scores file). `False` if the API was unreachable; nothing is written so the next backfill retries the date.

**Entry Point:** `python -m pipeline.main [--date YYYY-MM-DD] [--data-dir PATH] [--cleanup]`

**Exit codes:** `0` success or off day · `2` (`EXIT_API_UNREACHABLE`) schedule/scoreboard fetch failed · `1` uncaught exception. The workflow relies on `2` to distinguish "NBA blocked us" from "bug in pipeline".

### CDN Endpoints

- **Schedule:** `https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json` — full season schedule, filtered by date
- **Boxscore:** `https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json` — per-game box scores with player positions
- **Play-by-play:** `https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json` — per-game PBP events
- **No CDN rotation endpoint** — rotation data is derived from PBP substitution events + boxscore starters

**Access control:** `cdn.nba.com` is behind Akamai Bot Manager and only serves JSON to requests that look like the XHR nba.com's own page makes. Every request goes through `_fetch_json` using `curl_cffi` with `impersonate=IMPERSONATE` (a real Chrome TLS/HTTP2 fingerprint; the library supplies the matching `User-Agent`/`sec-ch-ua*`). `_HEADERS` holds only the request context (Accept, Origin, Referer, Sec-Fetch-*). Browser-like headers over plain `requests` worked from a home IP but were refused from GitHub Actions (2026-10-23); the older UA/Accept/Origin/Referer set has been refused everywhere since 2026-06-16. `tests/test_fetch.py::TestCdnHeaders` pins this, including an echo-server test of the wire request. History, version-bump procedure and the next escalation are in `docs/TROUBLESHOOTING.md`.

### Key Invariants

- CDN endpoints are used instead of stats.nba.com (which blocks cloud IPs)
- Every request to cdn.nba.com goes through `_fetch_json` with the full browser header set (see Access control above); do not add a second HTTP call site
- CDN data is mapped to V2-compatible DataFrame columns so transform.py works unchanged. Play-by-play rows must also carry `isFieldGoal`, `shotResult`, `shotValue` and the rebound `subType` (as `EVENTMSGACTIONTYPE`): transform's shot/stat classification keys off those, and without them every attempt is counted as a make and every rebound as offensive (shipped that way Feb–Oct 2026)
- Module-level caches prevent redundant fetches within a pipeline run (schedule, PBP, boxscore)
- Failed API calls are logged to stderr with ISO timestamps
- Stint timing uses decisecond precision from derived rotation data, converted to MM:SS format
- Each regulation period = 720 seconds (12 minutes), 7200 deciseconds
- Stint-level stats are filtered from play-by-play events
- Missing data fields are never written (validation before write)

## React Frontend

### Technology Stack

- **Framework:** React 19 with TypeScript
- **Styling:** Tailwind CSS v4 with @tailwindcss/vite plugin
- **UI Components:** shadcn/ui (Card, Button, Table, Collapsible, Popover)
- **Routing:** React Router v7
- **Tables:** TanStack React Table v8
- **Testing:** Vitest + React Testing Library
- **Build:** Vite 7

### Build & Deployment

- **Local dev:** `npm run dev` (Vite dev server)
- **Build:** `tsc -b && vite build` (TypeScript compile + Vite bundle)
- **Output:** `web/dist/` (Vite builds here, GitHub Pages deploys from this folder)
- **Base path:** `./` (relative, for GitHub Pages subpath deployment)
- **Data location:** `web/dist/data/` (copied from repo root `data/` during deploy)

### Component Architecture

Key rendering components:
- `GameCard.tsx` - Lists game summaries
- `StintBreakdown.tsx` - Player stint visualization
- `StintBar.tsx` - Visual stint timeline
- `StintDetailCard.tsx` - Detailed stint statistics
- `PlayerStatsTable.tsx` - Per-player box score table
- `GameflowTimeline.tsx` - Game progression visualization (stint rows, momentum chart, minute selector, hover cursor)
- `StintBar.tsx` - Not rendered by any page; only its own test uses it

Pure helpers in `src/lib/` (no React, no I/O — unit-tested directly):
- `team-palette.ts` - `buildTeamPalette({home, away})` picks on-court/bench/text colors per team from `src/data/teamColors.json`. Home takes its first color that reads against the dark page; away must also be distinct from home's (walks its palette, then tints). `paletteToCssVars()` yields the `--home-on-court`, `--home-bench`, `--home-text`, `--away-*` custom properties that `GameflowTimeline` sets on its root and `index.css` reads in `.hometeamIN` etc. A test checks all 870 real matchups.
- `timeline-geometry.ts` - Minute ↔ pixel conversions. 18px per game minute everywhere: 216px quarters, 90px overtimes. Player rows have a 1px spacer between periods (`minuteToRowX` / `rowXToMinute`); the chart and minute selector don't (`minuteToChartX` / `chartXToMinute`). Any new timeline positioning must go through these — the OT mismatch bug came from a second copy of the math.

Timeline interaction model: hover previews, click pins. `hoverMinute` (fractional) is set by mouse movement over the chart or the player-row block and drawn as a cursor in each region's own coordinates. `selectedMinute` (0-based bucket) is set by the minute selector or a chart click. `highlightMinute = selectedMinute ?? bucket(hoverMinute)` drives the on-court dimming in `PlayerRow`; while pinned, the hover cursor is hidden and a band marks the pinned minute.

All components:
- Load JSON data from `data/` at runtime
- Use TypeScript interfaces from `src/types/api.ts`
- Follow shadcn/ui component patterns
- Have corresponding .test.tsx files with Vitest coverage

### Testing Setup

- **Framework:** Vitest with jsdom environment
- **Test files:** `src/**/*.test.tsx`
- **Setup:** `src/test/setup.ts` (testing library configuration)
- **Run:** `npm run test` (watch) or `npm run test:run` (single run)

## CI/CD Workflows

### Data Pipeline Workflow (`.github/workflows/pipeline.yml`)

**Trigger:** Scheduled at 6 AM and 2 PM UTC daily, or manual dispatch

**Steps:**
1. Checkout code
2. Install `uv` (Python package manager)
3. Run `uv sync` to install dependencies
4. Run pipeline: scheduled runs backfill every date since the season started (Oct 1, via `python -m pipeline.season --start-of`) that lacks a `data/scores/` file, then re-run yesterday with `--cleanup`; manual runs fetch the given date. Existing dates are skipped by a file check, so the season-long walk is cheap. Every date that exits non-zero is recorded in the `failed_dates` step output with a `::error::` annotation (exit 2 = CDN unreachable, anything else = crash).
5. `git add data/` then check the staged diff (catches new untracked files, not just modified ones)
6. If changed: commit with bot credentials and push
7. If changed: `gh workflow run deploy.yml`
8. Keep schedule enabled: `gh api -X PUT .../actions/workflows/pipeline.yml/enable` on every run. GitHub disables scheduled workflows after 60 days without commits; this reset the clock after the 2026 offseason disabled it.
9. Fail the job if `failed_dates` is non-empty. Runs last so fetched data is already committed and deployed; a failed scheduled run emails the repo owner.

**Permissions:** `contents: write`, `actions: write` (step 8 and the deploy trigger)

### Deploy Workflow (`.github/workflows/deploy.yml`)

**Trigger:** Push to `main` branch or manual dispatch

**Build Steps:**
1. Checkout code
2. Setup Node 20 with npm cache
3. Install web dependencies: `cd web && npm ci`
4. Build: `cd web && npm run build`
5. Copy `data/` → `web/dist/data/`
6. Upload artifact to GitHub Pages
7. Deploy to GitHub Pages environment

**Permissions:** `contents: read`, `pages: write`, `id-token: write`

**Concurrency:** Cancels previous deploy if new push arrives (group: "pages")

## Dependencies & Versions

### Python
- `curl-cffi` - HTTP client for NBA CDN endpoints (Chrome impersonation; see Access control)
- `pandas` - Data manipulation and DataFrame construction

### Node.js
- React 19.2.0, React DOM 19.2.0
- TypeScript 5.9.3
- Vite 7.3.1
- Tailwind CSS 4.2.1
- React Router 7.13.1
- TanStack React Table 8.21.3
- Vitest 4.0.18

**Python Version:** 3.x (via `.python-version` and `uv`)
**Node Version:** 20.x (GitHub Actions)

## Key Decisions & Invariants

### Data Organization

- **Single source of truth:** `data/` directory is the authoritative state
- **Immutable writes:** JSON files are atomic (not appended)
- **Index structure:** Root-level `data/index.json` tracks all available games
- **No databases:** JSON provides version control, auditability, portability

### Scheduling & Cleanup

- **Daily updates:** Pipeline runs twice daily (6 AM, 2 PM UTC)
- **Season retention:** The whole current season (regular season, play-in, playoffs) is kept; previous seasons are deleted. A season is Oct 1 → Sep 30 and is named by its start year (`pipeline/season.py`). Because cleanup only runs after a day with games, last season survives the summer and is dropped on the first game day of the new one. ~180 KB per game ≈ 220 MB per season, under GitHub Pages' 1 GB cap for one season at a time.
- **Game types:** Only regular-season (`002…`), playoff (`004…`), and play-in (`005…`) game IDs are ingested. Preseason (`001…`) and All-Star (`003…`) are filtered in `fetch_scoreboard` (`is_tracked_game_type`).
- **Idempotent:** Pipeline can re-run same date without corruption
- **Error-safe:** Individual game failures don't stop other games or break index

### Frontend Deployment

- **Relative base path** (`./`) ensures GitHub Pages subpath works
- **Static assets:** Data copied at build time, no API calls to backend
- **SPA architecture:** Client-side routing with React Router
- **No backend required:** Pure static deployment

### Rate Limiting & Resilience

- **CDN endpoints:** Uses `cdn.nba.com` which is not blocked by cloud providers (unlike `stats.nba.com`)
- **2 retries:** Two retries with 5s backoff on network failure
- **Module-level caching:** Schedule, PBP, and boxscore data cached per pipeline run
- **Graceful degradation:** Missing games skip, others continue
- **Error logging:** Timestamped stderr output for debugging

## File Structure

```
popcorn-remake/
├── pipeline/                    # Python data pipeline
│   ├── __init__.py
│   ├── main.py                 # Orchestrator (entry point)
│   ├── fetch.py                # NBA CDN client (fetch_*)
│   ├── transform.py            # Contract mapping (transform_*)
│   ├── write.py                # JSON output (write_*)
│   ├── season.py               # Season arithmetic (season_for, season_start_date)
│   └── cleanup.py              # Season retention (cleanup_old_data, is_stale)
├── web/                        # React SPA
│   ├── src/
│   │   ├── types/api.ts       # TypeScript contract definitions
│   │   ├── components/        # React components (tsx)
│   │   ├── lib/               # Pure helpers: team-palette, timeline-geometry, timeline
│   │   ├── data/teamColors.json  # 30 teams: name + ordered color list (hex)
│   │   ├── test/              # Setup + test utilities
│   │   └── main.tsx           # App entry point
│   ├── vite.config.ts         # Build configuration (base: './')
│   ├── package.json           # npm dependencies
│   ├── tsconfig.json
│   └── index.html
├── data/                       # Generated JSON files (git-tracked)
│   ├── index.json             # Game index
│   ├── scores/
│   │   └── YYYY-MM-DD.json    # Daily scores
│   └── games/
│       └── {gameId}/          # Per-game data
│           ├── boxscore.json
│           └── gameflow.json
├── tests/                      # Python unit tests
│   ├── test_fetch.py
│   ├── test_transform.py
│   ├── test_write.py
│   ├── test_cleanup.py
│   ├── test_season.py
│   └── test_main.py
├── docs/
│   └── TROUBLESHOOTING.md     # Runbook: site not updating, CDN 403, disabled schedule
├── .github/workflows/          # CI/CD automation
│   ├── pipeline.yml           # Data fetch schedule
│   └── deploy.yml             # GitHub Pages deployment
├── pyproject.toml             # Python project config (uv)
├── .python-version            # Python version spec
├── CLAUDE.md                  # This file (architecture guide)
└── README.md
```

## Notes for Claude Developers

### When Adding Features

1. **Contracts first:** Define data shapes in `web/src/types/api.ts` before components
2. **Pipeline impact:** Changes to data structures require pipeline updates
3. **Testing:** New components need .test.tsx files; pipeline changes need tests/test_*.py
4. **Deployment:** Data changes are auto-deployed; web changes need explicit `npm run build`

### Common Tasks

**Add new game stat field:**
1. Update `StintData`, `PlayerTotals`, etc. in `web/src/types/api.ts`
2. Update `transform.py` to compute and write field
3. Update relevant components to display field
4. Test with sample data

**Deploy frontend changes:**
- Commit to main, GitHub Actions auto-builds and deploys

**Troubleshoot pipeline:**
- Start with `docs/TROUBLESHOOTING.md` — covers the 30-second diagnosis, running locally, the cdn.nba.com 403 history and fix, the disabled-schedule fix, and the escalation path
- Check workflow logs: GitHub Actions UI → Data Pipeline runs; read the annotations first
- Data issues: See stderr timestamps in workflow logs
- Game skipping: Check pipeline logs for specific game_id errors

**Update deploy frequency:**
- Edit `.github/workflows/pipeline.yml` cron schedule (6 AM, 2 PM UTC)
- Changes deploy via Actions; manual runs available via "workflow_dispatch"
