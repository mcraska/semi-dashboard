#!/usr/bin/env python3
"""Server-side refresh for data/data.json (stdlib only, no API keys required).

Sources (all free, public):
  - FRED PCU3344133441 via fredgraph.csv (no key)
  - SIA latest-news page -> newest monthly sales release (regex parse)
  - TSMC monthly revenue: SEC EDGAR 6-K (primary path, Actions-friendly) -> TSMC IR page fallback
  - Hyperscaler capex: SEC XBRL companyconcept (MSFT, GOOGL, AMZN, META)
  - SOXX net assets: iShares fund page
  - Taiwan export orders: MOEA open-data CSV (data.gov.tw 6845)
  - TrendForce public spot pages: DRAM spot, NAND wafer spot, NAND contract (card/UFD)
  - Quotes: CNBC quote web service -> Nasdaq API -> Yahoo v8 chart (first that works)
  - PCDS: https://mcraska.github.io/pcds-dashboard/dashboard.json (+ optional local last-state.json via PCDS_LOCAL)

Rules:
  - A source that fails keeps its previous values and as-of date (so the page shows them as STALE); never invent values.
  - The script always exits 0 so the page never breaks; failures are recorded in data.refreshLog.
  - Rule heat cells (semi_ppi, sales_yoy) are recomputed; a level change records prev state + change date.
  - Each run writes data/history/YYYY-MM-DD.json.
"""
import csv, datetime as dt, io, json, os, re, sys, html, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "data.json")
HIST = os.path.join(ROOT, "data", "history")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36",
      "Accept": "text/html,application/json;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"}
NOW = dt.datetime.now(dt.timezone.utc)
TODAY = (NOW - dt.timedelta(hours=5)).date().isoformat()  # US Central-ish calendar day
MONTHS = {m: i for i, m in enumerate(["january","february","march","april","may","june","july","august","september","october","november","december"], 1)}
LOG = []

def log(source, status, detail=""):
    LOG.append({"source": source, "status": status, "detail": detail[:300], "at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ")})
    print(f"[{status}] {source}: {detail}", file=sys.stderr)

def get(url, timeout=40, headers=None):
    h = dict(UA); h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def text_of(page):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page)))

def src(label, url, tag, asOf, cadence, note=None):
    d = {"label": label, "url": url, "tag": tag, "asOf": asOf, "cadence": cadence}
    if note: d["note"] = note
    return d

# ---------------- FRED ----------------
def refresh_fred(d):
    sid = d["ppi"].get("seriesId", "PCU3344133441")
    try:
        raw, last = None, None
        for attempt in range(3):
            try:
                raw = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", timeout=60,
                          headers={"User-Agent": "semi-dashboard-refresh/1.0 (+https://github.com/mcraska/semi-dashboard)", "Accept": "text/csv,*/*"})
                break
            except Exception as e:
                last = e
        if raw is None: raise last
        rows = [r for r in csv.reader(io.StringIO(raw))][1:]
        series = [{"period": r[0][:7], "value": float(r[1])} for r in rows if len(r) == 2 and r[1] not in (".", "") and r[0] >= "2024-01"]
        if len(series) < 13: raise ValueError(f"only {len(series)} rows")
        d["ppi"]["series"] = series
        d["ppi"].pop("prior", None)
        d["ppi"]["src"]["asOf"] = TODAY
        log("FRED", "ok", f"{sid} through {series[-1]['period']} = {series[-1]['value']}")
    except Exception as e:
        log("FRED", "fail", repr(e))

