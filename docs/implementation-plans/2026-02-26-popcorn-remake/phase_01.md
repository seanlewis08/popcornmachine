# Popcorn Remake Implementation Plan

**Goal:** Build a zero-cost NBA game stats viewer with a Python data pipeline and Vite React SPA, deployed via GitHub Pages.

**Architecture:** Python pipeline fetches post-game data from `nba_api`, pre-computes derived metrics, and commits structured JSON files to the repo. A Vite React SPA reads those JSON files at runtime to render three views: home/scores, box score, and gameflow. GitHub Pages serves both the app and data files.

**Tech Stack:** Python 3.11+ (uv), nba_api, Vite, React 18, TypeScript, Tailwind CSS v4, shadcn/ui, React Router v7 (hash routing), Vitest, GitHub Actions, GitHub Pages

**Scope:** 7 phases from original design (phases 1-7)

**Codebase verified:** 2026-02-26 — greenfield project, no existing code or configuration

---

## Phase 1: Project Scaffolding

**Verifies:** None — infrastructure phase, verified operationally

---

<!-- START_TASK_1 -->
### Task 1: Initialize Python pipeline with uv

**Files:**
- Create: `pyproject.toml`
- Create: `pipeline/__init__.py`
- Create: `pipeline/main.py`
- Create: `.python-version`

**Step 1: Initialize the Python project at the repo root**

Run:
```bash
uv init --name popcorn-remake
```

