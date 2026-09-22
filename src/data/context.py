"""Fast filtered views built from pre-aggregated cubes."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from config import AGGREGATE_CATEGORY
from src.data.cubes import TradeCubes, load_trade_cubes
from src.data.loader import load_scoped_commodity_totals
from src.processing.aggregate import (
    category_by_year as aggregate_category_by_year,
    category_totals as aggregate_category_totals,
    country_rankings,
    country_year_matrix,
    flow_by_year as aggregate_flow_by_year,
    trade_balance_by_country,
)
from src.utils.labels import category_label


@dataclass
class FilteredView:
    """All dashboard metrics derived from cubes — no full-table scans."""

    year_range: tuple[int, int]
    exclude_aggregate: bool
    country_year_flow: pd.DataFrame
    category_year_flow: pd.DataFrame
    country_category_year: pd.DataFrame
    commodity_totals: pd.DataFrame
    year_records: pd.DataFrame
    countries: tuple[str, ...] | None = None
    categories: tuple[str, ...] | None = None
    flows: tuple[str, ...] | None = None
    total_basis: str = "Authoritative country totals"
    is_conditional_basket: bool = False
    has_country_filter: bool = False
    has_category_filter: bool = False

    @property
    def profile(self) -> dict:
        row_est = int(self.year_records["records"].sum()) if not self.year_records.empty else 0
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
        if not self.year_records.empty:
            out = out.merge(
                self.year_records[["year", "records", "commodities"]], on="year", how="left"
            )
        out["trade_trillions"] = out["trade_usd"] / 1e12
        out["yoy_pct"] = out["trade_usd"].pct_change() * 100
        return out

    def flow_by_year(self) -> pd.DataFrame:
        return aggregate_flow_by_year(self.country_year_flow)

    def country_totals(self, flow: str | None = None) -> pd.DataFrame:
        return country_rankings(self.country_year_flow, flow, top_n=None).drop(
            columns="trade_billions"
        )

    def country_year(self, countries: list[str] | None = None, flow: str | None = None) -> pd.DataFrame:
        return country_year_matrix(self.country_year_flow, countries, flow).drop(
            columns="trade_billions"
        )

    def country_export_series(self, countries: list[str] | None = None) -> pd.DataFrame:
        """Export value trajectory per country (billions USD)."""
        out = self.country_year(countries=countries, flow="Export")
        out["trade_billions"] = out["trade_usd"] / 1e9
        out["yoy_pct"] = out.groupby("country_or_area")["trade_usd"].pct_change() * 100
        return out.sort_values(["country_or_area", "year"])

    def country_export_trajectory(self, country: str) -> pd.DataFrame:
        """Export value and shipped weight per year for one country."""
        data = self.country_category_year[
            (self.country_category_year["country_or_area"] == country)
            & (self.country_category_year["flow"] == "Export")
        ]
        if data.empty:
            return pd.DataFrame(columns=["year", "trade_usd", "trade_billions", "weight_kg", "weight_kt"])
        out = data.groupby("year", as_index=False).agg(
            trade_usd=("trade_usd", "sum"),
            weight_kg=("weight_kg", "sum"),
        )
        out["trade_billions"] = out["trade_usd"] / 1e9
        out["weight_kt"] = out["weight_kg"] / 1e6
        return out.sort_values("year")

    def trade_balance(self) -> pd.DataFrame:
        return trade_balance_by_country(self.country_year_flow)

    def category_totals(self, top_n: int | None = None) -> pd.DataFrame:
        return aggregate_category_totals(self.category_year_flow, top_n)

    def category_by_year(self, categories: list[str] | None = None) -> pd.DataFrame:
        return aggregate_category_by_year(self.category_year_flow, categories)

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
            out = exp.subtract(imp, fill_value=0).reset_index()
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
        codes = tuple(ct.loc[mask, "comm_code"].astype(str).unique())
        out = load_scoped_commodity_totals(
            codes,
            self.year_range,
            self.countries,
            self.categories,
            self.flows,
            self.exclude_aggregate,
        ).head(limit).copy()
        out["trade_millions"] = out["trade_usd"] / 1e6
        return out

    def category_change_table(self, y1: int, y2: int) -> pd.DataFrame:
        """Full category delta table between two years (signed)."""
        b = self.category_year_flow[self.category_year_flow["year"] == y1]
        a = self.category_year_flow[self.category_year_flow["year"] == y2]
        b_tot = b.groupby("category")["trade_usd"].sum()
        a_tot = a.groupby("category")["trade_usd"].sum()
        categories = b_tot.index.union(a_tot.index)
        before = b_tot.reindex(categories, fill_value=0)
        after = a_tot.reindex(categories, fill_value=0)
        delta = after - before
        out = pd.DataFrame(
            {
                "category": delta.index,
                "change_usd": delta.values,
                "change_billions": delta.values / 1e9,
                "change_pct": ((after / before.where(before > 0)) - 1).values * 100,
            }
        )
        out["short_label"] = out["category"].map(category_label)
        return out.sort_values("change_billions")

    def category_shock_delta(self, y1: int, y2: int, top_n: int = 10) -> pd.DataFrame:
        """Largest declines only (legacy helper)."""
        table = self.category_change_table(y1, y2)
        return table.nsmallest(top_n, "change_billions")

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


@lru_cache(maxsize=128)
def build_filtered_view(
    year_range: tuple[int, int],
    countries: tuple[str, ...] | None,
    categories: tuple[str, ...] | None,
    flows: tuple[str, ...] | None,
    exclude_aggregate: bool,
) -> FilteredView:
    return _build_filtered_view_from_cubes(
        load_trade_cubes(), year_range, countries, categories, flows, exclude_aggregate
    )


def _build_filtered_view_from_cubes(
    cubes: TradeCubes,
    year_range: tuple[int, int],
    countries: tuple[str, ...] | None,
    categories: tuple[str, ...] | None,
    flows: tuple[str, ...] | None,
    exclude_aggregate: bool = True,
) -> FilteredView:
    ccyy = _filter_cube_frame(
        cubes.country_category_year,
        year_range,
        countries,
        categories,
        flows,
        exclude_aggregate,
        category_col="category",
    )

    if categories:
        cyf = ccyy.groupby(["country_or_area", "year", "flow"], as_index=False)[
            "trade_usd"
        ].sum()
        total_basis = "Selected product categories only"
    else:
        cyf = _filter_cube_frame(
            cubes.country_year_flow, year_range, countries, None, flows, False
        )
        total_basis = "Authoritative country totals"

    catyf = ccyy.groupby(["category", "year", "flow"], as_index=False)[
        "trade_usd"
    ].sum()

    ct = cubes.commodity_totals
    if categories:
        ct = ct[ct["category"].isin(categories)]
    if exclude_aggregate:
        ct = ct[ct["category"] != AGGREGATE_CATEGORY]

    if "records" in ccyy:
        yr = ccyy.groupby("year", as_index=False).agg(
            records=("records", "sum"),
            countries=("country_or_area", "nunique"),
        )
        yr["commodities"] = pd.NA
    else:
        yr = pd.DataFrame(columns=["year", "records", "countries", "commodities"])

    return FilteredView(
        year_range=year_range,
        exclude_aggregate=exclude_aggregate,
        country_year_flow=cyf,
        category_year_flow=catyf,
        country_category_year=ccyy,
        commodity_totals=ct,
        year_records=yr,
        countries=countries,
        categories=categories,
        flows=flows,
        total_basis=total_basis,
        is_conditional_basket=bool(categories),
        has_country_filter=bool(countries),
        has_category_filter=bool(categories),
    )
