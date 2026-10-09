/**
 * Screen-to-Code vision lab.
 *
 * Converts a raster image (sketch, public-domain scan, or a screenshot of OUR map)
 * into vector polylines. This is not a Google Maps scraper: Google tiles, style
 * and POI databases are copyrighted and their ToS forbid extraction.
 */
import sharp from "sharp";
import { simplifyRing } from "./simplify.js";

export async function imageToMask(buffer, options = {}) {
  const {
    target = "auto",
    tolerance = 48,
    invert = false,
  } = options;
  const image = sharp(buffer).ensureAlpha();
  const { data, info } = await image.raw().toBuffer({ resolveWithObject: true });
  const { width, height } = info;
  const mask = new Uint8Array(width * height);
  const sample = samplePalette(data, width, height);

  const roadRgb = target === "auto" ? sample.road : hexToRgb(target);
  for (let i = 0; i < width * height; i += 1) {
    const o = i * 4;
    const d = colorDist(data[o], data[o + 1], data[o + 2], roadRgb);
    let on = d <= tolerance;
    if (invert) on = !on;
    mask[i] = on ? 1 : 0;
  }
  closeMask(mask, width, height);
  return { mask, width, height, palette: sample };
}

export function skeletonize(mask, width, height) {
  // Zhang-Suen thinning
  const img = mask.slice();
  let changed = true;
  const neighbors = (x, y) => {
    const p = (dx, dy) => (x + dx >= 0 && y + dy >= 0 && x + dx < width && y + dy < height ? img[(y + dy) * width + (x + dx)] : 0);
    return [p(0, -1), p(1, -1), p(1, 0), p(1, 1), p(0, 1), p(-1, 1), p(-1, 0), p(-1, -1)];
  };
  while (changed) {
    changed = false;
    for (const step of [0, 1]) {
      const toClear = [];
      for (let y = 1; y < height - 1; y += 1) {
        for (let x = 1; x < width - 1; x += 1) {
          const i = y * width + x;
          if (!img[i]) continue;
          const n = neighbors(x, y);
          const sum = n.reduce((a, b) => a + b, 0);
          if (sum < 2 || sum > 6) continue;
          let trans = 0;
          for (let k = 0; k < 8; k += 1) if (n[k] === 0 && n[(k + 1) % 8] === 1) trans += 1;
          if (trans !== 1) continue;
          if (step === 0 && n[0] * n[2] * n[4] !== 0) continue;
          if (step === 0 && n[2] * n[4] * n[6] !== 0) continue;
          if (step === 1 && n[0] * n[2] * n[6] !== 0) continue;
          if (step === 1 && n[0] * n[4] * n[6] !== 0) continue;
          toClear.push(i);
        }
      }
      if (toClear.length) {
        changed = true;
        for (const i of toClear) img[i] = 0;
      }
    }
  }
  return img;
}

export function traceSkeleton(skel, width, height) {
  const used = new Uint8Array(width * height);
  const lines = [];
  const idx = (x, y) => y * width + x;
  const n8 = [
    [1, 0],
    [-1, 0],
    [0, 1],
    [0, -1],
    [1, 1],
    [1, -1],
    [-1, 1],
    [-1, -1],
  ];
  const degree = (x, y) => {
    let d = 0;
    for (const [dx, dy] of n8) {
      const nx = x + dx;
      const ny = y + dy;
      if (nx >= 0 && ny >= 0 && nx < width && ny < height && skel[idx(nx, ny)]) d += 1;
    }
    return d;
  };
  const walk = (sx, sy) => {
    const line = [[sx, sy]];
    used[idx(sx, sy)] = 1;
    let x = sx;
    let y = sy;
    while (true) {
      let next = null;
      for (const [dx, dy] of n8) {
        const nx = x + dx;
        const ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
        const i = idx(nx, ny);
        if (skel[i] && !used[i]) {
          next = [nx, ny];
          break;
        }
      }
      if (!next) break;
      used[idx(next[0], next[1])] = 1;
      line.push(next);
      x = next[0];
      y = next[1];
    }
    return line;
  };
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const i = idx(x, y);
      if (!skel[i] || used[i]) continue;
      if (degree(x, y) !== 1) continue;
      const line = walk(x, y);
      if (line.length >= 6) lines.push(line);
    }
  }
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const i = idx(x, y);
      if (!skel[i] || used[i]) continue;
      const line = walk(x, y);
      if (line.length >= 8) lines.push(line);
    }
  }
  return lines;
}

export function pixelLinesToGeoJSON(lines, width, height, gcps = null, simplifyTol = 1.8) {
  const features = [];
  for (const line of lines) {
    const simplified = simplifyRing(
      line.map(([x, y]) => [x, y]),
      simplifyTol,
    );
    const coords = simplified.map(([x, y]) => {
      if (gcps && gcps.length >= 2) return applyGcps(x, y, width, height, gcps);
      return [x, y];
    });
    features.push({
      type: "Feature",
      properties: { source: "vision", kind: "road", class: "traced" },
      geometry: { type: "LineString", coordinates: coords },
    });
  }
  return {
    type: "FeatureCollection",
    features,
    properties: {
      space: gcps && gcps.length >= 2 ? "wgs84" : "pixel",
      width,
      height,
    },
  };
}

export async function extractVectors(buffer, options = {}) {
  const { mask, width, height, palette } = await imageToMask(buffer, options);
  const skel = skeletonize(mask, width, height);
  const lines = traceSkeleton(skel, width, height);
  const geojson = pixelLinesToGeoJSON(lines, width, height, options.gcps, options.simplifyTol ?? 1.8);
  return { geojson, width, height, palette, lineCount: lines.length };
}

