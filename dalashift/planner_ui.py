"""Streamlit UI for the 5-year planner tab. All numbers come from dalashift.planner."""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml
from plotly.subplots import make_subplots

from .i18n import CROP_NAMES, field_label, t
from .baseline import compare, evaluate_usual, water_deficit
from .planner import CONFIG, load_planner_config, plan_farm

# validated categorical slots 1-3 (blue, orange, aqua); comparison plan in neutral gray
PLAN_COLORS = {"profit": "#2a78d6", "balanced": "#eb6834", "water": "#1baf7a", "repeat_best": "#c3c2b7",
               "least_harm": "#898781"}
PLAN_KEYS = ["profit", "balanced", "water"]
RISK_ICON = {"low": "🟢", "medium": "🟠", "high": "🔴"}
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"


@st.cache_data(show_spinner=False)
def _demo_farms() -> dict:
    return yaml.safe_load((CONFIG / "demo_farms.yaml").read_text(encoding="utf-8"))


@st.cache_data(show_spinner="Checking every 5-year sequence…")
def _run(point_json: str, budget: float, rate: float, fresh: int, must_c: int, must_w: int) -> dict:
    import json
    return plan_farm(json.loads(point_json), budget, rate, fresh, {"cotton": must_c, "winter_wheat": must_w})


def option_name(key: str, lang: str, icons: bool = True) -> str:
    parts = key.split("+")
    return " → ".join((CROP_NAMES[c]["icon"] + " " if icons else "") + CROP_NAMES[c][lang] for c in parts)


def plan_name(kind: str, lang: str, res: dict | None = None) -> str:
    if kind == "repeat_best" and res and res.get("repeat_best"):
        return t("pl_plan_repeat", lang, crop=option_name(res["repeat_best"]["sequence"][0], lang, icons=False))
    return t(f"pl_plan_{kind}", lang)


def money_range(r: dict, lang: str) -> str:
    """'1,200 – 2,300 USD/ha' (estimate range; costs are placeholders)."""
    return f"{r['low']:,.0f} – {r['high']:,.0f} {t('pl_usd_ha', lang)}"


def _rules_text(rules, lang) -> str:
    return ", ".join(t(f"rule_{r}", lang) for r in rules) or t("pl_none", lang)


def _fail_reason(check: dict, budget: float, lang: str) -> str:
    parts = []
    for r in check["broken_rules"]:
        if r == "water":
            over = [y for y in check["years"] if y["water"] > budget + 1e-6]
            parts.append(t("pl_fail_water", lang, y=", ".join(str(y["year"]) for y in over),
                           n=max(y["water"] for y in over), b=budget))
        else:
            parts.append(t(f"rule_{r}", lang))
    return "; ".join(parts)


def _comparison_chart(res: dict, lang: str) -> go.Figure:
    plans = res["result"]["plans"]
    kinds = PLAN_KEYS + (["repeat_best"] if res.get("repeat_best") else [])
    get = lambda k: plans[k] if k in plans else res["repeat_best"]  # noqa: E731
    names = [plan_name(k, lang, res) for k in kinds]
    fig = make_subplots(rows=1, cols=3, shared_yaxes=True, horizontal_spacing=0.06,
                        subplot_titles=[f"{t('pl_npv', lang)} ({t('pl_usd_ha', lang)})",
                                        f"{t('pl_total_water', lang)} ({t('pl_m3_ha', lang)})",
                                        f"{t('pl_health', lang)} ({t('pl_points', lang)})"])
    for col, (metric, fmt) in enumerate([("npv", "{:,.0f}"), ("water_total", "{:,.0f}"), ("health", "{:.0f}")], 1):
        vals = [get(k)[metric] for k in kinds]
        fig.add_bar(y=names, x=vals, orientation="h", marker_color=[PLAN_COLORS[k] for k in kinds],
                    marker_line_width=0, marker_cornerradius=4, text=[fmt.format(v) for v in vals],
                    textposition="outside", textfont_color=INK2, cliponaxis=False, showlegend=False,
                    hovertemplate="%{y}: %{x:,.0f}<extra></extra>", row=1, col=col)
        top = max(max(vals), 1)
        fig.update_xaxes(range=[min(0, min(vals) * 1.3), (10.5 if metric == "health" else top * 1.35)], row=1, col=col)
    fig.update_layout(height=90 + 55 * len(kinds), margin=dict(l=10, r=20, t=50, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", bargap=0.3,
                      font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=INK2, size=12))
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=True, zerolinecolor=AXIS, tickfont_color=MUTED)
    fig.update_yaxes(autorange="reversed", tickfont_color=INK)
    fig.update_annotations(font_size=12, font_color=INK)
    return fig


