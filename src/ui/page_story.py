"""Optional guided story view."""

from __future__ import annotations

import streamlit as st

from config import OIL_CATEGORY
from src.analytics.mining import arima_forecast
from src.analytics.story import shock_events
from src.data.context import FilteredView
from src.ui.components import render_data_footer
from src.ui.styles import page_header
from src.viz.charts import counterfactual_chart, dual_series_timeline


def render(view: FilteredView, filters: dict) -> None:
    page_header(
        "Case study",
        "Ghost Boom narrative — illustrative; use Executive summary for your own decisions.",
    )

    yearly = view.yearly_summary()
    events = shock_events(yearly)
    counter = arima_forecast(yearly, train_end_year=min(2007, view.year_range[1] - 1))

    gap_2011 = counter.loc[counter["year"] == 2011, "gap_trillions"]
    gap_2015 = counter.loc[counter["year"] == 2015, "gap_trillions"]
    cum = counter.loc[counter["gap_trillions"] < 0, "gap_trillions"].sum()

    peak = yearly.loc[yearly["trade_trillions"].idxmax()]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Peak", f"{int(peak['year'])}")
    c2.metric("Peak volume", f"${peak['trade_trillions']:.1f}T")
    c3.metric("2015 gap", f"${gap_2015.iloc[0]:.1f}T" if len(gap_2015) else "—")
    c4.metric("Below-trend (cum.)", f"${abs(cum):.0f}T")

    st.dataframe(events, width="stretch", hide_index=True)
    st.plotly_chart(
        counterfactual_chart(
            counter["year"].tolist(),
            counter["trade_trillions"].tolist(),
            counter["forecast_trillions"].tolist(),
            "Actual vs counterfactual trend",
        ),
        width="stretch",
    )

    if len(gap_2011):
        st.markdown(
            f"Gap narrowed to **${gap_2011.iloc[0]:.1f}T** in 2011, "
            f"then widened to **${gap_2015.iloc[0]:.1f}T** by 2015."
            if len(gap_2015) else ""
        )

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**2009 category declines**")
        st.dataframe(view.category_shock_delta(2008, 2009).reset_index(), width="stretch", hide_index=True)
    with col_b:
        st.markdown("**2015 category declines**")
        st.dataframe(view.category_shock_delta(2014, 2015).reset_index(), width="stretch", hide_index=True)

    oil = view.oil_yearly(OIL_CATEGORY)
    merged = yearly[["year", "trade_trillions"]].merge(oil, on="year")
    st.plotly_chart(
        dual_series_timeline(merged, "trade_trillions", "oil_trillions", "Total", "Oil", "Oil vs total"),
        width="stretch",
    )
    render_data_footer(view, filters)
