import unittest

import pandas as pd

from src.analytics.kpis import root_cause_drivers
from src.api import default_countries
from src.data.context import _build_filtered_view_from_cubes
from src.data.cubes import _build_cubes_from_df
from src.data.loader import _random_sample
from src.data.validation import validate_trade_data
from src.utils.labels import CATEGORY_LABEL_OVERRIDES, category_label


def trade_frame() -> pd.DataFrame:
    rows = [
        ("A", 2000, "TOTAL", "All commodities", "Export", 100, "all_commodities"),
        ("A", 2000, "01", "Alpha", "Export", 40, "cat_a"),
        ("A", 2000, "02", "Beta", "Export", 30, "cat_b"),
        ("B", 2000, "TOTAL", "All commodities", "Export", 200, "all_commodities"),
        ("B", 2000, "01", "Alpha", "Export", 80, "cat_a"),
        ("B", 2000, "02", "Beta", "Export", 50, "cat_b"),
        ("A", 2001, "01", "Alpha", "Export", 60, "cat_a"),
        ("A", 2001, "02", "Beta", "Export", 40, "cat_b"),
    ]
    return pd.DataFrame(
        [
            {
                "country_or_area": country,
                "year": year,
                "comm_code": code,
                "commodity": commodity,
                "flow": flow,
                "trade_usd": trade,
                "weight_kg": 1.0,
                "quantity_name": "Weight in kilograms",
                "quantity": 1.0,
                "category": category,
            }
            for country, year, code, commodity, flow, trade, category in rows
        ]
    )


