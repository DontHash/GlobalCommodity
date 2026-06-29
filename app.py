"""
Global Commodity Trade Analytics Dashboard

Run: streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from src.data.context import build_filtered_view
from src.ui import (
    page_commodities,
    page_countries,
    page_explorer,
    page_growth,
    page_mining,
    page_overview,
    page_story,
    page_timeseries,
    page_why,
)
from src.ui.components import render_scope_banner
from src.ui.sidebar import render_filters
from src.ui.styles import apply_styles

st.set_page_config(
    page_title="Commodity Trade Analytics",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Question-driven navigation (decision flow)
PAGES = {
    "① Executive summary": page_overview,
    "② Trends": page_timeseries,
    "③ Regions": page_countries,
    "④ Country growth": page_growth,
    "⑤ Products": page_commodities,
    "⑥ Why it changed": page_why,
    "⑦ Export data": page_explorer,
    "⑧ Advanced models": page_mining,
    "⑨ Case study": page_story,
}


def main() -> None:
    apply_styles()

    st.sidebar.markdown("### Commodity Trade")
    st.sidebar.caption("Decision dashboard · UN Comtrade 1988–2016")

    filters = render_filters()
    view = build_filtered_view(
        year_range=filters["year_range"],
        countries=filters["countries"],
        categories=filters["categories"],
        flows=filters["flows"],
        exclude_aggregate=filters["exclude_aggregate"],
    )

    st.sidebar.markdown("### Navigate")
    st.sidebar.caption("Follow the flow: summary → trends → breakdown → root cause")
    page_name = st.sidebar.radio(
        "Section",
        list(PAGES.keys()),
        label_visibility="collapsed",
    )
    st.sidebar.divider()
    p = view.profile
    rows_txt = f"{p['rows']:,} rec · " if p["rows"] else ""
    st.sidebar.caption(f"{rows_txt}{p['countries']} countries · ${p['total_trade_usd']/1e12:.2f}T")

    render_scope_banner(filters, view)
    PAGES[page_name].render(view, filters)


if __name__ == "__main__":
    main()
