import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import express from "express";
import multer from "multer";
import {
  openDb,
  queryViewport,
  searchFeatures,
  getFeature,
  updateFeature,
  deleteFeature,
  insertFeature,
  stats,
  getMeta,
  setMeta,
  loadRoadGraph,
  nearestNode,
  routeAStar,
  DB_PATH,
} from "./lib/db.js";
import { extractVectors, rasterizeLinePng } from "./lib/vision.js";
import { ATTICA_BBOX } from "./lib/classify.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const PORT = Number(process.env.PORT || 3477);

if (!fs.existsSync(DB_PATH)) {
  const { spawnSync } = await import("node:child_process");
  const geojsonl = path.join(ROOT, "data/attica.geojsonl");
  const mode = fs.existsSync(geojsonl) ? "attica" : "seed";
  console.log(`No database yet. Importing OpenStreetMap (${mode}, ODbL)...`);
  const r = spawnSync(process.execPath, [path.join(__dirname, "import-osm.js"), "--mode", mode], {
    stdio: "inherit",
    cwd: ROOT,
  });
  if (r.status !== 0) {
    console.warn("Import failed. The map will start empty until you run npm run import:seed or import:attica.");
  }
}

const db = openDb();
function graphNear(from, to) {
  const pad = 0.12;
  const bbox = {
    west: Math.min(from[0], to[0]) - pad,
    east: Math.max(from[0], to[0]) + pad,
    south: Math.min(from[1], to[1]) - pad,
    north: Math.max(from[1], to[1]) + pad,
  };
  return loadRoadGraph(db, bbox);
}

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 8 * 1024 * 1024 },
});

const app = express();
app.use(express.json({ limit: "4mb" }));
app.use(express.static(path.join(ROOT, "public")));
app.use("/lib", express.static(path.join(ROOT, "src/lib")));

app.get("/api/health", (_req, res) => {
  res.json({
    ok: true,
    product: "Taxi and Fly Maps",
    google: false,
    paidServices: false,
    license: getMeta(db, "license"),
    coverage: getMeta(db, "coverage"),
    bbox: ATTICA_BBOX,
  });
});

app.get("/api/stats", (_req, res) => {
  res.json({
    ...stats(db),
    meta: {
      source: getMeta(db, "source"),
      license: getMeta(db, "license"),
      importedAt: getMeta(db, "importedAt"),
      coverage: getMeta(db, "coverage"),
    },
  });
});

app.get("/api/features", (req, res) => {
  const west = Number(req.query.west);
  const south = Number(req.query.south);
  const east = Number(req.query.east);
  const north = Number(req.query.north);
  const zoom = Number(req.query.zoom || 14);
  if (![west, south, east, north].every(Number.isFinite)) {
    res.status(400).json({ error: "bbox required" });
    return;
  }
  const features = queryViewport(db, { west, south, east, north }, zoom);
  res.json({ type: "FeatureCollection", features });
});

app.get("/api/search", (req, res) => {
  const q = String(req.query.q || "");
  res.json({ results: searchFeatures(db, q) });
});

app.get("/api/features/:id", (req, res) => {
  const row = getFeature(db, Number(req.params.id));
  if (!row) {
    res.status(404).json({ error: "not found" });
    return;
  }
  res.json(row);
});

app.post("/api/features", (req, res) => {
  const body = req.body || {};
  if (!body.geometry || !body.kind) {
    res.status(400).json({ error: "kind and geometry required" });
    return;
  }
  const id = insertFeature(db, {
    osm_id: null,
    kind: body.kind,
    class: body.class || "custom",
    name: body.name || "",
    name_en: body.name_en || "",
    tags: { ...(body.tags || {}), local: true },
    geom: body.geometry,
    source: "local-edit",
  });
  res.json(getFeature(db, id));
});

app.put("/api/features/:id", (req, res) => {
  const row = updateFeature(db, Number(req.params.id), req.body || {});
  if (!row) {
    res.status(404).json({ error: "not found" });
    return;
  }
  res.json(row);
});

app.delete("/api/features/:id", (req, res) => {
  deleteFeature(db, Number(req.params.id));
  res.json({ ok: true });
});

app.get("/api/route", (req, res) => {
  const from = String(req.query.from || "").split(",").map(Number);
  const to = String(req.query.to || "").split(",").map(Number);
  if (from.length !== 2 || to.length !== 2 || from.some(Number.isNaN) || to.some(Number.isNaN)) {
    res.status(400).json({ error: "from=lng,lat&to=lng,lat" });
    return;
  }
  const g = graphNear(from, to);
  const a = nearestNode(g, from[0], from[1]);
  const b = nearestNode(g, to[0], to[1]);
  if (!a || !b) {
    res.status(404).json({ error: "no road graph" });
    return;
  }
  const pathNodes = routeAStar(g, a.key, b.key);
  if (!pathNodes) {
    res.status(404).json({ error: "no route" });
    return;
  }
  const coordinates = pathNodes.map((n) => [n.lng, n.lat]);
  res.json({
    type: "Feature",
    properties: { kind: "route", from: a, to: b },
    geometry: { type: "LineString", coordinates },
  });
});

app.post("/api/vision/demo", async (_req, res) => {
  const png = await rasterizeLinePng(480, 320, [
    [[40, 40], [420, 50], [400, 260]],
    [[40, 40], [60, 280]],
    [[60, 160], [400, 150]],
  ]);
  res.type("image/png").send(png);
});

app.post("/api/vision/extract", upload.single("image"), async (req, res) => {
  try {
    if (!req.file) {
      res.status(400).json({ error: "image file required" });
      return;
    }
    let gcps = null;
    if (req.body.gcps) gcps = JSON.parse(req.body.gcps);
    const result = await extractVectors(req.file.buffer, {
      tolerance: Number(req.body.tolerance || 48),
      target: req.body.target || "auto",
      gcps,
    });
    res.json({
      warning:
        "Αυτό το εργαστήριο μετατρέπει εικόνα σε διανύσματα. Μην το χρησιμοποιείτε σε στιγμιότυπα Google Maps — τα δεδομένα και το στυλ της Google προστατεύονται. Χρησιμοποιήστε σκίτσα, δημόσιου τομέα χάρτες, ή στιγμιότυπα του δικού μας χάρτη.",
      ...result,
    });
  } catch (err) {
    res.status(500).json({ error: String(err.message || err) });
  }
});

app.post("/api/vision/commit", (req, res) => {
  const fc = req.body?.geojson;
  if (!fc?.features) {
    res.status(400).json({ error: "geojson required" });
    return;
  }
  if (fc.properties?.space !== "wgs84") {
    res.status(400).json({ error: "commit only georeferenced (wgs84) features" });
    return;
  }
  const ids = [];
  for (const feat of fc.features) {
    ids.push(
      insertFeature(db, {
        osm_id: null,
        kind: feat.properties?.kind || "road",
        class: feat.properties?.class || "traced",
        name: feat.properties?.name || "Vision trace",
        tags: { source: "vision" },
        geom: feat.geometry,
        source: "vision",
      }),
    );
  }
  res.json({ ids, count: ids.length });
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`Taxi and Fly Maps http://127.0.0.1:${PORT}`);
  setMeta(db, "serverStarted", new Date().toISOString());
});
