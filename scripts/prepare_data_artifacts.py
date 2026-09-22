"""Build and verify the Parquet files uploaded for production."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import DATA_BASE_URL, DATA_PATH, OUTPUT_DIR, PARQUET_PATH  # noqa: E402
from src.data.cubes import _build_cubes_from_df, _persist_cubes  # noqa: E402
from src.data.loader import _read_source_dataframe  # noqa: E402


ARTIFACTS = (
    "trade_data.parquet",
    "cube_country_year_flow.parquet",
    "cube_category_year_flow.parquet",
    "cube_country_category_year.parquet",
    "cube_commodity_totals.parquet",
    "cube_year_records.parquet",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if DATA_BASE_URL:
        raise SystemExit("Unset DATA_BASE_URL before building local artifacts.")
    if not DATA_PATH.exists():
        raise SystemExit(f"Source CSV not found: {DATA_PATH}")

    frame = _read_source_dataframe()
    _persist_cubes(_build_cubes_from_df(frame))
    if not PARQUET_PATH.exists():
        raise SystemExit(f"Parquet build failed: {PARQUET_PATH}")

    manifest = {
        "artifacts": [
            {
                "name": name,
                "bytes": (OUTPUT_DIR / name).stat().st_size,
                "sha256": sha256(OUTPUT_DIR / name),
            }
            for name in ARTIFACTS
        ]
    }
    manifest_path = OUTPUT_DIR / "data_artifacts.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Prepared {len(ARTIFACTS)} artifacts in {OUTPUT_DIR}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