# ---------------- SIA ----------------
def parse_sia(page_text):
    out = {}
    m = re.search(r"\$([\d.]+) billion during the month of (\w+) (\d{4})", page_text)
    if not m: return None
    val, mon, yr = float(m.group(1)), MONTHS.get(m.group(2).lower()), int(m.group(3))
    if not mon: return None
    out["period"] = f"{yr}-{mon:02d}"; out["valueB"] = val
    py1 = str(yr - 1)
    yoy = re.search(r"([\d.]+)% more than the \w+ " + py1 + r" total", page_text) or \
          re.search(r"increase of ([\d.]+)% compared to (?:the )?\w+ " + py1, page_text)
    out["yoyPct"] = float(yoy.group(1)) if yoy else None
    pm, py = (mon - 1, yr) if mon > 1 else (12, yr - 1)
    prev_name = [k for k, v in MONTHS.items() if v == pm][0]
    rev = re.search(r"compared to the " + prev_name.capitalize() + " " + str(py) + r" total of \$([\d.]+) billion", page_text)
    if rev: out["prevRevision"] = {"period": f"{py}-{pm:02d}", "valueB": float(rev.group(1))}
    rel = re.search(r"WASHINGTON\W+(\w+)\.? (\d{1,2}), (\d{4})", page_text)
    if rel:
        mm = MONTHS.get(rel.group(1).lower()) or {"jan":1,"feb":2,"mar":3,"apr":4,"jun":6,"jul":7,"aug":8,"sep":9,"sept":9,"oct":10,"nov":11,"dec":12}.get(rel.group(1).lower()[:4].rstrip("."), None) \
             or {"jan":1,"feb":2,"mar":3,"apr":4,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}.get(rel.group(1).lower()[:3])
        if mm: out["release"] = f"{rel.group(3)}-{mm:02d}-{int(rel.group(2)):02d}"
    proj = re.search(r"projected to (?:exceed|reach|top|hit) (?:roughly )?\$([\d.]+) trillion", page_text)
    if proj: out["projection"] = proj.group(1)
    return out

def refresh_sia(d):
    try:
        idx = get("https://www.semiconductors.org/news-events/latest-news/")
        links = []
        for u in re.findall(r'https://www\.semiconductors\.org/[a-z0-9-]+/', idx):
            if "semiconductor-sales" in u and u not in links: links.append(u)
        if not links: raise ValueError("no sales-release links on index")
        series = d["sia"]["series"]; known = {s["url"] for s in series}
        added = []
        for u in links[:3]:  # newest few
            if u in known: continue
            p = parse_sia(text_of(get(u)))
            if not p: log("SIA", "warn", f"could not parse {u}"); continue
            p["url"] = u
            rev = p.pop("prevRevision", None); proj = p.pop("projection", None)
            row = next((s for s in series if s["period"] == p["period"]), None)
            if row is None:
                row = {"period": p["period"], "valueB": p["valueB"], "firstPrintB": p["valueB"], "yoyPct": p.get("yoyPct"),
                       "release": p.get("release"), "url": u}
                series.append(row); added.append(p["period"])
            if rev:
                r0 = next((s for s in series if s["period"] == rev["period"]), None)
                if r0: r0["valueB"] = rev["valueB"]
            if proj and p.get("release") and p["release"] >= d["kpis"][0]["src"]["asOf"]:
                d["kpis"][0]["display"] = f">${proj}T" if "exceed" in text_of(get(u)) else f"${proj}T"
                d["kpis"][0]["src"] = src("SIA", u, "Confirmed", p["release"], "monthly")
        series.sort(key=lambda s: s["period"])
        last = series[-1]
        d["sia"]["src"]["asOf"] = last.get("release") or d["sia"]["src"]["asOf"]
        log("SIA", "ok", f"latest {last['period']} ${last['valueB']}B" + (f"; added {added}" if added else "; no new release"))
    except Exception as e:
        log("SIA", "fail", repr(e))

# ---------------- TSMC ----------------
TS_MON = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,"Jul":7,"Aug":8,"Sep":9,"Sept":9,"Oct":10,"Nov":11,"Dec":12}
def refresh_tsmc(d):
    try:
        latest = tsmc_from_edgar(d)
        log("TSMC", "ok", f"EDGAR 6-K latest {latest}"); return
    except Exception as e:
        log("TSMC/6-K", "warn", repr(e) + " -> trying TSMC IR page")
    yr = int(TODAY[:4])
    try:
        t = text_of(get(f"https://investor.tsmc.com/english/monthly-revenue/{yr}"))
        rows = re.findall(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)\.? ([\d,]{6,}) (-?[\d.]+) ?%", t)
        if not rows: raise ValueError("no rows parsed")
        series = {s["period"]: s for s in d["tsmc"]["series"]}
        before = max(series) if series else ""
        for m, v, y in rows:
            p = f"{yr}-{TS_MON[m]:02d}"
            series[p] = {"period": p, "ntdM": int(v.replace(",", "")), "yoyPct": float(y)}
        d["tsmc"]["series"] = [series[k] for k in sorted(series)]
        latest = max(series)
        if latest != before: d["tsmc"]["src"]["asOf"] = TODAY  # first seen
        log("TSMC", "ok", f"latest {latest} NT${series[latest]['ntdM']:,}M ({series[latest]['yoyPct']}% YoY)")
    except Exception as e:
        log("TSMC", "fail", repr(e))

