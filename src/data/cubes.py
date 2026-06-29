"""Pre-aggregated data cubes for fast filtering."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from config import CUBES_PATH, DATA_PATH, OUTPUT_DIR
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
    cyf = df.groupby(["country_or_area", "year", "flow"], as_index=False)["trade_usd"].sum()
    catyf = df.groupby(["category", "year", "flow"], as_index=False)["trade_usd"].sum()
    ccyy = df.groupby(["country_or_area", "category", "year", "flow"], as_index=False).agg(
        trade_usd=("trade_usd", "sum"),
        weight_kg=("weight_kg", "sum"),
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
    CUBES_PATH.touch()


@st.cache_data(show_spinner="Preparing analytics cubes…", ttl=86400)
def load_trade_cubes() -> TradeCubes:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "cyf": OUTPUT_DIR / "cube_country_year_flow.parquet",
        "catyf": OUTPUT_DIR / "cube_category_year_flow.parquet",
        "ccyy": OUTPUT_DIR / "cube_country_category_year.parquet",
        "ct": OUTPUT_DIR / "cube_commodity_totals.parquet",
        "yr": OUTPUT_DIR / "cube_year_records.parquet",
    }
    source_mtime = DATA_PATH.stat().st_mtime
    if CUBES_PATH.exists() and all(p.exists() and p.stat().st_mtime >= source_mtime for p in paths.values()):
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

    df = _read_source_dataframe()
    cubes = _build_cubes_from_df(df)
    _persist_cubes(cubes)
    return cubes
