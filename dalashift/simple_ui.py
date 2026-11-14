"""Farmer view: three plain steps, big numbers, no jargon.

Same engine and numbers as the expert view (dalashift.planner via planner_ui._run); only the
presentation is simpler. Money is shown in so'm per hectare per year (USD x the CBU rate in
config/retail_to_farmgate.yaml), water as a coloured bar against the farm's own water.
"""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st
import yaml

from .i18n import CROP_NAMES, DISTRICTS
from .planner import CONFIG, load_planner_config
from .planner_ui import _run

FARMER_DISTRICTS = ["Karshi", "Fergana", "Urgench", "Nukus", "Gulistan"]
# water a farmer can pick without knowing m3 (net irrigation water per ha per year; HYPOTHETICAL levels)
WATER_LEVELS = {"little": 6000, "normal": 8000, "plenty": 12000}
PLANS = ["profit", "balanced", "water"]
MUST_YEARS = 2          # "must grow cotton / wheat" = at least 2 of 5 years
GREEN, AMBER, RED, INK, MUTED = "#1f9d55", "#d97706", "#d64545", "#1b1b1b", "#6b6a66"

CSS = f"""
<style>
html {{ font-size: 18px; }}
.stMarkdown p, .stMarkdown li {{ font-size: 1.05rem; }}
#MainMenu, footer, [data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stSidebar"], [data-testid="collapsedControl"] {{ display: none; }}
.block-container {{ padding-top: 1.2rem; max-width: 1100px; }}
.f-step {{ font-size: 1.5rem; font-weight: 700; margin: 1.6rem 0 0.6rem; color: {INK}; }}
.f-card {{ border: 1px solid #e6e4dd; border-radius: 18px; padding: 18px 16px; text-align: center;
           background: #fff; height: 100%; }}
.f-icon {{ font-size: 2.4rem; line-height: 1.2; }}
.f-big {{ font-size: 2.4rem; font-weight: 800; line-height: 1.2; margin: 6px 0; }}
.f-text {{ font-size: 1.05rem; color: {MUTED}; }}
.f-years {{ display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin: 8px 0 4px; }}
.f-year {{ flex: 1 1 150px; max-width: 200px; border: 1px solid #e6e4dd; border-radius: 16px;
           padding: 12px 8px; text-align: center; background: #fff; }}
.f-year .y {{ color: {MUTED}; font-size: 0.95rem; }}
.f-year .e {{ font-size: 2.6rem; line-height: 1.3; }}
.f-year .n {{ font-weight: 700; font-size: 1.05rem; }}
.f-money {{ font-size: 2.6rem; font-weight: 800; color: {GREEN}; text-align: center; line-height: 1.2; }}
.f-bar {{ height: 26px; background: #eeece6; border-radius: 13px; overflow: hidden; }}
.f-bar > div {{ height: 100%; border-radius: 13px; }}
.stButton > button {{ font-size: 1.15rem; padding: 0.7rem 0.4rem; border-radius: 14px; width: 100%; }}
[data-testid="stButtonGroup"] button {{ padding: 0.55rem 1.2rem; min-height: 3rem; }}
[data-testid="stButtonGroup"] button p, .stButton > button p {{ font-size: 1.15rem; }}
[data-testid="stTabs"] button p {{ font-size: 1.1rem; }}
@media (max-width: 640px) {{ .f-big, .f-money {{ font-size: 2rem; }} .f-step {{ font-size: 1.3rem; }} }}
</style>
"""

