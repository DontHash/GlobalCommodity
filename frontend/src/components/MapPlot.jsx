import countries from "i18n-iso-countries";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import world from "world-atlas/countries-110m.json";

export default function MapPlot({ rows, metric }) {
  const validRows = rows.filter((row) => Number.isFinite(Number(row.value)));
  const values = new Map(validRows.map((row) => [Number(countries.alpha3ToNumeric(row.iso3)), { ...row, value: Number(row.value) }]));
  const max = Math.max(1, ...validRows.map((row) => Math.abs(Number(row.value))));
  return (
    <div className="relative h-full w-full">
      <ComposableMap projection="geoEqualEarth" role="img" aria-label="World trade choropleth" className="h-full w-full">
        <Geographies geography={world}>
          {({ geographies }) => geographies.map((geo) => {
            const row = values.get(Number(geo.id));
            const fill = !row ? "#e8e6e2" : metric === "trade_balance" ? (row.value < 0 ? "#d94b4b" : "#169b62") : "#789fa8";
            const opacity = row ? 0.25 + 0.75 * Math.sqrt(Math.abs(row.value) / max) : 1;
            return (
              <Geography key={geo.rsmKey} geography={geo} fill={fill} fillOpacity={opacity} stroke="#f8f7f5" strokeWidth={0.35} tabIndex={-1} style={{ default: { outline: "none" }, hover: { outline: "none", filter: "brightness(.9)" }, pressed: { outline: "none" } }}>
                {row && <title>{`${row.country_or_area}: ${row.value.toFixed(2)} billion USD`}</title>}
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
