"""Aggregation and feature engineering."""

from __future__ import annotations

import numpy as np
import pandas as pd


def yearly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Total trade and record counts per year."""
    out = (
        df.groupby("year", as_index=False)
        .agg(
            trade_usd=("trade_usd", "sum"),
            records=("trade_usd", "count"),
            countries=("country_or_area", "nunique"),
            commodities=("commodity", "nunique"),
        )
        .sort_values("year")
    )
    out["trade_trillions"] = out["trade_usd"] / 1e12
    out["yoy_pct"] = out["trade_usd"].pct_change() * 100
    return out


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


def country_rankings(df: pd.DataFrame, flow: str | None = None, top_n: int = 15) -> pd.DataFrame:
    """Rank countries by total trade value."""
    data = df if flow is None else df[df["flow"] == flow]
    out = (
        data.groupby("country_or_area", as_index=False)["trade_usd"]
        .sum()
        .sort_values("trade_usd", ascending=False)
        .head(top_n)
    )
    out["trade_billions"] = out["trade_usd"] / 1e9
    return out


def trade_balance_by_country(df: pd.DataFrame) -> pd.DataFrame:
    """Export minus import balance per country."""
    exp = df[df["flow"] == "Export"].groupby("country_or_area")["trade_usd"].sum()
    imp = df[df["flow"] == "Import"].groupby("country_or_area")["trade_usd"].sum()
    bal = (exp - imp).sort_values(ascending=False)
    out = pd.DataFrame({"balance_usd": bal})
    out["balance_billions"] = out["balance_usd"] / 1e9
    return out


def category_totals(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """Top categories by trade value."""
    out = (
        df.groupby("category", as_index=False)["trade_usd"]
        .sum()
        .sort_values("trade_usd", ascending=False)
        .head(top_n)
    )
    out["trade_billions"] = out["trade_usd"] / 1e9
    out["short_label"] = out["category"].str.replace(r"^\d+_", "", regex=True).str[:40]
    return out


def category_by_year(df: pd.DataFrame, categories: list[str] | None = None) -> pd.DataFrame:
    """Category trade over time (for multi-line charts)."""
    data = df if categories is None else df[df["category"].isin(categories)]
    out = data.groupby(["year", "category"], as_index=False)["trade_usd"].sum()
    out["trade_billions"] = out["trade_usd"] / 1e9
    return out


def country_year_matrix(df: pd.DataFrame, countries: list[str]) -> pd.DataFrame:
    """Country trade trajectory for comparison charts."""
    sub = df[df["country_or_area"].isin(countries)]
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


def commodity_search(df: pd.DataFrame, query: str, limit: int = 50) -> pd.DataFrame:
    """Search commodities by name or HS code."""
    q = query.strip().lower()
    mask = df["commodity"].str.lower().str.contains(q, na=False) | df["comm_code"].str.contains(q, na=False)
    out = (
        df.loc[mask]
        .groupby(["comm_code", "commodity", "category"], as_index=False)
        .agg(trade_usd=("trade_usd", "sum"), records=("trade_usd", "count"))
        .sort_values("trade_usd", ascending=False)
        .head(limit)
    )
    out["trade_millions"] = out["trade_usd"] / 1e6
    return out
