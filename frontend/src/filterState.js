export function createDefaultFilters(options) {
  return {
    year_from: options.default_range[0],
    year_to: options.default_range[1],
    countries: [],
    categories: [],
    flows: [...options.flows],
    exclude_aggregate: true,
    preset: "Default (1995-2015)",
  };
}

export function isDefaultFilters(filters, options) {
  if (!filters || !options) return true;
  const defaults = createDefaultFilters(options);
  return ["year_from", "year_to", "exclude_aggregate", "preset"].every((key) => filters[key] === defaults[key])
    && ["countries", "categories", "flows"].every((key) => JSON.stringify([...(filters[key] || [])].sort()) === JSON.stringify([...defaults[key]].sort()));
}
