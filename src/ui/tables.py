"""Formatted tables for executive and root-cause views."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.utils.labels import category_label, format_billions, format_pct


def _prep_category_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if "category" in out.columns:
        out["Category"] = out["category"].map(category_label)
    elif out.index.name == "category":
        out = out.reset_index()
        out["Category"] = out["category"].map(category_label)
    if "short_label" in out.columns and "Category" not in out.columns:
        out["Category"] = out["short_label"].map(lambda s: str(s).replace("_", " ").title())

    if "change_billions" in out.columns:
        out["Change ($B)"] = out["change_billions"].round(1)
    if "change_pct" in out.columns:
        out["Change (%)"] = out["change_pct"].round(1)

    cols = [c for c in ["Category", "Change ($B)", "Change (%)"] if c in out.columns]
    return out[cols] if cols else out


def _prep_country_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    name_col = "country" if "country" in out.columns else "country_or_area"
    out["Country"] = out[name_col]
    if "change_billions" in out.columns:
        out["Change ($B)"] = out["change_billions"].round(1)
    elif name_col in out.columns and out.columns[-1] != "Country":
        pass
    return out[["Country", "Change ($B)"]] if "Change ($B)" in out.columns else out


def show_category_changes(
    df: pd.DataFrame,
    title: str,
    subtitle: str = "",
    empty_message: str = "No categories in this direction for the selected period.",
) -> None:
    st.markdown(f"**{title}**")
    if subtitle:
        st.caption(subtitle)
    prepared = _prep_category_df(df)
    if prepared.empty:
        st.info(empty_message)
        return
    st.dataframe(
        prepared,
        width="stretch",
        hide_index=True,
        column_config={
            "Change ($B)": st.column_config.NumberColumn(format="%.1f"),
            "Change (%)": st.column_config.NumberColumn(format="%.1f"),
        },
    )


def show_macro_events(df: pd.DataFrame) -> None:
    """Formatted shock / peak timeline for case study."""
    if df.empty:
        st.info("No macro events in the selected year range.")
        return
    out = df.copy()
    out["Event"] = out["event"].str.replace("_", " ").str.title()
    out["Period"] = out.apply(
        lambda r: str(int(r["from_year"]))
        if pd.isna(r.get("to_year"))
        else f"{int(r['from_year'])} → {int(r['to_year'])}",
        axis=1,
    )
    out["Change (%)"] = out["change_pct"]
    out["Volume ($T)"] = out["volume_trillions"]
    display = out[["Event", "Period", "Change (%)", "Volume ($T)"]]
    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        column_config={
            "Change (%)": st.column_config.NumberColumn(format="%.1f"),
            "Volume ($T)": st.column_config.NumberColumn(format="%.2f"),
        },
    )


def show_country_changes(
    df: pd.DataFrame,
    title: str,
    subtitle: str = "",
    empty_message: str = "No countries in this direction for the selected period.",
) -> None:
    st.markdown(f"**{title}**")
    if subtitle:
        st.caption(subtitle)
    prepared = _prep_country_df(df)
    if prepared.empty:
        st.info(empty_message)
        return
    st.dataframe(
        prepared,
        width="stretch",
        hide_index=True,
        column_config={"Change ($B)": st.column_config.NumberColumn(format="%.1f")},
    )
