# 🌾 DalaShift — what should I plant next season?

**NASA Space Apps Challenge 2026 · Challenge: _Field Shift_**

*Dala* means "field" in Uzbek. DalaShift shows a farmer in Uzbekistan how the climate of **their field**
has shifted between **1991–2005** and **2011–2026**. It then recommends crops and rotations that fit the
climate *now* and use less irrigation water than cotton.

The app is bilingual (English / Oʻzbekcha). It runs entirely on precomputed files and never calls a NASA API live.

## App screens

1. **Map**: click a field or district (Nukus, Urgench, Gulistan, Fergana, Karshi).
2. **Your field then vs now**: hot days, heat sum (growing degree days, GDD), frost dates, growing-season rain and water demand (ET0).
3. **Water stress now**: satellite layers from NASA SMAP root-zone soil moisture, ECOSTRESS Evaporative Stress Index (ESI) and HLS NDVI, via AppEEARS. Shows "coming soon" until the files are added.
4. **What to plant**: top-3 crop cards showing irrigation need (m³/ha), water saved vs cotton, and heat/frost risk flags. Also covers rotations, a shifted wheat sowing date, and the limits of the method.

## Method

All rules are transparent and live in [`dalashift/`](dalashift/). No machine learning is used.

| Step | What | Where |
|---|---|---|
| 1 | NASA POWER daily point data, `community=AG`, 1991-01-01 → 2026-10-31: `T2M_MAX, T2M_MIN, T2M, PRECTOTCORR, EVPTRNS, RH2M, WS2M, ALLSKY_SFC_SW_DWN` | `scripts/fetch_power.py` → `data/power/*.csv` |
| 2 | Climate shift per point, 1991–2005 vs 2011–2026: hot days (Tmax > 35 °C), GDD (base 10 °C), last spring / first autumn frost (Tmin ≤ 0 °C), Apr–Oct rain, **FAO-56 Penman-Monteith ET0** | `dalashift/et0.py`, `dalashift/climate.py` → `data/summary.json` |
| 3 | Crop engine for cotton, winter wheat, maize, rice, sorghum, sunflower, mung bean (2nd crop after wheat), melon and alfalfa | `dalashift/crops.py`, `dalashift/engine.py` → `data/recommendations.json` |

**Crop water need.** Net irrigation need = Σ(Kc × ET0) − effective rain, reported in m³/ha (1 mm = 10 m³/ha).
- Kc values follow the FAO-56 Table 12 curve (Kc_ini → Kc_mid → Kc_end), with stage lengths adapted from Table 11.
- Kc_mid and Kc_end are adjusted for local wind and humidity with FAO-56 Eq. 62.
- Effective rain uses the USDA-SCS monthly method (the FAO CROPWAT 8 default) and is capped at each month's crop water use.
- Rice adds a rough 500 mm for paddy soaking and percolation.

**Season fit.** A crop fits if both hold, using fixed typical sowing dates:
- its heat requirement (GDD) is met in ≥ 80 % of years (for winter wheat, counted up to a latest harvest of 10 Jul, because cool years ripen later rather than fail);
- in-season frost (frost-sensitive crops) hits ≤ 20 % of years.

**Winterkill (winter wheat) is a risk warning, not an exclusion.** The app shows the % of winters with air Tmin below
about −25 °C, an approximate limit for hardened winter wheat (snow cover often protects the crop). It lowers the score
slightly but never removes wheat, which is widely grown in Karakalpakstan and Khorezm.

**Heat risk.** The share of days in the flowering / grain-fill stage with Tmax above the crop's threshold: low < 15 %, medium 15–40 %, high > 40 %.

**Ranking.** Crops that fit come first, then they are ordered by `0.6 × fit score + 0.4 × water score`. The water score is 100 for no irrigation and 0 for the thirstiest crop.

**Rotations.**
- Winter wheat → mung bean: two harvests a year.
- Cotton → wheat + mung bean: the classic two-year order.
- Alfalfa (2 years) → cotton: restores soil.

