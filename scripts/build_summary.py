"""STEPS 2 + 3 - Precompute climate shift and crop recommendations for every field point.

Run offline after fetch_power.py:   python scripts/build_summary.py
Writes data/summary.json (climate) and data/recommendations.json (crops).
"""
from __future__ import annotations

import hashlib
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

    # Fields whose POWER files are byte-identical sit in the same MERRA-2 grid cell
    # (0.5 deg x 0.625 deg). They get ONE climate profile, computed at the cells' mean location;
    # field-level differences must come from the satellite layers (SMAP, ECOSTRESS, HLS).
    pts["hash"] = [hashlib.md5((DATA / "power" / f"{i}.csv").read_bytes()).hexdigest() for i in pts["id"]]
    summary["cells"] = {}
    for _, g in pts.groupby("hash", sort=False):
        fields = g["id"].tolist()
        district = fields[0].split("_")[0]
        cell_id = f"{district}_cell" if len(fields) > 1 else fields[0]
        lat, lon = float(g["lat"].mean()), float(g["lon"].mean())
        elev = meta[fields[0]]["elevation_m"]
        df = load_point(DATA / "power" / f"{fields[0]}.csv", lat, elev)
        ann = annual_indicators(df)
        then, now = period_mean(ann, "then"), period_mean(ann, "now")
        change = {k: (None if then[k] is None or now[k] is None else round(now[k] - then[k], 1)) for k in then}
        for p in (then, now):
            p["last_spring_frost_date"] = doy_to_date(p["last_spring_frost"])
            p["first_autumn_frost_date"] = doy_to_date(p["first_autumn_frost"])
        climate = {
            "cell_id": cell_id, "cell_fields": fields, "cell_lat": round(lat, 4), "cell_lon": round(lon, 4),
            "district": district, "elevation_m": elev,
            "precip_qc_days_removed": int(df["P_QC_FLAG"].sum()),
            "then": then, "now": now, "change": change,
            "annual": {"year": ann.index.tolist(), **{c: ann[c].tolist() for c in ann.columns}},
            "monthly": {p: monthly_climatology(df, p) for p in PERIODS},
        }
        rec = recommend_point(df)
        summary["cells"][cell_id] = {"fields": fields, "lat": lat, "lon": lon}
        for row in g.itertuples():
            summary["points"][row.id] = {"lat": row.lat, "lon": row.lon, **climate}
            recs["points"][row.id] = {"cell_id": cell_id, **rec}
        print(f"{cell_id:16s} {fields} hot days {then['hot_days']:5.1f} -> {now['hot_days']:5.1f} | "
              f"GDD10 {then['gdd10']} -> {now['gdd10']} | top: {rec['ranking']['now'][:3]}")

    (DATA / "summary.json").write_text(json.dumps(clean(summary), indent=1))
    (DATA / "recommendations.json").write_text(json.dumps(clean(recs), indent=1))
    print("wrote data/summary.json and data/recommendations.json")


if __name__ == "__main__":
    main()
