"""Data loading, parquet cache, and lazy raw access."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

from config import (
    AGGREGATE_CATEGORY,
    DATA_BASE_URL,
    DATA_PATH,
    DATA_QUALITY_PATH,
    OUTPUT_DIR,
    PARQUET_PATH,
)
from src.data.artifacts import ensure_artifact
from src.data.validation import (
    report_matches_source,
    save_data_quality_report,
    source_fingerprint,
    validate_trade_data,
)


def _read_source_dataframe() -> pd.DataFrame:
    """Read CSV once into parquet for faster subsequent loads."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if DATA_BASE_URL:
        return pd.read_parquet(ensure_artifact(PARQUET_PATH))

    if PARQUET_PATH.exists() and report_matches_source(DATA_QUALITY_PATH, DATA_PATH):
        return pd.read_parquet(PARQUET_PATH)

    df = pd.read_csv(
        DATA_PATH,
        low_memory=False,
        dtype={"comm_code": str},
    )
    for col in ("year", "trade_usd", "weight_kg", "quantity"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    report = validate_trade_data(df, **source_fingerprint(DATA_PATH))
    save_data_quality_report(report, DATA_QUALITY_PATH)
    if not report.valid:
        raise ValueError(
            "Trade data failed validation: "
            + "; ".join(report.errors)
            + f". See {DATA_QUALITY_PATH}."
        )

    df["year"] = df["year"].astype(int)
    df.to_parquet(PARQUET_PATH, index=False)
    return df


def _available_parquet() -> Path:
    if DATA_BASE_URL:
        return ensure_artifact(PARQUET_PATH)
    if not PARQUET_PATH.exists() or not report_matches_source(DATA_QUALITY_PATH, DATA_PATH):
        _read_source_dataframe()
    return PARQUET_PATH


@lru_cache(maxsize=4)
def load_filtered_sample(
    year_range: tuple[int, int],
    countries: tuple[str, ...] | None,
    categories: tuple[str, ...] | None,
    flows: tuple[str, ...] | None,
    exclude_aggregate: bool,
    limit: int,
) -> pd.DataFrame:
    """Return a reproducible random sample of matching source rows."""
    return _sample_parquet(
        _available_parquet(), year_range, countries, categories, flows,
        exclude_aggregate, limit,
    )


def _sample_parquet(
    path: Path,
    year_range: tuple[int, int],
    countries: tuple[str, ...] | None,
    categories: tuple[str, ...] | None,
    flows: tuple[str, ...] | None,
    exclude_aggregate: bool,
    limit: int,
) -> pd.DataFrame:
    """Keep the rows with the lowest random priorities while scanning batches."""
    filters = (ds.field("year") >= year_range[0]) & (ds.field("year") <= year_range[1])
    for column, values in (("country_or_area", countries), ("category", categories), ("flow", flows)):
        if values:
            filters &= ds.field(column).isin(values)
    if exclude_aggregate:
        filters &= ds.field("category") != AGGREGATE_CATEGORY

    dataset = ds.dataset(path, format="parquet")
    selected: pd.DataFrame | None = None
    priorities = np.empty(0)
    random = np.random.default_rng(42)
    for batch in dataset.scanner(filter=filters, batch_size=65_536).to_batches():
        frame = batch.to_pandas()
        keys = random.random(len(frame))
        if len(frame) > limit:
            indices = np.argpartition(keys, limit - 1)[:limit]
            frame, keys = frame.iloc[indices], keys[indices]
        combined = frame if selected is None else pd.concat((selected, frame), ignore_index=True)
        priorities = keys if selected is None else np.concatenate((priorities, keys))
        if len(combined) > limit:
            indices = np.argpartition(priorities, limit - 1)[:limit]
            selected, priorities = combined.iloc[indices].reset_index(drop=True), priorities[indices]
        else:
            selected = combined

    if selected is None:
        selected = dataset.head(0).to_pandas()
    selected = selected.iloc[np.argsort(priorities)].reset_index(drop=True)
    selected["unit_price_per_kg"] = selected["trade_usd"] / selected["weight_kg"].where(selected["weight_kg"] > 0)
    return selected


def _random_sample(df: pd.DataFrame, limit: int) -> pd.DataFrame:
    """Use a stable seed so preview paging and downloads show the same sample."""
    return df.sample(n=min(limit, len(df)), random_state=42)


@lru_cache(maxsize=128)
def load_scoped_commodity_totals(
    comm_codes: tuple[str, ...],
    year_range: tuple[int, int],
    countries: tuple[str, ...] | None,
    categories: tuple[str, ...] | None,
    flows: tuple[str, ...] | None,
    exclude_aggregate: bool,
) -> pd.DataFrame:
    """Aggregate matching commodities while pushing all sidebar filters to Parquet."""
    if not comm_codes:
        return pd.DataFrame(
            columns=["comm_code", "commodity", "category", "trade_usd", "records"]
        )

    filters: list[tuple[str, str, object]] = [
        ("year", ">=", year_range[0]),
        ("year", "<=", year_range[1]),
        ("comm_code", "in", list(comm_codes)),
    ]
    if countries:
        filters.append(("country_or_area", "in", list(countries)))
    if categories:
        filters.append(("category", "in", list(categories)))
    if flows:
        filters.append(("flow", "in", list(flows)))
    if exclude_aggregate:
        filters.append(("category", "!=", AGGREGATE_CATEGORY))

    scoped = pd.read_parquet(
        _available_parquet(),
        columns=["comm_code", "commodity", "category", "trade_usd"],
        filters=filters,
    )
    return (
        scoped.groupby(["comm_code", "commodity", "category"], as_index=False)
        .agg(trade_usd=("trade_usd", "sum"), records=("trade_usd", "size"))
        .sort_values("trade_usd", ascending=False)
    )
