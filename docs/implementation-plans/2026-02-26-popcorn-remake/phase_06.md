# Popcorn Remake Implementation Plan

**Goal:** Build a zero-cost NBA game stats viewer with a Python data pipeline and Vite React SPA, deployed via GitHub Pages.

**Architecture:** Python pipeline fetches post-game data from `nba_api`, pre-computes derived metrics, and commits structured JSON files to the repo. A Vite React SPA reads those JSON files at runtime to render three views: home/scores, box score, and gameflow. GitHub Pages serves both the app and data files.

**Tech Stack:** Python 3.11+ (uv), nba_api, Vite, React 18, TypeScript, Tailwind CSS v4, shadcn/ui, React Router v7, Vitest, GitHub Actions, GitHub Pages

**Scope:** 7 phases from original design (phases 1-7)

**Codebase verified:** 2026-02-26 — greenfield project. Phase 2 creates pipeline modules (fetch, transform, write, main).

---

## Acceptance Criteria Coverage

This phase implements and tests:

### popcorn-remake.AC4: Data pipeline maintains current-month data
- **popcorn-remake.AC4.1 Success:** Pipeline purges data from previous months
- **popcorn-remake.AC4.2 Success:** Re-running pipeline for same date produces identical JSON
- **popcorn-remake.AC4.3 Failure:** API unavailability doesn't corrupt existing data files

---

## Phase 6: Monthly Cleanup & Pipeline Hardening

<!-- START_TASK_1 -->
### Task 1: Monthly cleanup module

**Verifies:** popcorn-remake.AC4.1

**Files:**
- Create: `pipeline/cleanup.py`

**Implementation:**

Create `pipeline/cleanup.py` with a function that removes data from previous months:

`cleanup_old_data(data_dir: str = "data", reference_date: str | None = None) -> list[str]`:
- Determines current month from `reference_date` (defaults to today)
- Scans `data/scores/` for date files (YYYY-MM-DD.json) — deletes any where the month differs from current month
- Scans `data/games/` for game directories — reads each game's boxscore.json to check the `date` field, deletes game directory if date is from a previous month
- Updates `data/index.json` — removes date entries from previous months
- Returns list of deleted paths for logging
- Uses `os.path.exists` checks before every delete to avoid errors on missing files
- Handles empty data/ directory gracefully

**Testing:**
Tests must verify:
- popcorn-remake.AC4.1: cleanup_old_data removes score files and game directories from previous months while keeping current month data intact

Set up a temporary directory with fixture data spanning two months. Run cleanup with a reference date in the newer month. Verify old month data is deleted, current month data remains, and index.json is updated.

**Verification:**
Run: `uv run pytest tests/ -v`
Expected: All tests pass

**Commit:** `feat: add monthly cleanup module for data retention`
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Idempotent pipeline writes

**Verifies:** popcorn-remake.AC4.2

**Files:**
- Modify: `pipeline/write.py` (ensure idempotent behavior)

**Implementation:**

Update `pipeline/write.py` to ensure idempotent writes:
- All JSON files are written with `json.dump(data, f, indent=2, sort_keys=True)` — `sort_keys=True` ensures deterministic key ordering
- `write_index` merges by replacing existing date entries (not appending duplicates) — compare by `date` field
- All write functions use atomic writes: write to `.tmp` file first, then `os.replace()` to target path
- Float values in derived metrics are rounded to consistent precision (2 decimal places for prod, integers for hv and eff)

**Testing:**
Tests must verify:
- popcorn-remake.AC4.2: Running the pipeline twice for the same date produces byte-identical JSON output

Create fixture input data. Run transform + write once, capture output. Run again with same input, compare output byte-for-byte using file hashing.

**Verification:**
Run: `uv run pytest tests/ -v`
Expected: All tests pass

**Commit:** `feat: ensure idempotent pipeline writes with deterministic JSON output`
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Error handling and data protection

**Verifies:** popcorn-remake.AC4.3

**Files:**
- Modify: `pipeline/main.py` (add error handling around fetch calls)
- Modify: `pipeline/fetch.py` (enhance error handling)

**Implementation:**

Update `pipeline/fetch.py`:
- Each fetch function already returns None on failure (from Phase 2)
- Add retry logic: on `requests.exceptions.RequestException`, wait 5 seconds and retry once before returning None
- Log all failures to stderr with timestamp, endpoint name, and error message

Update `pipeline/main.py`:
- Before writing any data, verify all transforms succeeded
- If any game fails to fetch/transform, skip that game but continue processing others
- Only write `index.json` and score files AFTER all successful game data is written
- Never delete existing valid data if the pipeline run fails partway through
- Add `--cleanup` CLI flag that runs `cleanup_old_data` only when explicitly requested (not by default)
- Log summary at end: "Processed N games for {date}. Skipped M games due to errors."

The key protection: existing data files are only overwritten when new data is successfully transformed. A failed API call results in the game being skipped, not in corrupted or deleted files.

**Testing:**
Tests must verify:
- popcorn-remake.AC4.3: When fetch functions return None (simulating API unavailability), existing data files in the data directory are not modified or deleted

Set up a temporary data directory with pre-existing valid fixture data. Mock fetch functions to return None for all calls. Run the main pipeline. Verify all pre-existing files are unchanged (compare file contents/hashes).

**Verification:**
Run: `uv run pytest tests/ -v`
Expected: All tests pass

**Commit:** `feat: add error handling to protect existing data from API failures`
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Integrate cleanup into main pipeline

**Verifies:** popcorn-remake.AC4.1

**Files:**
- Modify: `pipeline/main.py` (add cleanup integration)

**Implementation:**

Update `pipeline/main.py` to call `cleanup_old_data()` when the `--cleanup` flag is passed:

```python
if args.cleanup:
    deleted = cleanup_old_data(data_dir=args.data_dir)
    if deleted:
        print(f"Cleaned up {len(deleted)} old data files")
```

The cleanup runs AFTER successful data writes, ensuring new data is in place before old data is removed.

**Testing:**
Tests must verify:
- popcorn-remake.AC4.1: Running `pipeline/main.py --cleanup` purges previous-month data after writing new data

Integration test: set up fixture data from two months, mock fetch to return current-month data, run pipeline with --cleanup, verify old month removed and new data written.

**Verification:**
Run: `uv run pytest tests/ -v`
Expected: All tests pass

**Commit:** `feat: integrate monthly cleanup into pipeline CLI`
<!-- END_TASK_4 -->
