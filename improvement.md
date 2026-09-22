# Implemented Project Improvements

This document records the implemented improvement groups in the dashboard, how the relevant code worked before, how it works now, and why each change matters. The implementation reuses the existing dataframes and analytics functions while keeping one supported React + FastAPI application path.

## 1. Consistent filters

### Previous pattern

The sidebar exposed country, category, flow, year, and aggregate-row filters, but some summaries were produced from different pre-aggregated tables. A country or category choice could therefore affect one chart while another chart still represented the wider dataset.

### Implemented pattern

`frontend/src/components/Sidebar.jsx::Filters()` owns one filter object, and `frontend/src/api.js::queryString()` sends that same scope to every endpoint. `src/api.py::request_context()` validates it once and creates a `FilteredView`; `build_filtered_view()` and `_build_filtered_view_from_cubes()` then apply it to every cube. Category-filtered country totals are rebuilt from detailed category data so every total describes the same selected basket. API responses include `scope_payload()`, which the React page header and footer disclose to the user.

Relevant files and functions:

- `frontend/src/components/Sidebar.jsx::Filters`
- `frontend/src/api.js::queryString`
- `src/api.py::request_context`, `scope_payload`
- `src/data/context.py::_filter_cube_frame`, `build_filtered_view`, `_build_filtered_view_from_cubes`
- `src/data/cubes.py::_build_cubes_from_df`

### Impact and learning value

Every page now answers a question about the same population. This prevents misleading comparisons and demonstrates an important analytics principle: define the population once, propagate it through every denominator and aggregation, and clearly label conditional results.

## 2. Small data-quality gate

### Previous pattern

The loader converted a few columns and cached the source, but malformed schemas, unsupported flows, invalid years, negative trade values, or stale cached output could reach later calculations.

### Implemented pattern

`src/data/validation.py::validate_trade_data()` performs inexpensive schema and domain checks during source ingestion. It checks required columns, numeric conversion, missing key values, supported flows, non-negative trade values, and plausible years. `source_fingerprint()`, `save_data_quality_report()`, and `report_matches_source()` tie the validation report and Parquet cache to the source file size and modification time. `src/data/loader.py::_read_source_dataframe()` stops with a useful error when the gate fails. `src/data/cubes.py` also rebuilds derived cubes when the source changes.

Relevant files and functions:

- `src/data/validation.py::validate_trade_data`, `source_fingerprint`, `save_data_quality_report`, `report_matches_source`
- `src/data/loader.py::_read_source_dataframe`
- `src/data/cubes.py::_cube_cache_is_current`, `load_trade_cubes`
- `config.py` for the quality-report path

### Impact and learning value

Failures now occur at the data boundary, close to their cause, rather than as incorrect charts. This teaches schema validation, cache invalidation, data contracts, and why a small deterministic gate is often more valuable than complicated downstream error handling.

## 3. Trade diversification model

### Economic and mathematical model

For country `c`, year `t`, flow `f`, and detailed product category `i`, let trade value be `x_i` and define its basket share as:

`s_i = x_i / sum(x_i)`

The Herfindahl-Hirschman Index is `HHI = sum(s_i^2)`. It approaches 1 when one category dominates and becomes smaller as trade is distributed more evenly. The effective number of categories is `1 / HHI`: the number of equal-sized categories that would produce the observed concentration. With `N` observed positive categories, normalized concentration is `(HHI - 1/N) / (1 - 1/N)`, and the displayed diversification score is `1 - normalized_HHI`.

The model also reports top-one and top-three shares, observed category count, detailed-basket value, and coverage relative to the canonical aggregate total. Aggregate `all_commodities` rows are excluded from category shares because including a total alongside its components would double count trade. Import and export baskets are calculated separately.

### Implemented pattern

`src/analytics/concentration.py::_category_shares()` builds the positive detailed-category shares. `concentration_by_year()` computes the panel of metrics; `category_contributions()` explains which categories contribute to HHI. `src/api.py::growth()` exposes the model results, and `frontend/src/pages/growth.jsx::Diversification()` renders the interactive country/year/flow analysis, time series, rankings, and coverage warnings.

When the sidebar selects only part of the product basket, shares are renormalized within that selection and the UI labels the result as conditional. The model is descriptive: value shares can change through prices as well as quantities, and product concentration alone does not measure partner diversification or prove resilience.

Relevant files and functions:

