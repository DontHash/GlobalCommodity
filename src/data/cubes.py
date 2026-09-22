"""Pre-aggregated data cubes for fast filtering."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from config import (
    AGGREGATE_CATEGORY,
    CACHE_SCHEMA_VERSION,
    CUBES_PATH,
    DATA_BASE_URL,
    DATA_PATH,
    OUTPUT_DIR,
)
from src.data.artifacts import ensure_artifact
from src.data.loader import _read_source_dataframe


@dataclass(frozen=True)
class CubeMeta:
    year_min: int
    year_max: int
    countries: tuple[str, ...]
    categories: tuple[str, ...]
    flows: tuple[str, ...]


@dataclass
class TradeCubes:
    meta: CubeMeta
    country_year_flow: pd.DataFrame
    category_year_flow: pd.DataFrame
    country_category_year: pd.DataFrame
    commodity_totals: pd.DataFrame
    year_records: pd.DataFrame


def _build_cubes_from_df(df: pd.DataFrame) -> TradeCubes:
    total_keys = ["country_or_area", "year", "flow"]
    aggregate_rows = df[df["category"] == AGGREGATE_CATEGORY]
    detail_rows = df[df["category"] != AGGREGATE_CATEGORY]

    authoritative = aggregate_rows.groupby(total_keys, as_index=False)["trade_usd"].sum()
    fallback = detail_rows.groupby(total_keys, as_index=False)["trade_usd"].sum()
    # Prefer the published aggregate; use detailed rows only when that key has no aggregate.
    cyf = (
        pd.concat(
            [authoritative.assign(_priority=0), fallback.assign(_priority=1)],
            ignore_index=True,
        )
        .sort_values("_priority")
        .drop_duplicates(total_keys)
        .drop(columns="_priority")
    )
    catyf = df.groupby(["category", "year", "flow"], as_index=False)["trade_usd"].sum()
    ccyy = df.groupby(["country_or_area", "category", "year", "flow"], as_index=False).agg(
        trade_usd=("trade_usd", "sum"),
        weight_kg=("weight_kg", "sum"),
        records=("trade_usd", "size"),
    )
    commodity_totals = (
        df.groupby(["comm_code", "commodity", "category"], as_index=False)
        .agg(trade_usd=("trade_usd", "sum"), records=("trade_usd", "count"))
    )
    year_records = (
        df.groupby("year", as_index=False)
        .agg(
            records=("trade_usd", "count"),
            countries=("country_or_area", "nunique"),
            commodities=("commodity", "nunique"),
        )
    )
    meta = CubeMeta(
        year_min=int(df["year"].min()),
        year_max=int(df["year"].max()),
        countries=tuple(sorted(df["country_or_area"].unique())),
        categories=tuple(sorted(df["category"].unique())),
        flows=tuple(sorted(df["flow"].unique())),
    )
    return TradeCubes(meta, cyf, catyf, ccyy, commodity_totals, year_records)


def _persist_cubes(cubes: TradeCubes) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cubes.country_year_flow.to_parquet(OUTPUT_DIR / "cube_country_year_flow.parquet", index=False)
    cubes.category_year_flow.to_parquet(OUTPUT_DIR / "cube_category_year_flow.parquet", index=False)
    cubes.country_category_year.to_parquet(OUTPUT_DIR / "cube_country_category_year.parquet", index=False)
    cubes.commodity_totals.to_parquet(OUTPUT_DIR / "cube_commodity_totals.parquet", index=False)
    cubes.year_records.to_parquet(OUTPUT_DIR / "cube_year_records.parquet", index=False)
    CUBES_PATH.write_text(
        json.dumps({"cache_schema_version": CACHE_SCHEMA_VERSION}), encoding="utf-8"
    )


def _cube_cache_is_current(paths: dict[str, Path], source_mtime: float) -> bool:
    if not CUBES_PATH.exists():
        return False
    try:
        manifest = json.loads(CUBES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return manifest.get("cache_schema_version") == CACHE_SCHEMA_VERSION and all(
        path.exists() and path.stat().st_mtime >= source_mtime for path in paths.values()
    )


def _read_cubes(paths: dict[str, Path]) -> TradeCubes:
    cyf = pd.read_parquet(paths["cyf"])
    catyf = pd.read_parquet(paths["catyf"])
    ccyy = pd.read_parquet(paths["ccyy"])
    ct = pd.read_parquet(paths["ct"])
    yr = pd.read_parquet(paths["yr"])
    meta = CubeMeta(
        year_min=int(cyf["year"].min()),
        year_max=int(cyf["year"].max()),
        countries=tuple(sorted(cyf["country_or_area"].unique())),
        categories=tuple(sorted(catyf["category"].unique())),
        flows=tuple(sorted(cyf["flow"].unique())),
    )
    return TradeCubes(meta, cyf, catyf, ccyy, ct, yr)


@lru_cache(maxsize=1)
def load_trade_cubes() -> TradeCubes:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "cyf": OUTPUT_DIR / "cube_country_year_flow.parquet",
        "catyf": OUTPUT_DIR / "cube_category_year_flow.parquet",
        "ccyy": OUTPUT_DIR / "cube_country_category_year.parquet",
        "ct": OUTPUT_DIR / "cube_commodity_totals.parquet",
        "yr": OUTPUT_DIR / "cube_year_records.parquet",
    }
    if DATA_BASE_URL:
        for path in paths.values():
            ensure_artifact(path)
        return _read_cubes(paths)

    source_mtime = DATA_PATH.stat().st_mtime
    if _cube_cache_is_current(paths, source_mtime):
        return _read_cubes(paths)

    df = _read_source_dataframe()
    cubes = _build_cubes_from_df(df)
    _persist_cubes(cubes)
    return cubes
