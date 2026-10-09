import { test } from "node:test";
import assert from "node:assert/strict";
import { lngLatToWorld, worldToLngLat, lngLatToScreen, screenToLngLat } from "../src/lib/projection.js";

test("web mercator roundtrip around Athens", () => {
  const orig = { lng: 23.734, lat: 37.975 };
  const w = lngLatToWorld(orig.lng, orig.lat);
  const back = worldToLngLat(w.x, w.y);
  assert.ok(Math.abs(back.lng - orig.lng) < 1e-9);
  assert.ok(Math.abs(back.lat - orig.lat) < 1e-9);
});

test("screen roundtrip", () => {
  const camera = { lng: 23.73, lat: 37.97, zoom: 15 };
  const ll = { lng: 23.74, lat: 37.98 };
  const p = lngLatToScreen(ll.lng, ll.lat, camera, 800, 600);
  const back = screenToLngLat(p.x, p.y, camera, 800, 600);
  assert.ok(Math.abs(back.lng - ll.lng) < 1e-7);
  assert.ok(Math.abs(back.lat - ll.lat) < 1e-7);
});
