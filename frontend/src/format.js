export function compact(value, currency = false) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  const number = Number(value);
  const abs = Math.abs(number);
  const units = [[1e12, "T"], [1e9, "B"], [1e6, "M"]];
  const unit = units.find(([size]) => abs >= size);
  const formatted = unit ? `${(number / unit[0]).toFixed(abs >= unit[0] * 100 ? 0 : 1)}${unit[1]}` : number.toLocaleString(undefined, { useGrouping: false, maximumFractionDigits: 3 });
  return currency ? `$${formatted}` : formatted;
}

export const percent = (value) => `${Number(value) > 0 ? "+" : ""}${Number(value).toFixed(1)}%`;
export const titleCase = (value = "") => String(value).replace(/^\d+_/, "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

export function categoryOptionLabel(value, labels = {}) {
  const raw = String(value);
  const code = raw.match(/^\d+/)?.[0] || "";
  const label = (labels[raw] || titleCase(raw))
    .replace(/\bAnd Articles Thereof\b$/i, "")
    .replace(/\bParts And Accessories Thereof\b$/i, "parts and accessories")
    .replace(/\bParts Thereof\b$/i, "parts")
    .replace(/\bManufactures Thereof\b$/i, "products")
    .replace(/\bThereof\b/gi, "")
    .replace(/\bNes\b/gi, "")
    .replace(/\bEtc\b/gi, "")
    .replace(/\bMiscellaneous\b/gi, "Other")
    .replace(/\bAnd\s*$/i, "")
    .replace(/\s+/g, " ")
    .trim();
  return `${code} ${label}`.trim();
}

export const yearLabel = (value) => Number.isFinite(Number(value)) ? String(Math.trunc(Number(value))) : String(value ?? "");
