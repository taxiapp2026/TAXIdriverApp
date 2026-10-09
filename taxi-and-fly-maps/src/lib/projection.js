/** Web Mercator helpers. No third-party map SDK. */

export const MAX_LAT = 85.05112878;

export function clampLat(lat) {
  return Math.max(-MAX_LAT, Math.min(MAX_LAT, lat));
}

export function lngLatToWorld(lng, lat) {
  const x = (lng + 180) / 360;
  const s = Math.sin((clampLat(lat) * Math.PI) / 180);
  const y = 0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI);
  return { x, y };
}

export function worldToLngLat(x, y) {
  const lng = x * 360 - 180;
  const n = Math.PI - 2 * Math.PI * y;
  const lat = (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)));
  return { lng, lat };
}

export function zoomScale(zoom) {
  return 256 * 2 ** zoom;
}

export function lngLatToScreen(lng, lat, camera, width, height) {
  const world = lngLatToWorld(lng, lat);
  const scale = zoomScale(camera.zoom);
  const cx = lngLatToWorld(camera.lng, camera.lat);
  return {
    x: (world.x - cx.x) * scale + width / 2,
    y: (world.y - cx.y) * scale + height / 2,
  };
}

export function screenToLngLat(px, py, camera, width, height) {
  const scale = zoomScale(camera.zoom);
  const cx = lngLatToWorld(camera.lng, camera.lat);
  const x = cx.x + (px - width / 2) / scale;
  const y = cySafe(cx.y + (py - height / 2) / scale);
  return worldToLngLat(x, y);
}

function cySafe(y) {
  return Math.max(0, Math.min(1, y));
}

export function viewportBounds(camera, width, height, pad = 0.08) {
  const w = width * (1 + pad);
  const h = height * (1 + pad);
  const a = screenToLngLat(-width * pad, -height * pad, camera, width, height);
  const b = screenToLngLat(w, h, camera, width, height);
  return {
    west: Math.min(a.lng, b.lng),
    east: Math.max(a.lng, b.lng),
    north: Math.max(a.lat, b.lat),
    south: Math.min(a.lat, b.lat),
  };
}

export function haversineMeters(a, b) {
  const R = 6371000;
  const r1 = (a.lat * Math.PI) / 180;
  const r2 = (b.lat * Math.PI) / 180;
  const d1 = ((b.lat - a.lat) * Math.PI) / 180;
  const d2 = ((b.lng - a.lng) * Math.PI) / 180;
  const h =
    Math.sin(d1 / 2) ** 2 +
    Math.cos(r1) * Math.cos(r2) * Math.sin(d2 / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
}
