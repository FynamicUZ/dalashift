"""Crop parameter table used by the DalaShift rule engine.

Sources
-------
* Kc_ini / Kc_mid / Kc_end and maximum crop height h:
    FAO-56, Table 12 (Allen et al., 1998, FAO Irrigation and Drainage Paper 56).
    Kc_mid and Kc_end are later adjusted for the local climate with FAO-56 Eq. 62
    (wind speed u2 and minimum relative humidity RHmin), see engine.py.
* Stage lengths L_ini / L_dev / L_mid / L_late [days]:
    FAO-56, Table 11, adapted to typical Uzbek sowing calendars.
* GDD requirement, base temperature, heat threshold and frost behaviour are NOT from FAO-56.
  They are approximate agronomic thresholds (general crop-physiology literature and
  common Uzbek practice) and are kept deliberately simple and visible so judges and
  agronomists can change them.

Sowing dates are the conventional ones for irrigated lowland Uzbekistan.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Crop:
    key: str
    sow: tuple[int, int]               # (month, day); winter wheat is sown in the previous year
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

    @property
    def season_days(self) -> int:
        return sum(self.stages)


CROPS: dict[str, Crop] = {
    # Cotton - FAO-56 T11 (30/50/60/55, Mar-Apr sowing, arid regions); T12 Kc 0.35/1.15-1.20/0.70-0.50, h 1.2-1.5 m
    "cotton": Crop("cotton", (4, 15), (30, 50, 60, 55), 0.35, 1.18, 0.60, 1.35,
                   gdd_base=10, min_gdd=1900, heat_tmax=38, frost_sensitive=True),
    # Winter wheat - FAO-56 T11 (long initial stage incl. winter dormancy); T12 Kc 0.4 (frozen soil)/1.15/0.25-0.4, h 1 m
    "winter_wheat": Crop("winter_wheat", (10, 10), (130, 50, 40, 25), 0.40, 1.15, 0.30, 1.0,
                         gdd_base=0, min_gdd=2000, heat_tmax=32, frost_sensitive=False,
                         # approx. lethal AIR Tmin for hardened winter wheat (risk warning only)
                         winterkill_tmin=-25, overwinter=True, latest_harvest=(7, 10)),
    # Maize (grain) - FAO-56 T11 (30/40/50/30); T12 Kc 0.30/1.20/0.60-0.35, h 2 m
    "maize": Crop("maize", (4, 25), (30, 40, 50, 30), 0.30, 1.20, 0.50, 2.0,
                  gdd_base=10, min_gdd=1500, heat_tmax=35, frost_sensitive=True),
    # Rice (paddy) - FAO-56 T11 (30/30/60/30); T12 Kc 1.05/1.20/0.90-0.60, h 1 m
    "rice": Crop("rice", (5, 10), (30, 30, 60, 30), 1.05, 1.20, 0.75, 1.0,
                 gdd_base=10, min_gdd=1600, heat_tmax=35, frost_sensitive=True,
                 extra_mm=500),  # rough paddy losses (land soaking + percolation), not FAO-56
    # Sorghum (grain) - FAO-56 T11 (20/35/40/30); T12 Kc 0.30/1.00-1.10/0.55, h 1-2 m
    "sorghum": Crop("sorghum", (5, 1), (20, 35, 40, 30), 0.30, 1.05, 0.55, 1.5,
                    gdd_base=10, min_gdd=1300, heat_tmax=40, frost_sensitive=True),
    # Sunflower - FAO-56 T11 (25/35/45/25); T12 Kc 0.35/1.0-1.15/0.35, h 2 m
    "sunflower": Crop("sunflower", (4, 15), (25, 35, 45, 25), 0.35, 1.05, 0.35, 2.0,
                      gdd_base=10, min_gdd=1100, heat_tmax=37, frost_sensitive=True),
    # Mung bean (2nd crop after wheat) - FAO-56 T11 dry beans (15/25/35/20 class); T12 mung beans Kc 0.40/1.05/0.35, h 0.4 m
    "mung_bean": Crop("mung_bean", (6, 25), (15, 25, 30, 20), 0.40, 1.05, 0.35, 0.4,
                      gdd_base=10, min_gdd=900, heat_tmax=40, frost_sensitive=True,
                      second_crop=True),
    # Melon - FAO-56 T11 (25/35/40/20); T12 melons Kc 0.50/1.05/0.75, h 0.4 m
    "melon": Crop("melon", (4, 25), (25, 35, 40, 20), 0.50, 1.05, 0.75, 0.4,
                  gdd_base=10, min_gdd=1200, heat_tmax=40, frost_sensitive=True),
    # Alfalfa (hay, established stand) - FAO-56 T12 "averaged cutting effects" Kc 0.40/0.95/0.90, h 0.7 m
    "alfalfa": Crop("alfalfa", (3, 20), (10, 30, 165, 20), 0.40, 0.95, 0.90, 0.7,
                    gdd_base=5, min_gdd=1000, heat_tmax=38, frost_sensitive=False,
                    perennial=True),
}

BASELINE = "cotton"  # water savings are reported against cotton
