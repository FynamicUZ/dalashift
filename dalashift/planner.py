"""5-year crop rotation planner - transparent brute-force optimizer.

How it works
------------
1. Year options for a field = every crop that passes the existing Climate Fit test (GDD + frost
   window, FAO-56 engine) plus allowed double crops (winter wheat -> mung bean).
2. ALL 5-year sequences of those options are enumerated (at most 14^5 = 537,824), as numpy arrays.
3. A sequence is FEASIBLE only if it obeys every hard rule (config/rotation_rules.yaml), the water
   budget in every year, the fresh-market limit, each crop's maximum share of farm area and any
   "must grow" minimum. "Legume at least once in 5 years" is a SOFT rule: missing it costs rotation-
   health points (and the after-legume yield bonus) but never rejects a plan.
4. Each feasible sequence gets:
     discounted profit  NPV = sum_t profit_t / (1 + r)^t,  t = 1..5
     profit_t           = yield x climate factor x rotation effect x price - cost      (USD/ha)
     water              = sum_t net irrigation need_t (FAO-56, m3/ha)
     rotation health    = 0-10 points from the rules
5. Three plans are returned: "Most profit" (max NPV), "Least water" (min water, then max NPV) and
   "Balanced" (max of normalised NPV + normalised water saving + health/10, equal weights).
If no sequence is feasible the planner returns the LEAST-HARMFUL plan instead (fewest broken hard
rules, then least water over budget, then most profit), clearly marked, with the rules it breaks.

Area share: the farm is assumed to run the 5-year plan on 5 equal blocks, each one year behind the
next (standard rotation practice), so a crop grown k of 5 years covers k/5 of the farm every year.
A crop with max_area_share s may therefore appear at most floor(5 s) years (25 % -> 1 year).
Money: costs are placeholders, so profits are reported as an estimate range (config/planner.yaml).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .crops import load_crop_table

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
T = 5  # horizon (years)

RULE_KEYS = ["climate", "water", "cotton_run", "family_run", "alfalfa_stand",
             "market", "area", "must_cotton", "must_wheat"]          # HARD rules
SOFT_RULES = ["legume"]                                             # health penalty only
AGRONOMIC_RULES = ["cotton_run", "family_run", "alfalfa_stand"]


def load_rules(path: Path = CONFIG / "rotation_rules.yaml") -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_planner_config(path: Path = CONFIG / "planner.yaml") -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ year options
@dataclass
class Option:
    key: str
    crops: tuple[str, ...]
    fits: bool
    water: float              # net irrigation need, m3/ha/year (sum for double crops)
    revenue: float            # expected revenue before rotation effects, USD/ha
    cost: float               # USD/ha
    family_bits: int          # all families present this year (for diversity)
    family_rule_bits: int     # families counted by the "no same family 3 years" rule
    legume: bool              # any legume this year
    main_legume: bool         # the first (main) crop is a legume
    cotton: bool
    wheat: bool
    alfalfa: bool
    fresh: bool
    heat_risk: str
    p_frost: float
    p_winterkill: float
    climate_factor: float
    area_cap: dict = field(default_factory=dict)  # {crop: max years of 5} for crops with max_area_share < 1
    unfit_reason: str = ""
    unfit: list = field(default_factory=list)   # structured: [{crop, gdd_short, frost}] for the UI


def climate_factor(m: dict, losses: dict) -> float:
    """APPROXIMATE expected-yield factor from the engine's climate risks (config/planner.yaml)."""
    f = 1 - losses["heat_risk"][m["heat_risk"]]
    f *= 1 - losses["frost_loss_when_hit"] * m["p_frost"]
    f *= 1 - losses["winterkill_loss_when_hit"] * (m.get("p_winterkill") or 0)
    f *= 1 - losses["gdd_shortfall_loss"] * (1 - m["p_gdd_ok"])
    return f


def unfit_reason(m: dict) -> str:
    reasons = []
    if m["p_gdd_ok"] < 0.8:
        reasons.append(f"not enough heat in {100 * (1 - m['p_gdd_ok']):.0f}% of years")
    if m["p_frost"] > 0.2:
        reasons.append(f"frost in {100 * m['p_frost']:.0f}% of years")
    return "; ".join(reasons) or "climate fit"