FT = {
    "step1": {"uz": "1. Dalangiz qayerda?", "en": "1. Where is your field?"},
    "map": {"uz": "🗺️ Xaritada koʻrish", "en": "🗺️ Show on map"},
    "step2": {"uz": "2. Dalangizda nima oʻzgardi?", "en": "2. What changed on your field?"},
    "step2_sub": {"uz": "1991–2005 yillar bilan 2011–2026 yillarni solishtirdik (NASA sunʼiy yoʻldosh va ob-havo maʼlumotlari).",
                  "en": "We compared 1991–2005 with 2011–2026 (NASA satellite and weather data)."},
    "hot_title": {"uz": "Jazirama kunlar", "en": "Very hot days"},
    "hot_text": {"uz": "Yiliga 35 °C dan issiq kunlar: oldin {a}, hozir {b}.", "en": "Days above 35 °C a year: before {a}, now {b}."},
    "frost_title": {"uz": "Sovuqsiz mavsum", "en": "Frost-free season"},
    "frost_text": {"uz": "Sovuq urmaydigan kunlar: oldin {a}, hozir {b}.", "en": "Days without frost: before {a}, now {b}."},
    "frost_same": {"uz": "Deyarli oʻzgarmadi", "en": "About the same"},
    "water_title": {"uz": "Ekinlarga suv", "en": "Water for crops"},
    "water_text": {"uz": "Issiq tufayli har gektarga yiliga shuncha tonna koʻproq suv kerak.",
                   "en": "Because of the heat, each hectare needs this many more tonnes of water a year."},
    "water_less": {"uz": "Har gektarga yiliga shuncha tonna kamroq suv kerak.", "en": "Each hectare needs this many fewer tonnes of water a year."},
    "days": {"uz": "kun", "en": "days"},
    "tonnes": {"uz": "tonna", "en": "tonnes"},
    "step3": {"uz": "3. 5 yillik reja", "en": "3. Your 5-year plan"},
    "q_water": {"uz": "Dalangizga suv qancha keladi?", "en": "How much water does your field get?"},
    "w_little": {"uz": "Kam", "en": "Little"},
    "w_normal": {"uz": "Oʻrtacha", "en": "Medium"},
    "w_plenty": {"uz": "Koʻp", "en": "Plenty"},
    "q_must": {"uz": "Paxta / bugʻdoy ekish majburiymi?", "en": "Must you grow cotton / wheat?"},
    "must_help": {"uz": "Davlat buyurtmasi boʻlsa yoqing: rejada 5 yildan kamida 2 yil paxta va 2 yil bugʻdoy boʻladi.",
                  "en": "Switch on if you have a state order: the plan then has at least 2 years of cotton and 2 of wheat."},
    "must_cost": {"uz": "Bu majburiyat sizga 5 yilda taxminan **{m}** kamroq daromad beradi (gektariga).",
                  "en": "This obligation costs you about **{m}** less income over 5 years (per hectare)."},
    "must_free": {"uz": "Bu majburiyat daromadingizni kamaytirmaydi.", "en": "This obligation does not reduce your income."},
    "plan_profit": {"uz": "💰 Koʻproq daromad", "en": "💰 More income"},
    "plan_balanced": {"uz": "⚖️ Muvozanat", "en": "⚖️ Balanced"},
    "plan_water": {"uz": "💧 Kam suv", "en": "💧 Less water"},
    "year": {"uz": "{y}-yil", "en": "Year {y}"},
    "income": {"uz": "Taxminiy daromad, gektariga, yiliga", "en": "Expected income per hectare per year"},
    "water_use": {"uz": "Suv: eng koʻp suv talab qiladigan yil", "en": "Water: the thirstiest year"},
    "w_ok": {"uz": "Suvingiz yetadi", "en": "Your water is enough"},
    "w_tight": {"uz": "Suvingiz zoʻrgʻa yetadi", "en": "Your water is just enough"},
    "w_short": {"uz": "Suvingiz yetmaydi", "en": "Not enough water"},
    "why": {"uz": "Nega?", "en": "Why?"},
    "no_plan": {"uz": "Bu suv bilan barcha qoidalarga mos reja yoʻq. Quyida eng yaqin reja.",
                "en": "No plan fits every rule with this much water. Here is the closest one."},
    "no_cotton": {"uz": "🌱 Paxta bu yerda suvingizdan koʻproq suv talab qiladi, shuning uchun rejada yoʻq.",
                  "en": "🌱 Cotton needs more water here than you have, so it is not in the plan."},
    "disclaimer": {"uz": "Narxlar va xarajatlar taxminiy. Ekin oʻzgartirishdan oldin agronomingiz bilan maslahatlashing.",
                   "en": "Prices and costs are estimates. Talk to your agronomist before changing crops."},
    "expert_hint": {"uz": "Batafsil maʼlumot va NASA manbalari — «Mutaxassislar» boʻlimida.",
                    "en": "Details and NASA sources are in the “For judges & experts” tab."},
    "mln": {"uz": "mln soʻm", "en": "mln so'm"},
    "thousand": {"uz": "ming soʻm", "en": "thousand so'm"},
    "per": {"uz": "/ ga / yil", "en": "/ ha / year"},
    "then": {"uz": ", keyin ", "en": ", then "},
}

