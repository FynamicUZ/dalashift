"""DalaShift - Streamlit app (NASA Space Apps 2026, challenge: Field Shift).

Reads only precomputed files in data/ - never calls NASA APIs live.
Run locally:  streamlit run app.py
"""
from __future__ import annotations

import json
from pathlib import Path

import folium
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from dalashift import planner_ui, simple_ui
from dalashift.appeears import load_appeears
from dalashift.crops import BASELINE
from dalashift.i18n import (CROP_NAMES, DISTRICTS, MONTHS, ROTATION_NAMES, field_label, fields_str, ldate,
                            profile_label, t)

ROOT = Path(__file__).parent
DATA = ROOT / "data"

# --- chart tokens (validated categorical pair: slot 1 blue = then, slot 2 orange = now)
C_THEN, C_NOW, C_MID = "#2a78d6", "#eb6834", "#c3c2b7"
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
RISK_ICON = {"low": "🟢", "medium": "🟠", "high": "🔴"}

st.set_page_config(page_title="DalaShift", page_icon="🌾", layout="wide")


# ------------------------------------------------------------------ data
@st.cache_data
def load_json(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


@st.cache_data
def load_points() -> pd.DataFrame:
    return pd.read_csv(DATA / "points.csv")


@st.cache_data
def load_water() -> pd.DataFrame:
    return load_appeears(DATA / "appeears", load_points())


summary, recs, points = load_json("summary.json"), load_json("recommendations.json"), load_points()
planner_data = {"points": load_json("planner.json")["points"],
                "coords": {r.id: (r.lat, r.lon) for r in points.itertuples()}}
ids = points["id"].tolist()


def style(fig: go.Figure, title: str, ytitle: str = "", height: int = 340) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=INK)), height=height,
        margin=dict(l=10, r=10, t=50, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=INK2, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="white", font_color=INK), bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, linecolor=AXIS, tickcolor=AXIS, tickfont_color=MUTED)
    fig.update_yaxes(gridcolor=GRID, gridwidth=1, zeroline=False, linecolor=AXIS,
                     tickfont_color=MUTED, title_text=ytitle, title_font_color=MUTED)
    return fig


# ------------------------------------------------------------------ state + sidebar
# The keyed selectbox is the single source of truth for the selected field. A map click
# stores "pending_point" and reruns; it is applied here, BEFORE the widget is created
# (Streamlit forbids changing a widget's state after it has been drawn in the same run).
if "point" not in st.session_state:
    st.session_state.point = "Karshi_field1"
if "last_click" not in st.session_state:
    st.session_state.last_click = None
if "pending_point" in st.session_state:
    st.session_state.point = st.session_state.pop("pending_point")

# ---- top bar: app name left, language toggle right (Uzbek first)
top_l, top_r = st.columns([3, 2], vertical_alignment="center")
with top_r:
    lang = "en" if st.segmented_control("Til / Language", ["Oʻzbekcha", "English"], default="Oʻzbekcha",
                                        key="lang_toggle", label_visibility="collapsed") == "English" else "uz"
with top_l:
    st.markdown("<div style='display:flex;align-items:center;gap:10px;font-family:Inter,system-ui,sans-serif'>"
                "<svg width='30' height='30' viewBox='0 0 24 24' fill='none' stroke='#1f5f3f' stroke-width='2' "
                "stroke-linecap='round' stroke-linejoin='round'><path d='M7 20h10'/><path d='M10 20c5.5-2.5.8-6.4 3-10'/>"
                "<path d='M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z'/>"
                "<path d='M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z'/></svg>"
                "<span style='font-size:1.55rem;font-weight:700;color:#1d2521'>DalaShift</span></div>",
                unsafe_allow_html=True)

tab_farmer, tab_expert = st.tabs([t("tab_farmer", lang), t("tab_expert", lang)])

# ------------------------------------------------------------------ FARMER VIEW (default)
with tab_farmer:
    simple_ui.render(lang, planner_data, summary, points, load_water())

# ------------------------------------------------------------------ EXPERT VIEW (everything else)
with tab_expert:
    st.title("🌾 " + t("title", lang))
    st.caption(t("tagline", lang))
    # one widget per language so option labels re-render in the chosen language;
    # "point" stays the canonical selection and is synced in via the widget's state + on_change
    wkey = f"field_select_{lang}"
    st.session_state[wkey] = st.session_state.point
    st.selectbox(t("field", lang), ids, key=wkey, format_func=lambda p: field_label(p, lang),
                 on_change=lambda: st.session_state.update(point=st.session_state[wkey]))
    st.caption(t("credits", lang))

