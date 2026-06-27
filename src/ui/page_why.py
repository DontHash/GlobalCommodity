"""Why did trade change? — dedicated root-cause & comparison page."""

from __future__ import annotations

import streamlit as st

from src.analytics.kpis import root_cause_drivers, underperformers
from src.data.context import FilteredView
from src.ui.components import render_data_footer, section
from src.ui.styles import page_header
from src.viz.charts import bar_chart, line_chart


def render(view: FilteredView, filters: dict) -> None:
    page_header(
        "Why did it change?",
        "Compare periods, isolate drivers, and find underperforming regions.",
    )

    yearly = view.yearly_summary()
    years = yearly["year"].tolist()

    tab_rc, tab_cmp, tab_under = st.tabs(
        ["Root cause", "Period comparison", "Underperformers"]
    )

    with tab_rc:
        section("Driver analysis", "Which categories and countries moved trade?")
        c1, c2 = st.columns(2)
        with c1:
            y_from = st.selectbox("From", years, index=max(0, len(years) - 3), key="rc_from")
        with c2:
            y_to = st.selectbox("To", years, index=len(years) - 1, key="rc_to")
        if y_from < y_to:
            d = root_cause_drivers(view, int(y_from), int(y_to), top_n=8)
            if d["total_change_pct"] is not None:
                st.metric("Total trade change", f"{d['total_change_pct']:+.1f}%")
            st.dataframe(d["top_category_declines"], width="stretch", hide_index=True)
            st.dataframe(d["top_country_declines"], width="stretch", hide_index=True)
        else:
            st.warning("Pick a later 'To' year.")

    with tab_cmp:
        section("Year-over-year comparison", "Side-by-side trade levels")
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
            )

    with tab_under:
        section("Underperforming regions", "Countries below median YoY in focus year")
        fy = st.selectbox("Focus year", years, index=len(years) - 1, key="under_y")
        under = underperformers(view, int(fy))
        st.dataframe(under, width="stretch", hide_index=True)

    render_data_footer(view, filters)
