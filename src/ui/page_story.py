"""Optional guided story view."""

from __future__ import annotations

import streamlit as st

from config import OIL_CATEGORY
from src.analytics.mining import arima_forecast, pick_arima_train_end
from src.analytics.story import shock_events
from src.data.context import FilteredView
from src.ui.components import render_data_footer, section
from src.ui.styles import page_header
from src.ui.tables import show_category_changes, show_macro_events
from src.viz.charts import counterfactual_chart, dual_series_timeline


def render(view: FilteredView, filters: dict) -> None:
    page_header(
        "Case study",
        "Ghost Boom narrative — pre-set to 2007–2015 for full context. Use sidebar if your range differs.",
    )

    yearly = view.yearly_summary()
    if yearly.empty:
        st.warning("No data in the selected year range. Try **Full history** or **Commodity slowdown** preset.")
        render_data_footer(view, filters)
        return

    events = shock_events(yearly)
    train_end = pick_arima_train_end(yearly, preferred=2007)
    counter = arima_forecast(yearly, train_end) if train_end else None

    peak = yearly.loc[yearly["trade_trillions"].idxmax()]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Peak year", f"{int(peak['year'])}")
    c2.metric("Peak volume", f"${peak['trade_trillions']:.1f}T")

    if counter is not None and not counter.empty:
        gap_2015 = counter.loc[counter["year"] == 2015, "gap_trillions"]
        cum = counter.loc[counter["gap_trillions"] < 0, "gap_trillions"].sum()
        c3.metric("2015 vs trend", f"${gap_2015.iloc[0]:.1f}T" if len(gap_2015) else "—")
        c4.metric("Cumulative below trend", f"${abs(cum):.0f}T")
    else:
        c3.metric("2015 vs trend", "—")
        c4.metric("Cumulative below trend", "—")
        st.info(
            "ARIMA counterfactual needs at least 3 training years before the forecast window. "
            "Widen the year range (e.g. **Full history** preset) to see the Ghost Boom chart."
        )

    section("Macro events")
    show_macro_events(events)

    if counter is not None and not counter.empty:
        section("Actual vs counterfactual trend", f"Model trained through {train_end}")
        st.plotly_chart(
            counterfactual_chart(
                counter["year"].tolist(),
                counter["trade_trillions"].tolist(),
                counter["forecast_trillions"].tolist(),
                "Trade: actual vs pre-crisis trajectory",
            ),
            width="stretch",
        )
        gap_2011 = counter.loc[counter["year"] == 2011, "gap_trillions"]
        gap_2015 = counter.loc[counter["year"] == 2015, "gap_trillions"]
        if len(gap_2011) and len(gap_2015):
            st.markdown(
                f"Gap vs trend narrowed to **${gap_2011.iloc[0]:.1f}T** in 2011, "
                f"then widened to **${gap_2015.iloc[0]:.1f}T** by 2015."
            )

    col_a, col_b = st.columns(2)
    with col_a:
        show_category_changes(
            view.category_shock_delta(2008, 2009),
            "2009 crisis — largest category declines",
            "2008 → 2009",
        )
    with col_b:
        show_category_changes(
            view.category_shock_delta(2014, 2015),
            "2015 slowdown — largest category declines",
            "2014 → 2015",
        )

    oil = view.oil_yearly(OIL_CATEGORY)
    if not oil.empty:
        section("Oil vs total trade")
        merged = yearly[["year", "trade_trillions"]].merge(oil, on="year")
        st.plotly_chart(
            dual_series_timeline(
                merged, "trade_trillions", "oil_trillions", "Total", "Oil", "Oil share of trade value"
            ),
            width="stretch",
        )

    render_data_footer(view, filters)
