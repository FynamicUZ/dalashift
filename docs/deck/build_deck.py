"""Build the 7-slide DalaShift pitch deck as a story (reveal.js 4.6.1).

    python docs/deck/build_deck.py [number_of_tests]

Writes docs/deck/index.html (reveal.js from cdnjs) and docs/deck/offline.html (reveal.js vendored in
docs/deck/vendor/, no Wi-Fi needed). Every number is computed here from data/summary.json,
data/planner.json and the planner, so the deck matches the app.
Hero image: NASA Worldview snapshot, MODIS Terra corrected reflectance (true colour), 12 Aug 2025,
Karshi oasis (public domain, NASA EOSDIS GIBS / Worldview).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dalashift.baseline import compare, evaluate_usual, risk_level  # noqa: E402
from dalashift.planner import evaluate_plan, make_context, plan_farm  # noqa: E402
from dalashift.simple_ui import to_mln  # noqa: E402

DECK = Path(__file__).resolve().parent
CDN = "https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.6.1"
N_TESTS = int(sys.argv[1]) if len(sys.argv) > 1 else None
import pandas as pd  # noqa: E402

from dalashift.appeears import load_appeears  # noqa: E402
from dalashift.smap import summary as smap_summary  # noqa: E402

WATER = load_appeears(ROOT / "data/appeears", pd.read_csv(ROOT / "data/points.csv"))
HAS = set(WATER["var"]) if len(WATER) else set()
HAS_APPEEARS = bool(HAS)
SMAP_K = smap_summary(WATER, "Karshi_field1")

S = json.loads((ROOT / "data/summary.json").read_text(encoding="utf-8"))
P = json.loads((ROOT / "data/planner.json").read_text(encoding="utf-8"))["points"]
K = S["points"]["Karshi_field1"]
years, hot = K["annual"]["year"], K["annual"]["hot_days"]
k_then, k_now = round(K["then"]["hot_days"]), round(K["now"]["hot_days"])
rain_then, rain_now = round(K["then"]["gs_rain"]), round(K["now"]["gs_rain"])
et0_t = round((K["now"]["gs_et0"] - K["then"]["gs_et0"]) * 10, -1)

BUDGET = 8000
kb = P["Karshi_field1"]["baseline"]
wheat_need, cotton_need = kb["winter_wheat"]["need_m3ha"], kb["cotton"]["need_m3ha"]
over_pct = round(100 * (cotton_need / BUDGET - 1))
ctx = make_context(kb, BUDGET, 0.1, 2)
wc = evaluate_plan(["winter_wheat", "cotton", "winter_wheat", "cotton", "winter_wheat"], ctx, "wheat_cotton")
fallback = evaluate_usual(kb, BUDGET, 0.1, 2)
res = plan_farm(P["Karshi_field1"], BUDGET, 0.1, 2, {})
bal = res["result"]["plans"]["balanced"]
c_wc, c_fb = compare(bal, wc), compare(bal, fallback)
bal_low = to_mln(bal["profit_per_year_range"]["low"])
n_seq = max(plan_farm(P[p], b, 0.1, 2, {})["result"]["n_sequences"] for p, b in
            [("Karshi_field1", 8000), ("Fergana_field1", 12000)])
TEAM_MEMBERS = ["Ahmedov Zuhriddin", "Alisherov Azimbek", "Shermaxmatov Ozodbek", "Botirxonov Faxriyor", "Boyqulov Afzalbek"]
TEAM = " · ".join(TEAM_MEMBERS)
NAMES = {"winter_wheat": "Wheat", "chickpea": "Chickpea", "barley": "Barley", "cotton": "Cotton"}
bal_names = [" + ".join(NAMES.get(c, c.title()) for c in y["crops"]) for y in bal["years"]]


def chart_svg() -> str:
    """35-year line of very hot days at Karshi + the two period means (drawn on slide entry)."""
    w, h, pad = 900, 360, 40
    lo, hi = 60, 130
    x = lambda i: pad + i * (w - 2 * pad) / (len(years) - 1)  # noqa: E731
    y = lambda v: h - pad - (v - lo) / (hi - lo) * (h - 2 * pad)  # noqa: E731
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(hot) if v is not None)
    i0, i1 = years.index(1991), years.index(2005)
    j0, j1 = years.index(2011), len(years) - 1
    yt, yn = y(K["then"]["hot_days"]), y(K["now"]["hot_days"])
    return (f"<svg class='chart' viewBox='0 0 {w} {h}' width='{w}' height='{h}'>"
            f"<line x1='{pad}' x2='{w - pad}' y1='{h - pad}' y2='{h - pad}' stroke='#d9d4c7'/>"
            f"<polyline class='draw' points='{pts}' fill='none' stroke='#c0442f' stroke-width='3' stroke-linejoin='round'/>"
            f"<line class='mean' x1='{x(i0)}' x2='{x(i1)}' y1='{yt}' y2='{yt}' stroke='#6b716d' stroke-width='4' stroke-dasharray='8 6'/>"
            f"<line class='mean' x1='{x(j0)}' x2='{x(j1)}' y1='{yn}' y2='{yn}' stroke='#c0442f' stroke-width='4' stroke-dasharray='8 6'/>"
            f"<text x='{x(i0)}' y='{h - 10}' class='ax'>1991</text><text x='{x(j1) - 40}' y='{h - 10}' class='ax'>2026</text>"
            f"<text x='{x(i0)}' y='{yt + 30}' class='ax mean'>avg {k_then}</text>"
            f"<text x='{x(j0)}' y='{yn - 14}' class='ax mean' style='fill:#c0442f'>avg {k_now}</text></svg>")


def water_bars() -> str:
    seq = [("Wheat", wheat_need), ("Cotton", cotton_need), ("Wheat", wheat_need), ("Cotton", cotton_need),
           ("Wheat", wheat_need)]
    top = 14000
    bars = "".join(
        f"<div class='wb'><div class='wcol'><div class='wfill {'bad' if v > BUDGET else 'ok'}' style='--h:{v / top * 100:.1f}%'></div></div>"
        f"<div class='wl'>Year {i + 1}<br><b>{n}</b><br><span>{v:,.0f} t</span></div></div>"
        for i, (n, v) in enumerate(seq))
    # the bar area is the top 78 % of the 480 px block
    return (f"<div class='wbars'><div class='budget' style='bottom:calc(22% + 78% * {BUDGET / top:.4f})'>"
            f"<span>water the farm gets: {BUDGET:,} t / ha</span></div>{bars}</div>")


def cmp_bar(label: str, value: float, text: str, good: bool, scale: float = 60) -> str:
    width = min(abs(value) / scale * 100, 100)
    return (f"<div class='cb'><div class='cl'>{label}</div><div class='ct'><div class='cf {'ok' if good else 'bad'}' "
            f"style='--w:{width:.0f}%'></div></div><div class='cv' style='color:var(--{'ok' if good else 'bad'})'>{text}</div></div>")


data_rows = [
    ("NASA POWER", "35 years of daily weather: heat, frost, rain, crop water demand", "used"),
    ("NASA SMAP", "How dry is the soil under the field?", "used" if "sm" in HAS else "integrating"),
    ("NASA / USGS HLS", "How green is each field?", "used" if "ndvi" in HAS else "integrating"),
]
data_html = "".join(f"<div class='src'><div class='sn'>{n}</div><div class='sd'>{d}</div><div class='st {s}'>{s}</div></div>"
                    for n, d, s in data_rows)
tests_txt = f"{N_TESTS} automated tests · " if N_TESTS else ""
risk_now, risk_was = risk_level(bal), risk_level(wc)

SLIDES = f"""
<section class="hero" data-background-image="img/karshi_modis_terra_2025-08-12.jpg" data-background-size="cover"
         data-background-opacity="0.42" data-background-color="#0f1a14">
  <p class="hook fragment fade-up">Every spring, a farmer near Karshi bets the family's year on one decision:</p>
  <p class="hook2 fragment fade-up">what to plant.</p>
  <div class="fragment fade-up">
    <h1><img class="logo" src="img/dalashift_logo_light.png" alt="DalaShift"></h1>
    <p class="tag">Don't just choose the most profitable crop for this year.<br>Choose the best five-year future for your field.</p>
    <p class="meta">Field Shift: Adapting Farms with NASA Data · NASA Space Apps 2026 · Karshi · <b>KarPS</b></p>
  </div>
  <p class="credit">Karshi oasis from space: NASA MODIS Terra, 12 Aug 2025 (Worldview). The farmer is an illustrative persona.</p>
