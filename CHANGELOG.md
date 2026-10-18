# CHANGELOG

## v2.1.0, 2026-10-17: alternate sources for hand-entered and n/a cells

**Newly automated in `scripts/refresh.py`** (each one fails gracefully and keeps its last good value):
- **TSMC monthly revenue** now comes from SEC EDGAR 6-K filings, which fixes the investor.tsmc.com 403 from Actions. The IR page is kept as a fallback.
- **Hyperscaler capex** for all four now comes from SEC XBRL, on one basis: cash payments for PP&E, discrete quarter, YoY.
  - Quarter ended Jun 30 2026: MSFT $35.8B (+109.6%), GOOGL $44.9B (+100.1%), AMZN $54.2B (+68.4%), META $30.1B (+82.1%).
  - These replace the mixed release figures (MSFT $41.0B and META $31.08B included finance leases). The sum row now reads "same basis and quarter-end".
- **SOXX AUM** comes from the iShares page: $39.34B as of 2026-10-16.
- **Taiwan export orders** come from the MOEA open-data CSV. The cell only advances when the CSV is newer than the stored press figure (Aug $102.96B).
- **DRAM spot, NAND wafer spot and NAND contract** come from the TrendForce public tables.

**Hand-verified this release** (from `scripts/seed_2026-10-17_v2.1.py`):
- **Korea Customs Oct 1–10:** chip exports $12.20B, +170.9% (Confirmed, korea.kr).
- **CoreWeave 5y CDS:** ~1,038bp on Oct 15 (Reported, CNBC citing S&P Global MI).
- **September PC DRAM contract:** DDR4 8GB $148 (+4%) and DDR5 16GB $247 (flat). Reported: TrendForce data via a Daiwa note.
- **CoWoS capacity path:** Goldman Sachs estimate, ~106k/mo avg in 2026 rising to ~227.5k in 2027 (Forecast, via TrendForce 10-16).
- **Tariff/Trade heat cell:** re-sourced to Federal Register Proclamation 11002 (Section 232, 25% on certain advanced chips) and the CRS status as of 9/30. Level unchanged (High).

**Still n/a:**
- Quarterly CoWoS kwpm and utilization (not disclosed by TSMC)
- Taiwan September orders (due ~Oct 20)
- Korea Oct 1–20 days (due Oct 21)

**Workflow:**
- Removed the redundant "Request Pages rebuild" step and the `pages: write` permission. The data commit already triggers the branch build.
- Optional `KOREA_DATA_API_KEY` secret is passed through.

## v2.0.0, 2026-10-17: GitHub Pages rebuild (from the Vercel snapshot, md5 d3a24bd5…)

This version starts from `raw/index.html`, the Vercel build embedded as of Jul 10. It keeps Matt's dark theme, his sidebar plus main layout, the KPI strip, the heat map, the foundry and sector charts, alerts, company tiles and the daily-moves chart.

### 1. Corrected figures (sources are in `data/data.json`; values were checked by hand on 2026-10-17)

**SIA monthly sales:** Jan–Aug 2026, using the latest value SIA has stated for each month.
- Aug **$159.7B, +144.3% YoY, +8% MoM**.
- Jun is now $137.9B (revised from the first print of $134.5B). The Vercel version showed $91.2B.

**2026 projection:**
- SIA (Oct 5) says sales are projected to exceed **$1.6T**.
- The WSTS Spring forecast was $1.5T.
- Deloitte's $975B is kept as a note and marked superseded.