pid = st.session_state.point
S, R = summary["points"][pid], recs["points"][pid]
district = pid.split("_")[0]
cell_fields = S["cell_fields"]
shared = len(cell_fields) > 1                     # fields in one POWER cell share a district profile
climate_title = profile_label(cell_fields, lang)

with tab_expert:
    tab_map, tab_then, tab_water, tab_plant, tab_planner = st.tabs(
        [t("tab_map", lang), t("tab_then_now", lang), t("tab_water", lang), t("tab_plant", lang),
         t("tab_planner", lang)])

# ------------------------------------------------------------------ 1. MAP
with tab_map:
    st.info(t("map_hint", lang))
    left, right = st.columns([3, 2])
    with left:
        m = folium.Map(location=[41.0, 65.0], zoom_start=6, tiles=None, control_scale=True)
        folium.TileLayer("OpenStreetMap", name="Map").add_to(m)
        folium.TileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery", name="Satellite").add_to(m)
        for cell in summary["cells"].values():  # MERRA-2 cell: 0.5 deg lat x 0.625 deg lon
            f0 = summary["points"][cell["fields"][0]]
            clat, clon = round(f0["lat"] / 0.5) * 0.5, round(f0["lon"] / 0.625) * 0.625
            folium.Rectangle([[clat - 0.25, clon - 0.3125], [clat + 0.25, clon + 0.3125]],
                             color=INK2, weight=1.5, dash_array="6 4", fill=True, fill_opacity=0.05,
                             tooltip=f"{t('power_cell', lang)}: {profile_label(cell['fields'], lang)}").add_to(m)
        for d, g in points.groupby(points["id"].str.split("_").str[0]):
            c = [g["lat"].mean(), g["lon"].mean()]
            folium.Marker([c[0] + 0.42, c[1]], icon=folium.DivIcon(
                html=f'<div style="font:600 12px system-ui;color:{INK};white-space:nowrap;'
                     f'text-shadow:0 0 3px #fff,0 0 3px #fff">{DISTRICTS[d][lang]}</div>')).add_to(m)
        for r in points.itertuples():
            is_sel = r.id == pid
            folium.CircleMarker([r.lat, r.lon], radius=10 if is_sel else 7,
                                color="#ffffff", weight=2, fill=True, fill_opacity=1,
                                fill_color=C_NOW if is_sel else C_THEN,
                                tooltip=field_label(r.id, lang)).add_to(m)
        folium.LayerControl(collapsed=True).add_to(m)
        out = st_folium(m, height=520, use_container_width=True,
                        returned_objects=["last_object_clicked"], key="map")
        click = (out or {}).get("last_object_clicked")
        if click and click != st.session_state.last_click:
            st.session_state.last_click = click
            d = np.hypot(points["lat"] - click["lat"], points["lon"] - click["lng"])
            nearest = points["id"].iloc[int(d.idxmin())]
            if nearest != pid:
                st.session_state.pending_point = nearest
                st.rerun()
    with right:
        st.subheader(field_label(pid, lang))
        st.caption(f"{S['lat']:.4f}° N, {S['lon']:.4f}° E · {t('elevation', lang)} {S['elevation_m']:.0f} m")
        top = R["ranking"]["now"][:3]
        st.markdown(f"**{t('top3', lang)}:** " + " · ".join(
            f"{CROP_NAMES[k]['icon']} {CROP_NAMES[k][lang]}" for k in top))
        st.markdown(f"**{t('climate_profile', lang)}: {climate_title}**")
        st.caption(t("shared_note", lang, fields=fields_str(cell_fields, lang)) if shared else t("own_cell", lang))
        rows = [(t("hot_days", lang), "hot_days", ""), (t("gdd10", lang), "gdd10", ""),
                (t("frost_free", lang), "frost_free_days", ""),
                (t("gs_rain", lang), "gs_rain", " mm"), (t("gs_et0", lang), "gs_et0", " mm")]
        md = f"| | {t('then', lang)} | {t('now', lang)} | Δ |\n|---|---:|---:|---:|\n"
        for label, k, u in rows:
            th_v, nw_v = S["then"][k], S["now"][k]
            if th_v is None or nw_v is None:
                continue
            md += f"| {label} | {th_v:.0f}{u} | **{nw_v:.0f}{u}** | {nw_v - th_v:+.0f} |\n"
        st.markdown(md)