</section>

<section>
  <img class="corner" src="img/dalashift_mark.png" alt="">
  <h2>The rules changed.</h2>
  <div class="big"><span class="count" data-from="{k_then}" data-to="{k_now}">{k_now}</span> <small>very hot days a year in Karshi, up from {k_then}</small></div>
  {chart_svg()}
  <p class="sub">Days above 35 °C, 1991–2026 · season rain {rain_then} → {rain_now} mm · NASA POWER</p>
</section>

<section>
  <img class="corner" src="img/dalashift_mark.png" alt="">
  <h2>But fields are still planned one year at a time.</h2>
  {water_bars()}
  <p class="sub">The usual wheat ↔ cotton rotation: cotton years need <b class="badtxt">{over_pct} % more water</b> than the farm gets.</p>
</section>

<section>
  <img class="corner" src="img/dalashift_mark.png" alt="">
  <h2>DalaShift plans five years ahead.</h2>
  <div class="phonewrap">
    <div class="phone"><div class="screen"><img class="scroll" src="../screenshots/farmer_full_phone.png" alt="DalaShift on a phone"></div></div>
    <ol class="steps">
      <li class="fragment fade-left">Pick your field.</li>
      <li class="fragment fade-left">See what changed.</li>
      <li class="fragment fade-left">Get a five-year plan.</li>
    </ol>
  </div>
  <p class="sub">Uzbek first · income in soʻm · one plain reason for every choice</p>
