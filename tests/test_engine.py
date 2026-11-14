"""Tests for the crop engine's season window: frost counts only between emergence and harvest,
and the sowing date may shift inside the crop's typical Uzbek sowing window."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from dalashift.crops import CROPS
from dalashift.engine import evaluate_crop, simulate_season, sow_candidates

ROOT = Path(__file__).resolve().parents[1]
PLANNER = json.loads((ROOT / "data" / "planner.json").read_text())


def test_cotton_passes_the_season_check_at_karshi():
    m = PLANNER["points"]["Karshi_field1"]["baseline"]["cotton"]
    assert m["fits"] is True
    assert m["p_frost"] <= 0.2 and m["p_gdd_ok"] >= 0.8
    # chosen sowing date lies inside the cotton window (1-20 April)
    sow = pd.Timestamp(f"2001 {m['sow']}")
    assert pd.Timestamp(2001, 4, 1) <= sow <= pd.Timestamp(2001, 4, 20)


def test_potato_has_spring_and_summer_windows():
    cands = sow_candidates(CROPS["potato"])
    assert (3, 1) in cands and (7, 15) in cands


def _synthetic(frost_day: int) -> pd.DataFrame:
    idx = pd.date_range("2015-01-01", "2016-12-31", freq="D")
    df = pd.DataFrame(index=idx)
    df["T2M_MIN"], df["T2M_MAX"] = 12.0, 28.0
    df["TMEAN"] = 20.0
    df["ET0"], df["P"], df["WS2M"], df["RHMIN"] = 5.0, 0.0, 2.0, 40.0
    df.iloc[frost_day, df.columns.get_loc("T2M_MIN")] = -2.0
    return df


def test_frost_before_emergence_is_not_counted():
    crop = CROPS["potato"]                       # 21 days from planting to emergence
    sow = pd.Timestamp(2015, 3, 10)
    end = sow + pd.Timedelta(days=crop.season_days - 1)
    before = _synthetic(int((sow - pd.Timestamp(2015, 1, 1)).days) + 5)    # frost 5 days after planting
    after = _synthetic(int((sow - pd.Timestamp(2015, 1, 1)).days) + 30)    # frost after emergence
    assert simulate_season(crop, before, sow, end)["frost"] is False
    assert simulate_season(crop, after, sow, end)["frost"] is True


def test_sowing_date_stays_inside_window_and_avoids_frost():
    """If frost hits on 25 April every year, cotton is sown late enough that it emerges after it."""
    idx = pd.date_range("2010-01-01", "2026-10-31", freq="D")
    df = pd.DataFrame(index=idx)
    df["T2M_MIN"], df["T2M_MAX"], df["TMEAN"] = 15.0, 32.0, 23.5
    df["ET0"], df["P"], df["WS2M"], df["RHMIN"] = 6.0, 0.0, 2.0, 35.0
    df.loc[(df.index.month == 4) & (df.index.day == 25), "T2M_MIN"] = -1.0
    res = evaluate_crop(CROPS["cotton"], df, "now")
    assert res["fits"] and res["p_frost"] == 0
    sow = pd.Timestamp(f"2001 {res['sow']}")
    assert pd.Timestamp(2001, 4, 1) <= sow <= pd.Timestamp(2001, 4, 20)
    assert sow + pd.Timedelta(days=CROPS["cotton"].emergence_days) > pd.Timestamp(2001, 4, 25)
