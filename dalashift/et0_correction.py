"""ET0 bias correction for the crop engine (see config/et0_correction.yaml).

MERRA-2 (NASA POWER) has no irrigation, so ET0 over irrigated land is too high. The crop engine
multiplies ET0 by a factor per climate profile:
  1. calibrated with ECOSTRESS ETdaily (AppEEARS point samples in data/appeears/), if available;
  2. else a per-site value from the config;
  3. else the default (0.80, approximate, provisional).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .crops import CROPS

CONFIG = Path(__file__).resolve().parents[1] / "config" / "et0_correction.yaml"


def load_config(path: Path = CONFIG) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def ecostress_ratio(et_obs: pd.Series, et0: pd.Series, kc_mid: float, cfg: dict) -> tuple[float, int] | None:
    """et_obs: ECOSTRESS ETdaily (mm/day) indexed by date; et0: raw POWER ET0 (mm/day).
    Returns (clipped factor, matched days) or None if there are too few days."""
    e = cfg["ecostress"]
    obs = et_obs[et_obs.index.month.isin(e["months"])].dropna()
    obs = obs[obs > 0]
    days = obs.index.intersection(et0.index)
    if len(days) < e["min_days"]:
        return None
    ratio = float(np.median(obs.loc[days]) / np.median(et0.loc[days] * kc_mid))
    lo, hi = e["clip"]
    return float(np.clip(ratio, lo, hi)), int(len(days))


def et0_factor(fields: list[str], district: str, df: pd.DataFrame, appeears: pd.DataFrame | None,
               cfg: dict | None = None) -> dict:
    """Correction for one climate profile (all fields sharing a POWER cell)."""
    cfg = cfg or load_config()
    if appeears is not None and len(appeears):
        et = appeears[(appeears["var"] == "etdaily") & appeears["point"].isin(fields)]
        if len(et):
            obs = et.groupby("date")["value"].median()
            obs.index = pd.to_datetime(obs.index).normalize()
            kc = CROPS[cfg["ecostress"]["reference_crop"]].kc_mid
            r = ecostress_ratio(obs, df["ET0"], kc, cfg)
            if r is not None:
                return {"factor": round(r[0], 3), "method": "ecostress", "n_days": r[1],
                        "label": cfg["ecostress"]["label"]}
    sites = cfg.get("sites") or {}
    for key in [*fields, district]:
        if key in sites:
            return {"factor": float(sites[key]), "method": "site", "n_days": 0, "label": cfg["default_label"]}
    return {"factor": float(cfg["default_factor"]), "method": "default", "n_days": 0, "label": cfg["default_label"]}


def apply(df: pd.DataFrame, factor: float) -> pd.DataFrame:
    out = df.copy()
    out["ET0"] = out["ET0"] * factor
    return out
