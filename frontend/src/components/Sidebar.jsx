import {
  Activity,
  BarChart3,
  Boxes,
  BrainCircuit,
  ChartNoAxesCombined,
  Download,
  Globe2,
  LayoutDashboard,
  Map,
  Menu,
  SearchCode,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { useEffect, useRef } from "react";
import { categoryOptionLabel } from "../format";
import { MultiSelect, RangeSlider } from "./ui";

export const pages = [
  ["overview", "Executive summary", LayoutDashboard],
  ["trends", "Trends", Activity],
  ["regions", "Regions", Map],
  ["growth", "Country growth", ChartNoAxesCombined],
  ["products", "Products", Boxes],
  ["why", "Why it changed", SearchCode],
  ["preview", "Data preview", Download],
  ["models", "Advanced models", BrainCircuit],
  ["story", "Case study", BarChart3],
];

function Filters({ options, filters, onChange }) {
  if (!options) return <div className="skeleton h-48 w-full" />;
  const set = (key, value) => onChange({ ...filters, [key]: value, ...(key.startsWith("year_") ? { preset: "Custom" } : {}) });
  const setPreset = (label) => {
    const preset = options.presets.find((item) => item.label === label);
    onChange({ ...filters, preset: label, ...(preset?.range ? { year_from: preset.range[0], year_to: preset.range[1] } : {}) });
  };
  const setYears = (year_from, year_to) => onChange({ ...filters, year_from, year_to, preset: "Custom" });
  return (
    <>
      <div className="sidebar-label">Period</div>
      <label className="control text-white">
        <span>Quick range</span>
        <select className="sidebar-control" value={filters.preset} onChange={(event) => setPreset(event.target.value)}>
          {options.presets.map((item) => <option key={item.label}>{item.label}</option>)}
        </select>
      </label>
      <div className="mt-4"><RangeSlider dark label="Year range" min={options.year_min} max={options.year_max} from={filters.year_from} to={filters.year_to} onChange={setYears} /></div>
      <div className="sidebar-label">Scope</div>
      <label className="mb-2 flex items-start gap-2 px-1 text-[12px] leading-4 text-[#20221f]" title="Hides the all_commodities category bucket; country totals stay unchanged.">
        <input className="mt-0.5" type="checkbox" checked={filters.exclude_aggregate} onChange={(event) => set("exclude_aggregate", event.target.checked)} />
        <span>Exclude aggregate bucket</span>
      </label>
      <p className="mb-3 px-1 text-[11px] leading-4 text-[#222420]">Hides the all-commodities category bucket. Country totals and maps do not change.</p>
      <MultiSelect dark searchable label="Countries" options={options.countries} value={filters.countries} onChange={(value) => set("countries", value)} />
      <div className="mt-3"><MultiSelect dark searchable label="Categories" options={options.categories} value={filters.categories} onChange={(value) => set("categories", value)} formatOption={(value) => categoryOptionLabel(value, options.category_labels)} /></div>
      <div className="mt-3"><MultiSelect dark label="Flows" options={options.flows} value={filters.flows} onChange={(value) => set("flows", value)} /></div>
    </>
  );
}

export function Sidebar({ open, mobilePanel, collapsed, onClose, onToggle, page, onPage, options, filters, onFilters }) {
  const closeRef = useRef(null);
  const returnFocusRef = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    returnFocusRef.current = document.activeElement;
    closeRef.current?.focus();
    const closeOnEscape = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", closeOnEscape);
    return () => { window.removeEventListener("keydown", closeOnEscape); returnFocusRef.current?.focus(); };
  }, [open]);
  return (
    <aside id="dashboard-drawer" className={`sidebar ${open ? "open" : ""} ${collapsed ? "collapsed" : ""} mobile-${mobilePanel || "none"}`} aria-label={mobilePanel === "filters" ? "Dashboard filters" : "Dashboard navigation"} aria-modal={open || undefined} role={open ? "dialog" : undefined}>
      <div className="sidebar-header mb-7 flex items-center justify-between">
        <div className="flex items-center gap-3"><button className={`brand-mark ${collapsed ? "is-collapsed" : ""}`} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} aria-expanded={!collapsed} onClick={onToggle}><Globe2 size={22} /></button><div className="brand-copy"><div className="text-[15px] font-semibold"><span className="mobile-panel-title">{mobilePanel === "filters" ? "Filters" : "Navigation"}</span><span className="desktop-brand-title">Commodity Trade</span></div><div className="text-[11px] text-[#222420]">UN Comtrade analytics</div></div></div>
        <button ref={closeRef} className="mobile-close md:hidden" aria-label="Close drawer" onClick={onClose}><X size={20} /></button>
      </div>
      <div className="sidebar-body">
        <div className="sidebar-filters"><Filters options={options} filters={filters} onChange={onFilters} /></div>
        <div className="sidebar-navigation"><div className="sidebar-label">Navigate</div><nav className="grid gap-1">{pages.map(([key, label, Icon]) => <button key={key} className={`nav-button ${page === key ? "active" : ""}`} onClick={() => { onPage(key); onClose(); }}><Icon size={17} strokeWidth={1.8} /><span>{label}</span></button>)}</nav></div>
      </div>
    </aside>
  );
}

export function MobileHeader({ onMenu, onFilters, label, panel }) {
  return <header className="mobile-header"><button aria-label="Open navigation" aria-controls="dashboard-drawer" aria-expanded={panel === "navigation"} onClick={onMenu}><Menu size={22} /></button><span className="mobile-page-label">{label}</span><button className="mobile-filter-button" aria-label="Open filters" aria-controls="dashboard-drawer" aria-expanded={panel === "filters"} onClick={onFilters}><SlidersHorizontal size={17} /><span>Filters</span></button></header>;
}
