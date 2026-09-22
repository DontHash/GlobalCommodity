import { useState } from "react";
import { ChevronDown, RefreshCw, Search, TrendingDown, TrendingUp, X } from "lucide-react";
import { compact, titleCase, yearLabel } from "../format";

const pageDescriptionHeadings = {
  "Executive summary": "Trade at a glance",
  "Trends over time": "The shape of change",
  Regions: "Trade across borders",
  "Country growth": "Growth stories by market",
  Products: "Inside the product mix",
  "Why did it change?": "What moved the numbers",
  "Data preview": "Explore the evidence",
  "Advanced models": "Patterns beneath the surface",
  "Case study": "The boom, break, and aftermath",
};

export function Card({ children, className = "" }) {
  return <section className={`card ${className}`}>{children}</section>;
}

export function PageIntro({ title, subtitle }) {
  const descriptionHeading = pageDescriptionHeadings[title];
  return <header><h1 className="page-heading">{title}</h1><section className="page-description">{descriptionHeading && <h2>{descriptionHeading}</h2>}<p>{subtitle}</p></section></header>;
}

export function Section({ title, hint, children }) {
  return (
    <section>
      <h2 className="section-heading">{title}</h2>
      {hint && <p className="section-hint">{hint}</p>}
      {children}
    </section>
  );
}

export function StatCard({ label, value, delta, direction = "neutral", context, colored = false }) {
  return (
    <Card className={colored ? `metric-tone metric-${direction}` : "white"}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value ?? "-"}</div>
      {delta && (
        <div className={`trend ${direction}`}>
          {direction === "up" ? <TrendingUp size={13} /> : direction === "down" ? <TrendingDown size={13} /> : null}
          {delta}
        </div>
      )}
      {context && <div className="metric-context">{context}</div>}
    </Card>
  );
}

export function Tabs({ items, active, onChange }) {
  return (
    <div className="tabs" role="tablist" aria-label="Analysis views">
      {items.map((item) => (
        <button key={item} className={`tab ${active === item ? "active" : ""}`} role="tab" aria-selected={active === item} onClick={() => onChange(item)}>
          {item}
        </button>
      ))}
    </div>
  );
}

export function Select({ label, value, onChange, children, className = "" }) {
  return (
    <label className={`control ${className}`}>
      <span>{label}</span>
      <select className="input" value={value ?? ""} onChange={(event) => onChange(event.target.value)}>{children}</select>
    </label>
  );
}

export function NumberInput({ label, value, onChange, min, max, step = 1 }) {
  return (
    <label className="control">
      <span>{label}</span>
      <input className="input" type="number" value={value ?? ""} min={min} max={max} step={step} onChange={(event) => onChange(Number(event.target.value))} />
    </label>
  );
}