# ------------------------------------------------------------------ 2. THEN vs NOW
with tab_then:
    st.subheader(climate_title)
    if shared:
        st.info("🛰️ " + t("shared_note", lang, fields=fields_str(cell_fields, lang)))
    else:
        st.caption("ℹ️ " + t("own_cell", lang))

    th, nw = S["then"], S["now"]

    def frost_delta(key):
        if th[key] is None or nw[key] is None:
            return None
        d = nw[key] - th[key]
        return f"{d:+.0f} {t('days', lang)} ({t('earlier' if d < 0 else 'later', lang).split()[-1]})"

    cols = st.columns(3) + st.columns(3)
    cols[0].metric(t("hot_days", lang), f"{nw['hot_days']:.0f}", f"{nw['hot_days'] - th['hot_days']:+.0f} {t('days', lang)}", delta_color="inverse")
    cols[1].metric(t("gdd10", lang), f"{nw['gdd10']:.0f}", f"{nw['gdd10'] - th['gdd10']:+.0f}")
    cols[2].metric(t("last_frost", lang), ldate(nw["last_spring_frost_date"], lang) or "–", frost_delta("last_spring_frost"),
                   delta_color="off")
    cols[3].metric(t("first_frost", lang), ldate(nw["first_autumn_frost_date"], lang) or "–", frost_delta("first_autumn_frost"),
                   delta_color="off")
    cols[4].metric(t("gs_rain", lang), f"{nw['gs_rain']:.0f} mm", f"{nw['gs_rain'] - th['gs_rain']:+.0f} mm")
    cols[5].metric(t("gs_et0", lang), f"{nw['gs_et0']:.0f} mm", f"{nw['gs_et0'] - th['gs_et0']:+.0f} mm", delta_color="inverse")
    st.caption(f"{t('then', lang)} → {t('now', lang)}")

    ann = pd.DataFrame(S["annual"])
    p_then, p_now = summary["periods"]["then"], summary["periods"]["now"]
    ann["period"] = np.where(ann["year"] <= p_then[1], "then", np.where(ann["year"] >= p_now[0], "now", "mid"))
    colmap = {"then": C_THEN, "now": C_NOW, "mid": C_MID}
    names = {"then": t("then", lang), "now": t("now", lang), "mid": "2006–2010"}

    c1, c2 = st.columns(2)
    with c1:  # hot days per year
        fig = go.Figure()
        for per in ["then", "mid", "now"]:
            sub = ann[ann["period"] == per]
            fig.add_bar(x=sub["year"], y=sub["hot_days"], name=names[per], marker_color=colmap[per],
                        marker_line_width=0, hovertemplate="%{x}: %{y} " + t("days", lang) + "<extra></extra>")
            if per != "mid":
                mean = S[per]["hot_days"]
                fig.add_shape(type="line", x0=sub["year"].min() - 0.4, x1=sub["year"].max() + 0.4, y0=mean, y1=mean,
                              line=dict(color=INK2, width=2, dash="dash"))
                fig.add_annotation(x=sub["year"].mean(), y=mean, text=f"{t('period_mean', lang)}: {mean:.0f}",
                                   showarrow=False, yshift=12, font=dict(color=INK2, size=11),
                                   bgcolor="rgba(255,255,255,0.8)")
        fig.update_traces(marker_cornerradius=4, selector=dict(type="bar"))
        st.plotly_chart(style(fig, t("chart_hot", lang), t("days", lang)), width="stretch")

    with c2:  # monthly Tmax
        mo = MONTHS[lang]
        fig = go.Figure()
        for per, c in [("then", C_THEN), ("now", C_NOW)]:
            fig.add_scatter(x=mo, y=S["monthly"][per]["T2M_MAX"], name=names[per], mode="lines+markers",
                            line=dict(color=c, width=2), marker=dict(size=8, line=dict(color="white", width=2)),
                            hovertemplate="%{y:.1f} °C<extra>" + names[per] + "</extra>")
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(style(fig, t("chart_tmax", lang), "°C"), width="stretch")

    c3, c4 = st.columns(2)
    with c3:  # monthly water demand vs rain
        fig = go.Figure()
        for per, c in [("then", C_THEN), ("now", C_NOW)]:
            fig.add_bar(x=mo, y=S["monthly"][per]["P"], name=t(f"rain_{per}", lang), marker_color=c,
                        opacity=0.45, marker_line_width=0, marker_cornerradius=4,
                        hovertemplate="%{y:.0f} mm<extra>" + t(f"rain_{per}", lang) + "</extra>")
        for per, c in [("then", C_THEN), ("now", C_NOW)]:
            fig.add_scatter(x=mo, y=S["monthly"][per]["ET0"], name=t(f"et0_{per}", lang), mode="lines+markers",
                            line=dict(color=c, width=2), marker=dict(size=8, line=dict(color="white", width=2)),
                            hovertemplate="%{y:.0f} mm<extra>" + t(f"et0_{per}", lang) + "</extra>")
        fig.update_layout(hovermode="x unified", barmode="group")
        st.plotly_chart(style(fig, t("chart_water", lang), "mm / " + t("month", lang).lower()),
                        width="stretch")

    with c4:  # frost-free window per year
        fr = ann.dropna(subset=["last_spring_frost", "first_autumn_frost"])
        fig = go.Figure()
        for per in ["then", "mid", "now"]:
            sub = fr[fr["period"] == per]
            base = pd.Timestamp("2001-01-01")
            fig.add_bar(x=sub["year"], base=sub["last_spring_frost"],
                        y=sub["first_autumn_frost"] - sub["last_spring_frost"],
                        name=names[per], marker_color=colmap[per], marker_line_width=0, marker_cornerradius=4,
                        customdata=np.stack([
                            [ldate((base + pd.Timedelta(days=int(v) - 1)).strftime("%d %b"), lang) for v in sub["last_spring_frost"]],
                            [ldate((base + pd.Timedelta(days=int(v) - 1)).strftime("%d %b"), lang) for v in sub["first_autumn_frost"]],
                            sub["frost_free_days"].astype(int)], axis=-1) if len(sub) else None,
                        hovertemplate="%{x}: %{customdata[0]} → %{customdata[1]} (%{customdata[2]} "
                                      + t("days", lang) + ")<extra></extra>")
        month_starts = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
        fig.update_yaxes(tickvals=month_starts, ticktext=MONTHS[lang], range=[50, 350])
        st.plotly_chart(style(fig, t("chart_frost", lang)), width="stretch")