</section>

<section>
  <img class="corner" src="img/dalashift_mark.png" alt="">
  <h2>NASA satellites, explained like a neighbour.</h2>
  <div class="two">
    <div>{data_html}</div>
    <div class="sees">
      <div class="say fragment fade-up">“{k_now - k_then} more very hot days a year than in the 1990s.”</div>
      <div class="say fragment fade-up">“{rain_then - rain_now} mm less rain in the growing season.”</div>
      <div class="say fragment fade-up">“Each hectare needs ~{et0_t:,.0f} more tonnes of water a year.”</div>
      {f'<div class="say fragment fade-up">“Without canal water, your soil dries {SMAP_K["drop_pct"]} % from spring to summer.” <small>(SMAP, {SMAP_K["year"]})</small></div>' if SMAP_K else ''}
    </div>
  </div>
  <p class="sub">Also used, non-NASA: FAO-56 crop water method · FAOSTAT yields · Korzinka and Uzum retail prices</p>
</section>

<section>
  <img class="corner" src="img/dalashift_mark.png" alt="">
  <h2>What it changes in Karshi.</h2>
  <p class="plan">{" → ".join(bal_names)}</p>
  <div class="cmp">
    {cmp_bar("Water used", c_wc['water_pct'], f"{c_wc['water_pct']:+.0f} %", c_wc['water_pct'] < 0)}
    {cmp_bar("Income", c_wc['income_pct'], f"{c_wc['income_pct']:+.0f} %", c_wc['income_pct'] > 0)}
    <div class="cb"><div class="cl">Risk</div><div class="cv" style="grid-column: 2 / 4; color:var(--muted)">{"same: " + risk_now if risk_now == risk_was else risk_was + " → " + risk_now}</div></div>
  </div>
  <p class="sub">Balanced plan vs the usual wheat ↔ cotton, same farm, {BUDGET:,} t of water per ha · about {bal_low:g} mln soʻm / ha / year, conservative.<br>
  Must grow cotton? It needs {cotton_need:,} t / ha here: DalaShift says so, then shows the closest plan.</p>
</section>

<section>
  <img class="corner" src="img/dalashift_mark.png" alt="">
  <h2>Next: every field in Uzbekistan.</h2>
  <div class="road">
    <div class="rs fragment fade-up"><b>Uzcosmos</b><span>and national farm data</span></div>
    <div class="rs fragment fade-up"><b>Soil &amp; salinity</b><span>per field: SMAP, ECOSTRESS, HLS</span></div>
    <div class="rs fragment fade-up"><b>Telegram bot</b><span>in Uzbek</span></div>
    <div class="rs fragment fade-up"><b>More crops</b><span>melon varieties, real costs</span></div>
  </div>
  <p class="team"><b>KarPS</b> · {TEAM}</p>
  <p class="sub">{tests_txt}up to {n_seq:,} five-year plans checked per farm · Repo <b>github.com/FynamicUZ/dalashift</b> · App <b>dalashift.netlify.app</b></p>
