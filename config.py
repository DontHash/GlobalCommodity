"""Application configuration and constants."""

import os
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DATA_BASE_URL = os.getenv("DATA_BASE_URL", "").rstrip("/")
DATA_PATH = Path(
    os.getenv(
        "TRADE_DATA_CSV",
        ROOT_DIR / "CSV Dataset" / "commodity_trade_statistics_data.csv",
    )
)
OUTPUT_DIR = (
    Path(tempfile.gettempdir()) / "global-commodity-data"
    if DATA_BASE_URL
    else ROOT_DIR / "outputs"
)
PARQUET_PATH = OUTPUT_DIR / "trade_data.parquet"
CUBES_PATH = OUTPUT_DIR / "trade_cubes.json"
DATA_QUALITY_PATH = OUTPUT_DIR / "data_quality.json"
CACHE_SCHEMA_VERSION = 2

AGGREGATE_CATEGORY = "all_commodities"
OIL_CATEGORY = "27_mineral_fuels_oils_distillation_products_etc"

FLOWS = ["Import", "Export", "Re-Import", "Re-Export"]

DEFAULT_YEAR_RANGE = (1995, 2015)