# one plain "why" sentence per crop
WHY = {
    "cotton": {"uz": "Paxta — anʼanaviy ekin, lekin juda koʻp suv ichadi.", "en": "Cotton is the traditional crop, but it drinks a lot of water."},
    "winter_wheat": {"uz": "Kuzgi bugʻdoy qishda oʻsadi va kam suv ichadi.", "en": "Winter wheat grows over winter and needs little water."},
    "barley": {"uz": "Arpa eng kam suv talab qiladi.", "en": "Barley needs the least water."},
    "maize": {"uz": "Makkajoʻxori yaxshi hosil beradi, lekin koʻp suv ichadi.", "en": "Maize yields well but needs a lot of water."},
    "rice": {"uz": "Sholi juda koʻp suv talab qiladi.", "en": "Rice needs a very large amount of water."},
    "sorghum": {"uz": "Joʻxori issiqqa va suv kamligiga chidamli.", "en": "Sorghum copes with heat and little water."},
    "sunflower": {"uz": "Kungaboqar moy uchun, suvni oʻrtacha ichadi.", "en": "Sunflower is grown for oil and needs medium water."},
    "mung_bean": {"uz": "Bugʻdoydan keyin mosh: bir yilda ikki hosil, tuproqqa azot beradi.", "en": "Mung bean after wheat: two harvests in one year, and it feeds the soil."},
    "chickpea": {"uz": "Noʻxat tuproqqa azot beradi — keyingi ekin yaxshiroq oʻsadi.", "en": "Chickpea feeds the soil with nitrogen, so the next crop grows better."},
    "potato": {"uz": "Kartoshka yaxshi daromad beradi, lekin bozor toʻlib qolmasligi uchun dalaning chorak qismigacha.", "en": "Potato pays well, but only on up to a quarter of the farm so the market is not flooded."},
    "onion": {"uz": "Piyoz yaxshi daromad beradi, lekin dalaning chorak qismigacha.", "en": "Onion pays well, but only on up to a quarter of the farm."},
    "tomato": {"uz": "Pomidor eng daromadli, lekin bozor sababli dalaning chorak qismigacha.", "en": "Tomato pays most, but only on up to a quarter of the farm because of the market."},
    "melon": {"uz": "Qovun.", "en": "Melon."},
    "alfalfa": {"uz": "Beda tuproqni tiklaydi va shoʻrlanishga qarshi kurashadi.", "en": "Alfalfa rebuilds the soil and fights salt."},
}


def ft(key: str, lang: str, **kw) -> str:
    s = FT[key][lang]
    return s.format(**kw) if kw else s


@st.cache_data(show_spinner=False)
def uzs_per_usd() -> float:
    cfg = yaml.safe_load((CONFIG / "retail_to_farmgate.yaml").read_text(encoding="utf-8"))
    return float(cfg.get("uzs_per_usd") or 12000.0)


def soum(usd: float, lang: str) -> tuple[float, str]:
    """USD -> (rounded number, unit) in million or thousand so'm, no decimals."""
    v = usd * uzs_per_usd()
    if abs(v) >= 1e6:
        return round(v / 1e6), ft("mln", lang)
    return round(v / 1e3, -1), ft("thousand", lang)


