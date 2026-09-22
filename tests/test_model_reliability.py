import unittest

import numpy as np
import pandas as pd

from src.analytics.forecast import regression_forecast
from src.analytics.mining import detect_yoy_anomalies, rf_yoy_surprise


class ModelReliabilityTest(unittest.TestCase):
    def test_forecast_reports_rolling_validation_and_interval(self) -> None:
        trajectory = pd.DataFrame(
            {"year": range(2000, 2010), "value": np.linspace(10.0, 20.0, 10)}
        )
        result = regression_forecast(trajectory, "value", 2009, horizon=2)

        self.assertIsNotNone(result)
        self.assertEqual(result.validation_observations, 5)
        self.assertTrue({"lower_95", "upper_95"}.issubset(result.series.columns))
        self.assertTrue((result.series["lower_95"] <= result.series["value"]).all())
        self.assertTrue((result.series["upper_95"] >= result.series["value"]).all())

    def test_small_constant_anomaly_sample_is_safe(self) -> None:
        result = detect_yoy_anomalies(pd.DataFrame({"year": [1, 2], "yoy_pct": [3.0, 3.0]}))
        self.assertFalse(result["is_anomaly"].any())
        self.assertIn("warning", result.attrs["diagnostics"])

    def test_random_forest_uses_only_lagged_trade(self) -> None:
        yearly = pd.DataFrame(
            {
                "year": range(2000, 2015),
                "trade_trillions": np.linspace(1.0, 2.5, 15),
                "yoy_pct": np.sin(np.arange(15)) * 3 + 5,
            }
        )
        result = rf_yoy_surprise(yearly, train_end_year=2010)
        self.assertEqual(result.attrs["diagnostics"]["features"], ["lag1", "lag2", "lag_trade"])
        self.assertNotIn("trade_trillions", result.attrs["diagnostics"]["features"])


if __name__ == "__main__":
    unittest.main()
