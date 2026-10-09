import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Database from "better-sqlite3";
import { bboxOfCoords, simplifyGeometry } from "./simplify.js";
import { minZoomFor } from "./classify.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const DATA_DIR = path.resolve(__dirname, "../../data");
export const DB_PATH = path.join(DATA_DIR, "attica.sqlite");

export function openDb(file = DB_PATH) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const db = new Database(file);
  db.pragma("journal_mode = WAL");
  db.pragma("synchronous = NORMAL");
  db.exec(`
    CREATE TABLE IF NOT EXISTS features (
      id INTEGER PRIMARY KEY,
      osm_id TEXT,
      kind TEXT NOT NULL,
      class TEXT,
      name TEXT,
      name_en TEXT,
      tags TEXT,
      geom_type TEXT NOT NULL,
      geom TEXT NOT NULL,
      min_lng REAL, min_lat REAL, max_lng REAL, max_lat REAL,
      min_zoom INTEGER DEFAULT 0,
      source TEXT DEFAULT 'osm',
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_features_kind ON features(kind, class);
    CREATE INDEX IF NOT EXISTS idx_features_name ON features(name);
    CREATE INDEX IF NOT EXISTS idx_features_osm ON features(osm_id);
    CREATE VIRTUAL TABLE IF NOT EXISTS features_rtree USING rtree(
      id, min_lng, max_lng, min_lat, max_lat
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS features_fts USING fts5(
      name, name_en, class, kind, tokenize='unicode61'
    );
    CREATE TABLE IF NOT EXISTS edits (
      id INTEGER PRIMARY KEY,
      feature_id INTEGER,
      action TEXT,
      payload TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS meta (
      key TEXT PRIMARY KEY,
      value TEXT
    );
  `);
  return db;
}

export function setMeta(db, key, value) {
  db.prepare("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value").run(
    key,
    typeof value === "string" ? value : JSON.stringify(value),
  );
}

export function getMeta(db, key) {
  const row = db.prepare("SELECT value FROM meta WHERE key=?").get(key);
  if (!row) return null;
  try {
    return JSON.parse(row.value);
  } catch {
    return row.value;
  }
}

export function insertFeature(db, feature) {
  const geom = feature.geom;
  const box = bboxOfCoords(geom.coordinates);
  const minZoom = feature.min_zoom ?? minZoomFor(feature.kind, feature.class || "");
  const info = db
    .prepare(
      `INSERT INTO features (osm_id, kind, class, name, name_en, tags, geom_type, geom, min_lng, min_lat, max_lng, max_lat, min_zoom, source)
       VALUES (@osm_id, @kind, @class, @name, @name_en, @tags, @geom_type, @geom, @min_lng, @min_lat, @max_lng, @max_lat, @min_zoom, @source)`,
    )
    .run({
      osm_id: feature.osm_id || null,
      kind: feature.kind,
      class: feature.class || null,
      name: feature.name || "",
      name_en: feature.name_en || "",
      tags: JSON.stringify(feature.tags || {}),
      geom_type: geom.type,
      geom: JSON.stringify(geom),
      min_lng: box.minLng,
      min_lat: box.minLat,
      max_lng: box.maxLng,
      max_lat: box.maxLat,
      min_zoom: minZoom,
      source: feature.source || "osm",
    });
  const id = info.lastInsertRowid;
  db.prepare("INSERT INTO features_rtree(id, min_lng, max_lng, min_lat, max_lat) VALUES (?,?,?,?,?)").run(
    id,
    box.minLng,
    box.maxLng,
    box.minLat,
    box.maxLat,
  );
  if (feature.name || feature.name_en) {
    db.prepare("INSERT INTO features_fts(rowid, name, name_en, class, kind) VALUES (?,?,?,?,?)").run(
      id,
      feature.name || "",
      feature.name_en || "",
      feature.class || "",
      feature.kind,
    );
  }
  return id;
}

