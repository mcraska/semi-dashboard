#!/usr/bin/env python3
"""Server-side refresh for data/data.json (stdlib only, no API keys required).

Sources (all free, public):
  - FRED PCU3344133441 via fredgraph.csv (no key)
  - SIA latest-news page -> newest monthly sales release (regex parse)
  - TSMC IR monthly revenue table
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
    for fn in (refresh_fred, refresh_sia, refresh_tsmc, refresh_quotes, refresh_pcds):
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
