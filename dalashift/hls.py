"""NASA/USGS HLS NDVI (HLSL30_VI + HLSS30_VI, via AppEEARS) -> per-field greenness curve and season.

The VI products already mask clouds/shadow with Fmask (masked pixels arrive as fill values and are
dropped by dalashift.appeears). Landsat (L30) and Sentinel-2 (S30) values are merged per day
(median), resampled weekly and smoothed with a 3-week rolling median.

Used to sanity-check the crop calendars (winter crops peak in spring, summer crops in mid-summer),
not to change recommendations.
"""
from __future__ import annotations

import pandas as pd

SPRING, SUMMER = (3, 4, 5), (6, 7, 8, 9)
GREEN = 0.5   # NDVI above this = a crop is clearly growing


def weekly(appeears: pd.DataFrame, point: str) -> pd.Series:
    if appeears is None or appeears.empty:
        return pd.Series(dtype=float)
    n = appeears[(appeears["var"] == "ndvi") & (appeears["point"] == point)]
    if n.empty:
        return pd.Series(dtype=float)
    day = pd.to_datetime(n["date"]).dt.normalize()
    s = n.assign(day=day).groupby("day")["value"].median().sort_index()
    return s.resample("7D").median().interpolate(limit=3).rolling(3, center=True, min_periods=1).median().dropna()


def season(year_series: pd.Series) -> dict:
    """Peak date/value and which season(s) were green in one year."""
    spring = year_series[year_series.index.month.isin(SPRING)]
    summer = year_series[year_series.index.month.isin(SUMMER)]
    sp, su = (spring.max() if len(spring) else 0.0), (summer.max() if len(summer) else 0.0)
    kind = ("two_crops" if sp >= GREEN and su >= GREEN else "winter_crop" if sp >= GREEN
            else "summer_crop" if su >= GREEN else "low")
    peak = year_series.idxmax()
    return {"peak_date": peak.strftime("%Y-%m-%d"), "peak_month": int(peak.month), "peak": round(float(year_series.max()), 2),
            "spring_max": round(float(sp), 2), "summer_max": round(float(su), 2), "kind": kind}


MONTH_LOC = {"uz": ["yanvarda", "fevralda", "martda", "aprelda", "mayda", "iyunda", "iyulda", "avgustda", "sentyabrda",
                    "oktyabrda", "noyabrda", "dekabrda"],
             "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                    "November", "December"]}
LINE = {
    "summer_crop": {"uz": "NASA/USGS HLS sunʼiy yoʻldoshi: {y} yilda dalangiz {m} eng yashil boʻldi — yozgi ekin (masalan, paxta) belgisi.",
                    "en": "NASA/USGS HLS satellites: in {y} your field was greenest in {m}, the sign of a summer crop (e.g. cotton)."},
    "winter_crop": {"uz": "NASA/USGS HLS sunʼiy yoʻldoshi: {y} yilda dalangiz {m} eng yashil boʻldi — kuzgi ekin (masalan, bugʻdoy) belgisi.",
                    "en": "NASA/USGS HLS satellites: in {y} your field was greenest in {m}, the sign of a winter crop (e.g. wheat)."},
    "two_crops": {"uz": "NASA/USGS HLS sunʼiy yoʻldoshi: {y} yilda dala bahorda ham, yozda ham yashil boʻldi — bir yilda ikki hosil belgisi.",
                  "en": "NASA/USGS HLS satellites: in {y} the field was green in spring and again in summer, the sign of two harvests in one year."},
    "low": {"uz": "NASA/USGS HLS sunʼiy yoʻldoshi: {y} yilda dala deyarli yashillanmadi.",
            "en": "NASA/USGS HLS satellites: in {y} the field hardly turned green."},
}


def farmer_line(hs: dict | None, lang: str) -> str:
    if not hs:
        return ""
    return LINE[hs["kind"]][lang].format(y=hs["latest_year"], m=MONTH_LOC[lang][hs["peak_month"] - 1])


def summary(appeears: pd.DataFrame, point: str) -> dict | None:
    s = weekly(appeears, point)
    if len(s) < 10:
        return None
    years = {}
    for y in sorted(set(s.index.year)):
        ys = s[s.index.year == y]
        if len(ys) >= 20:          # at least ~5 months of data
            years[int(y)] = season(ys)
    if not years:
        return None
    # the current year counts only once its summer is covered
    latest = max(y for y in years if y < max(years) or s.index.max().month >= 9)
    return {"latest_year": latest, **years[latest], "years": years,
            "weekly_dates": [d.strftime("%Y-%m-%d") for d in s.index], "weekly": [round(float(v), 3) for v in s.values]}
