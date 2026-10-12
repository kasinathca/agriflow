from __future__ import annotations

import pandas as pd

from agriflow.ui import app as ui


def test_selected_state_does_not_reduce_national_map_frame(monkeypatch):
    prices = pd.DataFrame([
        {"date": pd.Timestamp("2024-01-01"), "commodity": "Onion", "state": "Maharashtra"},
        {"date": pd.Timestamp("2024-01-01"), "commodity": "Onion", "state": "Karnataka"},
        {"date": pd.Timestamp("2024-01-01"), "commodity": "Tomato", "state": "Kerala"},
    ])
    monkeypatch.setattr(ui, "PRICES", prices)

    linked = ui._filter("Onion", "Maharashtra", "2024-01-01", "2024-12-31")
    national = ui._national_map_frame("Onion", "2024-01-01", "2024-12-31")

    assert linked.state.nunique() == 1
    assert national.state.nunique() > 1
    assert set(national.state) == {"Maharashtra", "Karnataka"}


def test_map_click_updates_selector_with_canonical_state_name():
    click = {"points": [{"location": "Mahārāshtra"}]}
    assert ui._map_click_state(click, ["Maharashtra", "Karnataka"]) == "Maharashtra"
    assert ui._map_click_state({"points": [{"location": "Kerala"}]}, ["Maharashtra"]) is None
