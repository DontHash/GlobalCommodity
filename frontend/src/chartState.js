export function hasPlottableData(rows = [], keys = []) {
  return rows.some((row) => keys.some((key) => Number.isFinite(row?.[key])));
}

export function toggleSeries(visible, key, allKeys) {
  if (visible.includes(key)) return visible.length === 1 ? visible : visible.filter((item) => item !== key);
  return allKeys.filter((item) => item === key || visible.includes(item));
}

export function truncateLabel(value, limit = 19) {
  const label = String(value ?? "");
  if (label.length <= limit) return label;
  const clipped = label.slice(0, limit - 1).trimEnd();
  const boundary = clipped.lastIndexOf(" ");
  return `${boundary >= Math.floor(limit * .6) ? clipped.slice(0, boundary) : clipped}…`;
}
