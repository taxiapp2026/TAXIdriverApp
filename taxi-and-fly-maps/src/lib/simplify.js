/** Douglas-Peucker simplification for polylines in lng/lat space. */

function sqDist(p, a, b) {
  const x = a[0];
  const y = a[1];
  const dx = b[0] - x;
  const dy = b[1] - y;
  if (dx === 0 && dy === 0) {
    const qx = p[0] - x;
    const qy = p[1] - y;
    return qx * qx + qy * qy;
  }
  const t = Math.max(0, Math.min(1, ((p[0] - x) * dx + (p[1] - y) * dy) / (dx * dx + dy * dy)));
  const qx = p[0] - (x + t * dx);
  const qy = p[1] - (y + t * dy);
  return qx * qx + qy * qy;
}

export function simplifyRing(points, tolerance) {
  if (!points || points.length < 3) return points || [];
  const tol = tolerance * tolerance;
  const keep = new Uint8Array(points.length);
  keep[0] = 1;
  keep[points.length - 1] = 1;
  const stack = [[0, points.length - 1]];
  while (stack.length) {
    const [start, end] = stack.pop();
    let maxD = -1;
    let idx = -1;
    for (let i = start + 1; i < end; i += 1) {
      const d = sqDist(points[i], points[start], points[end]);
      if (d > maxD) {
        maxD = d;
        idx = i;
      }
    }
    if (maxD > tol && idx >= 0) {
      keep[idx] = 1;
      stack.push([start, idx], [idx, end]);
    }
  }
  const out = [];
  for (let i = 0; i < points.length; i += 1) if (keep[i]) out.push(points[i]);
  return out;
}

export function simplifyGeometry(geom, zoom) {
  if (!geom) return geom;
  const tolerance = zoom >= 16 ? 0 : zoom >= 14 ? 0.00004 : zoom >= 12 ? 0.00012 : 0.0004;
  if (tolerance === 0) return geom;
  if (geom.type === "LineString") {
    const coords = simplifyRing(geom.coordinates, tolerance);
    return coords.length >= 2 ? { type: "LineString", coordinates: coords } : geom;
  }
  if (geom.type === "Polygon") {
    return {
      type: "Polygon",
      coordinates: geom.coordinates.map((ring) => {
        const s = simplifyRing(ring, tolerance);
        return s.length >= 4 ? s : ring;
      }),
    };
  }
  if (geom.type === "MultiLineString") {
    return {
      type: "MultiLineString",
      coordinates: geom.coordinates.map((line) => {
        const s = simplifyRing(line, tolerance);
        return s.length >= 2 ? s : line;
      }),
    };
  }
  return geom;
}

export function bboxOfCoords(coords, acc = null) {
  const box = acc || { minLng: 180, minLat: 90, maxLng: -180, maxLat: -90 };
  if (typeof coords[0] === "number") {
    box.minLng = Math.min(box.minLng, coords[0]);
    box.minLat = Math.min(box.minLat, coords[1]);
    box.maxLng = Math.max(box.maxLng, coords[0]);
    box.maxLat = Math.max(box.maxLat, coords[1]);
    return box;
  }
  for (const c of coords) {
    if (Array.isArray(c)) bboxOfCoords(c, box);
  }
  return box;
}
