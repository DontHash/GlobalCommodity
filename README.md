# Global Commodity Trade Analytics

React and FastAPI dashboard for exploring UN Comtrade commodity trade data (1988-2016). Python remains responsible for loading, filtering, aggregation, and analytics; React handles the user interface.

## Architecture

```text
UN Comtrade CSV
  -> Python validation, cached cubes, and analytics
  -> FastAPI JSON endpoints
  -> React + Tailwind CSS + Recharts
```

The supported application is React + FastAPI only. The retired Streamlit renderer and its Python UI/chart modules have been removed.

## Setup

```bash
python -m pip install -r requirements.txt
cd frontend
npm install
```

Place the dataset at `CSV Dataset/commodity_trade_statistics_data.csv`. Python creates validated Parquet and analytical cube caches under `outputs/`.

## Development

Run the API from the repository root:

```bash
python -m uvicorn app:app --reload --port 8000
```

Run React in another terminal:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`. Development CORS defaults to that origin and can be changed with `CORS_ORIGINS`.

## Production-style local run

```bash
cd frontend
npm run build
cd ..
python -m uvicorn app:app --port 8000
```

FastAPI serves the compiled React application at `http://localhost:8000`.

## Sections

| Page | Purpose |
|------|---------|
| Executive summary | KPIs, alerts, trends, rankings, and root-cause summary |
| Trends | Volume, year-over-year growth, and flow composition |
| Regions | Country map, rankings, balance, and comparison |
| Country growth | Growth profiles, product diversification, drivers, and targets |
| Products | Category breakdown, trends, and commodity search |
| Why it changed | Root-cause drivers, period comparison, and underperformers |
| Data preview | Deterministic, paginated preview and CSV download |
| Advanced models | Anomalies, forecasting, clustering, correlation, and oil association |
| Case study | Narrative shock events and counterfactual analysis |

## Verification

```bash
python -m unittest discover -s tests -v
cd frontend
npm run build
```

Detailed methodology and implementation notes are in [`improvement.md`](improvement.md).

## Data note

The source CSV (about 1.2 GB) is not included in this repository. Download it separately and place it in `CSV Dataset/`.

For deployment, build the validated Parquet dataset and analytical cubes once:

```powershell
python scripts/prepare_data_artifacts.py
```

Production reads those artifacts from object storage through `DATA_BASE_URL`. Normal dashboard requests download only the compact analytical cubes; the detailed Parquet file is fetched lazily for data preview, commodity drill-down, and correlation.

## Vercel deployment

The application uses two existing Vercel projects, one for the API and one for the dashboard. They are currently deployed from the local checkout but are **not yet connected to GitHub**.

### Backend

- Root Directory: repository root (`.`)
- Framework: FastAPI (automatic detection through `app.py`)
- Environment variables:

```text
DATA_BASE_URL=https://bhvquuvpxslxofra.public.blob.vercel-storage.com/global-commodity/v2
CORS_ORIGINS=https://YOUR-FRONTEND.vercel.app
```

### Frontend

- Root Directory: `frontend`
- Framework: Vite
- Build Command: `npm run build`
- Output Directory: `dist`
- `frontend/vercel.json` proxies `/api/*` to the backend's stable URL, so no frontend environment variable or preview-specific CORS entry is needed. Update that destination if the backend project is moved.

Upload refreshed data after changing the source CSV with `powershell -ExecutionPolicy Bypass -File scripts/upload_data_artifacts.ps1`; the CLI reads the connected Blob-store token from the ignored `.env.local`. Do not commit the CSV, generated Parquet files, or credentials. Set a new `DATA_BASE_URL` version prefix when publishing a revised dataset so warm functions do not keep cached older artifacts.

This GitHub repository belongs to a personal account. Vercel requires its owner—not a GitHub collaborator—to connect it for automatic Git-based deployments. The owner can join your Vercel team and connect the repository to these projects, or import it into their own Vercel account. A fork under your own GitHub account is another option for Git-connected projects you control.

Until Git is connected, the linked checkout can make preview deployments with `vercel deploy --scope notjustauser` from the repository root for the API, or from `frontend/` for the dashboard. A GitHub push is not yet an automatic Vercel deployment.

## About The Project

The project was done as a part of coursework for COMP482, KU-DOCSE(IV/I)