- `src/analytics/concentration.py::_category_shares`, `concentration_by_year`, `category_contributions`
- `src/api.py::growth`
- `frontend/src/pages/growth.jsx::Diversification`
- `frontend/src/components/charts.jsx::MultiLine`

### Impact and learning value

The project gains an interpretable economic structure model rather than another opaque prediction. Implementing it builds skills in weighted shares, concentration indices, normalization, denominator choice, coverage diagnostics, and translating mathematical output into cautious policy interpretation.

## 4. Statistically honest model results

### Previous pattern

The advanced models returned outputs with little evidence about reliability. ARIMA accepted only three training points and reported no validation error or uncertainty. The Random Forest used the current year's total trade to predict the current year's growth, which leaked contemporaneous information. K-means tried values of `k` that could be invalid for small samples. The oil regression predicted total trade using oil trade even though oil was part of that total. A module-wide warning filter hid all model warnings. The country trend displayed only in-sample R-squared.

### Implemented pattern

- `detect_yoy_anomalies()` safely returns no anomalies for fewer than three or non-varying observations.
- `isolation_forest_years()` requires at least eight observations and a varying feature.
- `change_points()` rejects short, mismatched, or non-finite series.
- `arima_forecast()` requires ten training years, performs rolling one-step validation, reports MAE/MAPE and last-value naive MAE, and returns a 95% model interval. Warnings are captured only around the fit rather than globally suppressed.
- `rf_yoy_surprise()` replaces current total trade with lagged total trade, requires eight training observations, and compares its MAE with a last-growth-rate baseline.
- `country_shock_clusters_from_cyf()` limits `k` to the number of available distinct observations and returns a controlled empty result when clustering is not meaningful.
- `oil_regression_from_cyf()` predicts non-oil trade (`total - oil`) and labels the result as an association, not a causal estimate.
- `regression_forecast()` performs rolling-origin validation, reports MAE/MAPE and naive MAE, and supplies an approximate 95% log-residual interval. The UI calls it a trend scenario and warns when it does not beat the baseline.

Diagnostics are attached to existing dataframe results through `DataFrame.attrs` and to the existing `ForecastResult` object. This preserves the established function contracts with minimal caller changes.

Relevant files and functions:

- `src/analytics/mining.py` model functions listed above
- `src/analytics/forecast.py::ForecastResult`, `regression_forecast`
- `src/api.py::models`, `growth`
- `frontend/src/pages/other.jsx::ModelsPage`, `ModelDiagnostics`
- `frontend/src/pages/growth.jsx::TargetPlanner`

### Impact and learning value

Users can distinguish fit from predictive evidence, see uncertainty, and compare complex models with a simple baseline. This develops practical skills in leakage prevention, time-ordered validation, baseline selection, uncertainty communication, minimum sample rules, and the difference between association and causation.

The intervals are model-based diagnostics, not guaranteed real-world confidence bounds. More sophisticated calibration should be added only if forecast decisions require it.

## 5. Unambiguous preview download

### Previous pattern

The page was titled “Export data” and the button said “Download CSV,” but `load_filtered_sample()` returned only the first requested rows in source-file order. This could be mistaken for a full filtered export and could change if source row order changed.

### Implemented pattern

The page and controls now explicitly say “Data preview,” “Preview rows,” and “Download preview CSV.” `src/data/loader.py::load_filtered_sample()` draws a bounded seeded-random candidate pool, then interleaves representatives for distinct countries, years, commodities, and categories before filling the remaining preview slots. `src/api.py::trades()` paginates that reproducible preview and `trade_export()` exports only the disclosed preview rows. The React page states that the preview is incomplete, and an empty column selection produces a useful warning instead of an ambiguous download.

Relevant files and functions:

- `src/data/loader.py::load_filtered_sample`
- `src/api.py::trades`, `trade_export`
- `frontend/src/pages/other.jsx::PreviewPage`

### Impact and learning value

The interface now matches the actual data contract and preview results are reproducible without being biased toward the first source rows. This demonstrates honest product wording, seeded sampling, deliberate dimensional coverage, and guarding user-controlled selections.

A streaming full export was intentionally not added: loading and serializing the full filtered 1.2 GB source needs a separate resource and delivery design. It should be added only when full-export use cases justify that cost.

## 6. Consolidated aggregation logic

### Previous pattern

