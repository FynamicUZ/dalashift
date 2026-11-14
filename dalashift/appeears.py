"""Loader for NASA AppEEARS point-sample CSV exports placed in data/appeears/.

Expected (any subset):
  * SMAP L4 (SPL4SMGP)        -> column ending in 'sm_rootzone'                [m3/m3]
  * ECOSTRESS ESI             -> column ending in 'ESI' or 'ESIavg'             [-]
  * ECOSTRESS ET (PT-JPL)     -> column ending in 'ETdaily'                     [mm/day; W/m2 converted]
                                 (used to calibrate the ET0 bias correction, dalashift/et0_correction.py)
  * HLS L30 / S30             -> column containing 'NDVI', or computed from
                                 B04 (red) and B05 (L30 NIR) / B8A (S30 NIR)
Rows are matched to field points by the AppEEARS 'ID' column (use data/appeears_points.csv
as the upload) or, failing that, by the nearest lat/lon within 0.1 degree.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

VARS = ("sm", "esi", "ndvi", "etdaily")
W_M2_TO_MM_DAY = 86400 / 2.45e6   # latent heat flux W/m2 -> mm/day of water


def etdaily_mm(values: pd.Series) -> pd.Series:
    """ECOSTRESS ETdaily is W/m2 in collection 1 (ECO3ETPTJPL) and mm/day in collection 2.
    A column whose median is above 30 can only be W/m2 and is converted."""
    v = pd.to_numeric(values, errors="coerce")
    return v * W_M2_TO_MM_DAY if v.median() > 30 else v


def _find(cols, pattern):
    for c in cols:
        if re.search(pattern, c, flags=re.I):
            return c
    return None


def _match_ids(df: pd.DataFrame, points: pd.DataFrame) -> pd.Series:
    ids = set(points["id"])
    if "ID" in df.columns and df["ID"].astype(str).isin(ids).any():
        return df["ID"].astype(str)
    lat_c, lon_c = _find(df.columns, r"^lat"), _find(df.columns, r"^lon")
    if not lat_c or not lon_c:
        return pd.Series([None] * len(df), index=df.index)
    out = []
    for la, lo in zip(df[lat_c], df[lon_c]):
        d = np.hypot(points["lat"] - la, points["lon"] - lo)
        out.append(points["id"].iloc[d.idxmin()] if d.min() < 0.1 else None)
    return pd.Series(out, index=df.index)


def _clean(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    return s.where((s > -9000) & (s < 60000))


def load_appeears(folder: Path, points: pd.DataFrame) -> pd.DataFrame:
    """Return long table: point, date, var, value. Empty if folder has no usable CSVs."""
    frames = []
    for f in sorted(Path(folder).glob("*.csv")):
        try:
            df = pd.read_csv(f, low_memory=False)
        except Exception:  # noqa: BLE001
            continue
        date_c = _find(df.columns, r"^date$")
        if date_c is None:
            continue
        pid = _match_ids(df, points)
        date = pd.to_datetime(df[date_c], errors="coerce")
        series = {}
        if c := _find(df.columns, r"sm_rootzone$"):
            series["sm"] = _clean(df[c])
        if c := _find(df.columns, r"(_|^)ESI(avg)?$"):
            series["esi"] = _clean(df[c])
        if c := _find(df.columns, r"ETdaily$"):
            series["etdaily"] = etdaily_mm(_clean(df[c]))
        if c := _find(df.columns, r"NDVI"):
            series["ndvi"] = _clean(df[c])
        else:
            red = _find(df.columns, r"_B04$")
            nir = _find(df.columns, r"_B05$") or _find(df.columns, r"_B8A$")
            if red and nir:
                r, n = _clean(df[red]), _clean(df[nir])
                series["ndvi"] = (n - r) / (n + r)
        for var, val in series.items():
            if var == "ndvi":
                val = val.where(val.between(-1, 1))
            frames.append(pd.DataFrame({"point": pid, "date": date, "var": var, "value": val}))
    if not frames:
        return pd.DataFrame(columns=["point", "date", "var", "value"])
    out = pd.concat(frames).dropna(subset=["point", "date", "value"])
    return out.groupby(["point", "var", "date"], as_index=False)["value"].mean()
