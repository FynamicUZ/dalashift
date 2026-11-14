"""STEP 3 - Transparent rule-based crop recommendation engine (no ML).

For each field point, period ('then' / 'now'), crop and season-year:
  ETc   = sum(Kc(day) * ET0(day))              FAO-56 single crop coefficient approach (Eq. 56)
  Peff  = monthly effective rainfall            USDA-SCS method (FAO CROPWAT 8 default), capped at monthly ETc
  Need  = ETc - Peff + extra                    net irrigation need, mm  ->  x10 = m3/ha
  GDD   = sum(max(Tmean - Tbase, 0))            vs crop minimum  -> season fits?
  Frost = any Tmin <= 0 degC between emergence and harvest (frost-sensitive crops) / winterkill Tmin
  Sowing date = best date inside the crop's typical Uzbek sowing window(s) (config/crops.csv)
  Heat  = days with Tmax > crop threshold inside the mid (flowering / grain-fill) stage
Results are averaged over all season-years of the period.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .climate import PERIODS
from .crops import BASELINE, CROPS, Crop

FIT_GDD_PROB = 0.8     # season fits if GDD requirement is met in >= 80 % of years ...
FIT_FROST_PROB = 0.2   # ... and frost/winterkill hits <= 20 % of years


# ---------------------------------------------------------------- Kc helpers
def kc_adjust(kc: float, u2: float, rhmin: float, h: float) -> float:
    """FAO-56 Eq. 62 climatic adjustment of Kc_mid / Kc_end (only for Kc >= 0.45)."""
    if kc < 0.45:
        return kc
    u2 = float(np.clip(u2, 1, 6))
    rhmin = float(np.clip(rhmin, 20, 80))
    return kc + (0.04 * (u2 - 2) - 0.004 * (rhmin - 45)) * (h / 3) ** 0.3


def kc_curve(crop: Crop, kc_mid: float, kc_end: float) -> np.ndarray:
    li, ld, lm, ll = crop.stages
    kc = np.empty(crop.season_days)
    kc[:li] = crop.kc_ini
    kc[li:li + ld] = crop.kc_ini + (np.arange(1, ld + 1) / ld) * (kc_mid - crop.kc_ini)
    kc[li + ld:li + ld + lm] = kc_mid
    kc[li + ld + lm:] = kc_mid + (np.arange(1, ll + 1) / ll) * (kc_end - kc_mid)
    return kc


# ---------------------------------------------------------------- rainfall
def peff_month(p: float) -> float:
    """USDA-SCS effective rainfall for a monthly total P [mm] (default method in FAO CROPWAT 8)."""
    return p * (125 - 0.2 * p) / 125 if p <= 250 else 125 + 0.1 * p


def net_need(df: pd.DataFrame, s: pd.DataFrame, etc_daily: np.ndarray) -> tuple[float, float]:
    """Monthly water balance: Peff is pro-rated to the days in season and capped at that
    month's ETc (rain surplus is not counted). Returns (Peff used, net irrigation need) in mm."""
    monthly_p = df["P"].resample("MS").sum()
    etc = pd.Series(etc_daily, index=s.index)
    peff_used, need = 0.0, 0.0
    for m, etc_m in etc.groupby(etc.index.to_period("M")):
        ts = m.to_timestamp()
        frac = len(etc_m) / ts.days_in_month
        pe = min(peff_month(float(monthly_p.get(ts, 0.0))) * frac, float(etc_m.sum()))
        peff_used += pe
        need += float(etc_m.sum()) - pe
    return peff_used, need


# ---------------------------------------------------------------- one season
def sow_candidates(crop: Crop) -> list[tuple[int, int]]:
    """Sowing dates tried for a crop: every 5 days inside each typical sowing window (plus the
    window end). Crops without a window (winter cereals) keep their fixed typical date."""
    if not crop.sow_windows:
        return [crop.sow]
    out = []
    for a, b in crop.sow_windows:
        d0, d1 = pd.Timestamp(2001, *a), pd.Timestamp(2001, *b)
        days = list(pd.date_range(d0, d1, freq="5D"))
        if days[-1] != d1:
            days.append(d1)
        out += [(d.month, d.day) for d in days]
    return out


