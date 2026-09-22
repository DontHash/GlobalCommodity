"""Country export targets and short-horizon regression forecasts."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


@dataclass
class TargetPlan:
    metric: str
    unit: str
    country: str
    baseline_year: int
    baseline_value: float
    target_year: int
    target_value: float
    years_to_target: int
    required_cagr_pct: float
    required_annual_increase: float
    total_increase: float
    path: pd.DataFrame


@dataclass
class ForecastResult:
    method: str
    horizon: int
    series: pd.DataFrame
    slope_per_year: float | None
    r2: float | None
    training_observations: int
    validation_observations: int
    mae: float | None
    mape: float | None
    naive_mae: float | None
    beats_naive: bool | None


def compute_target_plan(
    country: str,
    metric: str,
    baseline_year: int,
    baseline_value: float,
    target_year: int,
    target_value: float,
) -> TargetPlan | None:
    """Compound-growth path required to reach a target by a future year."""
    if baseline_value <= 0 or target_year <= baseline_year:
        return None

    years_to_target = target_year - baseline_year
    cagr = (target_value / baseline_value) ** (1 / years_to_target) - 1
    total_increase = target_value - baseline_value
    annual_increase = total_increase / years_to_target

    years = list(range(baseline_year, target_year + 1))
    values = [baseline_value * (1 + cagr) ** (y - baseline_year) for y in years]
    path = pd.DataFrame({"year": years, "value": values, "series": "required_path"})

    unit = "B" if metric == "value" else "kt"
    return TargetPlan(
        metric=metric,
        unit=unit,
        country=country,
        baseline_year=baseline_year,
        baseline_value=baseline_value,
        target_year=target_year,
        target_value=target_value,
        years_to_target=years_to_target,
        required_cagr_pct=round(cagr * 100, 2),
        required_annual_increase=round(annual_increase, 2),
        total_increase=round(total_increase, 2),
        path=path,
    )


def regression_forecast(
    trajectory: pd.DataFrame,
    value_col: str,
    baseline_year: int,
    horizon: int = 5,
    min_points: int = 5,
) -> ForecastResult | None:
    """Project future years and validate the trend against a last-value baseline."""
    hist = trajectory[trajectory["year"] <= baseline_year].sort_values("year")
    if len(hist) < min_points:
        return None

    years = hist["year"].to_numpy(dtype=float)
    values = hist[value_col].to_numpy(dtype=float)
    if np.any(values <= 0):
        return None

    x = years.reshape(-1, 1)
    log_y = np.log(values)
    model = LinearRegression()
    model.fit(x, log_y)
    r2 = float(model.score(x, log_y))

    actual, predicted, naive = [], [], []
    for end in range(min_points, len(hist)):
        rolling = LinearRegression().fit(x[:end], log_y[:end])
        actual.append(values[end])
        predicted.append(float(np.exp(rolling.predict(x[end : end + 1])[0])))
        naive.append(values[end - 1])

    future_years = list(range(baseline_year + 1, baseline_year + horizon + 1))
    x_future = np.array(future_years, dtype=float).reshape(-1, 1)
    preds = np.exp(model.predict(x_future))

    anchor = pd.DataFrame(
        {"year": [baseline_year], value_col: [float(hist.loc[hist["year"] == baseline_year, value_col].iloc[0])]}
    )
    forecast = pd.DataFrame({"year": future_years, value_col: preds})
    series = pd.concat([anchor, forecast], ignore_index=True)
    series["series"] = "forecast"
    series = series.rename(columns={value_col: "value"})

    residuals = log_y - model.predict(x)
    sigma = float(np.sqrt(np.sum(residuals**2) / (len(hist) - 2))) if len(hist) > 2 else 0.0
    series["lower_95"] = series["value"] * np.exp(-1.96 * sigma)
    series["upper_95"] = series["value"] * np.exp(1.96 * sigma)
    anchor_mask = series["year"] == baseline_year
    series.loc[anchor_mask, "lower_95"] = series.loc[anchor_mask, "value"]
    series.loc[anchor_mask, "upper_95"] = series.loc[anchor_mask, "value"]

    # Approximate % change per calendar year at baseline
    slope_pct = (np.exp(model.coef_[0]) - 1) * 100

    actual_arr, predicted_arr, naive_arr = map(np.asarray, (actual, predicted, naive))
    mae = float(np.mean(np.abs(actual_arr - predicted_arr))) if actual else None
    naive_mae = float(np.mean(np.abs(actual_arr - naive_arr))) if actual else None
    mape = float(np.mean(np.abs((actual_arr - predicted_arr) / actual_arr)) * 100) if actual else None

    return ForecastResult(
        method="log-linear regression",
        horizon=horizon,
        series=series,
        slope_per_year=round(slope_pct, 2),
        r2=round(r2, 3),
        training_observations=len(hist),
        validation_observations=len(actual),
        mae=mae,
        mape=mape,
        naive_mae=naive_mae,
        beats_naive=mae < naive_mae if mae is not None and naive_mae is not None else None,
    )
