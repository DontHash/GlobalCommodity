"""Story-specific metrics."""

from __future__ import annotations

import pandas as pd


def shock_events(yearly: pd.DataFrame) -> pd.DataFrame:
    events = [
        ("2009 financial crisis", 2008, 2009),
        ("2015 commodity slowdown", 2014, 2015),
        ("2010 rebound", 2009, 2010),
    ]
    rows = []
    peak = yearly.loc[yearly["trade_trillions"].idxmax()]
    rows.append(
        {
            "event": "peak year",
            "from_year": int(peak["year"]),
            "to_year": None,
            "change_pct": None,
            "volume_trillions": round(peak["trade_trillions"], 2),
        }
    )
    for name, y1, y2 in events:
        if y1 not in yearly["year"].values or y2 not in yearly["year"].values:
            continue
        v1 = yearly.loc[yearly["year"] == y1, "trade_trillions"].iloc[0]
        v2 = yearly.loc[yearly["year"] == y2, "trade_trillions"].iloc[0]
        rows.append(
            {
                "event": name,
                "from_year": y1,
                "to_year": y2,
                "change_pct": round((v2 / v1 - 1) * 100, 1),
                "volume_trillions": round(v2, 2),
            }
        )
    return pd.DataFrame(rows)
