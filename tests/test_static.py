"""The static Netlify site (web/) must show the same numbers as the engine / Streamlit app.
If this fails, re-run:  python scripts/export_static.py"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dalashift.baseline import compare, evaluate_usual
from dalashift.planner import load_planner_config, plan_farm
from dalashift.simple_ui import FARMER_DISTRICTS, WATER_LEVELS, to_mln

ROOT = Path(__file__).resolve().parents[1]
WEB = json.loads((ROOT / "web/data.json").read_text(encoding="utf-8"))
PLANNER = json.loads((ROOT / "data/planner.json").read_text())["points"]
CFG = load_planner_config()


def test_static_site_files_exist_and_paths_are_relative():
    for f in ["index.html", "app.js", "style.css", "data.json", "deck/index.html", "deck/vendor/reveal.min.js",
              "deck/DalaShift_deck.pdf", "screenshots/farmer_full_phone.png"]:
        assert (ROOT / "web" / f).exists(), f
    html = (ROOT / "web/index.html").read_text(encoding="utf-8") + (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert 'src="/' not in html and 'href="/' not in html


def test_every_farmer_choice_is_exported():
    assert set(WEB["districts"]) == set(FARMER_DISTRICTS)
    for d in WEB["districts"].values():
        assert set(d["scenarios"]) == {f"{w}|{m}" for w in WATER_LEVELS for m in (0, 1)}


@pytest.mark.parametrize("district,water,must", [("Karshi", "normal", 0), ("Fergana", "plenty", 0),
                                                 ("Karshi", "normal", 1), ("Nukus", "little", 0)])
def test_static_numbers_match_the_engine(district, water, must):
    point, budget = PLANNER[f"{district}_field1"], float(WATER_LEVELS[water])
    rate, fresh = float(CFG["discount_rate"]), int(CFG["max_fresh_market_years"])
    res = plan_farm(point, budget, rate, fresh, {"cotton": 2 * must, "winter_wheat": 2 * must})
    usual = evaluate_usual(point["baseline"], budget, rate, fresh)
    sc = WEB["districts"][district]["scenarios"][f"{water}|{must}"]
    assert sc["status"] == res["result"]["status"]
    for kind, plan in res["result"]["plans"].items():
        w = sc["plans"][kind]
        assert w["sequence"] == plan["sequence"]
        assert w["income_low"] == max(to_mln(plan["profit_per_year_range"]["low"]), 0)
        assert w["water_per_year"] == round(plan["water_per_year"])
        c = compare(plan, usual)
        assert w["cmp"]["water_pct"] == round(c["water_pct"], 1)
