"""Fast filtered views built from pre-aggregated cubes."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from config import AGGREGATE_CATEGORY
from src.data.cubes import TradeCubes, load_trade_cubes


@dataclass
class FilteredView:
    """All dashboard metrics derived from cubes — no full-table scans."""

    year_range: tuple[int, int]
    exclude_aggregate: bool
    country_year_flow: pd.DataFrame
    category_year_flow: pd.DataFrame
    commodity_totals: pd.DataFrame
    year_records: pd.DataFrame
    has_country_filter: bool = False
    has_category_filter: bool = False

    @property
    def profile(self) -> dict:
        yearly = self.yearly_summary()
        row_est = (
            int(self.year_records["records"].sum())
            if not (self.has_country_filter or self.has_category_filter)
            else None
        )
        return {
            "rows": row_est,
            "countries": self.country_year_flow["country_or_area"].nunique(),
            "year_min": self.year_range[0],
            "year_max": self.year_range[1],
            "commodities": int(self.commodity_totals["comm_code"].nunique()),
            "categories": self.category_year_flow["category"].nunique(),
            "total_trade_usd": float(self.country_year_flow["trade_usd"].sum()),
            "flows": (
                self.country_year_flow.groupby("flow")["trade_usd"]
                .sum()
                .astype(int)
                .to_dict()
            ),
        }

    def yearly_summary(self) -> pd.DataFrame:
        out = (
            self.country_year_flow.groupby("year", as_index=False)
            .agg(
                trade_usd=("trade_usd", "sum"),
                countries=("country_or_area", "nunique"),
            )
            .sort_values("year")
        )
        if not (self.has_country_filter or self.has_category_filter):
            out = out.merge(
                self.year_records[["year", "records", "commodities"]], on="year", how="left"
            )
        out["trade_trillions"] = out["trade_usd"] / 1e12
        out["yoy_pct"] = out["trade_usd"].pct_change() * 100
        return out

    def flow_by_year(self) -> pd.DataFrame:
        wide = (
            self.country_year_flow.groupby(["year", "flow"])["trade_usd"]
            .sum()
            .unstack(fill_value=0)
            .reset_index()
        )
        for col in wide.columns:
            if col != "year":
                wide[col] = wide[col] / 1e12
        return wide.sort_values("year")

    def country_totals(self, flow: str | None = None) -> pd.DataFrame:
        data = self.country_year_flow
        if flow:
            data = data[data["flow"] == flow]
        return (
            data.groupby("country_or_area", as_index=False)["trade_usd"]
            .sum()
            .sort_values("trade_usd", ascending=False)
        )

    def country_year(self, countries: list[str] | None = None) -> pd.DataFrame:
        data = self.country_year_flow
        if countries:
            data = data[data["country_or_area"].isin(countries)]
        return (
            data.groupby(["year", "country_or_area"], as_index=False)["trade_usd"]
            .sum()
        )

    def trade_balance(self) -> pd.DataFrame:
        exp = (
            self.country_year_flow[self.country_year_flow["flow"] == "Export"]
            .groupby("country_or_area")["trade_usd"]
            .sum()
        )
        imp = (
            self.country_year_flow[self.country_year_flow["flow"] == "Import"]
            .groupby("country_or_area")["trade_usd"]
            .sum()
        )
        bal = (exp - imp).sort_values(ascending=False)
        out = pd.DataFrame({"balance_usd": bal})
        out["balance_billions"] = out["balance_usd"] / 1e9
        return out

    def category_totals(self, top_n: int | None = None) -> pd.DataFrame:
        out = (
            self.category_year_flow.groupby("category", as_index=False)["trade_usd"]
            .sum()
            .sort_values("trade_usd", ascending=False)
        )
        out["short_label"] = out["category"].str.replace(r"^\d+_", "", regex=True).str[:40]
        return out.head(top_n) if top_n else out

    def category_by_year(self, categories: list[str] | None = None) -> pd.DataFrame:
        data = self.category_year_flow
        if categories:
            data = data[data["category"].isin(categories)]
        out = data.groupby(["year", "category"], as_index=False)["trade_usd"].sum()
        out["trade_billions"] = out["trade_usd"] / 1e9
        return out

    def map_metrics(self, year: int, metric: str) -> pd.DataFrame:
        """Country-level values for choropleth. Includes metric_label column."""
        cy = self.country_year_flow[self.country_year_flow["year"] == year]
        labels = {
            "total_trade": "Trade (billions USD)",
            "trade_balance": "Balance (billions USD)",
            "exports": "Exports (billions USD)",
            "imports": "Imports (billions USD)",
        }
        label = labels.get(metric, "Value")

        if metric == "total_trade":
            out = cy.groupby("country_or_area", as_index=False)["trade_usd"].sum()
        elif metric == "trade_balance":
            exp = cy[cy["flow"] == "Export"].groupby("country_or_area")["trade_usd"].sum()
            imp = cy[cy["flow"] == "Import"].groupby("country_or_area")["trade_usd"].sum()
            out = (exp - imp).reset_index()
            out.columns = ["country_or_area", "trade_usd"]
        elif metric == "exports":
            out = cy[cy["flow"] == "Export"].groupby("country_or_area", as_index=False)["trade_usd"].sum()
        else:
            out = cy[cy["flow"] == "Import"].groupby("country_or_area", as_index=False)["trade_usd"].sum()

        out["value"] = out["trade_usd"] / 1e9
        out["metric_label"] = label
        return out

    def country_shock_frame(self, y1: int, y2: int) -> pd.DataFrame:
        b = self.country_year_flow[self.country_year_flow["year"] == y1]
        a = self.country_year_flow[self.country_year_flow["year"] == y2]
        b_tot = b.groupby("country_or_area")["trade_usd"].sum()
        a_tot = a.groupby("country_or_area")["trade_usd"].sum()
        common = b_tot.index.intersection(a_tot.index)
        pct = ((a_tot[common] / b_tot[common]) - 1) * 100
        return pct.rename("change_pct").reset_index()

    def commodity_search(self, query: str, limit: int = 50) -> pd.DataFrame:
        q = query.strip().lower()
        ct = self.commodity_totals
        mask = ct["commodity"].str.lower().str.contains(q, na=False) | ct["comm_code"].str.contains(
            q, na=False
        )
        out = ct.loc[mask].sort_values("trade_usd", ascending=False).head(limit)
        out["trade_millions"] = out["trade_usd"] / 1e6
        return out

    def category_shock_delta(self, y1: int, y2: int, top_n: int = 10) -> pd.DataFrame:
        b = self.category_year_flow[self.category_year_flow["year"] == y1]
        a = self.category_year_flow[self.category_year_flow["year"] == y2]
        b_tot = b.groupby("category")["trade_usd"].sum()
        a_tot = a.groupby("category")["trade_usd"].sum()
        delta = (a_tot - b_tot).sort_values()
        out = pd.DataFrame({"change_usd": delta, "change_billions": delta / 1e9})
        out["change_pct"] = ((a_tot / b_tot) - 1).reindex(delta.index) * 100
        out["short_label"] = out.index.str.replace(r"^\d+_", "", regex=True).str[:45]
        return out.head(top_n)

    def oil_yearly(self, oil_category: str) -> pd.DataFrame:
        oil = (
            self.category_year_flow[self.category_year_flow["category"] == oil_category]
            .groupby("year")["trade_usd"]
            .sum()
            .div(1e12)
            .reset_index(name="oil_trillions")
        )
        return oil


def _filter_cube_frame(
    df: pd.DataFrame,
    year_range: tuple[int, int],
    countries: tuple[str, ...] | None,
    categories: tuple[str, ...] | None,
    flows: tuple[str, ...] | None,
    exclude_aggregate: bool,
    category_col: str | None = None,
) -> pd.DataFrame:
    out = df[df["year"].between(year_range[0], year_range[1])]
    if countries:
        if "country_or_area" in out.columns:
            out = out[out["country_or_area"].isin(countries)]
    if category_col and categories:
        out = out[out[category_col].isin(categories)]
    if exclude_aggregate and category_col == "category":
        out = out[out["category"] != AGGREGATE_CATEGORY]
    if flows and "flow" in out.columns:
        out = out[out["flow"].isin(flows)]
    return out


@st.cache_data(show_spinner=False, ttl=3600)
def build_filtered_view(
    year_range: tuple[int, int],
    countries: tuple[str, ...] | None,
    categories: tuple[str, ...] | None,
    flows: tuple[str, ...] | None,
    exclude_aggregate: bool,
) -> FilteredView:
    cubes = load_trade_cubes()
    cyf = _filter_cube_frame(
        cubes.country_year_flow, year_range, countries, None, flows, False
    )
    catyf = _filter_cube_frame(
        cubes.category_year_flow,
        year_range,
        None,
        categories,
        flows,
        exclude_aggregate,
        category_col="category",
    )
    ct = cubes.commodity_totals
    if categories:
        ct = ct[ct["category"].isin(categories)]
    yr = cubes.year_records[
        cubes.year_records["year"].between(year_range[0], year_range[1])
    ]
    return FilteredView(
        year_range=year_range,
        exclude_aggregate=exclude_aggregate,
        country_year_flow=cyf,
        category_year_flow=catyf,
        commodity_totals=ct,
        year_records=yr,
        has_country_filter=bool(countries),
        has_category_filter=bool(categories),
    )