class DataPipelineTest(unittest.TestCase):
    def test_canonical_totals_do_not_add_aggregate_and_detail_rows(self) -> None:
        cubes = _build_cubes_from_df(trade_frame())
        totals = cubes.country_year_flow.set_index(["country_or_area", "year", "flow"])
        self.assertEqual(totals.loc[("A", 2000, "Export"), "trade_usd"], 100)
        self.assertEqual(totals.loc[("A", 2001, "Export"), "trade_usd"], 100)

    def test_country_and_category_filters_propagate_to_every_summary(self) -> None:
        cubes = _build_cubes_from_df(trade_frame())
        country_view = _build_filtered_view_from_cubes(
            cubes, (2000, 2000), ("A",), None, ("Export",)
        )
        self.assertEqual(country_view.country_year_flow["trade_usd"].sum(), 100)
        self.assertEqual(country_view.category_year_flow["trade_usd"].sum(), 70)
        self.assertEqual(country_view.total_basis, "Authoritative country totals")

        category_view = _build_filtered_view_from_cubes(
            cubes, (2000, 2000), None, ("cat_a",), ("Export",)
        )
        self.assertEqual(category_view.country_year_flow["trade_usd"].sum(), 120)
        self.assertEqual(category_view.category_year_flow["trade_usd"].sum(), 120)
        self.assertEqual(category_view.year_records["records"].sum(), 2)

        published_view = _build_filtered_view_from_cubes(
            cubes, (2000, 2000), None, None, ("Export",), False
        )
        self.assertEqual(published_view.country_year_flow["trade_usd"].sum(), 300)
        self.assertEqual(published_view.total_basis, "Authoritative country totals")
        self.assertEqual(country_view.country_year_flow["trade_usd"].sum(), 100)
        self.assertNotIn("all_commodities", country_view.category_year_flow["category"].values)
        self.assertIn("all_commodities", published_view.category_year_flow["category"].values)

    def test_trade_balance_keeps_export_only_and_import_only_countries(self) -> None:
        cubes = _build_cubes_from_df(trade_frame())
        view = _build_filtered_view_from_cubes(cubes, (2000, 2000), None, None, None)
        map_rows = view.map_metrics(2000, "trade_balance")
        balances = map_rows.set_index("country_or_area")["value"]
        self.assertEqual(balances.to_dict(), {"A": 1e-7, "B": 2e-7})
        self.assertFalse(map_rows["value"].isna().any())

    def test_category_labels_are_complete_and_plain_language(self) -> None:
        self.assertEqual(category_label("39_plastics_and_articles_thereof"), "Plastics and plastic products")
        self.assertEqual(
            category_label("03_fish_crustaceans_molluscs_aquatic_invertebrates_ne"),
            "Fish and seafood",
        )
        self.assertEqual(
            category_label("86_railway_tramway_locomotives_rolling_stock_equipmen"),
            "Railway vehicles and equipment",
        )
        self.assertEqual(category_label("74_copper_and_articles_thereof"), "Copper and copper products")
        self.assertEqual(category_label("88_aircraft_spacecraft_and_parts_thereof"), "Aircraft, spacecraft and parts")
        self.assertEqual(category_label("99_commodities_not_specified_according_to_kind"), "Unspecified commodities")
        self.assertGreaterEqual(len(CATEGORY_LABEL_OVERRIDES), 96)
        for label in CATEGORY_LABEL_OVERRIDES.values():
            self.assertNotRegex(label.lower(), r"\b(thereof|nes|etc|miscellaneous|articles|manufactures|related)\b")

    def test_driver_tables_include_disappearing_and_new_countries(self) -> None:
        frame = trade_frame()
        new_country = frame[(frame["country_or_area"] == "A") & (frame["year"] == 2001)].iloc[[0]].copy()
        new_country["country_or_area"] = "C"
        new_country["trade_usd"] = 50
        cubes = _build_cubes_from_df(pd.concat([frame, new_country], ignore_index=True))
        view = _build_filtered_view_from_cubes(cubes, (2000, 2001), None, None, ("Export",))
        drivers = root_cause_drivers(view, 2000, 2001)
        self.assertEqual(drivers["top_country_declines"].iloc[0]["country"], "B")
        self.assertEqual(drivers["top_country_declines"].iloc[0]["change_pct"], -100)
        self.assertEqual(drivers["top_country_gains"].iloc[0]["country"], "C")
        self.assertTrue(pd.isna(drivers["top_country_gains"].iloc[0]["change_pct"]))
        self.assertFalse(drivers["top_category_declines"].empty)

    def test_preferred_country_defaults(self) -> None:
        options = ["Afghanistan", "China", "Germany", "USA", "Zimbabwe"]
        self.assertEqual(default_countries(options), ["USA", "China", "Germany"])

    def test_preview_is_a_reproducible_random_source_sample(self) -> None:
        frame = pd.DataFrame({
            "country_or_area": [f"Country {i % 6}" for i in range(60)],
            "category": [f"Category {i % 5}" for i in range(60)],
            "commodity": [f"Commodity {i % 7}" for i in range(60)],
            "year": [2000 + i % 4 for i in range(60)],
            "trade_usd": range(60),
        })
        sample = _random_sample(frame, 12)
        self.assertTrue(sample.equals(frame.sample(n=12, random_state=42)))
        self.assertTrue(sample.equals(_random_sample(frame, 12)))
        self.assertTrue(set(sample.index).issubset(frame.index))
        self.assertGreaterEqual(sample["country_or_area"].nunique(), 3)
        self.assertGreaterEqual(sample["category"].nunique(), 3)
        self.assertGreaterEqual(sample["commodity"].nunique(), 3)
        self.assertGreaterEqual(sample["year"].nunique(), 3)

    def test_quality_gate_rejects_unsupported_values(self) -> None:
        bad = trade_frame()
        bad.loc[0, "flow"] = "Unknown"
        bad.loc[1, "trade_usd"] = -1
        bad["year"] = bad["year"].astype(object)
        bad.loc[2, "year"] = "bad"
        report = validate_trade_data(bad)
        self.assertFalse(report.valid)
        self.assertTrue(any("Unsupported flow" in error for error in report.errors))
        self.assertTrue(any("negative" in error for error in report.errors))
        self.assertIn("year must be numeric", report.errors)


if __name__ == "__main__":
    unittest.main()
