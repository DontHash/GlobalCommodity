# Country Growth Dynamics — Analysis Spec

> Checkpoint saved before building this section. Use this doc to scope the next feature.

## Goal

Add a **Country Growth Dynamics** section that classifies countries by *how* their trade evolved—not just *how much*—and links each growth pattern to shifts in exported goods, volumes, and other measurable drivers so we can explain *why* a country behaved the way it did.

## Growth archetypes

| Archetype | Definition | Signals |
|-----------|------------|---------|
| **Fast & sustained** | High CAGR over the window with low volatility | High mean YoY, low YoY std dev |
| **Sudden shock** | Large single-year jump or drop | YoY z-score > threshold, or change-point detected |
| **Slow & steady** | Moderate positive growth, low volatility | CAGR in middle quartile, low YoY std dev |
| **Stagnant / declining** | Flat or negative trend | Negative or near-zero CAGR |
| **Volatile / boom–bust** | High average growth but large swings | High YoY std dev, multiple sign reversals |

Countries are scored on **export value** (primary) and optionally **export weight (kg)** to separate price-driven vs volume-driven growth.

## Driver decomposition (link growth → cause)

For each country (or cluster), decompose total export change between period A and B into:

1. **Commodity mix** — which HS categories gained/lost share (composition effect)
2. **Within-category volume** — did kg shipped rise or fall?
3. **Within-category price** — did unit price (USD/kg) shift?
4. **Flow mix** — export vs re-export share
5. **Partner concentration** — optional if partner data is available

Present as a waterfall or ranked driver table: *"Country X grew +42% — 28pp from mineral fuels volume, 9pp from machinery value, −5pp from agricultural decline."*

## Other factors to surface

- **Global shock alignment** — did the country move with 2008–09, 2014–15 commodity slowdown, or diverge?
- **Oil / commodity dependence** — regression residual vs oil-heavy basket (extend existing oil model to country level)
- **Trade balance shift** — export-led vs import-led growth
- **Peer cluster** — reuse shock clustering (`country_shock_clusters_from_cyf`) to group similar responders
- **Underperformance vs median** — flag countries below global/regional median YoY in focus years

## UI sketch

New tab under **Regions** (or standalone page **⑧ Growth dynamics**):

1. **Archetype map / table** — filter by archetype, sort by CAGR or shock magnitude
2. **Country drill-down** — time series + YoY bars + change-point markers
3. **Driver panel** — top commodity/volume/price contributors for selected period
4. **Compare archetypes** — side-by-side commodity mix for "fast" vs "sudden" vs "slow"

## Existing code to reuse

- `view.country_year_flow`, `view.category_shock_delta` — country & category deltas
- `root_cause_drivers()` — period driver framework
- `country_shock_clusters_from_cyf()` — multi-shock clustering
- `change_points()`, `detect_yoy_anomalies()` — sudden-change detection
- `weight_kg`, `unit_price_per_kg` in raw loader — volume vs price split

## Acceptance criteria

- [ ] Every country assigned a primary growth archetype for a user-selected window
- [ ] Drill-down shows top 5 commodity/volume/price drivers for that country's change
- [ ] Sudden shocks flagged with year and magnitude
- [ ] Archetype filter works on map and comparison charts
