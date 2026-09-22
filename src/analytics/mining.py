"""Machine learning and data mining routines."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import ruptures as rpt
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA

from config import AGGREGATE_CATEGORY, OIL_CATEGORY


def detect_yoy_anomalies(yearly: pd.DataFrame, z_threshold: float = 1.5) -> pd.DataFrame:
    out = yearly.dropna(subset=["yoy_pct"]).copy()
    std = out["yoy_pct"].std()
    if len(out) < 3 or not np.isfinite(std) or std == 0:
        out["yoy_z"] = 0.0
        out["is_anomaly"] = False
        out.attrs["diagnostics"] = {"warning": "At least 3 varying YoY observations are required."}
        return out
    out["yoy_z"] = (out["yoy_pct"] - out["yoy_pct"].mean()) / std
    out["is_anomaly"] = out["yoy_z"].abs() > z_threshold
    return out


def isolation_forest_years(yearly: pd.DataFrame, contamination: float = 0.12) -> pd.DataFrame:
    cols = ["trade_trillions", "yoy_pct", "records"]
    data = yearly.dropna(subset=[c for c in cols if c in yearly.columns]).copy()
    use_cols = [c for c in cols if c in data.columns and data[c].nunique() > 1]
    if len(data) < 8 or not use_cols:
        data["is_anomaly"] = False
        data.attrs["diagnostics"] = {"warning": "At least 8 observations and one varying feature are required."}
        return data
    X = StandardScaler().fit_transform(data[use_cols])
    data["is_anomaly"] = IsolationForest(contamination=contamination, random_state=42).fit_predict(X) == -1
    return data


def change_points(series: np.ndarray, years: np.ndarray, pen: float = 10.0) -> list[int]:
    if len(series) < 6 or len(series) != len(years) or not np.isfinite(series).all():
        return []
    algo = rpt.Pelt(model="l2", min_size=3, jump=1).fit(series.reshape(-1, 1))
    return [int(years[i]) for i in algo.predict(pen=pen)[:-1]]


def arima_forecast(yearly: pd.DataFrame, train_end_year: int) -> pd.DataFrame:
    """ARIMA counterfactual with rolling validation and a naive baseline."""
    empty = pd.DataFrame(
        columns=["year", "trade_trillions", "forecast_trillions", "lower_95", "upper_95", "gap_trillions", "trade_usd"]
    )
    if yearly.empty:
        return empty

    series = yearly.sort_values("year")
    train = series.loc[series["year"] <= train_end_year, "trade_trillions"].values
    future = series.loc[series["year"] > train_end_year]
    if len(train) < 10 or future.empty:
        empty.attrs["diagnostics"] = {"warning": "ARIMA requires at least 10 training years and one later year."}
        return empty

    actual, predicted, naive, fit_warnings = [], [], [], []
    for end in range(8, len(train)):
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                prediction = ARIMA(train[:end], order=(1, 1, 1)).fit().forecast(1)[0]
            fit_warnings.extend(str(item.message) for item in caught)
            actual.append(train[end])
            predicted.append(prediction)
            naive.append(train[end - 1])
        except (ValueError, np.linalg.LinAlgError) as exc:
            fit_warnings.append(str(exc))
    if not actual:
        empty.attrs["diagnostics"] = {"warning": "ARIMA could not produce validation predictions."}
        return empty
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fitted = ARIMA(train, order=(1, 1, 1)).fit()
            forecast = fitted.get_forecast(len(future)).summary_frame(alpha=0.05)
        fit_warnings.extend(str(item.message) for item in caught)
    except (ValueError, np.linalg.LinAlgError) as exc:
        empty.attrs["diagnostics"] = {"warning": f"ARIMA fit failed: {exc}"}
        return empty
    out = future.copy()
    out["forecast_trillions"] = forecast["mean"].to_numpy()
    out["lower_95"] = forecast["mean_ci_lower"].to_numpy()
    out["upper_95"] = forecast["mean_ci_upper"].to_numpy()
    out["gap_trillions"] = out["trade_trillions"] - out["forecast_trillions"]
    actual_arr, predicted_arr = np.asarray(actual), np.asarray(predicted)
    model_mae = float(np.mean(np.abs(actual_arr - predicted_arr)))
    nonzero = actual_arr != 0
    mape = float(np.mean(np.abs((actual_arr[nonzero] - predicted_arr[nonzero]) / actual_arr[nonzero])) * 100) if nonzero.any() else None
    out.attrs["diagnostics"] = {
        "training_observations": len(train),
        "validation_observations": len(actual),
        "mae": model_mae,
        "mape": mape,
        "naive_mae": float(np.mean(np.abs(actual_arr - np.asarray(naive)))),
        "beats_naive": model_mae < float(np.mean(np.abs(actual_arr - np.asarray(naive)))),
        "warnings": sorted(set(fit_warnings)),
    }
    return out


def pick_arima_train_end(yearly: pd.DataFrame, preferred: int = 2007) -> int | None:
    """Pick a training cutoff that works with the filtered year range."""
    if yearly.empty:
        return None
    years = sorted(int(y) for y in yearly["year"].unique())
    before_preferred = [y for y in years if y <= preferred]
    if len(before_preferred) >= 10 and max(before_preferred) < years[-1]:
        return max(before_preferred)
    if len(years) >= 11:
        return years[max(9, int(len(years) * 0.7) - 1)]
    return None


def rf_yoy_surprise(yearly: pd.DataFrame, train_end_year: int = 2007) -> pd.DataFrame:
    df = yearly.sort_values("year")[["year", "trade_trillions", "yoy_pct"]].copy()
    df["lag1"] = df["yoy_pct"].shift(1)
    df["lag2"] = df["yoy_pct"].shift(2)
    df["lag_trade"] = df["trade_trillions"].shift(1)
    df = df.dropna()
    features = ["lag1", "lag2", "lag_trade"]
    train = df[df["year"] <= train_end_year]
    test = df[df["year"] > train_end_year].copy()
    if len(train) < 8 or test.empty:
        out = pd.DataFrame()
        out.attrs["diagnostics"] = {"warning": "Random Forest requires at least 8 training observations and one test observation."}
        return out
    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(train[features], train["yoy_pct"])
    test["predicted_yoy"] = model.predict(test[features])
    test["naive_yoy"] = test["lag1"]
    test["surprise"] = test["yoy_pct"] - test["predicted_yoy"]
    model_mae = float((test["yoy_pct"] - test["predicted_yoy"]).abs().mean())
    naive_mae = float((test["yoy_pct"] - test["naive_yoy"]).abs().mean())
    test.attrs["diagnostics"] = {
        "training_observations": len(train),
        "validation_observations": len(test),
        "mae": model_mae,
        "naive_mae": naive_mae,
        "beats_naive": model_mae < naive_mae,
        "features": features,
    }
    return test


def country_shock_clusters_from_cyf(
    cyf: pd.DataFrame,
    year_a: tuple[int, int],
    year_b: tuple[int, int],
) -> tuple[pd.DataFrame, pd.DataFrame, int, float]:
    def pct(y1: int, y2: int) -> pd.Series:
        b = cyf[cyf["year"] == y1].groupby("country_or_area")["trade_usd"].sum()
        a = cyf[cyf["year"] == y2].groupby("country_or_area")["trade_usd"].sum()
        common = b.index.intersection(a.index)
        return ((a[common] / b[common]) - 1) * 100

    shocks = pd.concat(
        [pct(*year_a).rename("shock_a_pct"), pct(*year_b).rename("shock_b_pct")], axis=1
    ).dropna()
    shocks = shocks.replace([np.inf, -np.inf], np.nan).dropna()
    shocks = shocks[
        shocks["shock_a_pct"].between(-80, 200) & shocks["shock_b_pct"].between(-80, 200)
    ]
    if len(shocks) < 3 or len(shocks.drop_duplicates()) < 2:
        return shocks, pd.DataFrame(), 0, float("nan")
    X = StandardScaler().fit_transform(shocks)
    best_k, best_score = 0, -1.0
    for k in range(2, min(5, len(shocks) - 1, len(shocks.drop_duplicates())) + 1):
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(X, labels)
        if score > best_score:
            best_k, best_score = k, score
    if best_k == 0:
        return shocks, pd.DataFrame(), 0, float("nan")
    shocks["cluster"] = KMeans(n_clusters=best_k, random_state=42, n_init=10).fit_predict(X)
    summary = (
        shocks.groupby("cluster")
        .agg(countries=("shock_a_pct", "count"), avg_a=("shock_a_pct", "mean"), avg_b=("shock_b_pct", "mean"))
        .round(1)
    )
    return shocks, summary, best_k, best_score


def oil_regression_from_cyf(category_year_flow: pd.DataFrame) -> tuple[pd.DataFrame, LinearRegression | None, float]:
    detail = category_year_flow[category_year_flow["category"] != AGGREGATE_CATEGORY]
    oil = (
        detail[detail["category"] == OIL_CATEGORY]
        .groupby("year")["trade_usd"]
        .sum()
        .div(1e12)
        .rename("oil_trillions")
    )
    total = detail.groupby("year")["trade_usd"].sum().div(1e12).rename("total_trillions")
    reg_df = pd.concat([total, oil], axis=1).dropna().reset_index()
    reg_df["non_oil_trillions"] = reg_df["total_trillions"] - reg_df["oil_trillions"]
    if len(reg_df) < 5 or reg_df["oil_trillions"].nunique() < 2:
        reg_df.attrs["diagnostics"] = {"warning": "At least 5 years with varying oil trade are required."}
        return reg_df, None, float("nan")
    model = LinearRegression()
    model.fit(reg_df[["oil_trillions"]], reg_df["non_oil_trillions"])
    reg_df["predicted"] = model.predict(reg_df[["oil_trillions"]])
    reg_df["residual"] = reg_df["non_oil_trillions"] - reg_df["predicted"]
    r2 = model.score(reg_df[["oil_trillions"]], reg_df["non_oil_trillions"])
    reg_df.attrs["diagnostics"] = {"observations": len(reg_df), "warning": "Association only; this model does not establish causation."}
    return reg_df, model, r2
