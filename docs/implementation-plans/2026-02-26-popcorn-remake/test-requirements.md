# Test Requirements Mapping: Popcorn Remake

## Overview

This document maps each acceptance criterion from the Popcorn Remake design to specific test requirements. For each criterion, we specify whether it requires automated testing or human verification, along with test strategies and expected file paths.

---

## AC1: Home/Scores Page Shows Game Results

### AC1.1: Page lists games grouped by date, most recent first

**Criterion ID:** popcorn-remake.AC1.1

**Text:** "Page lists games grouped by date, most recent first"

**Test Type:** Automated (Unit + Integration)

**Test Files:**
- `web/src/pages/__tests__/HomePage.test.tsx`
- `web/src/hooks/__tests__/useJsonData.test.ts`

**Test Description:**
- Verify `index.json` is parsed correctly with dates and game arrays
- Dates are rendered in descending order (most recent first)
- Each date renders as a distinct section heading
- Games within each date section are accessible

**Test Data:** Mock `data/index.json` with multiple games across 2-3 dates.

---

### AC1.2: Each game shows both team names and final scores

**Criterion ID:** popcorn-remake.AC1.2

**Text:** "Each game shows both team names and final scores"

**Test Type:** Automated (Component)

**Test Files:**
- `web/src/components/__tests__/GameCard.test.tsx`

**Test Description:**
- GameCard renders both team names (tricodes) and final scores
- Home and away teams are visually distinguished
- Score values match fixture data

**Test Data:** Mock game objects from `data/scores/YYYY-MM-DD.json` schema.

---

### AC1.3: Each game card links to box score and gameflow pages

**Criterion ID:** popcorn-remake.AC1.3

**Text:** "Each game card links to box score and gameflow pages"

**Test Type:** Automated (Component)

**Test Files:**
- `web/src/components/__tests__/GameCard.test.tsx`

**Test Description:**
- GameCard renders link elements to `/#/game/:gameId/boxscore` and `/#/game/:gameId/gameflow`
- Both links are present and contain the correct gameId

**Test Data:** Sample game ID `0022500001`.

---

### AC1.4: Missing date file shows graceful empty state (not a crash)

**Criterion ID:** popcorn-remake.AC1.4

**Text:** "Missing date file shows graceful empty state (not a crash)"

**Test Type:** Automated (Integration) + Human Verification

**Test Files:**
- `web/src/pages/__tests__/HomePage.test.tsx`

**Automated tests:**
- Mock fetch to return 404 for `index.json`
- Verify component catches error and displays empty state message
- No unhandled exceptions

**Human verification:**
- Browser DevTools console shows no JavaScript errors
- Page displays user-friendly message, not a blank screen

---

## AC2: Box Score Page Shows Complete Player Stats

### AC2.1: All stat columns render

**Criterion ID:** popcorn-remake.AC2.1

**Text:** "All stat columns render (Min, FG, 3PT, FT, Reb, Ast, Blk, Stl, TO, PF, Pts, +/-)"

**Test Type:** Automated (Component)

**Test Files:**
- `web/src/components/__tests__/PlayerStatsTable.test.tsx`

**Test Description:**
- Table renders column headers: Min, FG, 3PT, FT, Reb, Ast, Blk, Stl, TO, PF, Pts, +/-
- Each player row has values for all stat columns
- Values match fixture data

**Test Data:** Player object with complete `totals` stats from boxscore contract.

---

### AC2.2: Derived metrics display correctly

**Criterion ID:** popcorn-remake.AC2.2

**Text:** "Derived metrics (hv, prod, eff) display correctly for each player"

**Test Type:** Automated (Unit + Component)

**Test Files:**
- `tests/test_transform.py` (Python: derived metric calculations)
- `web/src/components/__tests__/PlayerStatsTable.test.tsx`

**Test Description:**
- Python unit tests: hv = Reb+Ast+Blk+Stl-TO, prod = (Pts+hv)/Min, eff = standard NBA formula — verify with known inputs
- React component tests: hv, prod, eff columns render with correct pre-computed values from JSON

**Test Data:** Player stats with hand-calculated expected metrics.

---

### AC2.3: Per-stint breakdowns expand when clicking a player row

**Criterion ID:** popcorn-remake.AC2.3

**Text:** "Per-stint breakdowns expand when clicking a player row"

**Test Type:** Automated (Component + Interaction)

**Test Files:**
- `web/src/components/__tests__/PlayerStatsTable.test.tsx`
- `web/src/components/__tests__/StintBreakdown.test.tsx`

**Test Description:**
- Clicking a player row toggles expanded state
- When expanded, stint rows display with per-stint stats
- Each stint shows period, in/out times, minutes, all stat columns
- Clicking again collapses the rows

**Test Data:** Player with multiple stints from boxscore contract.

---

### AC2.4: Team totals row shows aggregate stats

**Criterion ID:** popcorn-remake.AC2.4

