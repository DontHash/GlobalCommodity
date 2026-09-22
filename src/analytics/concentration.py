"""Product concentration and diversification metrics for trade baskets."""

from __future__ import annotations

import pandas as pd

from config import AGGREGATE_CATEGORY


KEYS = ["country_or_area", "year", "flow"]
REQUIRED_COLUMNS = {*KEYS, "category", "trade_usd"}
METRIC_COLUMNS = [
    *KEYS,
    "hhi",
    "effective_categories",
    "normalized_hhi",
    "diversification_score",
    "observed_categories",
    "top_category_share",
    "top_three_share",
    "measured_total_usd",
    "canonical_total_usd",
    "coverage_pct",
    "conditional",
]


def _category_shares(data: pd.DataFrame, flow: str | None) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"Missing concentration columns: {sorted(missing)}")

    detail = data[
        data["category"].ne(AGGREGATE_CATEGORY) & data["trade_usd"].gt(0)
    ]
    if flow:
        detail = detail[detail["flow"].eq(flow)]
    if detail.empty:
        return pd.DataFrame(columns=[*KEYS, "category", "trade_usd", "share", "share_sq", "rank"])

    shares = detail.groupby([*KEYS, "category"], as_index=False)["trade_usd"].sum()
    shares["measured_total_usd"] = shares.groupby(KEYS)["trade_usd"].transform("sum")
    shares["share"] = shares["trade_usd"] / shares["measured_total_usd"]
    shares["share_sq"] = shares["share"] ** 2
    shares = shares.sort_values(
        [*KEYS, "share"], ascending=[True, True, True, False]
    )
    shares["rank"] = shares.groupby(KEYS).cumcount() + 1
    return shares


def concentration_by_year(
    data: pd.DataFrame,
    flow: str | None = "Export",
    canonical_totals: pd.DataFrame | None = None,
    *,
    conditional: bool = False,
) -> pd.DataFrame:
    """Calculate one product-diversification observation per country/year/flow."""
    shares = _category_shares(data, flow)
    if shares.empty:
        return pd.DataFrame(columns=METRIC_COLUMNS)

    result = shares.groupby(KEYS, as_index=False).agg(
        hhi=("share_sq", "sum"),
        observed_categories=("category", "nunique"),
        top_category_share=("share", "max"),
        measured_total_usd=("trade_usd", "sum"),
    )
    top_three = (
        shares[shares["rank"] <= 3]
        .groupby(KEYS, as_index=False)["share"]
        .sum()
        .rename(columns={"share": "top_three_share"})
    )
    result = result.merge(top_three, on=KEYS, how="left")
    result["effective_categories"] = 1 / result["hhi"]
    n = result["observed_categories"]
    result["normalized_hhi"] = ((result["hhi"] - 1 / n) / (1 - 1 / n)).where(
        n > 1, 1.0
    ).clip(0, 1)
    result["diversification_score"] = 1 - result["normalized_hhi"]
    result["conditional"] = conditional

    if canonical_totals is not None and not canonical_totals.empty:
        missing = set(KEYS + ["trade_usd"]) - set(canonical_totals.columns)
        if missing:
            raise ValueError(f"Missing canonical total columns: {sorted(missing)}")
        canonical = (
            canonical_totals.groupby(KEYS, as_index=False)["trade_usd"]
            .sum()
            .rename(columns={"trade_usd": "canonical_total_usd"})
        )
        result = result.merge(canonical, on=KEYS, how="left")
        result["coverage_pct"] = (
            result["measured_total_usd"] / result["canonical_total_usd"] * 100
        ).where(result["canonical_total_usd"].gt(0))
    else:
        result["canonical_total_usd"] = float("nan")
        result["coverage_pct"] = float("nan")

    return result[METRIC_COLUMNS].sort_values(KEYS).reset_index(drop=True)


def category_contributions(
    data: pd.DataFrame, country: str, year: int, flow: str = "Export"
) -> pd.DataFrame:
    """Explain one HHI using category shares and squared-share contributions."""
    shares = _category_shares(data, flow)
    shares = shares[
        shares["country_or_area"].eq(country) & shares["year"].eq(year)
    ].copy()
    if shares.empty:
        return pd.DataFrame(
            columns=[
                "category",
                "trade_usd",
                "share",
                "share_sq",
                "hhi_contribution",
                "rank",
            ]
        )

    hhi = shares["share_sq"].sum()
    shares["hhi_contribution"] = shares["share_sq"] / hhi
    shares["share_pct"] = shares["share"] * 100
    shares["hhi_contribution_pct"] = shares["hhi_contribution"] * 100
    shares["trade_billions"] = shares["trade_usd"] / 1e9
    return shares.sort_values("hhi_contribution", ascending=False).reset_index(drop=True)
