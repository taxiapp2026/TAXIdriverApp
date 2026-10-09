#!/usr/bin/env node
/**
 * Import reusable OpenStreetMap data (ODbL) into the Taxi and Fly Maps database.
 * Never talks to Google. Free sources only: Geofabrik extracts + public Overpass.
 */
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { spawnSync } from "node:child_process";
import { Readable } from "node:stream";
import { fileURLToPath } from "node:url";
import { ATTICA_BBOX, classifyTags, displayName } from "./lib/classify.js";
import { DATA_DIR, openDb, replaceAllFeatures, setMeta, insertFeature } from "./lib/db.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const USER_AGENT = "TaxiAndFlyMaps/0.1 (ODbL consumer; https://github.com/taxiapp2026/TAXIdriverApp)";
const GEOFABRIK = "https://download.geofabrik.de/europe/greece-latest.osm.pbf";

const args = parseArgs(process.argv.slice(2));
const mode = args.mode || "seed";

await main();

async function main() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  const db = openDb();
  if (mode === "seed") {
    const packed = path.join(DATA_DIR, "seed-center.json.gz");
    let features;
    if (fs.existsSync(packed)) {
      features = JSON.parse(zlib.gunzipSync(fs.readFileSync(packed)).toString("utf8"));
      setMeta(db, "source", "OpenStreetMap (bundled central Athens extract, ODbL)");
    } else {
      features = await fetchOverpassTiles(seedTiles());
      setMeta(db, "source", "OpenStreetMap via Overpass API");
    }
    replaceAllFeatures(db, features);
    setMeta(db, "coverage", "seed-athens-center");
    setMeta(db, "license", "ODbL 1.0 https://opendatacommons.org/licenses/odbl/");
    setMeta(db, "importedAt", new Date().toISOString());
    console.log(`Imported ${features.length} seed features (central Athens).`);
    return;
  }
  if (mode === "bbox") {
    const bbox = {
      west: num(args.west, ATTICA_BBOX.west),
      south: num(args.south, ATTICA_BBOX.south),
      east: num(args.east, ATTICA_BBOX.east),
      north: num(args.north, ATTICA_BBOX.north),
    };
    const features = await fetchOverpassTiles(tileBbox(bbox, 0.04));
    replaceAllFeatures(db, features);
    setMeta(db, "coverage", bbox);
    setMeta(db, "source", "OpenStreetMap via Overpass API");
    setMeta(db, "license", "ODbL 1.0");
    setMeta(db, "importedAt", new Date().toISOString());
    console.log(`Imported ${features.length} features for bbox ${JSON.stringify(bbox)}.`);
    return;
  }
  if (mode === "attica") {
    const geojsonl = await prepareAtticaExtract();
    const count = await importGeojsonSeq(db, geojsonl);
    setMeta(db, "coverage", { ...ATTICA_BBOX, mode: "attica" });
    setMeta(db, "source", "OpenStreetMap via Geofabrik greece-latest.osm.pbf");
    setMeta(db, "license", "ODbL 1.0 — © OpenStreetMap contributors");
    setMeta(db, "importedAt", new Date().toISOString());
    console.log(`Imported ${count} Attica features from Geofabrik extract.`);
    return;
  }
  throw new Error(`Unknown mode ${mode}`);
}

function seedTiles() {
  return [
    { west: 23.71, south: 37.965, east: 23.76, north: 37.995, label: "syntagma-plaka" },
    { west: 23.71, south: 37.98, east: 23.745, north: 38.005, label: "omonia" },
    { west: 23.73, south: 37.97, east: 23.76, north: 37.99, label: "kolonaki" },
    { west: 23.62, south: 37.93, east: 23.66, north: 37.96, label: "piraeus" },
    { west: 23.93, south: 37.92, east: 23.97, north: 37.95, label: "airport" },
  ];
}

