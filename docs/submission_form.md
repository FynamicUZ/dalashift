# Space Apps project page: text to paste (KarPS · DalaShift)

## Project details

**What it does.** DalaShift is a 5-year crop rotation planner for irrigated farms, piloted in Uzbekistan. A farmer picks a district (or uses their phone's location), sets how much irrigation water the field gets, and says whether cotton or wheat is required. DalaShift then shows what has changed in the field's climate and a 5-year crop plan (most income, balanced, or least water) with a cautious income estimate in so'm, water use against the farm's own supply, a comparison with the usual wheat-cotton rotation, and a plain-language "why". It is Uzbek-first, with an English toggle and a detailed tab for experts and judges.

**How it works.** Daily NASA POWER weather (1991-2026) feeds an FAO-56 crop-water and climate-fit engine: sowing windows, frost between emergence and harvest, heat stress at flowering, and net irrigation need per crop. A brute-force planner checks every possible 5-year sequence (up to 248,832 per farm) against rotation rules and the water budget. NASA SMAP soil moisture and HLS greenness show how dry and how green the field is, and they confirm the crop calendars (e.g. in Karshi: winter wheat peaks in April, summer crops peak in August). 244 automated tests check the rules and the numbers.

**Benefits and impact.** In Karshi (8,000 m3/ha of water), a backcast with real 2021-2025 NASA weather shows the usual wheat-cotton rotation was short of water in 2 of 5 years. The DalaShift balanced plan fits the water every year, uses about 51% less water, and earns about 20% more (estimate), with 2 legume years that restore soil nitrogen. The intended impact is less water wasted, healthier rotations and more stable farm income, explained in the farmer's own language on a phone.

**Tools.** Python (pandas, NumPy), Streamlit, a static web app in HTML/CSS/JavaScript (Leaflet maps, OpenStreetMap tiles), reveal.js for the pitch deck, pytest, Playwright for screenshot checks, NASA AppEEARS API, Netlify and GitHub. A Telegram bot prototype (@dalashiftbot).

**Creativity.** Instead of answering "what is the most profitable crop this year?", DalaShift plans five years ahead and shows the trade-offs: income vs water vs soil. NASA climate data is turned into three plain facts for farmers, while all the science stays one tab away for experts.

**Factors we considered.** Uzbek language and money in so'm; farmers with no technical background; honest numbers (cautious estimates, clearly labelled assumptions, placeholder costs flagged); real constraints (water limits, compulsory cotton/wheat, 25% cap on fresh vegetables for markets); the ~50 km resolution of climate data; and scaling (NASA POWER, SMAP and HLS are global, so a new region needs only its crop list and local prices).

Links: App https://dalashift.netlify.app · Deck https://dalashift.netlify.app/deck/ · Video https://dalashift.netlify.app/video/ · Code https://github.com/FynamicUZ/dalashift · Telegram https://t.me/dalashiftbot

## Use of Super Intelligence (select what applies; team to confirm)

- Research or Information Gathering
- Data Analysis and Interpretation
- Coding, Debugging, or Troubleshooting
- Writing, Editing, or Translation
- (Ideation or Brainstorming: only if the team used AI for this)
- (Audio: if the video voice-over was made with text-to-speech, say so in the description, e.g. "Voice-over generated with a text-to-speech tool.")

## NASA Data (Link Text → Link URL)

| Link Text | Link URL |
|---|---|
| NASA POWER Daily API (MERRA-2, CERES, IMERG) | https://power.larc.nasa.gov |
| SMAP L4 Root-Zone Soil Moisture (SPL4SMGP v8) | https://nsidc.org/data/spl4smgp |
| HLS Landsat Vegetation Indices (HLSL30_VI v2.0) | https://lpdaac.usgs.gov/products/hlsl30_viv002/ |
| HLS Sentinel-2 Vegetation Indices (HLSS30_VI v2.0) | https://lpdaac.usgs.gov/products/hlss30_viv002/ |
| ECOSTRESS Evapotranspiration (ECO_L3T_JET v2, tested) | https://lpdaac.usgs.gov/products/eco_l3t_jetv002/ |
| ECOSTRESS Evaporative Stress Index (ECO_L4T_ESI v2, tested) | https://lpdaac.usgs.gov/products/eco_l4t_esiv002/ |
| NASA AppEEARS | https://appeears.earthdatacloud.nasa.gov |
| NASA Worldview (MODIS Terra image of Karshi) | https://worldview.earthdata.nasa.gov |

## Space Agency Partner & Other Data (Link Text → Link URL)

| Link Text | Link URL |
|---|---|
| FAO-56 Crop Evapotranspiration (method) | https://www.fao.org/4/x0490e/x0490e00.htm |
| FAOSTAT (Uzbekistan yields and producer prices) | https://www.fao.org/faostat |
| FAO AQUASTAT (global agricultural water use) | https://www.fao.org/aquastat |
| Central Bank of Uzbekistan exchange rates | https://cbu.uz |
| 2025 cotton prices and subsidies (zamin.uz) | https://zamin.uz/en/uzbekistan/159026-official-prices-and-subsidies-for-cotton-harvest-announced.html |
| Korzinka (retail prices) | https://korzinka.uz |
| Uzum Market (retail prices) | https://uzum.uz |
| OpenStreetMap (map tiles) | https://www.openstreetmap.org/copyright |
| Leaflet (map library) | https://leafletjs.com |
| reveal.js (pitch deck) | https://revealjs.com |
| Streamlit | https://streamlit.io |
| Lucide icons | https://lucide.dev |
| Inter font | https://fonts.google.com/specimen/Inter |
| DalaShift source code | https://github.com/FynamicUZ/dalashift |
