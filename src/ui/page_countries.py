"""Country analysis and world map."""

from __future__ import annotations

import streamlit as st

from config import TOP_N
from src.data.context import FilteredView
from src.data.country_iso import attach_iso3
from src.ui.components import render_data_footer
from src.ui.styles import page_header
from src.viz.charts import bar_chart, choropleth_map, line_chart


def render(view: FilteredView, filters: dict) -> None:
    page_header("Regions", "Which countries are over- or under-performing? Map and rankings.")

    tab_map, tab_rank, tab_bal, tab_cmp = st.tabs(
        ["World map", "Rankings", "Trade balance", "Compare"]
    )

    with tab_map:
        years = sorted(view.country_year_flow["year"].unique())
        c1, c2 = st.columns([1, 2])
        with c1:
            map_year = st.selectbox("Map year", years, index=len(years) - 1)
            metric = st.selectbox(
                "Color by",
                [
                    ("total_trade", "Total trade"),
                    ("trade_balance", "Export − import balance"),
                    ("exports", "Exports"),
                    ("imports", "Imports"),
                ],
                format_func=lambda x: x[1],
            )
        metrics = view.map_metrics(map_year, metric[0])
        geo = attach_iso3(metrics)
        unmapped = len(metrics) - len(geo)
        st.plotly_chart(
            choropleth_map(
                geo,
                title=f"{metric[1]} · {map_year}",
                color_label=metrics["metric_label"].iloc[0] if len(metrics) else "Value",
                diverging=(metric[0] == "trade_balance"),
            ),
            width="stretch",
        )
        if unmapped > 0:
            st.caption(
                f"{unmapped} territories omitted (aggregates or non-ISO labels e.g. EU-28)."
            )

    with tab_rank:
        flow_choice = st.selectbox("Flow", ["All", "Import", "Export"], key="rank_flow")
        flow = None if flow_choice == "All" else flow_choice
        top_n = st.slider("Top N", 5, 30, TOP_N, key="rank_n")
        ranks = view.country_totals(flow=flow).head(top_n)
        ranks["trade_billions"] = ranks["trade_usd"] / 1e9
        st.plotly_chart(
            bar_chart(
                ranks.sort_values("trade_billions"),
                "trade_billions",
                "country_or_area",
                title=f"Top {top_n} by trade",
                orientation="h",
            ),
            width="stretch",
        )

    with tab_bal:
        bal = view.trade_balance()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Largest surpluses**")
            sur = bal[bal["balance_billions"] >= 0].head(TOP_N).reset_index()
            st.plotly_chart(
                bar_chart(sur, "balance_billions", "country_or_area", orientation="h"),
                width="stretch",
            )
        with c2:
            st.markdown("**Largest deficits**")
            defi = bal[bal["balance_billions"] < 0].tail(TOP_N).reset_index()
            st.plotly_chart(
                bar_chart(defi, "balance_billions", "country_or_area", orientation="h"),
                width="stretch",
            )

    with tab_cmp:
        options = sorted(view.country_year_flow["country_or_area"].unique())
        selected = st.multiselect(
            "Countries", options, default=options[:3], max_selections=5
        )
        if selected:
            comp = view.country_year(selected)
            comp["trade_billions"] = comp["trade_usd"] / 1e9
            st.plotly_chart(
                line_chart(
                    comp, "year", "trade_billions", color="country_or_area", title="Comparison"
                ),
                width="stretch",
            )

    render_data_footer(view, filters)
