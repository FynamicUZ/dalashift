# DalaShift: technical Q&A prep

Short answers first (say this), then a "detail" line if they push. Be honest: "estimate", "approximate", "next step".

## A. Data

**1. Which NASA data do you use, and for what?**
NASA POWER daily weather (1991–2026) is the core input: temperature, humidity, wind, solar radiation and rain feed the crop-water engine. NASA SMAP L4 root-zone soil moisture shows how dry the soil gets. HLS (Landsat + Sentinel-2) NDVI shows how green the fields are and confirms the crop calendars. We got SMAP and HLS through NASA AppEEARS.
*Detail:* POWER sources are MERRA-2 (weather), CERES (radiation) and IMERG (rain).

**2. What is the resolution? Is it really "your field"?**
No. NASA POWER is about 50 km, so the plan is right for the area around the field, not for one plot. SMAP L4 is 9 km, and HLS is 30 m, which is truly field level. The next step is adding field-level soil and salinity data.

**3. Why do the SMAP and NDVI rows show "—" for Urgench, Nukus and Gulistan?**
We requested satellite data only for our two pilot districts, Karshi and Fergana. The same script works for any point. We just ran out of download time.

**4. How did you use ECOSTRESS?**
We tested it. In our window there were only 2 clear scenes, too few to calibrate, so we don't show it as a result. The code is ready to calibrate ET0 with ECOSTRESS once there are at least 5 clear summer days.

**5. Where do the prices come from?**
Yields come from FAOSTAT Uzbekistan. Cotton uses the FAOSTAT producer price plus the 2025 state subsidy of 1,000 so'm/kg. Other crops use Korzinka and Uzum retail prices × 0.40 to get an approximate farm-gate price. Money is converted at the Central Bank rate. All of these are estimates, and costs are placeholders.

## B. Method

**6. How do you calculate crop water need?**
We use the standard FAO-56 method. Penman–Monteith ET0 comes from the daily NASA POWER weather. It is multiplied by a crop coefficient Kc for each growth stage (FAO-56 single Kc, climate-adjusted), and we subtract effective rain (the USDA-SCS method, the CROPWAT default). The result is the net irrigation need in m³/ha.

**7. What is the "ET0 correction × 0.8"?**
MERRA-2 doesn't simulate irrigation, so over a green oasis its air is too hot and dry, and ET0 comes out too high. Without the correction, cotton in Karshi would need about 16,000 m³/ha. We scale ET0 by 0.8, and the app labels this as provisional. The plan is to calibrate it with ECOSTRESS.

**8. How do you decide whether a crop "fits" the climate?**
Four checks per crop, using real daily weather: enough heat (growing degree days) in at least 80% of years; frost between emergence and harvest in at most 20% of years; a sowing date inside the typical Uzbek sowing window; and hot days above the crop's limit during flowering, which reduce yield.

**9. How does the optimizer work? Why brute force?**
Every crop that fits is one option per year, plus allowed double crops such as wheat followed by mung bean. We check every 5-year combination: 12 options gives 12⁵ = 248,832 plans. Each plan is checked against hard rules (water budget every year, at most 2 cotton years in a row, no crop family 3 years in a row, a limit on fresh vegetables, the cotton/wheat obligation). Then it gets a score. Brute force is simple and fully transparent: we can say exactly why each plan won or lost.

**10. How do you choose between the "income", "balanced" and "water saving" plans?**
- Income: highest 5-year profit, discounted at 10% a year.
- Water saving: lowest water use; if two plans tie, the one with more profit.
- Balanced: profit, water saving and rotation health, each scaled 0–1, with equal weight.

**11. What is "rotation health"? Is it soil data?**
No, it's a 0–10 rule score, and we say so on the slide. It takes points off for repeating the same crop, having no legume year, or low crop variety. It is not measured soil nitrogen or carbon. Measured soil data is on our roadmap.

**12. How do rotations change yield?**
We use approximate effects from agronomy studies: −10% yield for each repeated year of the same crop (capped at −30%), +10% after a legume, and +15% after alfalfa. All of these can be changed in the config files.

**13. How do you compare with the "usual plan"?**
The usual plan is wheat ↔ cotton, run through the same engine, the same water budget and the same prices, so it's a like-for-like comparison.

## C. Hard questions (be honest)

**14. Your 5-year "replay" uses data the plan was built on. Isn't that circular?**
Yes, partly. The replay shows the plan fits real recent weather year by year, not just on average. A true out-of-sample test, choosing the plan with 1991–2020 data and testing it on 2021–2025, is our next validation step.

**15. Cotton fails only because you set water to 8,000. Isn't that rigged?**
The water amount is the farmer's own input; 8,000 m³/ha is a typical "medium" level. Cotton in Karshi needs about 12,900 m³/ha, so the usual plan fits only on farms with about 13,000 or more, and the slider shows that. Our point is that when water is short (and it is getting shorter), the wheat–cotton plan breaks first.

**16. Farmers in Uzbekistan often must grow cotton. Is this realistic?**
Yes, that's why there's a "cotton/wheat required" switch. With it on, DalaShift keeps the required crop and optimizes the other years and the rest of the rotation.

**17. How accurate is the income?**
It's an estimate. We show the low end of a ±15% range, rounded down. Costs are placeholders, and real farm costs are the first thing we would add with partners.

**18. Did farmers or agronomists test it?**
Not yet. The next step is a pilot with farmers in Karshi and an agronomist review. The rules are in plain config files, so an agronomist can change them without code.

**19. Is this AI or machine learning?**
No. DalaShift uses rules and physics (FAO-56) with a full search. Every number can be explained, which matters for farmers and for trust.

**20. How do you know your numbers are right?**
244 automated tests check the FAO-56 maths, the rules and the planner. The numbers are cross-checked with SMAP and HLS: wheat's NDVI peak in April and the summer crops' peak in August match our calendars.

**21. What about salinity, Uzbekistan's main soil problem?**
It isn't modelled yet. Field-level soil and salinity are on our roadmap; satellite salinity indices and national soil maps are the candidates.

## D. Tech and scaling

**22. What is the tech stack?**
Python (pandas, NumPy) runs the engine, and a Streamlit app is used for analysis. The public site is plain HTML, CSS and JavaScript with Leaflet maps, built from precomputed JSON and hosted on Netlify. The pitch deck is built with reveal.js. We use pytest and Playwright for testing, plus a prototype Telegram bot.

**23. Why a static site?**
It loads fast on a weak phone connection, is free to host, and needs no server. Plans for each district and water level are computed ahead of time (water from 4,000 to 16,000 m³/ha in steps of 500).

**24. How would you scale to all of Uzbekistan, or another country?**
NASA POWER, SMAP and HLS are global. A new region needs its crop list, sowing calendar and local prices; the engine is the same. For all of Uzbekistan, we would run the planner for each POWER grid cell and connect Uzcosmos and national farm data.

**25. What does "My location" do with my data?**
The location is used only inside the browser to pick the nearest district. We have no server, so nothing is sent to us or stored.