export function replaceAllFeatures(db, features) {
  const tx = db.transaction(() => {
    db.exec("DELETE FROM features_fts; DELETE FROM features_rtree; DELETE FROM features;");
    for (const f of features) insertFeature(db, f);
  });
  tx();
}

export function queryViewport(db, bbox, zoom, limit = 9000) {
  const rows = db
    .prepare(
      `SELECT f.id, f.kind, f.class, f.name, f.name_en, f.tags, f.geom_type, f.geom, f.source, f.min_zoom
       FROM features_rtree r
       JOIN features f ON f.id = r.id
       WHERE r.max_lng >= @west AND r.min_lng <= @east
         AND r.max_lat >= @south AND r.min_lat <= @north
         AND f.min_zoom <= @zoom
       ORDER BY CASE f.kind
         WHEN 'water' THEN 0 WHEN 'road' THEN 1 WHEN 'rail' THEN 2
         WHEN 'park' THEN 3 WHEN 'poi' THEN 4 WHEN 'place' THEN 5
         WHEN 'address' THEN 6 ELSE 7 END,
         CASE f.class
           WHEN 'motorway' THEN 0 WHEN 'trunk' THEN 1 WHEN 'primary' THEN 2
           WHEN 'secondary' THEN 3 WHEN 'airport' THEN 3 WHEN 'hotel' THEN 4
           WHEN 'fuel' THEN 4 ELSE 9 END
       LIMIT @limit`,
    )
    .all({ ...bbox, zoom, limit });
  return rows.map((row) => {
    const geom = simplifyGeometry(JSON.parse(row.geom), zoom);
    return {
      id: row.id,
      kind: row.kind,
      class: row.class,
      name: row.name,
      name_en: row.name_en,
      tags: JSON.parse(row.tags || "{}"),
      source: row.source,
      geometry: geom,
    };
  });
}