**FRED PCU3344133441:** the full series is now pulled live, so the chart is real FRED data. The heat cell reads +26.0% YoY (Sep'26). The old "+13% since Oct'25" was wrong; FRED shows about +25% for that span.

**Foundry KPI:** IDC's Foundry 2.0 2026 forecast of >$360B (+17%) replaces the unverifiable "$218.8B TTM". It's tagged Reported (via Electronics Weekly), because the IDC primary page is gated.

**KPMG 63:** verified against the 2026 outlook (151 executives, Q4'25 survey). The link now points to the 2026 article.

**Links:**
- The dead Deloitte link is replaced with the current Deloitte Insights URL.
- The dead IDC link is replaced with the Electronics Weekly report.
- SemiAnalysis and All-In now use their canonical hosts.

**Hard-coded values:** none remain in the page. KPIs, alert text, heat cells, tiles and charts all render from `data.json`.

**CoWoS panel:**
- Matt's unsourced quarterly series is removed: CoWoS 40→135k wpm, utilization 93–99%, and the "pressure index", which was never defined. It's preserved in `data/history/2026-07-10-matt-baseline.json`.
- The panel now shows:
  - a verified TSMC monthly revenue chart;
  - reported CoWoS capacity of 120–140k wpm in 2026, with the supply–demand gap narrowing from ~20% to ~10% (Economic Daily via TrendForce, Jun 15);
  - the TSMC Q3 call line "a little bit shortage on the back end" (Oct 15).
- The quarterly CoWoS wpm and utilization cell reads **n/a, source needed**.

**Semi Desk read applied:**
- **Power / Site Capacity: Warming → Hot**, changed 2026-10-17. Evidence: the Texas TCEQ permit freeze, Oregon's statewide DEQ pause to 2027-07-01, and San Francisco's 45-day moratorium signed Oct 16. The SemiAnalysis counterweight is noted in the source tooltip.
- **TSMC / CoWoS stays hot**, relabelled "Tight", per the Oct 15 call.

### 2. Data layer

**Data files:**
- `data/data.json`: every datum carries `{label, url, tag, asOf, cadence}`.
- `data/history/YYYY-MM-DD.json`: one snapshot per run, plus the original Jul 10 baseline.

**`scripts/refresh.py`:** standard library only, no keys. It pulls:
- FRED via fredgraph.csv;
- the newest SIA release, parsed for the value, YoY, the prior-month revision and the full-year projection;
- TSMC IR monthly revenue;
- quotes, trying CNBC's quote service first, then the Nasdaq API, then Yahoo v8, all server-side;
- PCDS, using the public dashboard.json plus the optional local `PCDS_LOCAL`, and never downgrading to an older as-of date.

If a source fails, its last good value and as-of date are kept, so the page marks it STALE. The script always exits 0.

**Workflow:** `.github/workflows/refresh-data.yml` runs weekdays at 12:00 UTC (7am CDT) and on `workflow_dispatch`. It commits the data and requests a Pages build.

**Reload button:** the "↻ Reload data" button re-reads `data/data.json`. It only shows a new time when the reload succeeds. A failure says so and keeps the previous generation time.

**Chart.js failure guard:**
- Chart.js is self-hosted in `vendor/`.
- Event listeners are bound before any chart is drawn.
- If `Chart` is missing, every chart falls back to a data table.
- Each render step is isolated, so one failure can't blank the page.

### 3. Leading Indicators panel (new)

**Foundry:** TSMC monthly revenue (auto).

**Memory (TrendForce public pages):**
- DRAM spot
- DRAM contract
- NAND wafer spot
- NAND contract
- 4Q26 contract forecast, labelled as a forecast

**Exports:**
- Korea chip exports for September (MOTIR)
- Taiwan export orders for August (MOEA via CNA)
- Korea October 1–20 days, and Taiwan September: n/a, not yet released

**Neocloud credit:**
- CoreWeave 2032 note yield (~14.6% on Oct 15, Reported via WSJ/MarketAxess)
- CRWV equity
- CoreWeave CDS: **n/a, source needed**

**Hyperscaler capex for Apr–Jun 2026,** from company releases: MSFT $41B (incl. finance leases), GOOGL $44.9B, AMZN $54.2B, META $31.1B. YoY is shown only where verified (GOOGL +100%, AMZN +68%).

### 4. Real change detection

Each heat cell stores its previous state `{level, value, date}` and a `changed` date. The card shows ▲, ▼ or ● plus either "Last changed …" or "Unchanged since …".

**Rule cells recompute on every refresh,** using v2 default thresholds that Matt can tune in `heatRules`:
- Semi PPI YoY: below 5% is low; 15% or more is high.
- SIA YoY: below 15% is low; 40% or more is high.

On first scoring, both moved to **Hot** (from Firming and Strong).

**Alerts fire only on:**
- a heat-cell state change in the last 14 days;
- a PCDS state flip;
- one of these thresholds:
  - TSMC monthly revenue YoY below +20%
  - SIA sales down month-over-month
  - Korea chip exports negative YoY
  - CoreWeave 2032 yield at 15% or more (watch) or above 18% (trip)
  - SOXX session move of −2% or worse
  - |NVDA − SOXX| greater than 1 pp

The old always-on alerts ("TSMC util 98%", "PPI +13%", "6-month streak") are removed.

### 5. Freshness and labelling

**Chips:** every datum has a source, tag and as-of chip.

**STALE badge** past these limits: daily 4 days, weekly 10, biweekly 21, monthly 45, quarterly 120, annual 400, event 30. Month-precision dates count from the end of the month.

**PCDS tile:** shows the state, score (−2…+2), lead flag and as-of date, and links to https://mcraska.github.io/pcds-dashboard/. It's seeded from Semi Desk `last-state.json` (asof 2026-10-09, −2 bearish, lead ON). The public PCDS site's dashboard.json is older (asof 2026-09-21), so the refresh keeps the newer value.

### Bug fixes

- **Browser calls to Yahoo:** removed. Quotes are fetched server-side.
- **False "live" timestamps after a failed refresh:** fixed.
- **Chart.js CDN failure disabling the button:** fixed.
- **Static "Quotes as of Apr 17" text:** removed. The quote as-of date now comes from the data (Oct 16 close).
- **SOXX:** labelled ETF, with **AUM: n/a, source needed**. CNBC's "market cap" field isn't AUM, so it isn't shown.
- **Contrast:**
  - Muted text changed from #6b7897 (4.0:1) to #8794b0 (5.8:1 on the panel).
  - Up and down colours are now blue and orange (colour-blind-safe), always shown with ▲/▼.
- **Brand colours:** AMD and TSM tags no longer use red (now fuchsia and pink). INTC and MU are brightened.
- **Mobile:**
  - Data now renders before the sidebar. The sidebar is placed after `<main>` in the DOM and laid out with grid areas.
  - New ≤600px single-column layout.
  - Tap targets are at least 44px.
- **Favicon:** added `favicon.svg`, plus meta description and OG tags.
- **"Live" dot:**
  - Green only when data.json is under 2 days old and quotes are under 4 days old; amber otherwise.
  - The pulse stops under `prefers-reduced-motion`.
- **Accessibility:** canvases get `role="img"` and `aria-label`; status uses `aria-live`; the button gets `aria-busy`; a `<noscript>` message is added.
- **Pressure index:** dropped, since it was undefined. Axes are labelled, sales and NT$ axes start at zero, and estimate quarters are no longer mixed in.

### Known gaps (left as "n/a, source needed")

- CoreWeave 5-year CDS: no linkable source.
- TrendForce September DRAM/NAND contract prices: paywalled.
- Korea October 1–20 days chip exports, due ~Oct 21.
- Taiwan September export orders, due ~Oct 20.
- Quarterly CoWoS wpm and utilization.
- SOXX AUM.
- MSFT and META capex YoY.
- The Tariff/Trade cell is still Matt's Jul 10 judgement. It's marked "Matt baseline" and goes STALE.
- Memory, export, capex and credit cells are seeded by hand. The workflow doesn't refresh them yet; they go STALE and must be updated in `data.json` (see DEPLOY.md).
