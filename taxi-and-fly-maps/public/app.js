import { TaxiMap } from "./map-engine.js";

const canvas = document.getElementById("map");
const map = new TaxiMap(canvas);
const $ = (id) => document.getElementById(id);

let moveTimer = 0;
let routeFrom = null;

map.on("move", (state) => {
  $("coords").textContent = `${state.lat.toFixed(5)}, ${state.lng.toFixed(5)} · z${state.zoom.toFixed(2)}`;
  $("scale").textContent = `${Math.round(map.metersPerPixel() * 80)} m`;
  clearTimeout(moveTimer);
  moveTimer = setTimeout(() => loadViewport(state), 80);
});

map.on("select", (f) => showDetail(f));
map.on("hover", (f) => {
  canvas.title = f?.name || "";
});

async function loadViewport(state) {
  const b = state.bounds;
  const url = `/api/features?west=${b.west}&south=${b.south}&east=${b.east}&north=${b.north}&zoom=${state.zoom}`;
  const res = await fetch(url);
  const data = await res.json();
  map.setFeatures(data.features || []);
  $("visible").textContent = String((data.features || []).length);
}

async function loadStats() {
  const res = await fetch("/api/stats");
  const s = await res.json();
  $("stat-roads").textContent = s.roads.toLocaleString("el-GR");
  $("stat-hotels").textContent = s.hotels.toLocaleString("el-GR");
  $("stat-fuel").textContent = s.fuel.toLocaleString("el-GR");
  $("stat-shops").textContent = s.shops.toLocaleString("el-GR");
  $("stat-addr").textContent = s.addresses.toLocaleString("el-GR");
  $("stat-total").textContent = s.total.toLocaleString("el-GR");
  $("source-line").textContent = s.meta?.source || "—";
}

async function search() {
  const q = $("q").value.trim();
  const box = $("results");
  if (!q) {
    box.innerHTML = "";
    return;
  }
  const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
  const data = await res.json();
  box.innerHTML = (data.results || [])
    .map(
      (r) => `<button data-id="${r.id}" data-lng="${r.center.lng}" data-lat="${r.center.lat}">
        <div>${escapeHtml(r.name || r.class || "Χωρίς όνομα")}</div>
        <div class="kind">${r.kind} · ${r.class || ""}</div>
      </button>`,
    )
    .join("") || "<div class='kind'>Κανένα αποτέλεσμα στη δική μας βάση.</div>";
  box.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      map.setView(Number(btn.dataset.lng), Number(btn.dataset.lat), Math.max(map.camera.zoom, 16));
    });
  });
}

function showDetail(f) {
  const el = $("detail");
  if (!f) {
    el.innerHTML = "<div class='kind'>Κλικ σε δρόμο ή σημείο.</div>";
    return;
  }
  el.innerHTML = `
    <strong>${escapeHtml(f.name || "Χωρίς όνομα")}</strong>
    <div class="kind">${f.kind} · ${f.class || ""} · ${f.source || ""}</div>
    <label>Όνομα <input id="edit-name" type="text" value="${escapeAttr(f.name || "")}"></label>
    <div class="toolbar" style="margin-top:8px">
      <button id="save-name">Αποθήκευση</button>
      <button class="ghost" id="route-from">Αφετηρία διαδρομής</button>
      <button class="ghost" id="route-to">Προορισμός</button>
      <button class="ghost" id="del">Διαγραφή</button>
    </div>`;
  $("save-name").onclick = async () => {
    await fetch(`/api/features/${f.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: $("edit-name").value }),
    });
    loadViewport(map.viewState());
    loadStats();
  };
  $("del").onclick = async () => {
    await fetch(`/api/features/${f.id}`, { method: "DELETE" });
    map.selected = null;
    loadViewport(map.viewState());
    loadStats();
    showDetail(null);
  };
  $("route-from").onclick = () => {
    routeFrom = centerOf(f);
    $("route-status").textContent = "Αφετηρία ορίστηκε. Διάλεξε προορισμό.";
  };
  $("route-to").onclick = async () => {
    const to = centerOf(f);
    if (!routeFrom) routeFrom = { lng: map.camera.lng, lat: map.camera.lat };
    const res = await fetch(`/api/route?from=${routeFrom.lng},${routeFrom.lat}&to=${to.lng},${to.lat}`);
    if (!res.ok) {
      $("route-status").textContent = "Δεν βρέθηκε διαδρομή στο δικό μας γράφο δρόμων.";
      return;
    }
    map.route = await res.json();
    $("route-status").textContent = "Διαδρομή πάνω στο δικό μας δίκτυο (A*), όχι Google.";
  };
}

function centerOf(f) {
  if (f.geometry.type === "Point") return { lng: f.geometry.coordinates[0], lat: f.geometry.coordinates[1] };
  const c = f.geometry.coordinates[0];
  const pt = Array.isArray(c[0]) ? c[Math.floor(c.length / 2)] : c;
  return { lng: pt[0], lat: pt[1] };
}

$("q").addEventListener("keydown", (e) => {
  if (e.key === "Enter") search();
});
$("search-btn").onclick = search;
$("zoom-in").onclick = () => map.setView(map.camera.lng, map.camera.lat, map.camera.zoom + 0.6);
$("zoom-out").onclick = () => map.setView(map.camera.lng, map.camera.lat, map.camera.zoom - 0.6);
$("go-airport").onclick = () => map.setView(23.944, 37.936, 13);
$("go-piraeus").onclick = () => map.setView(23.646, 37.948, 14);
$("go-center").onclick = () => map.setView(23.734, 37.975, 15);

document.querySelectorAll("[data-filter]").forEach((el) => {
  el.addEventListener("change", () => {
    const set = new Set();
    document.querySelectorAll("[data-filter]:checked").forEach((c) => set.add(c.value));
    map.filters = set;
  });
});
document.querySelectorAll("[data-poi]").forEach((el) => {
  el.addEventListener("change", () => {
    const set = new Set();
    document.querySelectorAll("[data-poi]:checked").forEach((c) => set.add(c.value));
    map.poiFilter = set;
  });
});

$("add-poi").onclick = () => {
  const name = $("new-name").value.trim() || "Νέο σημείο Taxi and Fly";
  const cls = $("new-class").value;
  map.drawing = null;
  const ll = { lng: map.camera.lng, lat: map.camera.lat };
  fetch("/api/features", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      kind: "poi",
      class: cls,
      name,
      geometry: { type: "Point", coordinates: [ll.lng, ll.lat] },
    }),
  }).then(() => {
    loadViewport(map.viewState());
    loadStats();
  });
};

$("draw-road").onclick = () => {
  if (map.drawing) {
    const pts = map.drawing.points;
    map.drawing = null;
    if (pts.length >= 2) {
      fetch("/api/features", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind: "road",
          class: "residential",
          name: $("new-name").value.trim() || "Νέος δρόμος",
          geometry: { type: "LineString", coordinates: pts },
        }),
      }).then(() => {
        loadViewport(map.viewState());
        loadStats();
      });
    }
    $("draw-road").textContent = "Σχεδίαση δρόμου";
  } else {
    map.drawing = { points: [] };
    $("draw-road").textContent = "Τέλος σχεδίασης";
  }
};

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) {
  return escapeHtml(s);
}

loadStats();
loadViewport(map.viewState());
