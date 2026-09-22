import { useState } from "react";
import { useApi } from "../hooks";
import { AreaTimeline, BarView, MultiArea, MultiLine, WorldMap } from "../components/charts";
import { Card, DataTable, ErrorState, MultiSelect, Notice, PageIntro, PageSkeleton, ScopeFooter, Section, Select, StatCard, Tabs } from "../components/ui";

function ContentState({ state, page, children }) {
  if (!state.data && state.loading) return <PageSkeleton page={page} />;
  if (state.error) return <ErrorState error={state.error} retry={state.retry} />;
  return <div className={state.loading ? "loading-dim" : ""}>{children}</div>;
}

export function OverviewPage({ filters }) {
  const [params, setParams] = useState({});
  const state = useApi("/api/overview", filters, params);
  const data = state.data;
  return <><PageIntro title="Executive summary" subtitle="A current trade snapshot covering year-over-year and period growth, net trade balance, product mix, active alerts, long-run movement, leading countries and products, and the category and country changes behind the selected period." scope={data?.scope} /><ContentState state={state} page="overview">{data && <div className="page-stack">
    {!data.years.length ? <Notice>No trade records match the selected filters.</Notice> : <>
      <div className="controls"><Select label="Focus year for KPIs and alerts" value={data.focus_year} onChange={(value) => setParams((p) => ({ ...p, focus_year: Number(value) }))}>{data.years.map((year) => <option key={year}>{year}</option>)}</Select></div>
      <Section title="Trade direction"><div className="grid-4">{data.kpis.map((kpi) => <StatCard key={kpi.label} {...kpi} direction={kpi.delta_direction} colored />)}</div></Section>
      <Section title="Current alerts"><div className="grid gap-3">{data.alerts.length ? data.alerts.map((item, index) => <Notice key={index} tone={item.level === "critical" ? "error" : item.level === "positive" ? "success" : item.level}><strong>{item.title}</strong><div>{item.detail}</div></Notice>) : <Notice tone="success">No critical exceptions in the current selection.</Notice>}</div></Section>
      <Section title="Trade over time"><Card className="white"><AreaTimeline data={data.yearly} y="trade_trillions" name="Trade (USD trillions)" /></Card></Section>
      <div className="grid-2"><Section title="Leading countries"><Card className="white"><BarView data={[...data.top_countries].reverse()} x="country_or_area" y="trade_billions" horizontal /></Card></Section><Section title="Leading product categories"><Card className="white"><BarView data={[...data.top_categories].reverse()} x="short_label" y="trade_billions" horizontal /></Card></Section></div>
      <Section title="Drivers of change"><Card className="white">{data.drivers ? <><StatCard label="Total trade change" value={`${data.drivers.total_change_pct >= 0 ? "+" : ""}${data.drivers.total_change_pct?.toFixed(1)}%`} context={`${data.compare_from} to ${data.compare_to}`} direction={data.drivers.total_change_pct >= 0 ? "up" : "down"} /><div className="mt-6 grid-2"><DriverTable title="Countries that gained the most" rows={data.drivers.top_country_gains} columns={["country","change_billions","change_pct"]} /><DriverTable title="Countries that lost the most" rows={data.drivers.top_country_declines} columns={["country","change_billions","change_pct"]} /><DriverTable title="Largest category gains" rows={data.drivers.top_category_gains} columns={["category","change_billions","change_pct"]} category /><DriverTable title="Largest category declines" rows={data.drivers.top_category_declines} columns={["category","change_billions","change_pct"]} category /></div></> : <Notice tone="warning">Choose a sidebar range containing at least two years.</Notice>}</Card></Section>
    </>}
    <ScopeFooter scope={data.scope} />
  </div>}</ContentState></>;
}

function DriverTable({ title, rows, columns, category = false }) { return <div><h3 className="mb-3 text-sm font-semibold">{title}</h3><DataTable rows={rows} columns={columns} columnLabels={category ? { category: "Category", change_billions: "Changes_Billions (USD)", change_pct: "Change %" } : { country: "Country", change_billions: "Changes_Billions (USD)", change_pct: "YoY pct change" }} /></div>; }

