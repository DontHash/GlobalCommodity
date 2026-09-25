import { lazy, Suspense, useEffect, useState } from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart,
  ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, Treemap,
  XAxis, YAxis, ZAxis,
} from "recharts";
import { hasPlottableData, toggleSeries, truncateLabel } from "../chartState";
import { compact, exactCurrency, scaledCurrency, titleCase, yearLabel } from "../format";
import { NoData } from "./ui";

const colors = ["#789fa8", "#a9dbc9", "#f56f5c", "#ef4f96", "#9caa91", "#b3a6c7", "#d0b58b", "#8fb7b2"];
export const TRADE_COLORS = {
  export: "#4f8892", reExport: "#8fb7b2", import: "#f56f5c", reImport: "#f2a296",
  neutral: "#789fa8", positive: "#169b62", negative: "#d94b4b",
};
const axis = { fontSize: 11, fill: "#8c9098" };
const grid = "#ebecea";
const animation = { isAnimationActive: true, animationDuration: 280, animationEasing: "ease-out" };
const MapPlot = lazy(() => import("./MapPlot"));
const xTickFormatter = (key) => String(key).toLowerCase().includes("year") ? yearLabel : undefined;
const seriesColor = (key, index) => ({ Export: TRADE_COLORS.export, "Re-Export": TRADE_COLORS.reExport, Import: TRADE_COLORS.import, "Re-Import": TRADE_COLORS.reImport }[key] || colors[index % colors.length]);

function PlotFrame({ children, loading = false, className = "chart-box" }) {
  return <div className={`${className} ${loading ? "chart-updating" : ""}`} aria-busy={loading}>{children}{loading && <ChartUpdateSkeleton />}</div>;
}

function ChartUpdateSkeleton() {
  return <div className="chart-update-skeleton" role="status" aria-label="Updating chart"><span /><span /><span /><span /></div>;
}

function useVisibleSeries(keys) {
  const signature = keys.join("\u0001");
  const [visible, setVisible] = useState(keys);
  useEffect(() => setVisible(keys), [signature]);
  return [visible, (key) => setVisible((current) => toggleSeries(current, key, keys))];
}

function ChartTooltip({ active, payload, label, currency = false, scale = 1, percent = false }) {
  if (!active || !payload?.length) return null;
  return <div className="chart-tooltip"><div className="chart-tooltip-label">{label}</div>{payload.filter((item) => item.value !== null && item.value !== undefined).map((item) => {
    const row = item.payload?.__meta?.[item.name] || item.payload || {};
    const entity = row.country_or_area || row.country;
    const value = percent ? `${compact(item.value)}%` : currency ? scaledCurrency(item.value, scale) : compact(item.value);
    const details = [entity || titleCase(item.name), row.rank ? `Rank #${row.rank}` : null, value, Number.isFinite(row.share_pct) ? `${row.share_pct.toFixed(1)}% of selected trade` : null, Number.isFinite(row.yoy_pct) ? `${row.yoy_pct > 0 ? "+" : ""}${row.yoy_pct.toFixed(1)}% YoY` : null].filter(Boolean);
    const exact = currency ? row.trade_usd ?? row.balance_usd ?? (scale === 1 ? item.value : null) : null;
    return <div className="chart-tooltip-entry" key={`${item.name}-${item.value}`}><div>{details.join(" • ")}</div>{exact !== null && <div className="chart-tooltip-exact">Exact: {exactCurrency(exact)}</div>}</div>;
  })}</div>;
}

