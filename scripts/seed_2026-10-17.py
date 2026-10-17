#!/usr/bin/env python3
"""One-time seed of data/data.json from values verified by hand on 2026-10-17.
Every value carries a source URL, a tag (Confirmed | Reported | Forecast | Rule | Desk read | Matt baseline)
and an as-of date. Anything that could not be verified is null with note 'n/a, source needed'.
The values come from /workspace/sources/semis/matt-semi-dashboard/VERIFIED-PRIMARY-DATA-2026-10-17.md.
After seeding, scripts/refresh.py owns the auto sections."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NA = "n/a, source needed"

def src(label, url, tag, asOf, cadence, note=None):
    d = {"label": label, "url": url, "tag": tag, "asOf": asOf, "cadence": cadence}
    if note: d["note"] = note
    return d

SIA_IDX = "https://www.semiconductors.org/news-events/latest-news/"
sia = [
 # period, latest stated $B, first print $B, yoy% (first print), release date, url
 ("2026-01", 82.54, 82.5, 46.1, "2026-03-06", "https://www.semiconductors.org/global-semiconductor-sales-increase-3-7-month-to-month-in-january/"),
 ("2026-02", 89.23, 88.8, 61.8, "2026-04-03", "https://www.semiconductors.org/?p=30831"),
 ("2026-03", 99.5, 99.5, 79.2, "2026-05-04", "https://www.semiconductors.org/global-semiconductor-sales-increase-25-from-q4-2025-to-q1-2026/"),
 ("2026-04", 110.5, 110.5, 93.9, "2026-06-05", "https://www.semiconductors.org/global-semiconductor-sales-increase-11-month-to-month-in-april/"),
 ("2026-05", 120.6, 120.6, 104.1, "2026-07-06", "https://www.semiconductors.org/global-semiconductor-sales-increase-9-2-month-to-month-in-may/"),
 ("2026-06", 137.9, 134.5, 123.6, "2026-08-06", "https://www.semiconductors.org/global-semiconductor-sales-increase-35-1-from-q1-2026-to-q2-2026/"),
 ("2026-07", 147.9, 146.8, 135.1, "2026-09-04", "https://www.semiconductors.org/global-semiconductor-sales-increase-6-4-month-to-month-in-july/"),
 ("2026-08", 159.7, 159.7, 144.3, "2026-10-05", "https://www.semiconductors.org/year-to-date-global-semiconductor-sales-top-1-trillion-through-august/"),
]
ppi = [("2025-10",60.125),("2025-11",60.868),("2025-12",61.063),("2026-01",61.583),("2026-02",67.019),("2026-03",68.282),
       ("2026-04",73.184),("2026-05",72.931),("2026-06",73.698),("2026-07",73.199),("2026-08",75.571),("2026-09",75.313)]
ppi_prior = {"2025-09": 59.765, "2025-08": 59.637, "2025-07": 57.576}
tsmc = [("2026-01",401255,36.8),("2026-02",317657,22.2),("2026-03",415191,45.2),("2026-04",410726,17.5),("2026-05",416975,30.1),
        ("2026-06",442680,67.9),("2026-07",467580,44.7),("2026-08",514806,53.3),("2026-09",511857,54.6)]
TSMC_URL = "https://investor.tsmc.com/english/monthly-revenue/2026"

data = {
 "schema": 1,
 "title": "Semiconductor Industry Dashboard (v2)",
 "generatedAt": "2026-10-17T21:10:00Z",
 "generatedBy": "scripts/seed_2026-10-17.py (hand-verified seed)",
 "staleDays": {"daily": 4, "weekly": 10, "biweekly": 21, "monthly": 45, "quarterly": 120, "annual": 400, "event": 30},
 "kpis": [
  {"id":"fy_projection","title":"2026 Semi Sales (projection)","display":">$1.6T",
   "sub":"SIA statement, Aug release · WSTS Spring fcst $1.5T · Deloitte $975B superseded",
   "src":src("SIA","https://www.semiconductors.org/year-to-date-global-semiconductor-sales-top-1-trillion-through-august/","Confirmed","2026-10-05","monthly")},
  {"id":"sia_latest","title":"auto","display":"auto","sub":"auto","src":None},
  {"id":"foundry2","title":"Foundry 2.0 Market 2026 (fcst)","display":">$360B",
   "sub":"IDC, +17% YoY (via Electronics Weekly) · old $218.8B TTM unverified, removed",
   "src":src("IDC via Electronics Weekly","https://www.electronicsweekly.com/news/business/foundry-2-0-to-grow-17-this-year-2026-03/","Reported","2026-03-15","annual","IDC primary is gated (my.idc.com); publication day approximate (Mar 2026).")},
  {"id":"kpmg","title":"Industry Confidence","display":"63",
   "sub":"KPMG Semi Confidence Index · 2026 outlook (151 execs, Q4'25 survey), up from 59",
   "src":src("KPMG 2026 Outlook","https://kpmg.com/us/en/articles/2026/global-semiconductor-industry-outlook-2026.html","Confirmed","2026-01-15","annual","Survey fielded Q4 2025; exact publication day not captured.")}
 ],
 "sia": {"series":[{"period":p,"valueB":v,"firstPrintB":f,"yoyPct":y,"release":r,"url":u} for p,v,f,y,r,u in sia],
         "note":"WSTS 3-month moving average. valueB = latest value SIA has stated (later releases revise prior month).",
         "src":src("SIA monthly release",SIA_IDX,"Confirmed","2026-10-05","monthly")},
 "ppi": {"series":[{"period":p,"value":v} for p,v in ppi], "prior":ppi_prior,
         "seriesId":"PCU3344133441","name":"PPI: Semiconductor & related device mfg",
         "src":src("FRED PCU3344133441","https://fred.stlouisfed.org/series/PCU3344133441","Confirmed","2026-10-17","monthly","Pulled via fredgraph.csv; PPI is revised ~4 months after first print.")},
 "tsmc": {"series":[{"period":p,"ntdM":v,"yoyPct":y} for p,v,y in tsmc],
          "src":src("TSMC IR monthly revenue",TSMC_URL,"Confirmed","2026-10-08","monthly")},
 "cowos": {
  "facts":[
   {"label":"TSMC CoWoS capacity 2026","value":"120–140k wafers/mo","sub":"Plus 50–60k from OSAT partners → ~200k industry",
    "src":src("Economic Daily via TrendForce","https://www.trendforce.com/news/2026/06/15/news-tsmc-cowos-supply-demand-gap-reportedly-seen-narrowing-from-20-to-10-by-end-2026-as-capacity-expands/","Reported","2026-06-15","quarterly")},
   {"label":"CoWoS supply–demand gap","value":"~20% → ~10% by end-2026","sub":"Institutional investors via EDN; TSMC plans >60% CoWoS expansion by 2027",
    "src":src("Economic Daily via TrendForce","https://www.trendforce.com/news/2026/06/15/news-tsmc-cowos-supply-demand-gap-reportedly-seen-narrowing-from-20-to-10-by-end-2026-as-capacity-expands/","Reported","2026-06-15","quarterly")},
   {"label":"TSMC Q3'26 call (C.C. Wei)","value":"\u201ca little bit shortage on the back end\u201d","sub":"GF silicon-interposer partnership; demand \u201cstill far above our capability today to supply\u201d",
    "src":src("TSMC Q3'26 call transcript","https://stockanalysis.com/quote/tpe/2330/transcripts/709077-q3-2026/","Confirmed","2026-10-15","quarterly")},
   {"label":"Quarterly CoWoS wafers/mo & utilization %","value":None,"sub":"Matt's Jul 10 series (40→135k, 93–99% util) had no per-point source; removed. Pressure index dropped (undefined).",
    "src":src("—",None,"n/a","2026-07-10","quarterly")}
  ]},
 "leading": [
  {"group":"Foundry","id":"tsmc_rev","label":"TSMC monthly revenue","auto":"tsmc"},
  {"group":"Memory","id":"dram_spot","label":"DRAM spot · DDR5 16Gb 4800/5600","value":"$60.60","sub":"session avg, ▲0.28% d/d",
   "src":src("TrendForce DRAMeXchange","https://www.trendforce.com/price/dram/dram_spot","Reported","2026-10-16","daily")},
  {"group":"Memory","id":"dram_contract","label":"DRAM contract · DDR5 8GB SO-DIMM","value":"$133.00","sub":"2H Aug avg, ▲2.31% · Sep contract paywalled (n/a, source needed)",
   "src":src("TrendForce DRAMeXchange","https://www.trendforce.com/price/dram/dram_contract","Reported","2026-08-31","biweekly")},
  {"group":"Memory","id":"nand_spot","label":"NAND wafer spot · 512Gb TLC","value":"$18.833","sub":"session avg, ▼2.90%",
   "src":src("TrendForce","https://www.trendforce.com/price/flash/flash_spot","Reported","2026-10-05","weekly")},
  {"group":"Memory","id":"nand_contract","label":"NAND contract · 128Gb MLC (card/UFD)","value":"$30.475","sub":"2H Aug avg, ▲1.42% · Sep paywalled",
   "src":src("TrendForce","https://www.trendforce.com/price/flash/flash_spot","Reported","2026-08-31","biweekly")},
  {"group":"Memory","id":"mem_fcst","label":"4Q26 contract forecast","value":"DRAM +10–15% · NAND +15–20% QoQ","sub":"Forecast — not a settled print",
   "src":src("TrendForce press 2026-09-30","https://www.trendforce.com/presscenter/news/20260930-13258.html","Forecast","2026-09-30","quarterly")},
  {"group":"Exports","id":"kr_chips","label":"Korea chip exports · Sep","value":"$60.30B","sub":"+262.8% YoY · record month (total exports $120.94B, +83.5%)","yoyPct":262.8,
   "src":src("MOTIR (Korea)","https://english.motir.go.kr/eng/article/EATCLdfa319ada/2743/view","Confirmed","2026-10-01","monthly")},
  {"group":"Exports","id":"kr_20d","label":"Korea chip exports · Oct 1–20 days","value":None,"sub":"Due ~Oct 21 (Korea Customs)",
   "src":src("Korea Customs Service",None,"n/a","2026-10-17","monthly")},
  {"group":"Exports","id":"tw_orders","label":"Taiwan export orders · Aug","value":"$102.96B","sub":"+71.4% YoY · record · electronics $45.75B (+83.9%), ICT $34.21B (+100.5%)",
   "src":src("MOEA via Focus Taiwan/CNA","https://focustaiwan.tw/business/202609220025","Reported","2026-09-22","monthly")},
  {"group":"Exports","id":"tw_orders_sep","label":"Taiwan export orders · Sep","value":None,"sub":"Not yet released (MOEA guide $106.0–109.1B)",
   "src":src("MOEA",None,"n/a","2026-10-17","monthly")},
  {"group":"Neocloud credit","id":"crwv_2032","label":"CoreWeave 9.625% 2032 notes · yield","value":"~14.6%","sub":"~81c on Oct 15 after >15% / <80c on Oct 14 · Watch ≥15%, trip >18% (T-05)","yieldPct":14.6,
   "src":src("WSJ citing MarketAxess","https://www.wsj.com/livecoverage/stock-market-today-dow-sp-500-nasdaq-10-15-2026/card/MLE9nNEYezUmliPXS9KA","Reported","2026-10-15","daily","Also CNBC 10-14: https://www.cnbc.com/2026/10/14/coreweave-stock-bond-yields-ai-debt.html . Not a direct TRACE pull; no 10-16 close in hand.")},
  {"group":"Neocloud credit","id":"crwv_cds","label":"CoreWeave 5y CDS","value":None,"sub":"Desk note cites a Bloomberg record ~1,194.5bp (10-15) but no linkable source in hand",
   "src":src("—",None,"n/a","2026-10-15","daily")},
  {"group":"Neocloud credit","id":"crwv_eq","label":"CRWV equity","auto":"quote:CRWV"}
 ],
 "capex": {"quarter":"Apr–Jun 2026 (latest reported)","rows":[
   {"co":"Microsoft","period":"FQ4'26","valueB":41.0,"basis":"incl. finance leases","yoyPct":None,
    "src":src("MSFT FY26 Q4 call","https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4","Confirmed","2026-07-29","quarterly","Release day approximate (late Jul 2026).")},
   {"co":"Alphabet","period":"Q2'26","valueB":44.924,"basis":"purchases of PP&E","yoyPct":100.1,
    "src":src("Alphabet Q2'26 release","https://s206.q4cdn.com/479360582/files/doc_financials/2026/q2/2026q2-alphabet-earnings-release.pdf","Confirmed","2026-07-23","quarterly","Q2'25 $22.446B. Release day approximate.")},
   {"co":"Amazon","period":"Q2'26","valueB":54.208,"basis":"gross purchases of P&E","yoyPct":68.4,
    "src":src("Amazon Q2'26 release","https://ir.aboutamazon.com/news-release/news-release-details/2026/Amazon-com-Announces-Second-Quarter-Results/default.aspx","Confirmed","2026-07-30","quarterly","Q2'25 $32.183B. Release day approximate.")},
   {"co":"Meta","period":"Q2'26","valueB":31.08,"basis":"incl. finance-lease principal","yoyPct":None,
    "src":src("Meta Q2'26 release","https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Second-Quarter-2026-Results/default.aspx","Confirmed","2026-07-29","quarterly","FY26 guide $130–145B (narrowed).")}
  ],"note":"Mixed definitions across companies; sum is indicative only. Q3 prints due late Oct."},
 "heatRules": {
  "semi_ppi": {"metric":"FRED PPI YoY %","low_lt":5,"high_gte":15,"words":{"low":"Stable","mid":"Firming","high":"Hot"}},
  "sales_yoy": {"metric":"SIA latest YoY %","low_lt":15,"high_gte":40,"words":{"low":"Normal","mid":"Strong","high":"Hot"}},
  "note":"v2 default thresholds proposed for Matt to tune; rule cells recompute on every refresh."
 },
 "heat": [
  {"id":"ai_demand","name":"AI Demand","mode":"manual","level":"high","value":"Elevated","note":"TSMC: demand \u201cstill far above our capability today to supply\u201d",
   "prev":{"level":"high","value":"Elevated","date":"2026-07-10"},"changed":None,
   "src":src("TSMC Q3'26 call","https://stockanalysis.com/quote/tpe/2330/transcripts/709077-q3-2026/","Confirmed","2026-10-15","event")},
  {"id":"hbm","name":"HBM / Memory","mode":"manual","level":"high","value":"Tight","note":"Loudest gate; 4Q26 DRAM contract fcst +10–15% QoQ; server DRAM undersupplied",
   "prev":{"level":"high","value":"Tight","date":"2026-07-10"},"changed":None,
   "src":src("TrendForce 2026-09-30 + Semi Desk board","https://www.trendforce.com/presscenter/news/20260930-13258.html","Desk read","2026-10-14","event")},
  {"id":"cowos","name":"TSMC / CoWoS Capacity","mode":"manual","level":"high","value":"Tight","note":"Wei 10-15: \u201ca little bit shortage on the back end\u201d",
   "prev":{"level":"high","value":"Hot","date":"2026-07-10"},"changed":None,
   "src":src("TSMC Q3'26 call","https://stockanalysis.com/quote/tpe/2330/transcripts/709077-q3-2026/","Confirmed","2026-10-15","event")},
  {"id":"trade","name":"Tariff / Trade Risk","mode":"manual","level":"high","value":"Rising","note":"Matt baseline, not re-verified in v2",
   "prev":{"level":"high","value":"Rising","date":"2026-07-10"},"changed":None,
   "src":src("Matt baseline (Jul 10)",None,"Matt baseline","2026-07-10","event")},
  {"id":"power","name":"Power / Site Capacity","mode":"manual","level":"high","value":"Hot","note":"TX TCEQ permit freeze · Oregon statewide DEQ pause to 2027-07-01 · SF 45-day moratorium (10-16)",
   "prev":{"level":"mid","value":"Warming","date":"2026-07-10"},"changed":"2026-10-17",
   "src":src("TX Gov / OR Gov letter / SF Standard","https://sfstandard.com/2026/10/16/mayor-lurie-data-center-moratorium/","Confirmed","2026-10-16","event",
    "TX: https://gov.texas.gov/uploads/files/press/TCEQ_Data_Center.pdf · OR: https://www.opb.org/pdf/100926_GovernorLettertoDEQDataCenterPermitting_1791931532928.pdf · Counterweight: SemiAnalysis says only ~2.3 GW of ~21 GW in local-moratorium areas likely delayed (excl. TX).")},
  {"id":"semi_ppi","name":"Semi PPI","mode":"rule","level":"auto","value":"auto","note":"auto",
   "prev":{"level":"mid","value":"Firming","date":"2026-07-10"},"changed":None,"src":None},
  {"id":"sales_yoy","name":"Global Sales YoY","mode":"rule","level":"auto","value":"auto","note":"auto",
   "prev":{"level":"low","value":"Strong","date":"2026-07-10"},"changed":None,"src":None},
  {"id":"confidence","name":"Confidence Index","mode":"manual","level":"low","value":"Stable","note":"KPMG 63 (2026 outlook), up from 59",
   "prev":{"level":"low","value":"Stable","date":"2026-07-10"},"changed":None,
   "src":src("KPMG 2026 Outlook","https://kpmg.com/us/en/articles/2026/global-semiconductor-industry-outlook-2026.html","Confirmed","2026-01-15","annual")}
 ],
 "companies": [
  {"sym":"NVDA","name":"NVIDIA Corp","color":"#76b900","thesis":"AI accelerators · supply-capped"},
  {"sym":"AMD","name":"Advanced Micro","color":"#e879f9","thesis":"MI-series AI · server CPUs"},
  {"sym":"INTC","name":"Intel","color":"#3b9be8","thesis":"18A foundry recovery"},
  {"sym":"TSM","name":"Taiwan Semi (ADR)","color":"#f472b6","thesis":"Leading-edge + CoWoS"},
  {"sym":"ASML","name":"ASML (ADR)","color":"#ff8000","thesis":"EUV lithography"},
  {"sym":"MU","name":"Micron Tech","color":"#22d3ee","thesis":"HBM · memory cycle"},
  {"sym":"SOXX","name":"iShares Semi ETF","color":"#a78bfa","thesis":"Sector proxy (ETF)","isETF":True}
 ],
 "extraQuotes": ["CRWV"],
 "quotes": {},
 "pcds": {"url":"https://mcraska.github.io/pcds-dashboard/","label":"Semi Desk PCDS v0.2.1 — recreation signal"},
 "refreshLog": []
}
os.makedirs(os.path.join(ROOT,"data","history"), exist_ok=True)
json.dump(data, open(os.path.join(ROOT,"data","data.json"),"w"), indent=1, ensure_ascii=False)

# Matt's original embedded baseline (Jul 10), preserved as the first history snapshot
baseline = {"snapshotOf":"Matt's Vercel dashboard embedded DATA (asOf Jul 10, 2026 4:00 PM ET)","source":"https://semi-dashboard-alpha.vercel.app (retired)",
 "warning":"Historical baseline. Several figures do not match primary sources; see CHANGELOG.md.",
 "companies":{"NVDA":210.96,"AMD":557.89,"INTC":109.84,"TSM":434.11,"ASML":1797.32,"MU":979.30,"SOXX":581.34},
 "foundry":{"labels":["Q4'24","Q1'25","Q2'25","Q3'25","Q4'25","Q1'26","Q2'26","Q3'26","Q4'26E","Q1'27E"],"cowos":[40,50,62,72,85,95,105,115,125,135],
            "pressure":[82,86,89,92,94,96,97,96,94,92],"utilization":[93,95,96,97,98,98,99,98,97,96]},
 "sector":{"labels":["Jan'26","Feb'26","Mar'26","Apr'26","May'26","Jun'26"],"salesB":[82.5,84.0,86.1,87.8,89.4,91.2],"ppi":[66.5,67.9,68.7,69.4,70.1,70.8]},
 "heat":{"ai_demand":["high","Elevated"],"hbm":["high","Tight"],"cowos":["high","Hot"],"trade":["high","Rising"],"power":["mid","Warming"],
         "semi_ppi":["mid","Firming"],"sales_yoy":["low","Strong"],"confidence":["low","Stable"]},
 "kpis":{"fy2026":"$975B (Deloitte)","jun_sales":"$91.2B +2.0% MoM +22% YoY (SIA est.)","foundry_ttm":"$218.8B (IDC)","kpmg":63}}
json.dump(baseline, open(os.path.join(ROOT,"data","history","2026-07-10-matt-baseline.json"),"w"), indent=1)
print("seeded")
