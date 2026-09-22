import { lazy, Suspense, useEffect, useState } from "react";
import { Sidebar, MobileHeader, pages } from "./components/Sidebar";
import { ErrorState, PageSkeleton } from "./components/ui";
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
  const [menuOpen, setMenuOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [filters, setFilters] = useState(null);
  useEffect(() => {
    if (optionsState.data && !filters) setFilters({ year_from: optionsState.data.default_range[0], year_to: optionsState.data.default_range[1], countries: [], categories: [], flows: optionsState.data.flows, exclude_aggregate: true, preset: "Default (1995-2015)" });
  }, [optionsState.data, filters]);
  const CurrentPage = pageComponents[page];
  const label = pages.find(([key]) => key === page)?.[1] || "Commodity Trade";
  if (optionsState.error) return <main className="content"><ErrorState error={optionsState.error} retry={optionsState.retry} /></main>;
  return (
    <div className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      <Sidebar open={menuOpen} collapsed={sidebarCollapsed} onClose={() => setMenuOpen(false)} onToggle={() => setSidebarCollapsed((value) => !value)} page={page} onPage={setPage} options={optionsState.data} filters={filters || { year_from: 1995, year_to: 2015, countries: [], categories: [], flows: [], exclude_aggregate: true, preset: "Custom" }} onFilters={setFilters} />
      {menuOpen && <button className="fixed inset-0 z-30 bg-black/20 md:hidden" aria-label="Close navigation backdrop" onClick={() => setMenuOpen(false)} />}
      <div className="workspace">
        <MobileHeader label={label} onMenu={() => { setSidebarCollapsed(false); setMenuOpen(true); }} />
        <main className="content">{filters ? <Suspense fallback={<PageSkeleton page={page} />}><CurrentPage filters={filters} /></Suspense> : <PageSkeleton page={page} />}</main>
      </div>
    </div>
  );
}