def _year_card(y: dict, lang: str, rot: dict) -> None:
    st.markdown(f"**{t('pl_year', lang, y=y['year'])}**")
    st.markdown(f"#### {option_name(y['option'], lang)}")
    st.markdown(f"{t('pl_profit_y', lang).capitalize()} ({t('pl_estimate', lang)}): **{y['low']:,.0f} – {y['high']:,.0f}** "
                f"{t('pl_usd_ha', lang)}  \n💧 {y['water']:,.0f} {t('pl_m3_ha', lang)}")
    if y.get("check_number"):
        st.caption("⚠️ " + t("pl_check_number", lang))
    risk = f"{RISK_ICON[y['heat_risk']]} {t('heat_risk', lang)}: {t(y['heat_risk'], lang)}"
    if y["p_frost"] > 0 or y["p_winterkill"] > 0:
        risk += f" · ❄️ {100 * max(y['p_frost'], y['p_winterkill']):.0f}%"
    st.caption(risk)
    notes = []
    f = y["yield_factor"]
    if y["option"] == "alfalfa" and f < 1:
        notes.append(t("pl_est", lang))
    elif f > 1.001:
        notes.append(t("pl_bonus", lang, p=100 * (f - 1)))
    elif f < 0.999:
        notes.append(t("pl_penalty", lang, p=100 * (1 - f)))
    if y["legume"]:
        notes.append(t("pl_legume_tag", lang))
    if y.get("fresh"):
        notes.append(t("pl_fresh_tag", lang))
    for c, cap in (y.get("area_cap") or {}).items():
        notes.append(t("pl_area_tag", lang, p=100 * y["area_share"][c], k=cap))
    if notes:
        st.caption(" · ".join(notes))


def _plan_metrics(plan: dict, rb: dict | None, lang: str, rate: float) -> None:
    """Profit as an estimate RANGE (per year and 5-year total), water, health."""
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t("pl_profit_year_avg", lang), money_range(plan["profit_per_year_range"], lang))
    m2.metric(t("pl_profit_5y", lang), money_range(plan["profit_total_range"], lang),
              f"{plan['profit_total'] - rb['profit_total']:+,.0f} "
              f"{t('pl_vs_repeat', lang, crop=option_name(rb['sequence'][0], lang, False))}" if rb else None,
              help=t("pl_npv_help", lang, r=100 * rate, v=plan["npv"]))
    m3.metric(t("pl_total_water", lang), f"{plan['water_total']:,.0f} {t('pl_m3_ha', lang)}",
              f"{plan['water_total'] - rb['water_total']:+,.0f}" if rb else None, delta_color="inverse",
              help=t("pl_water_per_year", lang, w=plan["water_per_year"]))
    m4.metric(t("pl_health", lang), f"{plan['health']:.0f} / 10",
              f"{plan['health'] - rb['health']:+.0f}" if rb else None)
    st.caption("💵 " + t("pl_money_note", lang))
    if plan.get("check_number"):
        st.warning("⚠️ " + t("pl_check_plan", lang))


def _soft_note(plan: dict, lang: str) -> None:
    if "legume" in plan.get("soft_broken", []):
        st.info("🌱 " + t("pl_soft_legume", lang))


