"""NASA SMAP L4 root-zone soil moisture (SPL4SMGP, via AppEEARS) -> simple per-field facts.

SMAP L4 is a 9 km model + satellite product (3-hourly). It does NOT simulate irrigation, so over an
irrigated field it shows how dry the land is *without* canal water: i.e. how much the field depends
on irrigation in summer. DalaShift uses it as information and validation only; it does not change
the crop recommendations.
"""
from __future__ import annotations

import pandas as pd

SPRING, SUMMER = (3, 4), (7, 8)


def daily(appeears: pd.DataFrame, point: str) -> pd.Series:
    """Daily mean root-zone soil moisture (m3/m3) for one field; empty if no SMAP data."""
    if appeears is None or appeears.empty:
        return pd.Series(dtype=float)
    sm = appeears[(appeears["var"] == "sm") & (appeears["point"] == point)]
    if sm.empty:
        return pd.Series(dtype=float)
    d = pd.to_datetime(sm["date"])
    if getattr(d.dt, "tz", None) is not None:
        d = d.dt.tz_localize(None)
    return sm.assign(day=d.dt.normalize()).groupby("day")["value"].mean().sort_index()


def summary(appeears: pd.DataFrame, point: str) -> dict | None:
    """Spring (Mar-Apr) vs summer (Jul-Aug) root-zone soil moisture in the latest year that has both,
    plus the latest value and a weekly series for charts."""
    s = daily(appeears, point)
    if s.empty:
        return None
    for year in sorted(set(s.index.year), reverse=True):
        y = s[s.index.year == year]
        spring, summer = y[y.index.month.isin(SPRING)], y[y.index.month.isin(SUMMER)]
        if len(spring) >= 30 and len(summer) >= 30:
            sp, su = float(spring.mean()), float(summer.mean())
            weekly = s.resample("W").mean().dropna()
            return {"year": int(year), "spring": round(sp, 3), "summer": round(su, 3),
                    "drop_pct": round(100 * (1 - su / sp)), "latest_date": s.index[-1].strftime("%Y-%m-%d"),
                    "latest": round(float(s.iloc[-1]), 3), "first_date": s.index[0].strftime("%Y-%m-%d"),
                    "weekly_dates": [d.strftime("%Y-%m-%d") for d in weekly.index],
                    "weekly": [round(float(v), 4) for v in weekly.values]}
    return None