</section>
"""

CSS = """
:root { --green:#1f5f3f; --ok:#2e7d4f; --warn:#c98a1b; --bad:#c0442f; --ink:#1d2521; --muted:#6b716d; --line:#e4e1d8; --bg:#faf9f6; }
.reveal { font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif; color: var(--ink); font-size: 34px; }
.reveal-viewport { background: var(--bg); }
.reveal h1, .reveal h2 { font-family: inherit; text-transform: none; color: var(--ink); letter-spacing: -0.01em; }
.reveal h2 { font-size: 1.55em; font-weight: 700; margin-bottom: .6em; }
.reveal .slide-number { font-size: 20px; background: transparent; color: var(--muted); }
.sub { font-size: .55em; color: var(--muted); margin-top: .8em; line-height: 1.5; }
.ph { background: #fff3c4; border: 2px dashed var(--warn); padding: 0 .3em; font-weight: 700; color: #6b4e00; }
/* 1 hero */
.reveal .hero, .reveal .hero h1, .reveal .hero p { color: #fff; text-align: left; }
.hero .hook { font-size: 1.15em; font-weight: 500; max-width: 1150px; line-height: 1.35; }
.hero .hook2 { font-size: 2.1em; font-weight: 800; margin: .1em 0 .7em; }
.hero h1 { font-size: 2.5em; margin: 0; color: #fff; }
.hero .tag { font-size: .8em; } .hero .meta { font-size: .5em; opacity: .9; }
.hero .credit { font-size: .32em; opacity: .75; margin-top: 2.5em; }
/* 2 chart */
.big { display: flex; align-items: baseline; justify-content: center; gap: 24px; }
.big .count { font-size: 3.2em; font-weight: 800; color: var(--bad); line-height: 1; }
.big small { font-size: .65em; color: var(--muted); }
.chart { width: 900px; height: 360px; display: block; margin: 10px auto 0; }
.chart .ax { font-size: 20px; fill: var(--muted); font-weight: 600; paint-order: stroke; stroke: #faf9f6; stroke-width: 6px; }
.chart .draw { stroke-dasharray: 3000; stroke-dashoffset: 3000; }
.chart .mean { opacity: 0; }
.present .chart .draw, .print .chart .draw { animation: draw 3.6s ease-out .8s forwards; }
.present .chart .mean, .print .chart .mean { animation: fadein .9s 4.2s forwards; }
.print .chart .draw { animation: none; stroke-dashoffset: 0; } .print .chart .mean { animation: none; opacity: 1; }
@keyframes draw { to { stroke-dashoffset: 0; } } @keyframes fadein { to { opacity: 1; } }
/* 3 water bars */
.wbars { position: relative; display: flex; gap: 40px; justify-content: center; height: 480px; align-items: flex-end; }
.wb { width: 170px; display: flex; flex-direction: column; align-items: center; height: 100%; justify-content: flex-end; }
.wcol { width: 110px; height: 78%; display: flex; align-items: flex-end; }
.wfill { width: 100%; height: 0; border-radius: 10px 10px 0 0; transition: height 1.8s ease-out; }
.present .wb:nth-child(2) .wfill { transition-delay: .8s; } .present .wb:nth-child(3) .wfill { transition-delay: 1.1s; }
.present .wb:nth-child(4) .wfill { transition-delay: 1.4s; } .present .wb:nth-child(5) .wfill { transition-delay: 1.7s; }
.present .wb:nth-child(6) .wfill { transition-delay: 2.0s; }
.present .wfill, .print .wfill { height: var(--h); }
.ok { background: var(--ok); } .bad { background: var(--bad); }
.wl { font-size: .5em; color: var(--muted); padding-top: 8px; line-height: 1.3; height: 22%; box-sizing: border-box; } .wl b { color: var(--ink); }
.budget { position: absolute; left: 0; right: 0; border-top: 3px dashed var(--ink); z-index: 2; }
.budget span { position: absolute; right: 0; top: -1.7em; font-size: .45em; font-weight: 600; background: var(--bg); padding: 0 .4em; }
.badtxt { color: var(--bad); }
/* 4 phone */
.phonewrap { display: flex; gap: 90px; justify-content: center; align-items: center; }
.phone { width: 300px; height: 600px; border-radius: 42px; background: #111; padding: 14px; box-shadow: 0 30px 60px rgba(0,0,0,.25); }
.screen { width: 100%; height: 100%; border-radius: 30px; overflow: hidden; background: #fff; }
.reveal .screen img.scroll { width: 100%; margin: 0; max-width: none; max-height: none; border: 0; display: block; }
.present .screen img.scroll { animation: scrollshot 20s ease-in-out 1.5s infinite alternate; }
@keyframes scrollshot { 0%, 8% { transform: translateY(0); } 92%, 100% { transform: translateY(calc(-100% + 572px)); } }
.reveal ol.steps, .reveal ol.steps li { list-style: none; }
.steps { text-align: left; font-size: 1.1em; font-weight: 700; list-style: none; counter-reset: s; margin: 0; }
.steps li { margin: .6em 0; counter-increment: s; }
.steps li::before { content: counter(s); display: inline-block; width: 1.5em; height: 1.5em; line-height: 1.5em; border-radius: 50%;
  background: var(--green); color: #fff; text-align: center; margin-right: .6em; font-size: .8em; }
/* 5 data */
.two { display: grid; grid-template-columns: 1.15fr 1fr; gap: 50px; align-items: center; text-align: left; }
.src { display: grid; grid-template-columns: 220px 1fr 140px; gap: 14px; align-items: center; padding: 14px 0; border-bottom: 1px solid var(--line); font-size: .5em; }
.src .sn { font-weight: 700; } .src .sd { color: var(--muted); }
.src .st { font-weight: 700; text-align: center; border-radius: 999px; padding: 4px 8px; }
.src .st.used { color: var(--ok); border: 2px solid var(--ok); } .src .st.limited, .src .st.integrating { color: var(--warn); border: 2px solid var(--warn); }
.say { background: #fff; border: 1px solid var(--line); border-radius: 16px; padding: 16px 22px; margin: 16px 0; font-size: .62em;
       box-shadow: 0 4px 16px rgba(20,30,25,.05); }
/* 6 comparison */
.plan { font-size: .62em; font-weight: 600; color: var(--green); }
.cmp { max-width: 1250px; margin: 30px auto 0; }
.cb { display: grid; grid-template-columns: 170px 1fr 360px; gap: 22px; align-items: center; margin: 24px 0; }
.cl { font-size: .75em; font-weight: 700; text-align: right; }
.ct { height: 36px; background: #efece4; border-radius: 18px; overflow: hidden; }
.cf { height: 100%; width: 0; border-radius: 18px; transition: width 2s ease-out .8s; }
.present .cb:nth-child(2) .cf { transition-delay: 1.3s; }
.present .cf, .print .cf { width: var(--w); }
.cv { font-size: .95em; font-weight: 800; text-align: left; }
/* 7 roadmap */
.road { display: grid; grid-template-columns: repeat(4, 1fr); gap: 22px; margin: 30px 0; }
.rs { background: #fff; border: 1px solid var(--line); border-top: 6px solid var(--green); border-radius: 14px; padding: 22px; text-align: left; }
.rs b { display: block; font-size: .78em; } .rs span { font-size: .52em; color: var(--muted); }
.team { font-size: .55em; }
.reveal img.corner { position: absolute; top: -10px; left: 0; width: 64px; height: 64px; margin: 0; }
.reveal .hero h1 img.logo { height: 1.4em; width: auto; margin: 0; display: block; }
"""

JS = """
function countUp(slide) {
  slide.querySelectorAll('.count').forEach(function (el) {
    var a = +el.dataset.from, b = +el.dataset.to, t0 = null;
    function step(t) { if (!t0) t0 = t; var p = Math.min(Math.max(t - t0 - 800, 0) / 2400, 1);
      el.textContent = Math.round(a + (b - a) * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(step); }
    requestAnimationFrame(step);
  });
}
if (/print-pdf/.test(location.search)) { document.documentElement.classList.add('print'); }
else { Reveal.on('ready', function (e) { countUp(e.currentSlide); });
       Reveal.on('slidechanged', function (e) { countUp(e.currentSlide); }); }
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
<style>{CSS}
@media print {{ .reveal .slides .pdf-page:last-of-type {{ page-break-after: avoid !important; break-after: avoid !important; }} }}
</style>
</head>
<body>
<div class="reveal"><div class="slides">
{SLIDES}
</div></div>
<script src="{base}/reveal.min.js"></script>
<script>
Reveal.initialize({{ hash: true, controls: false, progress: true, slideNumber: 'c/t', width: 1600, height: 900,
  margin: 0.04, transition: 'slide', transitionSpeed: 'slow', backgroundTransition: 'fade', pdfSeparateFragments: false, pdfMaxPagesPerSlide: 1 }});
{JS}
</script>
</body>
</html>
"""


(DECK / "index.html").write_text(page(CDN), encoding="utf-8", newline="\n")
(DECK / "offline.html").write_text(page("vendor"), encoding="utf-8", newline="\n")
print("wrote index.html and offline.html")
print(json.dumps({"hot": [k_then, k_now], "rain": [rain_then, rain_now], "et0_t": et0_t, "wheat_need": wheat_need,
                  "cotton_need": cotton_need, "over_pct": over_pct, "balanced": bal["sequence"], "bal_low_mln": bal_low,
                  "vs_wheat_cotton": {k: round(v) if isinstance(v, float) else v for k, v in c_wc.items()},
                  "vs_fallback": {k: round(v) if isinstance(v, float) else v for k, v in c_fb.items()},
                  "n_seq": n_seq, "appeears": HAS_APPEEARS}, indent=1))
