import countries from "i18n-iso-countries";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import world from "world-atlas/countries-110m.json";
import { compact, exactCurrency } from "../format";

const mapColors = { total_trade: "#789fa8", exports: "#4f8892", imports: "#f56f5c" };

export default function MapPlot({ rows, metric, onSelectCountry }) {
  const validRows = rows.filter((row) => Number.isFinite(Number(row.value)));
  const values = new Map(validRows.map((row) => [Number(countries.alpha3ToNumeric(row.iso3)), { ...row, value: Number(row.value) }]));
  const max = Math.max(1, ...validRows.map((row) => Math.abs(Number(row.value))));
  return (
    <div className="relative h-full w-full">
      <ComposableMap projection="geoEqualEarth" role="img" aria-label="World trade choropleth" className="h-full w-full">
        <Geographies geography={world}>
          {({ geographies }) => geographies.map((geo) => {
            const row = values.get(Number(geo.id));
            const fill = !row ? "#e8e6e2" : metric === "trade_balance" ? (row.value < 0 ? "#d94b4b" : "#169b62") : mapColors[metric];
            const opacity = row ? 0.25 + 0.75 * Math.sqrt(Math.abs(row.value) / max) : 1;
            const details = row ? [row.country_or_area, row.rank ? `Rank #${row.rank}` : null, compact(row.trade_usd, true), Number.isFinite(row.share_pct) ? `${row.share_pct.toFixed(1)}% of selected trade` : null, Number.isFinite(row.yoy_pct) ? `${row.yoy_pct > 0 ? "+" : ""}${row.yoy_pct.toFixed(1)}% YoY` : null].filter(Boolean).join(" • ") : "";
            const select = row && onSelectCountry ? () => onSelectCountry(row.country_or_area) : undefined;
            return (
              <Geography key={geo.rsmKey} geography={geo} fill={fill} fillOpacity={opacity} stroke="#f8f7f5" strokeWidth={0.35} className={select ? "country-mark" : undefined} role={select ? "button" : undefined} tabIndex={select ? 0 : -1} aria-label={select ? `Filter dashboard to ${row.country_or_area}` : undefined} onClick={select} onKeyDown={(event) => { if (select && (event.key === "Enter" || event.key === " ")) select(); }} style={{ default: { outline: "none" }, hover: { outline: "none", filter: "brightness(.9)" }, pressed: { outline: "none" } }}>
                {row && <title>{`${details}\nExact: ${exactCurrency(row.trade_usd)}`}</title>}
              </Geography>
            );
          })}
        </Geographies>
      </ComposableMap>
      <div className="absolute bottom-2 right-2 rounded-full bg-white/90 px-3 py-1 text-[10px] text-[var(--muted)] shadow-sm">
        {metric === "trade_balance" ? "Red deficit · Green surplus" : "Lighter low · Darker high"}
      </div>
    </div>
  );
}