# ------------------------------------------------------------------ 3. WATER STRESS
with tab_water:
    st.subheader(field_label(pid, lang))
    st.caption(t("water_intro", lang))
    st.caption("🔎 " + t("field_level_note", lang))
    water = load_water()
    wp = water[water["point"] == pid] if len(water) else water
    if wp.empty:
        st.info("🛰️ " + t("coming_soon", lang))
        with st.expander("How to add the data (for the team)"):
            st.markdown(
                "1. Upload `data/appeears_points.csv` to [NASA AppEEARS](https://appeears.earthdatacloud.nasa.gov/) → *Point Sample*.\n"
                "2. Layers: **SPL4SMGP** `sm_rootzone`, **ECOSTRESS** ESI (`ESI` / `ESIavg`), **HLSL30/HLSS30** `B04`,`B05`/`B8A` (or NDVI).\n"
                "3. Drop the result CSVs into `data/appeears/` and push — the app picks them up automatically.")
    else:
        units = {"sm": "m³/m³", "esi": "", "ndvi": ""}
        if (wp["var"] == "sm").any():
            st.caption("ℹ️ " + t("smap_note", lang))
        if wp["var"].isin(["esi", "etdaily"]).any():
            st.caption("ℹ️ " + t("ecostress_note", lang))
        if (wp["var"] == "ndvi").any():
            st.caption("ℹ️ " + t("hls_note", lang))
        for var in ["sm", "esi", "ndvi"]:
            v = wp[wp["var"] == var].sort_values("date")
            st.markdown(f"#### {t(var, lang)}")
            if v.empty:
                st.caption(t("no_data_layer", lang))
                continue
            last = v.iloc[-1]
            same_month = v[v["date"].dt.month == last["date"].month]
            pct = 100 * (same_month["value"] < last["value"]).mean()
            a, b = st.columns([1, 3])
            when = ldate(last["date"].strftime("%d %b %Y"), lang)
            a.metric(f"{t('latest', lang)} ({when})", f"{last['value']:.3f} {units[var]}")
            a.caption(t("pct_rank", lang, p=pct))
            fig = go.Figure(go.Scatter(x=v["date"], y=v["value"], mode="lines+markers",
                                       line=dict(color=C_THEN, width=2), marker=dict(size=5),
                                       hovertemplate=("%{x|%d %b %Y}" if lang == "en" else "%{x|%d.%m.%Y}")
                                       + ": %{y:.3f}<extra></extra>"))
            if lang != "en":
                fig.update_xaxes(tickformat="%m.%Y")
            b.plotly_chart(style(fig, t(var, lang), units[var], height=260), width="stretch")

