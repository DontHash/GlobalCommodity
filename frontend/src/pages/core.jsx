import { useState } from "react";
import { useApi } from "../hooks";
import { AreaTimeline, BarView, MultiArea, MultiLine, TRADE_COLORS, WorldMap } from "../components/charts";
import { Card, DataDisclosure, DataTable, ErrorState, MultiSelect, NoData, Notice, PageIntro, PageSkeleton, ScopeFooter, Section, Select, StatCard, Tabs } from "../components/ui";

function ContentState({ state, page, children }) {
  if (!state.data && state.loading) return <PageSkeleton page={page} />;
  if (state.error) return <ErrorState error={state.error} retry={state.retry} />;
  return children;
}

export function OverviewPage({ filters, onResetFilters, onSelectCountry }) {
  const [params, setParams] = useState({});
  const state = useApi("/api/overview", filters, params);
  const data = state.data;
  const resetPage = () => { setParams({}); onResetFilters(); };
  return <><PageIntro title="Executive summary" subtitle="A current trade snapshot covering year-over-year and period growth, net trade balance, product mix, active alerts, long-run movement, leading countries and products, and the category and country changes behind the selected period." scope={data?.scope} /><ContentState state={state} page="overview">{data && <div className="page-stack">
    {!data.years.length ? <NoData onReset={resetPage} /> : <>
      <div className="controls"><Select label="Focus year for KPIs and alerts" value={data.focus_year} onChange={(value) => setParams((p) => ({ ...p, focus_year: Number(value) }))}>{data.years.map((year) => <option key={year}>{year}</option>)}</Select></div>
      <Section title="Trade direction"><div className="grid-4">{data.kpis.map((kpi) => <StatCard key={kpi.label} {...kpi} direction={kpi.delta_direction} colored loading={state.loading} />)}</div></Section>
      <Section title="Current alerts"><div className="grid gap-3">{data.alerts.length ? data.alerts.map((item, index) => <Notice key={index} tone={item.level === "critical" ? "error" : item.level === "positive" ? "success" : item.level}><strong>{item.title}</strong><div>{item.detail}</div></Notice>) : <Notice tone="success">No critical exceptions in the current selection.</Notice>}</div></Section>
      <Card className="white chart-card" title="Trade over time"><AreaTimeline data={data.yearly} y="trade_trillions" name="Trade" currency scale={1e12} loading={state.loading} onReset={resetPage} /><DataDisclosure rows={data.yearly} columns={["year","trade_trillions","yoy_pct"]} /></Card>
      <div className="grid-2 chart-grid"><Card className="white chart-card" title="Leading countries"><BarView data={[...data.top_countries].reverse()} x="country_or_area" y="trade_billions" horizontal currency scale={1e9} loading={state.loading} onReset={resetPage} onSelectCountry={onSelectCountry} /><DataDisclosure rows={data.top_countries} columns={["rank","country_or_area","trade_usd","share_pct","yoy_pct"]} /></Card><Card className="white chart-card" title="Leading product categories"><BarView data={[...data.top_categories].reverse()} x="short_label" y="trade_billions" horizontal currency scale={1e9} loading={state.loading} onReset={resetPage} /><DataDisclosure rows={data.top_categories} columns={["short_label","trade_usd"]} /></Card></div>
      <Section title="Drivers of change"><Card className="white">{data.drivers ? <><StatCard label="Total trade change" value={`${data.drivers.total_change_pct >= 0 ? "+" : ""}${data.drivers.total_change_pct?.toFixed(1)}%`} context={`${data.compare_from} to ${data.compare_to}`} direction={data.drivers.total_change_pct >= 0 ? "up" : "down"} loading={state.loading} /><div className="mt-6 grid-2"><DriverTable title="Countries that gained the most" rows={data.drivers.top_country_gains} columns={["country","change_billions","change_pct"]} /><DriverTable title="Countries that lost the most" rows={data.drivers.top_country_declines} columns={["country","change_billions","change_pct"]} /><DriverTable title="Largest category gains" rows={data.drivers.top_category_gains} columns={["category","change_billions","change_pct"]} category /><DriverTable title="Largest category declines" rows={data.drivers.top_category_declines} columns={["category","change_billions","change_pct"]} category /></div></> : <Notice tone="warning">Choose a sidebar range containing at least two years.</Notice>}</Card></Section>
    </>}
    <ScopeFooter scope={data.scope} />
  </div>}</ContentState></>;
}

function DriverTable({ title, rows, columns, category = false }) { return <div><h3 className="mb-3 text-sm font-semibold">{title}</h3><DataTable rows={rows} columns={columns} columnLabels={category ? { category: "Category", change_billions: "Changes_Billions (USD)", change_pct: "Change %" } : { country: "Country", change_billions: "Changes_Billions (USD)", change_pct: "YoY pct change" }} /></div>; }

