import { test } from "node:test";
import assert from "node:assert/strict";
import { classifyTags, displayName } from "../src/lib/classify.js";
import { bboxOfCoords, simplifyRing } from "../src/lib/simplify.js";
import { extractVectors, rasterizeLinePng, applyGcps } from "../src/lib/vision.js";

test("classifies taxi-relevant OSM tags", () => {
  assert.equal(classifyTags({ highway: "residential" }).kind, "road");
  assert.equal(classifyTags({ amenity: "fuel" }).class, "fuel");
  assert.equal(classifyTags({ tourism: "hotel" }).class, "hotel");
  assert.equal(classifyTags({ shop: "supermarket" }).class, "shop");
  assert.equal(classifyTags({ aeroway: "aerodrome" }).class, "airport");
  assert.equal(displayName({ "addr:street": "Ερμού", "addr:housenumber": "12" }), "Ερμού 12");
});

test("bbox of point and linestring", () => {
  const p = bboxOfCoords([23.7, 37.9]);
  assert.equal(p.minLng, 23.7);
  const l = bboxOfCoords([[23.7, 37.9], [23.8, 38.0]]);
  assert.ok(l.maxLng > l.minLng);
});

test("douglas-peucker keeps endpoints", () => {
  const s = simplifyRing([[0, 0], [0.5, 0.00001], [1, 0]], 0.01);
  assert.equal(s[0][0], 0);
  assert.equal(s.at(-1)[0], 1);
});

test("vision traces a synthetic road sketch", async () => {
  const png = await rasterizeLinePng(200, 120, [[[10, 60], [190, 60]]]);
  const result = await extractVectors(png, { tolerance: 80 });
  assert.ok(result.lineCount >= 1);
  assert.equal(result.geojson.features[0].geometry.type, "LineString");
});

test("two-point georeference", () => {
  const gcps = [
    { pixel: [0, 0], lnglat: [23.7, 38.0] },
    { pixel: [100, 100], lnglat: [23.8, 37.9] },
  ];
  const ll = applyGcps(50, 50, 100, 100, gcps);
  assert.ok(Math.abs(ll[0] - 23.75) < 1e-9);
  assert.ok(Math.abs(ll[1] - 37.95) < 1e-9);
});