function tileBbox(bbox, step) {
  const tiles = [];
  for (let lat = bbox.south; lat < bbox.north; lat += step) {
    for (let lng = bbox.west; lng < bbox.east; lng += step) {
      tiles.push({
        west: lng,
        south: lat,
        east: Math.min(lng + step, bbox.east),
        north: Math.min(lat + step, bbox.north),
      });
    }
  }
  return tiles;
}

async function fetchOverpassTiles(tiles) {
  const all = [];
  const seen = new Set();
  for (const tile of tiles) {
    console.log(`Overpass ${tile.label || `${tile.west},${tile.south}`}`);
    const json = await overpass(tile);
    const feats = osmJsonToFeatures(json);
    for (const f of feats) {
      const key = `${f.osm_id}:${f.kind}:${f.class}:${f.name}`;
      if (seen.has(key)) continue;
      seen.add(key);
      all.push(f);
    }
  }
  return all;
}

async function overpass(bbox) {
  const q = `
[out:json][timeout:90];
(
  way["highway"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
  way["natural"="water"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
  way["leisure"="park"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
  way["landuse"~"forest|grass|recreation_ground"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
  way["waterway"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
  way["railway"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
  way["aeroway"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
  node["amenity"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
  node["shop"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
  node["tourism"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
  node["aeroway"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
  node["highway"="bus_stop"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
  node["railway"="station"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
  node["public_transport"="station"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
  node["addr:housenumber"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
);
(._;>;);
out body;
`;
  const endpoints = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.jp/api/interpreter",
  ];
  let lastErr;
  for (const url of endpoints) {
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "text/plain", "User-Agent": USER_AGENT },
        body: q,
      });
      if (!res.ok) throw new Error(`${url} ${res.status}`);
      return await res.json();
    } catch (err) {
      lastErr = err;
      console.warn(err.message);
    }
  }
  throw lastErr;
}

function osmJsonToFeatures(json) {
  const nodes = new Map();
  for (const el of json.elements || []) {
    if (el.type === "node") nodes.set(el.id, [el.lon, el.lat]);
  }
  const features = [];
  for (const el of json.elements || []) {
    const tags = el.tags || {};
    const classified = classifyTags(tags);
    if (!classified) continue;
    let geom = null;
    if (el.type === "node") {
      geom = { type: "Point", coordinates: [el.lon, el.lat] };
    } else if (el.type === "way" && el.nodes) {
      const coords = el.nodes.map((id) => nodes.get(id)).filter(Boolean);
      if (coords.length < 2) continue;
      const closed = coords.length >= 4 && coords[0][0] === coords.at(-1)[0] && coords[0][1] === coords.at(-1)[1];
      if (closed && (classified.kind === "water" || classified.kind === "park" || classified.kind === "building" || classified.kind === "area")) {
        geom = { type: "Polygon", coordinates: [coords] };
      } else {
        geom = { type: "LineString", coordinates: coords };
      }
    }
    if (!geom) continue;
    features.push({
      osm_id: `${el.type}/${el.id}`,
      kind: classified.kind,
      class: classified.class,
      name: displayName(tags),
      name_en: tags["name:en"] || "",
      tags,
      geom,
      source: "osm",
    });
  }
  return features;
}

