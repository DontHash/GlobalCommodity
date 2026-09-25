"""FastAPI adapter around the existing trade-data and analytics modules."""

from __future__ import annotations

import io
import json
import os
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from config import AGGREGATE_CATEGORY, DEFAULT_YEAR_RANGE, FLOWS, OIL_CATEGORY
from src.analytics.concentration import category_contributions, concentration_by_year
from src.analytics.forecast import compute_target_plan, regression_forecast
from src.analytics.growth import ARCHETYPES, country_growth_profiles, export_change_drivers
from src.analytics.kpis import compute_executive_kpis, detect_alerts, root_cause_drivers, underperformers
from src.analytics.mining import (
    arima_forecast,
    change_points,
    country_shock_clusters_from_cyf,
    detect_yoy_anomalies,
    isolation_forest_years,
    oil_regression_from_cyf,
    pick_arima_train_end,
    rf_yoy_surprise,
)
from src.analytics.story import shock_events
from src.data.context import FilteredView, build_filtered_view
from src.data.country_iso import actual_country_rows, attach_iso3, is_actual_country
from src.data.cubes import load_trade_cubes
from src.data.loader import load_filtered_sample
from src.processing.aggregate import correlation_matrix, country_rankings
from src.utils.labels import category_label


ROOT = Path(__file__).resolve().parents[1]
PERIOD_PRESETS = {
    "Custom": None,
    "Full history (1988-2016)": (1988, 2016),
    "Pre-crisis boom (2000-2008)": (2000, 2008),
    "Financial crisis (2007-2010)": (2007, 2010),
    "Peak era (2011-2014)": (2011, 2014),
    "Commodity slowdown (2014-2016)": (2014, 2016),
    "Default (1995-2015)": DEFAULT_YEAR_RANGE,
}
DEFAULT_COUNTRIES = ("USA", "China", "Germany")

