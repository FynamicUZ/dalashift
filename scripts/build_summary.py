"""STEPS 2 + 3 - Precompute climate shift and crop recommendations for every field point.

Run offline after fetch_power.py:   python scripts/build_summary.py
Writes data/summary.json (climate) and data/recommendations.json (crops).
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dalashift.climate import (PERIODS, PRECIP_QC_MAX, annual_indicators, doy_to_date,  # noqa: E402
                               load_point, monthly_climatology, period_mean)
from dalashift.engine import recommend_point  # noqa: E402

DATA = ROOT / "data"


def clean(o):
    """Make numpy / NaN values JSON-safe."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if np.isnan(o) else round(float(o), 2)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def main() -> None:
    pts = pd.read_csv(DATA / "points.csv")
    meta = json.loads((DATA / "power" / "_meta.json").read_text())
    summary = {"generated": date.today().isoformat(), "periods": PERIODS,
               "source": "NASA POWER daily, community=AG (MERRA-2 / CERES / IMERG-corrected precip)",
               "precip_qc_max_mm_day": PRECIP_QC_MAX, "points": {}}
    recs = {"generated": date.today().isoformat(), "periods": PERIODS, "points": {}}

    for row in pts.itertuples():
        elev = meta[row.id]["elevation_m"]
        df = load_point(DATA / "power" / f"{row.id}.csv", row.lat, elev)
        ann = annual_indicators(df)
        then, now = period_mean(ann, "then"), period_mean(ann, "now")
        change = {k: (None if then[k] is None or now[k] is None else round(now[k] - then[k], 1)) for k in then}
        for p in (then, now):
            p["last_spring_frost_date"] = doy_to_date(p["last_spring_frost"])
            p["first_autumn_frost_date"] = doy_to_date(p["first_autumn_frost"])
        summary["points"][row.id] = {
            "lat": row.lat, "lon": row.lon, "district": row.id.split("_")[0], "elevation_m": elev,
            "precip_qc_days_removed": int(df["P_QC_FLAG"].sum()),
            "then": then, "now": now, "change": change,
            "annual": {"year": ann.index.tolist(), **{c: ann[c].tolist() for c in ann.columns}},
            "monthly": {p: monthly_climatology(df, p) for p in PERIODS},
        }
        recs["points"][row.id] = recommend_point(df)
        top = recs["points"][row.id]["ranking"]["now"][:3]
        print(f"{row.id:16s} hot days {then['hot_days']:5.1f} -> {now['hot_days']:5.1f} | "
              f"GDD10 {then['gdd10']} -> {now['gdd10']} | ET0 gs {then['gs_et0']} -> {now['gs_et0']} | top: {top}")

    (DATA / "summary.json").write_text(json.dumps(clean(summary), indent=1))
    (DATA / "recommendations.json").write_text(json.dumps(clean(recs), indent=1))
    print("wrote data/summary.json and data/recommendations.json")


if __name__ == "__main__":
    main()
