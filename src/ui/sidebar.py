"""Shared sidebar filters."""

from __future__ import annotations

import streamlit as st

from config import DEFAULT_YEAR_RANGE, FLOWS
from src.data.cubes import load_trade_cubes

PERIOD_PRESETS = {
    "Custom": None,
    "Full history (1988–2016)": (1988, 2016),
    "Pre-crisis boom (2000–2008)": (2000, 2008),
    "Financial crisis (2007–2010)": (2007, 2010),
    "Peak era (2011–2014)": (2011, 2014),
    "Commodity slowdown (2014–2016)": (2014, 2016),
    "Default (1995–2015)": DEFAULT_YEAR_RANGE,
}


def render_filters() -> dict:
    cubes = load_trade_cubes()
    meta = cubes.meta

    st.sidebar.markdown("### Period")
    preset = st.sidebar.selectbox("Quick range", list(PERIOD_PRESETS.keys()), index=6)

    if preset != "Custom" and PERIOD_PRESETS[preset]:
        default_range = PERIOD_PRESETS[preset]
    else:
        default_range = DEFAULT_YEAR_RANGE

    year_range = st.sidebar.slider(
        "Year range",
        min_value=meta.year_min,
        max_value=meta.year_max,
        value=(
            max(meta.year_min, default_range[0]),
            min(meta.year_max, default_range[1]),
        ),
    )

    st.sidebar.markdown("### Scope")
    exclude_aggregate = st.sidebar.checkbox(
        "Exclude aggregate bucket",
        value=True,
        help="Removes all_commodities (recommended).",
    )

    countries = st.sidebar.multiselect(
        "Countries",
        options=meta.countries,
        default=[],
        placeholder="All countries",
    )

    selected_categories = st.sidebar.multiselect(
        "Categories",
        options=meta.categories,
        default=[],
        placeholder="All categories",
    )

    selected_flows = st.sidebar.multiselect("Flows", options=FLOWS, default=FLOWS)

    return {
        "year_range": year_range,
        "exclude_aggregate": exclude_aggregate,
        "countries": tuple(countries) if countries else None,
        "categories": tuple(selected_categories) if selected_categories else None,
        "flows": tuple(selected_flows) if selected_flows else None,
        "preset": preset,
    }
