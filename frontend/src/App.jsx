import { lazy, Suspense, useEffect, useState } from "react";
import { Sidebar, MobileHeader, pages } from "./components/Sidebar";
import { ActiveFilters, ErrorState, PageSkeleton } from "./components/ui";
import { createDefaultFilters, isDefaultFilters } from "./filterState";
import { useApi } from "./hooks";

const page = (load, name) => lazy(() => load().then((module) => ({ default: module[name] })));

const pageComponents = {
  overview: page(() => import("./pages/core"), "OverviewPage"),
  trends: page(() => import("./pages/core"), "TrendsPage"),
  regions: page(() => import("./pages/core"), "RegionsPage"),
  growth: page(() => import("./pages/growth"), "GrowthPage"),
  products: page(() => import("./pages/other"), "ProductsPage"),
  why: page(() => import("./pages/other"), "WhyPage"),
  preview: page(() => import("./pages/other"), "PreviewPage"),
  models: page(() => import("./pages/other"), "ModelsPage"),
  story: page(() => import("./pages/other"), "StoryPage"),
};

export default function App() {
  const optionsState = useApi("/api/filters");
  const [page, setPage] = useState("overview");
  const [mobilePanel, setMobilePanel] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [filters, setFilters] = useState(null);
  useEffect(() => {
    if (optionsState.data && !filters) setFilters(createDefaultFilters(optionsState.data));
  }, [optionsState.data, filters]);
  const CurrentPage = pageComponents[page];
  const label = pages.find(([key]) => key === page)?.[1] || "Commodity Trade";
  const resetFilters = () => optionsState.data && setFilters(createDefaultFilters(optionsState.data));
  const selectCountry = (country) => setFilters((current) => ({ ...current, countries: [country] }));
  if (optionsState.error) return <main className="content"><ErrorState error={optionsState.error} retry={optionsState.retry} /></main>;
  return (
    <div className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      <Sidebar open={Boolean(mobilePanel)} mobilePanel={mobilePanel} collapsed={sidebarCollapsed} onClose={() => setMobilePanel(null)} onToggle={() => setSidebarCollapsed((value) => !value)} page={page} onPage={setPage} options={optionsState.data} filters={filters || { year_from: 1995, year_to: 2015, countries: [], categories: [], flows: [], exclude_aggregate: true, preset: "Custom" }} onFilters={setFilters} />
      {mobilePanel && <button className="drawer-backdrop" aria-label="Close drawer" onClick={() => setMobilePanel(null)} />}
      <div className="workspace">
        <MobileHeader label={label} panel={mobilePanel} onMenu={() => { setSidebarCollapsed(false); setMobilePanel("navigation"); }} onFilters={() => { setSidebarCollapsed(false); setMobilePanel("filters"); }} />
        <main className="content">{filters && optionsState.data && <ActiveFilters filters={filters} options={optionsState.data} resetDisabled={isDefaultFilters(filters, optionsState.data)} onReset={resetFilters} />}{filters ? <Suspense fallback={<PageSkeleton page={page} />}><CurrentPage filters={filters} onResetFilters={resetFilters} onSelectCountry={selectCountry} /></Suspense> : <PageSkeleton page={page} />}</main>
      </div>
    </div>
  );
}