/** Two-point similarity or 3+ point affine georeference. gcps: [{pixel:[x,y], lnglat:[lng,lat]}] */
export function applyGcps(x, y, width, height, gcps) {
  if (gcps.length >= 3) return affine(x, y, gcps);
  const a = gcps[0];
  const b = gcps[1];
  const dxp = b.pixel[0] - a.pixel[0];
  const dyp = b.pixel[1] - a.pixel[1];
  const dxl = b.lnglat[0] - a.lnglat[0];
  const dyl = b.lnglat[1] - a.lnglat[1];
  const scaleX = dxp !== 0 ? dxl / dxp : 0;
  const scaleY = dyp !== 0 ? dyl / dyp : 0;
  return [a.lnglat[0] + (x - a.pixel[0]) * scaleX, a.lnglat[1] + (y - a.pixel[1]) * scaleY];
}

function affine(x, y, gcps) {
  const pts = gcps.slice(0, 3);
  const A = [
    [pts[0].pixel[0], pts[0].pixel[1], 1],
    [pts[1].pixel[0], pts[1].pixel[1], 1],
    [pts[2].pixel[0], pts[2].pixel[1], 1],
  ];
  const lng = [pts[0].lnglat[0], pts[1].lnglat[0], pts[2].lnglat[0]];
  const lat = [pts[0].lnglat[1], pts[1].lnglat[1], pts[2].lnglat[1]];
  const inv = invert3(A);
  const cx = mul3(inv, lng);
  const cy = mul3(inv, lat);
  return [cx[0] * x + cx[1] * y + cx[2], cy[0] * x + cy[1] * y + cy[2]];
}

function invert3(m) {
  const det =
    m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) -
    m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) +
    m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
  const i = 1 / det;
  return [
    [
      i * (m[1][1] * m[2][2] - m[1][2] * m[2][1]),
      i * (m[0][2] * m[2][1] - m[0][1] * m[2][2]),
      i * (m[0][1] * m[1][2] - m[0][2] * m[1][1]),
    ],
    [
      i * (m[1][2] * m[2][0] - m[1][0] * m[2][2]),
      i * (m[0][0] * m[2][2] - m[0][2] * m[2][0]),
      i * (m[0][2] * m[1][0] - m[0][0] * m[1][2]),
    ],
    [
      i * (m[1][0] * m[2][1] - m[1][1] * m[2][0]),
      i * (m[0][1] * m[2][0] - m[0][0] * m[2][1]),
      i * (m[0][0] * m[1][1] - m[0][1] * m[1][0]),
    ],
  ];
}

function mul3(m, v) {
  return [m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2], m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2], m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2]];
}

function samplePalette(data, width, height) {
  let r = 0;
  let g = 0;
  let b = 0;
  let n = 0;
  for (let y = 0; y < height; y += 8) {
    for (let x = 0; x < width; x += 8) {
      const o = (y * width + x) * 4;
      r += data[o];
      g += data[o + 1];
      b += data[o + 2];
      n += 1;
    }
  }
  const avg = { r: r / n, g: g / n, b: b / n };
  // Prefer mid-luminance “road-like” pixels rather than background.
  let best = { r: 180, g: 180, b: 180 };
  let bestScore = -1;
  for (let y = 0; y < height; y += 5) {
    for (let x = 0; x < width; x += 5) {
      const o = (y * width + x) * 4;
      const lum = 0.3 * data[o] + 0.59 * data[o + 1] + 0.11 * data[o + 2];
      const sat = Math.max(data[o], data[o + 1], data[o + 2]) - Math.min(data[o], data[o + 1], data[o + 2]);
      const score = lum > 70 && lum < 220 && sat < 40 ? lum : 0;
      if (score > bestScore) {
        bestScore = score;
        best = { r: data[o], g: data[o + 1], b: data[o + 2] };
      }
    }
  }
  return { average: avg, road: best };
}

function closeMask(mask, width, height) {
  const copy = mask.slice();
  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      const i = y * width + x;
      if (copy[i]) continue;
      let n = 0;
      for (let dy = -1; dy <= 1; dy += 1) {
        for (let dx = -1; dx <= 1; dx += 1) n += copy[(y + dy) * width + (x + dx)];
      }
      if (n >= 5) mask[i] = 1;
    }
  }
}

function colorDist(r, g, b, target) {
  return Math.hypot(r - target.r, g - target.g, b - target.b);
}

function hexToRgb(hex) {
  const h = hex.replace("#", "");
  return {
    r: parseInt(h.slice(0, 2), 16),
    g: parseInt(h.slice(2, 4), 16),
    b: parseInt(h.slice(4, 6), 16),
  };
}

export async function rasterizeLinePng(width, height, lines) {
  const buf = Buffer.alloc(width * height * 3, 12);
  for (const line of lines) {
    for (let i = 0; i < line.length - 1; i += 1) {
      drawLine(buf, width, height, line[i], line[i + 1], [210, 210, 210]);
    }
  }
  return sharp(buf, { raw: { width, height, channels: 3 } }).png().toBuffer();
}

function drawLine(buf, width, height, a, b, rgb) {
  const steps = Math.max(Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1]));
  for (let i = 0; i <= steps; i += 1) {
    const t = steps === 0 ? 0 : i / steps;
    const x = Math.round(a[0] + (b[0] - a[0]) * t);
    const y = Math.round(a[1] + (b[1] - a[1]) * t);
    for (let oy = -1; oy <= 1; oy += 1) {
      for (let ox = -1; ox <= 1; ox += 1) {
        const px = x + ox;
        const py = y + oy;
        if (px < 0 || py < 0 || px >= width || py >= height) continue;
        const o = (py * width + px) * 3;
        buf[o] = rgb[0];
        buf[o + 1] = rgb[1];
        buf[o + 2] = rgb[2];
      }
    }
  }
}
