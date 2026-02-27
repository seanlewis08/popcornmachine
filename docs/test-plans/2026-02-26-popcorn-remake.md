# Human Test Plan: Popcorn Remake

**Coverage:** 18/18 automated criteria pass. This plan covers manual verification for deployment (AC5) and visual/UX validation.

## Prerequisites

- All automated tests passing: `cd web && npx vitest run` (103 tests) and `uv run pytest tests/ -v` (71 tests)
- Application built: `cd web && npm run build`
- Browser with DevTools console access

## Phase 1: Home/Scores Page

| Step | Action | Expected |
|------|--------|----------|
| 1.1 | Open application home page (/) | Page loads without console errors |
| 1.2 | Scroll through game list | Games grouped by date, most recent first |
| 1.3 | Look at game cards | Both team names/tricodes and final scores visible |
| 1.4 | Click "Box Score" link on a game | Navigates to `/#/game/{gameId}/boxscore` |
| 1.5 | Go back, click "Gameflow" link | Navigates to `/#/game/{gameId}/gameflow` |
| 1.6 | Navigate to `/` with no games | "No games available" message displays gracefully |

## Phase 2: Box Score Page

| Step | Action | Expected |
|------|--------|----------|
| 2.1 | Navigate to a game's box score | Game header with teams and scores visible |
| 2.2 | Examine table headers | All 17 columns: Player, Min, FG, 3PT, FT, OREB, REB, AST, BLK, STL, TO, PF, PTS, +/-, HV, PROD, EFF |
| 2.3 | Verify both team tables | Home and away team tables render with player data |
| 2.4 | Check team totals rows | "Team Totals" row with aggregated stats for both teams |
| 2.5 | Check period breakdown rows | Q1-Q4 rows with per-quarter stats |
| 2.6 | Click a player row | Row expands showing per-stint breakdown with times |
| 2.7 | Click same row again | Stint breakdown collapses |
| 2.8 | Verify derived metrics | HV, PROD, EFF columns display calculated values |
| 2.9 | Navigate to invalid game ID | "Game not found" error displays; no console errors |

## Phase 3: Gameflow Page

| Step | Action | Expected |
|------|--------|----------|
| 3.1 | Navigate to gameflow page | Game header with "home vs away" visible |
| 3.2 | Examine timeline | Horizontal timeline with Q1-Q4 dividers |
| 3.3 | Count player rows | One lane per player; home team first, away second |
| 3.4 | Verify team colors | Home stints blue, away stints red |
| 3.5 | Hover a stint bar | Tooltip shows minutes and +/- |
| 3.6 | Click a stint bar | Detail popover with period, times, stats, play-by-play |
| 3.7 | Check alignment | Players subbed at same time have bars ending at same X |
| 3.8 | Tab through stint bars | Keyboard focus works; Enter/Space opens detail |
| 3.9 | Navigate to invalid gameflow | "Gameflow data not available" message |

## Phase 4: Deployment (Requires Live GitHub)

| Step | Action | Expected |
|------|--------|----------|
| 4.1 | Inspect pipeline.yml | Cron schedule `0 6,14 * * *`, git commit/push steps |
| 4.2 | Inspect deploy.yml | Triggers on push to main, builds and deploys |
| 4.3 | Manually trigger pipeline workflow | Workflow completes; data commit appears if new data |
| 4.4 | Push to main branch | Deploy workflow triggers automatically |
| 4.5 | Navigate to deployed site | React app loads with game list |
| 4.6 | Access `/data/index.json` on deployed site | JSON file served correctly |
| 4.7 | Check DevTools Network tab across all pages | No 404 errors for any data files |

## End-to-End User Journey

1. Open home page → verify games listed by date
2. Click "Box Score" → verify stats with all columns
3. Expand a player → verify stint breakdown
4. Navigate back → click "Gameflow"
5. Verify timeline with colored stint bars
6. Click stint → verify detail card with play-by-play
7. Navigate to nonexistent game → verify error handling
8. Check console → zero JavaScript errors throughout

## Traceability

| AC | Automated Test | Manual Step |
|----|---------------|-------------|
| AC1.1-1.4 | HomePage, GameCard tests | 1.1-1.6 |
| AC2.1-2.6 | PlayerStatsTable, BoxScorePage tests | 2.1-2.9 |
| AC3.1-3.5 | GameflowTimeline, StintBar, GameflowPage tests | 3.1-3.9 |
| AC4.1-4.3 | cleanup, write, main tests | 4.1-4.3 |
| AC5.1-5.3 | N/A (infrastructure) | 4.1-4.7 |