export function MultiSelect({ label, options = [], value = [], onChange, dark = false, max, formatOption = titleCase, searchable = false }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const toggle = (option) => {
    if (value.includes(option)) onChange(value.filter((item) => item !== option));
    else if (!max || value.length < max) {
      onChange([...value, option]);
      if (searchable) setQuery("");
    }
  };
  const visible = options.filter((option) => formatOption(option).toLowerCase().includes(query.trim().toLowerCase()));
  if (searchable) return (
    <div className={`control ${dark ? "text-white" : ""}`}>
      <span>{label}</span>
      <div className="multi" onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}>
        <div className={`multi-search-field ${dark ? "sidebar-control" : "input"}`}>
          <Search size={14} />
          <input className="multi-search-input" type="search" value={query} onFocus={() => setOpen(true)} onChange={(event) => { setQuery(event.target.value); setOpen(true); }} placeholder={`Search ${label.toLowerCase()}`} aria-label={`Search ${label.toLowerCase()}`} />
          <span className="multi-count">{value.length || "All"}</span>
          <button type="button" aria-label={`Show ${label.toLowerCase()} options`} onMouseDown={(event) => event.preventDefault()} onClick={() => setOpen((current) => !current)}><ChevronDown size={14} /></button>
        </div>
        {value.length > 0 && <div className="multi-chips">{value.map((option) => <button type="button" key={option} title={`Remove ${formatOption(option)}`} onClick={() => toggle(option)}><span>{formatOption(option)}</span><X size={11} /></button>)}</div>}
        {open && <div className="multi-panel multi-results">
          {visible.length ? visible.map((option) => <button type="button" className={`multi-option ${value.includes(option) ? "selected" : ""}`} aria-pressed={value.includes(option)} key={option} onMouseDown={(event) => event.preventDefault()} onClick={() => toggle(option)}><span>{formatOption(option)}</span></button>) : <div className="multi-empty">No matching {label.toLowerCase()}</div>}
        </div>}
      </div>
    </div>
  );
  return (
    <div className={`control ${dark ? "text-white" : ""}`}>
      <span>{label}</span>
      <details className="multi">
        <summary className={dark ? "sidebar-control" : "input"}>
          <span>{value.length ? `${value.length} selected` : "All"}</span><ChevronDown size={14} />
        </summary>
        <div className="multi-panel">
          {visible.map((option) => (
            <button type="button" className={`multi-option ${value.includes(option) ? "selected" : ""}`} aria-pressed={value.includes(option)} key={option} onClick={() => toggle(option)}><span>{formatOption(option)}</span></button>
          ))}
        </div>
      </details>
    </div>
  );
}

export function Notice({ children, tone = "info" }) {
  return <div className={`notice ${tone}`}>{children}</div>;
}

export function RangeSlider({ label, min, max, from, to, onChange, dark = false }) {
  const span = Math.max(1, max - min);
  const left = ((from - min) / span) * 100;
  const right = 100 - ((to - min) / span) * 100;
  return (
    <div className={`range-control ${dark ? "dark" : ""}`}>
      <div className="range-values"><span>{label}</span><strong>{from} to {to}</strong></div>
      <div className="dual-range">
        <div className="dual-range-track" style={{ left: `${left}%`, right: `${right}%` }} />
        <input type="range" min={min} max={Math.max(min, to - 1)} value={from} aria-label={`${label} from year`} onChange={(event) => onChange(Number(event.target.value), to)} />
        <input type="range" min={Math.min(max, from + 1)} max={max} value={to} aria-label={`${label} to year`} onChange={(event) => onChange(from, Number(event.target.value))} />
      </div>
    </div>
  );
}

