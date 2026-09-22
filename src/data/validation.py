"""Small, explicit data contract for the trade dataset."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from config import AGGREGATE_CATEGORY, CACHE_SCHEMA_VERSION, FLOWS


REQUIRED_COLUMNS = {
    "country_or_area",
    "year",
    "comm_code",
    "commodity",
    "flow",
    "trade_usd",
    "weight_kg",
    "quantity_name",
    "quantity",
    "category",
}
KEY_COLUMNS = (
    "country_or_area",
    "year",
    "comm_code",
    "commodity",
    "flow",
    "trade_usd",
    "category",
)


@dataclass(frozen=True)
class DataQualityReport:
    cache_schema_version: int
    source_size: int
    source_mtime_ns: int
    rows: int
    year_min: int | None
    year_max: int | None
    null_counts: dict[str, int]
    aggregate_rows: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {**asdict(self), "valid": self.valid}


def source_fingerprint(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {"source_size": stat.st_size, "source_mtime_ns": stat.st_mtime_ns}


def validate_trade_data(
    df: pd.DataFrame, *, source_size: int = 0, source_mtime_ns: int = 0
) -> DataQualityReport:
    """Return fatal errors and recoverable warnings without changing the frame."""
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        return DataQualityReport(
            CACHE_SCHEMA_VERSION,
            source_size,
            source_mtime_ns,
            len(df),
            None,
            None,
            {},
            0,
            (f"Missing required columns: {missing}",),
            (),
        )

    errors: list[str] = []
    warnings: list[str] = []
    null_counts = {col: int(df[col].isna().sum()) for col in sorted(REQUIRED_COLUMNS)}
    for col in KEY_COLUMNS:
        if null_counts[col]:
            errors.append(f"{col} contains {null_counts[col]:,} null values")

    for col in ("country_or_area", "comm_code", "commodity", "flow", "category"):
        blank_count = int(df[col].astype("string").str.strip().eq("").sum())
        if blank_count:
            errors.append(f"{col} contains {blank_count:,} blank values")

    year_is_numeric = pd.api.types.is_numeric_dtype(df["year"])
    if not year_is_numeric:
        errors.append("year must be numeric")
    if not pd.api.types.is_numeric_dtype(df["trade_usd"]):
        errors.append("trade_usd must be numeric")

    valid_years = df["year"].dropna() if year_is_numeric else pd.Series(dtype="float64")
    year_min = int(valid_years.min()) if len(valid_years) else None
    year_max = int(valid_years.max()) if len(valid_years) else None
    if year_min is not None and (year_min < 1988 or year_max > 2016):
        warnings.append(
            f"year range {year_min}-{year_max} extends beyond documented coverage 1988-2016"
        )

    if pd.api.types.is_numeric_dtype(df["trade_usd"]):
        negative_trade = int(df["trade_usd"].lt(0).sum())
        if negative_trade:
            errors.append(f"trade_usd contains {negative_trade:,} negative values")

    unknown_flows = sorted(
        str(value) for value in set(df["flow"].dropna()) if value not in FLOWS
    )
    if unknown_flows:
        errors.append(f"Unsupported flow values: {unknown_flows}")

    for col in ("weight_kg", "quantity"):
        if null_counts[col]:
            warnings.append(f"{col} contains {null_counts[col]:,} null values")

    aggregate_rows = int(df["category"].eq(AGGREGATE_CATEGORY).sum())
    if aggregate_rows and aggregate_rows < len(df):
        warnings.append(
            "Aggregate and detailed category rows coexist; canonical totals must not sum both"
        )

    return DataQualityReport(
        CACHE_SCHEMA_VERSION,
        source_size,
        source_mtime_ns,
        len(df),
        year_min,
        year_max,
        null_counts,
        aggregate_rows,
        tuple(errors),
        tuple(warnings),
    )


def save_data_quality_report(report: DataQualityReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def report_matches_source(report_path: Path, source_path: Path) -> bool:
    if not report_path.exists():
        return False
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        report.get("valid") is True
        and report.get("cache_schema_version") == CACHE_SCHEMA_VERSION
        and {
            "source_size": report.get("source_size"),
            "source_mtime_ns": report.get("source_mtime_ns"),
        }
        == source_fingerprint(source_path)
    )
