"""STEP 1 - Download NASA POWER daily data (community=AG) for every field point.

Run once offline:  python scripts/fetch_power.py
Writes data/power/<point_id>.csv and data/power/_meta.json (elevation, units).
The Streamlit app never calls this; it only reads precomputed files.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "power"
POINTS = ROOT / "data" / "points.csv"

API = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMS = ["T2M_MAX", "T2M_MIN", "T2M", "PRECTOTCORR", "EVPTRNS",
          "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN"]
START, END = "19910101", "20261031"


def fetch(pid: str, lat: float, lon: float, force: bool = False) -> dict:
    csv_path = OUT / f"{pid}.csv"
    if csv_path.exists() and not force:
        print(f"[skip] {pid} already downloaded")
        return {}
    q = {
        "parameters": ",".join(PARAMS),
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": START,
        "end": END,
        "format": "JSON",
        "time-standard": "LST",
    }
    for attempt in range(5):
        try:
            r = requests.get(API, params=q, timeout=300)
            r.raise_for_status()
            js = r.json()
            break
        except Exception as e:  # noqa: BLE001
            wait = 15 * (attempt + 1)
            print(f"[retry] {pid}: {e} - waiting {wait}s")
            time.sleep(wait)
    else:
        raise RuntimeError(f"Failed to download {pid}")

    fill = js.get("header", {}).get("fill_value", -999.0)
    data = js["properties"]["parameter"]
    df = pd.DataFrame(data)
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df.index.name = "DATE"
    df = df.replace(fill, pd.NA)
    df = df[PARAMS]
    df.to_csv(csv_path, float_format="%.3f")
    elev = js["geometry"]["coordinates"][2] if len(js["geometry"]["coordinates"]) > 2 else None
    units = {k: v.get("units") for k, v in js.get("parameters", {}).items()}
    print(f"[ok] {pid}: {len(df)} days, elevation={elev} m")
    return {"elevation_m": elev, "units": units}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    force = "--force" in sys.argv
    meta_path = OUT / "_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    pts = pd.read_csv(POINTS)
    for row in pts.itertuples():
        info = fetch(row.id, row.lat, row.lon, force=force)
        if info:
            meta[row.id] = info
            meta_path.write_text(json.dumps(meta, indent=2))
    print("done")


if __name__ == "__main__":
    main()
