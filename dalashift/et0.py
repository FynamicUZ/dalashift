"""FAO-56 Penman-Monteith reference evapotranspiration from NASA POWER daily variables.

Reference: Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998).
Crop evapotranspiration - Guidelines for computing crop water requirements.
FAO Irrigation and Drainage Paper 56. Rome: FAO.  (equation numbers below refer to it)

Inputs (POWER, community=AG):
  T2M_MAX, T2M_MIN [degC], RH2M [%], WS2M [m/s at 2 m],
  ALLSKY_SFC_SW_DWN [MJ/m2/day], site elevation [m], latitude [deg].
"""
from __future__ import annotations

import numpy as np
import pandas as pd

GSC = 0.0820          # solar constant, MJ m-2 min-1
SIGMA = 4.903e-9      # Stefan-Boltzmann, MJ K-4 m-2 day-1
ALBEDO = 0.23         # grass reference


def sat_vp(t):
    """Saturation vapour pressure e°(T) [kPa] - Eq. 11."""
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def extraterrestrial_radiation(doy, lat_deg):
    """Ra [MJ m-2 day-1] - Eqs. 21-25."""
    phi = np.deg2rad(lat_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)                  # Eq. 23
    delta = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)            # Eq. 24
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1, 1))   # Eq. 25
    return (24 * 60 / np.pi) * GSC * dr * (
        ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws)
    )


def penman_monteith(df: pd.DataFrame, lat: float, elev: float) -> pd.Series:
    """Daily ET0 [mm/day] - FAO-56 Eq. 6, with daily time step (G ~ 0, Eq. 42)."""
    tmax, tmin = df["T2M_MAX"], df["T2M_MIN"]
    tmean = (tmax + tmin) / 2                                       # Eq. 9
    rh = df["RH2M"].clip(1, 100)
    u2 = df["WS2M"].clip(lower=0.5)                                 # FAO-56 recommends u2 >= 0.5 m/s
    rs = df["ALLSKY_SFC_SW_DWN"]

    p = 101.3 * ((293 - 0.0065 * elev) / 293) ** 5.26               # Eq. 7
    gamma = 0.000665 * p                                            # Eq. 8
    es = (sat_vp(tmax) + sat_vp(tmin)) / 2                          # Eq. 12
    ea = rh / 100 * es                                              # Eq. 19 (RHmean variant)
    delta = 4098 * sat_vp(tmean) / (tmean + 237.3) ** 2             # Eq. 13

    doy = df.index.dayofyear.values
    ra = extraterrestrial_radiation(doy, lat)
    rso = (0.75 + 2e-5 * elev) * ra                                 # Eq. 37
    rns = (1 - ALBEDO) * rs                                         # Eq. 38
    rs_rso = np.clip(rs / rso, 0.25, 1.0)
    rnl = SIGMA * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2 \
        * (0.34 - 0.14 * np.sqrt(ea)) * (1.35 * rs_rso - 0.35)      # Eq. 39
    rn = rns - rnl                                                  # Eq. 40
    g = 0.0

    et0 = (0.408 * delta * (rn - g) + gamma * 900 / (tmean + 273) * u2 * (es - ea)) / (
        delta + gamma * (1 + 0.34 * u2)
    )
    return et0.clip(lower=0).rename("ET0")


def rh_min(df: pd.DataFrame) -> pd.Series:
    """Approximate daily RHmin [%] from mean RH: ea / e°(Tmax). Used for FAO-56 Kc climate adjustment."""
    es = (sat_vp(df["T2M_MAX"]) + sat_vp(df["T2M_MIN"])) / 2
    ea = df["RH2M"].clip(1, 100) / 100 * es
    return (100 * ea / sat_vp(df["T2M_MAX"])).clip(1, 100)
