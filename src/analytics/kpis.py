"""Executive KPIs, comparisons, alerts, and root-cause drivers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from config import OIL_CATEGORY
from src.data.country_iso import actual_country_rows


@dataclass
class KpiSnapshot:
    label: str
    value: str
    delta: str | None
    delta_direction: str  # "up", "down", "neutral"
    context: str


def _fmt_billions(usd: float) -> str:
    if abs(usd) >= 1e12:
        return f"${usd/1e12:.2f}T"
    return f"${usd/1e9:.1f}B"


def _fmt_pct(pct: float) -> str:
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"


def compute_executive_kpis(view, focus_year: int | None = None) -> list[KpiSnapshot]:
    """KPIs with period context — answers 'is trade growing?' and 'how much?'."""
    yearly = view.yearly_summary()
    if yearly.empty:
        return []

    if focus_year is None:
        focus_year = int(yearly["year"].max())

    row = yearly[yearly["year"] == focus_year]
    if row.empty:
        focus_year = int(yearly.iloc[-1]["year"])
        row = yearly.iloc[-1:]
    row = row.iloc[0]

    prev_row = yearly[yearly["year"] == focus_year - 1]
    start_row = yearly[yearly["year"] == view.year_range[0]]
    prev = prev_row.iloc[0] if not prev_row.empty else None
    start = start_row.iloc[0] if not start_row.empty else None

    kpis: list[KpiSnapshot] = []

    # Total trade
    yoy = row["yoy_pct"] if pd.notna(row.get("yoy_pct")) else 0
    kpis.append(
        KpiSnapshot(
            label=f"Total trade ({focus_year})",
            value=_fmt_billions(row["trade_usd"]),
            delta=_fmt_pct(yoy) + " vs prior year" if prev is not None else None,
            delta_direction="up" if yoy > 0.5 else "down" if yoy < -0.5 else "neutral",
            context=f"Prior year: {_fmt_billions(prev['trade_usd'])}" if prev is not None else "",
        )
    )

    # Range growth (first → focus year)
    if start is not None and focus_year != int(start["year"]):
        range_pct = (row["trade_usd"] / start["trade_usd"] - 1) * 100
        kpis.append(
            KpiSnapshot(
                label=f"Change since {int(start['year'])}",
                value=_fmt_pct(range_pct),
                delta=_fmt_billions(row["trade_usd"] - start["trade_usd"]),
                delta_direction="up" if range_pct > 0 else "down" if range_pct < 0 else "neutral",
                context=f"From {_fmt_billions(start['trade_usd'])} → {_fmt_billions(row['trade_usd'])}",
            )
        )

    # Export / import balance (focus year)
    cy = view.country_year_flow[view.country_year_flow["year"] == focus_year]
    exp = cy[cy["flow"] == "Export"]["trade_usd"].sum()
    imp = cy[cy["flow"] == "Import"]["trade_usd"].sum()
    balance = exp - imp
    kpis.append(
        KpiSnapshot(
            label=f"Net trade balance ({focus_year})",
            value=_fmt_billions(balance),
            delta=f"Exports {_fmt_billions(exp)}",
            delta_direction="up" if balance > 0 else "down" if balance < 0 else "neutral",
            context=f"Imports {_fmt_billions(imp)}",
        )
    )

    # Oil share
    oil = view.category_year_flow[
        (view.category_year_flow["year"] == focus_year)
        & (view.category_year_flow["category"] == OIL_CATEGORY)
    ]["trade_usd"].sum()
    total = cy["trade_usd"].sum()
    oil_pct = (oil / total * 100) if total > 0 else 0
    prev_oil_pct = None
    if prev is not None:
        po = view.category_year_flow[
            (view.category_year_flow["year"] == focus_year - 1)
            & (view.category_year_flow["category"] == OIL_CATEGORY)
        ]["trade_usd"].sum()
        pt = view.country_year_flow[view.country_year_flow["year"] == focus_year - 1]["trade_usd"].sum()
        prev_oil_pct = (po / pt * 100) if pt > 0 else 0
    oil_delta = (oil_pct - prev_oil_pct) if prev_oil_pct is not None else None
    kpis.append(
        KpiSnapshot(
            label=f"Oil & fuels share ({focus_year})",
            value=f"{oil_pct:.1f}%",
            delta=f"{oil_delta:+.1f} pp vs prior year" if oil_delta is not None else None,
            delta_direction="up" if oil_delta and oil_delta > 0 else "down" if oil_delta and oil_delta < 0 else "neutral",
            context="Share of total commodity trade",
        )
    )

    return kpis


def detect_alerts(view, focus_year: int | None = None) -> list[dict]:
    """Flag exceptions — answers 'what needs attention?'."""
    yearly = view.yearly_summary()
    alerts: list[dict] = []
    if yearly.empty:
        return alerts

    if focus_year is None:
        focus_year = int(yearly["year"].max())

    row = yearly[yearly["year"] == focus_year]
    if row.empty:
        return alerts
    row = row.iloc[0]

    yoy = row.get("yoy_pct")
    if pd.notna(yoy):
        if yoy <= -15:
            alerts.append(
                {
                    "level": "critical",
                    "title": f"Sharp contraction in {focus_year}",
                    "detail": f"Trade fell {yoy:.1f}% year-over-year. Investigate categories and key countries below.",
                }
            )
        elif yoy < 0:
            alerts.append(
                {
                    "level": "warning",
                    "title": f"Trade declined in {focus_year}",
                    "detail": f"Down {abs(yoy):.1f}% vs prior year.",
                }
            )
        elif yoy >= 15:
            alerts.append(
                {
                    "level": "positive",
                    "title": f"Strong growth in {focus_year}",
                    "detail": f"Trade up {yoy:.1f}% year-over-year.",
                }
            )

    # Statistical anomaly on YoY series
    yoy_series = yearly["yoy_pct"].dropna()
    if len(yoy_series) >= 5 and focus_year in yearly["year"].values:
        z = (yoy - yoy_series.mean()) / yoy_series.std() if yoy_series.std() > 0 else 0
        if abs(z) > 1.5 and not any(a["title"].startswith("Sharp") for a in alerts):
            alerts.append(
                {
                    "level": "warning",
                    "title": f"Unusual YoY swing in {focus_year}",
                    "detail": f"Growth rate is {abs(z):.1f}σ from the historical average.",
                }
            )

    if focus_year == 2016 or view.year_range[1] >= 2016:
        alerts.append(
            {
                "level": "info",
                "title": "2016 data may be incomplete",
                "detail": "Record counts drop ~22% in 2016. Treat that year cautiously in decisions.",
            }
        )

    if view.has_country_filter or view.has_category_filter:
        alerts.append(
            {
                "level": "info",
                "title": "Filtered view active",
                "detail": "KPIs reflect current sidebar filters, not global totals.",
            }
        )

    return alerts


def root_cause_drivers(view, year_from: int, year_to: int, top_n: int = 5) -> dict:
    """Top category/country gainers and losers (signed, not conflated)."""
    cat_full = view.category_change_table(year_from, year_to)
    cat_declines = cat_full[cat_full["change_billions"] < 0].nsmallest(top_n, "change_billions")
    cat_gains = cat_full[cat_full["change_billions"] > 0].nlargest(top_n, "change_billions")

    countries_only = actual_country_rows(view.country_year_flow)
    country_from = countries_only[countries_only["year"] == year_from]
    country_to = countries_only[countries_only["year"] == year_to]
    c_from = country_from.groupby("country_or_area")["trade_usd"].sum()
    c_to = country_to.groupby("country_or_area")["trade_usd"].sum()
    countries = c_from.index.union(c_to.index)
    before = c_from.reindex(countries, fill_value=0)
    after = c_to.reindex(countries, fill_value=0)
    country_changes = pd.DataFrame(
        {
            "country": countries,
            "change_billions": (after - before).values / 1e9,
            "change_pct": (((after / before.where(before > 0)) - 1) * 100).values,
        }
    )
    country_declines = country_changes[country_changes["change_billions"] < 0].nsmallest(
        top_n, "change_billions"
    )
    country_gains = country_changes[country_changes["change_billions"] > 0].nlargest(
        top_n, "change_billions"
    )

    yearly = view.yearly_summary()
    v_from = yearly.loc[yearly["year"] == year_from, "trade_trillions"]
    v_to = yearly.loc[yearly["year"] == year_to, "trade_trillions"]
    total_change_pct = None
    if not v_from.empty and not v_to.empty and v_from.iloc[0] > 0:
        total_change_pct = (v_to.iloc[0] / v_from.iloc[0] - 1) * 100

    return {
        "year_from": year_from,
        "year_to": year_to,
        "total_change_pct": total_change_pct,
        "top_category_declines": cat_declines,
        "top_category_gains": cat_gains,
        "top_country_declines": country_declines,
        "top_country_gains": country_gains,
        "all_categories_declined": cat_gains.empty and not cat_declines.empty,
    }


def underperformers(view, year: int, top_n: int = 5) -> pd.DataFrame:
    """Countries below median YoY in a given year."""
    cy = actual_country_rows(view.country_year_flow)
    y1, y2 = year - 1, year
    b = cy[cy["year"] == y1].groupby("country_or_area")["trade_usd"].sum()
    a = cy[cy["year"] == y2].groupby("country_or_area")["trade_usd"].sum()
    common = b.index.intersection(a.index)
    pct = ((a[common] / b[common]) - 1) * 100
    med = pct.median()
    under = pct[pct < med].sort_values().head(top_n)
    return under.rename("yoy_pct").reset_index().rename(columns={"country_or_area": "country"})
