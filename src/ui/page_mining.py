"""Data mining / ML lab."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from src.analytics.mining import (
    arima_forecast,
    change_points,
    country_shock_clusters_from_cyf,
    detect_yoy_anomalies,
    isolation_forest_years,
    oil_regression_from_cyf,
    rf_yoy_surprise,
)
from src.data.context import FilteredView
from src.data.loader import load_filtered_sample
from src.processing.aggregate import correlation_matrix
from src.ui.components import render_data_footer
from src.ui.styles import page_header
from src.viz.charts import counterfactual_chart, heatmap_corr, scatter_clusters


def render(view: FilteredView, filters: dict) -> None:
    page_header("Advanced models", "Anomaly detection, forecasting, clustering — for analysts.")
    yearly = view.yearly_summary()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Anomalies", "Forecast", "Clusters", "Correlations", "Oil model"]
    )

    with tab1:
        z = st.slider("YoY z threshold", 1.0, 3.0, 1.5, 0.1)
        yoy_anom = detect_yoy_anomalies(yearly, z)
        iso = isolation_forest_years(yearly, contamination=0.12)
        c1, c2 = st.columns(2)
        with c1:
            st.dataframe(
                yoy_anom.loc[yoy_anom["is_anomaly"], ["year", "yoy_pct", "yoy_z"]],
                width="stretch",
                hide_index=True,
            )
        with c2:
            st.dataframe(
                iso.loc[iso["is_anomaly"], ["year", "trade_trillions", "yoy_pct"]],
                width="stretch",
                hide_index=True,
            )

    with tab2:
        train_end = st.number_input("ARIMA train through", value=min(2007, view.year_range[1] - 1))
        if st.button("Run ARIMA forecast", type="primary"):
            counter = arima_forecast(yearly, int(train_end))
            st.dataframe(counter.round(2), width="stretch", hide_index=True)
            st.plotly_chart(
                counterfactual_chart(
                    counter["year"].tolist(),
                    counter["trade_trillions"].tolist(),
                    counter["forecast_trillions"].tolist(),
                    f"Actual vs forecast (train ≤ {train_end})",
                ),
                width="stretch",
            )
        if st.button("Run RF YoY surprise"):
            st.dataframe(rf_yoy_surprise(yearly, int(train_end)).round(1), width="stretch", hide_index=True)
        pen = st.slider("Change-point penalty", 1.0, 30.0, 10.0)
        if len(yearly) >= 5:
            st.write("Break years:", change_points(yearly["trade_trillions"].values, yearly["year"].values, pen))

    with tab3:
        y1a, y1b = st.number_input("Shock A from", value=2008), st.number_input("Shock A to", value=2009)
        y2a, y2b = st.number_input("Shock B from", value=2014), st.number_input("Shock B to", value=2015)
        if st.button("Cluster countries"):
            shocks, summary, k, sil = country_shock_clusters_from_cyf(
                view.country_year_flow, (int(y1a), int(y1b)), (int(y2a), int(y2b))
            )
            st.write(f"k={k}, silhouette={sil:.2f}")
            st.dataframe(summary, width="stretch")
            plot_df = shocks.reset_index()
            st.plotly_chart(
                scatter_clusters(
                    plot_df, "shock_a_pct", "shock_b_pct", "cluster",
                    "Country clusters", hover_name="country_or_area",
                ),
                width="stretch",
            )

    with tab4:
        if st.button("Compute correlation (sampled)"):
            sample = load_filtered_sample(
                filters["year_range"], filters["countries"], filters["categories"],
                filters["flows"], filters["exclude_aggregate"], 50_000,
            )
            st.plotly_chart(heatmap_corr(correlation_matrix(sample)), width="stretch")

    with tab5:
        reg_df, model, r2 = oil_regression_from_cyf(view.category_year_flow)
        st.metric("R²", f"{r2*100:.1f}%")
        st.metric("Slope", f"{model.coef_[0]:.2f}")
        st.dataframe(reg_df.round(3), width="stretch", hide_index=True)

    render_data_footer(view, filters)
