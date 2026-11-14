"""Build the 7-slide DalaShift pitch deck (reveal.js 4.6.1).

    python docs/deck/build_deck.py

Writes docs/deck/index.html (reveal.js from cdnjs) and docs/deck/offline.html (reveal.js vendored
in docs/deck/vendor/, works without Wi-Fi). All numbers are computed here from data/summary.json,
data/planner.json and the planner itself, so the deck matches the app.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dalashift.i18n import CROP_NAMES  # noqa: E402
from dalashift.planner import plan_farm  # noqa: E402
from dalashift.simple_ui import uzs_per_usd  # noqa: E402

DECK = Path(__file__).resolve().parent
CDN = "https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.6.1"
DISTRICTS = {"Karshi": "Karshi", "Fergana": "Fergana", "Urgench": "Urgench", "Nukus": "Nukus", "Gulistan": "Gulistan"}
N_TESTS = int(sys.argv[1]) if len(sys.argv) > 1 else None

S = json.loads((ROOT / "data/summary.json").read_text(encoding="utf-8"))
P = json.loads((ROOT / "data/planner.json").read_text(encoding="utf-8"))["points"]
RATE = uzs_per_usd()


def mln(usd: float) -> int:
    return round(usd * RATE / 1e6)


def hot(d):
    p = S["points"][f"{d}_field1"]
    return p["then"]["hot_days"], p["now"]["hot_days"]


k_then, k_now = hot("Karshi")
deltas = {d: hot(d)[1] - hot(d)[0] for d in DISTRICTS}
dmin, dmax = round(min(deltas.values())), round(max(deltas.values()))
K = S["points"]["Karshi_field1"]
rain_then, rain_now = K["then"]["gs_rain"], K["now"]["gs_rain"]
et0_tonnes = round((K["now"]["gs_et0"] - K["then"]["gs_et0"]) * 10, -1)
qc_max = max(p["precip_qc_days_removed"] for p in S["points"].values())

DEMO = {"Karshi": ("Karshi_field1", 8000), "Fergana": ("Fergana_field1", 12000)}
demo = {}
for name, (pid, budget) in DEMO.items():
    r = plan_farm(P[pid], budget, 0.1, 2, {})
    must = plan_farm(P[pid], budget, 0.1, 2, {"cotton": 2, "winter_wheat": 2})
    demo[name] = {"budget": budget, "res": r, "must": must, "cotton_need": P[pid]["baseline"]["cotton"]["need_m3ha"]}
max_seq = max(d["res"]["result"]["n_sequences"] for d in demo.values())


def icons(plan):
    return "".join(f"<span title='{'+'.join(y['crops'])}'>{''.join(CROP_NAMES[c]['icon'] for c in y['crops'])}</span>"
                   for y in plan["years"])


def plan_row(label, plan, budget):
    r = plan["profit_per_year_range"]
    peak = max(y["water"] for y in plan["years"])
    share = peak / budget
    color = "var(--green)" if share <= 0.8 else "var(--amber)" if share <= 1 else "var(--red)"
    names = " → ".join("+".join(CROP_NAMES[c]["en"] for c in y["crops"]) for y in plan["years"])
    return (f"<div class='plan'><div class='pl'>{label}</div><div class='ic'>{icons(plan)}</div>"
            f"<div class='nm'>{names}</div>"
            f"<div class='mn'>{mln(r['low'])}–{mln(r['high'])} <small>mln so'm/ha/yr</small></div>"
            f"<div class='bar'><div style='width:{min(share, 1) * 100:.0f}%;background:{color}'></div></div>"
            f"<div class='wt'>thirstiest year {peak:,.0f} of {budget:,} m³/ha</div></div>")


def results_col(name):
    d = demo[name]
    plans = d["res"]["result"]["plans"]
    rows = "".join(plan_row(lbl, plans[k], d["budget"]) for k, lbl in
                   [("profit", "💰 Most income"), ("balanced", "⚖️ Balanced"), ("water", "💧 Least water")])
    return f"<div class='col'><h3>{name} <small>· water {d['budget']:,} m³/ha/yr</small></h3>{rows}</div>"


kc = demo["Karshi"]
k_must = kc["must"]["result"]
fc = demo["Fergana"]["must"].get("constraint_cost") or {}
f_cost = fc.get("balanced", {}).get("npv_cost")
tests_line = f"<b>{N_TESTS}</b> automated tests" if N_TESTS else "automated tests"

SLIDES = f"""
<section class="title">
  <div class="split">
    <div>
      <h1>🌾 DalaShift</h1>
      <p class="tag">Don't just choose the most profitable crop for this year.<br><b>Choose the best five-year future for your field.</b></p>
      <p class="meta">Challenge: <b>Field Shift: Adapting Farms with NASA Data</b><br>NASA Space Apps Challenge 2026 · Karshi local event</p>
      <p class="team"><span class="ph">[TEAM NAME]</span><br>
        <span class="ph">[MEMBER 1]</span> <span class="ph">[MEMBER 2]</span> <span class="ph">[MEMBER 3]</span>
        <span class="ph">[MEMBER 4]</span> <span class="ph">[MEMBER 5]</span> <span class="ph">[MEMBER 6]</span></p>
    </div>
    <img class="shot" src="../screenshots/farmer_step3_desktop.png" alt="DalaShift farmer view: 5-year plan">
  </div>
