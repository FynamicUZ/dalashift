"""Farmer view: a calm, professional field card + 5-year plan, relative to the farm's usual rotation.

Same engine and numbers as the expert view (dalashift.planner via planner_ui._run); only the
presentation differs. Money: ONE conservative figure (the low end of the estimate, rounded down to
0.5 mln so'm) with a small +/-15 % band; every plan is also shown relative to "your usual rotation"
(dalashift.baseline). No emoji and no jargon on this screen.
"""
from __future__ import annotations

import json
import math

import pandas as pd
import streamlit as st
import yaml

from .baseline import compare, evaluate_usual, water_deficit
from .crops import load_crop_table
from .i18n import CROP_NAMES, DISTRICTS, MONTHS
from .planner import CONFIG, load_planner_config
from .planner_ui import _run

FARMER_DISTRICTS = ["Karshi", "Fergana", "Urgench", "Nukus", "Gulistan"]
# water a farmer can pick without knowing m3 (net irrigation water per ha per year; HYPOTHETICAL levels)
WATER_LEVELS = {"little": 6000, "normal": 8000, "plenty": 12000}
PLANS = ["profit", "balanced", "water"]
MUST_YEARS = 2          # "must grow cotton / wheat" = at least 2 of 5 years

GREEN, BG, INK, MUTED, LINE = "#1f5f3f", "#faf9f6", "#1d2521", "#6b716d", "#e4e1d8"
OK, WARN, BAD = "#2e7d4f", "#c98a1b", "#c0442f"
FAMILY_COLOR = {"Poaceae": "#c8a24a", "Fabaceae": "#2e7d4f", "Malvaceae": "#4f7cac", "Solanaceae": "#b5523b",
                "Amaryllidaceae": "#8a5a9e", "Asteraceae": "#d2a12b", "Cucurbitaceae": "#7aa63f"}

# Lucide icons (ISC licence), inline SVG
_SVG = ("<svg xmlns='http://www.w3.org/2000/svg' width='{s}' height='{s}' viewBox='0 0 24 24' fill='none' "
        "stroke='{c}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>{p}</svg>")
ICONS = {
    "pin": "<path d='M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z'/><circle cx='12' cy='10' r='3'/>",
    "thermo": "<path d='M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z'/>",
    "rain": "<path d='M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242'/><path d='M16 14v6'/><path d='M8 14v6'/><path d='M12 16v6'/>",
    "drop": "<path d='M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z'/>",
    "coins": "<circle cx='8' cy='8' r='6'/><path d='M18.09 10.37A6 6 0 1 1 10.34 18'/><path d='M7 6h1v4'/>",
    "shield": "<path d='M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z'/>",
    "alert": "<path d='m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z'/><path d='M12 9v4'/><path d='M12 17h.01'/>",
}


def icon(name: str, color: str = GREEN, size: int = 18) -> str:
    return _SVG.format(s=size, c=color, p=ICONS[name])


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, .stMarkdown, .stButton button, [data-testid="stButtonGroup"] button, [data-testid="stTabs"] button,
[data-testid="stWidgetLabel"], input {{ font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif !important; }}
html {{ font-size: 17px; }}
.stApp {{ background: {BG}; }}
#MainMenu, footer, [data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stSidebar"], [data-testid="collapsedControl"] {{ display: none; }}
.block-container {{ padding-top: 1.2rem; max-width: 1080px; }}
.f-eyebrow {{ font-size: .75rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: {GREEN}; margin-top: 1.3rem; }}
.f-h {{ font-size: 1.35rem; font-weight: 700; color: {INK}; margin: .15rem 0 .7rem; }}
.f-card {{ background: #fff; border: 1px solid {LINE}; border-radius: 14px; padding: 18px 20px;
           box-shadow: 0 1px 2px rgba(20,30,25,.04), 0 4px 16px rgba(20,30,25,.04); }}
