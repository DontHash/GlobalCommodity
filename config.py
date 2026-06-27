"""Application configuration and constants."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DATA_PATH = ROOT_DIR / "CSV Dataset" / "commodity_trade_statistics_data.csv"
OUTPUT_DIR = ROOT_DIR / "outputs"
PARQUET_PATH = OUTPUT_DIR / "trade_data.parquet"
CUBES_PATH = OUTPUT_DIR / "trade_cubes.parquet"

AGGREGATE_CATEGORY = "all_commodities"
OIL_CATEGORY = "27_mineral_fuels_oils_distillation_products_etc"

FLOWS = ["Import", "Export", "Re-Import", "Re-Export"]

DEFAULT_YEAR_RANGE = (1995, 2015)
TOP_N = 15

# Visual design
CHART_TEMPLATE = "plotly_white"
COLOR_SEQUENCE = ["#0ea5e9", "#6366f1", "#14b8a6", "#f43f5e", "#f59e0b", "#8b5cf6"]
MAP_COLORSCALE = "Blues"

UI = {
    "accent": "#0ea5e9",
    "accent_dark": "#0284c7",
    "surface": "#f8fafc",
    "border": "#e2e8f0",
    "text": "#0f172a",
    "muted": "#64748b",
}