async function prepareAtticaExtract() {
  const greece = path.join(DATA_DIR, "greece-latest.osm.pbf");
  const attica = path.join(DATA_DIR, "attica.osm.pbf");
  const filtered = path.join(DATA_DIR, "attica-map.osm.pbf");
  const geojsonl = path.join(DATA_DIR, "attica.geojsonl");
  if (!fs.existsSync(greece)) {
    console.log("Downloading Geofabrik greece-latest.osm.pbf (free, ODbL)...");
    await download(GEOFABRIK, greece);
  }
  if (!fs.existsSync(attica)) {
    osmium([
      "extract",
      `--bbox=${ATTICA_BBOX.west},${ATTICA_BBOX.south},${ATTICA_BBOX.east},${ATTICA_BBOX.north}`,
      "--overwrite",
      greece,
      "-o",
      attica,
    ]);
  }
  if (!fs.existsSync(filtered)) {
    osmium([
      "tags-filter",
      "--overwrite",
      attica,
      "-o",
      filtered,
      "w/highway",
      "w/waterway",
      "w/natural=water",
      "w/leisure",
      "w/landuse",
      "w/aeroway",
      "w/railway",
      "nwr/amenity",
      "nwr/shop",
      "nwr/tourism",
      "nwr/aeroway",
      "nwr/public_transport",
      "nwr/addr:housenumber",
      "nwr/office",
      "n/place",
    ]);
  }
  if (!fs.existsSync(geojsonl)) {
    osmium(["export", "--overwrite", "-f", "geojsonseq", "-o", geojsonl, filtered]);
  }
  return geojsonl;
}

function importGeojsonSeq(db, file) {
  db.exec("DELETE FROM features_fts; DELETE FROM features_rtree; DELETE FROM features;");
  const insertMany = db.transaction((batch) => {
    for (const f of batch) insertFeature(db, f);
  });
  const fd = fs.openSync(file, "r");
  const stream = fs.createReadStream(file, { encoding: "utf8", fd });
  let buf = "";
  let batch = [];
  let count = 0;
  return new Promise((resolve, reject) => {
    stream.on("data", (chunk) => {
      buf += chunk;
      let nl;
      while ((nl = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, nl).trim().replace(/^\u001e/, "");
        buf = buf.slice(nl + 1);
        if (!line) continue;
        const feat = geojsonFeature(JSON.parse(line));
        if (!feat) continue;
        batch.push(feat);
        if (batch.length >= 500) {
          insertMany(batch);
          count += batch.length;
          batch = [];
          if (count % 10000 === 0) console.log(`  ${count} features...`);
        }
      }
    });
    stream.on("end", () => {
      if (batch.length) {
        insertMany(batch);
        count += batch.length;
      }
      resolve(count);
    });
    stream.on("error", reject);
  });
}

function geojsonFeature(obj) {
  const feat = obj.type === "Feature" ? obj : obj.features ? null : obj;
  if (!feat || !feat.geometry) return null;
  const tags = feat.properties || {};
  const classified = classifyTags(tags);
  if (!classified) return null;
  const geom = feat.geometry;
  if (!geom.coordinates) return null;
  if (classified.kind === "building") return null;
  return {
    osm_id: tags["@id"] || tags.id || tags.osm_id || null,
    kind: classified.kind,
    class: classified.class,
    name: displayName(tags),
    name_en: tags["name:en"] || "",
    tags,
    geom,
    source: "osm",
  };
}

function osmium(argv) {
  console.log("osmium", argv.join(" "));
  const r = spawnSync("osmium", argv, { stdio: "inherit" });
  if (r.status !== 0) throw new Error(`osmium failed: ${argv[0]}`);
}

async function download(url, dest) {
  const tmp = `${dest}.part`;
  const res = await fetch(url, { headers: { "User-Agent": USER_AGENT } });
  if (!res.ok) throw new Error(`download ${url} ${res.status}`);
  const file = fs.createWriteStream(tmp);
  await new Promise((resolve, reject) => {
    const nodeStream = Readable.fromWeb(res.body);
    nodeStream.pipe(file);
    nodeStream.on("error", reject);
    file.on("finish", resolve);
    file.on("error", reject);
  });
  fs.renameSync(tmp, dest);
}

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const [k, v] = a.slice(2).split("=");
      if (v !== undefined) out[k] = v;
      else if (argv[i + 1] && !argv[i + 1].startsWith("--")) {
        out[k] = argv[++i];
      } else out[k] = true;
    }
  }
  return out;
}

function num(v, d) {
  const n = Number(v);
  return Number.isFinite(n) ? n : d;
}
