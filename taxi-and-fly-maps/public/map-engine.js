import { lngLatToScreen, screenToLngLat, viewportBounds, haversineMeters } from "/lib/projection.js";

const ROAD_STYLE = {
  motorway: { color: "#f5c518", width: 7, label: true },
  motorway_link: { color: "#d4a017", width: 4 },
  trunk: { color: "#e0b429", width: 6, label: true },
  trunk_link: { color: "#c9a227", width: 4 },
  primary: { color: "#f0d78c", width: 5, label: true },
  primary_link: { color: "#dcc57a", width: 3.5 },
  secondary: { color: "#cfd6e4", width: 4, label: true },
  secondary_link: { color: "#b7c0d0", width: 3 },
  tertiary: { color: "#9aa8bd", width: 3.2 },
  tertiary_link: { color: "#8b98ad", width: 2.6 },
  residential: { color: "#7d8aa0", width: 2.6 },
  living_street: { color: "#7d8aa0", width: 2.4 },
  unclassified: { color: "#6e7b90", width: 2.4 },
  service: { color: "#5b677a", width: 1.6 },
  pedestrian: { color: "#6b7280", width: 2.2 },
  footway: { color: "#4b5563", width: 1.1 },
  path: { color: "#4b5563", width: 1.1 },
  steps: { color: "#64748b", width: 1.2 },
  track: { color: "#57534e", width: 1.4 },
  cycleway: { color: "#22d3ee", width: 1.3 },
  construction: { color: "#78716c", width: 2 },
  traced: { color: "#fb7185", width: 2.5 },
};

const POI_COLOR = {
  airport: "#22d3ee",
  hotel: "#7dd3fc",
  fuel: "#fb923c",
  shop: "#c4b5fd",
  food: "#f472b6",
  health: "#34d399",
  pharmacy: "#6ee7b7",
  transit: "#60a5fa",
  taxi: "#f5c518",
  emergency: "#fb7185",
  attraction: "#fde047",
  bank: "#93c5fd",
  worship: "#d8b4fe",
  office: "#a5b4fc",
};

