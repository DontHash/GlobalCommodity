"""Time series analysis."""

from __future__ import annotations

import streamlit as st

from src.data.context import FilteredView
from src.ui.components import render_data_footer
from src.ui.styles import page_header
from src.viz.charts import bar_chart, line_chart, stacked_flow_area


def render(view: FilteredView, filters: dict) -> None:
    page_header("Trends over time", "Historical growth — red bars = contraction years.")
    yearly = view.yearly_summary()
    flow = view.flow_by_year()

    tab1, tab2, tab3 = st.tabs(["Volume", "Growth", "Flows"])

    with tab1:
        st.plotly_chart(
            line_chart(yearly, "year", "trade_trillions", title="Trade volume", y_unit="T"),
            width="stretch",
        )

    with tab2:
        yoy = yearly.dropna(subset=["yoy_pct"])
        colors = ["#f43f5e" if v < 0 else "#0ea5e9" for v in yoy["yoy_pct"]]
        fig = bar_chart(yoy, "year", "yoy_pct", title="Year-over-year change (%)")
        fig.update_traces(marker_color=colors)
        st.plotly_chart(fig, width="stretch")
        st.dataframe(
            yearly[["year", "trade_trillions", "yoy_pct"]].round(2),
            width="stretch",
            hide_index=True,
            column_config={
                "year": st.column_config.NumberColumn("Year", format="%d"),
                "trade_trillions": st.column_config.NumberColumn("Trade ($T)", format="%.2f"),
                "yoy_pct": st.column_config.NumberColumn("YoY (%)", format="%.1f"),
            },
        )

    with tab3:
        flow_cols = [c for c in flow.columns if c != "year"]
        st.plotly_chart(
            stacked_flow_area(flow, flow_cols, "Flow composition"),
            width="stretch",
        )

    render_data_footer(view, filters)
