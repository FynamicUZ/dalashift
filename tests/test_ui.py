"""Smoke tests of the Streamlit app: farmer view (UZ/EN, must-grow toggle, plan choice) and expert view."""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


@pytest.fixture(scope="module")
def at():
    a = AppTest.from_file(APP, default_timeout=180)
    a.run()
    assert not a.exception
    return a


def test_farmer_view_is_default_uzbek_and_in_soum(at):
    text = " ".join(m.value for m in at.tabs[0].markdown)     # farmer tab only
    assert "Dalangiz qayerda?" in text and "mln soʻm" in text
    for jargon in ("ET0", "GDD", "NDVI", "USD", "m³/ha"):
        assert jargon not in text, jargon


def test_must_grow_toggle_and_english(at):
    at.segmented_control(key="f_district").set_value("Fergana")
    at.segmented_control(key="f_water").set_value("plenty")
    at.toggle(key="f_must").set_value(True).run()
    assert not at.exception
    assert any("majburiyat" in i.value and "soʻm" in i.value for i in at.tabs[0].info)   # cost of the obligation
    at.segmented_control(key="lang_toggle").set_value("English").run()
    assert not at.exception
    assert "Where is your field?" in " ".join(m.value for m in at.tabs[0].markdown)


def test_every_district_and_water_level_renders():
    a = AppTest.from_file(APP, default_timeout=180)
    a.run()
    for d in ["Karshi", "Fergana", "Urgench", "Nukus", "Gulistan"]:
        for w in ["little", "normal", "plenty"]:
            a.segmented_control(key="f_district").set_value(d)
            a.segmented_control(key="f_water").set_value(w).run()
            assert not a.exception, (d, w)
