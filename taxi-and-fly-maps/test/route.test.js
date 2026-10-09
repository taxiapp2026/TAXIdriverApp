import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { openDb, insertFeature, loadRoadGraph, nearestNode, routeAStar } from "../src/lib/db.js";

test("A* follows connected roads and ignores polygons", () => {
  const file = path.join(os.tmpdir(), `tfm-route-${Date.now()}.sqlite`);
  const db = openDb(file);
  insertFeature(db, {
    kind: "road",
    class: "residential",
    name: "A",
    geom: { type: "LineString", coordinates: [[23.73, 37.97], [23.74, 37.97]] },
    source: "test",
  });
  insertFeature(db, {
    kind: "road",
    class: "residential",
    name: "B",
    geom: { type: "LineString", coordinates: [[23.74, 37.97], [23.74, 37.98]] },
    source: "test",
  });
  insertFeature(db, {
    kind: "road",
    class: "pedestrian",
    name: "plaza",
    geom: {
      type: "Polygon",
      coordinates: [[[23.735, 37.971], [23.736, 37.971], [23.736, 37.972], [23.735, 37.972], [23.735, 37.971]]],
    },
    source: "test",
  });
  const graph = loadRoadGraph(db);
  const a = nearestNode(graph, 23.73, 37.97);
  const b = nearestNode(graph, 23.74, 37.98);
  const route = routeAStar(graph, a.key, b.key);
  assert.ok(route && route.length >= 2);
  assert.ok(Math.abs(route.at(-1).lat - 37.98) < 0.001);
  db.close();
  fs.unlinkSync(file);
});
