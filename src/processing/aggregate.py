"""Aggregation and feature engineering."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.labels import category_label


def flow_by_year(df: pd.DataFrame) -> pd.DataFrame:
    """Import / export (etc.) totals per year."""
    wide = (
        df.groupby(["year", "flow"])["trade_usd"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    for col in wide.columns:
        if col != "year":
            wide[col] = wide[col] / 1e12
    return wide.sort_values("year")


def country_rankings(df: pd.DataFrame, flow: str | None = None, top_n: int | None = 15) -> pd.DataFrame:
    """Rank countries by total trade value."""
    data = df if flow is None else df[df["flow"] == flow]
    out = (
        data.groupby("country_or_area", as_index=False)["trade_usd"]
        .sum()
        .sort_values("trade_usd", ascending=False)
    )
    if top_n is not None:
        out = out.head(top_n)
    out["trade_billions"] = out["trade_usd"] / 1e9
    return out


def trade_balance_by_country(df: pd.DataFrame) -> pd.DataFrame:
    """Export minus import balance per country."""
    exp = df[df["flow"] == "Export"].groupby("country_or_area")["trade_usd"].sum()
    imp = df[df["flow"] == "Import"].groupby("country_or_area")["trade_usd"].sum()
    bal = exp.subtract(imp, fill_value=0).sort_values(ascending=False)
    out = pd.DataFrame({"balance_usd": bal})
    out["balance_billions"] = out["balance_usd"] / 1e9
    return out


def category_totals(df: pd.DataFrame, top_n: int | None = 20) -> pd.DataFrame:
    """Top categories by trade value."""
    out = (
        df.groupby("category", as_index=False)["trade_usd"]
        .sum()
        .sort_values("trade_usd", ascending=False)
    )
    if top_n is not None:
        out = out.head(top_n)
    out["trade_billions"] = out["trade_usd"] / 1e9
    out["short_label"] = out["category"].map(category_label)
    return out


def category_by_year(df: pd.DataFrame, categories: list[str] | None = None) -> pd.DataFrame:
    """Category trade over time (for multi-line charts)."""
    data = df if categories is None else df[df["category"].isin(categories)]
    out = data.groupby(["year", "category"], as_index=False)["trade_usd"].sum()
    out["trade_billions"] = out["trade_usd"] / 1e9
    return out


def country_year_matrix(
    df: pd.DataFrame,
    countries: list[str] | None = None,
    flow: str | None = None,
) -> pd.DataFrame:
    """Country trade trajectory for comparison charts."""
    sub = df
    if countries:
        sub = sub[sub["country_or_area"].isin(countries)]
    if flow:
        sub = sub[sub["flow"] == flow]
    out = sub.groupby(["year", "country_or_area"], as_index=False)["trade_usd"].sum()
    out["trade_billions"] = out["trade_usd"] / 1e9
    return out


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Log-scale correlation of numeric trade fields (sampled for speed)."""
    cols = ["trade_usd", "weight_kg", "quantity"]
    sample = df[cols].dropna()
    sample = sample[(sample > 0).all(axis=1)]
    if len(sample) > 50_000:
        sample = sample.sample(50_000, random_state=42)
    return np.log10(sample).corr()
