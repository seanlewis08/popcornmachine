# Popcorn Remake Implementation Plan

**Goal:** Build a zero-cost NBA game stats viewer with a Python data pipeline and Vite React SPA, deployed via GitHub Pages.

**Architecture:** Python pipeline fetches post-game data from `nba_api`, pre-computes derived metrics, and commits structured JSON files to the repo. A Vite React SPA reads those JSON files at runtime to render three views: home/scores, box score, and gameflow. GitHub Pages serves both the app and data files.

**Tech Stack:** Python 3.11+ (uv), nba_api, Vite, React 18, TypeScript, Tailwind CSS v4, shadcn/ui, React Router v7, Vitest, GitHub Actions, GitHub Pages

**Scope:** 7 phases from original design (phases 1-7)

**Codebase verified:** 2026-02-26 — greenfield project. Phase 1 creates GitHub Actions workflow stubs. Phase 2 creates pipeline. Phase 6 adds cleanup and error handling.

---

## Acceptance Criteria Coverage

This phase implements and tests:

### popcorn-remake.AC5: Automated deployment via GitHub
- **popcorn-remake.AC5.1 Success:** Pipeline runs on cron schedule and commits new data
- **popcorn-remake.AC5.2 Success:** Site auto-deploys when main branch is updated
- **popcorn-remake.AC5.3 Success:** GitHub Pages serves both the app and JSON data files

---

## Phase 7: GitHub Actions & Deployment

**Note:** This is an infrastructure phase. GitHub Actions workflows cannot be tested with automated unit tests — they are verified by reviewing the YAML configuration against the acceptance criteria and by manual deployment testing.

<!-- START_TASK_1 -->
### Task 1: Finalize pipeline workflow with git commit and push

**Verifies:** popcorn-remake.AC5.1

**Files:**
- Modify: `.github/workflows/pipeline.yml` (replace stub from Phase 1)

**Step 1: Replace `.github/workflows/pipeline.yml` contents**

```yaml
name: Data Pipeline

on:
  schedule:
    - cron: "0 6,14 * * *"  # 6 AM and 2 PM UTC
  workflow_dispatch: {}

permissions:
  contents: write

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
        run: uv run pipeline/main.py --cleanup

      - name: Check for changes
        id: changes
        run: |
          git diff --quiet data/ && echo "changed=false" >> $GITHUB_OUTPUT || echo "changed=true" >> $GITHUB_OUTPUT

      - name: Commit and push
        if: steps.changes.outputs.changed == 'true'
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/
          git commit -m "data: update game data $(date -u +%Y-%m-%d)"
          git push
```

**Step 2: Verify YAML is valid**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/pipeline.yml')); print('Valid')"
```

**Step 3: Commit**

```bash
git add .github/workflows/pipeline.yml
git commit -m "feat: finalize pipeline workflow with git commit and push"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Finalize deployment workflow

**Verifies:** popcorn-remake.AC5.2, popcorn-remake.AC5.3

**Files:**
- Modify: `.github/workflows/deploy.yml` (update from Phase 1 stub if needed)

**Step 1: Verify `.github/workflows/deploy.yml`**

The Phase 1 stub already contains the correct deployment workflow. Verify it includes:
- Trigger on push to main branch
- Node.js 20 setup with npm cache
- `npm ci` in web/ directory
- `npm run build` in web/ directory
- `cp -r data/ web/dist/data/` to include JSON data in the deployment
- Upload artifact with `actions/upload-pages-artifact@v3` pointing to `web/dist`
- Deploy with `actions/deploy-pages@v4`

**Step 2: Add Vite base path configuration for GitHub Pages**

Update `web/vite.config.ts` to set the base path for GitHub Pages. The base path should match the repository name:

Add to `vite.config.ts`:
```typescript
export default defineConfig({
  base: process.env.GITHUB_PAGES ? '/<repo-name>/' : '/',
  // ... existing config
});
```

Alternatively, use a simpler approach — set `base: './'` to use relative paths, which works on any hosting:

```typescript
export default defineConfig({
  base: './',
  // ... existing config
});
```

**Step 3: Commit**

```bash
git add .github/workflows/deploy.yml web/vite.config.ts
git commit -m "feat: configure deployment workflow and Vite base path for GitHub Pages"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Commit uv.lock for reproducible builds

**Verifies:** popcorn-remake.AC5.1

**Files:**
- Verify: `uv.lock` is committed (should already be from Phase 1)

**Step 1: Verify uv.lock is tracked**

```bash
git ls-files uv.lock
```
Expected: `uv.lock` appears in output.

**Step 2: If not tracked, add and commit**

```bash
git add uv.lock
git commit -m "chore: ensure uv.lock is committed for reproducible builds"
```

This ensures the GitHub Actions pipeline installs exact dependency versions.

**Step 3: Verify web/package-lock.json is tracked**

```bash
git ls-files web/package-lock.json
```
Expected: `web/package-lock.json` appears in output.

Both lockfiles ensure reproducible builds in CI.
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Verify end-to-end local build

**Files:** None (verification only)

**Step 1: Build the React app**

```bash
cd web && npm run build && cd ..
```
Expected: `web/dist/` created successfully.

**Step 2: Copy data to dist (simulating deploy workflow)**

```bash
cp -r data/ web/dist/data/
```

**Step 3: Serve locally and verify**

```bash
cd web && npx serve dist &
sleep 2
curl -s http://localhost:3000/data/index.json | python3 -m json.tool
kill %1
cd ..
```
Expected: index.json is served correctly from the built app directory.

**Step 4: Verify hash routing works**

```bash
cd web && npx serve dist &
sleep 2
curl -s http://localhost:3000/ | grep -o 'src="[^"]*"'
kill %1
cd ..
```
Expected: HTML file loads with bundled JS that handles hash routing.

This verifies AC5.3 — both the app and JSON data files are served from the same directory.
<!-- END_TASK_4 -->
