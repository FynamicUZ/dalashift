# DalaShift: 30-second video script

Format: 30 s, 16:9, English subtitles burned in. Voice-over in English (or Uzbek with these English
lines as subtitles). It follows the deck's story. Every number comes from the app
(`data/summary.json` and the planner; Karshi, water "Oʻrtacha" = 8,000 t per hectare).

## Beats and subtitles

| Time | Beat | On screen | Subtitle / voice-over (English) |
|---|---|---|---|
| 0:00–0:02 | Team | Team name and members (Ahmedov Zuhriddin, Alisherov Azimbek, Shermaxmatov Ozodbek, Botirxonov Faxriyor, Boyqulov Afzalbek) over the NASA image of the Karshi oasis | "We are KarPS, from Karshi." |
| 0:02–0:05 | Challenge | Text: *Field Shift: Adapting Farms with NASA Data* · NASA Space Apps 2026 | "Our challenge: Field Shift, adapting farms with NASA data." |
| 0:05–0:10 | Title + tagline | Deck slide 1: "Every spring, a farmer near Karshi bets the family's year on one decision: what to plant." → DalaShift + tagline | "DalaShift. Don't just choose the most profitable crop for this year. Choose the best five-year future for your field." |
| 0:10–0:13 | Demo: the field | Screen recording, Fermer tab, Qarshi selected: field card "96 → 104" hot days, rain 68 → 54 mm | "Near Karshi there are now 104 very hot days a year, up from 96, and less rain." |
| 0:13–0:17 | Demo: the plan | Scroll to *Keyingi besh yil uchun reja*, *Muvozanat*: 5-year timeline Chickpea → Wheat → Chickpea → Wheat → Barley, "≈ 6 mln soʻm" | "DalaShift checks every five-year crop plan and picks one that fits the farm's water." |
| 0:17–0:20 | Demo: vs usual | Hold on the comparison strip and the "Nega bu reja?" paragraph | "Compared with the usual wheat and cotton, it uses about half the water and earns more." |
| 0:20–0:23 | Demo: trade-off | Switch on *Paxta / bugʻdoy ekish majburiymi?*: red line "Paxta uchun … 13 ming tonna … sizda 8 ming tonna" | "Must you grow cotton? It needs 13 thousand tonnes of water per hectare here. The farm has 8." |
| 0:23–0:30 | Future | Deck slide 7 (roadmap cards appear), then logo + [REPO LINK] / [APP LINK] | "Next: Uzcosmos and national farm data, soil and salinity, and a Telegram bot in Uzbek. Every field in Uzbekistan." |

## Shot list

1. **NASA image + team** (0:00–0:02): `docs/deck/img/karshi_modis_terra_2025-08-12.jpg`, slow zoom-in, team name.
2. **Challenge card** (0:02–0:05).
3. **Deck slide 1** (0:05–0:10): open `docs/deck/offline.html`, press → three times to reveal the hook, then the title.
4. **Screen recording** (0:10–0:23), app on the *Fermer* tab in Uzbek (`streamlit run app.py`, browser zoom 110 %):
   - 4a. Qarshi field card (hot days, sparkline, rain).
   - 4b. Scroll to the 5-year timeline, *Muvozanat* selected; hold on the income figure.
   - 4c. Hold on the comparison strip and the *Nega bu reja?* paragraph.
   - 4d. Switch on the cotton/wheat toggle; hold on the red line.
5. **Deck slide 7** (0:23–0:30), then the logo with repo/app links.

## Sources for the numbers

- 96 → 104 very hot days (Tmax > 35 °C), Karshi, 1991–2005 vs 2011–2026; rain April–October 68 → 54 mm: NASA POWER (`data/summary.json`).
- "About half the water and earns more": Karshi balanced plan vs wheat ↔ cotton at 8,000 t/ha: water −51 %, income +20 % (`docs/deck/build_deck.py` prints these).
- "≈ 6 mln soʻm": conservative figure, the low end of the ±15 % estimate, × CBU rate 12,014.37 soʻm/USD (14 Nov 2026).
- "13 thousand tonnes": Karshi cotton net irrigation need ≈ 12,940 m³ (= t) per ha, after the provisional ×0.80 ET0 correction.
