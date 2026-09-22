# Global Commodity Trade Analytics

Global Commodity Trade Analytics is an interactive dashboard for exploring international commodity trade data from 1988 to 2016. It helps users compare countries, study imports and exports, investigate growth and trade balance, understand product concentration, and run supporting analytical models.

## Live website

The deployed dashboard is available at [global-commodity-dashboard.vercel.app](https://global-commodity-dashboard.vercel.app).


## What the dashboard offers

- Executive trade summary with trends, rankings, gains, and declines.
- Regional comparison, country trade balance, and map-based exploration.
- Country growth profiles, product diversification, and change drivers.
- Product-level breakdowns, category trends, and commodity search.
- A representative data preview and CSV export.
- Advanced analysis including forecasting, anomalies, clustering, correlation, and concentration measures.

## Technology

The project has a React frontend and a Python FastAPI backend.

```text
Trade data / Parquet artifacts
        ↓
Python data processing and analytics
        ↓
FastAPI endpoints
        ↓
React dashboard
```

React is responsible for the interface, charts, filters, and page navigation. Python is responsible for data loading, validation, aggregation, analytics, and API responses.

## Run locally

### Prerequisites

- Python 3.12 or later
- Node.js 20 or later
- npm

### 1. Install dependencies

From the repository root:

```powershell
python -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

### 2. Configure data access

For the deployed Parquet data, set these variables in the terminal that will run the backend:

```powershell
$env:DATA_BASE_URL = "https://bhvquuvpxslxofra.public.blob.vercel-storage.com/global-commodity/v2"
$env:CORS_ORIGINS = "http://localhost:5173"
```

Alternatively, place the original CSV at:

```text
CSV Dataset/commodity_trade_statistics_data.csv
```

The CSV is intentionally excluded from Git because it is large. When it is present, the backend can build and use local cached artifacts in `outputs/`.

### 3. Start the backend

Run this from the repository root:

```powershell
python -m uvicorn app:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

### 4. Start the frontend

Open a second terminal and run:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

## Verify the project

Run the backend tests:

```powershell
python -m unittest discover -s tests -v
```

Build the frontend for production:

```powershell
cd frontend
npm run build
```

## Deployment notes

The application is deployed as two Vercel projects:

- `global-commodity-api` for the FastAPI backend.
- `global-commodity-dashboard` for the Vite/React frontend.

Production data is stored outside the repository as versioned Parquet artifacts. The backend uses `DATA_BASE_URL` to retrieve compact analytical cubes for normal dashboard requests and reads the detailed data lazily for previews and product-level analysis.

Do not commit the original CSV, generated Parquet files, local environment files, build output, or object-storage credentials. The repository `.gitignore` already excludes them.

## About The Project

The project was done as a part of coursework for COMP482, KU-DOCSE(IV/I)
