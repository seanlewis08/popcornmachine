# Popcorn Remake Implementation Plan

**Goal:** Build a zero-cost NBA game stats viewer with a Python data pipeline and Vite React SPA, deployed via GitHub Pages.

**Architecture:** Python pipeline fetches post-game data from `nba_api`, pre-computes derived metrics, and commits structured JSON files to the repo. A Vite React SPA reads those JSON files at runtime to render three views: home/scores, box score, and gameflow. GitHub Pages serves both the app and data files.

**Tech Stack:** Python 3.11+ (uv), nba_api, Vite, React 18, TypeScript, Tailwind CSS v4, shadcn/ui, React Router v7, Vitest, GitHub Actions, GitHub Pages

**Scope:** 7 phases from original design (phases 1-7)

**Codebase verified:** 2026-02-26 — greenfield project. Phase 1 creates React app scaffold with routing, shadcn/ui, and Vitest.

---

## Acceptance Criteria Coverage

This phase implements and tests:

### popcorn-remake.AC1: Home/Scores page shows game results
- **popcorn-remake.AC1.1 Success:** Page lists games grouped by date, most recent first
- **popcorn-remake.AC1.2 Success:** Each game shows both team names and final scores
- **popcorn-remake.AC1.3 Success:** Each game card links to box score and gameflow pages
- **popcorn-remake.AC1.4 Failure:** Missing date file shows graceful empty state (not a crash)

---

## Phase 3: Home/Scores Page

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->
<!-- START_TASK_1 -->
### Task 1: Data fetching hook and TypeScript types

**Verifies:** popcorn-remake.AC1.1, popcorn-remake.AC1.4

**Files:**
- Create: `web/src/types/api.ts`
- Create: `web/src/hooks/useJsonData.ts`

**Implementation:**

Create `web/src/types/api.ts` with TypeScript interfaces matching the JSON API contracts from the design plan. Define: `IndexData`, `DateEntry`, `GameSummary`, `ScoreEntry`, `TeamInfo`, `BoxScoreData`, `PlayerData`, `PlayerTotals`, `StintData`, `TeamTotals`, `PeriodTotals`, `GameflowData`, `GameflowPlayer`, `GameflowStint`, `StintStats`, `PlayByPlayEvent`.

Create `web/src/hooks/useJsonData.ts` with a generic data fetching hook:

```typescript
export function useJsonData<T>(url: string | null) {
  // Uses useState for data, loading, error
  // Uses useEffect to fetch when url changes
  // Returns { data: T | null, loading: boolean, error: Error | null }
  // If url is null, returns { data: null, loading: false, error: null }
}
```

The hook handles: loading states, fetch errors (returns error object, does not crash), null URLs (no-op). This supports AC1.4 — when a date file doesn't exist, the fetch returns a 404 which the hook captures as an error state.

**Testing:**
Tests must verify:
- popcorn-remake.AC1.1: Hook fetches and returns data successfully
- popcorn-remake.AC1.4: Hook handles fetch errors gracefully (sets error state, does not throw)
- Hook handles null URL by returning idle state

**Verification:**
Run: `cd web && npm run test:run`
Expected: All tests pass

**Commit:** `feat: add TypeScript API types and useJsonData hook`
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Home/Scores page with game cards

**Verifies:** popcorn-remake.AC1.1, popcorn-remake.AC1.2, popcorn-remake.AC1.3, popcorn-remake.AC1.4

**Files:**
- Create: `web/src/components/GameCard.tsx`
- Modify: `web/src/pages/HomePage.tsx` (replace placeholder)

**Implementation:**

Before implementing, install the shadcn/ui Card component:
```bash
cd web && npx shadcn@latest add card && cd ..
```

Create `web/src/components/GameCard.tsx` — A card component using shadcn/ui `Card`, `CardHeader`, `CardContent`. Displays:
- Home team tricode and score on the left
- Away team tricode and score on the right
- "Final" status indicator
- Two links: one to `/#/game/{gameId}/boxscore` and one to `/#/game/{gameId}/gameflow`

Use React Router's `Link` component for navigation.

Update `web/src/pages/HomePage.tsx`:
- Fetch `index.json` using `useJsonData<IndexData>`
- For each date in `data.dates` (already sorted most-recent-first by pipeline), render a date heading and list of `GameCard` components
- Show loading spinner while fetching
- Show "No games available" empty state when data is empty or fetch fails (AC1.4)
- Show error message gracefully if fetch fails (not a crash)

**Testing:**
Tests must verify each AC:
- popcorn-remake.AC1.1: HomePage renders games grouped under date headings, most recent first
- popcorn-remake.AC1.2: Each GameCard displays both team names (tricodes) and final scores
- popcorn-remake.AC1.3: Each GameCard contains links to box score and gameflow routes
- popcorn-remake.AC1.4: HomePage shows "No games available" when fetch returns 404 or empty data

Mock `fetch` to return fixture JSON data matching `index.json` contract. Test error case by mocking fetch rejection.

**Verification:**
Run: `cd web && npm run test:run`
Expected: All tests pass

**Commit:** `feat: implement Home/Scores page with game cards`
<!-- END_TASK_2 -->
<!-- END_SUBCOMPONENT_A -->
