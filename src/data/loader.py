"""Data loading, parquet cache, and lazy raw access."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config import AGGREGATE_CATEGORY, DATA_PATH, OUTPUT_DIR, PARQUET_PATH


def _read_source_dataframe() -> pd.DataFrame:
    """Read CSV once into parquet for faster subsequent loads."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if PARQUET_PATH.exists() and PARQUET_PATH.stat().st_mtime >= DATA_PATH.stat().st_mtime:
        return pd.read_parquet(PARQUET_PATH)

    df = pd.read_csv(
        DATA_PATH,
        low_memory=False,
        dtype={"comm_code": str},
    )
    df["year"] = df["year"].astype(int)
    df.to_parquet(PARQUET_PATH, index=False)
    return df


@st.cache_data(show_spinner="Loading trade dataset…", ttl=86400)
def load_trade_data() -> pd.DataFrame:
    """Full dataset — only for explorer / correlation sampling."""
    df = _read_source_dataframe()
    df["unit_price_per_kg"] = df["trade_usd"] / df["weight_kg"].where(df["weight_kg"] > 0)
    return df


@st.cache_data(show_spinner="Sampling records…")
def load_filtered_sample(
    year_range: tuple[int, int],
    countries: tuple[str, ...] | None,
    categories: tuple[str, ...] | None,
    flows: tuple[str, ...] | None,
    exclude_aggregate: bool,
    limit: int,
) -> pd.DataFrame:
    """Lazy raw slice for the data explorer tab only."""
    df = load_trade_data()
    return _apply_row_filters(
        df, year_range, countries, categories, flows, exclude_aggregate
    ).head(limit)


def _apply_row_filters(
    df: pd.DataFrame,
    year_range: tuple[int, int] | None,
    countries: tuple[str, ...] | None,
    categories: tuple[str, ...] | None,
    flows: tuple[str, ...] | None,
    exclude_aggregate: bool,
) -> pd.DataFrame:
    out = df
    if exclude_aggregate:
        out = out[out["category"] != AGGREGATE_CATEGORY]
    if year_range:
        out = out[out["year"].between(year_range[0], year_range[1])]
    if countries:
        out = out[out["country_or_area"].isin(countries)]
    if categories:
        out = out[out["category"].isin(categories)]
    if flows:
        out = out[out["flow"].isin(flows)]
    return out


def apply_filters(
    df: pd.DataFrame,
    year_range: tuple[int, int] | None = None,
    countries: list[str] | None = None,
    categories: list[str] | None = None,
    flows: list[str] | None = None,
    exclude_aggregate: bool = True,
) -> pd.DataFrame:
    """Legacy row filter — prefer FilteredView from src.data.context."""
    return _apply_row_filters(
        df,
        year_range,
        tuple(countries) if countries else None,
        tuple(categories) if categories else None,
        tuple(flows) if flows else None,
        exclude_aggregate,
    )
