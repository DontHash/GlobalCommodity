const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export function queryString(filters = {}, params = {}) {
  const search = new URLSearchParams();
  const values = { ...filters, ...params };
  Object.entries(values).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    if (Array.isArray(value)) value.forEach((item) => search.append(key, item));
    else search.set(key, value);
  });
  return search.toString();
}

export async function api(path, filters, params, signal) {
  const query = queryString(filters, params);
  const response = await fetch(`${API_BASE_URL}${path}${query ? `?${query}` : ""}`, { signal });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

export function exportUrl(filters, params) {
  const query = queryString(filters, params);
  return `${API_BASE_URL}/api/trades/export?${query}`;
}
