"""'Your usual rotation' baseline for the farmer view (presentation helper, no new modelling).

The usual Uzbek rotation is winter wheat <-> cotton, in every district. Where cotton needs more
water than the farm has, the baseline is still shown (with the deficit), because it is what farms do.
The baseline is evaluated with the same planner (same yields, prices, rotation effects), but it is
NOT required to obey the rotation rules: it is what farms do today, not a recommendation.
"""
from __future__ import annotations

from .planner import evaluate_plan, make_context

RISK = {"low": 0, "medium": 1, "high": 2}


def usual_rotation(metrics: dict, budget: float) -> list[str]:
    """What farms actually do: winter wheat <-> cotton (even where cotton needs more water than the farm has)."""
    return ["winter_wheat", "cotton", "winter_wheat", "cotton", "winter_wheat"]


def water_deficit(usual: dict, budget: float) -> float:
    """m3/ha by which the thirstiest year of the usual rotation exceeds the farm's water (0 if it fits)."""
    return max(max(y["water"] for y in usual["years"]) - budget, 0.0)


def evaluate_usual(metrics: dict, budget: float, discount_rate: float, max_fresh_years: int) -> dict:
    keys = usual_rotation(metrics, budget)
    ctx = make_context(metrics, budget, discount_rate, max_fresh_years)
    return evaluate_plan(keys, ctx, "usual")


def risk_level(plan: dict) -> str:
    """low / medium / high from the yearly heat risk plus any frost or winterkill risk."""
    score = sum(RISK[y["heat_risk"]] + (1 if max(y["p_frost"], y["p_winterkill"]) > 0.1 else 0)
                for y in plan["years"]) / len(plan["years"])
    return "low" if score < 0.75 else "medium" if score < 1.5 else "high"


def compare(plan: dict, usual: dict) -> dict:
    """Plan relative to the usual rotation: income and water in %, risk levels."""
    base_income, base_water = usual["profit_total"], usual["water_total"]
    income_pct = (100 * (plan["profit_total"] - base_income) / abs(base_income)) if base_income > 1 else None
    return {
        "income_pct": income_pct,
        "income_diff_year": (plan["profit_total"] - base_income) / 5,
        "water_pct": 100 * (plan["water_total"] - base_water) / base_water if base_water else 0.0,
        "risk_plan": risk_level(plan), "risk_usual": risk_level(usual),
    }