export function DataTable({ rows = [], columns, columnLabels = {}, empty = "No records match the current selection." }) {
  if (!rows.length) return <Notice>{empty}</Notice>;
  const keys = columns || Object.keys(rows[0]).filter((key) => key !== "category" || !("short_label" in rows[0]));
  return (
    <div className="data-wrap">
      <table className="data-table">
        <thead><tr>{keys.map((key) => <th key={key}>{columnLabels[key] || titleCase(key)}</th>)}</tr></thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>{keys.map((key) => <td key={key}>{formatCell(row[key], key)}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(value, key) {
  if (value === null || value === undefined) return "-";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") {
    if (key.toLowerCase().includes("year")) return yearLabel(value);
    if (key.includes("usd")) return compact(value, true);
    if (key.includes("pct") || key.includes("share")) return Number(value).toFixed(2);
    return compact(value);
  }
  return String(value).includes("_") ? titleCase(String(value)) : String(value);
}

function SkeletonTabs() {
  return <div className="tabs h-[52px]"><div className="skeleton h-9 w-28" /><div className="skeleton h-9 w-24" /><div className="skeleton h-9 w-32" /></div>;
}

function SkeletonControls({ count = 2 }) {
  return <div className="controls">{Array.from({ length: count }, (_, index) => <div className="skeleton h-11 w-40" key={index} />)}</div>;
}

function SkeletonMetrics() {
  return <div className="grid-4">{Array.from({ length: 4 }, (_, index) => <div className="card white" key={index}><div className="skeleton h-3 w-24" /><div className="skeleton mt-4 h-10 w-36" /><div className="skeleton mt-5 h-4 w-28" /></div>)}</div>;
}

function SkeletonChart({ tall = false }) {
  return <div className="card white"><div className="skeleton h-5 w-44" /><div className={`skeleton mt-5 w-full ${tall ? "h-[400px]" : "h-[280px]"}`} /></div>;
}

function SkeletonTable() {
  return <div className="card white"><div className="skeleton h-5 w-48" />{Array.from({ length: 5 }, (_, index) => <div className="skeleton mt-4 h-9 w-full" key={index} />)}</div>;
}

function SkeletonPanel({ children }) {
  return <div className="card white">{children}</div>;
}

export function PageSkeleton({ page = "overview" }) {
  let content;
  if (page === "overview") content = <><SkeletonControls count={1} /><SkeletonMetrics /><div className="grid gap-3"><div className="skeleton h-16 w-full" /><div className="skeleton h-16 w-full" /></div><SkeletonChart /><div className="grid-2"><SkeletonChart /><SkeletonChart /></div><SkeletonTable /></>;
  else if (page === "trends") content = <><SkeletonTabs /><SkeletonChart /></>;
  else if (page === "regions") content = <><SkeletonTabs /><SkeletonPanel><SkeletonControls /><div className="skeleton h-[440px] w-full" /></SkeletonPanel></>;
  else if (page === "growth") content = <><SkeletonTabs /><SkeletonPanel><SkeletonControls count={3} /><div className="grid-2"><div className="skeleton h-[260px] w-full" /><div className="skeleton h-[260px] w-full" /></div>{Array.from({ length: 4 }, (_, index) => <div className="skeleton mt-4 h-9 w-full" key={index} />)}</SkeletonPanel></>;
  else if (page === "products") content = <><SkeletonTabs /><SkeletonPanel><SkeletonControls count={1} /><div className="skeleton h-[360px] w-full" /></SkeletonPanel></>;
  else if (page === "why") content = <><SkeletonTabs /><SkeletonPanel><SkeletonControls /><div className="skeleton h-28 w-full" /><div className="grid-2 mt-6"><SkeletonTable /><SkeletonTable /></div></SkeletonPanel></>;
  else if (page === "preview") content = <SkeletonPanel><SkeletonControls count={3} />{Array.from({ length: 8 }, (_, index) => <div className="skeleton mt-3 h-9 w-full" key={index} />)}<div className="mt-5 flex justify-between"><div className="skeleton h-10 w-24" /><div className="skeleton h-10 w-24" /></div></SkeletonPanel>;
  else if (page === "models") content = <><SkeletonTabs /><SkeletonPanel><SkeletonControls count={1} /><div className="grid-2"><SkeletonTable /><SkeletonTable /></div></SkeletonPanel></>;
  else content = <><SkeletonMetrics /><SkeletonTable /><SkeletonChart /><div className="grid-2"><SkeletonTable /><SkeletonTable /></div></>;
  return <div className={`page-stack skeleton-page skeleton-${page}`} aria-label={`Loading ${page} page`} aria-busy="true">{content}</div>;
}

export function ErrorState({ error, retry }) {
  return <div className="page-stack"><Notice tone="error"><strong>Unable to load trade data.</strong><div className="mt-1">{error}</div><button className="button mt-4" onClick={retry}><RefreshCw size={14} className="inline mr-2" />Retry</button></Notice></div>;
}

export function ScopeFooter({ scope }) {
  if (!scope) return null;
  return <footer className="footer-note">Source: {scope.source} · Indexed: {scope.indexed} · Preset: {scope.preset} · Period: {scope.period?.join(" to ")} · Scope: {scope.profile?.rows ? compact(scope.profile.rows) : "aggregated"} records, {scope.profile?.countries || 0} countries</footer>;
}
