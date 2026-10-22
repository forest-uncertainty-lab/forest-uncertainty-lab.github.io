"use strict";

const DATA = "../data/";
const NS = "http://www.w3.org/2000/svg";
const ORDER = ["other", "static_suspect", "volcano"];
const LABEL = { other: "Titik panas lain", static_suspect: "Dugaan sumber panas tetap/industri", volcano: "Gunung api" };
const CONFIDENCE = { l: "rendah", n: "sedang", h: "tinggi" };
const nf0 = new Intl.NumberFormat("id-ID");
const nf1 = new Intl.NumberFormat("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const css = getComputedStyle(document.documentElement);
const cssVar = (name) => css.getPropertyValue(name).trim();
const COLOR = { other: cssVar("--fire"), static_suspect: cssVar("--static"), volcano: cssVar("--volcano") };
const state = { window: "7d" };

function setAttrs(node, attrs) {
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined || value === false) continue;
    node.setAttribute(key, value === true ? "" : String(value));
  }
}

function h(tag, attrs, ...kids) {
  const node = document.createElement(tag);
  setAttrs(node, attrs);
  node.append(...kids.flat().filter((k) => k !== null && k !== undefined && k !== false));
  return node;
}

function s(tag, attrs, ...kids) {
  const node = document.createElementNS(NS, tag);
  setAttrs(node, attrs);
  node.append(...kids.flat().filter((k) => k !== null && k !== undefined && k !== false));
  return node;
}