This creates `pyproject.toml`, `.python-version`, and a sample `main.py`. Delete the sample `main.py` (we'll create our own in `pipeline/`).

**Step 2: Edit `pyproject.toml`**

Replace the generated `pyproject.toml` with:

```toml
[project]
name = "popcorn-remake"
version = "0.1.0"
description = "NBA game stats data pipeline"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "nba_api",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

**Step 3: Create `pipeline/__init__.py`**

Create an empty file:
```python
```

**Step 4: Create `pipeline/main.py`**

```python
"""Popcorn Remake data pipeline entry point."""


def main() -> None:
    print("Pipeline placeholder — will be implemented in Phase 2")


if __name__ == "__main__":
    main()
```

**Step 5: Install dependencies and verify**

Run:
```bash
uv sync
```
Expected: Dependencies install successfully, `uv.lock` is created.

Run:
```bash
uv run pipeline/main.py
```
Expected: Prints "Pipeline placeholder — will be implemented in Phase 2"

**Step 6: Commit**

```bash
git add pyproject.toml uv.lock .python-version pipeline/
git commit -m "chore: initialize Python pipeline with uv and nba_api dependency"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Scaffold Vite React TypeScript app in web/

**Files:**
- Create: `web/` directory (Vite scaffold)
- Modify: `web/package.json` (add scripts)

**Step 1: Scaffold the Vite project**

Run from repo root:
```bash
npm create vite@latest web -- --template react-ts
```

This creates the `web/` directory with a standard Vite React TypeScript project.

**Step 2: Install dependencies**

Run:
```bash
cd web && npm install && cd ..
```

**Step 3: Verify dev server starts**

Run:
```bash
cd web && npm run dev -- --host 0.0.0.0 &
sleep 3
curl -s http://localhost:5173 | head -5
kill %1
cd ..
```
Expected: HTML output from Vite dev server.

**Step 4: Verify production build**

Run:
```bash
cd web && npm run build && cd ..
```
Expected: `web/dist/` directory created with bundled assets.

**Step 5: Commit**

```bash
git add web/
git commit -m "chore: scaffold Vite React TypeScript app in web/"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Add Tailwind CSS v4 to web app

**Files:**
- Modify: `web/package.json` (new dependencies)
- Modify: `web/vite.config.ts` (Tailwind plugin)
- Modify: `web/src/index.css` (Tailwind import)

**Step 1: Install Tailwind CSS v4**

Run:
```bash
cd web && npm install tailwindcss @tailwindcss/vite && cd ..
```

**Step 2: Update `web/vite.config.ts`**

Replace contents with:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

**Step 3: Replace `web/src/index.css` contents**

```css
@import "tailwindcss";
```

**Step 4: Verify Tailwind works**

Replace `web/src/App.tsx` contents with:

```tsx
function App() {
  return (
    <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
      <h1 className="text-4xl font-bold">Popcorn Remake</h1>
    </div>
  );
}

export default App;
```

Run:
```bash
cd web && npm run build && cd ..
```
Expected: Build succeeds. The output CSS includes Tailwind utilities.

**Step 5: Commit**

```bash
git add web/
git commit -m "chore: add Tailwind CSS v4 to web app"
```
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Set up shadcn/ui

**Files:**
- Modify: `web/tsconfig.json` (path aliases)
- Modify: `web/tsconfig.app.json` (path aliases)
- Create: `web/components.json` (shadcn config)
- Create: `web/src/lib/utils.ts` (cn utility)
- Create: `web/src/components/ui/` (component directory)

**Step 1: Update TypeScript path aliases**

Add to `web/tsconfig.json` `compilerOptions`:
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

Add the same `baseUrl` and `paths` to `web/tsconfig.app.json` `compilerOptions`.

**Step 2: Initialize shadcn/ui**

Run:
```bash
cd web && npx shadcn@latest init && cd ..
```

When prompted, accept defaults (New York style, Zinc color). This creates `components.json` and `src/lib/utils.ts`.

**Step 3: Add a test component to verify setup**

Run:
```bash
cd web && npx shadcn@latest add button card && cd ..
```

**Step 4: Verify build still works**

Run:
```bash
cd web && npm run build && cd ..
```
Expected: Build succeeds with shadcn/ui components available.

**Step 5: Commit**

```bash
git add web/
git commit -m "chore: set up shadcn/ui with button and card components"
```
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Configure React Router with hash routing

**Files:**
- Modify: `web/package.json` (new dependency)
- Create: `web/src/pages/HomePage.tsx`
- Create: `web/src/pages/BoxScorePage.tsx`
- Create: `web/src/pages/GameflowPage.tsx`
- Create: `web/src/router.tsx`
- Modify: `web/src/main.tsx` (use router)

**Step 1: Install React Router**

Run:
```bash
cd web && npm install react-router-dom && cd ..
```

**Step 2: Create placeholder page components**

Create `web/src/pages/HomePage.tsx`:
```tsx
export default function HomePage() {
  return <div className="p-4"><h1 className="text-2xl font-bold">Scores</h1></div>;
}
```

Create `web/src/pages/BoxScorePage.tsx`:
```tsx
import { useParams } from "react-router-dom";

export default function BoxScorePage() {
  const { gameId } = useParams<{ gameId: string }>();
  return <div className="p-4"><h1 className="text-2xl font-bold">Box Score: {gameId}</h1></div>;
}
```

Create `web/src/pages/GameflowPage.tsx`:
```tsx
import { useParams } from "react-router-dom";

export default function GameflowPage() {
  const { gameId } = useParams<{ gameId: string }>();
  return <div className="p-4"><h1 className="text-2xl font-bold">Gameflow: {gameId}</h1></div>;
}
```

**Step 3: Create `web/src/router.tsx`**

```tsx
import { createHashRouter } from "react-router-dom";
import HomePage from "@/pages/HomePage";
import BoxScorePage from "@/pages/BoxScorePage";
import GameflowPage from "@/pages/GameflowPage";

export const router = createHashRouter([
  {
    path: "/",
    element: <HomePage />,
  },
  {
    path: "/game/:gameId/boxscore",
    element: <BoxScorePage />,
  },
  {
    path: "/game/:gameId/gameflow",
    element: <GameflowPage />,
  },
]);
```

**Step 4: Update `web/src/main.tsx`**

Replace contents with:
```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "@/router";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
);
```

**Step 5: Delete `web/src/App.tsx` and `web/src/App.css`**

These are no longer needed since routing replaces the single App component.

**Step 6: Verify build and routing**

Run:
```bash
cd web && npm run build && cd ..
```
Expected: Build succeeds.

**Step 7: Commit**

```bash
git add web/
git commit -m "chore: configure React Router with hash routing and placeholder pages"
```
<!-- END_TASK_5 -->

<!-- START_TASK_6 -->
### Task 6: Create sample JSON fixtures in data/

**Files:**
- Create: `data/index.json`
- Create: `data/scores/2026-01-19.json`
- Create: `data/games/0022500001/boxscore.json`
- Create: `data/games/0022500001/gameflow.json`

**Step 1: Create directory structure**

```bash
mkdir -p data/scores data/games/0022500001
```

**Step 2: Create `data/index.json`**

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

**Step 3: Create `data/scores/2026-01-19.json`**

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

**Step 4: Create `data/games/0022500001/boxscore.json`**

Use the exact contract from the design plan — a complete boxscore JSON with at least one player entry per team, team totals, and period totals. Include all fields from the API contract (gameId, date, homeTeam, awayTeam, players with totals and stints, teamTotals, periodTotals).

**Step 5: Create `data/games/0022500001/gameflow.json`**

Use the exact contract from the design plan — a complete gameflow JSON with at least one player entry per team, each with stints containing stats and events arrays.

**Step 6: Verify JSON is valid**

Run:
```bash
python3 -c "import json; [json.load(open(f)) for f in ['data/index.json', 'data/scores/2026-01-19.json', 'data/games/0022500001/boxscore.json', 'data/games/0022500001/gameflow.json']]; print('All JSON valid')"
```
Expected: "All JSON valid"

**Step 7: Commit**

```bash
git add data/
git commit -m "chore: add sample JSON fixtures matching API contracts"
```
<!-- END_TASK_6 -->

<!-- START_TASK_7 -->
### Task 7: Configure Vite to serve JSON fixtures and set up Vitest

**Files:**
- Modify: `web/vite.config.ts` (public dir, base path)
- Modify: `web/package.json` (test scripts)
- Create: `web/src/test/setup.ts`

**Step 1: Update `web/vite.config.ts`**

Add configuration so Vite serves the `data/` directory during development and the build copies it:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {},
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
```