export function TrendsPage({ filters, onResetFilters }) {
  const [tab, setTab] = useState("Volume");
  const state = useApi("/api/trends", filters);
  const data = state.data;
  const flowKeys = data?.flows?.length ? Object.keys(data.flows[0]).filter((key) => key !== "year") : [];
  return <><PageIntro title="Trends over time" subtitle="Shows trade value, year-over-year growth, and import, export, and re-export flows across the selected period so you can identify direction, contractions, and changes in composition." scope={data?.scope} /><ContentState state={state} page="trends">{data && <div className="page-stack"><Tabs items={["Volume", "Growth", "Flows"]} active={tab} onChange={setTab} />
    {tab === "Volume" && <Card className="white chart-card" title="Global trade volume"><AreaTimeline data={data.yearly} y="trade_trillions" name="Trade" currency scale={1e12} loading={state.loading} onReset={onResetFilters} /><DataDisclosure rows={data.yearly} columns={["year","trade_trillions","yoy_pct"]} /></Card>}
    {tab === "Growth" && <Card className="white chart-card" title="Year-over-year growth"><BarView data={data.yearly.filter((row) => row.yoy_pct !== null)} x="year" y="yoy_pct" signColors percent loading={state.loading} onReset={onResetFilters} /><DataTable rows={data.yearly} columns={["year", "trade_trillions", "yoy_pct"]} /></Card>}
    {tab === "Flows" && <Card className="white chart-card" title="Trade flows"><MultiArea data={data.flows} keys={flowKeys} stacked currency scale={1e12} loading={state.loading} onReset={onResetFilters} /><DataDisclosure rows={data.flows} /></Card>}
    <ScopeFooter scope={data.scope} /></div>}</ContentState></>;
}

export function RegionsPage({ filters, onResetFilters, onSelectCountry }) {
  const [tab, setTab] = useState("World map");
  const [params, setParams] = useState({});
  const state = useApi("/api/regions", filters, params);
  const data = state.data;
  const patch = (key, value) => setParams((previous) => ({ ...previous, [key]: value }));
  const resetPage = () => { setParams({}); onResetFilters(); };
  return <><PageIntro title="Regions" subtitle="Compares country trade on a world map, ranks markets, shows trade surpluses and deficits, and plots selected countries over time." scope={data?.scope} /><ContentState state={state} page="regions">{data && <div className="page-stack"><Tabs items={["World map", "Rankings", "Trade balance", "Compare"]} active={tab} onChange={setTab} />
    {tab === "World map" && <Card className="white chart-card" title="Country trade map"><div className="controls"><Select label="Map year" value={data.map_year} onChange={(value) => patch("map_year", Number(value))}>{data.years.map((year) => <option key={year}>{year}</option>)}</Select><Select label="Color by" value={data.map_metric} onChange={(value) => patch("map_metric", value)}><option value="total_trade">Total trade</option><option value="trade_balance">Export minus import balance</option><option value="exports">Exports</option><option value="imports">Imports</option></Select></div><WorldMap rows={data.map} metric={data.map_metric} loading={state.loading} onReset={resetPage} onSelectCountry={onSelectCountry} /><DataDisclosure rows={data.map} columns={["country_or_area","value","trade_usd","rank","share_pct","yoy_pct"]} />{data.unmapped > 0 && <p className="section-hint">{data.unmapped} aggregate or historical reporting areas are omitted.</p>}</Card>}
    {tab === "Rankings" && <Card className="white chart-card" title="Country rankings"><div className="controls"><Select label="Flow" value={params.rank_flow || "All"} onChange={(value) => patch("rank_flow", value)}><option>All</option><option>Import</option><option>Export</option></Select><Select label="Top N" value={params.top_n || 15} onChange={(value) => patch("top_n", Number(value))}>{[5,10,15,20,25,30].map((n) => <option key={n}>{n}</option>)}</Select></div><BarView data={[...data.ranking].reverse()} x="country_or_area" y="trade_billions" horizontal currency scale={1e9} color={(params.rank_flow || "All") === "Export" ? TRADE_COLORS.export : (params.rank_flow || "All") === "Import" ? TRADE_COLORS.import : TRADE_COLORS.neutral} loading={state.loading} onReset={resetPage} onSelectCountry={onSelectCountry} /><DataDisclosure rows={data.ranking} columns={["rank","country_or_area","trade_usd","share_pct","yoy_pct"]} /></Card>}
    {tab === "Trade balance" && <div className="grid-2 chart-grid"><Card className="white chart-card" title="Largest surpluses"><BarView data={data.surplus} x="country_or_area" y="balance_billions" horizontal signColors currency scale={1e9} loading={state.loading} onReset={resetPage} onSelectCountry={onSelectCountry} /><DataDisclosure rows={data.surplus} columns={["country_or_area","balance_usd"]} /></Card><Card className="white chart-card" title="Largest deficits"><BarView data={data.deficit} x="country_or_area" y="balance_billions" horizontal signColors currency scale={1e9} loading={state.loading} onReset={resetPage} onSelectCountry={onSelectCountry} /><DataDisclosure rows={data.deficit} columns={["country_or_area","balance_usd"]} /></Card></div>}
    {tab === "Compare" && <Card className="white chart-card" title="Country comparison"><div className="controls"><MultiSelect label="Countries" options={data.country_options} value={data.compare_countries} onChange={(value) => patch("compare_countries", value)} max={5} /></div>{data.comparison.length ? <><MultiLine data={data.comparison} keys={data.compare_countries} yKey="trade_billions" seriesKey="country_or_area" currency scale={1e9} loading={state.loading} onReset={resetPage} onSelectCountry={onSelectCountry} /><DataDisclosure rows={data.comparison} columns={["year","country_or_area","trade_usd","yoy_pct"]} /></> : <NoData onReset={resetPage} />}</Card>}
    <ScopeFooter scope={data.scope} /></div>}</ContentState></>;
}

export { ContentState };
