"""Tests for the 5-year planner.

The rule checks below are an INDEPENDENT plain-Python implementation of
config/rotation_rules.yaml (not the vectorised numpy code in dalashift/planner.py),
so a bug in the optimizer cannot hide behind the same bug in the test.

Run:  python -m pytest -q
"""
from __future__ import annotations

import itertools
import json
import math
import re
from pathlib import Path

import pandas as pd
import pytest
import yaml

from dalashift.crops import load_crop_table
from dalashift.planner import (load_planner_config, load_rules, make_context, optimize, plan_farm,
                               repeat_best_crop)

ROOT = Path(__file__).resolve().parents[1]
PLANNER = json.loads((ROOT / "data" / "planner.json").read_text())
POINTS = sorted(PLANNER["points"])
TABLE = load_crop_table()
RULES = load_rules()
CFG = load_planner_config()
FARMS = yaml.safe_load((ROOT / "config" / "demo_farms.yaml").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ independent rule checker
def check_plan(seq: list[str], metrics: dict, budget: float, fresh_cap: int, must: dict) -> list[str]:
    """Return the list of broken rules for a plan given as option keys like 'winter_wheat+mung_bean'."""
    hr = RULES["hard_rules"]
    years = [k.split("+") for k in seq]
    broken = []
    allowed_doubles = {tuple(p) for p in hr["double_crops"]}
    for crops in years:
        if len(crops) > 1 and tuple(crops) not in allowed_doubles:
            broken.append("double_crop")
        for c in crops:
            if TABLE.loc[c, "role"] == "second_crop" and len(crops) == 1:
                broken.append("second_crop_alone")
    if not all(metrics[c]["fits"] for crops in years for c in crops):
        broken.append("climate")
    if any(sum(metrics[c]["need_m3ha"] for c in crops) > budget + 1e-6 for crops in years):
        broken.append("water")
    run = 0
    for crops in years:
        run = run + 1 if "cotton" in crops else 0
        if run > hr["max_consecutive_cotton_years"]:
            broken.append("cotton_run")
            break
    exempt = set(hr["family_rule_exempt"])
    fams = [{TABLE.loc[c, "family"] for c in crops if c not in exempt} for crops in years]
    k = hr["max_same_family_run_years"] + 1
    for i in range(len(years) - k + 1):
        if set.intersection(*fams[i:i + k]):
            broken.append("family_run")
            break
    stand = hr["multi_year_crops"]["alfalfa"]
    alf = [crops == ["alfalfa"] for crops in years]
    i = 0
    while i < len(alf):
        if alf[i]:
            j = i
            while j < len(alf) and alf[j]:
                j += 1
            length, ends_at_horizon = j - i, j == len(alf)
            if length > stand["max_years"] or (length < stand["min_years"] and not ends_at_horizon):
                broken.append("alfalfa_stand")
            i = j
        else:
            i += 1
    fresh = sum(any(str(TABLE.loc[c, "local_market_tag"]).startswith("fresh") for c in crops) for crops in years)
    if fresh > fresh_cap:
        broken.append("market")
    for c in TABLE.index:
        cap = math.floor(float(TABLE.loc[c, "max_area_share"]) * 5 + 1e-9)
        if sum(c in crops for crops in years) > cap:
            broken.append("area")
            break
    if sum("cotton" in crops for crops in years) < must.get("cotton", 0):
        broken.append("must_cotton")
    if sum("winter_wheat" in crops for crops in years) < must.get("winter_wheat", 0):
        broken.append("must_wheat")
    return broken


CASES = [(p, b, m) for p in POINTS for b in (6000, 9000, 12000)
         for m in ({}, {"cotton": 2}, {"winter_wheat": 2}, {"cotton": 1, "winter_wheat": 2})]


@pytest.mark.parametrize("point,budget,must", CASES)
def test_every_returned_plan_obeys_all_rules_and_budget(point, budget, must):
    metrics = PLANNER["points"][point]["baseline"]
    res = optimize(make_context(metrics, budget, must_years=must))
    if res["status"] != "ok":
        _assert_least_harm(res, metrics, budget, must)
        return
    assert set(res["plans"]) == {"profit", "balanced", "water"}
    for plan in res["plans"].values():
        assert len(plan["sequence"]) == 5
        assert check_plan(plan["sequence"], metrics, budget, CFG["max_fresh_market_years"], must) == []
        assert all(y["water"] <= budget + 1e-6 for y in plan["years"])
        assert 0 <= plan["health"] <= 10


@pytest.mark.parametrize("point,budget,must", CASES[::7])
def test_plans_are_optimal_for_their_objective(point, budget, must):
    """No feasible sequence beats 'Most profit' on NPV or 'Least water' on water."""
    metrics = PLANNER["points"][point]["baseline"]
    ctx = make_context(metrics, budget, must_years=must)
    res = optimize(ctx)
    if res["status"] != "ok":
        return
    from dalashift.planner import enumerate_sequences, evaluate
    cands = [i for i, o in enumerate(ctx.options) if o.fits and o.water <= budget]
    ev = evaluate(enumerate_sequences(cands), ctx)
    f = ev["feasible"]
    assert res["plans"]["profit"]["npv"] == pytest.approx(ev["npv"][f].max())
    assert res["plans"]["water"]["water_total"] == pytest.approx(ev["water"][f].min())


# ------------------------------------------------------------------ no feasible plan -> least-harmful plan, clearly marked
def _assert_least_harm(res, metrics, budget, must):
    assert res["status"] == "relaxed" and set(res["plans"]) == {"least_harm"}
    plan = res["plans"]["least_harm"]
    assert plan["feasible"] is False and plan["broken_rules"]
    assert sorted(plan["broken_rules"]) == sorted(check_plan(plan["sequence"], metrics, budget,
                                                             CFG["max_fresh_market_years"], must))
    return plan


def test_no_water_gives_least_harmful_plan():
    metrics = PLANNER["points"]["Fergana_field1"]["baseline"]
    res = optimize(make_context(metrics, budget=100))
    plan = _assert_least_harm(res, metrics, 100, {})
    assert plan["broken_rules"] == ["water"]        # only the budget is broken, every rotation rule still holds


def test_legume_is_a_soft_rule():
    """No legume can be grown (all legumes made climate-unfit here). That is a soft penalty: a feasible
    plan is still returned, with lower rotation health and the rule listed."""
    metrics = {k: dict(v) for k, v in PLANNER["points"]["Fergana_field1"]["baseline"].items()}
    for c in ("chickpea", "mung_bean", "alfalfa"):
        metrics[c]["fits"] = False
    res = optimize(make_context(metrics, 12000))
    assert res["status"] == "ok"
    for plan in res["plans"].values():
        assert "legume" in plan["soft_broken"] and "legume" not in plan["broken_rules"]
        assert plan["health"] <= 10 - RULES["health_score"]["no_legume_year"]


def test_impossible_obligation_gives_least_harmful_plan():
    """Cotton in 5 of 5 years contradicts 'max 2 cotton years in a row'."""
    metrics = PLANNER["points"]["Fergana_field1"]["baseline"]
    res = optimize(make_context(metrics, 20000, must_years={"cotton": 5}))
    plan = _assert_least_harm(res, metrics, 20000, {"cotton": 5})
    assert len(plan["broken_rules"]) == 1           # breaks exactly one rule (the run limit or the obligation)
    assert "cotton_run" in res["relax"] or "must_cotton" in res["relax"]


def test_brute_force_matches_naive_enumeration():
    """Small case: compare against a naive itertools enumeration + the independent rule checker."""
    farm = FARMS["karshi"]
    metrics = PLANNER["points"][farm["point"]]["baseline"]
    budget = farm["water_budget_m3_ha"]
    ctx = make_context(metrics, budget)
    res = optimize(ctx)
    cands = [o.key for o in ctx.options if o.fits and o.water <= budget]
    naive_feasible = [s for s in itertools.product(cands, repeat=5)
                      if not check_plan(list(s), metrics, budget, CFG["max_fresh_market_years"], {})]
    assert res["n_feasible"] == len(naive_feasible)
    assert tuple(res["plans"]["profit"]["sequence"]) in set(naive_feasible)


# ------------------------------------------------------------------ beats "repeat the most profitable crop"
@pytest.mark.parametrize("point", POINTS)
@pytest.mark.parametrize("budget", [7000, 12000])
def test_optimizer_beats_repeating_the_most_profitable_crop(point, budget):
    ctx = make_context(PLANNER["points"][point]["baseline"], budget)
    res = optimize(ctx)
    base = repeat_best_crop(ctx)
    if res["status"] != "ok" or base is None:
        pytest.skip("no feasible plan / nothing to repeat")
    best = res["plans"]["profit"]
    assert best["npv"] > base["npv"]                     # discounted 5-year total
    assert best["profit_total"] > base["profit_total"]   # undiscounted 5-year total
    assert best["health"] >= base["health"]


# ------------------------------------------------------------------ scenarios and demo farms
@pytest.mark.parametrize("farm", list(FARMS))
def test_demo_farms_run_and_scenarios_recheck_baseline_plans(farm):
    f = FARMS[farm]
    budget = f["water_budget_m3_ha"]
    res = plan_farm(PLANNER["points"][f["point"]], budget, CFG["discount_rate"], f["max_fresh_market_years"], {})
    assert res["result"]["status"] == "ok"
    for s, sc in res["scenarios"].items():
        assert sc["budget"] == pytest.approx(budget * CFG["scenarios"][s]["water_factor"])
        for kind, check in sc["checks"].items():
            assert check["sequence"] == res["result"]["plans"][kind]["sequence"]
            metrics = PLANNER["points"][f["point"]]["hotter" if CFG["scenarios"][s]["delta_t_c"] > 0 else "baseline"]
            assert check["feasible"] == (check_plan(check["sequence"], metrics, sc["budget"],
                                                    f["max_fresh_market_years"], {}) == [])


def test_demo_farms_get_different_plans():
    seqs = {k: plan_farm(PLANNER["points"][f["point"]], f["water_budget_m3_ha"], 0.1, 2, {})["result"]["plans"]["profit"]["sequence"]
            for k, f in FARMS.items()}
    assert seqs["fergana"] != seqs["karshi"]


def test_demo_is_karshi_vs_fergana():
    assert set(FARMS) == {"karshi", "fergana"}
    assert FARMS["karshi"]["point"] == "Karshi_field1"
    assert 7000 <= FARMS["karshi"]["water_budget_m3_ha"] <= 9000


def test_must_grow_cost_is_reported_and_non_negative_for_profit_plan():
    res = plan_farm(PLANNER["points"]["Fergana_field1"], 12000, 0.1, 2, {"cotton": 2})
    cost = res["constraint_cost"]["profit"]["npv_cost"]
    assert cost is not None and cost >= -1e-6


# ------------------------------------------------------------------ crop database provenance
def test_crop_database_labels_and_faostat_values():
    df = pd.read_csv(ROOT / "config" / "crops.csv")
    expected = {"cotton", "winter_wheat", "barley", "maize", "rice", "sorghum", "sunflower", "mung_bean",
                "chickpea", "potato", "onion", "tomato", "melon", "alfalfa"}
    assert set(df["crop"]) == expected
    for col in [c for c in df.columns if c.endswith("_status")]:
        assert set(df[col]) <= {"documented", "approximate"}, col
        src = col.replace("_status", "_source")
        assert df[src].notna().all() and (df[src].astype(str).str.len() > 3).all(), src
    assert (df["cost_status"] == "approximate").all()   # no published cost source -> must say so
    prices = pd.read_csv(ROOT / "data" / "faostat" / "uz_producer_prices.csv")
    yields = pd.read_csv(ROOT / "data" / "faostat" / "uz_yields.csv")
    p = prices[prices["Year"].between(2023, 2024)].groupby("Item")["Value"].mean()
    y = yields[yields["Year"].between(2022, 2024)].groupby("Item")["Value"].mean() / 1000
    for r in df.itertuples():
        if r.price_status == "documented":
            item = re.search(r"\d{4}-\d{4} \((.*)\); accessed", r.price_source).group(1)
            assert math.isclose(r.price_usd_t, p[item], abs_tol=0.06), r.crop
        if r.yield_status == "documented":
            item = re.search(r"\d{4}-\d{4} \((.*)\); accessed", r.yield_source).group(1)
            assert math.isclose(r.yield_t_ha, y[item], abs_tol=0.006), r.crop


# ------------------------------------------------------------------ money realism
def test_profit_is_a_range_with_per_year_value_and_check_flag():
    f = FARMS["fergana"]
    res = plan_farm(PLANNER["points"][f["point"]], f["water_budget_m3_ha"], 0.1, 2, {})
    u, check = CFG["money"]["profit_uncertainty"], CFG["money"]["margin_check_usd_ha"]
    for plan in res["result"]["plans"].values():
        r = plan["profit_total_range"]
        assert r["low"] == pytest.approx(plan["profit_total"] * (1 - u))
        assert r["high"] == pytest.approx(plan["profit_total"] * (1 + u))
        assert plan["profit_per_year"] == pytest.approx(plan["profit_total"] / 5)
        for y in plan["years"]:
            assert y["low"] <= y["profit"] <= y["high"]
            assert y["check_number"] == (y["profit"] > check)


@pytest.mark.parametrize("point", POINTS)
def test_fresh_market_crops_limited_to_25_percent_of_area(point):
    res = optimize(make_context(PLANNER["points"][point]["baseline"], 15000, max_fresh_years=5))
    for plan in res["plans"].values():
        for c in ("tomato", "potato", "onion", "melon"):
            assert sum(c in k.split("+") for k in plan["sequence"]) <= 1   # 1 of 5 years = 20 % <= 25 %
