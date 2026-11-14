"""Download FAOSTAT bulk files and save Uzbekistan-only extracts used by config/crops.csv.

Run offline (needs internet, ~16 MB download):  python scripts/fetch_faostat.py
Writes:
  data/faostat/uz_producer_prices.csv   FAOSTAT "Prices" (PP), Producer Price (USD/tonne)
  data/faostat/uz_yields.csv            FAOSTAT "Crops and livestock products" (QCL), Yield (kg/ha)
The FAOSTAT API now requires a token, so the public bulk files are used instead.
"""
from __future__ import annotations

import io
import tempfile
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "faostat"
BULK = "https://bulks-faostat.fao.org/production/"
ITEMS = ["Seed cotton, unginned", "Wheat", "Barley", "Maize (corn)", "Rice", "Sorghum", "Sunflower seed",
         "Chick peas, dry", "Potatoes", "Onions and shallots, dry (excluding dehydrated)", "Tomatoes",
         "Cantaloupes and other melons", "Watermelons", "Peas, dry", "Beans, dry", "Pulses, Total"]


def _csv_from_zip(url: str, member_contains: str) -> pd.DataFrame:
    r = requests.get(url, timeout=600)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        name = next(n for n in z.namelist() if member_contains in n and "NOFLAG" not in n)
        with tempfile.TemporaryDirectory() as tmp:
            path = z.extract(name, tmp)
            return pd.read_csv(path, encoding="latin1", low_memory=False)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    accessed = date.today().isoformat()

    pr = _csv_from_zip(BULK + "Prices_E_All_Data_(Normalized).zip", "All_Data")
    pr = pr[(pr["Area"] == "Uzbekistan") & (pr["Element"] == "Producer Price (USD/tonne)") & pr["Item"].isin(ITEMS)]
    pr = pr[["Item", "Year", "Element", "Unit", "Value", "Flag"]].sort_values(["Item", "Year"])
    pr["accessed"] = accessed
    pr.to_csv(OUT / "uz_producer_prices.csv", index=False)

    qc = _csv_from_zip(BULK + "Production_Crops_Livestock_E_Asia.zip", "E_Asia.csv")
    qc = qc[(qc["Area"] == "Uzbekistan") & (qc["Element"] == "Yield") & qc["Item"].isin(ITEMS)]
    years = [c for c in qc.columns if len(c) == 5 and c.startswith("Y") and c[1:].isdigit()]
    qc = qc.melt(id_vars=["Item", "Unit"], value_vars=years, var_name="Year", value_name="Value").dropna()
    qc["Year"] = qc["Year"].str[1:].astype(int)
    qc = qc[qc["Year"] >= 2015].sort_values(["Item", "Year"])
    qc["accessed"] = accessed
    qc.to_csv(OUT / "uz_yields.csv", index=False)
    print(f"wrote {len(pr)} price rows and {len(qc)} yield rows to {OUT}")


if __name__ == "__main__":
    main()