# ------------------------------------------------------------------ 4. WHAT TO PLANT
with tab_plant:
    st.subheader(field_label(pid, lang))
    if shared:
        st.caption("ℹ️ " + t("plant_shared_note", lang, fields=fields_str(cell_fields, lang)))
    now, then = R["crops"]["now"], R["crops"]["then"]
    rank_now, rank_then = R["ranking"]["now"], R["ranking"]["then"]
    cot = now[BASELINE]["need_m3ha"]

    st.markdown(f"### {t('top3', lang)}")
    cards = st.columns(3)
    for i, key in enumerate(rank_now[:3]):
        c = now[key]
        with cards[i].container(border=True):
            st.markdown(f"#### {i + 1}. {CROP_NAMES[key]['icon']} {CROP_NAMES[key][lang]}")
            st.metric(t("water_need", lang), f"{c['need_m3ha']:,} m³/ha".replace(",", " "))
            saved = c["saved_vs_cotton_m3ha"]
            if saved >= 0:
                st.metric(t("saved", lang), f"{saved:,} m³/ha".replace(",", " "), f"-{100 * saved / cot:.0f}%",
                          delta_color="inverse")
            else:
                st.metric(t("more_than_cotton", lang), f"{-saved:,} m³/ha".replace(",", " "))
            hr = c["heat_risk"]
            st.markdown(f"{RISK_ICON[hr]} **{t('heat_risk', lang)}: {t(hr, lang)}** — "
                        + t("heat_detail", lang, d=c["heat_days"], t=c["heat_tmax"]))
            if c["p_frost"] > 0:
                st.markdown("❄️ " + t("frost_risk", lang, p=100 * c["p_frost"]))
            if c.get("winterkill_tmin") is not None:
                st.markdown(f"{'⚠️' if c['p_winterkill'] > 0 else '🟢'} " + t(
                    "winterkill_risk", lang, p=100 * c["p_winterkill"], tk=c["winterkill_tmin"]))
            if c["p_gdd_ok"] < 1:
                st.markdown("🌡️ " + t("gdd_short", lang, p=100 * (1 - c["p_gdd_ok"])))
            st.markdown(("✅ " + t("fits", lang)) if c["fits"] else ("⚠️ " + t("not_fits", lang)))
            st.caption(t("sow_harvest", lang, s=ldate(c["sow"], lang), h=ldate(c["harvest"], lang))
                       + f" · {t('then', lang)}: #{rank_then.index(key) + 1}")

    # water need of all crops
    order = sorted(rank_now, key=lambda k: -now[k]["need_m3ha"])  # plotly draws bottom-up: least water on top
    fig = go.Figure(go.Bar(
        y=[CROP_NAMES[k][lang] for k in order], x=[now[k]["need_m3ha"] for k in order], orientation="h",
        marker_color=[C_MID if k == BASELINE else C_THEN for k in order], marker_line_width=0,
        marker_cornerradius=4, text=[f"{now[k]['need_m3ha']:,}".replace(",", " ") for k in order],
        textposition="outside", textfont_color=INK2, cliponaxis=False,
        hovertemplate="%{y}: %{x:,} m³/ha<extra></extra>"))
    fig.add_vline(x=cot, line=dict(color=INK2, width=1, dash="dash"),
                  annotation_text=CROP_NAMES[BASELINE][lang], annotation_font_color=INK2,
                  annotation_position="bottom right")
    st.plotly_chart(style(fig, f"{t('water_need', lang)} — {t('now', lang)} (m³/ha)", height=360),
                    width="stretch")

    with st.expander(t("full_ranking", lang)):
        rows = []
        for i, k in enumerate(rank_now + ["mung_bean"]):
            c = now[k]
            rows.append({
                "#": str(i + 1) if k in rank_now else "2nd",
                t("crop", lang): f"{CROP_NAMES[k]['icon']} {CROP_NAMES[k][lang]}",
                t("fits", lang): "✅" if c["fits"] else "⚠️",
                f"{t('water_need', lang)} (m³/ha)": c["need_m3ha"],
                f"{t('then', lang)} (m³/ha)": then[k]["need_m3ha"],
                f"{t('saved', lang)} (m³/ha)": c["saved_vs_cotton_m3ha"],
                "ETc (mm)": c["etc_mm"], "Peff (mm)": c["peff_mm"], "Kc mid adj.": c["kc_mid_adj"],
                "GDD / min": f"{c['gdd']:.0f} / {c['min_gdd']:.0f} (base {c['gdd_base']:.0f})",
                t("heat_risk", lang): f"{RISK_ICON[c['heat_risk']]} {t(c['heat_risk'], lang)} ({c['heat_days']:.0f} d > {c['heat_tmax']:.0f} °C)",
                "Frost %": round(100 * c["p_frost"]),
                t("winterkill_col", lang): (round(100 * c["p_winterkill"]) if c.get("winterkill_tmin") is not None else None),
                t("score", lang): c["score"],
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    st.markdown(f"### 🔄 {t('rotations', lang)}")
    rc = st.columns(len(R["rotations"]))
    for col, r in zip(rc, R["rotations"]):
        with col.container(border=True):
            st.markdown(f"**{ROTATION_NAMES[r['key']][lang]}**")
            st.metric(f"{t('water_need', lang)}, {t('per_year', lang)}", f"{r['need_m3ha']:,} m³/ha".replace(",", " "),
                      f"{-r['saved_vs_cotton_m3ha']:+,} vs {CROP_NAMES[BASELINE][lang]}".replace(",", " "),
                      delta_color="inverse")
            st.markdown(f"{RISK_ICON[r['heat_risk']]} {t('heat_risk', lang)}: {t(r['heat_risk'], lang)} · "
                        + ("✅ " + t("fits", lang) if r["fits"] else "⚠️ " + t("not_fits", lang)))

    st.markdown(f"### 🌾 {t('wheat_shift', lang)}")
    ws = R["wheat_sowing"]
    best, conv, best_then = ws["now"]["best"], ws["now"]["conventional"], ws["then"]["best"]
    st.markdown(t("wheat_shift_text", lang, best=ldate(best["sow"], lang), conv=ldate(conv["sow"], lang),
                  h_conv=conv["heat_days"],
                  h_best=best["heat_days"], pw=best["prewinter_gdd"], pw_conv=conv["prewinter_gdd"],
                  r_conv=conv["risk"], r_best=best["risk"], best_then=ldate(best_then["sow"], lang)))
    fig = go.Figure()
    for per, c in [("then", C_THEN), ("now", C_NOW)]:
        tab = pd.DataFrame(ws[per]["table"])
        fig.add_scatter(x=[ldate(d, lang) for d in tab["sow"]], y=tab["risk"], name=names[per], mode="lines+markers",
                        line=dict(color=c, width=2), marker=dict(size=8, line=dict(color="white", width=2)),
                        customdata=np.stack([tab["heat_days"], tab["prewinter_gdd"]], axis=-1),
                        hovertemplate="%{x}: %{y:.1f} (heat %{customdata[0]:.0f} d, pre-winter %{customdata[1]:.0f} °C·d)"
                                      "<extra>" + names[per] + "</extra>")
        b = ws[per]["best"]
        fig.add_annotation(x=ldate(b["sow"], lang), y=b["risk"], text="★ " + ldate(b["sow"], lang),
                           showarrow=True, arrowcolor=c,
                           ay=-30, font=dict(color=INK, size=11), bgcolor="rgba(255,255,255,0.85)")
    fig.update_xaxes(title_text=t("sowing_date", lang), title_font_color=MUTED)
    st.plotly_chart(style(fig, t("wheat_chart", lang), t("risk_score", lang)), width="stretch")

    with st.expander("⚠️ " + t("limits", lang), expanded=True):
        st.markdown(t("limits_text", lang))

# ------------------------------------------------------------------ 5. FIVE-YEAR PLANNER
with tab_planner:
    planner_ui.render(lang, pid, planner_data)