export class TaxiMap {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.camera = { lng: 23.734, lat: 37.975, zoom: 15 };
    this.features = [];
    this.route = null;
    this.hover = null;
    this.selected = null;
    this.filters = new Set(["road", "water", "park", "poi", "rail", "address", "area"]);
    this.poiFilter = new Set(["hotel", "fuel", "shop", "airport", "transit", "taxi", "food", "health"]);
    this.listeners = {};
    this.drawing = null;
    this.resize();
    window.addEventListener("resize", () => this.resize());
    this.bindPointer();
    this.loop();
  }

  on(ev, fn) {
    (this.listeners[ev] ||= []).push(fn);
  }
  emit(ev, data) {
    (this.listeners[ev] || []).forEach((fn) => fn(data));
  }

  resize() {
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const r = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = Math.max(1, Math.floor(r.width * dpr));
    this.canvas.height = Math.max(1, Math.floor(r.height * dpr));
    this.canvas.style.width = `${r.width}px`;
    this.canvas.style.height = `${r.height}px`;
    this.dpr = dpr;
    this.emit("move", this.viewState());
  }

  viewState() {
    const w = this.canvas.width / this.dpr;
    const h = this.canvas.height / this.dpr;
    return { ...this.camera, bounds: viewportBounds(this.camera, w, h), width: w, height: h };
  }

  setFeatures(features) {
    this.features = features;
  }

  setView(lng, lat, zoom = this.camera.zoom) {
    this.camera = { lng, lat, zoom };
    this.emit("move", this.viewState());
  }

  bindPointer() {
    let drag = null;
    this.canvas.addEventListener("pointerdown", (e) => {
      this.canvas.setPointerCapture(e.pointerId);
      const p = this.eventXY(e);
      if (this.drawing) {
        const ll = this.screenToLl(p.x, p.y);
        this.drawing.points.push([ll.lng, ll.lat]);
        return;
      }
      drag = { x: p.x, y: p.y, lng: this.camera.lng, lat: this.camera.lat };
    });
    this.canvas.addEventListener("pointermove", (e) => {
      const p = this.eventXY(e);
      if (drag) {
        const a = this.screenToLl(drag.x, drag.y);
        const b = this.screenToLl(p.x, p.y);
        this.camera.lng = drag.lng - (b.lng - a.lng);
        this.camera.lat = drag.lat - (b.lat - a.lat);
        this.emit("move", this.viewState());
      } else {
        this.hover = this.pick(p.x, p.y);
        this.emit("hover", this.hover);
      }
    });
    const end = () => {
      drag = null;
    };
    this.canvas.addEventListener("pointerup", (e) => {
      const p = this.eventXY(e);
      if (!this.drawing && drag && Math.hypot(p.x - drag.x, p.y - drag.y) < 4) {
        this.selected = this.pick(p.x, p.y);
        this.emit("select", this.selected);
      }
      end();
    });
    this.canvas.addEventListener("pointercancel", end);
    this.canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const p = this.eventXY(e);
      const before = this.screenToLl(p.x, p.y);
      this.camera.zoom = Math.max(8, Math.min(19, this.camera.zoom - e.deltaY * 0.0015));
      const after = this.screenToLl(p.x, p.y);
      this.camera.lng += before.lng - after.lng;
      this.camera.lat += before.lat - after.lat;
      this.emit("move", this.viewState());
    }, { passive: false });
    this.canvas.addEventListener("dblclick", (e) => {
      const p = this.eventXY(e);
      const ll = this.screenToLl(p.x, p.y);
      this.setView(ll.lng, ll.lat, this.camera.zoom + 1);
    });
  }

  eventXY(e) {
    const r = this.canvas.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  screenToLl(x, y) {
    const w = this.canvas.width / this.dpr;
    const h = this.canvas.height / this.dpr;
    return screenToLngLat(x, y, this.camera, w, h);
  }

  llToScreen(lng, lat) {
    const w = this.canvas.width / this.dpr;
    const h = this.canvas.height / this.dpr;
    return lngLatToScreen(lng, lat, this.camera, w, h);
  }

  pick(x, y) {
    let best = null;
    let bestD = 18;
    for (const f of this.features) {
      if (f.kind === "poi" || f.kind === "address" || f.geometry?.type === "Point") {
        const [lng, lat] = f.geometry.coordinates;
        const p = this.llToScreen(lng, lat);
        const d = Math.hypot(p.x - x, p.y - y);
        if (d < bestD) {
          bestD = d;
          best = f;
        }
      }
    }
    if (best) return best;
    for (const f of this.features) {
      if (f.kind !== "road" || f.geometry?.type !== "LineString") continue;
      for (const c of f.geometry.coordinates) {
        const p = this.llToScreen(c[0], c[1]);
        const d = Math.hypot(p.x - x, p.y - y);
        if (d < 10) return f;
      }
    }
    return null;
  }

  loop() {
    this.draw();
    requestAnimationFrame(() => this.loop());
  }

  draw() {
    const ctx = this.ctx;
    const dpr = this.dpr;
    const w = this.canvas.width;
    const h = this.canvas.height;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const cssW = w / dpr;
    const cssH = h / dpr;
    ctx.fillStyle = "#0b1220";
    ctx.fillRect(0, 0, cssW, cssH);

    const drawPoly = (f, fill) => {
      const rings = f.geometry.type === "Polygon" ? f.geometry.coordinates : [];
      ctx.beginPath();
      for (const ring of rings) {
        ring.forEach((c, i) => {
          const p = this.llToScreen(c[0], c[1]);
          if (i === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        });
        ctx.closePath();
      }
      ctx.fillStyle = fill;
      ctx.fill();
    };

    for (const f of this.features) {
      if (!this.filters.has(f.kind)) continue;
      if (f.kind === "water") drawPoly(f, "#14344d");
      if (f.kind === "park" || f.kind === "area") drawPoly(f, "#163328");
      if (f.kind === "building") drawPoly(f, "#243044");
    }

    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    for (const f of this.features) {
      if (f.kind !== "rail" || !this.filters.has("rail")) continue;
      this.strokeLine(f, "#334155", 2.2);
    }
    for (const pass of ["casing", "fill"]) {
      for (const f of this.features) {
        if (f.kind !== "road" || !this.filters.has("road")) continue;
        const st = ROAD_STYLE[f.class] || ROAD_STYLE.unclassified;
        const width = st.width * (0.55 + this.camera.zoom / 18);
        if (pass === "casing") this.strokeLine(f, "#0b0f16", width + 2.2);
        else this.strokeLine(f, st.color, width);
      }
    }

    if (this.route) this.strokeLine({ geometry: this.route.geometry }, "#22d3ee", 4.5);

    const occupied = new Set();
    for (const f of this.features) {
      if (f.kind !== "poi" || !this.filters.has("poi")) continue;
      if (this.poiFilter.size && !this.poiFilter.has(f.class) && f.class !== "airport") continue;
      if (f.geometry.type !== "Point") continue;
      const p = this.llToScreen(f.geometry.coordinates[0], f.geometry.coordinates[1]);
      if (p.x < 0 || p.y < 0 || p.x > cssW || p.y > cssH) continue;
      ctx.beginPath();
      ctx.fillStyle = POI_COLOR[f.class] || "#e5e7eb";
      ctx.arc(p.x, p.y, f.class === "airport" ? 6 : 3.4, 0, Math.PI * 2);
      ctx.fill();
      const important = f.class === "airport" || f.class === "hotel" || f.class === "fuel" || f.class === "taxi" || f.class === "transit";
      const showLabel = f.name && (important ? this.camera.zoom >= 14 : this.camera.zoom >= 18);
      if (showLabel) {
        const key = `${Math.round(p.x / 72)}:${Math.round(p.y / 18)}`;
        if (!occupied.has(key)) {
          occupied.add(key);
          ctx.fillStyle = "rgba(12,16,24,0.7)";
          ctx.fillRect(p.x + 6, p.y - 8, Math.min(160, f.name.length * 6.2), 14);
          ctx.fillStyle = "#e8eef7";
          ctx.font = "11px sans-serif";
          ctx.fillText(f.name, p.x + 8, p.y + 3);
        }
      }
    }

    if (this.camera.zoom >= 16 && this.filters.has("road")) {
      ctx.font = "11px sans-serif";
      for (const f of this.features) {
        if (f.kind !== "road" || !f.name || f.geometry.type !== "LineString") continue;
        const st = ROAD_STYLE[f.class];
        if (!st?.label && this.camera.zoom < 17) continue;
        const coords = f.geometry.coordinates;
        const mid = coords[Math.floor(coords.length / 2)];
        const p = this.llToScreen(mid[0], mid[1]);
        const key = `${Math.round(p.x / 80)}:${Math.round(p.y / 16)}`;
        if (occupied.has(key) || p.x < 20 || p.y < 20) continue;
        occupied.add(key);
        ctx.fillStyle = "rgba(12,16,24,0.65)";
        ctx.fillRect(p.x - 2, p.y - 10, Math.min(180, f.name.length * 6.1), 14);
        ctx.fillStyle = "#dbe4f0";
        ctx.fillText(f.name, p.x, p.y);
      }
    }

    if (this.selected) this.mark(this.selected, "#f5c518");
    if (this.hover && this.hover !== this.selected) this.mark(this.hover, "#22d3ee");
    if (this.drawing?.points?.length) {
      ctx.strokeStyle = "#fb7185";
      ctx.lineWidth = 2;
      ctx.beginPath();
      this.drawing.points.forEach((c, i) => {
        const p = this.llToScreen(c[0], c[1]);
        if (i === 0) ctx.moveTo(p.x, p.y);
        else ctx.lineTo(p.x, p.y);
      });
      ctx.stroke();
    }
  }

  strokeLine(f, color, width) {
    const ctx = this.ctx;
    const lines = f.geometry.type === "LineString" ? [f.geometry.coordinates] : f.geometry.type === "MultiLineString" ? f.geometry.coordinates : [];
    ctx.beginPath();
    for (const line of lines) {
      line.forEach((c, i) => {
        const p = this.llToScreen(c[0], c[1]);
        if (i === 0) ctx.moveTo(p.x, p.y);
        else ctx.lineTo(p.x, p.y);
      });
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.stroke();
  }

  mark(f, color) {
    let lng;
    let lat;
    if (f.geometry.type === "Point") {
      lng = f.geometry.coordinates[0];
      lat = f.geometry.coordinates[1];
    } else {
      const c = f.geometry.coordinates[0];
      const pt = Array.isArray(c[0]) ? c[Math.floor(c.length / 2)] : c;
      lng = pt[0];
      lat = pt[1];
    }
    const p = this.llToScreen(lng, lat);
    const ctx = this.ctx;
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.arc(p.x, p.y, 10, 0, Math.PI * 2);
    ctx.stroke();
  }

  metersPerPixel() {
    const a = this.screenToLl(0, 0);
    const b = this.screenToLl(100, 0);
    return haversineMeters({ lat: a.lat, lng: a.lng }, { lat: b.lat, lng: b.lng }) / 100;
  }
}
