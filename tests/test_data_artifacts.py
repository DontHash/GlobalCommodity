import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.data.artifacts import ensure_artifact
from src.data.loader import _sample_parquet


class DataArtifactTest(unittest.TestCase):
    def test_remote_artifact_is_downloaded_once(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "cube.parquet"
            with (
                patch("src.data.artifacts.DATA_BASE_URL", "https://data.example/v2"),
                patch("src.data.artifacts.urlopen", return_value=io.BytesIO(b"parquet")) as fetch,
            ):
                self.assertEqual(ensure_artifact(target).read_bytes(), b"parquet")
                ensure_artifact(target)
            fetch.assert_called_once()

    def test_filtered_sample_scans_multiple_batches_without_loading_all_rows(self):
        count = 70_000
        numbers = np.arange(count)
        frame = pd.DataFrame({
            "country_or_area": np.where(numbers % 3 == 0, "A", "B"),
            "year": 2000 + numbers % 2,
            "comm_code": "01",
            "commodity": "Product",
            "flow": "Export",
            "trade_usd": numbers,
            "weight_kg": 2,
            "quantity_name": "Weight",
            "quantity": 2,
            "category": np.where(numbers % 5 == 0, "all_commodities", "cat_a"),
        })
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.parquet"
            frame.to_parquet(path, index=False)
            args = (path, (2000, 2001), ("A",), ("cat_a",), ("Export",), True, 500)
            sample = _sample_parquet(*args)
            self.assertTrue(sample.equals(_sample_parquet(*args)))
            self.assertEqual(len(sample), 500)
            self.assertEqual(sample["country_or_area"].unique().tolist(), ["A"])
            self.assertEqual(sample["category"].unique().tolist(), ["cat_a"])
            self.assertGreater(sample["trade_usd"].max(), 65_536)
            self.assertTrue(pd.api.types.is_numeric_dtype(sample["trade_usd"]))
            self.assertTrue(pd.api.types.is_numeric_dtype(sample["unit_price_per_kg"]))


if __name__ == "__main__":
    unittest.main()
