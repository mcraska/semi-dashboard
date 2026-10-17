# DEPLOY: Matt's semi dashboard on GitHub Pages

- **Repo:** https://github.com/mcraska/semi-dashboard (public)
- **Site:** https://mcraska.github.io/semi-dashboard/
- **Setup:** same as PCDS. Pages uses a legacy build from branch `master`, path `/`. There's no build step, and `.nojekyll` is present.

## Publish a change (same pattern as PCDS `publish_github.sh`)
```bash
cd /workspace/sources/semis/matt-semi-dashboard/v2
git add -A && git -c user.email="mcraska@gmail.com" -c user.name="Matt C" commit -m "dashboard: <what>"
git push origin master
gh api repos/mcraska/semi-dashboard/pages/builds -X POST >/dev/null || true
```
Pages usually updates within a minute or two. Hard-refresh the browser if the CDN copy lags.

## Scheduled data refresh
- **Workflow:** `.github/workflows/refresh-data.yml`.
- **Schedule:** cron `0 12 * * 1-5`, which is 7:00 AM CDT, or 6:00 AM CST after Nov 1. For 7am CST in winter, change it to `0 13 * * 1-5`. GitHub cron is UTC-only and can start late at busy times.
- **Run it now:** `gh workflow run refresh-data.yml -R mcraska/semi-dashboard`, or use Actions → "Refresh dashboard data" → Run workflow.
- **Watch it:** `gh run list -R mcraska/semi-dashboard -w refresh-data.yml` and `gh run view <id> --log`.
- **No API keys or secrets needed.** Every source is a free public page or endpoint.
- **When a source fails:** its last good value stays and turns STALE on the page. The job still succeeds, and the reason is printed in the job log and in the page footer under "Last refresh log".
- **GitHub auto-disables scheduled workflows** after 60 days with no repo activity. The daily data commits normally keep it alive. If it gets disabled, re-enable it in the Actions tab.
- **Optional paid sources:** if you later add one (for example a TrendForce contract feed or a quotes API key), store it in repo Settings → Secrets → Actions. Read it in `refresh.py` via `os.environ`, and skip that source when the variable is absent, so the page never fails.

## What the workflow refreshes automatically
| Section | Source | Cadence |
|---|---|---|
| Semi PPI and the PPI heat cell | FRED PCU3344133441 (fredgraph.csv) | monthly |
| SIA monthly sales, YoY, revisions, the projection KPI, the Sales YoY heat cell | Newest release on semiconductors.org/news-events/latest-news | monthly (~1st week) |
| TSMC monthly revenue (chart + leading cell) | investor.tsmc.com monthly-revenue | monthly (~10th) |
| Quotes for 7 names + CRWV | CNBC quote service → Nasdaq API → Yahoo v8 | daily |
| PCDS tile | mcraska.github.io/pcds-dashboard/dashboard.json (newest as-of wins) | when PCDS publishes |

## Updated by hand in `data/data.json` (until automated)
- **Memory pricing:** the TrendForce public price pages.
- **Korea chip exports:** MOTIR, 1st of the month.
- **Taiwan export orders:** MOEA, ~20th of the month.
- **Hyperscaler capex:** quarterly, late Jan/Apr/Jul/Oct.
- **CoreWeave 2032 yield:** press or TRACE.
- **Judgement heat cells** (`"mode":"manual"`): when you move one, follow these steps:
  1. Copy its current `{level, value, date}` into `prev`.
  2. Set `changed` to today.
  3. Update `level`, `value`, `note` and `src`.

  The arrow, "last changed" text and alert follow automatically.
- **Never enter a number without `src.url` and `src.asOf`.** Use `"value": null` to show "n/a, source needed".

## Local preview
```bash
cd v2 && python3 -m http.server 8000   # http://localhost:8000
PCDS_LOCAL=/workspace/sources/semis/pc-demand-signal/last-state.json python3 scripts/refresh.py   # optional local refresh
```

## Retired
The Vercel copy at https://semi-dashboard-alpha.vercel.app was retired by Matt. It wasn't modified or redeployed in this work.
