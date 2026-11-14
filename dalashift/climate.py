"""STEP 2 - Climate-shift indicators per field point (1991-2005 'then' vs 2011-2026 'now')."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .et0 import penman_monteith, rh_min

PERIODS = {"then": (1991, 2005), "now": (2011, 2026)}
HOT_TMAX = 35.0            # hot day threshold, degC
GDD_BASE = 10.0            # degC
FROST_TMIN = 0.0           # frost = Tmin <= 0 degC
GS_MONTHS = range(4, 11)   # growing season April-October
PRECIP_QC_MAX = 80.0       # mm/day; larger values in POWER PRECTOTCORR here are spurious spikes
LAMBDA = 2.45              # MJ/kg, latent heat -> EVPTRNS MJ/m2/day to mm/day


def load_point(path, lat: float, elev: float) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df = df.astype(float)
    # QC: drop physically implausible daily rain (treated as 0 / missing)
    bad = df["PRECTOTCORR"] > PRECIP_QC_MAX
    df["P_QC_FLAG"] = bad.astype(int)
    df.loc[bad, "PRECTOTCORR"] = np.nan
    df["P"] = df["PRECTOTCORR"].fillna(0.0)
    df["TMEAN"] = (df["T2M_MAX"] + df["T2M_MIN"]) / 2
    df["ET0"] = penman_monteith(df, lat, elev)
    df["RHMIN"] = rh_min(df)
    df["AET"] = df["EVPTRNS"] / LAMBDA  # MERRA-2 modelled actual ET, mm/day (no irrigation in model)
    return df


def _frost_dates(year_df: pd.DataFrame, complete_year: bool):
    """Last spring frost and first autumn frost as day-of-year (split at 1 July)."""
    frost = year_df["T2M_MIN"] <= FROST_TMIN
    spring = frost[year_df.index.month < 7]
    autumn = frost[year_df.index.month >= 7]
    last_spring = spring[spring].index.max().dayofyear if spring.any() else np.nan
    if autumn.any():
        first_autumn = autumn[autumn].index.min().dayofyear
    else:
        # no frost found: only meaningful if the whole year is in the record
        first_autumn = 366 if complete_year else np.nan
    return last_spring, first_autumn


def annual_indicators(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, g in df.groupby(df.index.year):
        complete = g.index.max() >= pd.Timestamp(year, 12, 31)
        gs = g[g.index.month.isin(GS_MONTHS)]
        ls, fa = _frost_dates(g, complete)
        rows.append({
            "year": year,
            "hot_days": int((g["T2M_MAX"] > HOT_TMAX).sum()),
            "gdd10": float(np.maximum(g["TMEAN"] - GDD_BASE, 0).sum()) if complete else np.nan,
            "gdd10_gs": float(np.maximum(gs["TMEAN"] - GDD_BASE, 0).sum()),
            "last_spring_frost": ls,
            "first_autumn_frost": fa,
            "frost_free_days": (fa - ls) if not (np.isnan(ls) or np.isnan(fa)) else np.nan,
            "gs_rain": float(gs["P"].sum()),
            "annual_rain": float(g["P"].sum()) if complete else np.nan,
            "gs_et0": float(gs["ET0"].sum()),
            "annual_et0": float(g["ET0"].sum()) if complete else np.nan,
            "summer_tmax": float(g.loc[g.index.month.isin([6, 7, 8]), "T2M_MAX"].mean()),
        })
    return pd.DataFrame(rows).set_index("year")


def period_mean(annual: pd.DataFrame, period: str) -> dict:
    a, b = PERIODS[period]
    sub = annual.loc[a:b]
    return {k: (None if np.isnan(v) else round(float(v), 1)) for k, v in sub.mean().items()}


def monthly_climatology(df: pd.DataFrame, period: str) -> dict:
    a, b = PERIODS[period]
    sub = df[(df.index.year >= a) & (df.index.year <= b)]
    out = {}
    for col, how in [("TMEAN", "mean"), ("T2M_MAX", "mean"), ("T2M_MIN", "mean"),
                     ("P", "sum"), ("ET0", "sum"), ("AET", "sum")]:
        m = sub[col].groupby([sub.index.year, sub.index.month]).agg(how)
        clim = m.groupby(level=1).mean()
        out[col] = [round(float(clim.get(i, np.nan)), 2) for i in range(1, 13)]
    return out


def doy_to_date(doy) -> str | None:
    if doy is None or (isinstance(doy, float) and np.isnan(doy)):
        return None
    d = pd.Timestamp(2001, 1, 1) + pd.Timedelta(days=int(round(doy)) - 1)
    return d.strftime("%d %b")
