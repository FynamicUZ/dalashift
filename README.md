# 🌾 DalaShift — a 5-year crop rotation planner for Uzbek fields

**NASA Space Apps Challenge 2026 · Challenge: _Field Shift_**

> *Don't just choose the most profitable crop for this year. Choose the best five-year future for your field.*

*Dala* means "field" in Uzbek. DalaShift shows a farmer in Uzbekistan how the climate of **their field**
has shifted between **1991–2005** and **2011–2026** (NASA POWER). It then builds a **5-year crop rotation plan**
that fits the climate *now*, stays within the farm's irrigation water, and follows simple rotation rules.

The app is bilingual (English / Oʻzbekcha). It runs entirely on precomputed files and never calls a NASA API live.

## Team KarPS

Ahmedov Zuhriddin · Alisherov Azimbek · Shermaxmatov Ozodbek · Botirxonov Faxriyor · Boyqulov Afzalbek
(NASA Space Apps Challenge 2026, Karshi local event)

## App screens

The app opens on a simple **Farmer view** ([`dalashift/simple_ui.py`](dalashift/simple_ui.py); screenshots in [`docs/screenshots/`](docs/screenshots/)), a calm field-card + plan layout (Inter font, Lucide SVG icons, no emoji):
1. *Dalangiz qayerda?*: district (Qarshi, Fargʻona, Urganch, Nukus, Guliston), a field card with three facts (very hot days then → now with a 35-year sparkline, season rain then → now, the farm's water), a small map, and two controls: water *Kam / Oʻrtacha / Koʻp* (6,000 / 8,000 / 12,000 m³/ha, hypothetical levels) and *must grow cotton/wheat* (2 of 5 years each; its cost is shown in soʻm).
2. *Keyingi besh yil uchun reja*: plan choice *Daromad / Muvozanat / Suv tejash*; a 5-year timeline (crop, sowing → harvest month, water bar against the farm's water); ONE conservative income figure (the low end of the ±15 % estimate, rounded down to 0.5 mln soʻm, labelled *taxminan, ehtiyotkor hisob*); and a comparison with **your usual rotation** ([`dalashift/baseline.py`](dalashift/baseline.py): winter wheat ↔ cotton, or ↔ maize / barley where cotton / maize needs more water than the farm has): income %, water %, risk level.
3. *Nega bu reja?*: a short plain-language paragraph built from the plan.

No jargon on farmer screens (no ET0, GDD, NDVI, m³/ha or USD), checked by tests. Same engine and numbers as the expert view.

**Expert view:**

1. **Map**: click a field or district (Nukus, Urgench, Gulistan, Fergana, Karshi, Navoi). Dashed boxes show the NASA POWER grid cells.
2. **Your field then vs now**: hot days, heat sum (growing degree days, GDD), frost dates, growing-season rain and water demand (ET0).
3. **Water stress now**: satellite layers from NASA SMAP root-zone soil moisture, ECOSTRESS Evaporative Stress Index (ESI) and HLS NDVI, via AppEEARS. Shows "coming soon" until the files are added.
4. **What to plant**: top-3 crop cards showing irrigation need (m³/ha), water saved vs cotton, and heat/frost risk flags. Also covers rotations, a shifted wheat sowing date, and the limits of the method.
5. **5-Year Planner**:
   - a Year 1–5 timeline of crop cards showing profit, water and risk;
   - a comparison of three plans ("Most profit", "Balanced", "Least water") against simply repeating the most profitable crop;
   - plain-language reasons why each crop was chosen and why the others were rejected;
   - the cost of a "must grow cotton / wheat" obligation;
   - a stress test under "Hotter (+1.5 °C)" and "Less water (−20 %)".
   - It also has two demo farms, **Karshi** (Kashkadarya: hot cotton-and-wheat district, ~8,000 m³/ha) and **Fergana** (good water). Their inputs are hypothetical, clearly labelled and editable in the app.

## Method

All rules are transparent and live in [`dalashift/`](dalashift/) and [`config/`](config/). No machine learning is used.

| Step | What | Where |
|---|---|---|
| 1 | NASA POWER daily point data, `community=AG`, 1991-01-01 → 2026-10-31: `T2M_MAX, T2M_MIN, T2M, PRECTOTCORR, EVPTRNS, RH2M, WS2M, ALLSKY_SFC_SW_DWN` | `scripts/fetch_power.py` → `data/power/*.csv` |
| 2 | Climate shift per point, 1991–2005 vs 2011–2026: hot days (Tmax > 35 °C), GDD (base 10 °C), last spring / first autumn frost (Tmin ≤ 0 °C), Apr–Oct rain, **FAO-56 Penman-Monteith ET0** | `dalashift/et0.py`, `dalashift/climate.py` → `data/summary.json` |
| 3 | Crop engine (Climate Fit, water need, heat risk) for 14 approved crops | `config/crops.csv`, `dalashift/engine.py` → `data/recommendations.json` |
| 4 | Planner inputs: crop metrics under baseline climate and +1.5 °C | `scripts/build_summary.py` → `data/planner.json` |
| 5 | 5-year rotation optimizer | `config/rotation_rules.yaml`, `config/planner.yaml`, `dalashift/planner.py` |

### Crop engine (unchanged scoring)

**Crop water need.** Net irrigation need = Σ(Kc × ET0) − effective rain, reported in m³/ha (1 mm = 10 m³/ha).
- Kc values follow the FAO-56 Table 12 curve (Kc_ini → Kc_mid → Kc_end), with stage lengths adapted from Table 11.
- Kc_mid and Kc_end are adjusted for local wind and humidity with FAO-56 Eq. 62.
- Effective rain uses the USDA-SCS monthly method (the FAO CROPWAT 8 default) and is capped at each month's crop water use.
- Rice adds a rough 500 mm for paddy soaking and percolation.

**Sowing window.** Each crop has a typical Uzbek sowing window in `config/crops.csv` (cotton 1–20 April; potato 1–20 March **or** a summer planting 25 June–15 July; maize 10 April–10 May; …). The engine tries every 5th day in the window and keeps, per site, the date with the best Climate Fit (ties → closest to the usual date). One date is used for all years of the period, so there is no hindsight. Winter cereals keep a fixed date (see the wheat sowing-shift chart).

**Climate Fit.** A crop fits if both hold:
- its heat requirement (GDD) is met in ≥ 80 % of years (winter cereals are counted up to a latest harvest date, because cool years ripen later rather than fail);
- frost (Tmin ≤ 0 °C) between **emergence and harvest** hits ≤ 20 % of years (frost-sensitive crops). Frost between sowing and emergence (`emergence_days`, e.g. cotton 10 d, potato 21 d) is not counted: the seed or tuber is still in the soil.

**Winterkill (winter wheat, barley) is a risk warning, not an exclusion.** The app shows the % of winters with air Tmin below
an approximate limit (−25 °C for hardened winter wheat). This lowers the score slightly but never removes wheat,
which is widely grown in Karakalpakstan and Khorezm.

**Heat risk.** The share of days in the flowering / grain-fill stage with Tmax above the crop's threshold: low < 15 %, medium 15–40 %, high > 40 %.

**Ranking (screen 4).** Crops that fit come first, then they are ordered by `0.6 × fit score + 0.4 × water score`.

### Crop database — [`config/crops.csv`](config/crops.csv)

There are 14 approved crops: cotton, winter wheat, barley, maize, rice, sorghum, sunflower, mung bean (only as a 2nd crop after wheat), chickpea, potato, onion, tomato, melon and alfalfa.
**Melon is excluded from the 5-year planner** (`planner_enabled = False`): many varieties with different soil/season needs and no reliable farm-gate price; future work. Its data stay in the table and on screen 4 for reference.

Each crop has: family, season window (sowing date + FAO-56 stage lengths), GDD needed, heat tolerance, frost sensitivity, winterkill,
salinity tolerance, FAO-56 Kc values, typical yield, price, cost and `local_market_tag`.
**Every value group carries `_status` (`documented` or `approximate`), `_source` and `_date`.**

| Value | Source | Status |
|---|---|---|
| Kc, crop height | FAO-56 Table 12 (1998) | documented |
| Stage lengths | FAO-56 Table 11, adapted to Uzbek calendar | approximate |
| Salinity threshold ECe | FAO-29 Table 4 (Ayers & Westcot 1985); Maas (1990) for sunflower / mung bean | documented / approximate |
| Yield (t/ha) | FAOSTAT QCL, Uzbekistan, mean 2022–2024 (11 crops) | documented |
| Producer price (USD/t) | FAOSTAT PP, Uzbekistan, mean 2023–2024 (10 crops; 2022 excluded because of a series break) | documented |
| Melon, chickpea, mung bean prices | proxies: FAOSTAT "Watermelons" / "Peas, dry" | approximate |
| Mung bean (2nd crop) and alfalfa yield; alfalfa price | DalaShift assumptions | approximate |
| **Costs per ha** | DalaShift placeholders — **no published farm budget used** | approximate |
| GDD, heat, frost thresholds, sowing dates | general agronomic literature / Uzbek practice | approximate |

FAOSTAT extracts are saved in [`data/faostat/`](data/faostat/) and are reproduced by `scripts/fetch_faostat.py`. A test checks that every documented value in `crops.csv` matches them.

### Rotation rules — [`config/rotation_rules.yaml`](config/rotation_rules.yaml)

Hard rules (a plan that breaks one is rejected):
- no more than **2 years of cotton in a row**;
- no **same botanical family 3 years running** (a multi-year alfalfa stand is exempt);
- **winter wheat → mung bean** double crop allowed in the same year;
- **alfalfa is multi-year**: a stand lasts 2–3 years (a stand started in year 5 may continue after the plan).

Soft rule (a plan that breaks it is allowed but scores lower):
- a **legume break** (chickpea, mung bean or alfalfa) at least once in 5 years: −3 rotation-health points if missing (and no after-legume yield bonus).

**Rotation health (0–10)** = 10 − 3 if no legume year − 1 per same crop in consecutive years − 1 if only one legume year − 1 if < 4 plant families − 1 more if < 3 families
(− 3 per broken hard rule, which only affects the comparison plan). This is a **rule score instead of a soil-carbon model**.

**Rotation effects on yield** (approximate, editable): −10 % per consecutive repeat of the same crop (max −30 %); +10 % after a legume; +15 % after alfalfa; the alfalfa establishment year yields half.

### Water budget, economics and the optimizer — [`dalashift/planner.py`](dalashift/planner.py)

```
expected yield_t   = FAOSTAT yield × climate factor × rotation effect_t
climate factor     = (1 − heat loss[low 0 | medium 0.10 | high 0.20])
                     × (1 − 0.5 × P(frost)) × (1 − 0.5 × P(winterkill)) × (1 − 0.5 × P(GDD short))
profit_t           = Σ crops in year t (expected yield × price) − Σ costs                [USD/ha]
discounted profit  = Σ_{t=1..5} profit_t / (1 + r)^t          r = 10 % (editable)
water              = Σ_{t=1..5} net irrigation need_t                                    [m³/ha]
feasible           ⇔ every crop passes Climate Fit, need_t ≤ budget in EVERY year, all hard rules hold,
                     fresh-market crops ≤ limit, each crop ≤ its max share of farm area,
                     and "must grow" minimums are met
```

**Money realism.** Costs per ha are placeholders, so the app never shows a single profit number:
- tomato, onion, potato and maize yields are FAOSTAT national averages (intensive farms included), so they are multiplied by an **open-field realism factor of 0.7** (approximate, `yield_realism_factor` / `yield_realism_crops` in `config/planner.yaml`);
- cotton uses the FAOSTAT producer price **plus the 2025 state subsidy of 1,000 so'm/kg** (`config/local_prices.csv`). Even so, cotton's margin stays low, which matches the real debate about cotton profitability for farmers;
- every profit is an **estimate range**, low = 0.85 × profit, high = 1.15 × profit (`money.profit_uncertainty` in `config/planner.yaml`);
- each plan shows the **average profit per ha per year** next to the **5-year total** (the discounted value, used to rank plans, is in the tooltip);
- any crop margin above **3,000 USD/ha/year** is flagged **"check this number"** (`money.margin_check_usd_ha`);
- **max share of farm area** per crop (`max_area_share` in `config/crops.csv`): tomato, potato, onion and melon ≤ 25 %. The farm is assumed to run the plan on 5 blocks, each one year behind the next, so a crop grown k of 5 years covers k/5 of the farm every year; 25 % therefore means at most 1 year in 5 per fresh-market crop. **Legumes** (chickpea, mung bean, alfalfa) are provisionally capped at **40 %** (2 years in 5) because their prices are proxies.

**Local prices.** [`config/local_prices.csv`](config/local_prices.csv) (`crop,price_usd_per_t,source,date`) overrides the FAOSTAT/proxy price for any crop listed. It ships with headers only.

**Retail prices (manual entry).** [`config/retail_prices.csv`](config/retail_prices.csv) (`crop,retail_uzs_per_kg,where,date`) has rows for chickpea, mung bean, tomato, onion, potato, carrot and melon with **empty prices**: fill them in from a store or bazaar visit. A filled row becomes the crop price:
`farm-gate USD/t = retail so'm/kg × farm_gate_share × 1000 ÷ uzs_per_usd`, with `farm_gate_share` = 0.40 by default (*approximate, retail-to-farm-gate assumption*, editable per crop) and `uzs_per_usd` set in [`config/retail_to_farmgate.yaml`](config/retail_to_farmgate.yaml). **`uzs_per_usd` is a placeholder (empty): set the current rate and its date first**; until then retail prices are ignored with a warning. Precedence: `local_prices.csv` > retail > FAOSTAT. Empty rows keep FAOSTAT. Cotton and wheat are not retail goods and keep FAOSTAT prices; carrot is recorded but is not a planner crop.

**Brute force.** The year options are every crop that passes Climate Fit and fits the water budget, plus the wheat→mung bean double crop. The planner enumerates **all** 5-year sequences of those options (at most 14⁵ = 537,824) as numpy arrays and evaluates every one; nothing is sampled.
- **Most profit**: the highest discounted profit.
- **Least water**: the lowest total water; ties are broken by profit.
- **Balanced**: the highest equal-weight sum of normalised profit + normalised water saving + health/10.

**No plan meets every rule.** The app says so and shows the **least-harmful plan**: from all sequences of climate-fit crops (even ones over budget) it picks the one that breaks the fewest hard rules, then needs the least water over budget, then earns the most, and lists exactly which rules it breaks. It also lists the crops that pass Climate Fit and the budget, the share of sequences each rule breaks, and which single rule (if any) would need relaxing.

**Must grow cotton / wheat.** A minimum % of years is turned into a minimum number of years. The planner is re-run without the obligation, and the difference is shown as the cost of the constraint (lost profit, extra water).

**Comparison: "repeat the most profitable crop".** This is the single crop with the highest one-year margin that the farm could actually repeat (Climate Fit, water budget, fresh-market limit), grown for 5 years with no rotation. Its broken rules and health score are shown next to the three plans.

**Scenarios.**
- *Baseline*: 2011–2026 climate.
- *Hotter*: +1.5 °C on every daily Tmax/Tmin, with ET0, heat days, frost and GDD recomputed (a delta method, not a climate projection).
- *Less water*: −20 % budget.

The three baseline plans are re-checked under each scenario (feasible or not, and why), and the planner is also re-optimised per scenario.

### Demo farms — [`config/demo_farms.yaml`](config/demo_farms.yaml)

| Farm | NASA POWER point | Water budget | Inputs |
|---|---|---|---|
| Karshi farm | Karshi_field1 (38.92 N, 65.62 E), Kashkadarya | 8,000 m³/ha (editable) | **hypothetical** |
| Fergana farm | Fergana_field1 (40.49 N, 71.63 E) | 12,000 m³/ha (editable) | **hypothetical** |

The engine is the same for both farms, but they get different plans: Fergana's water lets it grow high-value crops, while Karshi's 8,000 m³/ha budget limits the choice (see *Desert bias → ET0 correction* under Limits).

### Main references
- Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). *Crop evapotranspiration — Guidelines for computing crop water requirements.* **FAO Irrigation and Drainage Paper 56.** FAO, Rome.
- Ayers, R.S., Westcot, D.W. (1985). *Water quality for agriculture.* **FAO Irrigation and Drainage Paper 29** Rev. 1. FAO, Rome.
- FAOSTAT (2026). Crops and livestock products (QCL); Producer Prices (PP). FAO, Rome. Bulk download, accessed 2026-11-14.

## Limits (also shown in the app)

- **Coarse grid.** NASA POWER weather is about 50 km (MERRA-2, 0.5° × 0.625°). Field pairs at Urgench, Gulistan, Fergana and Karshi fall in the same grid cell, so they share one district climate profile. Field-level differences come from the satellite layers (SMAP, ECOSTRESS, HLS).
- **Desert bias → ET0 correction.** The reanalysis has no irrigation, so Tmax and ET0 over irrigated oases are too high (without correction, cotton at Karshi needed ~16,300 m³/ha net). The crop engine and planner use **ET0 × 0.80**, an *approximate, provisional bias correction for MERRA-2 desert bias over irrigated land* ([`config/et0_correction.yaml`](config/et0_correction.yaml), editable per field or district). If `data/appeears/` holds ECOSTRESS `ETdaily` for a site, the factor is instead *calibrated with ECOSTRESS*: median(ECOSTRESS ETdaily, June–August clear-sky days) ÷ median(POWER ET0 × cotton Kc_mid, same days), clipped to 0.4–1.2, at least 5 days. Screen 2 keeps the raw ET0. The modelled actual ET (`EVPTRNS`) is close to zero there, so it is stored but not used.
- **Net need only.** Values are net crop water need. Gross field delivery is higher: furrow irrigation efficiency is about 50–60 %, and salt leaching needs extra water.
- **Rotation health is a rule score, not a soil model.** It does not simulate soil carbon, nitrogen, salinity or pests.
- **Prices and costs.** FAOSTAT national averages and annual prices; the tomato price probably overstates open-field farm-gate prices. **All costs are placeholders.** Profit ignores subsidies, credit, labour limits and price risk.
- **Hypothetical inputs.** Water budgets, the fresh-market limit (2 of 5 years) and demo-farm obligations are examples, not data.
- **Frost check.** Frost counts from emergence to harvest at one sowing date per site; emergence days and sowing windows are approximate. Air Tmin is a proxy for canopy temperature.
- **Rain QC.** A few implausible `PRECTOTCORR` spikes above 80 mm/day were removed (0–3 days per point).

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Tests (rules, budget, "no feasible plan", optimality, beating "repeat the best crop", data provenance):

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

To rebuild the data (needs internet):

```bash
python scripts/fetch_power.py      # STEP 1  NASA POWER (add --force to re-download)
python scripts/fetch_faostat.py    # FAOSTAT Uzbekistan extracts (prices, yields)
python scripts/build_summary.py    # STEPS 2-4  climate shift, crop engine, planner inputs
```

## Deploy on Streamlit Community Cloud

1. Push this folder to a **public GitHub repo**, including `data/` and `config/`.
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
- **FAOSTAT**, Food and Agriculture Organization of the United Nations: crop yields (QCL) and producer prices (PP) for Uzbekistan.
- Basemaps: © OpenStreetMap contributors; Esri World Imagery.

*DalaShift is a decision-support prototype. Check plans with a local agronomist or water user association before changing crops.*