`FilteredView` and `src/processing/aggregate.py` independently implemented the same group-by operations for flow totals, country rankings, country/year trajectories, balances, and category totals. A future bug fix or label change therefore had to be repeated.

### Implemented pattern

The existing functions in `src/processing/aggregate.py` remain the single aggregation implementations. Their optional parameters were widened only where needed: `country_rankings()` and `category_totals()` accept `top_n=None`, while `country_year_matrix()` accepts optional country and flow filters. `FilteredView` delegates to those functions and trims helper-only columns where necessary to preserve its existing return shape. Category labels now consistently use `src/utils/labels.py::category_label()`.

Relevant files and functions:

- `src/processing/aggregate.py::flow_by_year`, `country_rankings`, `trade_balance_by_country`, `category_totals`, `category_by_year`, `country_year_matrix`
- `src/data/context.py::FilteredView.flow_by_year`, `country_totals`, `country_year`, `trade_balance`, `category_totals`, `category_by_year`
- `src/utils/labels.py::category_label`

### Impact and learning value

One correction now reaches every caller, reducing drift without adding an abstraction layer. This is a useful refactoring lesson: consolidate at an existing pure-function boundary, preserve public outputs, and avoid rewriting unrelated code.

## Verification

The regression checks live in:

- `tests/test_data_pipeline.py` for canonical totals, filter propagation, and the quality gate
- `tests/test_concentration.py` for HHI mathematics, scale invariance, duplicates, and contributions
- `tests/test_model_reliability.py` for forecast validation/intervals, safe anomaly behavior, and Random Forest leakage prevention

Run all checks with:

```bash
python -m unittest discover -s tests -v
```

The analytical improvements add no analytical dependencies and preserve the existing Python calculation contracts.

## 7. React and FastAPI frontend migration

### Previous pattern

`app.py` and the files under `src/ui/` used Streamlit for navigation, controls, rendering, and caching. Analytics were mostly separated into `src/analytics/`, `src/data/`, and `src/processing/`, but a browser could reach them only through Streamlit reruns.

### Implemented pattern

`app.py` is now the FastAPI production entry point and `src/api.py` exposes filtered, page-specific JSON responses. Cache decorators in `src/data/loader.py`, `src/data/cubes.py`, and `src/data/context.py` use bounded `functools.lru_cache`, removing Streamlit from the data path. After feature parity was verified, the retired Streamlit entry point and `src/ui/` and `src/viz/` modules were removed.

The React application lives under `frontend/` and preserves all nine original sections, shared filters, tabs, KPI arrangements, charts, tables, model controls, preview pagination, and CSV download. `frontend/src/api.js` is the single API client. Reusable UI and chart components live in `frontend/src/components/`, while page components live in `frontend/src/pages/`.

The visual system follows the supplied references: warm gray workspace, navy navigation, soft rounded surfaces, minimal borders, coral accents, restrained green/red change semantics, and muted teal/blue-gray charts. Time-series charts use smooth curves and translucent fills where the data meaning supports them. Other visualizations retain their original semantic form. Initial loads and filter refreshes use component-shaped skeletons; empty and error states do not invent fallback data.

Relevant files:

- `app.py`, `src/api.py`
- `frontend/src/App.jsx`, `frontend/src/api.js`, `frontend/src/index.css`
- `frontend/src/components/Sidebar.jsx`, `ui.jsx`, `charts.jsx`, `MapPlot.jsx`
- `frontend/src/pages/core.jsx`, `growth.jsx`, `other.jsx`
- `requirements.txt`, `frontend/package.json`, `frontend/vite.config.js`

### Impact and learning value

Python remains the analytical source of truth, while the frontend can evolve independently through a documented API contract. This builds practical skills in separating presentation from business logic, designing filtered APIs for large datasets, preserving information architecture during migration, responsive React component design, accessibility, loading and error states, and performance-aware code splitting.

## 8. Runtime cleanup and bundle reduction

The codebase now has one supported UI path. The unused Streamlit entry point, Python UI/chart modules, compatibility helpers, formatting helpers, UI-only constants, and the unused runtime `matplotlib` dependency were removed. Exploratory notebooks remain available, but their optional plotting packages are no longer installed with the web application.

The Regions map now uses a small SVG choropleth instead of the Plotly browser bundle, and page groups load only when opened. This reduces installation size, browser parsing work, and initial JavaScript transfer while preserving the existing map and all API contracts.

## 9. Dashboard reliability and clarity fixes