def soum_range(lo: float, hi: float, lang: str) -> str:
    a, unit = soum(lo, lang)
    b, unit_b = soum(hi, lang)
    if unit != unit_b:                       # e.g. 700 thousand - 1 mln -> show both in thousands
        a, b, unit = round(lo * uzs_per_usd() / 1e3, -1), round(hi * uzs_per_usd() / 1e3, -1), ft("thousand", lang)
    return f"{a:,.0f}–{b:,.0f} {unit}".replace(",", " ")


def _card(icon: str, big: str, title: str, text: str, color: str = INK) -> str:
    return (f"<div class='f-card'><div class='f-icon'>{icon}</div><div class='f-text'><b>{title}</b></div>"
            f"<div class='f-big' style='color:{color}'>{big}</div><div class='f-text'>{text}</div></div>")


def _crop_name(option: str, lang: str) -> str:
    return ft("then", lang).join(CROP_NAMES[c][lang] for c in option.split("+"))


def render(lang: str, planner_data: dict, summary: dict, points: pd.DataFrame) -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    cfg = load_planner_config()

    # ---------------------------------------------------------------- step 1: where
    st.markdown(f"<div class='f-step'>{ft('step1', lang)}</div>", unsafe_allow_html=True)
    d = st.segmented_control(ft("step1", lang), FARMER_DISTRICTS, default="Karshi", key="f_district",
                             format_func=lambda k: DISTRICTS[k][lang].split(" (")[0],
                             label_visibility="collapsed") or "Karshi"
    with st.expander(ft("map", lang)):
        pts = points[points["id"].str.startswith(d + "_")]
        st.map(pts.rename(columns={"lat": "latitude", "lon": "longitude"}), zoom=8, size=1500)
    pid = f"{d}_field1"

    # ---------------------------------------------------------------- step 2: what changed
    st.markdown(f"<div class='f-step'>{ft('step2', lang)}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='f-text'>{ft('step2_sub', lang)}</div>", unsafe_allow_html=True)
    S = summary["points"][pid]
    th, nw = S["then"], S["now"]
    c1, c2, c3 = st.columns(3)
    dh = round(nw["hot_days"] - th["hot_days"])
    c1.markdown(_card("🌡️", f"{dh:+d} {ft('days', lang)}", ft("hot_title", lang),
                      ft("hot_text", lang, a=round(th["hot_days"]), b=round(nw["hot_days"])),
                      RED if dh > 0 else GREEN), unsafe_allow_html=True)
    ff = (th.get("frost_free_days"), nw.get("frost_free_days"))
    if None not in ff:
        dfz = round(ff[1] - ff[0])
        big = f"{dfz:+d} {ft('days', lang)}" if abs(dfz) >= 2 else f"≈ 0 {ft('days', lang)}"
        c2.markdown(_card("❄️", big, ft("frost_title", lang),
                          (ft("frost_same", lang) + ". " if abs(dfz) < 2 else "")
                          + ft("frost_text", lang, a=round(ff[0]), b=round(ff[1])), AMBER if abs(dfz) >= 2 else INK),
                    unsafe_allow_html=True)
    de = (nw["gs_et0"] - th["gs_et0"]) * 10          # mm -> m3/ha = tonnes of water per ha
    tonnes = int(round(abs(de), -1))
    c3.markdown(_card("💧", f"{'+' if de >= 0 else '−'}{tonnes:,} {ft('tonnes', lang)}".replace(",", " "),
                      ft("water_title", lang), ft("water_text" if de >= 0 else "water_less", lang),
                      RED if de > 0 else GREEN), unsafe_allow_html=True)

    # ---------------------------------------------------------------- step 3: 5-year plan
    st.markdown(f"<div class='f-step'>{ft('step3', lang)}</div>", unsafe_allow_html=True)
    k1, k2 = st.columns([1.2, 1])
    with k1:
        st.markdown(f"**{ft('q_water', lang)}**")
        lvl = st.segmented_control(ft("q_water", lang), list(WATER_LEVELS), default="normal", key="f_water",
                                   format_func=lambda k: ft(f"w_{k}", lang), label_visibility="collapsed") or "normal"
    with k2:
        must = st.toggle(ft("q_must", lang), key="f_must", help=ft("must_help", lang))
    budget = WATER_LEVELS[lvl]

    point = planner_data["points"][pid]
    res = _run(json.dumps(point), float(budget), float(cfg["discount_rate"]), int(cfg["max_fresh_market_years"]),
               MUST_YEARS if must else 0, MUST_YEARS if must else 0)
    out = res["result"]

    if out["status"] == "ok":
        if "f_plan" not in st.session_state:
            st.session_state.f_plan = "balanced"
        b1, b2, b3 = st.columns(3)
        for col, kind in zip((b1, b2, b3), PLANS):
            p = out["plans"][kind]
            r = p["profit_per_year_range"]
            if col.button(ft("plan_" + kind, lang), key=f"f_btn_{kind}",
                          type="primary" if st.session_state.f_plan == kind else "secondary", use_container_width=True):
                st.session_state.f_plan = kind
                st.rerun()
            col.markdown(f"<div class='f-text' style='text-align:center;margin:-0.4rem 0 0.9rem'>{soum_range(r['low'], r['high'], lang)} {ft('per', lang)}</div>",
                         unsafe_allow_html=True)
        plan = out["plans"][st.session_state.f_plan]
    else:
        plan = out["plans"].get("least_harm")
        st.error(ft("no_plan", lang))
        if not plan:
            return

    # 5 crop icons, Year 1..5
    tiles = "".join(
        f"<div class='f-year'><div class='y'>{ft('year', lang, y=y['year'])}</div>"
        f"<div class='e'>{' '.join(CROP_NAMES[c]['icon'] for c in y['crops'])}</div>"
        f"<div class='n'>{_crop_name(y['option'], lang)}</div></div>" for y in plan["years"])
    st.markdown(f"<div class='f-years'>{tiles}</div>", unsafe_allow_html=True)

    m, w = st.columns(2, gap="large")
    r = plan["profit_per_year_range"]
    m.markdown(f"<div class='f-text' style='text-align:center'>{ft('income', lang)}</div>"
               f"<div class='f-money'>{soum_range(r['low'], r['high'], lang)}</div>"
               f"<div class='f-text' style='text-align:center'>{ft('per', lang)}</div>", unsafe_allow_html=True)
    peak = max(y["water"] for y in plan["years"])
    share = peak / budget if budget else 2
    color, label = (GREEN, "w_ok") if share <= 0.8 else (AMBER, "w_tight") if share <= 1.0 + 1e-9 else (RED, "w_short")
    w.markdown(f"<div class='f-text' style='text-align:center'>{ft('water_use', lang)}</div>"
               f"<div class='f-bar' style='margin:14px 0 8px'><div style='width:{min(share, 1) * 100:.0f}%;background:{color}'></div></div>"
               f"<div style='text-align:center;font-size:1.4rem;font-weight:700;color:{color}'>{ft(label, lang)}</div>",
               unsafe_allow_html=True)

    if must:
        cc = (res.get("constraint_cost") or {}).get(st.session_state.get("f_plan", "balanced")) if out["status"] == "ok" else None
        if cc and cc["npv_cost"] is not None:
            if cc["npv_cost"] > 1:
                a, unit = soum(cc["npv_cost"], lang)
                st.info("🏛️ " + ft("must_cost", lang, m=f"{a:,.0f} {unit}".replace(",", " ")))
            else:
                st.info("🏛️ " + ft("must_free", lang))

    # why: one plain sentence per crop
    st.markdown(f"<div class='f-step' style='font-size:1.3rem'>{ft('why', lang)}</div>", unsafe_allow_html=True)
    seen = []
    for y in plan["years"]:
        for c in y["crops"]:
            if c not in seen:
                seen.append(c)
    for c in seen:
        st.markdown(f"{CROP_NAMES[c]['icon']} {WHY[c][lang]}")
    if not any("cotton" in y["crops"] for y in plan["years"]) and point["baseline"]["cotton"]["need_m3ha"] > budget:
        st.markdown(ft("no_cotton", lang))

    st.write("")
    st.caption("⚠️ " + ft("disclaimer", lang))
    st.caption("🔎 " + ft("expert_hint", lang))
