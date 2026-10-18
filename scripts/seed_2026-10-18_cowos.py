"""v2.1.1 CoWoS facts refresh (2026-10-18).

Replaces the June-15 capacity and gap cells (past the 120-day quarterly stale
window) with side-by-side Reported estimates from Silicon Analysts, UAnalyze and
MoneyDJ. Keeps the Goldman path (Forecast) and the TSMC Q3 call (Confirmed).
Does not touch heat-map cells. Run once; refresh.py never overwrites cowos.facts.
"""
import json, pathlib
P = pathlib.Path(__file__).resolve().parent.parent / "data" / "data.json"
d = json.loads(P.read_text())

def src(label, url, tag, asOf, cadence, note=None):
    s = {"label": label, "url": url, "tag": tag, "asOf": asOf, "cadence": cadence}
    if note: s["note"] = note
    return s

# Preserve Confirmed call and Goldman Forecast if present; rebuild the rest.
by_label = {f.get("label"): f for f in d["cowos"]["facts"]}
q3 = by_label.get("TSMC Q3'26 call (C.C. Wei)")
goldman = by_label.get("CoWoS capacity path (Goldman Sachs est.)")
if goldman is None:
    goldman = {
        "label": "CoWoS capacity path (Goldman Sachs est.)",
        "value": "~106k/mo avg 2026 → ~227.5k 2027 → ~290k 2028",
        "sub": "1.275M wafers 2026, 2.73M 2027 (+114%), 3.48M 2028. Quarterly kwpm & utilization: n/a, source needed (TSMC does not disclose)",
        "src": src("Goldman Sachs via TrendForce 2026-10-16",
                   "https://www.trendforce.com/news/2026/10/16/news-after-tsmcs-3q26-earnings-key-brokerage-takeaways-as-2028-capex-forecasts-reach-us105b/",
                   "Forecast", "2026-10-16", "quarterly",
                   "Tried: TrendForce, Digitimes (96.2% is TSMC overall utilization, not CoWoS), Morgan Stanley via press, TSMC Q3 call."),
    }

d["cowos"]["facts"] = [
    {
        "label": "TSMC CoWoS · end-2026 (Silicon Analysts)",
        "value": "~120–130k wafers/mo",
        "sub": "Central ~125k wpm. Replaces Jun-15 Economic Daily via TrendForce 120–140k (now past quarterly stale window). TSMC does not disclose CoWoS capacity",
        "src": src("Silicon Analysts Qual Watch 2026-09-07",
                   "https://siliconanalysts.com/newsletter/qual-watch/2026-09-07",
                   "Reported", "2026-09-07", "quarterly"),
    },
    {
        "label": "TSMC CoWoS · end-2026/27 (UAnalyze)",
        "value": "~120k end-2026 · ~180k end-2027",
        "sub": "End-2027 raised from ~160k (institutional investors via UAnalyze). Conflicts with Goldman ~227.5k avg 2027 — shown side by side",
        "src": src("UAnalyze citing institutional investors",
                   "https://uanalyze.com.tw/articles/9531755299",
                   "Reported", "2026-09-15", "quarterly"),
    },
    goldman,
    {
        "label": "CoWoS supply–demand gap (MoneyDJ)",
        "value": "~30–35% now → 15–20% after expansion",
        "sub": "Research houses via MoneyDJ; expansion path ~185–190k wpm. Wider than Jun-15 EDN/TrendForce ~20%→~10% — supports Tight heat cell (unchanged)",
        "src": src("MoneyDJ citing research houses 2026-10-15",
                   "https://www.moneydj.com/kmdj/news/newsviewer.aspx?a=cc9317f2-f219-4d57-adae-f620e1ad4af9",
                   "Reported", "2026-10-15", "quarterly",
                   "Prior Jun-15 figure (~20%→~10% by end-2026, Economic Daily via TrendForce) retired as STALE; kept in CHANGELOG."),
    },
]

if q3:
    d["cowos"]["facts"].append(q3)
else:
    d["cowos"]["facts"].append({
        "label": "TSMC Q3'26 call (C.C. Wei)",
        "value": "“a little bit shortage on the back end”",
        "sub": "GF silicon-interposer partnership; demand “still far above our capability today to supply”",
        "src": src("TSMC Q3'26 call transcript",
                   "https://stockanalysis.com/quote/tpe/2330/transcripts/709077-q3-2026/",
                   "Confirmed", "2026-10-15", "quarterly"),
    })

P.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
print("seeded v2.1.1 CoWoS facts:", [f["label"] for f in d["cowos"]["facts"]])
