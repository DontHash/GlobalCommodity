# Global Commodity Trade Analytics

Streamlit dashboard for exploring UN Comtrade commodity trade data (1988–2016).

## Setup

```bash
pip install -r requirements.txt
```

Place the dataset at:

```
CSV Dataset/commodity_trade_statistics_data.csv
```

The app auto-caches a parquet file under `outputs/` on first load.

## Run

```bash
streamlit run app.py
```

## Sections

| Page | Purpose |
|------|---------|
| Executive summary | KPIs and alerts |
| Trends | Time series |
| Regions | Country map, rankings, balance |
| Products | Commodity breakdown |
| Why it changed | Root-cause drivers |
| Export data | Raw explorer |
| Advanced models | Anomalies, forecasting, clustering |
| Case study | Narrative shock events |

## Data note

The source CSV (~1.2 GB) is **not** included in this repository. Download it separately and place it in `CSV Dataset/`.