def build_options(metrics: dict, table: pd.DataFrame, rules: dict, cfg: dict) -> list[Option]:
    """All candidate year options (fit or not - unfit ones are kept so plans can be re-checked)."""
    fams = sorted(table["family"].unique())
    bit = {f: 1 << i for i, f in enumerate(fams)}
    exempt = set(rules["hard_rules"].get("family_rule_exempt", []))
    losses = cfg["climate_yield_losses"]
    # crops with planner_enabled = False (config/crops.csv, e.g. melon) are kept for reference only
    enabled = {c for c in table.index if str(table.loc[c, "planner_enabled"]).strip().lower() != "false"}
    groups = [(c,) for c in table.index if table.loc[c, "role"] != "second_crop" and c in enabled]
    groups += [tuple(pair) for pair in rules["hard_rules"].get("double_crops", []) if set(pair) <= enabled]
    opts = []
    for crops in groups:
        rows = [table.loc[c] for c in crops]
        ms = [metrics[c] for c in crops]
        cf = [climate_factor(m, losses) for m in ms]
        risk_order = ["low", "medium", "high"]
        opts.append(Option(
            key="+".join(crops), crops=crops,
            fits=all(m["fits"] for m in ms),
            water=float(sum(m["need_m3ha"] for m in ms)),
            revenue=float(sum(r["yield_t_ha"] * r["price_usd_t"] * f
                              * (cfg.get("yield_realism_factor", 1.0)
                                 if r["crop"] in cfg.get("yield_realism_crops", []) else 1.0)
                              for r, f in zip(rows, cf))),
            cost=float(sum(r["cost_usd_ha"] for r in rows)),
            family_bits=int(np.bitwise_or.reduce([bit[r["family"]] for r in rows])),
            family_rule_bits=int(np.bitwise_or.reduce([0 if c in exempt else bit[r["family"]]
                                                       for c, r in zip(crops, rows)])),
            legume=any(bool(r["legume"]) for r in rows), main_legume=bool(rows[0]["legume"]),
            cotton="cotton" in crops, wheat="winter_wheat" in crops, alfalfa=crops == ("alfalfa",),
            fresh=any(str(r["local_market_tag"]).startswith("fresh") for r in rows),
            heat_risk=max((m["heat_risk"] for m in ms), key=risk_order.index),
            p_frost=max(m["p_frost"] for m in ms), p_winterkill=max((m.get("p_winterkill") or 0) for m in ms),
            climate_factor=float(np.prod(cf)),
            area_cap={c: int(np.floor(float(r["max_area_share"]) * T + 1e-9)) for c, r in zip(crops, rows)
                      if float(r["max_area_share"]) < 1},
            unfit_reason="; ".join(f"{c}: {unfit_reason(m)}" for c, m in zip(crops, ms) if not m["fits"]),
            unfit=[{"crop": c, "gdd_short": 1 - m["p_gdd_ok"], "frost": m["p_frost"]}
                   for c, m in zip(crops, ms) if not m["fits"]],
        ))
    return opts


# ------------------------------------------------------------------ context
@dataclass
class Context:
    options: list[Option]
    rules: dict
    cfg: dict
    budget: float
    discount_rate: float
    max_fresh_years: int
    must_years: dict = field(default_factory=dict)   # {"cotton": k, "winter_wheat": k}
    arr: dict = field(default_factory=dict)

    def __post_init__(self):
        o = self.options
        self.arr = {
            "water": np.array([x.water for x in o]), "revenue": np.array([x.revenue for x in o]),
            "cost": np.array([x.cost for x in o]), "fits": np.array([x.fits for x in o]),
            "fam": np.array([x.family_bits for x in o], dtype=np.int64),
            "fam_rule": np.array([x.family_rule_bits for x in o], dtype=np.int64),
            "legume": np.array([x.legume for x in o]), "main_legume": np.array([x.main_legume for x in o]),
            "cotton": np.array([x.cotton for x in o]), "wheat": np.array([x.wheat for x in o]),
            "alfalfa": np.array([x.alfalfa for x in o]), "fresh": np.array([x.fresh for x in o]),
        }
        self.index = {x.key: i for i, x in enumerate(o)}
        self.area_caps = {c: cap for x in o for c, cap in x.area_cap.items()}
        self.arr["area"] = {c: np.array([c in x.crops for x in o]) for c in self.area_caps}


