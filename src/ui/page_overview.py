"""Executive summary — decision hub (KPIs → trend → breakdown → root cause)."""

from __future__ import annotations

import streamlit as st

from src.analytics.kpis import compute_executive_kpis, detect_alerts, root_cause_drivers
from src.data.context import FilteredView
from src.ui.components import (
    render_alerts,
    render_data_footer,
    render_kpi_row,
    render_questions_expander,
    section,
)
from src.ui.styles import page_header
from src.ui.tables import show_category_changes, show_country_changes
from src.viz.charts import bar_chart, line_chart


def render(view: FilteredView, filters: dict) -> None:
    page_header(
        "Executive summary",
        "Start here: KPIs with context, trends, and what drove change.",
    )
    render_questions_expander()

    yearly = view.yearly_summary()
    if yearly.empty:
        st.warning("No data for this filter. Adjust the sidebar year range.")
        render_data_footer(view, filters)
        return

    years = yearly["year"].tolist()
    focus = st.selectbox(
        "Focus year for KPIs & alerts",
        options=years,
        index=len(years) - 1,
        help="Compared against the prior year and your selected range.",
    )

    section("1 · Are we growing or declining?")
    render_kpi_row(compute_executive_kpis(view, int(focus)))

    section("2 · What needs attention?")
    render_alerts(detect_alerts(view, int(focus)))

    section("3 · How has trade moved over time?")
    st.plotly_chart(
        line_chart(yearly, "year", "trade_trillions", title="Trade volume trend", y_unit="T"),
        width="stretch",
    )

    col_l, col_r = st.columns(2)
    with col_l:
        section("4a · Top countries")
        top_c = view.country_totals().head(10)
        top_c["trade_billions"] = top_c["trade_usd"] / 1e9
        st.plotly_chart(
            bar_chart(
                top_c.sort_values("trade_billions"),
                "trade_billions",
                "country_or_area",
                title="Top 10 by trade value",
                orientation="h",
            ),
            width="stretch",
        )
    with col_r:
        section("4b · Top categories")
        top_cat = view.category_totals(top_n=10)
        top_cat["trade_billions"] = top_cat["trade_usd"] / 1e9
        st.plotly_chart(
            bar_chart(
                top_cat.sort_values("trade_billions"),
                "trade_billions",
                "short_label",
                title="Top 10 categories",
                orientation="h",
            ),
            width="stretch",
        )

    section("5 · Why did trade change?")
    if len(years) >= 2:
        c1, c2 = st.columns(2)
        with c1:
            y_from = st.selectbox("From year", years, index=max(0, len(years) - 3), key="sum_from")
        with c2:
            y_to = st.selectbox("To year", years, index=len(years) - 1, key="sum_to")
        if y_from < y_to:
            drivers = root_cause_drivers(view, int(y_from), int(y_to))
            period = f"{y_from} → {y_to}"
            if drivers["total_change_pct"] is not None:
                st.metric("Total trade change", f"{drivers['total_change_pct']:+.1f}%", period)
            if drivers.get("all_categories_declined"):
                st.caption(
                    "All categories declined in this period — 'gains' shows smallest losses, not true growth."
                )
            d1, d2 = st.columns(2)
            with d1:
                show_category_changes(
                    drivers["top_category_declines"],
                    "Largest category declines",
                    period,
                    empty_message="No declining categories in this period.",
                )
            with d2:
                show_category_changes(
                    drivers["top_category_gains"],
                    "Largest category gains",
                    period,
                    empty_message="No categories grew in this period (all declined).",
                )
            d3, d4 = st.columns(2)
            with d3:
                show_country_changes(
                    drivers["top_country_declines"],
                    "Countries that lost the most",
                    period,
                )
            with d4:
                show_country_changes(
                    drivers["top_country_gains"],
                    "Countries that gained the most",
                    period,
                )
        else:
            st.info("Select a later 'To year' than 'From year'.")

    render_data_footer(view, filters)