**Shifted wheat sowing.** The engine tests sowing dates from 15 Sep to 15 Nov with GDD-driven phenology (base 0 °C; flowering at about 1800 °C·days, maturity at about 2550). The risk score adds:
- days above 32 °C during grain fill;
- frost near flowering;
- a penalty when warmth before winter falls outside 400–700 °C·days.

### Main reference
Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). *Crop evapotranspiration — Guidelines for computing crop water requirements.* **FAO Irrigation and Drainage Paper 56.** FAO, Rome.

## Limits (also shown in the app)

- **Coarse grid.** NASA POWER weather is about 50 km (MERRA-2, 0.5° × 0.625°). Field pairs at Urgench, Gulistan, Fergana and Karshi fall in the same grid cell, so they have identical climate.
- **Desert bias.** The reanalysis has no irrigation, so Tmax and ET0 over irrigated oases are likely 10–20 % too high. The modelled actual ET (`EVPTRNS`) is close to zero there, so it is stored but not used for crop water. Treat the m³/ha values as a tool for **comparing crops**.
- **Net need only.** Values are net crop water need. Gross field delivery is higher: furrow irrigation efficiency is about 50–60 %, and salt leaching needs extra water.
- **Rain QC.** A few implausible `PRECTOTCORR` spikes above 80 mm/day were removed (0–3 days per point).
- **No yield or market model.** GDD, heat-tolerance and frost thresholds are approximate, editable values in `crops.py`.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

To rebuild the data (needs internet, about 2 minutes):

```bash
python scripts/fetch_power.py      # STEP 1  (add --force to re-download)
python scripts/build_summary.py    # STEPS 2 + 3
```

## Deploy on Streamlit Community Cloud

1. Push this folder to a **public GitHub repo**, including `data/`. The app reads only `data/summary.json`, `data/recommendations.json`, `data/points.csv` and the optional `data/appeears/*.csv`.
2. On [share.streamlit.io](https://share.streamlit.io), click **New app**, choose the repo and branch, and set the main file to `app.py`.
3. No secrets or API keys are needed.

## Adding satellite water-stress data (AppEEARS)

1. Upload [`data/appeears_points.csv`](data/appeears_points.csv) to [NASA AppEEARS](https://appeears.earthdatacloud.nasa.gov/) as a **Point Sample** request.
2. Add these layers:
   - **SPL4SMGP**: `sm_rootzone`
   - **ECOSTRESS ESI**: `ESI` or `ESIavg`
   - **HLSL30 / HLSS30**: `B04` plus `B05` / `B8A` (NDVI is computed automatically), or an NDVI column
3. Put the output CSVs in `data/appeears/` and push. Rows are matched to fields by `ID`, or by the nearest lat/lon.

## Data credits

- **NASA POWER**: Prediction Of Worldwide Energy Resources, NASA Langley Research Center (LaRC), funded by the NASA Earth Science Applied Sciences Program. Data accessed via the POWER Daily API, `community=AG`, November 2026. https://power.larc.nasa.gov
  - Meteorology: GMAO MERRA-2. Solar radiation: CERES / GEWEX SRB. Corrected precipitation: `PRECTOTCORR` (MERRA-2 bias-corrected with IMERG).
- **NASA SMAP** L4 Global 3-hourly 9 km Surface and Root Zone Soil Moisture (SPL4SMGP), NSIDC DAAC.
- **NASA ECOSTRESS** Evaporative Stress Index, LP DAAC.
- **NASA/USGS Harmonized Landsat Sentinel-2 (HLS)**, LP DAAC.
- **NASA AppEEARS** (Application for Extracting and Exploring Analysis Ready Samples), LP DAAC.
- Basemaps: © OpenStreetMap contributors; Esri World Imagery.

*DalaShift is a decision-support prototype. Check recommendations with a local agronomist or water user association.*