def make_context(metrics: dict, budget: float, discount_rate: float | None = None,
                 max_fresh_years: int | None = None, must_years: dict | None = None,
                 table: pd.DataFrame | None = None, rules: dict | None = None, cfg: dict | None = None) -> Context:
    table = load_crop_table() if table is None else table
    rules = load_rules() if rules is None else rules
    cfg = load_planner_config() if cfg is None else cfg
    return Context(build_options(metrics, table, rules, cfg), rules, cfg, float(budget),
                   cfg["discount_rate"] if discount_rate is None else float(discount_rate),
                   cfg["max_fresh_market_years"] if max_fresh_years is None else int(max_fresh_years),
                   must_years or {})


# ------------------------------------------------------------------ vectorised evaluation
def _run_lengths(b: np.ndarray) -> np.ndarray:
    run = np.zeros(b.shape, dtype=np.int16)
    run[:, 0] = b[:, 0]
    for i in range(1, b.shape[1]):
        run[:, i] = np.where(b[:, i], run[:, i - 1] + 1, 0)
    return run


def evaluate(seq: np.ndarray, ctx: Context) -> dict:
    """Evaluate (N, 5) arrays of option indices. Returns rule violations, profit, water, health."""
    a, hr, h = ctx.arr, ctx.rules["hard_rules"], ctx.rules["health_score"]
    eff = ctx.rules["rotation_effects"]
    n, t = seq.shape
    water_y = a["water"][seq]
    cot, alf, leg = a["cotton"][seq], a["alfalfa"][seq], a["legume"][seq]

    v = {}
    v["climate"] = ~a["fits"][seq].all(1)
    v["water"] = (water_y > ctx.budget + 1e-6).any(1)
    v["cotton_run"] = _run_lengths(cot).max(1) > hr["max_consecutive_cotton_years"]
    k = hr["max_same_family_run_years"] + 1
    fam = a["fam_rule"][seq]
    win = fam[:, 0:t - k + 1].copy()
    for j in range(1, k):
        win &= fam[:, j:t - k + 1 + j]
    v["family_run"] = (win != 0).any(1)
    stand = hr["multi_year_crops"]["alfalfa"]
    run = _run_lengths(alf)
    ends = alf & np.concatenate([~alf[:, 1:], np.ones((n, 1), bool)], axis=1)
    last_col = np.zeros(t, bool)
    last_col[-1] = stand.get("may_continue_after_horizon", True)
    short = ends & (run < stand["min_years"]) & ~last_col
    v["alfalfa_stand"] = short.any(1) | (run.max(1) > stand["max_years"])
    v["market"] = a["fresh"][seq].sum(1) > ctx.max_fresh_years
    v["area"] = np.zeros(n, bool)
    for c, cap in ctx.area_caps.items():
        v["area"] |= a["area"][c][seq].sum(1) > cap
    v["must_cotton"] = cot.sum(1) < ctx.must_years.get("cotton", 0)
    v["must_wheat"] = a["wheat"][seq].sum(1) < ctx.must_years.get("winter_wheat", 0)
    feasible = ~np.any(np.stack([v[r] for r in RULE_KEYS]), axis=0)
    no_legume = leg.sum(1) < ctx.rules["soft_rules"]["min_legume_years"]
    v["legume"] = no_legume            # SOFT: reported and penalised, never makes a plan infeasible

    # rotation effects on yield
    same = np.zeros((n, t), bool)
    same[:, 1:] = (seq[:, 1:] == seq[:, :-1]) & ~alf[:, 1:]
    rep = _run_lengths(same)
    mult = 1 - np.minimum(eff["same_crop_repeat_penalty_per_year"] * rep, eff["same_crop_repeat_penalty_max"])
    prev_alf = np.zeros((n, t), bool)
    prev_alf[:, 1:] = alf[:, :-1]
    prev_leg = np.zeros((n, t), bool)
    prev_leg[:, 1:] = leg[:, :-1]
    bonus = np.where(prev_alf & ~alf, 1 + eff["after_alfalfa_bonus"],
                     np.where(prev_leg & ~a["main_legume"][seq], 1 + eff["after_legume_bonus"], 1.0))
    est = np.where(alf & ~prev_alf, eff["alfalfa_establishment_yield_factor"], 1.0)
    factor = mult * bonus * est
    profit_y = a["revenue"][seq] * factor - a["cost"][seq]
    disc = 1 / (1 + ctx.discount_rate) ** np.arange(1, t + 1)
    npv = profit_y @ disc

    # rotation health 0-10
    n_fam = np.bitwise_count(np.bitwise_or.reduce(a["fam"][seq], axis=1))
    broken = sum(v[r].astype(int) for r in AGRONOMIC_RULES)
    health = (h["start"] - h["per_same_crop_next_year"] * same.sum(1)
              - h["only_one_legume_year"] * (leg.sum(1) == 1) - h["no_legume_year"] * no_legume
              - h["fewer_than_4_families"] * (n_fam < 4) - h["fewer_than_3_families"] * (n_fam < 3)
              - h["per_broken_hard_rule"] * broken)
    n_broken = np.sum(np.stack([v[r] for r in RULE_KEYS]), axis=0)
    excess = np.maximum(water_y - ctx.budget, 0).sum(1)
    return {"violations": v, "feasible": feasible, "n_broken": n_broken, "water_excess": excess, "npv": npv, "profit_y": profit_y,
            "water_y": water_y, "water": water_y.sum(1), "health": np.clip(health, 0, 10),
            "yield_factor": factor, "n_families": n_fam}


