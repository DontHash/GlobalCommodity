"""Country export growth profiles and driver decomposition."""

from __future__ import annotations

import numpy as np
import pandas as pd

ARCHETYPES = (
    "Fast & sustained",
    "Sudden shock",
    "Slow & steady",
    "Declining",
    "Volatile",
    "Stagnant",
)


def _short_label(category: str) -> str:
    import re
    return re.sub(r"^\d+_", "", category).replace("_", " ")[:45]


def classify_archetype(cagr_pct: float, yoy_std: float, max_yoy_abs: float, sign_reversals: int) -> str:
    if cagr_pct < -1.0:
        return "Declining"
    if max_yoy_abs >= 30.0:
        return "Sudden shock"
    if yoy_std >= 18.0 or sign_reversals >= 3:
        return "Volatile"
    if cagr_pct >= 5.0 and yoy_std < 12.0:
        return "Fast & sustained"
    if cagr_pct >= 0.5:
        return "Slow & steady"
    return "Stagnant"


def country_growth_profiles(
    export_series: pd.DataFrame,
    year_from: int,
    year_to: int,
) -> pd.DataFrame:
    """Score each country on export growth pattern over the selected window."""
    sub = export_series[
        export_series["year"].between(year_from, year_to)
    ].copy()
    rows = []
    for country, grp in sub.groupby("country_or_area"):
        grp = grp.sort_values("year")
        if len(grp) < 2:
            continue
        start_val = grp.iloc[0]["trade_usd"]
        end_val = grp.iloc[-1]["trade_usd"]
        if start_val <= 0:
            continue
        years_span = grp.iloc[-1]["year"] - grp.iloc[0]["year"]
        cagr = ((end_val / start_val) ** (1 / years_span) - 1) * 100 if years_span > 0 else 0.0
        yoy = grp["yoy_pct"].dropna()
        yoy_std = float(yoy.std()) if len(yoy) > 1 else 0.0
        max_yoy = float(yoy.abs().max()) if not yoy.empty else 0.0
        shock_row = yoy.abs().idxmax() if not yoy.empty else grp.index[0]
        shock_year = int(grp.loc[shock_row, "year"]) if shock_row in grp.index else None
        shock_yoy = float(yoy.loc[shock_row]) if shock_row in yoy.index else None
        signs = np.sign(yoy.replace(0, np.nan).dropna())
        reversals = int((signs.diff().abs() > 1).sum()) if len(signs) > 1 else 0
        total_change_pct = (end_val / start_val - 1) * 100
        archetype = classify_archetype(cagr, yoy_std, max_yoy, reversals)
        rows.append(
            {
                "country": country,
                "cagr_pct": round(cagr, 1),
                "total_change_pct": round(total_change_pct, 1),
                "yoy_std": round(yoy_std, 1),
                "max_yoy_abs": round(max_yoy, 1),
                "shock_year": shock_year,
                "shock_yoy_pct": round(shock_yoy, 1) if shock_yoy is not None else None,
                "archetype": archetype,
                "export_start_b": round(start_val / 1e9, 2),
                "export_end_b": round(end_val / 1e9, 2),
            }
        )
    return pd.DataFrame(rows).sort_values("cagr_pct", ascending=False)