# ---------------- Quotes ----------------
def num(s):
    try: return float(str(s).replace(",", "").replace("%", "").replace("$", ""))
    except Exception: return None

def quotes_cnbc(syms):
    u = ("https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?symbols=" + "%7C".join(syms) +
         "&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json")
    j = json.loads(get(u, timeout=30))
    out = {}
    for q in j["FormattedQuoteResult"]["FormattedQuote"]:
        price = num(q.get("last"))
        if price is None or q.get("code") not in (0, "0", None): continue
        out[q["symbol"]] = {"price": price, "chg": num(q.get("change")), "pct": num(q.get("change_pct")),
                            "mcap": None if q.get("subType") == "Exchange Traded Fund" else q.get("mktcapView"),
                            "asOf": q.get("last_time"), "src": src("CNBC quote service", f"https://www.cnbc.com/quotes/{q['symbol']}", "Reported", q.get("last_time"), "daily", "Regular-session last; server-side fetch")}
    return out

def quote_nasdaq(sym, asset="stocks"):
    j = json.loads(get(f"https://api.nasdaq.com/api/quote/{sym}/info?assetclass={asset}", timeout=30, headers={"Accept": "application/json"}))
    p = j["data"]["primaryData"]
    ts = p.get("lastTradeTimestamp", "")
    try: asof = dt.datetime.strptime(re.sub(r"^.*?([A-Z][a-z]{2} \d{1,2}, \d{4}).*$", r"\1", ts), "%b %d, %Y").date().isoformat()
    except Exception: asof = None
    return {"price": num(p["lastSalePrice"]), "chg": num(p["netChange"]), "pct": num(p["percentageChange"]), "mcap": None, "asOf": asof,
            "src": src("Nasdaq quote API", f"https://www.nasdaq.com/market-activity/stocks/{sym.lower()}", "Reported", asof, "daily")}

def quote_yahoo(sym):
    j = json.loads(get(f"https://query2.finance.yahoo.com/v8/finance/chart/{sym}?range=5d&interval=1d", timeout=30))
    m = j["chart"]["result"][0]["meta"]; prev = m.get("chartPreviousClose") or m.get("previousClose")
    closes = j["chart"]["result"][0]["indicators"]["quote"][0]["close"]; tss = j["chart"]["result"][0]["timestamp"]
    c = [x for x in closes if x is not None]
    price = m["regularMarketPrice"]; prev = c[-2] if len(c) >= 2 else prev
    asof = dt.datetime.fromtimestamp(m.get("regularMarketTime", tss[-1]), dt.timezone.utc).date().isoformat()
    return {"price": price, "chg": price - prev, "pct": (price - prev) / prev * 100, "mcap": None, "asOf": asof,
            "src": src("Yahoo Finance chart (server-side)", f"https://finance.yahoo.com/quote/{sym}", "Reported", asof, "daily")}

def refresh_quotes(d):
    syms = [c["sym"] for c in d["companies"]] + d.get("extraQuotes", [])
    got = {}
    try: got = quotes_cnbc(syms)
    except Exception as e: log("Quotes/CNBC", "fail", repr(e))
    for s in syms:
        if s in got: continue
        for fn in (lambda: quote_nasdaq(s, "etf" if s == "SOXX" else "stocks"), lambda: quote_yahoo(s)):
            try:
                q = fn()
                if q.get("price"): got[s] = q; break
            except Exception as e:
                log(f"Quotes/{s}", "warn", repr(e))
    for s, q in got.items(): d["quotes"][s] = q
    missing = [s for s in syms if s not in got]
    log("Quotes", "ok" if not missing else "partial", f"{len(got)}/{len(syms)} updated" + (f"; kept previous for {missing}" if missing else ""))