# ------------------------------------------------------------------ optimizer
def _plan_dict(i: int, seq: np.ndarray, ev: dict, ctx: Context, kind: str) -> dict:
    keys = [ctx.options[j].key for j in seq[i]]
    years = []
    for y, j in enumerate(seq[i]):
        o = ctx.options[j]
        years.append({"year": y + 1, "option": o.key, "crops": list(o.crops),
                      "profit": float(ev["profit_y"][i, y]), "water": float(ev["water_y"][i, y]),
                      "yield_factor": float(ev["yield_factor"][i, y]), "heat_risk": o.heat_risk,
                      "p_frost": o.p_frost, "p_winterkill": o.p_winterkill, "legume": o.legume,
                      "climate_factor": o.climate_factor})
    broken = [r for r in RULE_KEYS if ev["violations"][r][i]]
    soft = [r for r in SOFT_RULES if ev["violations"][r][i]]
    money = ctx.cfg["money"]
    for y in years:
        y.update(profit_low_high(y["profit"], money["profit_uncertainty"]))
        y["check_number"] = y["profit"] > money["margin_check_usd_ha"]
    total = float(ev["profit_y"][i].sum())
    return {"kind": kind, "sequence": keys, "years": years, "npv": float(ev["npv"][i]),
            "npv_range": profit_low_high(float(ev["npv"][i]), money["profit_uncertainty"]),
            "profit_total": total, "profit_total_range": profit_low_high(total, money["profit_uncertainty"]),
            "profit_per_year": total / T, "profit_per_year_range": profit_low_high(total / T, money["profit_uncertainty"]),
            "water_total": float(ev["water"][i]), "water_per_year": float(ev["water"][i]) / T,
            "health": float(ev["health"][i]), "feasible": bool(ev["feasible"][i]), "broken_rules": broken,
            "soft_broken": soft, "water_excess": float(ev["water_excess"][i]),
            "check_number": any(y["check_number"] for y in years)}


def profit_low_high(x: float, u: float) -> dict:
    """Costs are placeholders, so a profit is shown as an ESTIMATE range x (1 -/+ u)."""
    lo, hi = sorted((x * (1 - u), x * (1 + u)))
    return {"low": lo, "high": hi}


def enumerate_sequences(cands: list[int]) -> np.ndarray:
    c = np.asarray(cands, dtype=np.int16)
    grid = np.indices((len(c),) * T, dtype=np.int16).reshape(T, -1).T
    return c[grid]