app = FastAPI(title="Global Commodity Trade Analytics API", version="1.0.0")
origins = [item.strip() for item in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@dataclass
class RequestContext:
    view: FilteredView
    year_from: int
    year_to: int
    countries: tuple[str, ...] | None
    categories: tuple[str, ...] | None
    flows: tuple[str, ...] | None
    exclude_aggregate: bool
    preset: str


def request_context(
    year_from: int = DEFAULT_YEAR_RANGE[0],
    year_to: int = DEFAULT_YEAR_RANGE[1],
    countries: list[str] | None = Query(default=None),
    categories: list[str] | None = Query(default=None),
    flows: list[str] | None = Query(default=None),
    preset: str = "Default (1995-2015)",
    exclude_aggregate: bool = True,
) -> RequestContext:
    meta = load_trade_cubes().meta
    if year_from > year_to or year_from < meta.year_min or year_to > meta.year_max:
        raise HTTPException(422, f"Year range must be within {meta.year_min}-{meta.year_max}.")
    unknown_flows = set(flows or ()) - set(FLOWS)
    if unknown_flows:
        raise HTTPException(422, f"Unsupported flows: {sorted(unknown_flows)}")
    country_tuple = tuple(countries) if countries else None
    category_tuple = tuple(categories) if categories else None
    flow_tuple = tuple(flows) if flows else None
    return RequestContext(
        view=build_filtered_view(
            (year_from, year_to), country_tuple, category_tuple, flow_tuple, exclude_aggregate
        ),
        year_from=year_from,
        year_to=year_to,
        countries=country_tuple,
        categories=category_tuple,
        flows=flow_tuple,
        exclude_aggregate=exclude_aggregate,
        preset=preset,
    )


def records(df: pd.DataFrame | None) -> list[dict]:
    if df is None or df.empty:
        return []
    display = df.copy()
    if "category" in display:
        display["category"] = display["category"].map(category_label)
    return json.loads(display.to_json(orient="records", date_format="iso"))


def default_countries(options: list[str], limit: int = 3) -> list[str]:
    preferred = [country for country in DEFAULT_COUNTRIES if country in options]
    return (preferred + [country for country in options if country not in preferred])[:limit]


def country_year_metrics(df: pd.DataFrame, flow: str | None = None) -> pd.DataFrame:
    """Actual-country yearly values with rank, selected-scope share, and YoY change."""
    data = actual_country_rows(df)
    if flow:
        data = data[data["flow"] == flow]
    out = (
        data.groupby(["year", "country_or_area"], as_index=False)["trade_usd"]
        .sum()
        .sort_values(["country_or_area", "year"])
    )
    if out.empty:
        return out
    out["yoy_pct"] = out.groupby("country_or_area")["trade_usd"].pct_change() * 100
    out["share_pct"] = out["trade_usd"] / out.groupby("year")["trade_usd"].transform("sum") * 100
    out["rank"] = out.groupby("year")["trade_usd"].rank(method="first", ascending=False).astype(int)
    out["trade_billions"] = out["trade_usd"] / 1e9
    return out.sort_values(["year", "rank"])


def country_period_ranking(
    df: pd.DataFrame, flow: str | None = None, top_n: int | None = None
) -> pd.DataFrame:
    """Actual-country period ranking enriched before applying the requested limit."""
    data = actual_country_rows(df)
    ranking = country_rankings(data, flow, top_n=None)
    if ranking.empty:
        return ranking
    ranking["rank"] = range(1, len(ranking) + 1)
    total = ranking["trade_usd"].sum()
    ranking["share_pct"] = ranking["trade_usd"] / total * 100 if total else 0.0
    yearly = country_year_metrics(data, flow)
    if not yearly.empty:
        latest = yearly.sort_values("year").groupby("country_or_area", as_index=False).tail(1)[
            ["country_or_area", "yoy_pct"]
        ]
        ranking = ranking.merge(latest, on="country_or_area", how="left")
    return ranking.head(top_n) if top_n is not None else ranking


def diagnostics(df: pd.DataFrame | None) -> dict:
    return dict(df.attrs.get("diagnostics", {})) if df is not None else {}


def driver_payload(result: dict | None) -> dict | None:
    if result is None:
        return None
    return {
        **{key: value for key, value in result.items() if not isinstance(value, pd.DataFrame)},
        "top_category_declines": records(result["top_category_declines"]),
        "top_category_gains": records(result["top_category_gains"]),
        "top_country_declines": records(result["top_country_declines"]),
        "top_country_gains": records(result["top_country_gains"]),
    }


def scope_payload(ctx: RequestContext) -> dict:
    profile = ctx.view.profile
    actual_countries = actual_country_rows(ctx.view.country_year_flow)["country_or_area"].nunique()
    return {
        "profile": profile,
        "period": [ctx.year_from, ctx.year_to],
        "preset": ctx.preset,
        "countries": list(ctx.countries or ()),
        "categories": list(ctx.categories or ()),
        "flows": list(ctx.flows or FLOWS),
        "total_basis": ctx.view.total_basis,
        "conditional_basket": ctx.view.is_conditional_basket,
        "aggregate_excluded": ctx.exclude_aggregate,
        "actual_countries": int(actual_countries),
        "non_country_areas": max(0, int(profile["countries"] - actual_countries)),
        "source": "UN Comtrade",
        "indexed": "2026-06-17",
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/filters")
def filter_options() -> dict:
    meta = load_trade_cubes().meta
    categories = [item for item in meta.categories if item != AGGREGATE_CATEGORY]
    return {
        "year_min": meta.year_min,
        "year_max": meta.year_max,
        "countries": [item for item in meta.countries if is_actual_country(item)],
        "categories": categories,
        "category_labels": {item: category_label(item) for item in categories},
        "flows": FLOWS,
        "presets": [{"label": label, "range": value} for label, value in PERIOD_PRESETS.items()],
        "default_range": list(DEFAULT_YEAR_RANGE),
    }


@app.get("/api/overview")
def overview(
    focus_year: int | None = None,
    compare_from: int | None = None,
    compare_to: int | None = None,
    ctx: RequestContext = Depends(request_context),
) -> dict:
    yearly = ctx.view.yearly_summary()
    years = yearly["year"].astype(int).tolist()
    if not years:
        return {"scope": scope_payload(ctx), "years": [], "yearly": []}
    focus = focus_year if focus_year in years else years[-1]
    y_from = compare_from if compare_from in years else years[0]
    y_to = compare_to if compare_to in years else years[-1]
    top_countries = country_period_ranking(ctx.view.country_year_flow, top_n=10)
    top_categories = ctx.view.category_totals(10).copy()
    drivers = root_cause_drivers(ctx.view, y_from, y_to) if y_from < y_to else None
    return {
        "scope": scope_payload(ctx),
        "years": years,
        "focus_year": focus,
        "compare_from": y_from,
        "compare_to": y_to,
        "yearly": records(yearly),
        "kpis": [asdict(item) for item in compute_executive_kpis(ctx.view, focus)],
        "alerts": detect_alerts(ctx.view, focus),
        "top_countries": records(top_countries),
        "top_categories": records(top_categories),
        "drivers": driver_payload(drivers),
    }


@app.get("/api/trends")
def trends(ctx: RequestContext = Depends(request_context)) -> dict:
    return {
        "scope": scope_payload(ctx),
        "yearly": records(ctx.view.yearly_summary()),
        "flows": records(ctx.view.flow_by_year()),
    }


@app.get("/api/regions")
def regions(
    map_year: int | None = None,
    map_metric: str = "total_trade",
    rank_flow: str = "All",
    top_n: int = Query(15, ge=5, le=30),
    compare_countries: list[str] | None = Query(default=None),
    ctx: RequestContext = Depends(request_context),
) -> dict:
    years = sorted(int(year) for year in ctx.view.country_year_flow["year"].unique())
    selected_year = map_year if map_year in years else (years[-1] if years else ctx.year_to)
    if map_metric not in {"total_trade", "trade_balance", "exports", "imports"}:
        raise HTTPException(422, "Unsupported map metric.")
    metrics = ctx.view.map_metrics(selected_year, map_metric)
    if map_metric != "trade_balance":
        metric_flow = {"exports": "Export", "imports": "Import"}.get(map_metric)
        metric_meta = country_year_metrics(ctx.view.country_year_flow, metric_flow)
        metric_meta = metric_meta[metric_meta["year"] == selected_year][
            ["country_or_area", "rank", "share_pct", "yoy_pct"]
        ]
        metrics = metrics.merge(metric_meta, on="country_or_area", how="left")
    geo = attach_iso3(metrics)
    flow = None if rank_flow == "All" else rank_flow
    ranking = country_period_ranking(ctx.view.country_year_flow, flow, top_n)
    balance = actual_country_rows(ctx.view.trade_balance().reset_index())
    surplus = balance[balance["balance_billions"] >= 0].head(15)
    deficit = balance[balance["balance_billions"] < 0].tail(15)
    yearly_countries = country_year_metrics(ctx.view.country_year_flow)
    options = sorted(yearly_countries["country_or_area"].unique())
    selected = compare_countries or default_countries(options)
    comparison = (
        yearly_countries[yearly_countries["country_or_area"].isin(selected)].copy()
        if selected
        else pd.DataFrame()
    )
    return {
        "scope": scope_payload(ctx),
        "years": years,
        "map_year": selected_year,
        "map_metric": map_metric,
        "map": records(geo),
        "unmapped": int(len(metrics) - len(geo)),
        "ranking": records(ranking),
        "surplus": records(surplus),
        "deficit": records(deficit),
        "country_options": options,
        "compare_countries": selected,
        "comparison": records(comparison),
    }


@app.get("/api/growth")
def growth(
    growth_from: int | None = None,
    growth_to: int | None = None,
    archetypes: list[str] | None = Query(default=None),
    compare_countries: list[str] | None = Query(default=None),
    focus_country: str | None = None,
    diversification_flow: str = "Export",
    diversification_country: str | None = None,
    diversification_year: int | None = None,
    driver_country: str | None = None,
    driver_from: int | None = None,
    driver_to: int | None = None,
    target_country: str | None = None,
    target_metric: str = "value",
    baseline_year: int | None = None,
    target_year: int | None = None,
    target_value: float | None = None,
    forecast_horizon: int = Query(5, ge=3, le=10),
    ctx: RequestContext = Depends(request_context),
) -> dict:
    years = list(range(ctx.year_from, ctx.year_to + 1))
    actual_cyf = actual_country_rows(ctx.view.country_year_flow)
    export_series = country_year_metrics(actual_cyf, "Export")
    country_options = sorted(export_series["country_or_area"].unique()) if not export_series.empty else []
    y_from = growth_from if growth_from in years else years[0]
    y_to = growth_to if growth_to in years else years[-1]
    profiles = country_growth_profiles(export_series, y_from, y_to) if y_from < y_to and not export_series.empty else pd.DataFrame()
    if archetypes and not profiles.empty:
        profiles = profiles[profiles["archetype"].isin(archetypes)]
    counts = (
        profiles["archetype"].value_counts().rename_axis("archetype").reset_index(name="count")
        if not profiles.empty
        else pd.DataFrame()
    )
    selected_countries = compare_countries or default_countries(country_options)
    comparison = export_series[export_series["country_or_area"].isin(selected_countries)]
    focused = focus_country if focus_country in selected_countries else (selected_countries[0] if selected_countries else None)
    focus_profile = (
        country_growth_profiles(export_series[export_series["country_or_area"] == focused], ctx.year_from, ctx.year_to)
        if focused and not export_series.empty
        else pd.DataFrame()
    )

    detail = actual_country_rows(ctx.view.country_category_year)
    div_flows = sorted(detail["flow"].unique(), key=lambda value: (value != "Export", value)) if not detail.empty else []
    div_flow = diversification_flow if diversification_flow in div_flows else (div_flows[0] if div_flows else None)
    div_metrics = (
        concentration_by_year(
            detail,
            div_flow,
            None if ctx.view.is_conditional_basket else actual_cyf,
            conditional=ctx.view.is_conditional_basket,
        )
        if div_flow
        else pd.DataFrame()
    )
    div_countries = sorted(div_metrics["country_or_area"].unique()) if not div_metrics.empty else []
    div_country = diversification_country if diversification_country in div_countries else (default_countries(div_countries, 1) or [None])[0]
    country_metrics = div_metrics[div_metrics["country_or_area"] == div_country] if div_country else pd.DataFrame()
    div_years = country_metrics["year"].astype(int).tolist() if not country_metrics.empty else []
    div_year = diversification_year if diversification_year in div_years else (div_years[-1] if div_years else None)
    contributions = category_contributions(detail, div_country, div_year, div_flow) if div_country and div_year else pd.DataFrame()
    if not contributions.empty:
        contributions["short_label"] = contributions["category"].map(category_label)
    div_ranking = div_metrics[div_metrics["year"] == div_year].copy() if div_year else pd.DataFrame()

    selected_driver_country = driver_country if driver_country in country_options else (default_countries(country_options, 1) or [None])[0]
    d_from = driver_from if driver_from in years else years[max(0, len(years) - 5)]
    d_to = driver_to if driver_to in years else years[-1]
    driver_rows, driver_summary = (
        export_change_drivers(ctx.view.country_category_year, selected_driver_country, d_from, d_to, 10)
        if selected_driver_country and d_from < d_to
        else (pd.DataFrame(), {})
    )

    selected_target_country = target_country if target_country in country_options else (default_countries(country_options, 1) or [None])[0]
    trajectory = ctx.view.country_export_trajectory(selected_target_country) if selected_target_country else pd.DataFrame()
    metric = target_metric if target_metric in {"value", "volume"} else "value"
    value_col = "trade_billions" if metric == "value" else "weight_kt"
    available_years = trajectory["year"].astype(int).tolist() if not trajectory.empty else []
    baseline = baseline_year if baseline_year in available_years else (available_years[-1] if available_years else None)
    plan_payload = None
    forecast_payload = None
    baseline_value = None
    if baseline is not None:
        baseline_value = float(trajectory.loc[trajectory["year"] == baseline, value_col].iloc[0])
        goal_year = target_year if target_year and target_year > baseline else baseline + 5
        goal_value = target_value if target_value and target_value > 0 else baseline_value * 1.5
        plan = compute_target_plan(selected_target_country, metric, baseline, baseline_value, goal_year, goal_value)
        forecast = regression_forecast(trajectory, value_col, baseline, forecast_horizon)
        if plan:
            plan_payload = {
                **{key: value for key, value in asdict(plan).items() if key != "path"},
                "path": records(plan.path),
            }
        if forecast:
            forecast_payload = {
                **{key: value for key, value in asdict(forecast).items() if key != "series"},
                "series": records(forecast.series),
            }
    return {
        "scope": scope_payload(ctx),
        "years": years,
        "archetypes": list(ARCHETYPES),
        "profiles": records(profiles),
        "archetype_counts": records(counts),
        "country_options": country_options,
        "compare_countries": selected_countries,
        "comparison": records(comparison),
        "focus_country": focused,
        "focus_profile": records(focus_profile),
        "diversification": {
            "flows": div_flows,
            "flow": div_flow,
            "countries": div_countries,
            "country": div_country,
            "years": div_years,
            "year": div_year,
            "series": records(country_metrics),
            "current": records(country_metrics[country_metrics["year"] == div_year])[0] if div_year and not country_metrics.empty else None,
            "contributions": records(contributions.head(20)),
            "ranking": records(div_ranking),
            "conditional": ctx.view.is_conditional_basket,
        },
        "drivers": {
            "country": selected_driver_country,
            "year_from": d_from,
            "year_to": d_to,
            "rows": records(driver_rows),
            "summary": driver_summary,
        },
        "target": {
            "country": selected_target_country,
            "metric": metric,
            "available_years": available_years,
            "baseline_year": baseline,
            "baseline_value": baseline_value,
            "trajectory": records(trajectory.rename(columns={value_col: "value"})[["year", "value"]]) if not trajectory.empty else [],
            "plan": plan_payload,
            "forecast": forecast_payload,
        },
    }


@app.get("/api/products")
def products(
    top_n: int = Query(15, ge=5, le=30),
    trend_categories: list[str] | None = Query(default=None),
    search: str = "",
    ctx: RequestContext = Depends(request_context),
) -> dict:
    category_options = sorted(ctx.view.category_year_flow["category"].unique())
    selected = trend_categories or category_options[:5]
    trend = ctx.view.category_by_year(selected)
    if not trend.empty:
        trend["label"] = trend["category"].map(category_label)
    return {
        "scope": scope_payload(ctx),
        "categories": records(ctx.view.category_totals(top_n)),
        "category_options": category_options,
        "category_labels": {item: category_label(item) for item in category_options},
        "trend_categories": selected,
        "trends": records(trend),
        "search": records(ctx.view.commodity_search(search)) if search.strip() else [],
    }


@app.get("/api/why")
def why_changed(
    compare_from: int | None = None,
    compare_to: int | None = None,
    compare_years: list[int] | None = Query(default=None),
    focus_year: int | None = None,
    ctx: RequestContext = Depends(request_context),
) -> dict:
    yearly = ctx.view.yearly_summary()
    years = yearly["year"].astype(int).tolist()
    if not years:
        return {"scope": scope_payload(ctx), "years": []}
    y_from = compare_from if compare_from in years else years[max(0, len(years) - 3)]
    y_to = compare_to if compare_to in years else years[-1]
    selected_years = compare_years or years[-3:]
    focus = focus_year if focus_year in years else years[-1]
    return {
        "scope": scope_payload(ctx),
        "years": years,
        "compare_from": y_from,
        "compare_to": y_to,
        "drivers": driver_payload(root_cause_drivers(ctx.view, y_from, y_to, 8)) if y_from < y_to else None,
        "compare_years": selected_years,
        "comparison": records(yearly[yearly["year"].isin(selected_years)]),
        "focus_year": focus,
        "underperformers": records(underperformers(ctx.view, focus)),
    }


@app.get("/api/trades")
def trades(
    preview_rows: int = Query(1000, ge=100, le=5000),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    columns: list[str] | None = Query(default=None),
    columns_empty: bool = False,
    ctx: RequestContext = Depends(request_context),
) -> dict:
    sample = load_filtered_sample(
        (ctx.year_from, ctx.year_to), ctx.countries, ctx.categories, ctx.flows, ctx.exclude_aggregate, preview_rows
    )
    selected_columns = [] if columns_empty else (columns or ["country_or_area", "year", "commodity", "flow", "trade_usd", "category"])
    invalid = set(selected_columns) - set(sample.columns)
    if invalid:
        raise HTTPException(422, f"Unknown columns: {sorted(invalid)}")
    start = (page - 1) * page_size
    return {
        "scope": scope_payload(ctx),
        "preview_rows": preview_rows,
        "available_columns": list(sample.columns),
        "columns": selected_columns,
        "page": page,
        "page_size": page_size,
        "total_preview_rows": len(sample),
        "rows": records(sample.iloc[start : start + page_size][selected_columns]),
    }


@app.get("/api/trades/export")
def trade_export(
    preview_rows: int = Query(1000, ge=100, le=5000),
    columns: list[str] | None = Query(default=None),
    columns_empty: bool = False,
    ctx: RequestContext = Depends(request_context),
) -> Response:
    sample = load_filtered_sample(
        (ctx.year_from, ctx.year_to), ctx.countries, ctx.categories, ctx.flows, ctx.exclude_aggregate, preview_rows
    )
    selected_columns = [] if columns_empty else (columns or ["country_or_area", "year", "commodity", "flow", "trade_usd", "category"])
    if not selected_columns:
        raise HTTPException(422, "Select at least one column to export.")
    invalid = set(selected_columns) - set(sample.columns)
    if invalid:
        raise HTTPException(422, f"Unknown columns: {sorted(invalid)}")
    buffer = io.StringIO()
    sample[selected_columns].to_csv(buffer, index=False)
    filename = f"trade_preview_{ctx.year_from}-{ctx.year_to}_{date.today():%Y%m%d}.csv"
    return Response(
        buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/models/{model_name}")
def models(
    model_name: str,
    z_threshold: float = Query(1.5, ge=1, le=3),
    train_end: int = 2007,
    penalty: float = Query(10, ge=1, le=30),
    shock_a_from: int = 2008,
    shock_a_to: int = 2009,
    shock_b_from: int = 2014,
    shock_b_to: int = 2015,
    ctx: RequestContext = Depends(request_context),
) -> dict:
    yearly = ctx.view.yearly_summary()
    base = {"scope": scope_payload(ctx), "model": model_name}
    if model_name == "anomalies":
        z = detect_yoy_anomalies(yearly, z_threshold)
        iso = isolation_forest_years(yearly, 0.12)
        return {**base, "z_score": records(z[z["is_anomaly"]]), "z_diagnostics": diagnostics(z), "isolation_forest": records(iso[iso["is_anomaly"]]), "isolation_diagnostics": diagnostics(iso)}
    if model_name == "forecast":
        cutoff = pick_arima_train_end(yearly, train_end) or train_end
        result = arima_forecast(yearly, cutoff)
        breaks = change_points(yearly["trade_trillions"].to_numpy(), yearly["year"].to_numpy(), penalty)
        return {**base, "train_end": cutoff, "rows": records(result), "diagnostics": diagnostics(result), "break_years": breaks}
    if model_name == "random-forest":
        result = rf_yoy_surprise(yearly, train_end)
        return {**base, "rows": records(result), "diagnostics": diagnostics(result)}
    if model_name == "clusters":
        shocks, summary, k, score = country_shock_clusters_from_cyf(actual_country_rows(ctx.view.country_year_flow), (shock_a_from, shock_a_to), (shock_b_from, shock_b_to))
        return {**base, "rows": records(shocks.reset_index()), "summary": records(summary.reset_index()), "k": k, "silhouette": score if np.isfinite(score) else None}
    if model_name == "correlation":
        sample = load_filtered_sample((ctx.year_from, ctx.year_to), ctx.countries, ctx.categories, ctx.flows, ctx.exclude_aggregate, 50_000)
        corr = correlation_matrix(sample)
        return {**base, "columns": list(corr.columns), "matrix": corr.to_numpy().round(4).tolist()}
    if model_name == "oil":
        result, model, r2 = oil_regression_from_cyf(ctx.view.category_year_flow)
        return {**base, "rows": records(result), "diagnostics": diagnostics(result), "r2": float(r2) if np.isfinite(r2) else None, "slope": float(model.coef_[0]) if model is not None else None}
    raise HTTPException(404, "Unknown model.")


@app.get("/api/story")
def story(ctx: RequestContext = Depends(request_context)) -> dict:
    yearly = ctx.view.yearly_summary()
    if yearly.empty:
        return {"scope": scope_payload(ctx), "yearly": []}
    events = shock_events(yearly)
    cutoff = pick_arima_train_end(yearly, 2007)
    counter = arima_forecast(yearly, cutoff) if cutoff else pd.DataFrame()
    peak = yearly.loc[yearly["trade_trillions"].idxmax()]
    gap_2015 = counter.loc[counter["year"] == 2015, "gap_trillions"] if not counter.empty else pd.Series(dtype=float)
    cumulative = counter.loc[counter["gap_trillions"] < 0, "gap_trillions"].sum() if not counter.empty else None
    oil = ctx.view.oil_yearly(OIL_CATEGORY)
    oil_timeline = yearly[["year", "trade_trillions"]].merge(oil, on="year") if not oil.empty else pd.DataFrame()
    return {
        "scope": scope_payload(ctx),
        "yearly": records(yearly),
        "events": records(events),
        "train_end": cutoff,
        "counterfactual": records(counter),
        "diagnostics": diagnostics(counter),
        "kpis": [
            {"label": "Peak year", "value": str(int(peak["year"]))},
            {"label": "Peak volume", "value": f"${peak['trade_trillions']:.1f}T"},
            {"label": "2015 vs trend", "value": f"${gap_2015.iloc[0]:.1f}T" if len(gap_2015) else "-"},
            {"label": "Cumulative below trend", "value": f"${abs(cumulative):.0f}T" if cumulative is not None else "-"},
        ],
        "crisis_categories": records(ctx.view.category_shock_delta(2008, 2009)),
        "slowdown_categories": records(ctx.view.category_shock_delta(2014, 2015)),
        "oil_timeline": records(oil_timeline),
    }


frontend_dist = ROOT / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
