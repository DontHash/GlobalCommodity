"""Country export growth trends and underlying drivers."""

from __future__ import annotations

import streamlit as st

from src.analytics.growth import ARCHETYPES, country_growth_profiles, export_change_drivers
from src.data.context import FilteredView
from src.ui.components import render_data_footer, section
from src.ui.styles import page_header
from src.viz.charts import bar_chart, driver_waterfall, line_chart, yoy_bar_chart


def render(view: FilteredView, filters: dict) -> None:
    page_header(
        "Country growth",
        "How fast or sudden did exports grow — and which goods or volumes drove it?",
    )

    years = list(range(view.year_range[0], view.year_range[1] + 1))
    export_series = view.country_export_series()

    tab_overview, tab_detail, tab_drivers = st.tabs(
        ["Growth profiles", "Country trends", "Underlying drivers"]
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

    render_data_footer(view, filters)
