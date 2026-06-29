"""Country export growth trends and underlying drivers."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analytics.forecast import compute_target_plan, regression_forecast
from src.analytics.growth import ARCHETYPES, country_growth_profiles, export_change_drivers
from src.data.context import FilteredView
from src.ui.components import render_data_footer, section
from src.ui.styles import page_header
from src.viz.charts import bar_chart, driver_waterfall, line_chart, target_forecast_chart, yoy_bar_chart


def render(view: FilteredView, filters: dict) -> None:
    page_header(
        "Country growth",
        "How fast or sudden did exports grow — and which goods or volumes drove it?",
    )

    years = list(range(view.year_range[0], view.year_range[1] + 1))
    export_series = view.country_export_series()

    tab_overview, tab_detail, tab_drivers, tab_target = st.tabs(
        ["Growth profiles", "Country trends", "Underlying drivers", "Target & forecast"]
    )

    with tab_overview:
        section("Export growth patterns", "Classify countries by speed and volatility over a window.")
        c1, c2, c3 = st.columns(3)
        with c1:
            y_from = st.selectbox("From", years, index=0, key="growth_from")
        with c2:
            y_to = st.selectbox("To", years, index=len(years) - 1, key="growth_to")
        with c3:
            archetype_filter = st.multiselect(
                "Filter archetype",
                list(ARCHETYPES),
                default=[],
                key="growth_archetype",
            )
        if y_from >= y_to:
            st.warning("Pick a later 'To' year.")
        else:
            profiles = country_growth_profiles(export_series, int(y_from), int(y_to))
            if archetype_filter:
                profiles = profiles[profiles["archetype"].isin(archetype_filter)]
            if profiles.empty:
                st.info("No export data for this period.")
            else:
                c1, c2 = st.columns([1, 1])
                with c1:
                    st.plotly_chart(
                        bar_chart(
                            profiles["archetype"]
                            .value_counts()
                            .reset_index(name="count")
                            .rename(columns={"index": "archetype"}),
                            "archetype",
                            "count",
                            title="Countries by growth type",
                        ),
                        width="stretch",
                    )
                with c2:
                    st.plotly_chart(
                        bar_chart(
                            profiles.head(15).sort_values("cagr_pct"),
                            "cagr_pct",
                            "country",
                            title="Top 15 by export CAGR (%)",
                            orientation="h",
                        ),
                        width="stretch",
                    )
                st.dataframe(
                    profiles[
                        [
                            "country",
                            "archetype",
                            "cagr_pct",
                            "total_change_pct",
                            "yoy_std",
                            "shock_year",
                            "shock_yoy_pct",
                            "export_start_b",
                            "export_end_b",
                        ]
                    ].rename(
                        columns={
                            "cagr_pct": "CAGR %",
                            "total_change_pct": "Total change %",
                            "yoy_std": "YoY volatility",
                            "shock_year": "Largest shock year",
                            "shock_yoy_pct": "Shock YoY %",
                            "export_start_b": "Export start ($B)",
                            "export_end_b": "Export end ($B)",
                        }
                    ),
                    width="stretch",
                    hide_index=True,
                )

    with tab_detail:
        section("Detailed export trends", "Select countries to compare trajectories and year-over-year swings.")
        options = sorted(export_series["country_or_area"].unique())
        default = options[:3] if len(options) >= 3 else options
        selected = st.multiselect(
            "Countries",
            options,
            default=default,
            max_selections=6,
            key="growth_countries",
        )
        if not selected:
            st.info("Select at least one country.")
        else:
            detail = export_series[export_series["country_or_area"].isin(selected)]
            st.plotly_chart(
                line_chart(
                    detail,
                    "year",
                    "trade_billions",
                    color="country_or_area",
                    title="Export value over time",
                    y_unit="B",
                ),
                width="stretch",
            )
            focus = st.selectbox("Focus country for YoY detail", selected, key="growth_focus")
            focus_df = detail[detail["country_or_area"] == focus].dropna(subset=["yoy_pct"])
            if not focus_df.empty:
                st.plotly_chart(
                    yoy_bar_chart(
                        focus_df,
                        "year",
                        "yoy_pct",
                        title=f"{focus} — year-over-year export change",
                    ),
                    width="stretch",
                )
                prof = country_growth_profiles(
                    export_series[export_series["country_or_area"] == focus],
                    view.year_range[0],
                    view.year_range[1],
                )
                if not prof.empty:
                    row = prof.iloc[0]
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Growth type", row["archetype"])
                    m2.metric("CAGR", f"{row['cagr_pct']:+.1f}%")
                    m3.metric("Total change", f"{row['total_change_pct']:+.1f}%")
                    shock = (
                        f"{int(row['shock_year'])} ({row['shock_yoy_pct']:+.1f}%)"
                        if row["shock_year"]
                        else "—"
                    )
                    m4.metric("Largest shock", shock)

    with tab_drivers:
        section(
            "Probable underlying causes",
            "Break export change into commodity categories, volumes (tonnes), and unit prices.",
        )
        c1, c2, c3 = st.columns(3)
        driver_options = sorted(export_series["country_or_area"].unique())
        with c1:
            driver_country = st.selectbox("Country", driver_options, key="driver_country")
        with c2:
            d_from = st.selectbox("From", years, index=max(0, len(years) - 5), key="driver_from")
        with c3:
            d_to = st.selectbox("To", years, index=len(years) - 1, key="driver_to")
        if d_from >= d_to:
            st.warning("Pick a later 'To' year.")
        else:
            drivers, summary = export_change_drivers(
                view.country_category_year,
                driver_country,
                int(d_from),
                int(d_to),
                top_n=10,
            )
            if not summary:
                st.info("No export category data for this country and period.")
            else:
                if summary.get("total_change_pct") is not None:
                    st.metric(
                        f"Export change ({d_from}→{d_to})",
                        f"${summary['total_change_b']:+.2f}B",
                        f"{summary['total_change_pct']:+.1f}%",
                    )
                st.info(summary["narrative"])
                if not drivers.empty:
                    st.plotly_chart(
                        driver_waterfall(drivers, title=f"{driver_country} — category contributions"),
                        width="stretch",
                    )
                    display = drivers[
                        [
                            "short_label",
                            "value_change_b",
                            "weight_change_k_t",
                            "volume_effect_b",
                            "price_effect_b",
                            "primary_driver",
                        ]
                    ].rename(
                        columns={
                            "short_label": "Category",
                            "value_change_b": "Value change ($B)",
                            "weight_change_k_t": "Weight change (kt)",
                            "volume_effect_b": "Volume effect ($B)",
                            "price_effect_b": "Price effect ($B)",
                            "primary_driver": "Primary driver",
                        }
                    )
                    st.dataframe(display.round(2), width="stretch", hide_index=True)
                    st.caption(
                        "**Volume effect** ≈ change in kg shipped × average unit price. "
                        "**Price effect** ≈ change in USD/kg × starting volume. "
                        "Use together to see whether growth came from shipping more or higher unit values."
                    )

    with tab_target:
        section(
            "Export target planner",
            "Set a future goal and see required annual growth, volume increase, and a 5-year model forecast.",
        )
        options = sorted(export_series["country_or_area"].unique())
        if not options:
            st.info("No export data in the current filter.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                target_country = st.selectbox("Country", options, key="target_country")
            with c2:
                metric_choice = st.selectbox(
                    "Metric",
                    [("value", "Export value ($B)"), ("volume", "Export volume (kt)")],
                    format_func=lambda x: x[1],
                    key="target_metric",
                )
            metric_key = metric_choice[0]
            value_col = "trade_billions" if metric_key == "value" else "weight_kt"
            unit_label = "Billions USD" if metric_key == "value" else "Thousand tonnes (kt)"

            traj = view.country_export_trajectory(target_country)
            if traj.empty:
                st.warning(f"No export trajectory for {target_country} in this filter.")
            else:
                avail_years = traj["year"].tolist()
                with c3:
                    baseline_year = st.selectbox(
                        "Baseline year",
                        avail_years,
                        index=len(avail_years) - 1,
                        key="target_baseline",
                    )
                baseline_row = traj[traj["year"] == baseline_year].iloc[0]
                baseline_val = float(baseline_row[value_col])

                c4, c5, c6 = st.columns(3)
                with c4:
                    target_year = st.number_input(
                        "Target year",
                        min_value=int(baseline_year) + 1,
                        max_value=int(baseline_year) + 20,
                        value=min(int(baseline_year) + 5, int(baseline_year) + 20),
                        key="target_year",
                    )
                with c5:
                    default_target = round(baseline_val * 1.5, 2) if baseline_val > 0 else 1.0
                    target_val = st.number_input(
                        f"Target ({'$B' if metric_key == 'value' else 'kt'})",
                        min_value=0.01,
                        value=float(default_target),
                        step=max(0.1, default_target * 0.05),
                        format="%.2f",
                        key="target_value",
                    )
                with c6:
                    forecast_horizon = st.slider("Forecast horizon (years)", 3, 10, 5, key="fc_horizon")

                if target_val <= baseline_val:
                    st.warning("Target should exceed the baseline to compute a growth plan.")
                else:
                    plan = compute_target_plan(
                        target_country,
                        metric_key,
                        int(baseline_year),
                        baseline_val,
                        int(target_year),
                        float(target_val),
                    )
                    fc = regression_forecast(
                        traj,
                        value_col,
                        int(baseline_year),
                        horizon=int(forecast_horizon),
                    )

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric(
                        f"Baseline ({baseline_year})",
                        f"${baseline_val:.1f}B" if metric_key == "value" else f"{baseline_val:,.1f} kt",
                    )
                    m2.metric(
                        f"Target ({target_year})",
                        f"${target_val:.1f}B" if metric_key == "value" else f"{target_val:,.1f} kt",
                    )
                    if plan:
                        m3.metric("Required CAGR", f"{plan.required_cagr_pct:+.1f}%")
                        inc_label = (
                            f"${plan.required_annual_increase:.2f}B/yr"
                            if metric_key == "value"
                            else f"{plan.required_annual_increase:,.1f} kt/yr"
                        )
                        m4.metric("Avg. annual increase", inc_label)

                    if plan and fc:
                        fc_end = fc.series.iloc[-1]["value"]
                        gap = target_val - fc_end
                        st.caption(
                            f"At the current log-linear trend ({fc.slope_per_year:+.1f}%/yr, R²={fc.r2:.2f}), "
                            f"{target_country} would reach "
                            f"{'$' + f'{fc_end:.1f}B' if metric_key == 'value' else f'{fc_end:,.1f} kt'} "
                            f"by {int(fc.series['year'].max())} — "
                            f"{'above' if gap < 0 else 'below'} target by "
                            f"{'$' + f'{abs(gap):.1f}B' if metric_key == 'value' else f'{abs(gap):,.1f} kt'}."
                        )

                    actual = traj.rename(columns={value_col: "value"})[["year", "value"]].copy()
                    actual["series"] = "actual"

                    st.plotly_chart(
                        target_forecast_chart(
                            actual,
                            plan.path if plan else pd.DataFrame(),
                            fc.series if fc else pd.DataFrame(),
                            title=f"{target_country} — exports vs target & forecast",
                            y_axis_title=unit_label,
                            baseline_year=int(baseline_year),
                        ),
                        width="stretch",
                    )

                    if plan:
                        compare = plan.path.copy()
                        compare = compare.rename(columns={"value": "required"})
                        if fc is not None:
                            fc_tbl = fc.series[fc.series["year"] > baseline_year][["year", "value"]].rename(
                                columns={"value": "forecast"}
                            )
                            compare = compare.merge(fc_tbl, on="year", how="left")
                            compare["gap_to_target"] = compare["required"] - compare["forecast"]
                        st.dataframe(
                            compare.round(2),
                            width="stretch",
                            hide_index=True,
                            column_config={
                                "year": st.column_config.NumberColumn("Year", format="%d"),
                                "required": st.column_config.NumberColumn(
                                    f"Required ({'$B' if metric_key == 'value' else 'kt'})",
                                    format="%.2f",
                                ),
                                "forecast": st.column_config.NumberColumn(
                                    f"Forecast ({'$B' if metric_key == 'value' else 'kt'})",
                                    format="%.2f",
                                ),
                                "gap_to_target": st.column_config.NumberColumn("Gap (req − forecast)", format="%.2f"),
                            },
                        )
                        st.caption(
                            "Target years are forward projections beyond the UN Comtrade series (ends 2016). "
                            "Forecast uses log-linear regression on pre-baseline history."
                        )
                    if fc is None:
                        st.info(
                            "Need at least 3 positive baseline years for regression forecast. "
                            "Widen the year range or pick another baseline."
                        )

    render_data_footer(view, filters)