</section>

<section>
  <h2>The problem</h2>
  <div class="split">
    <div class="bignum"><div class="n">{k_then:.0f} → {k_now:.0f}</div>
      <div>days a year above 35 °C in <b>Karshi</b><br><small>1991–2005 vs 2011–2026, NASA POWER</small></div></div>
    <ul>
      <li>All 5 districts got hotter: <b>+{dmin} to +{dmax}</b> very hot days a year</li>
      <li>Karshi growing-season rain: {rain_then:.0f} → {rain_now:.0f} mm; crops need <b>~{et0_tonnes:,.0f} t</b> more water per ha per year</li>
      <li>Irrigation water is limited, and crops are chosen <b>one year at a time</b></li>
      <li class="persona">Meet a wheat and cotton farmer near Karshi: which crops, in which order, with the water they actually get?</li>
    </ul>
  </div>
</section>

<section>
  <h2>The solution: 3 steps, in Uzbek first</h2>
  <div class="three">
    <figure><img class="fit" src="../screenshots/farmer_step1_phone.png" alt=""><figcaption>1 · Where is your field?</figcaption></figure>
    <figure><img src="../screenshots/farmer_step2_phone.png" alt=""><figcaption>2 · What changed on it?</figcaption></figure>
    <figure><img style="object-position: 50% 52%" src="../screenshots/farmer_step3_phone.png" alt=""><figcaption>3 · Your 5-year plan</figcaption></figure>
  </div>
  <p class="small">Income in so'm per hectare per year, water as a green / amber / red bar, one plain reason per crop. Experts and judges get every number in a separate tab.</p>
</section>

<section>
  <h2>The data: what each source answers</h2>
  <table class="data">
    <tr><th>Source</th><th>What it answers</th><th>Status</th></tr>
    <tr><td><b>NASA POWER</b> (MERRA-2, CERES, IMERG)</td><td>35 years of daily weather: heat days, frost dates, rain, reference crop water use (FAO-56 Penman-Monteith)</td><td class="ok">used</td></tr>
    <tr><td><b>NASA SMAP</b> root-zone soil moisture</td><td>How dry is the soil under each field right now?</td><td class="wip">requested, integrating</td></tr>
    <tr><td><b>NASA ECOSTRESS</b> ET / ESI</td><td>Is the crop water-stressed? Calibrates our water-need correction</td><td class="wip">requested, integrating</td></tr>
    <tr><td><b>NASA/USGS HLS</b> NDVI</td><td>How green is each field? (field-level differences)</td><td class="wip">requested, integrating</td></tr>
    <tr class="non"><td>FAO-56 (method) · FAOSTAT yields &amp; prices</td><td>Crop water need per crop; typical Uzbek yields and producer prices</td><td>non-NASA</td></tr>
    <tr class="non"><td>Korzinka, Uzum Market · CBU exchange rate</td><td>Current retail prices (× 0.40 to farm gate), so'm per USD</td><td>non-NASA</td></tr>
  </table>
</section>

<section>
  <h2>How it works, and how we checked it</h2>
  <div class="split">
    <ul>
      <li>Checks <b>every</b> 5-year crop sequence: up to <b>{max_seq:,}</b> per farm, nothing sampled</li>
      <li>Rules: rotation (no cotton 3 years running, legume break), water budget every year, frost only between emergence and harvest</li>
      <li>3 plans: most income · balanced · least water</li>
      <li>Stress test: <b>+1.5 °C</b> and <b>−20 % water</b></li>
    </ul>
    <ul>
      <li>{tests_line}: every plan re-checked by an independent rule checker</li>
      <li>Data issues found and fixed: removed impossible rain spikes (0–{qc_max} days per point); <b>ET0 × 0.80</b> correction for the desert bias over irrigated land; fields sharing one POWER grid cell get one district profile</li>
      <li class="limits"><b>Limits:</b> ~50 km weather grid, placeholder costs, prices partly estimated from retail; rotation health is a rule score, not a soil model</li>
    </ul>
  </div>
</section>

<section>
  <h2>Results: Karshi vs Fergana</h2>
  <div class="cols">{results_col("Karshi")}{results_col("Fergana")}</div>
  <p class="small"><b>Must grow cotton at Karshi?</b> Cotton needs ~{kc['cotton_need']:,} m³/ha of water here, more than the {kc['budget']:,} available, so no plan with cotton fits; DalaShift says so and shows the closest plan{f" (in Fergana the obligation costs ~{mln(f_cost)} mln so'm/ha over 5 years)" if f_cost else ""}.</p>
</section>

