"""v2.1 hand-verified updates (2026-10-17). Each value was read from the linked page on 2026-10-17.
Run once; refresh.py keeps automated cells current afterwards."""
import json, pathlib
P = pathlib.Path(__file__).resolve().parent.parent / "data" / "data.json"
d = json.loads(P.read_text())
L = {l["id"]: l for l in d["leading"]}
def src(label, url, tag, asOf, cadence, note=None):
    s = {"label": label, "url": url, "tag": tag, "asOf": asOf, "cadence": cadence}
    if note: s["note"] = note
    return s

L["dram_contract"].update({"label": "PC DRAM contract · Sep", "value": "DDR4 8GB $148 · DDR5 16GB $247",
    "sub": "Sep avg: DDR4 8GB +4% MoM, DDR5 16GB flat; PC DRAM +2–4% MoM overall. 4Q26 PC DRAM fcst raised to +13–18% QoQ",
    "src": src("TrendForce 9/30 data via Daiwa note (Longbridge)", "https://longbridge.com/en/news/300766812.md", "Reported", "2026-09-30", "monthly",
               "TrendForce's own Sep table is members-only; public page still shows 2H Aug (DDR5 8GB SO-DIMM $133, +2.31%).")})
L["nand_contract"]["label"] = "NAND contract · 128Gb MLC (public table)"
L["nand_contract"]["src"]["note"] = "TrendForce public table last updated 2H Aug; Sep MLC 'edged up slightly' (TrendForce via Daiwa). Sep % not publicly verifiable."
L["kr_20d"].update({"label": "Korea chip exports · Oct 1–10", "value": "$12.20B",
    "sub": "+170.9% YoY · 46.7% of exports · total $26.10B (+102.0%), daily avg +28.5% (5.5 vs 3.5 working days). Provisional; 1–20 days due Oct 21",
    "yoyPct": 170.9,
    "src": src("Korea Customs Service via korea.kr", "https://www.korea.kr/briefing/pressReleaseView.do?newsId=156784799", "Confirmed", "2026-10-12", "event",
               "Mirror: https://www.donga.com/news/Economy/article/all/20261012/134824529/1. Automating needs a free data.go.kr key (KOREA_DATA_API_KEY), not wired.")})
L["tw_orders"]["period"] = "2026-08"
L["tw_orders_sep"]["sub"] = "Not yet released (due ~Oct 20; MOEA guide $106.0–109.1B). Auto via MOEA CSV once posted"
L["tw_orders_sep"]["src"].update({"url": "https://data.gov.tw/dataset/6845", "label": "MOEA open data CSV"})
L["crwv_cds"].update({"value": "~1,038bp", "sub": "Last ~1,038bp on Oct 15 (+16% w/w, +164% y/y); intraday above 1,140bp. ≥1,000bp = distressed (S&P Global MI). Bloomberg/ICE intraday record 1,194.5bp (reported second-hand)",
    "bp": 1038, "src": src("CNBC citing S&P Global Market Intelligence", "https://www.cnbc.com/2026/10/15/coreweave-credit-default-swaps-hit-distress-levels-as-investors-sour-on-ai-debt.html", "Reported", "2026-10-15", "event",
    "Reuters (US News mirror) same day: '>1,100bp' per S&P Global MI. CNBC: 9.75% 2031 notes YTM 15.78%.")})
L["crwv_2032"]["src"]["note"] = (L["crwv_2032"]["src"].get("note","") + " FINRA TRACE: public bond center needs a JS session and api.finra.org needs credentials (401), so not automated.").strip()

for f in d["cowos"]["facts"]:
    if f["value"] is None:
        f.update({"label": "CoWoS capacity path (Goldman Sachs est.)", "value": "~106k/mo avg 2026 → ~227.5k 2027 → ~290k 2028",
                  "sub": "1.275M wafers 2026, 2.73M 2027 (+114%), 3.48M 2028. Quarterly kwpm & utilization: n/a, source needed (TSMC does not disclose)",
                  "src": src("Goldman Sachs via TrendForce 2026-10-16", "https://www.trendforce.com/news/2026/10/16/news-after-tsmcs-3q26-earnings-key-brokerage-takeaways-as-2028-capex-forecasts-reach-us105b/", "Forecast", "2026-10-16", "quarterly",
                             "Tried: TrendForce, Digitimes (96.2% is TSMC overall utilization, not CoWoS), Morgan Stanley via press, TSMC Q3 call.")})

for h in d["heat"]:
    if h["id"] == "trade":
        h.update({"value": "Active · broader pending",
                  "note": "Sec. 232 Proc. 11002: 25% on certain advanced computing chips (e.g. H200, MI325X) since Jan 15 2026, with exemptions incl. US data centers. Broader semi tariffs + offset program contingent on Commerce/USTR talks. CRS lists it in effect as of Sep 30 2026. Level kept High (desk read 10-17)",
                  "src": src("Federal Register 91 FR 2443 (Proc. 11002)", "https://www.federalregister.gov/documents/2026/01/20/2026-01052/adjusting-imports-of-semiconductors-semiconductor-manufacturing-equipment-and-their-derivative", "Confirmed", "2026-09-30", "event",
                             "Status check: CRS R49481 (in effect as of 2026-09-30) https://www.everycrsreport.com/reports/R49481.html ; WH fact sheet 2026-01-14. Level = desk read.")})
d.setdefault("aum", {})["SOXX"] = {"valueB": 39.34, "asOf": "2026-10-16",
    "src": src("iShares SOXX fund page", "https://www.ishares.com/us/products/239705/ishares-phlx-semiconductor-etf", "Confirmed", "2026-10-16", "daily", "Net assets of fund $39,340,454,181")}
P.write_text(json.dumps(d, indent=1, ensure_ascii=False))
print("seeded v2.1")