def export_change_drivers(
    country_category_year: pd.DataFrame,
    country: str,
    year_from: int,
    year_to: int,
    top_n: int = 8,
) -> tuple[pd.DataFrame, dict]:
    """Decompose export change into category value, volume, and price effects."""
    data = country_category_year[
        (country_category_year["country_or_area"] == country)
        & (country_category_year["flow"] == "Export")
        & (country_category_year["year"].isin([year_from, year_to]))
    ]
    if data.empty:
        return pd.DataFrame(), {}

    pivot = (
        data.groupby(["category", "year"], as_index=False)
        .agg(trade_usd=("trade_usd", "sum"), weight_kg=("weight_kg", "sum"))
    )
    from_df = pivot[pivot["year"] == year_from].set_index("category")
    to_df = pivot[pivot["year"] == year_to].set_index("category")
    cats = from_df.index.union(to_df.index)

    rows = []
    for cat in cats:
        v0 = float(from_df.loc[cat, "trade_usd"]) if cat in from_df.index else 0.0
        v1 = float(to_df.loc[cat, "trade_usd"]) if cat in to_df.index else 0.0
        w0 = float(from_df.loc[cat, "weight_kg"]) if cat in from_df.index else 0.0
        w1 = float(to_df.loc[cat, "weight_kg"]) if cat in to_df.index else 0.0
        p0 = v0 / w0 if w0 > 0 else np.nan
        p1 = v1 / w1 if w1 > 0 else np.nan
        delta_v = v1 - v0
        delta_w = w1 - w0
        prices = [p for p in (p0, p1) if p is not None and not np.isnan(p)]
        avg_p = float(np.mean(prices)) if prices else np.nan
        volume_effect = delta_w * avg_p if not np.isnan(avg_p) else 0.0
        price_effect = (p1 - p0) * w0 if not np.isnan(p0) and not np.isnan(p1) else 0.0
        if abs(delta_v) < 1:
            continue
        if v0 <= 0 and v1 > 0:
            driver = "new export"
        elif abs(volume_effect) >= abs(price_effect):
            driver = "volume"
        else:
            driver = "price"
        rows.append(
            {
                "category": cat,
                "short_label": _short_label(cat),
                "value_change_b": delta_v / 1e9,
                "weight_change_k_t": delta_w / 1e6,
                "price_from_per_kg": round(p0, 2) if not np.isnan(p0) else None,
                "price_to_per_kg": round(p1, 2) if not np.isnan(p1) else None,
                "volume_effect_b": volume_effect / 1e9,
                "price_effect_b": price_effect / 1e9,
                "primary_driver": driver,
            }
        )

    drivers = pd.DataFrame(rows)
    if drivers.empty:
        return drivers, {}

    drivers = drivers.reindex(drivers["value_change_b"].abs().sort_values(ascending=False).index)
    total_from = float(from_df["trade_usd"].sum()) if not from_df.empty else 0.0
    total_to = float(to_df["trade_usd"].sum()) if not to_df.empty else 0.0
    total_change = total_to - total_from
    total_change_pct = (total_to / total_from - 1) * 100 if total_from > 0 else None

    top = drivers.iloc[0]
    summary = {
        "country": country,
        "year_from": year_from,
        "year_to": year_to,
        "total_change_b": total_change / 1e9,
        "total_change_pct": round(total_change_pct, 1) if total_change_pct is not None else None,
        "top_category": top["short_label"],
        "top_change_b": top["value_change_b"],
        "top_driver": top["primary_driver"],
        "narrative": _build_narrative(country, year_from, year_to, total_change_pct, drivers.head(3)),
    }
    return drivers.head(top_n), summary


def _build_narrative(
    country: str,
    year_from: int,
    year_to: int,
    total_change_pct: float | None,
    top_drivers: pd.DataFrame,
) -> str:
    if top_drivers.empty:
        return f"No export category shifts detected for {country} between {year_from} and {year_to}."
    pct_txt = f"{total_change_pct:+.1f}%" if total_change_pct is not None else "a notable shift"
    parts = [f"{country} exports changed {pct_txt} ({year_from}→{year_to})."]
    for _, row in top_drivers.iterrows():
        direction = "rose" if row["value_change_b"] > 0 else "fell"
        driver_hint = {
            "volume": "mainly from higher shipped volumes",
            "price": "mainly from unit-price changes",
            "new export": "as a newly exported category",
        }.get(row["primary_driver"], "")
        parts.append(
            f"{row['short_label']} {direction} by ${abs(row['value_change_b']):.2f}B"
            + (f" ({driver_hint})" if driver_hint else "")
            + "."
        )
    return " ".join(parts)
