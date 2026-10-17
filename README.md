# Semiconductor Industry Dashboard (v2)

**Live site:** https://mcraska.github.io/semi-dashboard/. This is Matt's semi dashboard, now on GitHub Pages; the old Vercel version is retired.

It's a static site: `index.html` reads `data/data.json`. A GitHub Action refreshes that file server-side every weekday morning, so the browser never calls quote APIs.

| Path | What |
|---|---|
| `index.html` | Dashboard: Matt's original look, rendered entirely from `data/data.json` |
| `data/data.json` | Every figure, each with a source, tag (Confirmed / Reported / Forecast / Rule / Desk read / n/a) and as-of date |
| `data/history/` | One snapshot per refresh day, plus `2026-07-10-matt-baseline.json` (the original embedded data) |
| `scripts/refresh.py` | Server-side refresh, Python standard library only and no keys |
| `scripts/seed_2026-10-17.py` | One-time, hand-verified seed (provenance) |
| `.github/workflows/refresh-data.yml` | Runs weekdays at 12:00 UTC (7am CDT) and on manual dispatch |
| `vendor/chart.umd.min.js` | Chart.js 4.4.3, self-hosted so a CDN outage can't break the page |

See `CHANGELOG.md` for what changed from the Vercel version and `DEPLOY.md` for how to operate it.
