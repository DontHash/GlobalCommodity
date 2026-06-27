"""Commodity exploration."""

from __future__ import annotations

import streamlit as st

from config import TOP_N
from src.data.context import FilteredView
from src.ui.components import render_data_footer
from src.ui.styles import page_header
from src.viz.charts import line_chart, treemap_categories


def render(view: FilteredView, filters: dict) -> None:
    page_header("Products", "Which commodity categories drive trade value?")
    tab1, tab2, tab3 = st.tabs(["Categories", "Trends", "Search"])

    with tab1:
        top_n = st.slider("Top categories", 5, 30, TOP_N, key="cat_n")
        cats = view.category_totals(top_n=top_n)
        st.plotly_chart(treemap_categories(cats, title="Trade by category"), width="stretch")

    with tab2:
        all_cats = sorted(view.category_year_flow["category"].unique())
        pick = st.multiselect("Plot categories", all_cats, default=all_cats[:5], max_selections=8)
        if pick:
            trend = view.category_by_year(pick)
            st.plotly_chart(
                line_chart(trend, "year", "trade_billions", color="category", title="Category trends"),
                width="stretch",
            )

    with tab3:
        query = st.text_input("Commodity or HS code", placeholder="oil · 2709 · wheat")
        if query:
            st.dataframe(view.commodity_search(query), width="stretch", hide_index=True)
        else:
            st.info("Enter a search term.")

    render_data_footer(view, filters)
