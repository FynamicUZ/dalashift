"""Export the farmer view (and key expert numbers) to a static site for Netlify: web/data.json.

    python scripts/export_static.py

Every combination the farmer can choose (5 districts x 3 water levels x must-grow on/off x 3 plans)
is computed with the SAME engine and the SAME formatting functions as the Streamlit app
(dalashift.planner, dalashift.baseline, dalashift.simple_ui), so web/ shows identical numbers.
The static page (web/index.html + app.js) only renders this file; no server is needed.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dalashift import simple_ui as su  # noqa: E402
from dalashift.appeears import load_appeears  # noqa: E402
from dalashift.smap import summary as smap_summary  # noqa: E402
from dalashift.hls import farmer_line as hls_line, summary as hls_summary  # noqa: E402
from dalashift.baseline import compare, evaluate_usual, water_deficit  # noqa: E402
from dalashift.crops import load_crop_table  # noqa: E402
from dalashift.i18n import CROP_NAMES, DISTRICTS, T  # noqa: E402
from dalashift.planner import load_planner_config, plan_farm  # noqa: E402

LANGS = ("uz", "en")
BUDGETS = list(range(4000, 16001, 500))   # water slider: every 500 m3/ha (Kam/O'rtacha/Ko'p = 6,000 / 8,000 / 12,000)
WEB = ROOT / "web"
UI_KEYS = ["step1", "eyebrow1", "eyebrow2", "plan_h", "since", "hot", "rain", "budget", "mm", "k_tonnes", "q_water",
           "w_little", "w_normal", "w_plenty", "q_must", "must_help", "q_goal", "plan_profit", "plan_balanced",
           "plan_water", "plan_low_risk", "income", "conservative", "vs_usual", "c_income", "c_water", "c_risk", "why",
           "disclaimer", "mln", "smap"]


def both(fn, *a, **kw) -> dict:
    return {lang: fn(*a, lang=lang, **kw) for lang in LANGS}


def md_to_html(md: str) -> str:
    """Tiny markdown -> HTML for the bullet lists in the limits texts."""
    items = [ln.strip()[2:] for ln in md.strip().splitlines() if ln.strip().startswith("* ")]
    conv = lambda s: re.sub(r"`(.+?)`", r"<code>\1</code>", re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", s)))  # noqa: E731
    return "<ul>" + "".join(f"<li>{conv(i)}</li>" for i in items) + "</ul>"


def plan_entry(plan: dict, kind: str, res: dict, usual: dict, point: dict, budget: float, must: bool) -> dict:
    fam = dict(zip(load_crop_table().index, load_crop_table()["family"]))
    m = point["baseline"]
    years = []
    for y in plan["years"]:
        first, last = y["crops"][0], y["crops"][-1]
        share = y["water"] / budget if budget else 2
        years.append({
            "year": y["year"], "option": y["option"],
            "name": {lang: su.crop_name(y["option"], lang) for lang in LANGS},
            "months": {lang: f"{su.month(m[first]['sow'], lang)} → {su.month(m[last]['harvest'], lang)}" for lang in LANGS},
            "water": round(y["water"]), "share": round(min(share, 1), 3),
            "water_color": su.OK if share <= 0.8 else su.WARN if share <= 1.0 + 1e-9 else su.BAD,
            "dot": su.FAMILY_COLOR.get(fam[first], su.GREEN),
            "usd_low": round(y["low"]), "usd_high": round(y["high"]),
        })
    r = plan["profit_per_year_range"]
    cmp = compare(plan, usual)
    deficit = water_deficit(usual, budget)
    wp = cmp["water_pct"]
    entry = {
        "kind": kind, "sequence": plan["sequence"], "years": years,
        "income_low": max(su.to_mln(r["low"]), 0), "band_lo": max(su.to_mln(r["low"]), 0),
        "band_hi": max(su.to_mln(r["high"], round), 0),
        "usd_per_year": [round(r["low"]), round(r["high"])], "water_per_year": round(plan["water_per_year"]),
        "water_total": round(plan["water_total"]), "health": plan["health"], "npv": round(plan["npv"]),
        "cmp": {
            "usual": {lang: " ↔ ".join(dict.fromkeys(CROP_NAMES[k][lang] for k in usual["sequence"])) for lang in LANGS},
            "usual_short": ({lang: su.ft("usual_short", lang, n=su.fmt_mln(round(deficit / 100) / 10, lang)) for lang in LANGS}
                            if deficit > 0 else None),
            "income": {lang: su.vs_usual(cmp["income_pct"], lang, True)[0] for lang in LANGS},
            "income_color": su.vs_usual(cmp["income_pct"], "en", True)[1],
            "water": {lang: su.vs_usual(wp, lang, False)[0] for lang in LANGS},
            "water_color": su.vs_usual(wp, "en", False)[1],
            "risk_reason": {lang: su.risk_reason(plan, lang) for lang in LANGS},
            "risk": {lang: su.ft("risk_" + cmp["risk_plan"], lang) for lang in LANGS},
            "risk_color": {"low": su.OK, "medium": su.WARN, "high": su.BAD}[cmp["risk_plan"]],
            "income_pct": None if cmp["income_pct"] is None else round(cmp["income_pct"], 1),
            "water_pct": round(wp, 1),
        },
        "why": {lang: su._why(plan, cmp, point, budget, lang) for lang in LANGS},
        "broken_rules": plan["broken_rules"],
    }
    if must and res["result"]["status"] == "ok":
        cc = (res.get("constraint_cost") or {}).get(kind)
        if cc and cc["npv_cost"] is not None:
            if cc["npv_cost"] > 1:
                entry["must_note"] = {}
                for lang in LANGS:
                    a, unit = su.soum(cc["npv_cost"], lang)
                    entry["must_note"][lang] = su.ft("must_cost", lang, m=f"{a:,.0f} {unit}".replace(",", " "))
            else:
                entry["must_note"] = {lang: su.ft("must_free", lang) for lang in LANGS}
    return entry


def build() -> dict:
    cfg = load_planner_config()
    rate, fresh = float(cfg["discount_rate"]), int(cfg["max_fresh_market_years"])
    summary = json.loads((ROOT / "data/summary.json").read_text(encoding="utf-8"))
    planner = json.loads((ROOT / "data/planner.json").read_text(encoding="utf-8"))["points"]
    pts = pd.read_csv(ROOT / "data/points.csv").set_index("id")
    water = load_appeears(ROOT / "data/appeears", pts.reset_index())
    out = {"ui": {k: {lang: su.FT[k][lang] for lang in LANGS} for k in UI_KEYS},
           "water_levels": su.WATER_LEVELS, "budgets": BUDGETS, "plans": su.PLANS, "uzs_per_usd": su.uzs_per_usd(),
           "limits": {lang: md_to_html(T["limits_text"][lang]) + md_to_html(T["pl_limits_text"][lang]) for lang in LANGS},
           "credits": {lang: T["credits"][lang] for lang in LANGS},
           "smap_note": {lang: T["smap_note"][lang] for lang in LANGS},
           "hls_note": {lang: T["hls_note"][lang] for lang in LANGS},
           "ecostress_note": {lang: T["ecostress_note"][lang] for lang in LANGS},
           "crop_names": {c: {lang: v[lang] for lang in LANGS} for c, v in CROP_NAMES.items()},
           "districts": {}}
    for d in su.FARMER_DISTRICTS:
        pid = f"{d}_field1"
        S, point = summary["points"][pid], planner[pid]
        th, nw = S["then"], S["now"]
        dist = {
            "name": {lang: DISTRICTS[d][lang] for lang in LANGS},
            "short": {lang: DISTRICTS[d][lang].split(" (")[0] for lang in LANGS},
            "lat": float(pts.loc[pid, "lat"]), "lon": float(pts.loc[pid, "lon"]),
            "facts": {"hot_then": round(th["hot_days"]), "hot_now": round(nw["hot_days"]),
                      "rain_then": round(th["gs_rain"]), "rain_now": round(nw["gs_rain"]),
                      "years": S["annual"]["year"], "hot_series": S["annual"]["hot_days"]},
            "crops": [{"crop": c, "need": m["need_m3ha"], "fits": m["fits"], "sow": m["sow"], "harvest": m["harvest"],
                       "heat_risk": m["heat_risk"], "p_frost": m["p_frost"]}
                      for c, m in point["baseline"].items() if c in CROP_NAMES],
            "et0_correction": point.get("et0_correction"),
            "smap": smap_summary(water, pid),
            "hls": hls_summary(water, pid),
            "hls_line": {lang: hls_line(hls_summary(water, pid), lang) for lang in LANGS},
            "has_ecostress": bool(len(water) and water[(water["point"] == pid) & water["var"].isin(["esi", "etdaily"])].shape[0]),
            "scenarios": {},
        }
        cotton_need = point["baseline"]["cotton"]["need_m3ha"]
        for budget in BUDGETS:
            usual = evaluate_usual(point["baseline"], float(budget), rate, fresh)
            for must in (False, True):
                k = 2 if must else 0
                res = plan_farm(point, float(budget), rate, fresh, {"cotton": k, "winter_wheat": k})
                status = res["result"]["status"]
                sc = {"status": status, "error": None, "plans": {},
                      "n_sequences": int(res["result"].get("n_sequences") or 0), "n_options": int(res["result"].get("n_options") or 0)}
                if status != "ok":
                    sc["error"] = {lang: (su.ft("cotton_short", lang, n=round(cotton_need / 1000), b=round(budget / 1000))
                                          if must and cotton_need > budget else su.ft("no_plan", lang)) for lang in LANGS}
                for kind, plan in res["result"]["plans"].items():
                    sc["plans"][kind] = plan_entry(plan, kind, res, usual, point, float(budget), must)
                dist["scenarios"][f"{budget}|{int(must)}"] = sc
        out["districts"][d] = dist
        print(d, "done")
    return out


def copy_deck() -> None:
    """web/deck/ = the offline deck (vendored reveal.js, no CDN), its image, the PDF and the one screenshot it uses."""
    import shutil
    src, dst = ROOT / "docs/deck", WEB / "deck"
    (dst / "vendor/theme").mkdir(parents=True, exist_ok=True)
    (dst / "img").mkdir(exist_ok=True)
    (WEB / "screenshots").mkdir(exist_ok=True)
    shutil.copy2(src / "offline.html", dst / "index.html")
    for f in ["reveal.min.css", "reveal.min.js", "reset.min.css", "theme/white.min.css"]:
        shutil.copy2(src / "vendor" / f, dst / "vendor" / f)
    for f in list((src / "img").glob("*.jpg")) + list((src / "img").glob("*.png")):
        shutil.copy2(f, dst / "img" / f.name)
    shutil.copy2(src / "DalaShift_deck.pdf", dst / "DalaShift_deck.pdf")
    shutil.copy2(ROOT / "docs/screenshots/farmer_full_phone.png", WEB / "screenshots/farmer_full_phone.png")


def main() -> None:
    WEB.mkdir(exist_ok=True)
    copy_deck()
    data = build()
    (WEB / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("wrote", WEB / "data.json", f"{(WEB / 'data.json').stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