# ---------------- PCDS ----------------
def refresh_pcds(d):
    cands = []
    try: cands.append(("public", json.loads(get("https://mcraska.github.io/pcds-dashboard/dashboard.json", timeout=30))))
    except Exception as e: log("PCDS/public", "warn", repr(e))
    lp = os.environ.get("PCDS_LOCAL")
    if lp and os.path.exists(lp):
        try: cands.append(("local", json.load(open(lp))))
        except Exception as e: log("PCDS/local", "warn", repr(e))
    if not cands: log("PCDS", "fail", "no source reachable; kept previous"); return
    origin, j = max(cands, key=lambda c: c[1].get("asof", ""))
    cur = d["pcds"]
    if cur.get("asof") and j.get("asof", "") < cur["asof"]:
        log("PCDS", "ok", f"sources older ({j.get('asof')}) than stored {cur['asof']}; kept"); return
    if cur.get("state_code") is not None and cur.get("state_code") != j.get("state_code"):
        cur["prev"] = {"state_code": cur["state_code"], "state_label": cur.get("state_label"), "asof": cur.get("asof")}
        cur["changed"] = j.get("asof")
    for k in ("asof", "pcds_score", "state_code", "state_label", "lead_flag", "version"): cur[k] = j.get(k)
    cur["label"] = j.get("label_required", cur.get("label"))
    cur["src"] = src("PCDS " + ("dashboard.json (GitHub Pages)" if origin == "public" else "last-state.json (Semi Desk)"),
                     cur["url"], "Desk read", j.get("asof"), "weekly")
    log("PCDS", "ok", f"{origin} asof {j.get('asof')} state {j.get('state_code')} score {j.get('pcds_score')}")


# ---------------- SEC EDGAR helpers ----------------
SEC_UA = os.environ.get("SEC_USER_AGENT", "semi-dashboard/1.0 mcraska@gmail.com")
def sec_get(url, timeout=40):
    return get(url, timeout=timeout, headers={"User-Agent": SEC_UA, "Accept": "application/json,text/html;q=0.9"})

# TSMC monthly revenue from SEC 6-K (works from Actions; tsmc.com 403s there)
def tsmc_from_edgar(d):
    sub = json.loads(sec_get("https://data.sec.gov/submissions/CIK0001046179.json"))["filings"]["recent"]
    hits = [(sub["filingDate"][i], sub["accessionNumber"][i], sub["primaryDocument"][i]) for i, f in enumerate(sub["form"])
            if f == "6-K" and "revenue" in sub["primaryDocument"][i].lower()][:3]
    if not hits: raise ValueError("no revenue 6-Ks in submissions")
    series = {s["period"]: s for s in d["tsmc"]["series"]}
    latest_seen = None
    for fdate, acc, doc in hits:
        url = f"https://www.sec.gov/Archives/edgar/data/1046179/{acc.replace('-', '')}/{doc}"
        t = text_of(sec_get(url))
        m = re.search(r"net revenue for (\w+) (\d{4})", t)
        n = re.search(r"Net Revenue ([\d,]+) ([\d,]+) \(?(-?[\d.]+)\)? ([\d,]+) \(?(-?[\d.]+)\)?", t)
        if not (m and n and MONTHS.get(m.group(1).lower())): log("TSMC/6-K", "warn", f"could not parse {url}"); continue
        mon, yr = MONTHS[m.group(1).lower()], int(m.group(2))
        cur, prior_y = int(n.group(1).replace(",", "")), int(n.group(4).replace(",", ""))
        yoy = round((cur / prior_y - 1) * 100, 1)
        p = f"{yr}-{mon:02d}"
        series[p] = {"period": p, "ntdM": cur, "yoyPct": yoy, "release": fdate, "url": url}
        if latest_seen is None or p > latest_seen[0]: latest_seen = (p, fdate, url)
    if not latest_seen: raise ValueError("no parsable 6-K")
    d["tsmc"]["series"] = [series[k] for k in sorted(series)]
    d["tsmc"]["src"] = src("TSMC monthly revenue 6-K (SEC EDGAR)", latest_seen[2], "Confirmed", latest_seen[1], "monthly",
                           "Filed same day as TSMC's Taiwan release; IR page: https://investor.tsmc.com/english/monthly-revenue")
    return latest_seen[0]