**Text:** "Team totals row shows aggregate stats"

**Test Type:** Automated (Component)

**Test Files:**
- `web/src/components/__tests__/PlayerStatsTable.test.tsx`

**Test Description:**
- Table renders a team totals row after player rows
- Totals row shows aggregated values from `teamTotals`
- All stat columns are populated

**Test Data:** `teamTotals` object from boxscore contract.

---

### AC2.5: Period breakdown rows show per-quarter stats

**Criterion ID:** popcorn-remake.AC2.5

**Text:** "Period breakdown rows show per-quarter stats for each team"

**Test Type:** Automated (Component)

**Test Files:**
- `web/src/components/__tests__/PlayerStatsTable.test.tsx`

**Test Description:**
- Period breakdown rows render for each quarter (Q1-Q4)
- Each row shows FGM-FGA, FG3M-FG3A, FTM-FTA, PTS for that period
- Values match `periodTotals` from boxscore contract

**Test Data:** `periodTotals` arrays from boxscore contract.

---

### AC2.6: Invalid game ID shows error state

**Criterion ID:** popcorn-remake.AC2.6

**Text:** "Invalid game ID shows error state (not a crash)"

**Test Type:** Automated (Integration) + Human Verification

**Test Files:**
- `web/src/pages/__tests__/BoxScorePage.test.tsx`

**Automated tests:**
- Mock fetch to return 404 for an invalid gameId
- Verify "Game not found" error message displays
- No unhandled exceptions

**Human verification:**
- Browser console shows no JavaScript errors
- Page displays user-friendly error, not blank screen

---

## AC3: Gameflow Page Shows Interactive Rotation Timeline

### AC3.1: Each player has a horizontal timeline lane across four quarters

**Criterion ID:** popcorn-remake.AC3.1

**Text:** "Each player has a horizontal timeline lane across four quarters"

**Test Type:** Automated (Component) + Human Verification

**Test Files:**
- `web/src/components/__tests__/GameflowTimeline.test.tsx`

**Automated tests:**
- GameflowTimeline renders one lane per player
- Players are grouped by team (home first, then away)
- Quarter dividers are present

**Human verification:**
- Each player lane visually spans all four quarters
- Layout is readable and not overcrowded

---

### AC3.2: Stints are color-coded by team

**Criterion ID:** popcorn-remake.AC3.2

**Text:** "Stints are color-coded by team"

**Test Type:** Automated (Component) + Human Verification

**Test Files:**
- `web/src/components/__tests__/StintBar.test.tsx`

**Automated tests:**
- StintBar applies different CSS classes based on team
- Home and away team stints have distinct class names

**Human verification:**
- Colors are visually distinct and accessible

---

### AC3.3: Clicking/hovering a stint shows stats and play-by-play events

**Criterion ID:** popcorn-remake.AC3.3

**Text:** "Clicking/hovering a stint shows stats and play-by-play events"

**Test Type:** Automated (Component + Interaction)

**Test Files:**
- `web/src/components/__tests__/StintBar.test.tsx`
- `web/src/components/__tests__/StintDetailCard.test.tsx`

**Test Description:**
- Clicking a StintBar opens a detail popover
- Detail card shows stint stats (PTS, AST, REB, etc.)
- Detail card shows play-by-play events (clock, type, description)
- Events are sorted chronologically

**Test Data:** Stint with stats and events from gameflow contract.

---

### AC3.4: Timeline aligns correctly across players

**Criterion ID:** popcorn-remake.AC3.4

**Text:** "Timeline aligns correctly across players for the same time periods"

**Test Type:** Automated (Unit) + Human Verification

**Test Files:**
- `web/src/lib/__tests__/timeline.test.ts`

**Automated tests:**
- `clockToSeconds` maps game times consistently across all quarters
- `getStintPixelRange` produces consistent X positions for the same absolute time across different players
- Quarter boundaries are calculated correctly

**Human verification:**
- Quarter dividers form straight vertical lines
- Stints at the same game time align horizontally

---

### AC3.5: Game with no gameflow data shows graceful fallback

**Criterion ID:** popcorn-remake.AC3.5

**Text:** "Game with no gameflow data shows graceful fallback"

**Test Type:** Automated (Integration) + Human Verification

**Test Files:**
- `web/src/pages/__tests__/GameflowPage.test.tsx`

**Automated tests:**
- Mock fetch to return 404 or empty players array
- Verify fallback message displays
- No unhandled exceptions

**Human verification:**
- Browser console shows no JavaScript errors
- Fallback message is helpful

---

## AC4: Data Pipeline Maintains Current-Month Data

### AC4.1: Pipeline purges data from previous months

**Criterion ID:** popcorn-remake.AC4.1

**Text:** "Pipeline purges data from previous months"

**Test Type:** Automated (Unit)

**Test Files:**
- `tests/test_cleanup.py`

