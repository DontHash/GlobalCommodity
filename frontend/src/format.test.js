import test from "node:test";
import assert from "node:assert/strict";
import { compact, exactCurrency, yearLabel } from "./format.js";
import { createDefaultFilters, isDefaultFilters } from "./filterState.js";
import { hasPlottableData, toggleSeries, truncateLabel } from "./chartState.js";

test("formats large currency without abbreviating thousands", () => {
  assert.equal(compact(1_240_000_000_000, true), "$1.24T");
  assert.equal(compact(482_600_000_000, true), "$482.6B");
  assert.equal(compact(18_300_000, true), "$18.3M");
  assert.equal(compact(482_600, true), "$482,600");
  assert.equal(compact(-18_300_000, true), "-$18.3M");
  assert.equal(compact(null, true), "-");
  assert.equal(exactCurrency(18_300_000), "$18,300,000");
  assert.equal(yearLabel(2001), "2001");
});

test("recognizes and recreates the shared default filters", () => {
  const options = { default_range: [1995, 2015], flows: ["Import", "Export"] };
  const defaults = createDefaultFilters(options);
  assert.equal(isDefaultFilters(defaults, options), true);
  assert.equal(isDefaultFilters({ ...defaults, flows: [...defaults.flows].reverse() }, options), true);
  assert.equal(isDefaultFilters({ ...defaults, countries: ["USA"] }, options), false);
  assert.deepEqual(createDefaultFilters(options), defaults);
});

test("detects chart gaps and keeps one legend series visible", () => {
  assert.equal(hasPlottableData([{ Export: null }, { Export: 12 }], ["Export"]), true);
  assert.equal(hasPlottableData([{ Export: null }, {}], ["Export"]), false);
  assert.deepEqual(toggleSeries(["Export", "Import"], "Import", ["Export", "Import"]), ["Export"]);
  assert.deepEqual(toggleSeries(["Export"], "Export", ["Export", "Import"]), ["Export"]);
  assert.deepEqual(toggleSeries(["Export"], "Import", ["Export", "Import"]), ["Export", "Import"]);
  assert.equal(truncateLabel("United States of America"), "United States of…");
  assert.equal(truncateLabel("Germany"), "Germany");
});