<section>
  <h2>Next steps</h2>
  <div class="split">
    <ul>
      <li>Connect <b>Uzcosmos</b> and national agriculture data</li>
      <li>Real <b>soil and salinity</b> layers per field; SMAP, ECOSTRESS and HLS live</li>
      <li><b>Telegram bot in Uzbek</b>: farmers ask, DalaShift answers</li>
      <li>More crops and varieties (melon), real costs per hectare</li>
      <li>Re-plan every year with the new season's data</li>
    </ul>
    <div class="teambox">
      <p><span class="ph">[TEAM NAME]</span></p>
      <p><span class="ph">[MEMBER 1]</span> <span class="ph">[MEMBER 2]</span> <span class="ph">[MEMBER 3]</span><br>
         <span class="ph">[MEMBER 4]</span> <span class="ph">[MEMBER 5]</span> <span class="ph">[MEMBER 6]</span></p>
      <p>Repo: <span class="ph">[REPO LINK]</span><br>App: <span class="ph">[APP LINK]</span></p>
    </div>
  </div>
</section>
"""

CSS = """
:root { --green:#1f9d55; --amber:#d97706; --red:#d64545; --ink:#1b1b1b; --muted:#6b6a66; }
.reveal { font-family: "Segoe UI", system-ui, -apple-system, sans-serif; color: var(--ink); font-size: 34px; }
.reveal h1, .reveal h2, .reveal h3 { font-family: inherit; text-transform: none; color: var(--ink); }
.reveal h1 { font-size: 2.6em; margin-bottom: .2em; }
.reveal h2 { font-size: 1.5em; margin-bottom: .5em; }
.reveal .slide-number { font-size: 22px; background: transparent; color: var(--muted); }
.split { display: grid; grid-template-columns: 1.1fr 1fr; gap: 40px; align-items: center; text-align: left; }
.tag { font-size: .95em; } .meta { font-size: .7em; color: var(--muted); }
.ph { background: #fff3c4; border: 2px dashed var(--amber); padding: 0 .25em; font-weight: 700; font-size: .7em; }
.shot { border: 1px solid #ddd; border-radius: 12px; box-shadow: 0 6px 24px rgba(0,0,0,.08); }
.bignum .n { font-size: 3.2em; font-weight: 800; color: var(--red); line-height: 1; }
.reveal ul { font-size: .78em; } .reveal li { margin: .35em 0; }
.persona { color: var(--muted); font-style: italic; list-style: none; margin-top: .8em !important; }
.three { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.three img { height: 480px; width: 100%; object-fit: cover; object-position: top; border-radius: 14px; border: 1px solid #ddd; }
.three img.fit { object-fit: contain; background: #fafaf8; }
.three figcaption { font-size: .7em; font-weight: 700; }
.small { font-size: .6em; color: var(--muted); }
table.data { font-size: .55em; width: 100%; } table.data td, table.data th { padding: .35em .5em; text-align: left; }
td.ok { color: var(--green); font-weight: 700; } td.wip { color: var(--amber); font-weight: 700; }
tr.non td { color: var(--muted); }
.limits { color: var(--muted); }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; text-align: left; }
.cols h3 { font-size: .8em; } .cols h3 small { color: var(--muted); font-weight: 400; }
.plan { border: 1px solid #e6e4dd; border-radius: 14px; padding: 8px 14px; margin-bottom: 10px; }
.plan .pl { font-size: .5em; font-weight: 700; } .plan .ic { font-size: 1.1em; letter-spacing: .15em; }
.plan .nm { font-size: .35em; color: var(--muted); }
.plan .mn { font-size: .7em; font-weight: 800; color: var(--green); } .plan .mn small { font-size: .55em; color: var(--muted); font-weight: 400; }
.bar { height: 12px; background: #eeece6; border-radius: 6px; overflow: hidden; margin: 4px 0; } .bar div { height: 100%; }
.plan .wt { font-size: .35em; color: var(--muted); }
.teambox { font-size: .75em; text-align: left; }
@media print { .reveal .slides .pdf-page:last-of-type { page-break-after: avoid !important; break-after: avoid !important; } }
"""


def page(base: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DalaShift Pitch Deck</title>
<link rel="stylesheet" href="{base}/reset.min.css">
<link rel="stylesheet" href="{base}/reveal.min.css">
<link rel="stylesheet" href="{base}/theme/white.min.css">
<style>{CSS}</style>
</head>
<body>
<div class="reveal"><div class="slides">
{SLIDES}
</div></div>
<script src="{base}/reveal.min.js"></script>
<script>
Reveal.initialize({{ hash: true, controls: false, slideNumber: 'c/t', width: 1600, height: 900, margin: 0.04,
  transition: 'fade', pdfSeparateFragments: false, pdfMaxPagesPerSlide: 1 }});
</script>
</body>
</html>
"""


(DECK / "index.html").write_text(page(CDN), encoding="utf-8", newline="\n")
(DECK / "offline.html").write_text(page("vendor"), encoding="utf-8", newline="\n")
print("wrote", DECK / "index.html", "and", DECK / "offline.html")
print("numbers:", dict(k_then=k_then, k_now=k_now, dmin=dmin, dmax=dmax, rain=(rain_then, rain_now),
                       et0_tonnes=et0_tonnes, qc_max=qc_max, max_seq=max_seq, f_cost_mln=f_cost and mln(f_cost)))