- Trade balance uses zero when a country has only exports or only imports, eliminating null map values and the Regions blank-page crash. The SVG map also normalizes numeric values defensively.
- All shared bar charts use a higher-contrast teal fill and explicit dark hover fill, so bars remain visible under the tooltip cursor.
- `category_label()` is the single category-name formatter. It expands truncated source labels and replaces archaic “thereof” names with complete plain-language names in filters, charts, and driver results.
- Advanced model actions track loading independently, so ARIMA and Random Forest can run concurrently and keep both outputs visible.
- The `Exclude aggregate bucket` setting controls category buckets only. Checked hides `category == "all_commodities"` from product breakdowns; unchecked shows it. Country totals, KPIs, rankings, and maps always retain the authoritative country totals (with detailed-row fallback when the source has no aggregate total).
- The Executive summary now uses descriptive copy and unnumbered section titles. All four direction cards use green, red, or neutral gradients based on their computed direction instead of a fixed first-card color.

## 10. Category, comparison, filter, year, and preview refinements

Category names now pass through a complete backend catalog covering all 97 chapters present in the dataset and a defensive frontend formatter. Sidebar choices keep the two-digit HS code while showing readable names such as `74 Copper and copper products` and `88 Aircraft, spacecraft and parts`. Truncations and source terms such as “thereof,” “nes,” and “etc” are no longer exposed. The same formatter is reused by product-category controls.

The sidebar now owns one accessible dual-handle year-range controller. Executive Summary drivers automatically compare the first and last years in that shared range and retain the requested 2×2 reading order: country gains, country losses, category gains, then category declines. Category tables explicitly show Category, Change in USD (billions), and YoY pct. Shared chart and table formatting renders year fields as plain four-digit text without thousands separators.

Country and category controls are searchable directly in their visible fields, with matching options opening below on a pale blue-gray surface that remains legible against the navy sidebar. `load_filtered_sample()` now takes a standard seeded random sample from every matching source row. This removes both source-order bias and the artificial ordering introduced by forced dimension interleaving; the seed keeps pagination and downloads reproducible.

Relevant files and functions:

- `src/utils/labels.py::category_label`
- `src/data/loader.py::load_filtered_sample`, `_random_sample`
- `frontend/src/format.js::categoryOptionLabel`, `yearLabel`
- `frontend/src/components/ui.jsx::MultiSelect`, `RangeSlider`, `DataTable`
- `frontend/src/components/charts.jsx` shared x-axis formatters
- `frontend/src/components/Sidebar.jsx::Filters`
- `frontend/src/pages/core.jsx::OverviewPage`, `DriverTable`
- `frontend/src/pages/other.jsx::ProductsPage`, `PreviewPage`

These changes improve trust and usability: labels retain analytical HS context, comparison periods take less space, drivers have a predictable layout and unit contract, years no longer look like quantities, long filter lists are practical, and previews cover more of the selected data. The implementation reuses shared boundaries and native range/search inputs, so it adds no frontend dependency.

## 11. Sidebar, loading-state, and product-chart refinement

The desktop sidebar is now 380 pixels wide so country and category controls do not feel compressed. Its expanded surface uses `#8E8A7A`, its active-page highlight uses `#AEB8C2`, and its controls and dropdown menus use coordinated lighter neutral surfaces with dark accessible text. Its globe is the desktop collapse controller: the expanded state keeps the existing coral-pink mark, while the collapsed state leaves only the same-position white button with a dark outline. The sidebar surface is removed in the collapsed state, so the control does not shift or sit inside a residual colored rail. Mobile navigation still opens as a full drawer.

`PageSkeleton` now receives the active page and renders the corresponding default structure: summary metrics for Executive Summary, chart tabs for Trends, a map surface for Regions, chart-and-table profiles for Country Growth, a treemap for Products, driver tables for Why It Changed, a preview table and pager for Data Preview, diagnostic tables for Advanced Models, and the KPI/event/chart sequence for the Case Study.

The Products treemap uses custom cells that display the complete category name and compact trade value within each rectangle. Product Trends uses a vertically stacked, left-aligned color legend below the plot, keeping the graph unobstructed while longer commodity names remain easy to scan.

Relevant files:

- `frontend/src/App.jsx`
- `frontend/src/components/Sidebar.jsx`, `ui.jsx`, `charts.jsx`
- `frontend/src/pages/core.jsx`, `growth.jsx`, `other.jsx`
- `frontend/src/index.css`

