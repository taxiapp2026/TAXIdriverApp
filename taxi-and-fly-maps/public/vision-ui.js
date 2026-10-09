const canvas = document.getElementById("visionCanvas");
const ctx = canvas.getContext("2d");
const status = document.getElementById("status");
let file = null;

document.getElementById("file").addEventListener("change", (e) => {
  file = e.target.files[0] || null;
});

document.getElementById("run").onclick = async () => {
  if (!file) {
    status.textContent = "Διάλεξε εικόνα.";
    return;
  }
  await extract(file);
};

document.getElementById("demo").onclick = async () => {
  const demo = await fetch("/api/vision/demo", { method: "POST" }).catch(() => null);
  if (demo?.ok) {
    const blob = await demo.blob();
    file = new File([blob], "demo.png", { type: "image/png" });
    await extract(file);
    return;
  }
  const c = document.createElement("canvas");
  c.width = 480;
  c.height = 320;
  const g = c.getContext("2d");
  g.fillStyle = "#0b1220";
  g.fillRect(0, 0, 480, 320);
  g.strokeStyle = "#d6d6d6";
  g.lineWidth = 6;
  g.beginPath();
  g.moveTo(40, 40);
  g.lineTo(420, 50);
  g.lineTo(400, 260);
  g.moveTo(40, 40);
  g.lineTo(60, 280);
  g.moveTo(60, 160);
  g.lineTo(400, 150);
  g.stroke();
  c.toBlob(async (blob) => {
    file = new File([blob], "sketch.png", { type: "image/png" });
    await extract(file);
  });
};

async function extract(imageFile) {
  status.textContent = "Ανάλυση…";
  const fd = new FormData();
  fd.append("image", imageFile);
  fd.append("tolerance", document.getElementById("tol").value);
  const gcp = document.getElementById("gcp").value.trim();
  if (gcp) fd.append("gcps", gcp);
  const res = await fetch("/api/vision/extract", { method: "POST", body: fd });
  const data = await res.json();
  if (!res.ok) {
    status.textContent = data.error || "Σφάλμα";
    return;
  }
  status.textContent = `${data.lineCount} γραμμές · ${data.geojson.features.length} διανύσματα`;
  document.getElementById("out").textContent = JSON.stringify(data.geojson.features.slice(0, 8), null, 2);
  await drawResult(imageFile, data.geojson);
}

async function drawResult(imageFile, geojson) {
  const bmp = await createImageBitmap(imageFile);
  canvas.width = bmp.width;
  canvas.height = bmp.height;
  ctx.drawImage(bmp, 0, 0);
  ctx.strokeStyle = "#f5c518";
  ctx.lineWidth = 2;
  for (const f of geojson.features) {
    const coords = f.geometry.coordinates;
    ctx.beginPath();
    coords.forEach((c, i) => {
      const x = geojson.properties.space === "wgs84" ? null : c[0];
      const y = geojson.properties.space === "wgs84" ? null : c[1];
      if (x == null) return;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }
}