**Test Description:**
- Create temp directory with fixture data spanning two months
- Run cleanup with reference date in newer month
- Verify old month files deleted, current month files intact
- Verify index.json updated

---

### AC4.2: Re-running pipeline for same date produces identical JSON

**Criterion ID:** popcorn-remake.AC4.2

**Text:** "Re-running pipeline for same date produces identical JSON"

**Test Type:** Automated (Integration)

**Test Files:**
- `tests/test_idempotency.py`

**Test Description:**
- Run transform + write with mocked API data
- Capture output files
- Run again with same input
- Compare files byte-for-byte using hashing

---

### AC4.3: API unavailability doesn't corrupt existing data files

**Criterion ID:** popcorn-remake.AC4.3

**Text:** "API unavailability doesn't corrupt existing data files"

**Test Type:** Automated (Integration)

**Test Files:**
- `tests/test_resilience.py`

**Test Description:**
- Set up temp data directory with pre-existing valid JSON
- Mock all fetch functions to return None (API unavailable)
- Run pipeline
- Verify all pre-existing files unchanged (compare hashes)

---

## AC5: Automated Deployment via GitHub

### AC5.1: Pipeline runs on cron schedule and commits new data

**Criterion ID:** popcorn-remake.AC5.1

**Text:** "Pipeline runs on cron schedule and commits new data"

**Test Type:** Human Verification

**Justification:** GitHub Actions cron workflows cannot be tested with automated unit tests. They must be verified by inspecting workflow YAML and manual trigger testing.

**Verification Approach:**
- Inspect `.github/workflows/pipeline.yml` for correct cron syntax
- Verify workflow installs uv, runs pipeline, commits and pushes if data changed
- Trigger workflow manually via workflow_dispatch and verify commit is created

---

### AC5.2: Site auto-deploys when main branch is updated

**Criterion ID:** popcorn-remake.AC5.2

**Text:** "Site auto-deploys when main branch is updated"

**Test Type:** Human Verification

**Justification:** GitHub Pages deployment requires live GitHub infrastructure that cannot be simulated in unit tests.

**Verification Approach:**
- Inspect `.github/workflows/deploy.yml` for push-to-main trigger
- Push a test commit to main and verify workflow runs
- Verify GitHub Pages deployment succeeds

---

### AC5.3: GitHub Pages serves both the app and JSON data files

**Criterion ID:** popcorn-remake.AC5.3

**Text:** "GitHub Pages serves both the app and JSON data files"

**Test Type:** Human Verification

**Justification:** Requires live deployed site to verify both static app and data files are served.

**Verification Approach:**
- Navigate to deployed site URL — verify React app loads
- Navigate to `/data/index.json` — verify JSON data is served
- Open browser DevTools Network tab — verify no 404s for data files
- Test all three pages: home, box score, gameflow

---

## Summary Table

| AC ID | Description | Test Type | Test Files |
|-------|-------------|-----------|-----------|
| AC1.1 | Games grouped by date | Automated | `HomePage.test.tsx`, `useJsonData.test.ts` |
| AC1.2 | Team names and scores | Automated | `GameCard.test.tsx` |
| AC1.3 | Links to box score and gameflow | Automated | `GameCard.test.tsx` |
| AC1.4 | Graceful empty state | Automated + Human | `HomePage.test.tsx` |
| AC2.1 | All stat columns | Automated | `PlayerStatsTable.test.tsx` |
| AC2.2 | Derived metrics | Automated | `test_transform.py`, `PlayerStatsTable.test.tsx` |
| AC2.3 | Expandable stint rows | Automated | `PlayerStatsTable.test.tsx`, `StintBreakdown.test.tsx` |
| AC2.4 | Team totals | Automated | `PlayerStatsTable.test.tsx` |
| AC2.5 | Period breakdowns | Automated | `PlayerStatsTable.test.tsx` |
| AC2.6 | Invalid game error state | Automated + Human | `BoxScorePage.test.tsx` |
| AC3.1 | Player timeline lanes | Automated + Human | `GameflowTimeline.test.tsx` |
| AC3.2 | Team color coding | Automated + Human | `StintBar.test.tsx` |
| AC3.3 | Stint detail on click | Automated | `StintBar.test.tsx`, `StintDetailCard.test.tsx` |
| AC3.4 | Timeline alignment | Automated + Human | `timeline.test.ts` |
| AC3.5 | No gameflow fallback | Automated + Human | `GameflowPage.test.tsx` |
| AC4.1 | Monthly data purge | Automated | `test_cleanup.py` |
| AC4.2 | Idempotent pipeline | Automated | `test_idempotency.py` |
| AC4.3 | API failure data safety | Automated | `test_resilience.py` |
| AC5.1 | Cron pipeline commits | Human | `pipeline.yml` inspection |
| AC5.2 | Auto-deploy on push | Human | `deploy.yml` inspection |
| AC5.3 | Pages serves app + data | Human | Live site verification |
