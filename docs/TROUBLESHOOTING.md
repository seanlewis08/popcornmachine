# Troubleshooting the data pipeline

**Last updated:** 2026-10-23

Start here when the site at `seanlewis08.github.io/popcornmachine` stops showing new games.

## 30-second diagnosis

1. Open **GitHub → Actions → Data Pipeline**.
2. Look at the left sidebar. If it says **Disabled** next to Data Pipeline, see [Schedule got disabled](#schedule-got-disabled).
3. Look at the most recent run. Red X → open it, click the `fetch-data` job, read the annotations at the top. They name the problem and link back here.
4. Green check but no new data → that shouldn't happen anymore (the job now fails when a fetch fails). If it does, open the run and check whether "Commit and push" was skipped.

## Run the pipeline locally

Faster than waiting on a workflow run, and the output is the same.

```bash
cd ~/DataspellProjects/popcornmachine
git pull
uv run python -m pipeline.main --date 2026-10-22   # yesterday's date, YYYY-MM-DD
echo "exit code: $?"
```

What you want to see:

```
Running pipeline for 2026-10-22
Fetching scoreboard for 2026-10-22...
Transforming scores...
Found 2 games
Processing game 0022600006...
Wrote game data for 0022600006
...
Pipeline complete for 2026-10-22. Processed 2 games ...
exit code: 0
```

Exit codes:

| Code | Meaning | What to do |
|------|---------|------------|
| 0 | Worked. "No games found" with exit 0 is also fine (off day). | Nothing. |
| 2 | The NBA CDN was unreachable. The log will show `Error fetching ... 403` (blocked) or a timeout. | See [NBA CDN returns 403](#nba-cdn-returns-403-access-denied). |
| 1 | Python crashed. There's a traceback above. | A real bug; the traceback says where. |

If it works locally but fails on GitHub Actions, the CDN is blocking GitHub's IP range specifically. That hasn't happened yet, but see [If headers stop working](#if-headers-stop-working).

## NBA CDN returns 403 Access Denied

**Symptom:** every date fails with

```
Error fetching https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json: 403 Client Error: Forbidden
```

**Cause:** `cdn.nba.com` sits behind Akamai Bot Manager. It serves the JSON only to requests that look like the XHR calls nba.com's own pages make. Anything that looks scripted gets an HTML "Access Denied" page with status 403.

**History:**

- Feb 2026: `stats.nba.com` started blocking cloud IPs. Pipeline moved to `cdn.nba.com`.
- 2026-06-16: `cdn.nba.com` started rejecting our header set over HTTP/1.1 (which is what Python `requests` speaks). Every run from then until 2026-08-15 fetched nothing and reported success. See [Why the job used to stay green](#why-the-job-used-to-stay-green).
- 2026-10-23: fixed by sending Chrome's client-hint and fetch-metadata headers. Verified locally the same day: 2 games fetched for 2026-10-22.

**The fix lives in one place:** `_HEADERS` at the top of `pipeline/fetch.py`. Four tests in `tests/test_fetch.py::TestCdnHeaders` pin the header set so it can't regress by accident.

### Bumping the Chrome version

Akamai may eventually reject Chrome 140 as too old. To update:

1. Open Chrome, go to `https://www.nba.com`, open DevTools → Network, reload, click any request to `cdn.nba.com`.
2. Copy these request headers **exactly**: `sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`, `User-Agent`.
3. Paste them into `_HEADERS` in `pipeline/fetch.py`.
4. Run `uv run pytest tests/test_fetch.py -k TestCdnHeaders`. The version test fails if `sec-ch-ua` and `User-Agent` disagree.
5. Run the pipeline locally for yesterday's date to confirm the CDN accepts it.

Copy the whole `sec-ch-ua` value. Chromium derives the placeholder brand (`"Not=A?Brand"`) and the brand order from the major version, so editing only the numbers produces a combination no real Chrome ever sends.

### If headers stop working

Next escalation: Akamai starts checking the TLS fingerprint, which headers can't fake. Plain `curl` already fails this way (it's refused even with the full header set). The fix is to replace `requests` with [`curl_cffi`](https://github.com/lexiforest/curl_cffi), which impersonates Chrome's TLS handshake:

```python
from curl_cffi import requests  # drop-in: requests.get(url, headers=..., impersonate="chrome")
```

Only `_fetch_json` in `fetch.py` makes HTTP calls, so this is a contained change.

Before doing that, check what the community libraries did. They hit the same walls weeks before we notice, and their fixes have been copyable each time:

- https://github.com/sportsdataverse/hoopR/pulls (R, but documents the exact headers and what was tested)
- https://github.com/swar/nba_api/pulls (Python)

Search for "cdn.nba.com", "403", or "Access Denied".

### Last resort: a different data source

ESPN's unofficial API (`site.api.espn.com/apis/site/v2/sports/basketball/nba/...`) has scores, box scores, and play-by-play including substitutions. It's a multi-day rewrite: different game and player IDs, different play types, different clock format, and `transform.py` is written against the NBA shapes. Only go here if the NBA CDN is gone for good.

## Schedule got disabled

**Symptom:** the Actions sidebar shows **Disabled** next to Data Pipeline. Runs stopped on a date 60 days after the last commit to the repo.

**Cause:** GitHub disables scheduled workflows after 60 days with no commits. During the offseason there's nothing to commit, so this happened on 2026-08-15 (60 days after the last data commit on 2026-06-16).

**Fix:** Actions → Data Pipeline → **Enable workflow**. Then trigger a run with **Run workflow** to confirm it works.

**Prevention:** the workflow's "Keep schedule enabled" step calls the enable API on every run, which resets GitHub's 60-day clock. It should not happen again unless that step is removed or the workflow stops running entirely for 60 days (which would mean GitHub Actions itself was broken).

## Why the job used to stay green

Before 2026-10-23 the backfill loop ran `pipeline.main ... || echo "Warning: ..."`, so a date that failed to fetch printed a warning and the job finished green. The pipeline also exited 0 on an unreachable API because it's designed to write nothing and retry next time. The combination meant a four-month outage with 120 green runs.

Now:

- `pipeline.main` exits 2 when the schedule/scoreboard API is unreachable (`EXIT_API_UNREACHABLE` in `pipeline/main.py`).
- The workflow records every date that exited non-zero, writes a `::error::` annotation for each, commits and deploys whatever did fetch, then fails the job. A failed scheduled run emails the repo owner.

Expect two failure emails a day during an outage. That's the point. If it's genuinely a long outage you can't fix yet, disable the workflow manually rather than silencing the failure.

## Backfill and cleanup behaviour

Scheduled runs don't just fetch yesterday. They walk every date from the season's start (Oct 1) to yesterday and fetch any date without a `data/scores/YYYY-MM-DD.json` file. Existing dates are skipped by a file check, so this costs nothing extra, and after any outage the first successful run catches up on the whole gap (as long as the CDN still serves those games; the live endpoints have kept games for well over a year so far).

A date with zero games writes an empty `[]` scores file so it isn't retried forever. A date where the API failed writes nothing, so it is retried.

Only regular-season, play-in, and playoff games are kept. Preseason and All-Star games are dropped by their game-ID prefix (`001…` and `003…`) in `fetch_scoreboard`.

Cleanup (`--cleanup`) keeps the current season and deletes everything from earlier seasons. A season runs Oct 1 → Sep 30 and is named by its start year (`pipeline/season.py`). Cleanup only runs on the final "yesterday" invocation and only if that day had games, so last season survives the summer and disappears on the first game day of the new one. To check what a date maps to:

```bash
uv run python -c "from pipeline.season import season_for; print(season_for('2027-07-04'))"   # 2026-27
```

Size budget: ~180 KB per game, ~220 MB per season. GitHub Pages caps a site at 1 GB, so one season at a time is comfortable; keeping several would not be.

## Checking the live site's data

The deployed site reads `data/index.json` relative to itself. The deploy workflow copies `data/` into `web/dist/data/` at build time, so the site shows whatever was in the repo at the last deploy, not the latest commit. If data is committed but the site is stale, check that **Deploy to GitHub Pages** ran after the data commit. The pipeline triggers it with `gh workflow run deploy.yml`; a push to `main` also triggers it.
