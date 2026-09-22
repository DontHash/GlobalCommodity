import unittest

import pandas as pd

from src.analytics.concentration import category_contributions, concentration_by_year


def basket(values: list[float], *, scale: float = 1.0) -> pd.DataFrame:
    rows = [
        {
            "country_or_area": "A",
            "year": 2000,
            "flow": "Export",
            "category": "all_commodities",
            "trade_usd": sum(values) * scale,
        }
    ]
    rows.extend(
        {
            "country_or_area": "A",
            "year": 2000,
            "flow": "Export",
            "category": f"cat_{index}",
            "trade_usd": value * scale,
        }
        for index, value in enumerate(values)
    )
    return pd.DataFrame(rows)


class ConcentrationModelTest(unittest.TestCase):
    def test_four_equal_categories(self) -> None:
        data = basket([25, 25, 25, 25])
        metrics = concentration_by_year(
            data,
            canonical_totals=pd.DataFrame(
                [{"country_or_area": "A", "year": 2000, "flow": "Export", "trade_usd": 100}]
            ),
        ).iloc[0]
        self.assertAlmostEqual(metrics["hhi"], 0.25)
        self.assertAlmostEqual(metrics["effective_categories"], 4)
        self.assertAlmostEqual(metrics["normalized_hhi"], 0)
        self.assertAlmostEqual(metrics["diversification_score"], 1)
        self.assertAlmostEqual(metrics["top_three_share"], 0.75)
        self.assertAlmostEqual(metrics["coverage_pct"], 100)

    def test_single_category_and_scale_invariance(self) -> None:
        single = concentration_by_year(basket([100])).iloc[0]
        self.assertAlmostEqual(single["hhi"], 1)
        self.assertAlmostEqual(single["effective_categories"], 1)
        self.assertAlmostEqual(single["diversification_score"], 0)

        base = concentration_by_year(basket([70, 10, 10, 10])).iloc[0]
        scaled = concentration_by_year(basket([70, 10, 10, 10], scale=100)).iloc[0]
        self.assertAlmostEqual(base["hhi"], 0.52)
        self.assertAlmostEqual(base["hhi"], scaled["hhi"])
        self.assertAlmostEqual(
            base["diversification_score"], scaled["diversification_score"]
        )

    def test_duplicate_rows_and_contributions(self) -> None:
        data = basket([50, 50])
        duplicate = data[data["category"].eq("cat_0")].copy()
        data.loc[data["category"].eq("cat_0"), "trade_usd"] = 25
        duplicate["trade_usd"] = 25
        data = pd.concat([data, duplicate], ignore_index=True)

        metrics = concentration_by_year(data, conditional=True).iloc[0]
        contributions = category_contributions(data, "A", 2000)
        self.assertAlmostEqual(metrics["hhi"], 0.5)
        self.assertTrue(metrics["conditional"])
        self.assertAlmostEqual(contributions["share"].sum(), 1)
        self.assertAlmostEqual(contributions["hhi_contribution"].sum(), 1)


if __name__ == "__main__":
    unittest.main()
