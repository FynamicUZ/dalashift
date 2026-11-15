# DalaShift: Space Apps 2026 submission text (ready to paste)

Team **KarPS**: Ahmedov Zuhriddin · Alisherov Azimbek · Shermaxmatov Ozodbek · Botirxonov Faxriyor · Boyqulov Afzalbek
Challenge: **Field Shift: Adapting Farms with NASA Data** · Local event: Karshi, Uzbekistan

Links: App **[APP LINK]** · Deck **[DECK LINK]** · Code **[REPO LINK]**

---

## Project name

DalaShift

## Summary (1–2 sentences)

DalaShift turns 35 years of NASA climate data and current NASA satellite observations into a simple 5-year crop rotation plan for a farmer's field in Uzbekistan, in Uzbek, with income in so'm and water measured against what the farm actually gets. *Don't just choose the most profitable crop for this year. Choose the best five-year future for your field.*

## Project description (~250 words)

**Problem.** Uzbek farms are getting hotter and drier. Near Karshi, days above 35 °C rose from 96 to 104 a year between 1991–2005 and 2011–2026 (NASA POWER), and growing-season rain fell from 68 to 54 mm. Irrigation water is limited, yet crops are still chosen one year at a time. The usual wheat ↔ cotton rotation needs about 13,000 m³/ha in cotton years, far more than many farms receive.

**What it does.** A farmer picks a district, how much water the field gets, and whether cotton/wheat is compulsory. DalaShift shows what changed on the field, a 5-year crop plan (most income, balanced or least water), one cautious income figure, a comparison with the usual rotation, and a plain-language "why". At Karshi the balanced plan uses about 51 % less water than wheat ↔ cotton with about 20 % more income (estimate).

**How it works.** Daily NASA POWER weather feeds an FAO-56 crop-water and climate-fit engine (sowing windows, frost between emergence and harvest, heat risk). A brute-force planner checks every 5-year sequence (up to 248,832 per farm) against rotation rules and the water budget. NASA SMAP, HLS and ECOSTRESS show soil moisture, field greenness and crop stress, and serve as a check on the crop calendars. 241 automated tests check the rules and numbers.

**Benefits.** Less water, healthier rotations and honest numbers, in the farmer's language, on a phone.

**Scale and next steps.** Climate is computed once per ~50 km grid cell (about 100 irrigated cells nationally, a few hundred MB). Satellite layers are read only for the field a farmer opens, from NASA's cloud. Next: Uzcosmos and national farm data, soil and salinity layers, a Telegram bot in Uzbek, and real farm costs.

## NASA data used

| Data | Product | How DalaShift uses it |
|---|---|---|
| NASA POWER daily (MERRA-2 meteorology, CERES radiation, IMERG-corrected precipitation), `community=AG`, 1991-01-01 → 2026-10-31 | POWER Daily API: `T2M_MAX, T2M_MIN, T2M, PRECTOTCORR, EVPTRNS, RH2M, WS2M, ALLSKY_SFC_SW_DWN` | Climate shift (hot days, frost, rain), FAO-56 Penman-Monteith reference ET, crop water need, climate fit, 5-year planner |
| NASA SMAP L4 root-zone soil moisture, 9 km, 3-hourly | **SPL4SMGP.008** `Geophysical_Data_sm_rootzone`, 2024-01-01 → 2026-11-10 | Farmer line + expert chart: without irrigation, Karshi's root zone dries ~41 % from spring to summer (2026) |
| NASA/USGS Harmonized Landsat Sentinel-2, 30 m | **HLSL30_VI.020** and **HLSS30_VI.020** `NDVI` (Fmask cloud-masked), 2025-03 → 2026-11 | Field greenness curve; checks the crop calendars (Karshi: wheat peak Apr 2025, summer crop peak Aug 2026) |
| NASA ECOSTRESS, 70 m | **ECO_L3T_JET.002** `ETdaily`, **ECO_L4T_ESI.002** `ESI`, Jun–Sep 2025 | *Limited:* only 2 clear scenes for Karshi, too few to calibrate the water-need correction, which stays provisional (×0.80) |
| NASA AppEEARS (LP DAAC) | Point-sample API | Extraction of SMAP, HLS and ECOSTRESS at the field points |
| NASA Worldview / GIBS | MODIS Terra Corrected Reflectance (true colour), 12 Aug 2025 | Image of the Karshi oasis in the pitch deck |

## Other data and methods (non-NASA)

- **FAO-56** (Allen et al., 1998): crop coefficients and the crop water method. **FAO-29** (Ayers & Westcot, 1985): salinity thresholds.
- **FAOSTAT**, Uzbekistan crop yields 2022–2024 and producer prices 2023–2024.
- **Retail prices** for tomato, onion and potato (Korzinka) and for chickpea and mung bean (Uzum Market), 14 Nov 2026, × 0.40 to estimate the farm-gate price (approximate).
- **Central Bank of Uzbekistan** exchange rate: 12,014.37 so'm/USD (14 Nov 2026).
- **2025 cotton subsidy** of 1,000 so'm/kg to farmers (Ministry of Agriculture, reported by zamin.uz, 31 Aug 2025), added to the FAOSTAT cotton price.
- Costs per hectare are **placeholders** (no published farm budget), so every income figure is shown as a cautious estimate.

## Use of AI (disclosure)

*Team: check that this matches how you worked before submitting.*
The team used Claude (Anthropic) as an AI assistant to help write and test the code, research data sources and prices, build the app interface, the pitch deck and the video script, and draft texts like this one. The team chose the idea and the challenge, set the requirements, made the design and content decisions, and reviewed the data, the outputs and these texts. All numbers in the app and deck are computed from the data sources listed above, not generated by AI. Values that are assumptions are labelled "approximate" or "estimate".

## References

- NASA POWER: https://power.larc.nasa.gov
- NASA AppEEARS: https://appeears.earthdatacloud.nasa.gov
- SMAP L4 Global 3-hourly 9 km Surface and Root Zone Soil Moisture (SPL4SMGP), NSIDC DAAC: https://nsidc.org/data/spl4smgp
- HLS Vegetation Indices (HLSL30_VI / HLSS30_VI), LP DAAC: https://lpdaac.usgs.gov/products/hlsl30_viv002/ · https://lpdaac.usgs.gov/products/hlss30_viv002/
- ECOSTRESS ECO_L3T_JET / ECO_L4T_ESI, LP DAAC: https://lpdaac.usgs.gov/products/eco_l3t_jetv002/ · https://lpdaac.usgs.gov/products/eco_l4t_esiv002/
- NASA Worldview: https://worldview.earthdata.nasa.gov
- Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). *Crop evapotranspiration.* FAO Irrigation and Drainage Paper 56: https://www.fao.org/4/x0490e/x0490e00.htm
- Ayers, R.S., Westcot, D.W. (1985). *Water quality for agriculture.* FAO Irrigation and Drainage Paper 29.
- FAOSTAT: https://www.fao.org/faostat
- Central Bank of Uzbekistan exchange rates: https://cbu.uz
- Cotton prices and subsidies 2025 (zamin.uz): https://zamin.uz/en/uzbekistan/159026-official-prices-and-subsidies-for-cotton-harvest-announced.html
- Korzinka: https://korzinka.uz · Uzum Market: https://uzum.uz