def optimize(ctx: Context) -> dict:
    """Brute force over all 5-year sequences of climate-fit, within-budget options."""
    cands = [i for i, o in enumerate(ctx.options) if o.fits and o.water <= ctx.budget + 1e-6]
    if not cands:
        return {"n_options": 0, "n_sequences": 0, "n_feasible": 0, **least_harmful(ctx)}
    seq = enumerate_sequences(cands)
    ev = evaluate(seq, ctx)
    feas = np.flatnonzero(ev["feasible"])
    out = {"n_options": len(cands), "n_sequences": int(len(seq)), "n_feasible": int(len(feas))}
    if len(feas) == 0:
        return {**out, **least_harmful(ctx)}
    npv, water, health = ev["npv"][feas], ev["water"][feas], ev["health"][feas]
    i_profit = feas[np.lexsort((water, -npv))[0]]
    i_water = feas[np.lexsort((-npv, water))[0]]
    w = ctx.cfg["balanced_weights"]
    span = lambda x: (x.max() - x.min()) or 1.0  # noqa: E731
    score = (w["profit"] * (npv - npv.min()) / span(npv) + w["water"] * (water.max() - water) / span(water)
             + w["health"] * health / 10)
    i_bal = feas[np.lexsort((-npv, -score))[0]]
    out["status"] = "ok"
    out["plans"] = {"profit": _plan_dict(i_profit, seq, ev, ctx, "profit"),
                    "balanced": _plan_dict(i_bal, seq, ev, ctx, "balanced"),
                    "water": _plan_dict(i_water, seq, ev, ctx, "water")}
    return out


def least_harmful(ctx: Context) -> dict:
    """No plan meets every hard rule. Search ALL sequences of climate-fit options (even ones over
    the water budget) and return the one that breaks the fewest hard rules, then needs the least
    water over budget, then earns the most. Status 'relaxed': the plan is shown with the list of
    rules it breaks and is never labelled feasible."""
    cands = [i for i, o in enumerate(ctx.options) if o.fits]
    if not cands:
        return {"status": "infeasible", "blocking": {"climate": 1.0}, "relax": [], "plans": {}}
    seq = enumerate_sequences(cands)
    ev = evaluate(seq, ctx)
    v = ev["violations"]
    within = (ev["water_y"] <= ctx.budget + 1e-6).all(1)
    blocking = ({r: float(v[r][within].mean()) for r in RULE_KEYS if v[r][within].any()} if within.any()
                else {"water": 1.0})
    # which single rule, if relaxed, would make some plan feasible?
    relax = [r for r in RULE_KEYS if (~np.any(np.stack([v[q] for q in RULE_KEYS if q != r]), axis=0)).any()]
    i = np.lexsort((-ev["npv"], ev["water_excess"], ev["n_broken"]))[0]
    return {"status": "relaxed", "blocking": blocking, "relax": relax,
            "plans": {"least_harm": _plan_dict(i, seq, ev, ctx, "least_harm")}}


def evaluate_plan(keys: list[str], ctx: Context, kind: str = "check") -> dict:
    """Re-check a given sequence of option keys under (possibly different) context/scenario."""
    seq = np.array([[ctx.index[k] for k in keys]], dtype=np.int16)
    return _plan_dict(0, seq, evaluate(seq, ctx), ctx, kind)


def repeat_best_crop(ctx: Context) -> dict | None:
    """Comparison: repeat the single most profitable crop for 5 years (what many farms do).
    Limited only by what the farm can physically/commercially repeat (climate fit, water budget,
    fresh-market limit); rotation rules are ignored, so its broken rules and health are reported."""
    best, best_p = None, -np.inf
    for i, o in enumerate(ctx.options):
        if len(o.crops) != 1 or not o.fits or o.water > ctx.budget + 1e-6:
            continue
        if (o.fresh and ctx.max_fresh_years < T) or o.area_cap:
            continue
        p = o.revenue * (ctx.rules["rotation_effects"]["alfalfa_establishment_yield_factor"] if o.alfalfa else 1) - o.cost
        if p > best_p:
            best, best_p = i, p
    if best is None:
        return None
    seq = np.full((1, T), best, dtype=np.int16)
    return _plan_dict(0, seq, evaluate(seq, ctx), ctx, "repeat_best")


