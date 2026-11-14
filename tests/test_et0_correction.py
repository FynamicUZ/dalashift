"""ET0 bias correction: default factor, per-site override, ECOSTRESS calibration path."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dalashift.appeears import load_appeears
from dalashift.crops import CROPS
from dalashift.et0_correction import et0_factor, load_config

ROOT = Path(__file__).resolve().parents[1]
CFG = load_config()


def _df():
    idx = pd.date_range("2024-01-01", "2024-12-31", freq="D")
    return pd.DataFrame({"ET0": 8.0}, index=idx)


def test_default_factor_is_080_and_labelled_provisional():
    c = et0_factor(["X_field1"], "X", _df(), None, CFG)
    assert c["factor"] == pytest.approx(0.80) and c["method"] == "default"
    assert "provisional" in c["label"] and "MERRA-2" in c["label"]


def test_site_override():
    cfg = {**CFG, "sites": {"Karshi": 0.7}}
    assert et0_factor(["Karshi_field1"], "Karshi", _df(), None, cfg)["factor"] == pytest.approx(0.7)


def test_ecostress_calibration_used_when_data_present():
    kc = CROPS[CFG["ecostress"]["reference_crop"]].kc_mid
    days = pd.date_range("2024-06-05", "2024-08-25", freq="7D")
    obs = 8.0 * kc * 0.75                                   # observed ET = 75 % of POWER ET0 x Kc_mid
    ap = pd.DataFrame({"point": "X_field1", "var": "etdaily", "date": days, "value": obs})
    c = et0_factor(["X_field1"], "X", _df(), ap, CFG)
    assert c["method"] == "ecostress" and c["label"] == "calibrated with ECOSTRESS"
    assert c["factor"] == pytest.approx(0.75, abs=1e-3) and c["n_days"] == len(days)


def test_too_few_ecostress_days_falls_back_to_default():
    ap = pd.DataFrame({"point": "X_field1", "var": "etdaily",
                       "date": pd.to_datetime(["2024-07-01", "2024-07-10"]), "value": [5.0, 5.0]})
    assert et0_factor(["X_field1"], "X", _df(), ap, CFG)["method"] == "default"


def test_appeears_loader_reads_etdaily_in_w_m2(tmp_path):
    pts = pd.DataFrame({"id": ["X_field1"], "lat": [38.9], "lon": [65.6]})
    pd.DataFrame({"ID": ["X_field1"] * 3, "Date": ["2024-07-01", "2024-07-08", "2024-07-15"],
                  "ECO3ETPTJPL_001_EVAPOTRANSPIRATION_PT_JPL_ETdaily": [200.0, 220.0, 180.0]}
                 ).to_csv(tmp_path / "eco.csv", index=False)
    a = load_appeears(tmp_path, pts)
    v = a[a["var"] == "etdaily"]["value"]
    assert len(v) == 3 and np.allclose(v.median(), 200 * 86400 / 2.45e6)   # ~7.05 mm/day


def test_rebuilt_data_carries_the_correction():
    planner = json.loads((ROOT / "data" / "planner.json").read_text())
    for p in planner["points"].values():
        assert 0.4 <= p["et0_correction"]["factor"] <= 1.2
