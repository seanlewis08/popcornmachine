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
- 2026-10-23 (morning): sending Chrome's client-hint and fetch-metadata headers with Python `requests` worked from a home connection (2 games fetched for 2026-10-22) but **still got 403 from GitHub Actions** (run #348, all 22 dates). Datacenter IPs get a stricter check.
- 2026-10-23 (afternoon): switched the HTTP client to [`curl_cffi`](https://github.com/lexiforest/curl_cffi) impersonating Chrome — real Chrome TLS handshake and HTTP/2 fingerprint, with the matching identity headers supplied by the library. Worked immediately from a home IP.
- 2026-10-23 (later): after ~40 requests from the same home IP in one day, the CDN started **slowing** the impersonated client instead of refusing it — `200` responses, but 5–30+ s before the first byte (plain `curl` still got an instant `403`, so the network was fine). With a 30 s timeout the multi-MB schedule file looked "unreachable". Raised `FETCH_TIMEOUT_S` to 120. Every impersonation target behaved the same (chrome136/146, safari184, firefox147), so this is reputation throttling of the address, not a fingerprint problem. *Result from GitHub Actions with curl_cffi: record it here.*

### Slow responses / timeouts (not 403)

**Symptom:** `curl: (28) Operation timed out ... with 0 bytes received`, or responses that take many seconds for small files, while a plain `curl` to the same URL returns `403` instantly.

**Cause:** Akamai's "slow down" action for a client it finds suspicious — typically after a burst of requests. It clears on its own; the pipeline's normal cadence (a handful of requests per game, twice a day) stays well under it. Testing many dates by hand in one sitting is what trips it.

**What to do:** nothing to the code — `FETCH_TIMEOUT_S` (120 s) absorbs it. If you're testing locally, space your runs out, or probe with the small scoreboard file:

```bash
uv run python - <<'PY'
import time
from curl_cffi import requests as r
from pipeline.fetch import _HEADERS, IMPERSONATE
s = time.time()
resp = r.get("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
             headers=_HEADERS, impersonate=IMPERSONATE, timeout=60)
print(resp.status_code, f"{time.time()-s:.1f}s", len(resp.content), "bytes")
PY
```

Under 2 s is normal. 5–30 s means you're being throttled. A `403` means the impersonation itself is being refused — see the next section.

**The fix lives in one place:** `_fetch_json` at the top of `pipeline/fetch.py`, plus the `IMPERSONATE` target and the `_HEADERS` request-context set. `tests/test_fetch.py::TestCdnHeaders` pins all of it, including an end-to-end test through a local echo server that checks what actually goes over the wire.

### How the request is built

Two layers, deliberately separate:

- **Browser identity** (`User-Agent`, `sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`, `Accept-Encoding`) comes from `curl_cffi` for the `IMPERSONATE` target. It is generated to match the TLS fingerprint, so it is always internally consistent. Don't add these to `_HEADERS` — a test fails if you do.
- **Request context** (`Accept`, `Origin`, `Referer`, `Sec-Fetch-Site/Mode/Dest`, `Accept-Language`) is in `_HEADERS` and describes the XHR nba.com's page makes.

### Bumping the Chrome version

Akamai may eventually reject the impersonated Chrome as too old.

1. `uv run python -c "from curl_cffi.requests.impersonate import BrowserTypeLiteral; print(BrowserTypeLiteral)"` lists the targets your installed `curl_cffi` supports. If the newest is still old, `uv lock --upgrade-package curl-cffi` first.
2. Set `IMPERSONATE = "chromeNNN"` in `pipeline/fetch.py`.
3. `uv run pytest tests/test_fetch.py -k TestCdnHeaders`.
4. Run the pipeline locally for yesterday's date, then push and trigger a workflow run — a home connection passing does not prove GitHub's runners pass (see 2026-10-23 above).

### If impersonation is refused (403 again)

Then Akamai is scoring the IP itself, and nothing in the request can fix that. The data has to be fetched from somewhere Akamai trusts:

- **Run the pipeline from your Mac on a schedule** (launchd job, twice a day). It pushes `data/` to GitHub and the deploy workflow takes over exactly as now. The Mac has to be awake; the season-wide backfill catches up any missed days on the next run.
- **Self-hosted GitHub runner on your Mac.** Keeps logs, annotations and the keepalive step in GitHub, with only `runs-on` changing in the workflow. GitHub advises against self-hosted runners on **public** repos (fork PRs can execute on them), so weigh that first.

Before any of that, check what the community libraries did. They hit the same walls weeks before we notice, and their fixes have been copyable each time:

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
