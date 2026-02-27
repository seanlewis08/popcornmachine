# Popcorn Remake Implementation Plan

**Goal:** Build a zero-cost NBA game stats viewer with a Python data pipeline and Vite React SPA, deployed via GitHub Pages.

**Architecture:** Python pipeline fetches post-game data from `nba_api`, pre-computes derived metrics, and commits structured JSON files to the repo. A Vite React SPA reads those JSON files at runtime to render three views: home/scores, box score, and gameflow. GitHub Pages serves both the app and data files.

**Tech Stack:** Python 3.11+ (uv), nba_api, Vite, React 18, TypeScript, Tailwind CSS v4, shadcn/ui, React Router v7, Vitest, GitHub Actions, GitHub Pages

**Scope:** 7 phases from original design (phases 1-7)

**Codebase verified:** 2026-02-26 — greenfield project. Phase 1 creates React app scaffold. Phase 3 creates shared types and useJsonData hook.

---

## Acceptance Criteria Coverage

This phase implements and tests:

### popcorn-remake.AC3: Gameflow page shows interactive rotation timeline
- **popcorn-remake.AC3.1 Success:** Each player has a horizontal timeline lane across four quarters
- **popcorn-remake.AC3.2 Success:** Stints are color-coded by team
- **popcorn-remake.AC3.3 Success:** Clicking/hovering a stint shows stats and play-by-play events
- **popcorn-remake.AC3.4 Success:** Timeline aligns correctly across players for the same time periods
- **popcorn-remake.AC3.5 Failure:** Game with no gameflow data shows graceful fallback

---

## Phase 5: Gameflow Page

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->
<!-- START_TASK_1 -->
### Task 1: Timeline utility functions and constants

**Verifies:** popcorn-remake.AC3.4

**Files:**
- Create: `web/src/lib/timeline.ts`

**Implementation:**

Create `web/src/lib/timeline.ts` with pure utility functions for converting game time data to pixel coordinates for the timeline visualization.

Constants:
- `QUARTER_DURATION_SECONDS = 720` (12 minutes)
- `OT_DURATION_SECONDS = 300` (5 minutes)
- `TOTAL_REGULATION_SECONDS = 2880` (48 minutes)

Functions:
- `clockToSeconds(period: number, clock: string) -> number` — Converts a period number and clock string (e.g., "10:30") to an absolute seconds value from game start. Period 1 clock "12:00" = 0 seconds. Period 1 clock "0:00" = 720 seconds. Period 2 clock "12:00" = 720 seconds. etc.
- `secondsToPixelX(seconds: number, totalWidth: number, totalSeconds: number) -> number` — Converts absolute seconds to a pixel X position within the timeline.
- `getQuarterBoundaries(numPeriods: number) -> { period: number, startSeconds: number, endSeconds: number }[]` — Returns the start/end boundaries for each quarter/OT period.
- `getStintPixelRange(inTime: string, outTime: string, period: number, totalWidth: number, totalSeconds: number) -> { x: number, width: number }` — Converts stint in/out clock times to pixel position and width for rendering.

**Testing:**
Tests must verify:
- popcorn-remake.AC3.4: clockToSeconds correctly maps times across all four quarters so that stints at the same game time align to the same X coordinate
- Quarter boundaries are calculated correctly for 4-period and overtime games
- Stint pixel ranges are proportional and non-overlapping within a player's timeline

These are pure function tests — no DOM or React needed.

**Verification:**
Run: `cd web && npm run test:run`
Expected: All tests pass

**Commit:** `feat: add timeline utility functions for gameflow calculations`
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Timeline visualization components

**Verifies:** popcorn-remake.AC3.1, popcorn-remake.AC3.2, popcorn-remake.AC3.3

**Files:**
- Create: `web/src/components/GameflowTimeline.tsx`
- Create: `web/src/components/StintBar.tsx`
- Create: `web/src/components/StintDetailCard.tsx`

**Implementation:**

Before implementing, install shadcn/ui Popover component for stint detail display:
```bash
cd web && npx shadcn@latest add popover && cd ..
```

Create `web/src/components/StintBar.tsx`:
- Renders a single stint as a colored horizontal rectangle positioned absolutely within its player lane
- Props: `stint: GameflowStint`, `team: string`, `x: number`, `width: number`, `homeTeamTricode: string`
- Color-coded by team: one color for home team, another for away team (AC3.2)
- On click, opens a `StintDetailCard` popover (AC3.3)
- On hover, shows a brief tooltip with stint minutes and +/-

Create `web/src/components/StintDetailCard.tsx`:
- Renders inside a shadcn/ui Popover when a stint is clicked
- Shows: period, in/out times, minutes played, plus/minus
- Shows stat summary: PTS, AST, REB, STL, BLK, TOV, FGM-FGA, FG3M-FG3A, FTM-FTA
- Shows play-by-play events as a scrollable list: clock time, event type, description
- Props: `stint: GameflowStint`

Create `web/src/components/GameflowTimeline.tsx`:
- Renders the full gameflow visualization
- Props: `data: GameflowData`
- Layout structure:
  - Top: Quarter divider labels (Q1, Q2, Q3, Q4, OT if applicable) positioned at boundaries
  - Left column: Player names (grouped by team, with team header)
  - Main area: For each player, a horizontal lane with `StintBar` components positioned using `getStintPixelRange`
- Uses `useRef` + `clientWidth` or a fixed width (e.g., 800px) for the timeline width
- Players grouped by team (home team first, then away team)
- Vertical lines at quarter boundaries for alignment reference (AC3.4)

**Testing:**
Tests must verify each AC:
- popcorn-remake.AC3.1: GameflowTimeline renders one lane per player with horizontal stint bars
- popcorn-remake.AC3.2: StintBars have different CSS classes/colors based on team affiliation
- popcorn-remake.AC3.3: Clicking a StintBar opens a popover showing stint stats and play-by-play events

Use fixture gameflow JSON data. Render with React Testing Library, verify DOM structure and interactions.

**Verification:**
Run: `cd web && npm run test:run`
Expected: All tests pass

**Commit:** `feat: add gameflow timeline visualization components`
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: GameflowPage integrating data fetch and timeline

**Verifies:** popcorn-remake.AC3.1, popcorn-remake.AC3.5

**Files:**
- Modify: `web/src/pages/GameflowPage.tsx` (replace placeholder)

**Implementation:**

Update `web/src/pages/GameflowPage.tsx`:
- Extract `gameId` from URL params using `useParams`
- Fetch `data/games/{gameId}/gameflow.json` using `useJsonData<GameflowData>`
- Display game header: home team vs away team
- Render `GameflowTimeline` component with fetched data
- Show loading state while fetching
- Show graceful fallback for missing gameflow data (AC3.5): "Gameflow data not available for this game" message when fetch fails or returns empty players array

**Testing:**
Tests must verify:
- popcorn-remake.AC3.1: GameflowPage renders the timeline with player lanes when data loads
- popcorn-remake.AC3.5: GameflowPage shows fallback message when fetch returns 404 or empty data

Mock `fetch` to return fixture gameflow JSON.

**Verification:**
Run: `cd web && npm run test:run`
Expected: All tests pass

**Commit:** `feat: implement GameflowPage with timeline visualization`
<!-- END_TASK_3 -->
<!-- END_SUBCOMPONENT_A -->
