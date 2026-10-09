import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { openDb, insertFeature, searchFeatures, queryViewport, stats } from "../src/lib/db.js";

test("sqlite spatial search and FTS", () => {
  const file = path.join(os.tmpdir(), `tfm-${Date.now()}.sqlite`);
  const db = openDb(file);
  insertFeature(db, {
    kind: "road",
    class: "primary",
    name: "Ερμού",
    name_en: "Ermou",
    tags: { highway: "primary" },
    geom: { type: "LineString", coordinates: [[23.73, 37.976], [23.735, 37.976]] },
    source: "test",
  });
  insertFeature(db, {
    kind: "poi",
    class: "hotel",
    name: "Grande Bretagne",
    tags: { tourism: "hotel" },
    geom: { type: "Point", coordinates: [23.735, 37.976] },
    source: "test",
  });
  const found = searchFeatures(db, "Ερμού");
  assert.ok(found.some((f) => f.name === "Ερμού"));
  const hotels = searchFeatures(db, "Grande");
  assert.ok(hotels.some((f) => f.class === "hotel"));
  const vp = queryViewport(db, { west: 23.72, south: 37.97, east: 23.74, north: 37.98 }, 15);
  assert.equal(vp.length, 2);
  assert.equal(stats(db).hotels, 1);
  db.close();
  fs.unlinkSync(file);
});
