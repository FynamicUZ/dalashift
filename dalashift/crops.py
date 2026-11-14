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

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

CROPS_CSV = Path(__file__).resolve().parents[1] / "config" / "crops.csv"


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


def load_crop_table(path: Path = CROPS_CSV) -> pd.DataFrame:
    return pd.read_csv(path, keep_default_na=True).set_index("crop", drop=False)


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