export function AreaTimeline({ data = [], x = "year", y, name = "Trade", currency = false, scale = 1, color = TRADE_COLORS.neutral, loading = false, onReset }) {
  if (!hasPlottableData(data, [y])) return <NoData onReset={onReset} />;
  return <PlotFrame loading={loading}><ResponsiveContainer><AreaChart data={data} margin={{ top: 12, right: 12, left: 4, bottom: 0 }}><defs><linearGradient id={`fill-${y}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity={0.62} /><stop offset="100%" stopColor={color} stopOpacity={0.10} /></linearGradient></defs><CartesianGrid stroke={grid} vertical={false} /><XAxis dataKey={x} tick={axis} axisLine={false} tickLine={false} tickFormatter={xTickFormatter(x)} /><YAxis tick={axis} axisLine={false} tickLine={false} tickFormatter={(value) => currency ? scaledCurrency(value, scale) : compact(value)} width={64} /><Tooltip content={<ChartTooltip currency={currency} scale={scale} />} /><Area {...animation} type="monotone" dataKey={y} name={name} stroke={color} fill={`url(#fill-${y})`} strokeWidth={1.6} dot={false} activeDot={{ r: 4 }} /></AreaChart></ResponsiveContainer></PlotFrame>;
}

export function MultiArea({ data = [], keys = [], x = "year", stacked = false, currency = false, scale = 1, loading = false, onReset }) {
  const [visible, toggle] = useVisibleSeries(keys);
  if (!hasPlottableData(data, keys)) return <NoData onReset={onReset} />;
  return <div className="chart-with-bottom-legend"><PlotFrame loading={loading}><ResponsiveContainer><AreaChart data={data} margin={{ top: 12, right: 12, left: 4, bottom: 0 }}><CartesianGrid stroke={grid} vertical={false} /><XAxis dataKey={x} tick={axis} axisLine={false} tickLine={false} tickFormatter={xTickFormatter(x)} /><YAxis tick={axis} axisLine={false} tickLine={false} tickFormatter={(value) => currency ? scaledCurrency(value, scale) : compact(value)} width={64} /><Tooltip content={<ChartTooltip currency={currency} scale={scale} />}/>{keys.filter((key) => visible.includes(key)).map((key) => <Area {...animation} key={key} type="monotone" dataKey={key} stackId={stacked ? "total" : undefined} stroke={seriesColor(key, keys.indexOf(key))} fill={seriesColor(key, keys.indexOf(key))} fillOpacity={stacked ? .52 : .32} strokeWidth={1.5} dot={false} activeDot={{ r: 4 }} />)}</AreaChart></ResponsiveContainer></PlotFrame><ChartLegend keys={keys} visible={visible} onToggle={toggle} /></div>;
}

export function MultiLine({ data = [], keys = [], x = "year", yKey = "value", seriesKey = "series", reference, currency = false, scale = 1, loading = false, onReset, onSelectCountry }) {
  const normalized = seriesKey ? mergeSeries(data, x, seriesKey, yKey) : data;
  const [visible, toggle] = useVisibleSeries(keys);
  if (!hasPlottableData(normalized, keys)) return <NoData onReset={onReset} />;
  return <div className="chart-with-bottom-legend"><PlotFrame loading={loading}><ResponsiveContainer><LineChart data={normalized} margin={{ top: 12, right: 15, left: 4, bottom: 0 }}><CartesianGrid stroke={grid} vertical={false} /><XAxis dataKey={x} tick={axis} axisLine={false} tickLine={false} tickFormatter={xTickFormatter(x)} /><YAxis tick={axis} axisLine={false} tickLine={false} tickFormatter={(value) => currency ? scaledCurrency(value, scale) : compact(value)} width={64} /><Tooltip content={<ChartTooltip currency={currency} scale={scale} />}/>{reference !== undefined && <ReferenceLine y={reference} stroke="#a4a6ab" strokeDasharray="3 4" />}{keys.filter((key) => visible.includes(key)).map((key) => <Line {...animation} key={key} type="monotone" dataKey={key} stroke={seriesColor(key, keys.indexOf(key))} strokeWidth={1.8} dot={false} activeDot={{ r: 4, onClick: () => onSelectCountry?.(key) }} connectNulls={false} className={onSelectCountry ? "country-mark" : undefined} role={onSelectCountry ? "button" : undefined} tabIndex={onSelectCountry ? 0 : undefined} aria-label={onSelectCountry ? `Filter dashboard to ${key}` : undefined} onClick={() => onSelectCountry?.(key)} onKeyDown={(event) => { if (onSelectCountry && (event.key === "Enter" || event.key === " ")) onSelectCountry(key); }} />)}</LineChart></ResponsiveContainer></PlotFrame><ChartLegend keys={keys} visible={visible} onToggle={toggle} /></div>;
}

function mergeSeries(rows, x, seriesKey, valueKey) {
  const merged = new Map();
  rows.forEach((row) => {
    const current = merged.get(row[x]) || { [x]: row[x], __meta: {} };
    current[row[seriesKey]] = row[valueKey];
    current.__meta[row[seriesKey]] = row;
    merged.set(row[x], current);
  });
  return [...merged.values()].sort((a, b) => a[x] - b[x]);
}

function ChartLegend({ keys, visible, onToggle }) {
  return <div className="chart-legend-bottom" aria-label="Chart series">{keys.map((key, index) => <button type="button" className={`chart-legend-item ${visible.includes(key) ? "" : "muted"}`} aria-pressed={visible.includes(key)} key={key} onClick={() => onToggle(key)}><span style={{ background: seriesColor(key, index) }} />{titleCase(key)}</button>)}</div>;
}

export function BarView({ data = [], x, y, horizontal = false, signColors = false, accentIndex = -1, color = TRADE_COLORS.neutral, currency = false, scale = 1, percent = false, loading = false, onReset, onSelectCountry }) {
  if (!hasPlottableData(data, [y])) return <NoData onReset={onReset} />;
  const verticalLayout = horizontal ? "vertical" : "horizontal";
  const valueTick = (value) => percent || String(y).includes("pct") ? `${compact(value)}%` : currency ? scaledCurrency(value, scale) : compact(value);
  return <PlotFrame loading={loading}><ResponsiveContainer><BarChart data={data} layout={verticalLayout} margin={{ top: 10, right: 16, left: horizontal ? 24 : 4, bottom: 6 }}><CartesianGrid stroke={grid} vertical={!horizontal} horizontal={horizontal} /><XAxis type={horizontal ? "number" : "category"} dataKey={horizontal ? undefined : x} tick={axis} axisLine={false} tickLine={false} tickFormatter={horizontal ? valueTick : xTickFormatter(x)} /><YAxis type={horizontal ? "category" : "number"} dataKey={horizontal ? x : undefined} tick={axis} axisLine={false} tickLine={false} width={horizontal ? 112 : 56} tickFormatter={horizontal ? truncateLabel : valueTick} /><Tooltip content={<ChartTooltip currency={currency} scale={scale} percent={percent || String(y).includes("pct")} />} /><Bar {...animation} dataKey={y} activeBar={{ fill: "#315f68", stroke: "#f8f7f5", strokeWidth: 1 }} radius={horizontal ? [0, 8, 8, 0] : [8, 8, 0, 0]}>{data.map((row, index) => {
    const country = row.country_or_area || row.country;
    const select = country && onSelectCountry ? () => onSelectCountry(country) : undefined;
    return <Cell key={index} fill={signColors ? (row[y] < 0 ? TRADE_COLORS.negative : TRADE_COLORS.positive) : index === accentIndex ? "#f56f5c" : color} className={select ? "country-mark" : undefined} role={select ? "button" : undefined} tabIndex={select ? 0 : undefined} aria-label={select ? `Filter dashboard to ${country}` : undefined} onClick={select} onKeyDown={(event) => { if (select && (event.key === "Enter" || event.key === " ")) select(); }} />;
  })}</Bar></BarChart></ResponsiveContainer></PlotFrame>;
}

function CountryDot({ cx, cy, fill, payload, onSelectCountry, nameKey }) {
  const country = payload?.[nameKey];
  const select = country && onSelectCountry ? () => onSelectCountry(country) : undefined;
  return <circle cx={cx} cy={cy} r={5} fill={fill} className={select ? "country-mark" : undefined} role={select ? "button" : undefined} tabIndex={select ? 0 : undefined} aria-label={select ? `Filter dashboard to ${country}` : undefined} onClick={select} onKeyDown={(event) => { if (select && (event.key === "Enter" || event.key === " ")) select(); }} />;
}

export function ScatterView({ data = [], x, y, group = "cluster", name = "country_or_area", loading = false, onReset, onSelectCountry }) {
  if (!hasPlottableData(data, [x, y])) return <NoData onReset={onReset} />;
  const groups = [...new Set(data.map((row) => row[group]))];
  return <PlotFrame loading={loading}><ResponsiveContainer><ScatterChart margin={{ top: 12, right: 12, left: 2, bottom: 4 }}><CartesianGrid stroke={grid} /><XAxis type="number" dataKey={x} name={titleCase(x)} tick={axis} axisLine={false} tickLine={false} /><YAxis type="number" dataKey={y} name={titleCase(y)} tick={axis} axisLine={false} tickLine={false} /><ZAxis dataKey={name} name="Country" /><Tooltip cursor={{ strokeDasharray: "3 3" }} content={<ChartTooltip />} />{groups.map((value, index) => <Scatter {...animation} key={value} name={`Cluster ${value}`} data={data.filter((row) => row[group] === value)} fill={colors[index % colors.length]} shape={(props) => <CountryDot {...props} onSelectCountry={onSelectCountry} nameKey={name} />} />)}</ScatterChart></ResponsiveContainer></PlotFrame>;
}

function TreemapCell(props) {
  const { depth, x, y, width, height, index, name } = props;
  if (depth === 0) return null;
  const amount = props.size ?? props.value ?? props.payload?.size;
  const fontSize = Math.max(7, Math.min(13, width / 13, height / 4));
  return <g><rect x={x} y={y} width={width} height={height} rx={5} fill={colors[index % colors.length]} stroke="#f8f7f5" strokeWidth={2} /><foreignObject x={x + 5} y={y + 5} width={Math.max(0, width - 10)} height={Math.max(0, height - 10)}><div className="treemap-label" title={`${name}: ${compact(amount, true)}`} style={{ fontSize }}><span>{name}</span><strong>{compact(amount, true)}</strong></div></foreignObject></g>;
}

export function TreeMapView({ data = [], loading = false, onReset }) {
  if (!hasPlottableData(data, ["trade_usd"])) return <NoData onReset={onReset} />;
  return <PlotFrame loading={loading} className="chart-box treemap-box"><ResponsiveContainer><Treemap {...animation} data={data.map((row) => ({ name: row.short_label || row.category, size: row.trade_usd }))} dataKey="size" nameKey="name" aspectRatio={4 / 3} content={<TreemapCell />}><Tooltip content={<ChartTooltip currency />} /></Treemap></ResponsiveContainer></PlotFrame>;
}

export function WorldMap({ rows = [], metric, loading = false, onReset, onSelectCountry }) {
  if (!hasPlottableData(rows, ["value"])) return <NoData onReset={onReset} />;
  return <PlotFrame loading={loading} className="map-box"><Suspense fallback={<div className="skeleton h-full w-full" />}><MapPlot rows={rows} metric={metric} onSelectCountry={onSelectCountry} /></Suspense></PlotFrame>;
}

export function Heatmap({ columns = [], matrix = [], onReset, loading = false }) {
  if (!matrix.length) return <NoData onReset={onReset} />;
  return <div className={`heatmap-frame ${loading ? "chart-updating" : ""}`} aria-busy={loading}><div className="overflow-auto"><div className="grid min-w-[420px] gap-1" style={{ gridTemplateColumns: `110px repeat(${columns.length}, minmax(72px,1fr))` }}><div />{columns.map((column) => <div className="p-2 text-center text-[11px] text-[var(--muted)]" key={column}>{titleCase(column)}</div>)}{matrix.flatMap((row, r) => [<div className="p-2 text-[11px] text-[var(--muted)]" key={`label-${r}`}>{titleCase(columns[r])}</div>, ...row.map((value, c) => <div key={`${r}-${c}`} className="rounded-xl p-3 text-center text-xs" style={{ background: `rgba(120,159,168,${.12 + Math.abs(value) * .65})`, color: Math.abs(value) > .6 ? "#fff" : "#101524" }}>{value.toFixed(2)}</div>)])}</div></div>{loading && <ChartUpdateSkeleton />}</div>;
}