def render(lang: str, pid: str, planner_data: dict) -> None:
    cfg = load_planner_config()
    farms = _demo_farms()
    st.subheader("🗓️ " + t("pl_title", lang))
    st.caption(t("pl_intro", lang))

    choices = ["field"] + list(farms)
    labels = {"field": t("pl_farm_field", lang, name=field_label(pid, lang)),
              **{k: v["name"][lang] for k, v in farms.items()}}
    choice = st.radio(t("pl_farm", lang), choices, format_func=labels.get, horizontal=True, key="pl_farm")
    if choice == "field":
        point_id, d_budget, d_fresh, d_must = pid, cfg["default_water_budget_m3_ha"], cfg["max_fresh_market_years"], {}
        st.caption("ℹ️ " + t("pl_field_note", lang))
    else:
        f = farms[choice]
        point_id, d_budget, d_fresh, d_must = (f["point"], f["water_budget_m3_ha"], f["max_fresh_market_years"],
                                               f.get("must_grow_pct", {}))
        pt = planner_data["coords"][point_id]
        st.warning("🧪 " + t("pl_demo_note", lang, lat=pt[0], lon=pt[1], note=f["note"][lang]))

    corr = planner_data["points"][point_id].get("et0_correction")
    if corr:
        st.caption("💧 " + t("pl_et0_note", lang, f=corr["factor"],
                             label=t("pl_et0_ecostress" if corr["method"] == "ecostress" else "pl_et0_provisional", lang)))

    c1, c2, c3 = st.columns(3)
    budget = c1.number_input(t("pl_budget", lang), min_value=0, max_value=40000, value=int(d_budget), step=500,
                             key=f"pl_budget_{choice}")
    rate = c2.number_input(t("pl_rate", lang), min_value=0.0, max_value=40.0,
                           value=float(cfg["discount_rate"] * 100), step=1.0, key=f"pl_rate_{choice}") / 100
    fresh = c3.slider(t("pl_fresh", lang), 0, 5, int(d_fresh), help=t("pl_fresh_help", lang), key=f"pl_fresh_{choice}")
    must_on = st.toggle(t("pl_must", lang), value=any(d_must.values()), key=f"pl_must_{choice}")
    must_c = must_w = 0
    if must_on:
        m1, m2 = st.columns(2)
        pc = m1.select_slider(t("pl_must_cotton", lang), [0, 20, 40, 60, 80, 100],
                              value=int(d_must.get("cotton", 40) or 40), key=f"pl_mc_{choice}")
        pw = m2.select_slider(t("pl_must_wheat", lang), [0, 20, 40, 60, 80, 100],
                              value=int(d_must.get("winter_wheat", 40) or 40), key=f"pl_mw_{choice}")
        must_c, must_w = math.ceil(pc / 100 * 5 - 1e-9), math.ceil(pw / 100 * 5 - 1e-9)

    import json
    res = _run(json.dumps(planner_data["points"][point_id]), float(budget), float(rate), int(fresh), must_c, must_w)
    out = res["result"]
    opt_by_key = {o["key"]: o for o in res["options"]}

    # ------------------------------------------------------------ no plan meets every rule
    if out["status"] != "ok":
        st.error(t("pl_infeasible", lang))
        lh = out["plans"].get("least_harm")
        if lh:
            st.markdown(f"#### {t('pl_plan_least_harm', lang)}")
            st.warning("⚠️ " + t("pl_least_harm_breaks", lang, rules=_fail_reason(lh, budget, lang)))
            for y in lh["years"]:
                y["fresh"] = opt_by_key[y["option"]]["fresh"]
                y["area_cap"] = opt_by_key[y["option"]]["area_cap"]
                y["area_share"] = opt_by_key[y["option"]]["area_share"]
            cols = st.columns(5)
            for col, y in zip(cols, lh["years"]):
                with col.container(border=True):
                    _year_card(y, lang, opt_by_key)
            _plan_metrics(lh, None, lang, rate)
            _soft_note(lh, lang)
        ok_crops = [option_name(o["key"], lang) for o in res["options"] if o["fits"] and o["water"] <= budget]
        st.markdown(t("pl_inf_crops", lang, crops=", ".join(ok_crops) or t("pl_none", lang)))
        if out.get("blocking"):
            st.markdown(t("pl_inf_block", lang, rules=", ".join(
                f"{t(f'rule_{r}', lang)} {100 * v:.0f}%" for r, v in sorted(out["blocking"].items(), key=lambda x: -x[1]))))
        st.markdown(t("pl_relax", lang, rules=_rules_text(out["relax"], lang)) if out.get("relax")
                    else t("pl_relax_none", lang))
        _scenarios(res, lang, budget)
        return

    st.markdown(t("pl_checked", lang, n=out["n_sequences"], k=out["n_options"], f=out["n_feasible"]))
    plans = out["plans"]
    kind = st.radio(t("pl_plan", lang), PLAN_KEYS, format_func=lambda k: plan_name(k, lang), horizontal=True,
                    key="pl_kind")
    plan = plans[kind]
    for y in plan["years"]:
        y["fresh"] = opt_by_key[y["option"]]["fresh"]
        y["area_cap"] = opt_by_key[y["option"]]["area_cap"]
        y["area_share"] = opt_by_key[y["option"]]["area_share"]

    # timeline
    cols = st.columns(5)
    for col, y in zip(cols, plan["years"]):
        with col.container(border=True):
            _year_card(y, lang, opt_by_key)

    rb = res.get("repeat_best")
    _plan_metrics(plan, rb, lang, rate)
    usual = evaluate_usual(planner_data["points"][point_id]["baseline"], float(budget), float(rate), int(fresh))
    c = compare(plan, usual)
    deficit = water_deficit(usual, float(budget))
    st.caption("🔁 " + t("pl_vs_usual", lang, i=(f"{c['income_pct']:+.0f} %" if c["income_pct"] is not None else "–"),
                             w=f"{c['water_pct']:+.0f} %", d=(t("pl_usual_deficit", lang, n=deficit) if deficit > 0 else "")))
    _soft_note(plan, lang)

    # comparison
    st.markdown(f"#### {t('pl_compare', lang)}")
    st.plotly_chart(_comparison_chart(res, lang), width="stretch")

    # explanation
    left, right = st.columns(2)
    with left:
        st.markdown(f"#### {t('pl_why', lang)}")
        st.markdown(t(f"pl_why_{kind}", lang, f=out["n_feasible"]))
        cands = sorted([o for o in res["options"] if o["fits"] and o["water"] <= budget],
                       key=lambda o: -o["profit_1y"])
        rank = {o["key"]: i + 1 for i, o in enumerate(cands)}
        must = res["must_years"]
        for y in plan["years"]:
            extra = []
            if y["legume"]:
                extra.append(t("pl_legume_tag", lang))
            f = y["yield_factor"]
            if y["option"] == "alfalfa" and f < 1:
                extra.append(t("pl_est", lang))
            elif f > 1.001:
                extra.append(t("pl_bonus", lang, p=100 * (f - 1)))
            elif f < 0.999:
                extra.append(t("pl_penalty", lang, p=100 * (1 - f)))
            if (must.get("cotton") and "cotton" in y["crops"]) or (must.get("winter_wheat") and "winter_wheat" in y["crops"]):
                extra.append(t("pl_counts_must", lang))
            if y.get("check_number"):
                extra.append("⚠️ " + t("pl_check_short", lang))
            st.markdown("- " + t("pl_year_reason", lang, y=y["year"], crop=option_name(y["option"], lang),
                                 lo=y["low"], hi=y["high"], r=rank.get(y["option"], "–"), n=len(cands), w=y["water"],
                                 extra=("; " + "; ".join(extra)) if extra else ""))
    with right:
        st.markdown(f"#### {t('pl_why_not', lang)}")
        for w in res["why_not"][kind]:
            r = w["reason"]
            if r == "climate":
                parts = []
                for u in w.get("unfit", []):
                    if u["gdd_short"] > 0.2:
                        parts.append(t("gdd_short", lang, p=100 * u["gdd_short"]))
                    if u["frost"] > 0.2:
                        parts.append(t("frost_risk", lang, p=100 * u["frost"]))
                txt = t("pl_wn_climate", lang, d="; ".join(parts) or t("rule_climate", lang))
            elif r == "water":
                txt = t("pl_wn_water", lang, n=w["need"], b=w["budget"])
            elif r == "less_profit":
                txt = t("pl_wn_less_profit", lang, y=w["year"], d=-w["delta"])
            elif r == "worse_balance":
                txt = t("pl_wn_worse_balance", lang, y=w["year"], d=w["delta"], w=w["delta_water"])
            elif r == "more_water":
                txt = t("pl_wn_more_water", lang, y=w["year"], d=w["delta"])
            else:
                txt = t("pl_wn_rule", lang, r=t(f"rule_{w['rule']}", lang))
            st.markdown(f"- **{option_name(w['option'], lang)}**: {txt}")

    # cost of the must-grow obligation
    if res.get("constraint_cost"):
        st.markdown(f"#### {t('pl_constraint', lang)}")
        for k, c in res["constraint_cost"].items():
            if c["npv_cost"] is None:
                continue
            st.markdown("- " + t("pl_constraint_row", lang, plan=plan_name(k, lang), d=c["npv_cost"], w=c["water_change"],
                                 seq=" → ".join(option_name(s, lang, False) for s in c["free_sequence"])))

    _scenarios(res, lang, budget)