.f-district {{ display:flex; align-items:center; gap:8px; font-size:1.25rem; font-weight:700; color:{INK}; }}
.f-sub {{ color:{MUTED}; font-size:.88rem; }}
.f-facts {{ display:grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 14px; }}
.f-fact {{ border-top: 1px solid {LINE}; padding-top: 10px; }}
.f-fact .l {{ display:flex; align-items:center; gap:6px; color:{MUTED}; font-size:.82rem; min-height: 2.4em; }}
.f-fact .v {{ font-size:1.2rem; font-weight:700; color:{INK}; margin-top:2px; }}
.f-fact .d {{ font-size:.85rem; font-weight:600; }}
.f-steps {{ display:grid; grid-template-columns: repeat(5, 1fr); margin: 6px 0 4px; }}
.f-step {{ padding: 0 10px 0 0; position: relative; }}
.f-step::before {{ content:''; position:absolute; top:6px; left:0; right:0; height:2px; background:{LINE}; }}
.f-step .dot {{ width: 14px; height: 14px; border-radius: 50%; border: 3px solid #fff; box-shadow: 0 0 0 1px {LINE};
                margin-bottom: 10px; position: relative; z-index: 1; }}
.f-step .y {{ font-size:.72rem; font-weight:600; color:{MUTED}; text-transform: uppercase; letter-spacing:.05em; }}
.f-step .c {{ font-weight:700; color:{INK}; font-size:1rem; margin: 2px 0; line-height: 1.25; min-height: 2.5em; }}
.f-step .m {{ font-size:.82rem; color:{MUTED}; }}
.f-wbar {{ height:6px; background:#efece4; border-radius:3px; margin-top:8px; overflow:hidden; }}
.f-wbar > div {{ height:100%; border-radius:3px; }}
.f-cmp {{ display:grid; grid-template-columns: 1.4fr 1fr 1fr 1fr; margin-top: 16px; border:1px solid {LINE};
          border-radius:12px; overflow:hidden; background:#fff; }}
.f-cmp > div {{ padding: 12px 14px; border-left: 1px solid {LINE}; }}
.f-cmp > div:first-child {{ border-left: none; background: #f6f3ea; }}
.f-cmp .l {{ display:flex; align-items:center; gap:6px; font-size:.8rem; color:{MUTED}; }}
.f-cmp .v {{ font-size:1.15rem; font-weight:700; margin-top: 2px; }}
.f-money {{ font-size: 1.9rem; font-weight: 700; color: {INK}; line-height: 1.2; }}
.f-why {{ font-size: 1rem; line-height: 1.65; color: {INK}; }}
.f-note {{ display:flex; gap:8px; align-items:flex-start; font-size:.9rem; color:{INK}; background:#fbf3e4;
           border:1px solid #f0dfbc; border-radius:10px; padding:10px 12px; margin-top:14px; }}
[data-testid="stButtonGroup"] button {{ border-radius: 10px; }}
.f-card svg, .f-cmp svg, .f-note svg {{ flex-shrink: 0; }}
@media (max-width: 700px) {{
  .f-facts {{ grid-template-columns: 1fr; }}
  .f-fact .l {{ min-height: 0; }}
  .f-steps {{ grid-template-columns: 1fr; gap: 8px; }}
  .f-step::before {{ display:none; }}
  .f-step {{ border:1px solid {LINE}; border-radius:10px; padding:10px 12px; background:#fff; }}
  .f-step .c {{ min-height: 0; display:inline; margin-right:8px; }}
  .f-step .dot {{ display:none; }}
  .f-step .y {{ display:inline; margin-right:8px; }}
  .f-step .m {{ display:inline; }}
  .f-step {{ padding: 8px 12px; }}
  .f-cmp {{ grid-template-columns: 1fr 1fr 1fr; }}
  .f-cmp > div:first-child {{ grid-column: 1 / -1; }}
}}
</style>
"""

FT = {
    "step1": {"uz": "Dalangiz qayerda?", "en": "Where is your field?"},
    "eyebrow1": {"uz": "Dala", "en": "Field"},
    "eyebrow2": {"uz": "5 yillik reja", "en": "5-year plan"},
    "plan_h": {"uz": "Keyingi besh yil uchun reja", "en": "Plan for the next five years"},
    "since": {"uz": "1991–2005 va 2011–2026 yillar, NASA maʼlumotlari", "en": "1991–2005 vs 2011–2026, NASA data"},
    "hot": {"uz": "Jazirama kunlar (35 °C dan issiq), yiliga", "en": "Very hot days (above 35 °C) a year"},
    "rain": {"uz": "Mavsumdagi yomgʻir (aprel–oktabr)", "en": "Season rain (April–October)"},
    "budget": {"uz": "Sizning suvingiz, gektariga yiliga", "en": "Your water, per hectare a year"},
    "mm": {"uz": "mm", "en": "mm"},
    "k_tonnes": {"uz": "ming tonna", "en": "thousand tonnes"},
    "q_water": {"uz": "Dalangizga suv qancha keladi?", "en": "How much water does your field get?"},
    "w_little": {"uz": "Kam", "en": "Little"},
    "w_normal": {"uz": "Oʻrtacha", "en": "Medium"},
    "w_plenty": {"uz": "Koʻp", "en": "Plenty"},
    "q_must": {"uz": "Paxta / bugʻdoy ekish majburiymi?", "en": "Must you grow cotton / wheat?"},
    "must_help": {"uz": "Davlat buyurtmasi boʻlsa yoqing: rejada 5 yildan kamida 2 yil paxta va 2 yil bugʻdoy boʻladi.",
                  "en": "Switch on if you have a state order: the plan then has at least 2 years of cotton and 2 of wheat."},
    "q_goal": {"uz": "Nima muhimroq?", "en": "What matters most?"},
    "plan_profit": {"uz": "Daromad", "en": "Income"},
    "plan_balanced": {"uz": "Muvozanat", "en": "Balanced"},
    "plan_water": {"uz": "Suv tejash", "en": "Save water"},
    "year": {"uz": "{y}-yil", "en": "Year {y}"},
    "income": {"uz": "Daromad, gektariga yiliga", "en": "Income per hectare per year"},
    "conservative": {"uz": "taxminan, ehtiyotkor hisob", "en": "approx., conservative estimate"},
    "band": {"uz": "oraliq ±15 %: {lo}–{hi} mln", "en": "range ±15 %: {lo}–{hi} mln"},
    "vs_usual": {"uz": "Odatiy almashlab ekishga nisbatan", "en": "Compared with your usual rotation"},
    "usual_short": {"uz": "suvingiz yetmaydi: paxta yilida {n} ming tonna kam", "en": "not enough water: {n} thousand tonnes short in cotton years"},
    "c_income": {"uz": "Daromad", "en": "Income"},
    "c_water": {"uz": "Suv", "en": "Water"},
    "c_risk": {"uz": "Xavf", "en": "Risk"},
    "risk_low": {"uz": "past", "en": "low"},
    "risk_medium": {"uz": "oʻrta", "en": "medium"},
    "risk_high": {"uz": "yuqori", "en": "high"},
    "same": {"uz": "deyarli bir xil", "en": "about the same"},
    "times": {"uz": "{x} barobar", "en": "{x}×"},
    "why": {"uz": "Nega bu reja?", "en": "Why this plan?"},
    "must_cost": {"uz": "Bu majburiyat sizga 5 yilda taxminan {m} kamroq daromad beradi (gektariga).",
                  "en": "This obligation costs you about {m} less income over 5 years (per hectare)."},
    "must_free": {"uz": "Bu majburiyat daromadingizni kamaytirmaydi.", "en": "This obligation does not reduce your income."},
    "cotton_short": {"uz": "Paxta uchun gektariga taxminan {n} ming tonna suv kerak, sizda {b} ming tonna bor. Quyida eng kam zararli reja.",
                     "en": "Cotton needs about {n} thousand tonnes of water per hectare, you have {b} thousand. Below is the least-harmful plan."},
    "no_plan": {"uz": "Bu suv bilan barcha qoidalarga mos reja yoʻq. Quyida eng yaqin reja.",
                "en": "No plan fits every rule with this much water. Here is the closest one."},
    "disclaimer": {"uz": "Narxlar va xarajatlar taxminiy. Ekin oʻzgartirishdan oldin agronomingiz bilan maslahatlashing.",
                   "en": "Prices and costs are estimates. Talk to your agronomist before changing crops."},
    "expert_hint": {"uz": "Batafsil maʼlumot va NASA manbalari — «Mutaxassislar» boʻlimida.",
                    "en": "Details and NASA sources are in the “For judges & experts” tab."},
    "mln": {"uz": "mln soʻm", "en": "mln so'm"},
    "thousand": {"uz": "ming soʻm", "en": "thousand so'm"},
}

# plain-language building blocks for the "why" paragraph
WHY = {
    "legume": {"uz": "{c} tuproqqa azot beradi, shuning uchun undan keyingi ekin yaxshiroq hosil beradi.",
               "en": "{c} feeds the soil with nitrogen, so the crop after it yields better."},
    "rotate": {"uz": "Ekinlar har yili almashadi — zararkunanda va kasalliklar kamroq toʻplanadi.",
               "en": "The crop changes every year, so pests and diseases build up less."},
    "water": {"uz": "Eng koʻp suv talab qiladigan yilda ham suvingizning {s} ishlatiladi.",
              "en": "Even the thirstiest year uses {s} of your water."},
    "share_low": {"uz": "yarmidan kami", "en": "less than half"},
    "share_mid": {"uz": "katta qismi", "en": "most"},
    "share_full": {"uz": "deyarli hammasi", "en": "almost all"},
    "share_over": {"uz": "hammasi va undan ham koʻprogʻi", "en": "all of it and more"},
    "fresh": {"uz": "{c} yaxshi pul keltiradi, lekin bozor toʻlib qolmasligi uchun dalaning chorak qismidan oshmaydi.",
              "en": "{c} pays well, but stays on at most a quarter of the farm so the market is not flooded."},
    "wheat": {"uz": "Kuzgi bugʻdoy qishda oʻsadi va kam suv ichadi.", "en": "Winter wheat grows over winter and needs little water."},
    "no_cotton": {"uz": "Paxta bu yerda gektariga taxminan {n} ming tonna suv talab qiladi — bu sizdagidan koʻp, shuning uchun u rejada yoʻq.",
                  "en": "Cotton needs about {n} thousand tonnes of water per hectare here, more than you have, so it is not in the plan."},
    "vs": {"uz": "Odatiy almashlab ekishingizga nisbatan daromad {i}, suv {w}.",
           "en": "Compared with your usual rotation, income is {i} and water use is {w}."},
    "more": {"uz": "{p} koʻproq", "en": "{p} higher"},
    "less": {"uz": "{p} kamroq", "en": "{p} lower"},
}


def ft(key: str, lang: str, **kw) -> str:
    s = FT[key][lang]
    return s.format(**kw) if kw else s


def wt(key: str, lang: str, **kw) -> str:
    s = WHY[key][lang]
    return s.format(**kw) if kw else s


@st.cache_data(show_spinner=False)
def uzs_per_usd() -> float:
    cfg = yaml.safe_load((CONFIG / "retail_to_farmgate.yaml").read_text(encoding="utf-8"))
    return float(cfg.get("uzs_per_usd") or 12000.0)


@st.cache_data(show_spinner=False)
def _families() -> dict:
    t = load_crop_table()
    return dict(zip(t.index, t["family"]))


@st.cache_data(show_spinner=False)
def _usual(point_json: str, budget: float, rate: float, fresh: int) -> dict:
    return evaluate_usual(json.loads(point_json)["baseline"], budget, rate, fresh)


def soum(usd: float, lang: str) -> tuple[float, str]:
    """USD -> (rounded number, unit) in million or thousand so'm."""
    v = usd * uzs_per_usd()
    if abs(v) >= 1e6:
        return round(v / 1e6), ft("mln", lang)
    return round(v / 1e3, -1), ft("thousand", lang)


def to_mln(usd: float, how=math.floor) -> float:
    """USD -> million so'm rounded to 0.5 (down by default: conservative)."""
    return how(usd * uzs_per_usd() / 1e6 * 2) / 2


def fmt_mln(x: float, lang: str) -> str:
    s = f"{x:.1f}".rstrip("0").rstrip(".")
    return s.replace(".", ",") if lang == "uz" else s


def crop_name(option: str, lang: str) -> str:
    return " + ".join(CROP_NAMES[c][lang] for c in option.split("+"))


def month(d: str, lang: str) -> str:
    """'11 Apr' -> 'Apr' (localised)."""
    return MONTHS[lang][MONTHS["en"].index(d.split()[1])]


def pct_text(p: float | None, lang: str) -> tuple[str, str]:
    """+18 % / -22 % / 2.5x and a colour (for income: higher = good)."""
    if p is None:
        return "–", MUTED
    if abs(p) < 3:
        return ft("same", lang), MUTED
    if p >= 100:
        return ft("times", lang, x=fmt_mln(round((1 + p / 100) * 2) / 2, lang)), OK
    return f"{p:+.0f} %", OK if p > 0 else BAD


def sparkline(values: list, width: int = 130, height: int = 26) -> str:
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    pts = " ".join(f"{i * width / (len(vals) - 1):.1f},{height - 2 - (v - lo) / span * (height - 4):.1f}"
                   for i, v in enumerate(vals))
    return (f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}' style='margin-top:4px'>"
            f"<polyline points='{pts}' fill='none' stroke='{BAD}' stroke-width='1.5' stroke-linejoin='round'/></svg>")


def _field_card(d: str, summary: dict, budget: float, lang: str) -> str:
    S = summary["points"][f"{d}_field1"]
    th, nw = S["then"], S["now"]
    dh = round(nw["hot_days"] - th["hot_days"])
    dr = round(nw["gs_rain"] - th["gs_rain"])
    return (
        f"<div class='f-card'><div class='f-district'>{icon('pin', GREEN, 20)} {DISTRICTS[d][lang]}</div>"
        f"<div class='f-sub'>{ft('since', lang)}</div><div class='f-facts'>"
        f"<div class='f-fact'><div class='l'>{icon('thermo', MUTED, 15)} {ft('hot', lang)}</div>"
        f"<div class='v'>{round(th['hot_days'])} → {round(nw['hot_days'])} "
        f"<span class='d' style='color:{BAD if dh > 0 else OK}'>{dh:+d}</span></div>{sparkline(S['annual']['hot_days'])}</div>"
        f"<div class='f-fact'><div class='l'>{icon('rain', MUTED, 15)} {ft('rain', lang)}</div>"
        f"<div class='v'>{round(th['gs_rain'])} → {round(nw['gs_rain'])} {ft('mm', lang)} "
        f"<span class='d' style='color:{BAD if dr < 0 else OK}'>{dr:+d}</span></div></div>"
        f"<div class='f-fact'><div class='l'>{icon('drop', MUTED, 15)} {ft('budget', lang)}</div>"
        f"<div class='v'>{fmt_mln(budget / 1000, lang)} {ft('k_tonnes', lang)}</div></div>"
        f"</div></div>")


def _timeline(plan: dict, point: dict, budget: float, lang: str) -> str:
    fam, m = _families(), point["baseline"]
    steps = []
    for y in plan["years"]:
        first, last = y["crops"][0], y["crops"][-1]
        months = f"{month(m[first]['sow'], lang)} → {month(m[last]['harvest'], lang)}"
        share = y["water"] / budget if budget else 2
        col = OK if share <= 0.8 else WARN if share <= 1.0 + 1e-9 else BAD
        steps.append(
            f"<div class='f-step'><div class='dot' style='background:{FAMILY_COLOR.get(fam[first], GREEN)}'></div>"
            f"<div class='y'>{ft('year', lang, y=y['year'])}</div><div class='c'>{crop_name(y['option'], lang)}</div>"
            f"<div class='m'>{months}</div>"
            f"<div class='f-wbar'><div style='width:{min(share, 1) * 100:.0f}%;background:{col}'></div></div></div>")
    return f"<div class='f-steps'>{''.join(steps)}</div>"


def _comparison(cmp: dict, usual: dict, lang: str, deficit: float = 0.0) -> str:
    inc, inc_col = pct_text(cmp["income_pct"], lang)
    wp = cmp["water_pct"]
    wat = ft("same", lang) if abs(wp) < 3 else f"{wp:+.0f} %"
    wat_col = MUTED if abs(wp) < 3 else (OK if wp < 0 else WARN)
    risk_col = {"low": OK, "medium": WARN, "high": BAD}[cmp["risk_plan"]]
    usual_name = " ↔ ".join(dict.fromkeys(CROP_NAMES[k][lang] for k in usual["sequence"]))
    return (f"<div class='f-cmp'><div><div class='l'>{ft('vs_usual', lang)}</div>"
            f"<div class='v' style='font-size:.95rem'>{usual_name}</div>"
            + (f"<div style='color:{BAD};font-size:.8rem;font-weight:600;margin-top:2px'>"
               f"{ft('usual_short', lang, n=fmt_mln(round(deficit / 100) / 10, lang))}</div>" if deficit > 0 else "")
            + "</div>"
            f"<div><div class='l'>{icon('coins', MUTED, 14)} {ft('c_income', lang)}</div><div class='v' style='color:{inc_col}'>{inc}</div></div>"
            f"<div><div class='l'>{icon('drop', MUTED, 14)} {ft('c_water', lang)}</div><div class='v' style='color:{wat_col}'>{wat}</div></div>"
            f"<div><div class='l'>{icon('shield', MUTED, 14)} {ft('c_risk', lang)}</div>"
            f"<div class='v' style='color:{risk_col}'>{ft('risk_' + cmp['risk_plan'], lang)}</div></div></div>")


def _why(plan: dict, cmp: dict, point: dict, budget: float, lang: str) -> str:
    parts = []
    crops = [c for y in plan["years"] for c in y["crops"]]
    legume = next((c for c in crops if c in ("chickpea", "mung_bean", "alfalfa")), None)
    if legume:
        parts.append(wt("legume", lang, c=CROP_NAMES[legume][lang]))
    fresh = next((c for c in crops if c in ("tomato", "onion", "potato")), None)
    if fresh:
        parts.append(wt("fresh", lang, c=CROP_NAMES[fresh][lang]))
    elif "winter_wheat" in crops:
        parts.append(wt("wheat", lang))
    seq = plan["sequence"]
    if all(a != b for a, b in zip(seq, seq[1:])):
        parts.append(wt("rotate", lang))
    share = max(y["water"] for y in plan["years"]) / budget
    s = "share_low" if share < 0.5 else "share_mid" if share < 0.85 else "share_full" if share <= 1.0 + 1e-9 else "share_over"
    parts.append(wt("water", lang, s=wt(s, lang)))
    p = cmp["income_pct"]
    if p is not None and abs(p) >= 3:
        inc = pct_text(p, lang)[0] if p >= 100 else wt("more" if p > 0 else "less", lang, p=f"{abs(p):.0f} %")
        w = cmp["water_pct"]
        wat = ft("same", lang) if abs(w) < 3 else wt("more" if w > 0 else "less", lang, p=f"{abs(w):.0f} %")
        parts.append(wt("vs", lang, i=inc, w=wat))
    need = point["baseline"]["cotton"]["need_m3ha"]
    if "cotton" not in crops and need > budget:
        parts.append(wt("no_cotton", lang, n=round(need / 1000)))
    return " ".join(parts)


def render(lang: str, planner_data: dict, summary: dict, points: pd.DataFrame) -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    cfg = load_planner_config()
    rate, fresh = float(cfg["discount_rate"]), int(cfg["max_fresh_market_years"])

    # ---------------------------------------------------------------- field
    st.markdown(f"<div class='f-eyebrow'>{ft('eyebrow1', lang)}</div><div class='f-h'>{ft('step1', lang)}</div>",
                unsafe_allow_html=True)
    d = st.segmented_control(ft("step1", lang), FARMER_DISTRICTS, default="Karshi", key="f_district",
                             format_func=lambda k: DISTRICTS[k][lang].split(" (")[0],
                             label_visibility="collapsed") or "Karshi"
    c1, c2 = st.columns([1.35, 1], gap="medium")
    with c2:
        st.markdown(f"<div class='f-sub' style='margin-bottom:6px'>{ft('q_water', lang)}</div>", unsafe_allow_html=True)
        lvl = st.segmented_control(ft("q_water", lang), list(WATER_LEVELS), default="normal", key="f_water",
                                   format_func=lambda k: ft(f"w_{k}", lang), label_visibility="collapsed") or "normal"
        must = st.toggle(ft("q_must", lang), key="f_must", help=ft("must_help", lang))
        pts = points[points["id"].str.startswith(d + "_")]
        st.map(pts.rename(columns={"lat": "latitude", "lon": "longitude"}), zoom=7, size=2500, height=160,
               color=GREEN)
    budget = WATER_LEVELS[lvl]
    with c1:
        st.markdown(_field_card(d, summary, budget, lang), unsafe_allow_html=True)

    # ---------------------------------------------------------------- plan
    point = planner_data["points"][f"{d}_field1"]
    pj = json.dumps(point)
    res = _run(pj, float(budget), rate, fresh, MUST_YEARS if must else 0, MUST_YEARS if must else 0)
    out = res["result"]
    st.markdown(f"<div class='f-eyebrow'>{ft('eyebrow2', lang)}</div><div class='f-h'>{ft('plan_h', lang)}</div>",
                unsafe_allow_html=True)

    kind = "least_harm"
    if out["status"] == "ok":
        kind = st.segmented_control(ft("q_goal", lang), PLANS, default="balanced", key="f_goal",
                                    format_func=lambda k: ft(f"plan_{k}", lang)) or "balanced"
        plan = out["plans"][kind]
    else:
        plan = out["plans"].get("least_harm")
        need = point["baseline"]["cotton"]["need_m3ha"]
        st.error(ft("cotton_short", lang, n=round(need / 1000), b=round(budget / 1000)) if must and need > budget
                 else ft("no_plan", lang))
        if not plan:
            return

    usual = _usual(pj, float(budget), rate, fresh)
    cmp = compare(plan, usual)
    r = plan["profit_per_year_range"]
    low, lo_b, hi_b = max(to_mln(r["low"]), 0), max(to_mln(r["low"]), 0), max(to_mln(r["high"], round), 0)
    st.markdown(f"<div class='f-card'>{_timeline(plan, point, budget, lang)}"
                f"<div style='margin-top:18px'><div class='f-sub'>{ft('income', lang)}</div>"
                f"<div class='f-money'>≈ {fmt_mln(low, lang)} {ft('mln', lang)}</div>"
                f"<div class='f-sub'>{ft('conservative', lang)} · "
                f"{ft('band', lang, lo=fmt_mln(lo_b, lang), hi=fmt_mln(hi_b, lang))}</div></div>"
                f"{_comparison(cmp, usual, lang, water_deficit(usual, budget))}</div>", unsafe_allow_html=True)

    if must and out["status"] == "ok":
        cc = (res.get("constraint_cost") or {}).get(kind)
        if cc and cc["npv_cost"] is not None:
            if cc["npv_cost"] > 1:
                a, unit = soum(cc["npv_cost"], lang)
                st.info(ft("must_cost", lang, m=f"{a:,.0f} {unit}".replace(",", " ")))
            else:
                st.info(ft("must_free", lang))

    st.markdown(f"<div class='f-eyebrow'>{ft('why', lang)}</div>"
                f"<div class='f-card f-why'>{_why(plan, cmp, point, budget, lang)}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='f-note'>{icon('alert', WARN, 18)}<div>{ft('disclaimer', lang)} "
                f"<span style='color:{MUTED}'>{ft('expert_hint', lang)}</span></div></div>", unsafe_allow_html=True)