- `src/data/context.py`, `src/data/loader.py`, `src/api.py`

## 12. Category language, aggregate scope, and driver tables

All HS chapter labels now use concise display names while retaining the original two-digit HS code in category selectors. Legalistic or filler wording such as “thereof,” “articles,” “miscellaneous,” and “related parts” is removed from displayed category names. The backend remains the authoritative label source, and frontend fallbacks also strip legacy source wording.

The aggregate checkbox now affects product-category buckets only. Country totals and every downstream country view—including Regions maps—use the same authoritative country totals whether the checkbox is checked or unchecked. Category filters still intentionally create a selected-category total.

Driver comparisons now use the union of countries and categories present in the start and end years, so newly appearing and disappearing entities are included. Country gain/loss tables include percentage change, category change tables use consistent headings, missing values display as `-`, and Country Growth defaults to USA, China, and Germany when available.

## 13. Page guidance, navigation polish, and numeric clarity

Regions comparison now uses the same preferred defaults as Country Growth: USA, China, and Germany when those countries are available. The shared `PageIntro` component replaces the redundant scope pills with a full-width explanation card on every page, while `ScopeFooter` keeps the detailed source and filter context available without competing with the page heading.

The expanded sidebar is rounded on every corner and uses `#94A8A8`, with `#507D7C` controls and white control text. Native CSS scrollbars use narrow rounded tracks and `#135454` thumbs across the application, with a translucent teal track that blends into each surface. Search fields no longer receive the large blue focus halo; button and navigation focus indicators remain visible for keyboard users.

The shared numeric formatter does not abbreviate thousands, so values such as `1200` remain `1200`; values of one million or more retain the familiar `M`, `B`, and `T` suffixes. Each full-width description card uses a distinct guide heading, and its body copy and section guidance use larger type for easier reading. Country Growth's diversification explanation documents `HHI = Σ share²`, its interpretation, and its role in assessing product concentration and shock exposure; both diversification plots use unitless y-axes.

Relevant files and functions:

- `src/api.py::regions`, `default_countries`
- `src/analytics/kpis.py::_fmt_billions`
- `frontend/src/format.js::compact`
- `frontend/src/components/ui.jsx::PageIntro`, `DataTable`, `ScopeFooter`
- `frontend/src/pages/core.jsx`, `growth.jsx`, `other.jsx`
- `frontend/src/index.css`

## 14. Description headings, persistent multi-selects, and case-study metadata

Page description cards now use concise, page-specific headings rather than repeating the page title or a generic phrase. Sidebar multi-select options are accessible buttons without checkboxes; choosing an item keeps the list open so several countries or categories can be selected in one pass. The dropdown uses a `#698282` surface, larger option text, and a rounded `#AEB8C2` selected and hover state.

The Case Study peak event is defined as 2013 to 2014 and calculates its change and ending volume from those two years when available. Every footer now reports the fixed indexed date `2026-06-17` and omits the redundant total-basis sentence.

## 15. Deployment-ready Parquet data and Vercel projects

The 1.15 GB source CSV is validated locally and converted into one 124 MB detailed Parquet file plus five analytical cube files. `scripts/prepare_data_artifacts.py` creates those files and a SHA-256 manifest; `scripts/upload_data_artifacts.ps1` uploads the files to Vercel Blob. The CSV, Parquet files, and credentials remain outside Git. All six uploaded object lengths match the local manifest.

At runtime `DATA_BASE_URL` selects versioned object-storage artifacts. `src/data/artifacts.py::ensure_artifact` downloads each file atomically into a temporary cache. `src/data/cubes.py::load_trade_cubes` loads only the five small cubes for standard pages; `src/data/loader.py::_sample_parquet` scans the detailed file in filtered batches for preview, export, and correlation, retaining a deterministic random sample instead of loading eight million rows into memory. Commodity drill-down also uses the same lazy Parquet source. Local CSV development remains supported.

The FastAPI Vercel project uses Python 3.12 and `app.py`. The Vite project uses `frontend/` as its root and `frontend/vercel.json` to proxy `/api/*` to the backend, avoiding cross-origin settings for preview domains. The repository belongs to another person's personal GitHub account, so Vercel's Git integration requires action from that owner; the current projects were deployed from the local checkout and are not connected to GitHub. See `README.md` for the setup and handoff.