def _scenarios(res: dict, lang: str, budget: float) -> None:
    st.markdown(f"#### 🌡️ {t('pl_scen', lang)}")
    scen = res["scenarios"]
    names = {s: t(f"scen_{s}", lang) for s in scen}
    plans = res["result"]["plans"]
    if plans:
        rows = []
        for k in [k for k in PLAN_KEYS + ["least_harm"] if k in plans]:
            row = {t("pl_plan", lang): plan_name(k, lang)}
            for s, sc in scen.items():
                c = sc["checks"][k]
                row[names[s]] = (f"{t('pl_ok', lang)} · {money_range(c['profit_total_range'], lang)}" if c["feasible"]
                                 else f"{t('pl_fail', lang)}: {_fail_reason(c, sc['budget'], lang)}")
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    with st.expander(t("pl_reopt", lang), expanded=not plans):
        for s, sc in scen.items():
            r = sc["reoptimized"]
            st.markdown(f"**{names[s]}** — {sc['budget']:,.0f} {t('pl_m3_ha', lang)}")
            if r["status"] != "ok":
                st.markdown("- " + t("pl_infeasible", lang))
                lh = r["plans"].get("least_harm")
                if lh:
                    st.markdown(f"- {plan_name('least_harm', lang)}: "
                                + " → ".join(option_name(x, lang, False) for x in lh["sequence"])
                                + f" · {money_range(lh['profit_total_range'], lang)}"
                                + f" · {lh['water_total']:,.0f} {t('pl_m3_ha', lang)} · "
                                + t("pl_breaks", lang, rules=_fail_reason(lh, sc["budget"], lang)))
                continue
            for k in PLAN_KEYS:
                p = r["plans"][k]
                st.markdown(f"- {plan_name(k, lang)}: " + " → ".join(option_name(x, lang, False) for x in p["sequence"])
                            + f" · {money_range(p['profit_total_range'], lang)} · {p['water_total']:,.0f} {t('pl_m3_ha', lang)}"
                            + f" · {p['health']:.0f}/10")
    with st.expander("⚠️ " + t("limits", lang)):
        st.markdown(t("pl_limits_text", lang))