function esc(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

async function load(name) {
  const response = await fetch(DATA + name, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${name}: HTTP ${response.status}`);
  return response.json();
}

function witaTime(iso) {
  const text = new Date(iso).toLocaleString("id-ID", {
    timeZone: "Asia/Makassar", day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
  return `${text} WITA`;
}

function shortDay(isoDate) {
  return new Date(`${isoDate}T12:00:00+08:00`).toLocaleDateString("id-ID", { timeZone: "Asia/Makassar", day: "numeric", month: "short" });
}

const noData = (c) => c.days > 0 && c.missing === c.days;

function coverageNote(c) {
  if (noData(c)) return "Tidak ada data satelit untuk periode ini.";
  if (c.complete === c.days) return `Data satelit lengkap untuk ${c.days} hari.`;
  const parts = [`Data lengkap ${c.complete} dari ${c.days} hari`];
  if (c.partial) parts.push(`${c.partial} hari sebagian`);
  if (c.missing) parts.push(`${c.missing} hari tanpa data`);
  return `${parts.join(", ")}. Jumlah sebenarnya bisa lebih tinggi.`;
}

function renderStatus(status) {
  const target = document.getElementById("status");
  if (!status) {
    target.textContent = "Status pembaruan tidak tersedia.";
    return;
  }
  if (status.status === "update_failed") {
    target.className = "status warn";
    target.textContent = status.last_success
      ? `Pembaruan terakhir gagal (${witaTime(status.last_attempt)}). Data yang tampil berasal dari ${witaTime(status.last_success)} dan mungkin sudah lama.`
      : `Pembaruan gagal (${witaTime(status.last_attempt)}). Belum ada data yang berhasil diambil.`;
    return;
  }
  const lagging = Object.values(status.sensors || {}).filter((v) => v.status !== "ok").map((v) => v.name);
  target.textContent = `Diperbarui ${witaTime(status.last_success)}.`
    + (lagging.length ? ` Data ${lagging.join(", ")} tidak lengkap pada pembaruan ini.` : "");
  if (lagging.length) target.className = "status warn";
}

const focusCounts = (win, focus) => win.provinces.find((p) => p.name === focus).counts;

function renderTallies(win, focus) {
  document.getElementById("window-label").textContent = win.label;
  document.getElementById("coverage-note").textContent = coverageNote(win.coverage);
  const counts = focusCounts(win, focus);
  const empty = noData(win.coverage);
  const target = document.getElementById("tallies");
  target.replaceChildren(...ORDER.map((key) => h("div", { class: `tally tally-${key}` },
    h("span", { class: "tally-num" }, empty ? "–" : nf0.format(counts[key])),
    h("span", { class: "tally-label" }, LABEL[key]))));
  if (!empty && counts.all === 0) {
    target.append(h("p", { class: "quiet" }, "Tidak ada deteksi yang dilaporkan dalam periode ini."));
  }
  renderSplit(counts, empty);
}

function renderSplit(counts, empty) {
  const target = document.getElementById("split");
  if (empty || counts.all === 0) {
    target.replaceChildren(h("div", { class: `split-bar${empty ? " no-data" : ""}`, "aria-hidden": "true" }));
    return;
  }
  const segments = ORDER.filter((k) => counts[k] > 0).map((k) =>
    h("span", { class: `split-${k}`, style: `flex-grow:${counts[k]}`, title: `${LABEL[k]}: ${nf0.format(counts[k])}` }));
  target.replaceChildren(
    h("div", { class: "split-bar", "aria-hidden": "true" }, segments),
    h("p", { class: "split-caption" }, `Total ${nf0.format(counts.all)} deteksi, semuanya ditampilkan dan dipisah menurut jenis sumber panas.`));
}

function renderDistricts(win) {
  const target = document.getElementById("districts");
  if (noData(win.coverage)) {
    target.replaceChildren(h("p", { class: "quiet" }, "Tidak ada data untuk periode ini."));
    return;
  }
  if (!win.focus_districts.length) {
    target.replaceChildren(h("p", { class: "quiet" }, "Tidak ada deteksi yang dilaporkan dalam periode ini."));
    return;
  }
  const head = h("tr", {}, h("th", { scope: "col" }, "Kabupaten/kota"),
    ...ORDER.map((k) => h("th", { scope: "col", class: "num" }, LABEL[k])));
  const rows = win.focus_districts.map((d) => h("tr", {}, h("th", { scope: "row" }, d.district),
    ...ORDER.map((k) => h("td", { class: "num" }, nf0.format(d.counts[k])))));
  target.replaceChildren(h("div", { class: "table-scroll" }, h("table", {}, h("thead", {}, head), h("tbody", {}, rows))));
}

function renderCompare(win, focus) {
  const target = document.getElementById("compare");
  if (noData(win.coverage)) {
    target.replaceChildren(h("li", { class: "quiet" }, "Tidak ada data untuk periode ini."));
    return;
  }
  const rows = win.provinces.map((p) => {
    const k = 1000 / p.area_km2;
    return { p, other: p.counts.other * k, fixed: (p.counts.static_suspect + p.counts.volcano) * k };
  }).sort((a, b) => b.other - a.other || a.p.name.localeCompare(b.p.name));
  const max = Math.max(...rows.map((r) => r.other + r.fixed), 1e-9);
  const pct = (v) => `${(v / max) * 100}%`;
  target.replaceChildren(...rows.map(({ p, other, fixed }) => {
    const share = p.counts.all ? (p.counts.static_suspect + p.counts.volcano) / p.counts.all : 0;
    const note = share === 0 ? "" : share < 0.01 ? " · <1% sumber panas tetap" : ` · ${Math.round(share * 100)}% sumber panas tetap`;
    return h("li", { class: p.name === focus ? "focus" : null },
      h("span", { class: "bar-name" }, p.name),
      h("span", { class: "bar-track", "aria-hidden": "true" },
        h("span", { class: "bar-other", style: `width:${pct(other)}` }),
        h("span", { class: "bar-fixed", style: `width:${pct(fixed)}` })),
      h("span", { class: "bar-value" }, nf1.format(other), h("small", {}, note)));
  }));
}

function niceCeil(v) {
  const p = 10 ** Math.floor(Math.log10(v));
  for (const f of [1, 2, 2.5, 5, 10]) if (f * p >= v) return f * p;
  return 10 * p;
}

function renderDaily(now) {
  const target = document.getElementById("daily");
  const days = now.daily;
  const width = Math.max(target.clientWidth, 300);
  const height = 200;
  const m = { t: 10, r: 6, b: 26, l: 46 };
  const step = (width - m.l - m.r) / days.length;
  const totals = days.map((d) => (d.counts ? ORDER.reduce((sum, k) => sum + d.counts[k], 0) : 0));
  const top = niceCeil(Math.max(1, ...totals));
  const y = (v) => height - m.b - (v / top) * (height - m.t - m.b);
  const missing = days.filter((d) => !d.counts).length;
  const chart = s("svg", {
    width, height, viewBox: `0 0 ${width} ${height}`, role: "img",
    "aria-label": `Titik panas per hari di ${now.focus}, ${shortDay(days[0].date)} sampai ${shortDay(days[days.length - 1].date)}. ${missing} hari tanpa data.`,
  });
  chart.append(s("defs", {}, s("pattern", { id: "nodata", width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" },
    s("line", { x1: 0, y1: 0, x2: 0, y2: 6, class: "hatch" }))));
  for (let i = 0; i <= 4; i += 1) {
    const v = (top * i) / 4;
    chart.append(s("line", { x1: m.l, x2: width - m.r, y1: y(v), y2: y(v), class: "grid" }));
    chart.append(s("text", { x: m.l - 6, y: y(v), class: "tick", "text-anchor": "end", "dominant-baseline": "middle" }, nf0.format(v)));
  }
  days.forEach((d, i) => {
    const x = m.l + i * step + step * 0.12;
    const w = Math.max(step * 0.76, 1);
    if (!d.counts) {
      chart.append(s("rect", { x, y: m.t, width: w, height: height - m.t - m.b, fill: "url(#nodata)" },
        s("title", {}, `${shortDay(d.date)}: tidak ada data`)));
    } else {
      let base = 0;
      for (const key of ORDER) {
        const v = d.counts[key];
        if (!v) continue;
        chart.append(s("rect", { x, y: y(base + v), width: w, height: y(base) - y(base + v), class: `bar-${key}${d.coverage === "partial" ? " partial" : ""}` },
          s("title", {}, `${shortDay(d.date)}: ${nf0.format(v)} ${LABEL[key].toLowerCase()}`)));
        base += v;
      }
    }
    const day = Number(d.date.slice(8, 10));
    if (day === 1 || (day === 15 && step > 6)) {
      chart.append(s("text", { x: m.l + i * step, y: height - 8, class: "tick" }, shortDay(d.date)));
    }
  });
  target.replaceChildren(chart);
}

function sitePopup(p) {
  return `<strong>Dugaan sumber panas tetap</strong><br>${esc(p.district || "")}<br>`
    + `${nf0.format(p.detections)} deteksi pada ${p.calendar_months} bulan berbeda, ${p.years} tahun (2023–2025)`;
}

function pointPopup(p) {
  return `<strong>${esc(LABEL[p.category])}</strong><br>${esc(p.district || "")}<br>${witaTime(p.utc)}<br>`
    + `Satelit ${esc(p.sensor)} · keyakinan ${esc(CONFIDENCE[p.confidence] || p.confidence)}`;
}

function makeMap(provinces, districts, sites, focus) {
  const map = L.map("map", { preferCanvas: true, scrollWheelZoom: false });
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 17, className: "basemap",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">kontributor OpenStreetMap</a>',
  }).addTo(map);
  let focusLayer = null;
  if (provinces) {
    L.geoJSON(provinces, {
      style: (f) => ({ color: cssVar("--forest"), weight: f.properties.name === focus ? 2 : 0.8, opacity: f.properties.name === focus ? 0.9 : 0.35, fill: false }),
      onEachFeature: (f, layer) => { if (f.properties.name === focus) focusLayer = layer; },
      interactive: false,
    }).addTo(map);
  }
  if (districts) {
    L.geoJSON(districts, { style: { color: cssVar("--muted"), weight: 0.6, dashArray: "3 3", fill: false }, interactive: false }).addTo(map);
  }
  if (sites) {
    L.geoJSON(sites, {
      filter: (f) => f.properties.province === focus,
      pointToLayer: (f, latlng) => L.circleMarker(latlng, { radius: 7, color: COLOR.static_suspect, weight: 2, fillColor: "#ffffff", fillOpacity: 0.9 }),
      onEachFeature: (f, layer) => layer.bindPopup(sitePopup(f.properties)),
    }).addTo(map);
  }
  if (focusLayer) map.fitBounds(focusLayer.getBounds(), { padding: [12, 12] });
  else map.setView([-1.4, 121.4], 7);
  return { map, points: L.layerGroup().addTo(map) };
}

function inWindow(props, win, key) {
  if (key === "24h" || key === "7d") {
    const t = Date.parse(props.utc);
    return t > Date.parse(win.start) && t <= Date.parse(win.end);
  }
  return props.local_date >= win.start && props.local_date <= win.end;
}

function updatePoints(ctx, points, win, key) {
  ctx.points.clearLayers();
  if (!points) return;
  for (const f of points.features) {
    if (!inWindow(f.properties, win, key)) continue;
    const [lon, lat] = f.geometry.coordinates;
    const color = COLOR[f.properties.category];
    L.circleMarker([lat, lon], { radius: 4, color, weight: 1, fillColor: color, fillOpacity: 0.75 })
      .bindPopup(pointPopup(f.properties)).addTo(ctx.points);
  }
}

function renderSources(manifest, status) {
  const items = [];
  for (const v of Object.values((status && status.sensors) || {})) {
    items.push(h("li", {}, `NASA FIRMS, VIIRS ${v.name}, data hampir waktu nyata: `,
      v.last_success ? `diambil ${witaTime(v.last_success)}` : "belum berhasil diambil"));
  }
  if (manifest) {
    items.push(h("li", {}, `Penanda sumber panas tetap dan gunung api: arsip FIRMS VIIRS Suomi NPP ${manifest.rule.archive_years.join(", ")}, dibuat ${witaTime(manifest.built_at)}.`));
  }
  items.push(h("li", {}, "Batas provinsi dan kabupaten/kota: geoBoundaries (OpenStreetMap)."));
  document.getElementById("sources").replaceChildren(...items);
}

function setupButtons(onChange) {
  const buttons = [...document.querySelectorAll("#window-buttons button")];
  for (const button of buttons) {
    button.addEventListener("click", () => {
      state.window = button.dataset.window;
      for (const b of buttons) b.setAttribute("aria-pressed", String(b === button));
      onChange();
    });
  }
}

function debounce(fn, ms) {
  let timer;
  return () => { clearTimeout(timer); timer = setTimeout(fn, ms); };
}

async function main() {
  const names = ["now.json", "status.json", "focus_detections.geojson", "static_sites.geojson", "provinces.geojson", "districts_focus.geojson", "manifest.json"];
  const results = await Promise.allSettled(names.map(load));
  const [now, status, points, sites, provinces, districts, manifest] = results.map((r) => (r.status === "fulfilled" ? r.value : null));
  renderStatus(status);
  renderSources(manifest, status);
  if (!now) {
    for (const id of ["tallies", "districts", "daily", "compare", "map"]) {
      document.getElementById(id).replaceChildren(h("p", { class: "quiet" }, "Data tidak dapat dimuat."));
    }
    return;
  }
  const ctx = typeof L === "undefined" ? null : makeMap(provinces, districts, sites, now.focus);
  if (!ctx) document.getElementById("map").replaceChildren(h("p", { class: "quiet" }, "Peta tidak dapat dimuat."));
  const update = () => {
    const win = now.windows[state.window];
    renderTallies(win, now.focus);
    renderDistricts(win);
    renderCompare(win, now.focus);
    if (ctx) updatePoints(ctx, points, win, state.window);
  };
  setupButtons(update);
  update();
  renderDaily(now);
  window.addEventListener("resize", debounce(() => renderDaily(now), 150));
}

main();