def season_years(crop: Crop, period: str, df: pd.DataFrame, sow_md: tuple[int, int] | None = None) -> list[int]:
    a, b = PERIODS[period]
    years = []
    for y in range(a, b + 1):
        start, end = season_window(crop, y, sow_md)
        if start >= df.index.min() and end <= df.index.max():
            years.append(y)
    return years


def season_window(crop: Crop, year: int, sow_md: tuple[int, int] | None = None):
    """Season keyed by harvest year (winter wheat sown in year-1). Returns (sowing, harvest)."""
    sow_year = year - 1 if crop.overwinter else year
    sow = pd.Timestamp(sow_year, *(sow_md or crop.sow))
    return sow, sow + pd.Timedelta(days=crop.season_days - 1)


def simulate_season(crop: Crop, df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    s = df.loc[start:end]
    li, ld, lm, ll = crop.stages
    mid = s.iloc[li + ld:li + ld + lm]
    late = s.iloc[li + ld + lm:]
    kc_mid = kc_adjust(crop.kc_mid, mid["WS2M"].mean(), mid["RHMIN"].mean(), crop.height_m)
    kc_end = kc_adjust(crop.kc_end, late["WS2M"].mean(), late["RHMIN"].mean(), crop.height_m)
    kc = kc_curve(crop, kc_mid, kc_end)[:len(s)]
    etc_daily = kc * s["ET0"].values
    etc = float(etc_daily.sum())
    peff, need = net_need(df, s, etc_daily)
    need += crop.extra_mm
    gdd_end = pd.Timestamp(end.year, *crop.latest_harvest) if crop.latest_harvest else end
    gdd = float(np.maximum(df.loc[start:gdd_end, "TMEAN"] - crop.gdd_base, 0).sum())
    # frost only damages the crop between EMERGENCE and harvest: before emergence the seed or
    # tuber is still in the soil (a frost then is not counted)
    emerged = s.iloc[crop.emergence_days:]
    frost = bool((emerged["T2M_MIN"] <= 0).any()) if crop.frost_sensitive else False
    # winterkill is a RISK warning (lowers the score), not an exclusion: snow cover and
    # hardening often protect the crop, and air Tmin is only a proxy for crown temperature
    winterkill = bool((s["T2M_MIN"] < crop.winterkill_tmin).any()) if crop.winterkill_tmin is not None else False
    heat = int((mid["T2M_MAX"] > crop.heat_tmax).sum())
    return {"etc": etc, "peff": peff, "need": need, "gdd": gdd, "frost": frost, "winterkill": winterkill,
            "heat_days": heat, "kc_mid_adj": kc_mid}


def heat_flag(heat_days: float, mid_len: int) -> str:
    frac = heat_days / mid_len
    return "low" if frac < 0.15 else ("medium" if frac < 0.40 else "high")


def evaluate_crop_at(crop: Crop, df: pd.DataFrame, period: str, sow_md: tuple[int, int]) -> dict:
    """All season-years of a period for ONE fixed sowing date (the same date every year)."""
    runs = [simulate_season(crop, df, *season_window(crop, y, sow_md))
            for y in season_years(crop, period, df, sow_md)]
    r = pd.DataFrame(runs)
    p_gdd = float((r["gdd"] >= crop.min_gdd).mean())
    p_frost = float(r["frost"].mean())
    p_winterkill = float(r["winterkill"].mean())
    heat_days = float(r["heat_days"].mean())
    mid_len = crop.stages[2]
    fits = p_gdd >= FIT_GDD_PROB and p_frost <= FIT_FROST_PROB
    # transparent fit score, 0-100
    fit_score = (100 - 50 * (1 - p_gdd) - 50 * p_frost - 25 * p_winterkill
                 - 60 * min(heat_days / mid_len, 0.5))
    sow, end = season_window(crop, 2001, sow_md)
    return {
        "crop": crop.key,
        "n_years": len(r),
        "sow": sow.strftime("%d %b"),
        "harvest": end.strftime("%d %b"),
        "sow_window": [[pd.Timestamp(2001, *a).strftime("%d %b"), pd.Timestamp(2001, *b).strftime("%d %b")]
                       for a, b in crop.sow_windows],
        "emergence_days": crop.emergence_days,
        "season_days": crop.season_days,
        "etc_mm": round(float(r["etc"].mean()), 0),
        "peff_mm": round(float(r["peff"].mean()), 0),
        "need_mm": round(float(r["need"].mean()), 0),
        "need_m3ha": int(round(float(r["need"].mean()) * 10, -1)),
        "gdd": round(float(r["gdd"].mean()), 0),
        "min_gdd": crop.min_gdd,
        "gdd_base": crop.gdd_base,
        "p_gdd_ok": round(p_gdd, 2),
        "p_frost": round(p_frost, 2),
        "p_winterkill": round(p_winterkill, 2),
        "winterkill_tmin": crop.winterkill_tmin,
        "heat_days": round(heat_days, 1),
        "heat_tmax": crop.heat_tmax,
        "heat_risk": heat_flag(heat_days, mid_len),
        "kc_mid_adj": round(float(r["kc_mid_adj"].mean()), 2),
        "fits": fits,
        "fit_score": round(max(fit_score, 0), 1),
        "second_crop": crop.second_crop,
    }


def evaluate_crop(crop: Crop, df: pd.DataFrame, period: str) -> dict:
    """Try every sowing date in the crop's typical window(s) and keep the best for this site:
    fits first, then highest fit score, then the date closest to the usual sowing date.
    ONE date is chosen for all years of the period (no hindsight per year)."""
    usual = pd.Timestamp(2001, *crop.sow)
    best, best_key = None, None
    for md in sow_candidates(crop):
        res = evaluate_crop_at(crop, df, period, md)
        key = (not res["fits"], -res["fit_score"], abs((pd.Timestamp(2001, *md) - usual).days))
        if best_key is None or key < best_key:
            best, best_key = res, key
    return best


def rank(results: dict[str, dict]) -> list[str]:
    """Fitting crops first, then by 0.6*fit + 0.4*water score (less water = better)."""
    main = {k: v for k, v in results.items() if not v["second_crop"]}
    max_need = max(v["need_m3ha"] for v in main.values()) or 1
    for v in results.values():
        v["water_score"] = round(100 * (1 - v["need_m3ha"] / max_need), 1)
        v["score"] = round(0.6 * v["fit_score"] + 0.4 * v["water_score"], 1)
        v["saved_vs_cotton_m3ha"] = results[BASELINE]["need_m3ha"] - v["need_m3ha"]
    return sorted(main, key=lambda k: (not main[k]["fits"], -main[k]["score"]))


# ---------------------------------------------------------------- wheat sowing shift
WHEAT_ANTHESIS_GDD = 1800   # degC-days base 0 from sowing (approx., winter wheat)
WHEAT_MATURITY_GDD = 2550
WHEAT_GRAINFILL_TMAX = 32
PREWINTER_GDD = (400, 700)  # good tillering + hardening before winter (approx.)


def wheat_sowing_shift(df: pd.DataFrame) -> dict:
    """Test sowing dates 15 Sep - 15 Nov with GDD-driven phenology; pick the lowest-risk one."""
    cands = pd.date_range("2001-09-15", "2001-11-15", freq="5D")
    out = {}
    for period in PERIODS:
        a, b = PERIODS[period]
        rows = []
        for c in cands:
            per_year = []
            for hy in range(a, b + 1):
                sow = pd.Timestamp(hy - 1, c.month, c.day)
                if sow < df.index.min():
                    continue
                s = df.loc[sow:pd.Timestamp(hy, 7, 31)]
                cum = np.maximum(s["TMEAN"], 0).cumsum()
                if cum.iloc[-1] < WHEAT_MATURITY_GDD:
                    continue
                anth = cum.index[np.argmax(cum.values >= WHEAT_ANTHESIS_GDD)]
                mat = cum.index[np.argmax(cum.values >= WHEAT_MATURITY_GDD)]
                prew = float(np.maximum(df.loc[sow:pd.Timestamp(hy - 1, 12, 31), "TMEAN"], 0).sum())
                heat = int((df.loc[anth:mat, "T2M_MAX"] > WHEAT_GRAINFILL_TMAX).sum())
                frost_fl = int((df.loc[anth - pd.Timedelta(days=7):anth + pd.Timedelta(days=7), "T2M_MIN"] <= 0).sum())
                lo, hi = PREWINTER_GDD
                pen = max(lo - prew, 0) / 25 + max(prew - hi, 0) / 25
                per_year.append({"anth_doy": anth.dayofyear, "mat_doy": mat.dayofyear, "prewinter": prew,
                                 "heat": heat, "frost": frost_fl, "risk": heat + 2 * frost_fl + pen})
            if not per_year:
                continue
            py = pd.DataFrame(per_year)
            rows.append({"sow": c.strftime("%d %b"), "sow_doy": c.dayofyear,
                         "risk": round(py["risk"].mean(), 2), "heat_days": round(py["heat"].mean(), 1),
                         "frost_days": round(py["frost"].mean(), 1),
                         "prewinter_gdd": round(py["prewinter"].mean(), 0),
                         "anthesis_doy": round(py["anth_doy"].mean(), 0),
                         "maturity_doy": round(py["mat_doy"].mean(), 0)})
        table = pd.DataFrame(rows)
        best = table.loc[table["risk"].idxmin()].to_dict()
        conv = table.loc[table["sow"] == pd.Timestamp(2001, *CROPS["winter_wheat"].sow).strftime("%d %b")]
        out[period] = {"table": table.to_dict(orient="records"), "best": best,
                       "conventional": conv.iloc[0].to_dict() if len(conv) else None}
    return out


# ---------------------------------------------------------------- rotations
def rotations(res_now: dict, res_then: dict) -> list[dict]:
    ww, mb, al = res_now["winter_wheat"], res_now["mung_bean"], res_now["alfalfa"]
    cot = res_now[BASELINE]
    rots = [
        {"key": "wheat_mung", "crops": ["winter_wheat", "mung_bean"],
         "need_m3ha": ww["need_m3ha"] + mb["need_m3ha"],
         "fits": ww["fits"] and mb["fits"], "harvests_per_year": 2,
         "heat_risk": max([ww["heat_risk"], mb["heat_risk"]], key=["low", "medium", "high"].index)},
        # classic Uzbek 2-year order: cotton, then wheat + mung bean; water shown per year
        {"key": "cotton_wheat_mung", "crops": ["cotton", "winter_wheat", "mung_bean"],
         "need_m3ha": int(round((cot["need_m3ha"] + ww["need_m3ha"] + mb["need_m3ha"]) / 2, -1)),
         "fits": cot["fits"] and ww["fits"] and mb["fits"], "harvests_per_year": 1.5,
         "heat_risk": cot["heat_risk"]},
        {"key": "alfalfa_cotton", "crops": ["alfalfa", "cotton"],
         "need_m3ha": int(round((2 * al["need_m3ha"] + cot["need_m3ha"]) / 3, -1)),
         "fits": al["fits"] and cot["fits"], "harvests_per_year": 1,
         "heat_risk": cot["heat_risk"]},
    ]
    for r in rots:
        r["saved_vs_cotton_m3ha"] = cot["need_m3ha"] - r["need_m3ha"]
    return rots


def recommend_point(df: pd.DataFrame) -> dict:
    out = {"crops": {}, "ranking": {}}
    for period in PERIODS:
        res = {k: evaluate_crop(c, df, period) for k, c in CROPS.items()}
        out["ranking"][period] = rank(res)
        out["crops"][period] = res
    out["rotations"] = rotations(out["crops"]["now"], out["crops"]["then"])
    out["wheat_sowing"] = wheat_sowing_shift(df)
    return out
