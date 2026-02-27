# Popcorn Remake Implementation Plan

**Goal:** Build a zero-cost NBA game stats viewer with a Python data pipeline and Vite React SPA, deployed via GitHub Pages.

**Architecture:** Python pipeline fetches post-game data from `nba_api`, pre-computes derived metrics, and commits structured JSON files to the repo. A Vite React SPA reads those JSON files at runtime to render three views: home/scores, box score, and gameflow. GitHub Pages serves both the app and data files.

**Tech Stack:** Python 3.11+ (uv), nba_api, Vite, React 18, TypeScript, Tailwind CSS v4, shadcn/ui, React Router v7, Vitest, @tanstack/react-table, GitHub Actions, GitHub Pages

**Scope:** 7 phases from original design (phases 1-7)

**Codebase verified:** 2026-02-26 — greenfield project. Phase 1 creates React app scaffold. Phase 3 creates shared types and useJsonData hook.

---

## Acceptance Criteria Coverage

This phase implements and tests:

### popcorn-remake.AC2: Box Score page shows complete player stats
- **popcorn-remake.AC2.1 Success:** All stat columns render (Min, FG, 3PT, FT, Reb, Ast, Blk, Stl, TO, PF, Pts, +/-)
- **popcorn-remake.AC2.2 Success:** Derived metrics (hv, prod, eff) display correctly for each player
- **popcorn-remake.AC2.3 Success:** Per-stint breakdowns expand when clicking a player row
- **popcorn-remake.AC2.4 Success:** Team totals row shows aggregate stats
- **popcorn-remake.AC2.5 Success:** Period breakdown rows show per-quarter stats for each team
- **popcorn-remake.AC2.6 Failure:** Invalid game ID shows error state (not a crash)

---

## Phase 4: Box Score Page

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->
<!-- START_TASK_1 -->
### Task 1: Install TanStack React Table and shadcn/ui table components

**Files:**
- Modify: `web/package.json` (new dependencies)

**Step 1: Install dependencies**

```bash
cd web && npm install @tanstack/react-table && npx shadcn@latest add table collapsible && cd ..
```

**Step 2: Verify build**

```bash
cd web && npm run build && cd ..
```
Expected: Build succeeds.

**Step 3: Commit**

```bash
git add web/
git commit -m "chore: add TanStack React Table and shadcn table/collapsible components"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: PlayerStatsTable component with expandable stint rows

**Verifies:** popcorn-remake.AC2.1, popcorn-remake.AC2.2, popcorn-remake.AC2.3, popcorn-remake.AC2.4, popcorn-remake.AC2.5

**Files:**
- Create: `web/src/components/PlayerStatsTable.tsx`
- Create: `web/src/components/StintBreakdown.tsx`

**Implementation:**

Create `web/src/components/PlayerStatsTable.tsx` — A table component using shadcn/ui Table + @tanstack/react-table that renders one team's box score.

Props: `players: PlayerData[]`, `teamTotals: object`, `periodTotals: PeriodTotals[]`, `teamName: string`, `teamTricode: string`

Column definitions using `ColumnDef<PlayerData>`:
- Player name (sticky left column)
- MIN (formatted as M:SS from decimal minutes)
- FG (formatted as "FGM-FGA")
- 3PT (formatted as "FG3M-FG3A")
- FT (formatted as "FTM-FTA")
- OREB
- REB
- AST
- BLK
- STL
- TO
- PF
- PTS
- +/- (with color: green for positive, red for negative)
- HV (derived metric)
- PROD (derived metric, formatted to 2 decimal places)
- EFF (derived metric)

Each player row is clickable. When clicked, it expands to reveal a `StintBreakdown` component showing per-stint stats. Use React state (`useState`) to track which player rows are expanded (by playerId).

Below the player rows, render:
- A **team totals** row with aggregate stats from `teamTotals`
- **Period breakdown** rows from `periodTotals` — one row per quarter showing FGM-FGA, FG3M-FG3A, FTM-FTA, PTS for that period

Create `web/src/components/StintBreakdown.tsx` — Renders a sub-table of stint data for an expanded player row. Shows period, in/out times, minutes, and all stat columns matching the stint data contract. Compact font size, indented styling to visually distinguish from main table.

**Testing:**
Tests must verify each AC:
- popcorn-remake.AC2.1: Table renders all stat columns (verify column headers present in DOM)
- popcorn-remake.AC2.2: Derived metrics (hv, prod, eff) display with correct values from fixture data
- popcorn-remake.AC2.3: Clicking a player row reveals stint breakdown table with per-stint stats
- popcorn-remake.AC2.4: Team totals row renders with aggregate stat values
- popcorn-remake.AC2.5: Period breakdown rows render with per-quarter stats

Use fixture data from design plan contracts. Mock no fetching needed — these are pure presentational components receiving data via props.

**Verification:**
Run: `cd web && npm run test:run`
Expected: All tests pass

**Commit:** `feat: add PlayerStatsTable with expandable stint breakdowns`
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: BoxScorePage integrating data fetch and table components

**Verifies:** popcorn-remake.AC2.1, popcorn-remake.AC2.6

**Files:**
- Modify: `web/src/pages/BoxScorePage.tsx` (replace placeholder)

**Implementation:**

Update `web/src/pages/BoxScorePage.tsx`:
- Extract `gameId` from URL params using `useParams`
- Fetch `data/games/{gameId}/boxscore.json` using `useJsonData<BoxScoreData>`
- Display game header: home team vs away team with final scores
- Render two `PlayerStatsTable` components — one for home team, one for away team
- Filter `players` array by `team` field to split into home and away
- Pass corresponding `teamTotals` and `periodTotals` to each table
- Show loading state while fetching
- Show error state for invalid game ID (AC2.6): "Game not found" message when fetch fails with 404

**Testing:**
Tests must verify:
- popcorn-remake.AC2.1: BoxScorePage renders both team tables with all stat columns
- popcorn-remake.AC2.6: BoxScorePage shows "Game not found" error for invalid game IDs (mock fetch returning 404)

Mock `fetch` to return fixture boxscore JSON.

**Verification:**
Run: `cd web && npm run test:run`
Expected: All tests pass

**Commit:** `feat: implement BoxScorePage with dual team stat tables`
<!-- END_TASK_3 -->
<!-- END_SUBCOMPONENT_A -->