# Hyperscaler capex from XBRL companyconcept (cash payments for PP&E, discrete quarters)
CAPEX_COS = [("Microsoft", "0000789019", "PaymentsToAcquirePropertyPlantAndEquipment"),
             ("Alphabet", "0001652044", "PaymentsToAcquirePropertyPlantAndEquipment"),
             ("Amazon", "0001018724", "PaymentsToAcquireProductiveAssets"),
             ("Meta", "0001326801", "PaymentsToAcquirePropertyPlantAndEquipment")]
def _days(a, b): return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days
def discrete_quarters(rows):
    """rows: XBRL facts with start/end/val. Return {end: (val, fact)} for ~3-month periods, deriving Q2/Q3/Q4 from YTD differences."""
    facts = {}
    for r in rows:
        if r.get("form") not in ("10-Q", "10-K"): continue
        k = (r["start"], r["end"])
        if k not in facts or r["filed"] > facts[k]["filed"]: facts[k] = r
    out = {}
    for (st, en), r in facts.items():
        if 80 <= _days(st, en) <= 100: out[en] = (r["val"], r)
    for (st, en), r in facts.items():
        if en in out or _days(st, en) < 170: continue
        for (st2, en2), r2 in facts.items():
            if st2 == st and 80 <= _days(en2, en) <= 100:
                out[en] = (r["val"] - r2["val"], r); break
    return out

