export function compact(value, currency = false) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  const number = Number(value);
  const abs = Math.abs(number);
  const units = [[1e12, "T"], [1e9, "B"], [1e6, "M"]];
  const unit = units.find(([size]) => abs >= size);
  const scaled = unit ? abs / unit[0] : abs;
  const formatted = scaled.toLocaleString("en-US", {
    maximumFractionDigits: unit?.[1] === "T" ? 2 : unit ? 1 : 3,
  });
  return `${number < 0 ? "-" : ""}${currency ? "$" : ""}${formatted}${unit?.[1] || ""}`;
}

export const scaledCurrency = (value, scale = 1) => compact(Number(value) * scale, true);

export function exactCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
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
