"""NASA SMAP root-zone soil moisture (AppEEARS CSV in data/appeears/) -> farmer facts."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from dalashift.appeears import load_appeears
from dalashift.smap import summary

ROOT = Path(__file__).resolve().parents[1]
WATER = load_appeears(ROOT / "data/appeears", pd.read_csv(ROOT / "data/points.csv"))
HAS_SMAP = len(WATER) and (WATER["var"] == "sm").any()


def test_summary_on_synthetic_series():
    days = pd.date_range("2025-01-01", "2025-12-31", freq="D", tz="UTC")
    val = [0.15 if d.month in (3, 4) else 0.09 if d.month in (7, 8) else 0.12 for d in days]
    df = pd.DataFrame({"point": "X", "var": "sm", "date": days, "value": val})
    s = summary(df, "X")
    assert s["year"] == 2025 and s["spring"] == 0.15 and s["summer"] == 0.09 and s["drop_pct"] == 40


def test_no_data_gives_none():
    assert summary(pd.DataFrame(columns=["point", "var", "date", "value"]), "X") is None


@pytest.mark.skipif(not HAS_SMAP, reason="no SMAP file in data/appeears")
def test_real_smap_karshi_is_physical_and_exported():
    s = summary(WATER, "Karshi_field1")
    assert s and 0.02 < s["summer"] < s["spring"] < 0.6 and 10 <= s["drop_pct"] <= 80
    web = json.loads((ROOT / "web/data.json").read_text(encoding="utf-8"))
    assert web["districts"]["Karshi"]["smap"]["drop_pct"] == s["drop_pct"]
