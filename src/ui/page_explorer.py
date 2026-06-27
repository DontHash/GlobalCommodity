"""Raw data explorer — lazy-loaded samples only."""

from __future__ import annotations

import streamlit as st

from src.data.context import FilteredView
from src.data.loader import load_filtered_sample
from src.ui.components import render_data_footer
from src.ui.styles import page_header


def render(view: FilteredView, filters: dict) -> None:
    page_header("Export data", "Detailed rows for analysts — sort, inspect, download CSV.")
    max_rows = st.slider("Sample size", 100, 5000, 1000, step=100)

    sample = load_filtered_sample(
        year_range=filters["year_range"],
        countries=filters["countries"],
        categories=filters["categories"],
        flows=filters["flows"],
        exclude_aggregate=filters["exclude_aggregate"],
        limit=max_rows,
    )

    cols = st.multiselect(
        "Columns",
        list(sample.columns),
        default=["country_or_area", "year", "commodity", "flow", "trade_usd", "category"],
    )
    st.dataframe(sample[cols], width="stretch", hide_index=True)
    st.download_button(
        "Download CSV",
        sample[cols].to_csv(index=False),
        "trade_sample.csv",
        "text/csv",
    )

    st.caption(
        f"Sample of {len(sample):,} records"
        + (f" from {view.profile['rows']:,} matching." if view.profile["rows"] else ".")
    )
    render_data_footer(view, filters)