def refresh_capex(d):
    rows, got = [], 0
    old = {r["co"]: r for r in d["capex"]["rows"]}
    for name, cik, concept in CAPEX_COS:
        try:
            j = json.loads(sec_get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json"))
            q = discrete_quarters(j["units"]["USD"])
            end = max(q); val, fact = q[end]
            yago = [e for e in q if 350 <= _days(e, end) <= 380]
            yoy = round((val / q[yago[0]][0] - 1) * 100, 1) if yago else None
            e = dt.date.fromisoformat(end)
            acc = fact["accn"].replace("-", "")
            rows.append({"co": name, "period": f"Qtr ended {e.strftime('%b %d, %Y')}", "periodEnd": end, "valueB": round(val / 1e9, 3),
                         "basis": f"cash payments for PP&E (XBRL {concept})", "yoyPct": yoy,
                         "src": src(f"{name} {fact['form']} (SEC XBRL)", f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/",
                                    "Confirmed", fact["filed"], "quarterly", "Discrete quarter derived from XBRL (YTD differences where needed). Excludes finance leases.")})
            got += 1
        except Exception as ex:
            log(f"Capex/{name}", "fail", repr(ex))
            if name in old: rows.append(old[name])
    if rows:
        d["capex"]["rows"] = rows
        ends = sorted({r.get("periodEnd", "") for r in rows})
        d["capex"]["quarter"] = "Latest reported quarter per company (SEC XBRL)" if len(ends) > 1 else f"Quarter ended {ends[0]}"
        d["capex"]["note"] = "Cash purchases of PP&E from 10-Q/10-K XBRL, one consistent basis; excludes finance leases (MSFT/META headline capex includes them). Q3 2026 prints due late Oct."
    log("Capex/EDGAR", "ok" if got == 4 else "partial", f"{got}/4 companies")

# SOXX fund net assets from the iShares product page
def refresh_soxx_aum(d):
    try:
        t = text_of(get("https://www.ishares.com/us/products/239705/ishares-phlx-semiconductor-etf", timeout=40))
        m = re.search(r'Net Assets of Fund","value":"\$([\d,]+)".{0,160}?"value":"(\w{3} \d{1,2}, \d{4})"', t) or \
            re.search(r"Net Assets of Fund \$?([\d,]+(?:\.\d+)?)[ ]?(?:[MB])? as of (\w{3} \d{1,2}, \d{4})", t)
        if not m: raise ValueError("Net Assets not found")
        asof = dt.datetime.strptime(m.group(2), "%b %d, %Y").date().isoformat()
        d.setdefault("aum", {})["SOXX"] = {"valueB": round(int(m.group(1).replace(",", "")) / 1e9, 2), "asOf": asof,
            "src": src("iShares SOXX fund page", "https://www.ishares.com/us/products/239705/ishares-phlx-semiconductor-etf", "Confirmed", asof, "daily", "Net assets of fund")}
        log("SOXX AUM", "ok", f"${d['aum']['SOXX']['valueB']}B as of {asof}")
    except Exception as e:
        log("SOXX AUM", "fail", repr(e))

# Taiwan export orders from MOEA open-data CSV (data.gov.tw dataset 6845)
def refresh_tw_orders(d):
    try:
        raw = get("https://service.moea.gov.tw/EE520/opendata/b.csv", timeout=40)
        vals = {}
        for r in list(csv.reader(io.StringIO(raw)))[1:]:
            if len(r) >= 3 and r[1].isdigit() and len(r[1]) == 5:
                vals[f"{int(r[1][:3]) + 1911}-{r[1][3:]}"] = float(r[2])
        last = max(vals); y, m = int(last[:4]), int(last[5:])
        yoy = (vals[last] / vals[f"{y-1}-{m:02d}"] - 1) * 100 if f"{y-1}-{m:02d}" in vals else None
        cell = next(l for l in d["leading"] if l["id"] == "tw_orders")
        if cell.get("period") and cell["period"] >= last:
            log("TW orders", "ok", f"CSV latest {last} not newer than stored {cell['period']}; kept"); return
        mon = dt.date(y, m, 1).strftime("%b")
        cell.update({"label": f"Taiwan export orders · {mon}", "period": last, "value": f"${vals[last]/1000:.2f}B",
                     "sub": f"{yoy:+.1f}% YoY (MOEA open data)" if yoy is not None else "MOEA open data", "yoyPct": round(yoy, 1) if yoy is not None else None,
                     "src": src("MOEA open data CSV (data.gov.tw 6845)", "https://data.gov.tw/dataset/6845", "Confirmed", TODAY, "monthly")})
        d["leading"] = [l for l in d["leading"] if l["id"] != "tw_orders_sep" or last < "2026-09"]
        log("TW orders", "ok", f"updated to {last} ${vals[last]:,.0f}M")
    except Exception as e:
        log("TW orders", "fail", repr(e))

# TrendForce public spot pages (DRAM spot, NAND wafer spot, NAND contract)
TF_ITEMS = [("dram_spot", "https://www.trendforce.com/price/dram/dram_spot", "DDR5 16Gb (2Gx8) 4800/5600", 4, "daily", "session avg"),
            ("nand_spot", "https://www.trendforce.com/price/flash/flash_spot", "512Gb TLC", 4, "weekly", "session avg"),
            ("nand_contract", "https://www.trendforce.com/price/flash/flash_spot", "NAND 128Gb 16Gx8 MLC", 2, "biweekly", "avg")]
def refresh_trendforce(d):
    pages, n = {}, 0
    for cid, url, item, avg_idx, cad, word in TF_ITEMS:
        try:
            if url not in pages: pages[url] = text_of(get(url, timeout=40))
            t = pages[url]; i = t.find(item + " ")
            if i < 0: raise ValueError("item not found")
            nums = re.findall(r"-?[\d,]+\.\d+|-?[\d,]+", t[i + len(item):i + len(item) + 160])
            chg = re.search(r"([▲▼—])\s*(-?[\d.]+)\s*%", t[i:i + 200])
            upd = re.findall(r"Last Update (\d{4}-\d{2}-\d{2})", t[:i])
            if not upd: raise ValueError("no date")
            v = float(nums[avg_idx].replace(",", ""))
            cell = next(l for l in d["leading"] if l["id"] == cid)
            cell["value"] = f"${v:,.3f}" if v < 20 else f"${v:,.2f}"
            cell["sub"] = f"{word}, {chg.group(1)}{abs(float(chg.group(2))):.2f}%" if chg else word
            cell["src"] = src("TrendForce DRAMeXchange" if "dram" in url else "TrendForce", url, "Reported", upd[-1], cad)
            n += 1
        except Exception as e:
            log(f"TrendForce/{cid}", "fail", repr(e))
    log("TrendForce", "ok" if n == len(TF_ITEMS) else "partial", f"{n}/{len(TF_ITEMS)} cells")

# ---------------- Derived ----------------
def level_for(v, rule):
    return "low" if v < rule["low_lt"] else ("high" if v >= rule["high_gte"] else "mid")

def set_cell(cell, level, value, note, s):
    cur_level = cell.get("level")
    if cur_level in (None, "auto"):
        cur_level, since = cell["prev"]["level"], cell["prev"]["date"]
        if level != cur_level: cell["changed"] = TODAY
    elif level != cur_level:
        cell["prev"] = {"level": cur_level, "value": cell.get("value"), "date": cell.get("changed") or cell["prev"]["date"]}
        cell["changed"] = TODAY
    cell.update({"level": level, "value": value, "note": note, "src": s})

def derive(d):
    rules = d["heatRules"]; cells = {c["id"]: c for c in d["heat"]}
    ppi = {s["period"]: s["value"] for s in d["ppi"]["series"]}; ppi.update(d["ppi"].get("prior", {}))
    lp = max(k for k in ppi if k >= "2026-01" or True)
    y, m = int(lp[:4]), int(lp[5:])
    base = f"{y-1}-{m:02d}"
    if base in ppi:
        yoy = (ppi[lp] / ppi[base] - 1) * 100
        lv = level_for(yoy, rules["semi_ppi"])
        set_cell(cells["semi_ppi"], lv, rules["semi_ppi"]["words"][lv], f"FRED PPI {yoy:+.1f}% YoY ({lp})",
                 dict(d["ppi"]["src"], tag="Rule", note=f"Rule: <{rules['semi_ppi']['low_lt']}% low, ≥{rules['semi_ppi']['high_gte']}% high"))
    s = d["sia"]["series"][-1]
    if s.get("yoyPct") is not None:
        lv = level_for(s["yoyPct"], rules["sales_yoy"])
        set_cell(cells["sales_yoy"], lv, rules["sales_yoy"]["words"][lv], f"SIA {s['yoyPct']:+.1f}% YoY ({s['period']}, ${s['valueB']}B)",
                 src("SIA monthly release", s["url"], "Rule", s.get("release"), "monthly", f"Rule: <{rules['sales_yoy']['low_lt']}% low, ≥{rules['sales_yoy']['high_gte']}% high"))
    # KPI: latest SIA month
    ser = d["sia"]["series"]; last, prev = ser[-1], (ser[-2] if len(ser) > 1 else None)
    mom = (last["valueB"] / prev["valueB"] - 1) * 100 if prev else None
    mon = dt.date(int(last["period"][:4]), int(last["period"][5:]), 1).strftime("%b %Y")
    k = next(k for k in d["kpis"] if k["id"] == "sia_latest")
    k.update({"title": f"{mon} Global Sales", "display": f"${last['valueB']:.1f}B",
              "mom": round(mom, 1) if mom is not None else None, "yoy": last.get("yoyPct"),
              "sub": "SIA/WSTS 3-mo moving avg", "src": src("SIA", last["url"], "Confirmed", last.get("release"), "monthly")})

def main():
    d = json.load(open(DATA))
    for fn in (refresh_fred, refresh_sia, refresh_tsmc, refresh_quotes, refresh_pcds, refresh_capex, refresh_soxx_aum, refresh_tw_orders, refresh_trendforce):
        try: fn(d)
        except Exception as e: log(fn.__name__, "fail", repr(e))
    try: derive(d)
    except Exception as e: log("derive", "fail", repr(e))
    d["generatedAt"] = NOW.strftime("%Y-%m-%dT%H:%M:%SZ"); d["generatedBy"] = "scripts/refresh.py"
    d["refreshLog"] = LOG
    json.dump(d, open(DATA, "w"), indent=1, ensure_ascii=False)
    os.makedirs(HIST, exist_ok=True)
    snap = {k: v for k, v in d.items() if k != "refreshLog"}
    json.dump(snap, open(os.path.join(HIST, f"{TODAY}.json"), "w"), indent=1, ensure_ascii=False)
    idx = sorted(f for f in os.listdir(HIST) if f.endswith(".json") and f != "index.json")
    json.dump(idx, open(os.path.join(HIST, "index.json"), "w"))
    print(json.dumps({"ok": [l["source"] for l in LOG if l["status"] == "ok"], "notOk": [(l["source"], l["status"]) for l in LOG if l["status"] != "ok"]}))

if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"refresh failed but exiting 0 so the site keeps the last good data.json: {e!r}", file=sys.stderr)
    sys.exit(0)
