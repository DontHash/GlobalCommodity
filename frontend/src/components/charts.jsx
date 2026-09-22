import { lazy, Suspense } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  Treemap,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { compact, titleCase, yearLabel } from "../format";

const colors = ["#789fa8", "#a9dbc9", "#f56f5c", "#ef4f96", "#9caa91", "#b3a6c7", "#d0b58b", "#8fb7b2"];
const axis = { fontSize: 11, fill: "#8c9098" };
const grid = "#ebecea";
const MapPlot = lazy(() => import("./MapPlot"));
const xTickFormatter = (key) => String(key).toLowerCase().includes("year") ? yearLabel : undefined;

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return <div className="chart-tooltip"><div className="mb-1 font-semibold">{label}</div>{payload.map((item) => <div key={`${item.name}-${item.value}`}>{titleCase(item.name)}: {typeof item.value === "number" ? compact(item.value) : item.value}</div>)}</div>;
}

export function AreaTimeline({ data, x = "year", y, name = "Trade", currency = false }) {
  return <div className="chart-box"><ResponsiveContainer><AreaChart data={data} margin={{ top: 12, right: 12, left: 4, bottom: 0 }}><defs><linearGradient id={`fill-${y}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#789fa8" stopOpacity={0.62} /><stop offset="100%" stopColor="#789fa8" stopOpacity={0.10} /></linearGradient></defs><CartesianGrid stroke={grid} vertical={false} /><XAxis dataKey={x} tick={axis} axisLine={false} tickLine={false} tickFormatter={xTickFormatter(x)} /><YAxis tick={axis} axisLine={false} tickLine={false} tickFormatter={(value) => compact(value, currency)} width={55} /><Tooltip content={<ChartTooltip />} /><Area type="monotone" dataKey={y} name={name} stroke="#789fa8" fill={`url(#fill-${y})`} strokeWidth={1.6} dot={false} activeDot={{ r: 3 }} /></AreaChart></ResponsiveContainer></div>;
}

export function MultiArea({ data, keys, x = "year", stacked = false }) {
  return <div className="chart-box"><ResponsiveContainer><AreaChart data={data} margin={{ top: 12, right: 12, left: 4, bottom: 0 }}><CartesianGrid stroke={grid} vertical={false} /><XAxis dataKey={x} tick={axis} axisLine={false} tickLine={false} tickFormatter={xTickFormatter(x)} /><YAxis tick={axis} axisLine={false} tickLine={false} tickFormatter={compact} width={55} /><Tooltip content={<ChartTooltip />} /><Legend iconType="circle" iconSize={7} />{keys.map((key, index) => <Area key={key} type="monotone" dataKey={key} stackId={stacked ? "total" : undefined} stroke={colors[index % colors.length]} fill={colors[index % colors.length]} fillOpacity={stacked ? .52 : .32} strokeWidth={1.5} dot={false} activeDot={{ r: 3 }} />)}</AreaChart></ResponsiveContainer></div>;
}

export function MultiLine({ data, keys, x = "year", yKey = "value", seriesKey = "series", reference, legendLayout = "horizontal" }) {
  const normalized = seriesKey ? mergeSeries(data, x, seriesKey, yKey) : data;
  const vertical = legendLayout === "vertical";
  const chart = <ResponsiveContainer><LineChart data={normalized} margin={{ top: 12, right: 15, left: 4, bottom: 0 }}><CartesianGrid stroke={grid} vertical={false} /><XAxis dataKey={x} tick={axis} axisLine={false} tickLine={false} tickFormatter={xTickFormatter(x)} /><YAxis tick={axis} axisLine={false} tickLine={false} tickFormatter={compact} width={55} /><Tooltip content={<ChartTooltip />} />{!vertical && <Legend iconType="circle" iconSize={7} />}{reference !== undefined && <ReferenceLine y={reference} stroke="#a4a6ab" strokeDasharray="3 4" />}{keys.map((key, index) => <Line key={key} type="monotone" dataKey={key} stroke={colors[index % colors.length]} strokeWidth={1.8} dot={false} activeDot={{ r: 3 }} connectNulls />)}</LineChart></ResponsiveContainer>;
  if (!vertical) return <div className="chart-box">{chart}</div>;
  return <div className="chart-with-bottom-legend"><div className="chart-box">{chart}</div><div className="chart-legend-bottom" aria-label="Chart series">{keys.map((key, index) => <div className="chart-legend-item" key={key}><span style={{ background: colors[index % colors.length] }} />{key}</div>)}</div></div>;
}

function mergeSeries(rows, x, seriesKey, valueKey) {
  const merged = new Map();
  rows.forEach((row) => merged.set(row[x], { ...(merged.get(row[x]) || { [x]: row[x] }), [row[seriesKey]]: row[valueKey] }));
  return [...merged.values()].sort((a, b) => a[x] - b[x]);
}

export function BarView({ data, x, y, horizontal = false, signColors = false, accentIndex = -1 }) {
  const verticalLayout = horizontal ? "vertical" : "horizontal";
  const valueTick = (value) => `${compact(value)}${String(y).includes("pct") ? "%" : ""}`;
  return <div className="chart-box"><ResponsiveContainer><BarChart data={data} layout={verticalLayout} margin={{ top: 10, right: 16, left: horizontal ? 32 : 4, bottom: 6 }}><CartesianGrid stroke={grid} vertical={!horizontal} horizontal={horizontal} /><XAxis type={horizontal ? "number" : "category"} dataKey={horizontal ? undefined : x} tick={axis} axisLine={false} tickLine={false} tickFormatter={horizontal ? valueTick : xTickFormatter(x)} /><YAxis type={horizontal ? "category" : "number"} dataKey={horizontal ? x : undefined} tick={axis} axisLine={false} tickLine={false} width={horizontal ? 120 : 48} tickFormatter={horizontal ? (value) => String(value).slice(0, 19) : valueTick} /><Tooltip content={<ChartTooltip />} /><Bar dataKey={y} activeBar={{ fill: "#315f68", stroke: "#f8f7f5", strokeWidth: 1 }} radius={horizontal ? [0, 8, 8, 0] : [8, 8, 0, 0]}>{data.map((row, index) => <Cell key={index} fill={signColors ? (row[y] < 0 ? "#d94b4b" : "#169b62") : index === accentIndex ? "#f56f5c" : "#4f8892"} />)}</Bar></BarChart></ResponsiveContainer></div>;
}

export function ScatterView({ data, x, y, group = "cluster", name = "country_or_area" }) {
  const groups = [...new Set(data.map((row) => row[group]))];
  return <div className="chart-box"><ResponsiveContainer><ScatterChart margin={{ top: 12, right: 12, left: 2, bottom: 4 }}><CartesianGrid stroke={grid} /><XAxis type="number" dataKey={x} name={titleCase(x)} tick={axis} axisLine={false} tickLine={false} /><YAxis type="number" dataKey={y} name={titleCase(y)} tick={axis} axisLine={false} tickLine={false} /><ZAxis dataKey={name} name="Country" /><Tooltip cursor={{ strokeDasharray: "3 3" }} content={<ChartTooltip />} />{groups.map((value, index) => <Scatter key={value} name={`Cluster ${value}`} data={data.filter((row) => row[group] === value)} fill={colors[index % colors.length]} />)}</ScatterChart></ResponsiveContainer></div>;
}

function TreemapCell(props) {
  const { depth, x, y, width, height, index, name } = props;
  if (depth === 0) return null;
  const amount = props.size ?? props.value ?? props.payload?.size;
  const fontSize = Math.max(7, Math.min(13, width / 13, height / 4));
  return <g><rect x={x} y={y} width={width} height={height} rx={5} fill={colors[index % colors.length]} stroke="#f8f7f5" strokeWidth={2} /><foreignObject x={x + 5} y={y + 5} width={Math.max(0, width - 10)} height={Math.max(0, height - 10)}><div className="treemap-label" title={`${name}: ${compact(amount, true)}`} style={{ fontSize }}><span>{name}</span><strong>{compact(amount, true)}</strong></div></foreignObject></g>;
}

export function TreeMapView({ data }) {
  return <div className="chart-box treemap-box"><ResponsiveContainer><Treemap data={data.map((row) => ({ name: row.short_label || row.category, size: row.trade_usd }))} dataKey="size" nameKey="name" aspectRatio={4 / 3} content={<TreemapCell />}><Tooltip content={<ChartTooltip />} /></Treemap></ResponsiveContainer></div>;
}

export function WorldMap({ rows, metric }) {
  return <div className="h-[440px] w-full"><Suspense fallback={<div className="skeleton h-full w-full" />}><MapPlot rows={rows} metric={metric} /></Suspense></div>;
}

export function Heatmap({ columns = [], matrix = [] }) {
  if (!matrix.length) return null;
  return <div className="overflow-auto"><div className="grid min-w-[420px] gap-1" style={{ gridTemplateColumns: `110px repeat(${columns.length}, minmax(72px,1fr))` }}><div />{columns.map((column) => <div className="p-2 text-center text-[11px] text-[var(--muted)]" key={column}>{titleCase(column)}</div>)}{matrix.flatMap((row, r) => [<div className="p-2 text-[11px] text-[var(--muted)]" key={`label-${r}`}>{titleCase(columns[r])}</div>, ...row.map((value, c) => <div key={`${r}-${c}`} className="rounded-xl p-3 text-center text-xs" style={{ background: `rgba(120,159,168,${.12 + Math.abs(value) * .65})`, color: Math.abs(value) > .6 ? "#fff" : "#101524" }}>{value.toFixed(2)}</div>)])}</div></div>;
}
