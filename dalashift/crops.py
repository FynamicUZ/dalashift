"""Crop parameter table used by the DalaShift rule engine - loaded from config/crops.csv.

config/crops.csv is the single source of truth. Every value group there carries a
`<group>_status` ("documented" / "approximate"), `<group>_source` and `<group>_date`.

Sources (summary - see the CSV for each value)
-------
* Kc_ini / Kc_mid / Kc_end and maximum crop height h:
    FAO-56, Table 12 (Allen et al., 1998, FAO Irrigation and Drainage Paper 56).
    Kc_mid and Kc_end are later adjusted for the local climate with FAO-56 Eq. 62
    (wind speed u2 and minimum relative humidity RHmin), see engine.py.
* Stage lengths L_ini / L_dev / L_mid / L_late [days]:
    FAO-56, Table 11, adapted to typical Uzbek sowing calendars.
* Salinity thresholds: FAO-29 Table 4 (Ayers & Westcot, 1985) where listed.
* Yields / producer prices: FAOSTAT (Uzbekistan) where a series exists, else labelled proxies/assumptions.
* GDD requirement, base temperature, heat threshold, frost behaviour and costs are NOT from
  FAO-56. They are approximate and kept deliberately visible so agronomists can change them.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

CROPS_CSV = Path(__file__).resolve().parents[1] / "config" / "crops.csv"
# Optional local price override: crop,price_usd_per_t,source,date. Rows here REPLACE the FAOSTAT
# (or proxy) price in crops.csv. Shipped with headers only until real local prices arrive.
LOCAL_PRICES_CSV = CROPS_CSV.parent / "local_prices.csv"
# Optional manual retail prices (so'm/kg) -> farm-gate USD/t via config/retail_to_farmgate.yaml.
RETAIL_PRICES_CSV = CROPS_CSV.parent / "retail_prices.csv"
RETAIL_CFG = CROPS_CSV.parent / "retail_to_farmgate.yaml"


@dataclass(frozen=True)
class Crop:
    key: str
    sow: tuple[int, int]               # (month, day); winter crops are sown in the previous year
    stages: tuple[int, int, int, int]  # FAO-56 Table 11: L_ini, L_dev, L_mid, L_late
    kc_ini: float                      # FAO-56 Table 12
    kc_mid: float                      # FAO-56 Table 12
    kc_end: float                      # FAO-56 Table 12
    height_m: float                    # FAO-56 Table 12 (for Eq. 62 adjustment)
    gdd_base: float                    # degC
    min_gdd: float                     # degC-days from sowing to maturity (approx.)
    heat_tmax: float                   # Tmax above which the sensitive (mid) stage is stressed
    frost_sensitive: bool              # any Tmin <= 0 degC in season = damage
    winterkill_tmin: float | None = None   # winter crops: approx. lethal air Tmin -> risk warning, not exclusion
    extra_mm: float = 0.0              # non-ET water use (rice: soaking/ponding/percolation)
    latest_harvest: tuple[int, int] | None = None  # GDD fit is checked up to this date (cool years ripen later)
    second_crop: bool = False          # only grown after a winter crop (not ranked alone)
    overwinter: bool = False           # sown in autumn, harvested next year
    perennial: bool = False
    family: str = ""
    legume: bool = False
    # sowing windows [((m, d), (m, d)), ...]; the engine picks the best date inside them per site.
    # Empty = fixed date `sow` (winter cereals: see engine.wheat_sowing_shift).
    sow_windows: tuple = ()
    emergence_days: int = 0            # frost before emergence does not count (seed / tuber is in the soil)

    @property
    def season_days(self) -> int:
        return sum(self.stages)


def _bool(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def _opt_float(v):
    return None if pd.isna(v) or str(v).strip() == "" else float(v)


def _windows(v) -> tuple:
    if not isinstance(v, str) or not v.strip():
        return ()
    out = []
    for w in v.split(";"):
        a, b = w.split(":")
        out.append((tuple(int(x) for x in a.split("-")), tuple(int(x) for x in b.split("-"))))
    return tuple(out)


def load_crop_table(path: Path = CROPS_CSV, local_prices: Path | None = LOCAL_PRICES_CSV,
                    retail_prices: Path | None = RETAIL_PRICES_CSV, retail_cfg: Path | None = RETAIL_CFG) -> pd.DataFrame:
    """crops.csv, then retail-based farm-gate prices, then local_prices.csv (which wins if both exist)."""
    table = pd.read_csv(path, keep_default_na=True).set_index("crop", drop=False)
    table = apply_retail_prices(table, retail_prices, retail_cfg)
    return apply_local_prices(table, local_prices)


def farm_gate_prices(retail_prices: Path | None, retail_cfg: Path | None) -> pd.DataFrame:
    """Rows of config/retail_prices.csv that have a price, converted to farm-gate USD/t:
    retail_uzs_per_kg x farm_gate_share x 1000 / uzs_per_usd. Empty rows are skipped."""
    cols = ["crop", "retail_uzs_per_kg", "where", "date", "share", "uzs_per_usd", "price_usd_t"]
    if retail_prices is None or retail_cfg is None or not Path(retail_prices).exists() or not Path(retail_cfg).exists():
        return pd.DataFrame(columns=cols)
    rp = pd.read_csv(retail_prices)
    rp["retail_uzs_per_kg"] = pd.to_numeric(rp["retail_uzs_per_kg"], errors="coerce")
    rp = rp.dropna(subset=["retail_uzs_per_kg"])
    rp = rp[rp["retail_uzs_per_kg"] > 0]
    if rp.empty:
        return pd.DataFrame(columns=cols)
    cfg = yaml.safe_load(Path(retail_cfg).read_text(encoding="utf-8"))
    rate = cfg.get("uzs_per_usd")
    if not rate:
        warnings.warn("config/retail_prices.csv has prices but uzs_per_usd in config/retail_to_farmgate.yaml "
                      "is not set - retail prices are NOT used (FAOSTAT kept).", stacklevel=2)
        return pd.DataFrame(columns=cols)
    shares = cfg.get("farm_gate_share") or {}
    rp["share"] = [float(shares.get(c, cfg["default_farm_gate_share"])) for c in rp["crop"]]
    rp["uzs_per_usd"] = float(rate)
    rp["price_usd_t"] = rp["retail_uzs_per_kg"] * rp["share"] * 1000 / rp["uzs_per_usd"]
    return rp[cols]


def apply_retail_prices(table: pd.DataFrame, retail_prices: Path | None, retail_cfg: Path | None) -> pd.DataFrame:
    fg = farm_gate_prices(retail_prices, retail_cfg)
    fg = fg[fg["crop"].isin(table.index)]          # e.g. carrot is not a planner crop
    if fg.empty:
        return table
    table = table.copy()
    for r in fg.itertuples(index=False):
        table.loc[r.crop, "price_usd_t"] = round(float(r.price_usd_t), 1)
        table.loc[r.crop, "price_status"] = "approximate"
        table.loc[r.crop, "price_source"] = (f"Retail {r.retail_uzs_per_kg:,.0f} so'm/kg ({r.where}, {r.date}) "
                                             f"x farm-gate share {r.share:.2f} (approximate) / {r.uzs_per_usd:,.0f} so'm per USD")
        table.loc[r.crop, "price_date"] = str(r.date)
    return table


def apply_local_prices(table: pd.DataFrame, path: Path | None) -> pd.DataFrame:
    """Replace price_usd_t with local prices where config/local_prices.csv has a row for the crop."""
    if path is None or not Path(path).exists():
        return table
    lp = pd.read_csv(path).dropna(subset=["crop", "price_usd_per_t"])
    lp = lp[lp["crop"].isin(table.index)]
    if lp.empty:
        return table
    table = table.copy()
    for r in lp.itertuples(index=False):
        table.loc[r.crop, "price_usd_t"] = float(r.price_usd_per_t)
        table.loc[r.crop, "price_status"] = "documented"
        table.loc[r.crop, "price_source"] = f"Local price (config/local_prices.csv): {r.source}"
        table.loc[r.crop, "price_date"] = str(r.date)
    return table


def load_crops(path: Path = CROPS_CSV) -> dict[str, Crop]:
    crops = {}
    for r in load_crop_table(path).itertuples(index=False):
        lh = None
        if isinstance(r.latest_harvest, str) and r.latest_harvest.strip():
            m, d = r.latest_harvest.split("-")
            lh = (int(m), int(d))
        crops[r.crop] = Crop(
            key=r.crop, sow=(int(r.sow_month), int(r.sow_day)),
            stages=(int(r.l_ini), int(r.l_dev), int(r.l_mid), int(r.l_late)),
            kc_ini=float(r.kc_ini), kc_mid=float(r.kc_mid), kc_end=float(r.kc_end), height_m=float(r.height_m),
            gdd_base=float(r.gdd_base_c), min_gdd=float(r.min_gdd), heat_tmax=float(r.heat_tmax_c),
            frost_sensitive=_bool(r.frost_sensitive), winterkill_tmin=_opt_float(r.winterkill_tmin_c),
            extra_mm=float(r.extra_water_mm), latest_harvest=lh,
            second_crop=r.role == "second_crop", overwinter=_bool(r.overwinter), perennial=r.role == "perennial",
            family=r.family, legume=_bool(r.legume),
            sow_windows=_windows(r.sow_window), emergence_days=int(r.emergence_days),
        )
    return crops


CROPS: dict[str, Crop] = load_crops()
BASELINE = "cotton"  # water savings are reported against cotton