export function TrendsPage({ filters }) {
  const [tab, setTab] = useState("Volume");
  const state = useApi("/api/trends", filters);
  const data = state.data;
  const flowKeys = data?.flows?.length ? Object.keys(data.flows[0]).filter((key) => key !== "year") : [];
  return <><PageIntro title="Trends over time" subtitle="Shows trade value, year-over-year growth, and import, export, and re-export flows across the selected period so you can identify direction, contractions, and changes in composition." scope={data?.scope} /><ContentState state={state} page="trends">{data && <div className="page-stack"><Tabs items={["Volume", "Growth", "Flows"]} active={tab} onChange={setTab} />
    {tab === "Volume" && <Card className="white"><AreaTimeline data={data.yearly} y="trade_trillions" name="Trade (USD trillions)" /></Card>}
    {tab === "Growth" && <Card className="white"><BarView data={data.yearly.filter((row) => row.yoy_pct !== null)} x="year" y="yoy_pct" signColors /><DataTable rows={data.yearly} columns={["year", "trade_trillions", "yoy_pct"]} /></Card>}
    {tab === "Flows" && <Card className="white"><MultiArea data={data.flows} keys={flowKeys} stacked /></Card>}
    <ScopeFooter scope={data.scope} /></div>}</ContentState></>;
}

export function RegionsPage({ filters }) {
  const [tab, setTab] = useState("World map");
  const [params, setParams] = useState({});
  const state = useApi("/api/regions", filters, params);
  const data = state.data;
  const patch = (key, value) => setParams((previous) => ({ ...previous, [key]: value }));
  return <><PageIntro title="Regions" subtitle="Compares country trade on a world map, ranks markets, shows trade surpluses and deficits, and plots selected countries over time." scope={data?.scope} /><ContentState state={state} page="regions">{data && <div className="page-stack"><Tabs items={["World map", "Rankings", "Trade balance", "Compare"]} active={tab} onChange={setTab} />
    {tab === "World map" && <Card className="white"><div className="controls"><Select label="Map year" value={data.map_year} onChange={(value) => patch("map_year", Number(value))}>{data.years.map((year) => <option key={year}>{year}</option>)}</Select><Select label="Color by" value={data.map_metric} onChange={(value) => patch("map_metric", value)}><option value="total_trade">Total trade</option><option value="trade_balance">Export minus import balance</option><option value="exports">Exports</option><option value="imports">Imports</option></Select></div><WorldMap rows={data.map} metric={data.map_metric} />{data.unmapped > 0 && <p className="section-hint">{data.unmapped} aggregate or non-ISO territories are omitted.</p>}</Card>}
    {tab === "Rankings" && <Card className="white"><div className="controls"><Select label="Flow" value={params.rank_flow || "All"} onChange={(value) => patch("rank_flow", value)}><option>All</option><option>Import</option><option>Export</option></Select><Select label="Top N" value={params.top_n || 15} onChange={(value) => patch("top_n", Number(value))}>{[5,10,15,20,25,30].map((n) => <option key={n}>{n}</option>)}</Select></div><BarView data={[...data.ranking].reverse()} x="country_or_area" y="trade_billions" horizontal /></Card>}
    {tab === "Trade balance" && <div className="grid-2"><Card className="white"><h2 className="section-heading">Largest surpluses</h2><BarView data={data.surplus} x="country_or_area" y="balance_billions" horizontal /></Card><Card className="white"><h2 className="section-heading">Largest deficits</h2><BarView data={data.deficit} x="country_or_area" y="balance_billions" horizontal signColors /></Card></div>}
    {tab === "Compare" && <Card className="white"><div className="controls"><MultiSelect label="Countries" options={data.country_options} value={data.compare_countries} onChange={(value) => patch("compare_countries", value)} max={5} /></div>{data.comparison.length ? <MultiLine data={data.comparison} keys={data.compare_countries} yKey="trade_billions" seriesKey="country_or_area" /> : <Notice>Select at least one country.</Notice>}</Card>}
    <ScopeFooter scope={data.scope} /></div>}</ContentState></>;
}

export { ContentState };