export function searchFeatures(db, q, limit = 25) {
  const query = q.trim();
  if (!query) return [];
  const like = `%${query.replaceAll("%", "")}%`;
  const fts = query.replace(/['"]/g, " ").split(/\s+/).filter(Boolean).map((w) => `${w}*`).join(" ");
  let rows = [];
  if (fts) {
    try {
      rows = db
        .prepare(
          `SELECT f.id, f.kind, f.class, f.name, f.name_en, f.geom, f.tags, f.source
           FROM features_fts t
           JOIN features f ON f.id = t.rowid
           WHERE features_fts MATCH ?
           LIMIT ?`,
        )
        .all(fts, limit);
    } catch {
      rows = [];
    }
  }
  if (rows.length < 5) {
    const extra = db
      .prepare(
        `SELECT id, kind, class, name, name_en, geom, tags, source
         FROM features
         WHERE name LIKE ? OR name_en LIKE ? OR class LIKE ?
         LIMIT ?`,
      )
      .all(like, like, like, limit);
    const seen = new Set(rows.map((r) => r.id));
    for (const r of extra) if (!seen.has(r.id)) rows.push(r);
  }
  return rows.slice(0, limit).map((row) => {
    const geom = JSON.parse(row.geom);
    const center = centroid(geom);
    return {
      id: row.id,
      kind: row.kind,
      class: row.class,
      name: row.name,
      name_en: row.name_en,
      tags: JSON.parse(row.tags || "{}"),
      source: row.source,
      center,
    };
  });
}

export function getFeature(db, id) {
  const row = db.prepare("SELECT * FROM features WHERE id=?").get(id);
  if (!row) return null;
  return {
    ...row,
    tags: JSON.parse(row.tags || "{}"),
    geometry: JSON.parse(row.geom),
  };
}

export function updateFeature(db, id, patch) {
  const current = getFeature(db, id);
  if (!current) return null;
  const name = patch.name ?? current.name;
  const name_en = patch.name_en ?? current.name_en;
  const kind = patch.kind ?? current.kind;
  const cls = patch.class ?? current.class;
  const tags = { ...current.tags, ...(patch.tags || {}) };
  const geom = patch.geometry ?? current.geometry;
  const box = bboxOfCoords(geom.coordinates);
  db.prepare(
    `UPDATE features SET name=@name, name_en=@name_en, kind=@kind, class=@class, tags=@tags,
      geom=@geom, geom_type=@geom_type, min_lng=@min_lng, min_lat=@min_lat, max_lng=@max_lng, max_lat=@max_lat,
      source='local-edit', updated_at=datetime('now') WHERE id=@id`,
  ).run({
    id,
    name,
    name_en,
    kind,
    class: cls,
    tags: JSON.stringify(tags),
    geom: JSON.stringify(geom),
    geom_type: geom.type,
    min_lng: box.minLng,
    min_lat: box.minLat,
    max_lng: box.maxLng,
    max_lat: box.maxLat,
  });
  db.prepare("UPDATE features_rtree SET min_lng=?, max_lng=?, min_lat=?, max_lat=? WHERE id=?").run(
    box.minLng,
    box.maxLng,
    box.minLat,
    box.maxLat,
    id,
  );
  db.prepare("DELETE FROM features_fts WHERE rowid=?").run(id);
  db.prepare("INSERT INTO features_fts(rowid, name, name_en, class, kind) VALUES (?,?,?,?,?)").run(
    id,
    name || "",
    name_en || "",
    cls || "",
    kind,
  );
  db.prepare("INSERT INTO edits(feature_id, action, payload) VALUES (?,?,?)").run(id, "update", JSON.stringify(patch));
  return getFeature(db, id);
}

export function deleteFeature(db, id) {
  db.prepare("DELETE FROM features WHERE id=?").run(id);
  db.prepare("DELETE FROM features_rtree WHERE id=?").run(id);
  db.prepare("DELETE FROM features_fts WHERE rowid=?").run(id);
  db.prepare("INSERT INTO edits(feature_id, action, payload) VALUES (?,?,?)").run(id, "delete", "{}");
}

export function stats(db) {
  const counts = db
    .prepare(
      `SELECT kind, class, COUNT(*) AS n FROM features GROUP BY kind, class ORDER BY n DESC`,
    )
    .all();
  const total = db.prepare("SELECT COUNT(*) AS n FROM features").get().n;
  const named = db.prepare("SELECT COUNT(*) AS n FROM features WHERE name IS NOT NULL AND name != ''").get().n;
  const hotels = db.prepare("SELECT COUNT(*) AS n FROM features WHERE class='hotel'").get().n;
  const fuel = db.prepare("SELECT COUNT(*) AS n FROM features WHERE class='fuel'").get().n;
  const shops = db.prepare("SELECT COUNT(*) AS n FROM features WHERE class='shop'").get().n;
  const roads = db.prepare("SELECT COUNT(*) AS n FROM features WHERE kind='road'").get().n;
  const addresses = db.prepare("SELECT COUNT(*) AS n FROM features WHERE kind='address'").get().n;
  const extent = db
    .prepare("SELECT MIN(min_lng) west, MIN(min_lat) south, MAX(max_lng) east, MAX(max_lat) north FROM features")
    .get();
  return { total, named, hotels, fuel, shops, roads, addresses, counts, extent };
}

export function loadRoadGraph(db, bbox = null) {
  const rows = bbox
    ? db
        .prepare(
          `SELECT f.id, f.class, f.name, f.geom FROM features_rtree r
           JOIN features f ON f.id = r.id
           WHERE f.kind='road' AND f.class NOT IN ('footway','path','steps','cycleway')
             AND r.max_lng >= @west AND r.min_lng <= @east
             AND r.max_lat >= @south AND r.min_lat <= @north`,
        )
        .all(bbox)
    : db
        .prepare(
          `SELECT id, class, name, geom FROM features
           WHERE kind='road' AND class NOT IN ('footway','path','steps','cycleway')`,
        )
        .all();
  const nodes = new Map();
  const adj = new Map();
  const key = (lng, lat) => `${lng.toFixed(5)},${lat.toFixed(5)}`;
  const ensure = (k, coord) => {
    if (!nodes.has(k)) nodes.set(k, { key: k, lng: coord[0], lat: coord[1] });
    if (!adj.has(k)) adj.set(k, []);
    return nodes.get(k);
  };
  for (const row of rows) {
    const geom = JSON.parse(row.geom);
    const lines = geom.type === "LineString" ? [geom.coordinates] : geom.coordinates || [];
    for (const line of lines) {
      for (let i = 0; i < line.length - 1; i += 1) {
        const a = ensure(key(line[i][0], line[i][1]), line[i]);
        const b = ensure(key(line[i + 1][0], line[i + 1][1]), line[i + 1]);
        const dx = a.lng - b.lng;
        const dy = a.lat - b.lat;
        const w = Math.hypot(dx * 85000, dy * 111000);
        adj.get(a.key).push({ to: b.key, w, way: row.id, name: row.name, class: row.class });
        adj.get(b.key).push({ to: a.key, w, way: row.id, name: row.name, class: row.class });
      }
    }
  }
  return { nodes, adj };
}

export function nearestNode(graph, lng, lat) {
  let best = null;
  let bestD = Infinity;
  for (const n of graph.nodes.values()) {
    const d = (n.lng - lng) ** 2 + (n.lat - lat) ** 2;
    if (d < bestD) {
      bestD = d;
      best = n;
    }
  }
  return best;
}

export function routeAStar(graph, startKey, endKey) {
  const { nodes, adj } = graph;
  const h = (k) => {
    const a = nodes.get(k);
    const b = nodes.get(endKey);
    return Math.hypot((a.lng - b.lng) * 85000, (a.lat - b.lat) * 111000);
  };
  const heap = [];
  const push = (key, f) => {
    heap.push({ key, f });
    let i = heap.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (heap[p].f <= heap[i].f) break;
      [heap[p], heap[i]] = [heap[i], heap[p]];
      i = p;
    }
  };
  const pop = () => {
    const top = heap[0];
    const last = heap.pop();
    if (heap.length) {
      heap[0] = last;
      let i = 0;
      while (true) {
        let s = i;
        const l = i * 2 + 1;
        const r = l + 1;
        if (l < heap.length && heap[l].f < heap[s].f) s = l;
        if (r < heap.length && heap[r].f < heap[s].f) s = r;
        if (s === i) break;
        [heap[s], heap[i]] = [heap[i], heap[s]];
        i = s;
      }
    }
    return top;
  };
  const came = new Map();
  const gScore = new Map([[startKey, 0]]);
  push(startKey, h(startKey));
  const seen = new Set();
  while (heap.length) {
    const current = pop().key;
    if (seen.has(current)) continue;
    seen.add(current);
    if (current === endKey) {
      const path = [current];
      while (came.has(path[0])) path.unshift(came.get(path[0]));
      return path.map((k) => nodes.get(k));
    }
    for (const e of adj.get(current) || []) {
      const tentative = (gScore.get(current) ?? Infinity) + e.w;
      if (tentative < (gScore.get(e.to) ?? Infinity)) {
        came.set(e.to, current);
        gScore.set(e.to, tentative);
        push(e.to, tentative + h(e.to));
      }
    }
  }
  return null;
}

function centroid(geom) {
  if (geom.type === "Point") return { lng: geom.coordinates[0], lat: geom.coordinates[1] };
  const ring = geom.type === "LineString" ? geom.coordinates : geom.coordinates[0];
  const mid = ring[Math.floor(ring.length / 2)];
  return { lng: mid[0], lat: mid[1] };
}
