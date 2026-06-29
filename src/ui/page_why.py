"""Why did trade change? — dedicated root-cause & comparison page."""

from __future__ import annotations

import streamlit as st

from src.analytics.kpis import root_cause_drivers, underperformers
from src.data.context import FilteredView
from src.ui.components import render_data_footer, section
from src.ui.styles import page_header
from src.ui.tables import show_category_changes, show_country_changes
from src.viz.charts import bar_chart, line_chart


def render(view: FilteredView, filters: dict) -> None:
    page_header(
        "Why did it change?",
        "Compare periods, isolate drivers, and find underperforming regions.",
    )

    yearly = view.yearly_summary()
    years = yearly["year"].tolist()
    if not years:
        st.warning("No data in range.")
        render_data_footer(view, filters)
        return

    tab_rc, tab_cmp, tab_under = st.tabs(
        ["Root cause", "Period comparison", "Underperformers"]
    )

    with tab_rc:
        section("Driver analysis")
        c1, c2 = st.columns(2)
        with c1:
            y_from = st.selectbox("From", years, index=max(0, len(years) - 3), key="rc_from")
        with c2:
            y_to = st.selectbox("To", years, index=len(years) - 1, key="rc_to")
        if y_from < y_to:
            d = root_cause_drivers(view, int(y_from), int(y_to), top_n=8)
            period = f"{y_from} → {y_to}"
            if d["total_change_pct"] is not None:
                st.metric("Total trade change", f"{d['total_change_pct']:+.1f}%", period)
            if d.get("all_categories_declined"):
                st.caption(
                    "All categories declined in this period — gains shows smallest losses, not true growth."
                )
            c1, c2 = st.columns(2)
            with c1:
                show_category_changes(d["top_category_declines"], "Largest category declines", period)
            with c2:
                show_category_changes(
                    d["top_category_gains"],
                    "Largest category gains",
                    period,
                    empty_message="No categories grew in this period.",
                )
            c3, c4 = st.columns(2)
            with c3:
                show_country_changes(d["top_country_declines"], "Countries that lost the most", period)
            with c4:
                show_country_changes(d["top_country_gains"], "Countries that gained the most", period)
        else:
            st.warning("Pick a later 'To' year.")

    with tab_cmp:
        section("Year-over-year comparison")
        compare_years = st.multiselect(
            "Years to compare", years, default=years[-3:] if len(years) >= 3 else years
        )
        if compare_years:
            sub = yearly[yearly["year"].isin(compare_years)]
            st.plotly_chart(
                bar_chart(sub, "year", "trade_trillions", title="Trade by selected years"),
                width="stretch",
            )
            st.dataframe(
                sub[["year", "trade_trillions", "yoy_pct"]].round(2),
                width="stretch",
                hide_index=True,
                column_config={
                    "trade_trillions": st.column_config.NumberColumn("Trade ($T)", format="%.2f"),
                    "yoy_pct": st.column_config.NumberColumn("YoY (%)", format="%.1f"),
                },
            )

    with tab_under:
        section("Underperforming regions", "Below median YoY in focus year")
        fy = st.selectbox("Focus year", years, index=len(years) - 1, key="under_y")
        under = underperformers(view, int(fy))
        st.dataframe(
            under.rename(columns={"yoy_pct": "YoY (%)"}),
            width="stretch",
            hide_index=True,
            column_config={"YoY (%)": st.column_config.NumberColumn(format="%.1f")},
        )

    render_data_footer(view, filters)
