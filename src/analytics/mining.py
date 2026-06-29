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

from config import OIL_CATEGORY

warnings.filterwarnings("ignore")


def detect_yoy_anomalies(yearly: pd.DataFrame, z_threshold: float = 1.5) -> pd.DataFrame:
    out = yearly.dropna(subset=["yoy_pct"]).copy()
    out["yoy_z"] = (out["yoy_pct"] - out["yoy_pct"].mean()) / out["yoy_pct"].std()
    out["is_anomaly"] = out["yoy_z"].abs() > z_threshold
    return out


def isolation_forest_years(yearly: pd.DataFrame, contamination: float = 0.12) -> pd.DataFrame:
    cols = ["trade_trillions", "yoy_pct", "records"]
    data = yearly.dropna(subset=[c for c in cols if c in yearly.columns]).copy()
    use_cols = [c for c in cols if c in data.columns]
    X = StandardScaler().fit_transform(data[use_cols])
    data["is_anomaly"] = IsolationForest(contamination=contamination, random_state=42).fit_predict(X) == -1
    return data


def change_points(series: np.ndarray, years: np.ndarray, pen: float = 10.0) -> list[int]:
    algo = rpt.Pelt(model="l2", min_size=3, jump=1).fit(series.reshape(-1, 1))
    return [int(years[i]) for i in algo.predict(pen=pen)[:-1]]


def arima_forecast(yearly: pd.DataFrame, train_end_year: int) -> pd.DataFrame:
    """ARIMA counterfactual; returns empty frame with schema if not enough data."""
    empty = pd.DataFrame(
        columns=["year", "trade_trillions", "forecast_trillions", "gap_trillions", "trade_usd"]
    )
    if yearly.empty:
        return empty

    series = yearly.sort_values("year")
    train = series.loc[series["year"] <= train_end_year, "trade_trillions"].values
    future = series.loc[series["year"] > train_end_year]
    if len(train) < 3 or future.empty:
        return empty

    forecast = ARIMA(train, order=(1, 1, 1)).fit().forecast(len(future))
    out = future.copy()
    out["forecast_trillions"] = forecast
    out["gap_trillions"] = out["trade_trillions"] - out["forecast_trillions"]
    return out


def pick_arima_train_end(yearly: pd.DataFrame, preferred: int = 2007) -> int | None:
    """Pick a training cutoff that works with the filtered year range."""
    if yearly.empty:
        return None
    years = sorted(int(y) for y in yearly["year"].unique())
    before_preferred = [y for y in years if y <= preferred]
    if len(before_preferred) >= 3:
        return max(before_preferred)
    if len(years) >= 4:
        return years[max(2, int(len(years) * 0.55) - 1)]
    return None


def rf_yoy_surprise(yearly: pd.DataFrame, train_end_year: int = 2007) -> pd.DataFrame:
    df = yearly.sort_values("year")[["year", "trade_trillions", "yoy_pct"]].copy()
    df["lag1"] = df["yoy_pct"].shift(1)
    df["lag2"] = df["yoy_pct"].shift(2)
    df = df.dropna()
    features = ["lag1", "lag2", "trade_trillions"]
    train = df[df["year"] <= train_end_year]
    test = df[df["year"] > train_end_year].copy()
    if train.empty or test.empty:
        return pd.DataFrame()
    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(train[features], train["yoy_pct"])
    test["predicted_yoy"] = model.predict(test[features])
    test["surprise"] = test["yoy_pct"] - test["predicted_yoy"]
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
    X = StandardScaler().fit_transform(shocks)
    best_k, best_score = 3, -1.0
    for k in range(2, 6):
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X)
        score = silhouette_score(X, labels)
        if score > best_score:
            best_k, best_score = k, score
    shocks["cluster"] = KMeans(n_clusters=best_k, random_state=42, n_init=10).fit_predict(X)
    summary = (
        shocks.groupby("cluster")
        .agg(countries=("shock_a_pct", "count"), avg_a=("shock_a_pct", "mean"), avg_b=("shock_b_pct", "mean"))
        .round(1)
    )
    return shocks, summary, best_k, best_score


def oil_regression_from_cyf(category_year_flow: pd.DataFrame) -> tuple[pd.DataFrame, LinearRegression, float]:
    oil = (
        category_year_flow[category_year_flow["category"] == OIL_CATEGORY]
        .groupby("year")["trade_usd"]
        .sum()
        .div(1e12)
        .rename("oil_trillions")
    )
    total = category_year_flow.groupby("year")["trade_usd"].sum().div(1e12).rename("total_trillions")
    reg_df = pd.concat([total, oil], axis=1).dropna().reset_index()
    model = LinearRegression()
    model.fit(reg_df[["oil_trillions"]], reg_df["total_trillions"])
    reg_df["predicted"] = model.predict(reg_df[["oil_trillions"]])
    reg_df["residual"] = reg_df["total_trillions"] - reg_df["predicted"]
    r2 = model.score(reg_df[["oil_trillions"]], reg_df["total_trillions"])
    return reg_df, model, r2