def why_not(plan: dict, ctx: Context, objective: str) -> list[dict]:
    """For each crop option not used in the plan: why it was rejected (structured, for the UI)."""
    used = set(plan["sequence"])
    base = np.array([[ctx.index[k] for k in plan["sequence"]]], dtype=np.int16)
    out = []
    for j, o in enumerate(ctx.options):
        if o.key in used:
            continue
        if not o.fits:
            out.append({"option": o.key, "reason": "climate", "detail": o.unfit_reason, "unfit": o.unfit})
            continue
        if o.water > ctx.budget + 1e-6:
            out.append({"option": o.key, "reason": "water", "need": o.water, "budget": ctx.budget})
            continue
        swaps = np.repeat(base, T, axis=0)
        swaps[np.arange(T), np.arange(T)] = j
        ev = evaluate(swaps, ctx)
        if ev["feasible"].any():
            f = np.flatnonzero(ev["feasible"])
            if objective == "water":
                d = ev["water"][f] - plan["water_total"]
                b = f[np.argmin(d)]
                out.append({"option": o.key, "reason": "more_water", "year": int(b) + 1,
                            "delta": float(ev["water"][b] - plan["water_total"])})
            else:
                b = f[np.argmax(ev["npv"][f])]
                out.append({"option": o.key, "reason": "less_profit" if objective == "profit" else "worse_balance",
                            "year": int(b) + 1, "delta": float(ev["npv"][b] - plan["npv"]),
                            "delta_water": float(ev["water"][b] - plan["water_total"])})
        else:
            counts = {r: int(ev["violations"][r].sum()) for r in RULE_KEYS}
            out.append({"option": o.key, "reason": "rule", "rule": max(counts, key=counts.get)})
    return out


# ------------------------------------------------------------------ scenarios + constraint cost
def scenario_metrics(point: dict, scenario: str, cfg: dict) -> dict:
    """Pick the precomputed crop metrics for a scenario ('hotter' = +delta_t climate, else baseline)."""
    return point["hotter"] if cfg["scenarios"][scenario]["delta_t_c"] > 0 else point["baseline"]


def plan_farm(point: dict, budget: float, discount_rate: float, max_fresh_years: int,
              must_years: dict | None = None) -> dict:
    """Full planner run for one field: 3 plans, comparison baseline, must-grow cost, scenarios."""
    cfg, rules, table = load_planner_config(), load_rules(), load_crop_table()
    must_years = {k: v for k, v in (must_years or {}).items() if v}

    def ctx_for(metrics, b, must):
        return make_context(metrics, b, discount_rate, max_fresh_years, must, table, rules, cfg)

    base_ctx = ctx_for(point["baseline"], budget, must_years)
    res = {"budget": budget, "must_years": must_years, "result": optimize(base_ctx),
           "repeat_best": repeat_best_crop(base_ctx),
           "options": [{"key": o.key, "fits": o.fits, "water": o.water, "unfit_reason": o.unfit_reason,
                        "profit_1y": o.revenue - o.cost, "fresh": o.fresh, "legume": o.legume,
                        "area_cap": o.area_cap,
                        "area_share": {c: float(table.loc[c, "max_area_share"]) for c in o.area_cap},
                        "check_number": o.revenue - o.cost > cfg["money"]["margin_check_usd_ha"]}
                       for o in base_ctx.options]}
    plans = res["result"]["plans"]
    res["why_not"] = ({k: why_not(p, base_ctx, k) for k, p in plans.items()}
                      if res["result"]["status"] == "ok" else {})

    # cost of the "must grow" constraint: same optimizer without it
    res["constraint_cost"] = None
    if must_years:
        free = optimize(ctx_for(point["baseline"], budget, {}))
        if free["status"] == "ok":
            res["constraint_cost"] = {
                k: {"npv_free": free["plans"][k]["npv"],
                    "npv_cost": free["plans"][k]["npv"] - plans[k]["npv"] if k in plans else None,
                    "water_change": (plans[k]["water_total"] - free["plans"][k]["water_total"]) if k in plans else None,
                    "free_sequence": free["plans"][k]["sequence"]}
                for k in free["plans"]}

    # scenarios: re-check the 3 baseline plans, and re-optimise
    res["scenarios"] = {}
    for s, sc in cfg["scenarios"].items():
        ctx = ctx_for(scenario_metrics(point, s, cfg), budget * sc["water_factor"], must_years)
        res["scenarios"][s] = {
            "budget": budget * sc["water_factor"], "delta_t_c": sc["delta_t_c"],
            "checks": {k: evaluate_plan(p["sequence"], ctx, k) for k, p in plans.items()},
            "reoptimized": optimize(ctx),
        }
    return res
