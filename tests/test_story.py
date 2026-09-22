import unittest

import pandas as pd

from src.analytics.story import shock_events


class StoryEventsTest(unittest.TestCase):
    def test_peak_event_uses_2013_to_2014(self) -> None:
        yearly = pd.DataFrame({"year": [2013, 2014], "trade_trillions": [10.0, 12.0]})
        peak = shock_events(yearly).iloc[0]
        self.assertEqual((peak["from_year"], peak["to_year"]), (2013, 2014))
        self.assertEqual(peak["change_pct"], 20.0)
        self.assertEqual(peak["volume_trillions"], 12.0)


if __name__ == "__main__":
    unittest.main()
