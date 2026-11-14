# DalaShift: 30-second video script

Format: 30 s, 16:9, English subtitles (burned in). Voice-over in English (optionally Uzbek with the
English lines as subtitles). Every number below comes from the app (data/summary.json and the
planner, Karshi demo farm, "Oʻrtacha" water = 8,000 m³/ha).

## Beats and subtitles

| Time | Beat | On screen | Subtitle / voice-over (English) |
|---|---|---|---|
| 0:00–0:02 | Team | Team name + member names over the DalaShift logo | "We are [TEAM NAME], from Karshi." |
| 0:02–0:05 | Challenge | Text card: *Field Shift: Adapting Farms with NASA Data* · NASA Space Apps 2026 | "Our challenge: Field Shift, adapting farms with NASA data." |
| 0:05–0:10 | Title + tagline | 🌾 DalaShift, then the tagline | "DalaShift. Don't just choose the most profitable crop for this year. Choose the best five-year future for your field." |
| 0:10–0:13 | Demo: step 1 | Screen recording, farmer view: tap **Qarshi** | "A farmer near Karshi picks their district." |
| 0:13–0:16 | Demo: step 2 | Scroll to the 3 cards: **+8 kun**, ≈0 kun, **+370 tonna** | "NASA data shows 8 more very hot days a year than in 1991–2005, and crops need more water." |
| 0:16–0:20 | Demo: step 3 | Pick water **Oʻrtacha**, tap **Muvozanat**: 5 crop tiles, **5–10 mln soʻm / ga / yil**, green bar "Suvingiz yetadi" | "DalaShift checks every five-year crop plan and shows one that pays and fits the water: chickpea and wheat in rotation." |
| 0:20–0:23 | Demo: trade-off | Switch on *Paxta / bugʻdoy ekish majburiymi?* → red line "Paxta uchun … 13 ming tonna … sizda 8 ming tonna" | "Must you grow cotton? Here it needs about 13 thousand tonnes of water per hectare. The farm has 8." |
| 0:23–0:30 | Future | Slide 7 bullets, then logo + [REPO LINK] / [APP LINK] | "Next: Uzcosmos and national farm data, soil and salinity layers, and a Telegram bot in Uzbek. DalaShift: plan the next five years, not just the next one." |

## Shot list

1. **Logo card** (0:00–0:02): white background, 🌾 DalaShift, team name and members (fill the placeholders).
2. **Challenge card** (0:02–0:05): challenge title, NASA Space Apps 2026, Karshi local event.
3. **Title card** (0:05–0:10): slide 1 of `docs/deck/index.html` (tagline visible).
4. **Screen recording, desktop or phone** (0:10–0:23), app on the 👨‍🌾 *Fermer* tab, Uzbek:
   - 4a. Tap *Qarshi* (already selected; tap once for the motion).
   - 4b. Scroll to *2. Dalangizda nima oʻzgardi?* and hold 2 s on the three cards.
   - 4c. Scroll to *3. 5 yillik reja*, keep *Oʻrtacha*, tap *⚖️ Muvozanat*, hold on the crop tiles and the income.
   - 4d. Switch on the cotton/wheat toggle; hold on the red explanation line.
   - Recording tip: run `streamlit run app.py`, browser zoom 110 %, hide the mouse pointer where possible.
5. **Future card** (0:23–0:30): slide 7 of the deck, then the logo with repo/app links.

## Sources for the numbers

- "+8 more very hot days": Karshi, days with Tmax > 35 °C, 96 (1991–2005) → 104 (2011–2026), NASA POWER (`data/summary.json`).
- "+370 tonnes": Karshi, April–October reference crop water use (ET0) +37 mm = +370 m³ = 370 t per ha.
- "5–10 mln soʻm / ga / yil": Karshi balanced plan at 8,000 m³/ha, estimate range (±30 %) × CBU rate 12,014.37 soʻm/USD (14 Nov 2026).
- "13 thousand tonnes": Karshi cotton net irrigation need ≈ 12,940 m³/ha (after the provisional ×0.80 ET0 correction).