**Step 2: Create `web/src/test/setup.ts`**

```typescript
import "@testing-library/jest-dom";
```

**Step 3: Install test dependencies**

Run:
```bash
cd web && npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom && cd ..
```

**Step 4: Add test script to `web/package.json`**

Add to the `scripts` section:
```json
{
  "scripts": {
    "test": "vitest",
    "test:run": "vitest run"
  }
}
```

**Step 5: Verify Vitest runs**

Run:
```bash
cd web && npm run test:run && cd ..
```
Expected: Vitest runs (may report "No test files found" which is fine at this stage).

**Step 6: Commit**

```bash
git add web/
git commit -m "chore: configure Vitest and test utilities"
```
<!-- END_TASK_7 -->

<!-- START_TASK_8 -->
### Task 8: Create GitHub Actions workflow stubs

**Files:**
- Create: `.github/workflows/pipeline.yml`
- Create: `.github/workflows/deploy.yml`

**Step 1: Create workflows directory**

```bash
mkdir -p .github/workflows
```

**Step 2: Create `.github/workflows/pipeline.yml`**

```yaml
name: Data Pipeline

on:
  schedule:
    - cron: "0 6,14 * * *"  # 6 AM and 2 PM UTC
  workflow_dispatch: {}

jobs:
  fetch-data:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - name: Install dependencies
        run: uv sync
      - name: Run pipeline
        run: echo "Pipeline placeholder — will be implemented in Phase 2"
      # TODO Phase 7: Add git commit and push steps
```

**Step 3: Create `.github/workflows/deploy.yml`**

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch: {}

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: web/package-lock.json
      - name: Install dependencies
        run: cd web && npm ci
      - name: Build
        run: cd web && npm run build
      - name: Copy data to dist
        run: cp -r data/ web/dist/data/
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: web/dist

  deploy:
    environment:
      name: github-pages
      url: ${{ github.pages.url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy to GitHub Pages
        uses: actions/deploy-pages@v4
```

**Step 4: Verify YAML is valid**

Run:
```bash
python3 -c "import yaml; [yaml.safe_load(open(f)) for f in ['.github/workflows/pipeline.yml', '.github/workflows/deploy.yml']]; print('YAML valid')"
```
Expected: "YAML valid" (install PyYAML first if needed: `pip install pyyaml`)

**Step 5: Commit**

```bash
git add .github/
git commit -m "chore: add GitHub Actions workflow stubs for pipeline and deployment"
```
<!-- END_TASK_8 -->

<!-- START_TASK_9 -->
### Task 9: Update .gitignore for full project

**Files:**
- Modify: `.gitignore`

**Step 1: Replace `.gitignore` contents**

```gitignore
# Worktrees
.worktrees/

# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/

# Node
node_modules/
web/dist/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Environment
.env
.env.local
```

**Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: update .gitignore for Python and Node project"
```
<!-- END_TASK_9 -->
