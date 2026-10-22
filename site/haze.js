// Haze tab: the air now, the last two days and the next three, where the air came from, and what is
// still unknown. Reads data/haze.json (refreshed every six hours) and data/land.json; the air numbers
// are refreshed live from NEA and Open-Meteo in the browser when they answer.
(() => {
  const panel = document.getElementById("tab-haze"), $ = id => document.getElementById(id);
  const LEVELS = [["925", "h925"], ["850", "h850"], ["700", "h700"]];
  const WHO_24H = 15;
  const PSI_BANDS = [[50, "good"], [100, "moderate"], [200, "unhealthy"], [300, "veryUnhealthy"], [Infinity, "hazardous"]];
  const REGIONS = ["north", "south", "east", "west", "central"];
  const OFFICIAL = {
    sg: ["https://www.haze.gov.sg/", "NEA haze advisory (Singapore)", "Imbauan kabut asap NEA (Singapura)"],
    my: ["https://eqms.doe.gov.my/APIMS/main", "APIMS air pollutant index (Malaysia)", "Indeks pencemar udara APIMS (Malaysia)"],
    id: ["https://ispu.menlhk.go.id/", "ISPU air quality index (Indonesia, KLHK)", "Indeks Standar Pencemar Udara ISPU (KLHK)"],
  };

  const T = {
    en: {
      title: c => `Haze over ${c}`,
      lede: "What is in the air now, where that air came from over the last two days, and what is still unknown.",
      hNow: "The air now", hTrend: "The last two days and the next three", hPath: "Where the air came from",
      pathSub: "Each colour traces the air that is over the city now back 48 hours at one height. The bold line is the central path, the thin lines the other eight variants with slightly different timing and wind. Dots are satellite fire detections from the last 48 hours.",
      pathCaveat: "A path that crosses fire detections shows where smoke could have been picked up. It does not establish a smoke source. These paths ignore rising and sinking air, mixing and rain, and smoke from one height can reach the ground at another.",
      hEvidence: "What we know, what we don't, and what would settle it", know: "Known", unknown: "Not known", settle: "Would settle it",
      hDo: "What to do", doSub: "Health advice comes from the agencies below. This page does not give its own.",
      hMethod: "How these numbers are made",
      measured: "Measured", estimate: "Model estimate",
      psiWhat: (v, r, band) => `24-hour PSI in the ${r} region, the highest of Singapore's five. NEA calls ${v} "${band}".`,
      estWhat: h => `Estimated PM2.5, particles up to 2.5 micrometres across, averaged of the last 24 hours, in micrograms per cubic metre. ${h} the WHO 24-hour guideline of ${WHO_24H}.`,
      times: x => x >= 1.5 ? `${x.toFixed(x >= 10 ? 0 : 1)} times` : (x >= 1 ? "Just above" : "Below"),
      noStation: c => `This page has no official station feed for ${c}. The number comes from a global model.`,
      regionsCap: "NEA readings at", region: "Region", psi24: "PSI, 24 h", pm1: "PM2.5, 1 h (µg/m³)",
      modelVs: (m, lo, hi) => `The model estimate for Singapore at the same hour was ${m} µg/m³; NEA stations read ${lo} to ${hi}.`,
      trackLine: (h, q) => `Over the last ${h} hours, NEA measured ${q[1].toFixed(2)} times the model's value (8 hours in 10 between ${q[0].toFixed(2)} and ${q[2].toFixed(2)} times).`,
      estNowLine: (m, t) => `The latest hourly estimate is ${m} µg/m³ at ${t}.`,
      regions: { north: "North", south: "South", east: "East", west: "West", central: "Central" },
      bands: { good: "Good", moderate: "Moderate", unhealthy: "Unhealthy", veryUnhealthy: "Very unhealthy", hazardous: "Hazardous" },
      trendSubSg: "Hourly PM2.5. The band is the range across NEA's five regions; the line is the model estimate, dashed where it is a forecast.",
      trendSub: "Hourly PM2.5 from the model, dashed where it is a forecast. This page has no station measurement to compare here.",
      lgModel: "Model estimate", lgForecast: "Model forecast", lgBand: "NEA stations, range of 5 regions", lgWho: "WHO 24-hour guideline (15)",
      lgFire: n => `Fire detection, last 48 h (${n.toLocaleString("en")})`, lgDots: "Dots on the bold line mark 12-hour steps", now: "now",
      tipModel: "Model", tipNea: "NEA range",
      level: { "925": "About 750 m up", "850": "About 1.5 km up", "700": "About 3 km up" },
      pathLine: (km, dir, stop) => stop ? `The central path leaves the map after ${stop} hours.` : `48 hours ago the air on the central path was ${km.toLocaleString("en")} km ${dir}.`,
      upwindLine: u => u.share === 0 ? "None of the nine paths passed a fire detection after leaving the city." :
        `${Math.round(u.share * 9)} of 9 paths passed within 50 km of fire detections after leaving the city; a typical path passed ${Math.round(u.median).toLocaleString("en")}, the most ${u.max.toLocaleString("en")}.`,
      dirs: ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"],
      k1sg: (lo, hi, t) => `NEA measured a 24-hour PSI of ${lo} to ${hi} across Singapore at ${t}.`,
      k1: c => `This page uses a model estimate for ${c} because it has no station feed for this city.`,
      k2: (n, t) => `Satellites recorded ${n.toLocaleString("en")} fire detections in the map area in the 48 hours to ${t}.`,
      k3: "The wind paths are computed from model winds hour by hour, nine variants per height.",
      u1: km => `The height carrying the air people breathe is uncertain. The three central paths were up to ${km.toLocaleString("en")} km apart 48 hours earlier.`,
      u2: "How many detections were burning vegetation. Known volcanoes and industrial sites are left out, but a smelter or flare that started recently is not flagged until the masks are rebuilt.",
      u3sg: q => `The model has a measured error. NEA has measured ${q[1].toFixed(2)} times the model's value in Singapore lately, and the gap varies from hour to hour.`,
      u3: "This page has no station measurement here to check the model against.",
      s1: "The next satellite passes, around 01:30 and 13:30 local time, show whether the fires upwind are still burning.",
      s2: c => `A smoke-transport model run from these fires (HYSPLIT, for example) would show whether their smoke reaches ${c}, and how much.`,
      s3: "A ground station upwind would let us check the model close to the detections. This page has not integrated those readings.",
      method: [
        ["Measurements in Singapore", "NEA publishes the 24-hour PSI and 1-hour PM2.5 for five regions every hour on data.gov.sg. This page integrates that feed; it has not yet integrated official feeds for the other cities."],
        ["Model estimates", "The model estimate comes from CAMS, the global air-quality forecast run by ECMWF for the EU's Copernicus programme, read through Open-Meteo. CAMS works on a grid of about 45 km, so one value covers a whole city. The global model updates every 12 hours and forecasts five days ahead. Open-Meteo supplies values at hourly intervals from its underlying three-hourly output. The page does not correct it against local stations. Forecasts can differ from later measurements."],
        ["The model's track record", "On each refresh, the pipeline pairs NEA's mean of the five regions with the model's value for the same hour and keeps 30 days of pairs. It reports the middle ratio and the range of 8 hours in 10. That record holds for Singapore only; it says nothing about the model's error near the fires, where this page has no station feed."],
        ["Wind paths", "From the city at the latest hour, each path steps back one hour at a time against the model wind at a fixed pressure level. The levels are 925 hPa (about 750 m), 850 hPa (about 1.5 km) and 700 hPa (about 3 km). Winds are hourly Open-Meteo values on a 1-degree grid, interpolated between grid points. Nine variants per height start 0, 1 or 2 hours earlier and use the wind as given, 10% weaker turned 10 degrees one way, or 10% stronger turned the other way. The method ignores vertical motion, turbulence and rain. These paths provide a rough guide to direction. When the heights or the variants disagree, the source is uncertain."],
        ["Fires along the paths", "NASA FIRMS VIIRS detections from Suomi NPP, NOAA-20 and NOAA-21 at 375 m over the last 48 hours, without known volcanoes and industrial sites, counted in cells of 0.02 degrees. A path passes a detection when any of its points from the third hour on lies within 50 km of it; the first hours are left out so fires around the city itself do not count for every path. A detection is a hot pixel, not a confirmed fire."],
        ["Times", "Times are local to the selected city (SGT, MYT, WIB or WITA)."],
      ],
      snapshot: t => `Data from ${t}.`, liveAt: t => `Air numbers refreshed live at ${t}.`, noPaths: "Wind paths are unavailable in this snapshot. Fire detections remain visible on the map.", noData: "The haze data could not be loaded. Reload the page or download haze.json from the footer.",
    },
    id: {
      title: c => `Kabut asap di ${c}`,
      lede: "Apa yang ada di udara sekarang, dari mana udara itu datang selama dua hari terakhir, dan apa yang belum diketahui.",
      hNow: "Udara saat ini", hTrend: "Dua hari terakhir dan tiga hari ke depan", hPath: "Dari mana udara ini datang",
      pathSub: "Setiap warna menelusuri udara yang kini berada di atas kota, mundur 48 jam pada satu ketinggian. Garis tebal adalah lintasan tengah, garis tipis delapan varian lainnya dengan waktu dan angin yang sedikit berbeda. Titik adalah deteksi api satelit dalam 48 jam terakhir.",
      pathCaveat: "Lintasan yang melewati deteksi api menunjukkan di mana asap bisa terbawa, bukan bahwa asap memang terbawa. Lintasan ini mengabaikan udara yang naik dan turun, percampuran, dan hujan, dan asap dari satu ketinggian bisa turun ke tanah di ketinggian lain.",
      hEvidence: "Yang kita tahu, yang belum, dan yang bisa memastikannya", know: "Diketahui", unknown: "Belum diketahui", settle: "Bisa memastikan",
      hDo: "Yang bisa dilakukan", doSub: "Saran kesehatan datang dari lembaga di bawah ini. Halaman ini tidak memberi sarannya sendiri.",
      hMethod: "Cara angka ini dibuat",
      measured: "Hasil ukur", estimate: "Perkiraan model",
      psiWhat: (v, r, band) => `PSI 24 jam di wilayah ${r}, tertinggi dari lima wilayah Singapura. NEA menggolongkan ${v} sebagai "${band}".`,
      estWhat: h => `Perkiraan PM2.5, yaitu partikel berdiameter paling besar 2,5 mikrometer, dengan rata-rata 24 jam terakhir, dalam mikrogram per meter kubik. ${h} pedoman 24 jam WHO sebesar ${WHO_24H}.`,
      times: x => x >= 1.5 ? `${x.toFixed(x >= 10 ? 0 : 1).replace(".", ",")} kali` : (x >= 1 ? "Sedikit di atas" : "Di bawah"),
      noStation: c => `Halaman ini belum memakai data stasiun resmi untuk ${c}. Angka ini berasal dari model global.`,
      regionsCap: "Bacaan NEA pukul", region: "Wilayah", psi24: "PSI, 24 jam", pm1: "PM2.5, 1 jam (µg/m³)",
      modelVs: (m, lo, hi) => `Perkiraan model untuk Singapura pada jam yang sama adalah ${m} µg/m³; stasiun NEA membaca ${lo} sampai ${hi}.`,
      trackLine: (h, q) => `Selama ${h} jam terakhir, NEA mengukur ${q[1].toFixed(2).replace(".", ",")} kali nilai model (8 dari 10 jam antara ${q[0].toFixed(2).replace(".", ",")} dan ${q[2].toFixed(2).replace(".", ",")} kali).`,
      estNowLine: (m, t) => `Perkiraan per jam terbaru sebesar ${m} µg/m³ pukul ${t}.`,
      regions: { north: "Utara", south: "Selatan", east: "Timur", west: "Barat", central: "Tengah" },
      bands: { good: "Baik", moderate: "Sedang", unhealthy: "Tidak sehat", veryUnhealthy: "Sangat tidak sehat", hazardous: "Berbahaya" },
      trendSubSg: "PM2.5 per jam. Pita adalah rentang lima wilayah NEA; garis adalah perkiraan model, putus-putus bila berupa prakiraan.",
      trendSub: "PM2.5 per jam dari model, putus-putus bila berupa prakiraan. Halaman ini belum memakai hasil ukur stasiun untuk dibandingkan.",
      lgModel: "Perkiraan model", lgForecast: "Prakiraan model", lgBand: "Stasiun NEA, rentang 5 wilayah", lgWho: "Pedoman 24 jam WHO (15)",
      lgFire: n => `Deteksi api, 48 jam terakhir (${n.toLocaleString("id")})`, lgDots: "Titik pada garis tebal menandai tiap 12 jam", now: "kini",
      tipModel: "Model", tipNea: "Rentang NEA",
      level: { "925": "Sekitar 750 m", "850": "Sekitar 1,5 km", "700": "Sekitar 3 km" },
      pathLine: (km, dir, stop) => stop ? `Lintasan tengah keluar dari peta setelah ${stop} jam.` : `48 jam lalu udara pada lintasan tengah berada ${km.toLocaleString("id")} km ke arah ${dir}.`,
      upwindLine: u => u.share === 0 ? "Tidak satu pun dari sembilan lintasan melewati deteksi api setelah meninggalkan kota." :
        `${Math.round(u.share * 9)} dari 9 lintasan lewat dalam jarak 50 km dari deteksi api setelah meninggalkan kota; lintasan yang khas melewati ${Math.round(u.median).toLocaleString("id")}, paling banyak ${u.max.toLocaleString("id")}.`,
      dirs: ["utara", "timur laut", "timur", "tenggara", "selatan", "barat daya", "barat", "barat laut"],
      k1sg: (lo, hi, t) => `NEA mengukur PSI 24 jam sebesar ${lo} sampai ${hi} di seluruh Singapura pukul ${t}.`,
      k1: c => `Halaman ini memakai perkiraan model untuk ${c} karena belum memakai data stasiun kota ini.`,
      k2: (n, t) => `Satelit mencatat ${n.toLocaleString("id")} deteksi api di area peta dalam 48 jam sampai pukul ${t}.`,
      k3: "Lintasan angin dihitung dari angin model jam demi jam, sembilan varian per ketinggian.",
      u1: km => `Ketinggian yang membawa udara yang dihirup warga belum pasti. Tiga lintasan tengah berjarak hingga ${km.toLocaleString("id")} km pada 48 jam sebelumnya.`,
      u2: "Berapa deteksi yang benar-benar vegetasi terbakar. Gunung api dan lokasi industri yang dikenal tidak dihitung, tetapi smelter atau suar gas yang baru beroperasi belum ditandai sampai masker dibangun ulang.",
      u3sg: q => `Model memiliki kesalahan terukur. Akhir-akhir ini NEA mengukur ${q[1].toFixed(2).replace(".", ",")} kali nilai model di Singapura, dan selisihnya berubah dari jam ke jam.`,
      u3: "Halaman ini belum memakai hasil ukur stasiun di sini untuk memeriksa model.",
      s1: "Lintasan satelit berikutnya, sekitar pukul 01.30 dan 13.30 waktu setempat, menunjukkan apakah api di arah datangnya angin masih menyala.",
      s2: c => `Model sebaran asap dari api-api ini (misalnya HYSPLIT) akan menunjukkan apakah asapnya sampai ke ${c}, dan seberapa banyak.`,
      s3: "Stasiun darat di arah datangnya angin memungkinkan pemeriksaan model di dekat deteksi. Halaman ini belum memakai bacaan tersebut.",
      method: [
        ["Hasil ukur di Singapura", "NEA menerbitkan PSI 24 jam dan PM2.5 1 jam untuk lima wilayah setiap jam di data.gov.sg. Halaman ini memakai data tersebut dan belum memakai data resmi untuk kota lain."],
        ["Perkiraan model", "Perkiraan model berasal dari CAMS, prakiraan kualitas udara global yang dijalankan ECMWF untuk program Copernicus Uni Eropa, dibaca melalui Open-Meteo. CAMS bekerja pada grid sekitar 45 km, jadi satu nilai mewakili satu kota. Model global diperbarui tiap 12 jam dan memprakirakan lima hari ke depan. Open-Meteo menyediakan nilai per jam dari keluaran dasarnya yang berjarak tiga jam. Halaman ini tidak mengoreksinya terhadap stasiun setempat. Prakiraan dapat berbeda dari hasil ukur kemudian."],
        ["Rekam jejak model", "Pada setiap pembaruan, pipeline memasangkan rata-rata lima wilayah NEA dengan nilai model pada jam yang sama dan menyimpan pasangan selama 30 hari. Yang dilaporkan adalah rasio tengah dan rentang 8 dari 10 jam. Rekam jejak ini hanya berlaku untuk Singapura; ia tidak mengatakan apa-apa tentang kesalahan model di dekat api, tempat halaman ini belum memakai data stasiun."],
        ["Lintasan angin", "Dari kota pada jam terbaru, setiap lintasan mundur satu jam demi satu jam melawan angin model pada satu tingkat tekanan. Tingkatnya adalah 925 hPa (sekitar 750 m), 850 hPa (sekitar 1,5 km), dan 700 hPa (sekitar 3 km). Angin adalah nilai per jam Open-Meteo pada grid 1 derajat, diinterpolasi antartitik grid. Sembilan varian per ketinggian dimulai 0, 1, atau 2 jam lebih awal dan memakai angin apa adanya, 10% lebih lemah dan berbelok 10 derajat ke satu arah, atau 10% lebih kuat dan berbelok ke arah lain. Metode ini mengabaikan gerak vertikal, turbulensi, dan hujan. Lintasan ini memberi petunjuk kasar arah. Bila ketinggian atau varian tidak sepakat, sumbernya belum pasti."],
        ["Api di sepanjang lintasan", "Deteksi VIIRS NASA FIRMS dari Suomi NPP, NOAA-20, dan NOAA-21 pada resolusi 375 m selama 48 jam terakhir, tanpa gunung api dan lokasi industri yang dikenal, dihitung dalam sel 0,02 derajat. Lintasan dianggap melewati deteksi bila salah satu titiknya mulai jam ketiga berada dalam jarak 50 km; jam-jam pertama tidak dihitung supaya api di sekitar kota tidak terhitung untuk setiap lintasan. Deteksi adalah piksel panas, bukan kebakaran yang terkonfirmasi."],
        ["Waktu", "Waktu mengikuti kota yang dipilih (SGT, MYT, WIB, atau WITA)."],
      ],
      snapshot: t => `Data dari ${t}.`, liveAt: t => `Angka udara diperbarui langsung pukul ${t}.`, noPaths: "Lintasan angin tidak tersedia pada cuplikan ini. Deteksi api tetap terlihat pada peta.", noData: "Data kabut asap tidak dapat dimuat. Muat ulang halaman atau unduh haze.json di bagian bawah.",
    },
  };

  let lang = "en", city = "singapore", SNAP = null, LAND = null, loading = null;
  const live = { cams: {}, nea: null, at: null };
  const t = () => T[lang];
  const cities = () => Object.fromEntries(SNAP.cities.map(c => [c.key, c]));
  const svgEl = (tag, attrs, text) => { const e = document.createElementNS("http://www.w3.org/2000/svg", tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (text != null) e.textContent = text; return e; };
  const fmtTime = (d, c) => {
    const x = new Date(d.getTime() + c.utc_offset * 3600e3);
    const hh = String(x.getUTCHours()).padStart(2, "0"), mm = String(x.getUTCMinutes()).padStart(2, "0");
    return `${lang === "id" ? `${hh}.${mm}` : `${hh}:${mm}`} ${c.tz}`;
  };
  const fmtDay = (d, c) => new Date(d.getTime() + c.utc_offset * 3600e3)
    .toLocaleDateString(lang === "id" ? "id-ID" : "en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });
  const km = (a, b) => { const r = Math.PI / 180, dLa = (b[1] - a[1]) * r, dLo = (b[0] - a[0]) * r;
    const h = Math.sin(dLa / 2) ** 2 + Math.cos(a[1] * r) * Math.cos(b[1] * r) * Math.sin(dLo / 2) ** 2; return 6371 * 2 * Math.asin(Math.sqrt(h)); };
  const bearing = (a, b) => { const r = Math.PI / 180, y = Math.sin((b[0] - a[0]) * r) * Math.cos(b[1] * r),
    x = Math.cos(a[1] * r) * Math.sin(b[1] * r) - Math.sin(a[1] * r) * Math.cos(b[1] * r) * Math.cos((b[0] - a[0]) * r);
    return (Math.atan2(y, x) / r + 360) % 360; };
  const now = () => new Date();

  async function getJSON(url) { const r = await fetch(url, { cache: "no-cache" }); if (!r.ok) throw new Error(r.status); return r.json(); }
  function load() {
    loading = loading || Promise.all([getJSON("data/haze.json"), getJSON("data/land.json")]).then(([s, l]) => { SNAP = s; LAND = l; });
    return loading;
  }

  function camsSeries(key) {
    const s = live.cams[key] || (SNAP.cams || {})[key];
    return s ? s.time.map((tt, i) => ({ t: new Date(tt + "Z"), v: s.pm2_5[i] })).filter(p => p.v != null) : [];
  }
  const neaData = () => live.nea || SNAP.nea;
  const neaRows = () => (neaData() ? neaData().pm25_hourly.map(r => ({ t: new Date(r.time), lo: r.lo, hi: r.hi, mean: r.mean })) : []);
  const latestModel = key => { const s = camsSeries(key).filter(p => p.t <= now()); return s[s.length - 1]; };

  async function refreshLive(key) {
    const c = cities()[key];
    try {
      const url = `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${c.lat}&longitude=${c.lon}&hourly=pm2_5&past_days=2&forecast_days=3&timezone=GMT`;
      const j = await getJSON(url);
      live.cams[key] = { time: j.hourly.time, pm2_5: j.hourly.pm2_5 };
      live.at = new Date();
    } catch (e) { /* the snapshot stays */ }
    if (key === "singapore" && !live.nea) {
      try {
        const sgt = new Date(Date.now() + 8 * 3600e3), day = d => d.toISOString().slice(0, 10);
        const [today, yesterday, psi] = await Promise.all([
          getJSON(`https://api-open.data.gov.sg/v2/real-time/api/pm25?date=${day(sgt)}`),
          getJSON(`https://api-open.data.gov.sg/v2/real-time/api/pm25?date=${day(new Date(sgt - 864e5))}`),
          getJSON("https://api-open.data.gov.sg/v2/real-time/api/psi"),
        ]);
        const hourly = {};
        for (const item of [...yesterday.data.items, ...today.data.items]) {
          const regions = Object.fromEntries(Object.entries(item.readings.pm25_one_hourly).filter(([, v]) => v != null));
          const values = Object.values(regions);
          if (values.length) hourly[item.timestamp] = { time: item.timestamp, lo: Math.min(...values), hi: Math.max(...values),
            mean: values.reduce((a, b) => a + b, 0) / values.length, regions };
        }
        const latest = psi.data.items[0];
        live.nea = { pm25_hourly: Object.values(hourly).sort((a, b) => a.time.localeCompare(b.time)).slice(-48),
          psi_time: latest.timestamp, psi_24h: latest.readings.psi_twenty_four_hourly, pm25_24h: latest.readings.pm25_twenty_four_hourly };
        live.at = new Date();
      } catch (e) { /* the snapshot stays */ }
    }
    if (!panel.hidden && city === key) render();
  }

  function renderStatic() {
    panel.querySelectorAll("[data-t]").forEach(e => { const v = t()[e.dataset.t]; if (typeof v === "string") e.textContent = v; });
    $("hzCities").setAttribute("aria-label", lang === "id" ? "Pilih kota" : "Pick a city");
    $("hzCities").replaceChildren(...SNAP.cities.map(c => {
      const b = document.createElement("button"); b.type = "button"; b.textContent = c.name; b.setAttribute("aria-pressed", String(c.key === city));
      b.onclick = () => { city = c.key; render(); refreshLive(c.key); }; return b;
    }));
    $("hzMethod").innerHTML = t().method.map(([h, d]) => `<dt>${h}</dt><dd>${d}</dd>`).join("");
  }

  function renderNow() {
    const c = cities()[city], hero = $("hzHero"), side = $("hzSide"), nea = neaData();
    if (city === "singapore" && nea) {
      const top = Object.entries(nea.psi_24h).sort((a, b) => b[1] - a[1])[0];
      const band = PSI_BANDS.find(b => top[1] <= b[0])[1];
      hero.innerHTML = `<div><span class="num">${top[1]}</span><span class="unit">PSI</span></div>
        <p class="what">${t().psiWhat(top[1], t().regions[top[0]].toLowerCase(), t().bands[band])}</p>
        <span class="kind">${t().measured} · NEA · ${fmtTime(new Date(nea.psi_time), c)}</span>`;
      const last = nea.pm25_hourly[nea.pm25_hourly.length - 1], model = latestModel(city);
      side.innerHTML = `<table class="regions"><caption class="meta" style="text-align:left;caption-side:top;margin:0 0 .4rem">${t().regionsCap} ${fmtTime(new Date(last.time), c)}</caption>
        <thead><tr><th>${t().region}</th><th>${t().psi24}</th><th>${t().pm1}</th></tr></thead><tbody>${
        REGIONS.map(k => `<tr><td>${t().regions[k]}</td><td>${nea.psi_24h[k] ?? "–"}</td><td>${last.regions[k] ?? "–"}</td></tr>`).join("")}</tbody></table>
        ${model ? `<p class="meta">${t().modelVs(model.v.toFixed(0), last.lo, last.hi)}</p>` : ""}
        ${SNAP.track ? `<p class="meta">${t().trackLine(SNAP.track.hours, SNAP.track.ratio)}</p>` : ""}`;
    } else {
      const s = camsSeries(city).filter(p => p.t <= now() && p.t > new Date(now() - 24 * 3600e3)), model = latestModel(city);
      if (!s.length) { hero.innerHTML = `<p>${t().noData}</p>`; side.innerHTML = ""; return; }
      const mean = s.reduce((a, p) => a + p.v, 0) / s.length;
      hero.innerHTML = `<div><span class="num">${Math.round(mean)}</span><span class="unit">µg/m³</span></div>
        <p class="what">${t().estWhat(t().times(mean / WHO_24H))}</p>
        <span class="kind estimate">${t().estimate} · CAMS</span>`;
      side.innerHTML = `<p>${t().noStation(c.name)}</p>${model ? `<p class="meta">${t().estNowLine(model.v.toFixed(0), fmtTime(model.t, c))}</p>` : ""}`;
    }
  }

  function renderChart() {
    const c = cities()[city], svg = $("hzChart"), W = 1000, H = 310, m = { l: 48, r: 16, t: 28, b: 34 };
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.replaceChildren();
    const x0 = new Date(now() - 48 * 3600e3), x1 = new Date(+now() + 72 * 3600e3);
    const model = camsSeries(city).filter(p => p.t >= x0 && p.t <= x1);
    const band = city === "singapore" ? neaRows().filter(p => p.t >= x0) : [];
    if (!model.length) return;
    const yMax = Math.max(WHO_24H * 2, ...model.map(p => p.v), ...band.map(p => p.hi)) * 1.08;
    const X = d => m.l + (d - x0) / (x1 - x0) * (W - m.l - m.r), Y = v => H - m.b - v / yMax * (H - m.t - m.b);
    const step = [10, 20, 25, 50, 100, 200, 250, 500].find(s => yMax / s <= 5) || 1000;
    for (let v = 0; v <= yMax; v += step) {
      svg.append(svgEl("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), stroke: "var(--line)" }));
      svg.append(svgEl("text", { x: m.l - 8, y: Y(v) + 4, "text-anchor": "end", "font-size": 12, fill: "var(--muted)" }, v));
    }
    for (let h = -48; h <= 72; h += 24) {
      const d = new Date(+now() + h * 3600e3);
      svg.append(svgEl("text", { x: X(d), y: H - 10, "text-anchor": h === -48 ? "start" : h === 72 ? "end" : "middle", "font-size": 12, fill: "var(--muted)" }, h === 0 ? t().now : fmtDay(d, c)));
    }
    svg.append(svgEl("text", { x: 4, y: 4, "font-size": 12, fill: "var(--muted)", "dominant-baseline": "hanging" }, "µg/m³"));
    svg.append(svgEl("line", { x1: m.l, x2: W - m.r, y1: Y(WHO_24H), y2: Y(WHO_24H), stroke: "var(--guide)", "stroke-dasharray": "2 4", "stroke-width": 1.5 }));
    svg.append(svgEl("text", { x: W - m.r, y: Y(WHO_24H) - 6, "text-anchor": "end", "font-size": 12, fill: "var(--muted)" }, "WHO 15"));
    if (band.length) {
      const d = band.map((p, i) => `${i ? "L" : "M"}${X(p.t)},${Y(p.hi)}`).join("") + band.slice().reverse().map(p => `L${X(p.t)},${Y(p.lo)}`).join("") + "Z";
      svg.append(svgEl("path", { d, fill: "var(--band)" }));
    }
    const past = model.filter(p => p.t <= now()), fut = model.filter(p => p.t >= now());
    const line = pts => pts.map((p, i) => `${i ? "L" : "M"}${X(p.t)},${Y(p.v)}`).join("");
    svg.append(svgEl("path", { d: line(past), fill: "none", stroke: "var(--model)", "stroke-width": 2, "stroke-linejoin": "round" }));
    svg.append(svgEl("path", { d: line(fut), fill: "none", stroke: "var(--model)", "stroke-width": 2, "stroke-dasharray": "6 5" }));
    svg.append(svgEl("line", { x1: X(now()), x2: X(now()), y1: m.t, y2: H - m.b, stroke: "var(--muted)", "stroke-width": 1 }));
    if (fut.length) {
      const peak = fut.reduce((a, p) => p.v > a.v ? p : a, fut[0]);
      svg.append(svgEl("circle", { cx: X(peak.t), cy: Y(peak.v), r: 4, fill: "var(--model)", stroke: "var(--surface)", "stroke-width": 2 }));
      svg.append(svgEl("text", { x: X(peak.t), y: Y(peak.v) - 10, "text-anchor": "middle", "font-size": 12, fill: "var(--text)", "font-weight": 700 }, `${Math.round(peak.v)}`));
    }
    svg.setAttribute("aria-label", `${t().hTrend}. ${t().lgModel}.`);
    const cross = svgEl("line", { y1: m.t, y2: H - m.b, stroke: "var(--text)", "stroke-width": 1, opacity: 0 }); svg.append(cross);
    const hit = svgEl("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "transparent" }); svg.append(hit);
    const tip = $("hzChartTip");
    hit.onmousemove = ev => {
      const r = svg.getBoundingClientRect(), fx = (ev.clientX - r.left) / r.width * W;
      const d = new Date(+x0 + (fx - m.l) / (W - m.l - m.r) * (x1 - x0));
      const p = model.reduce((a, q) => Math.abs(q.t - d) < Math.abs(a.t - d) ? q : a, model[0]);
      const b = band.find(q => Math.abs(q.t - p.t) < 1800e3);
      cross.setAttribute("x1", X(p.t)); cross.setAttribute("x2", X(p.t)); cross.setAttribute("opacity", .5);
      tip.innerHTML = `<b>${fmtDay(p.t, c)} ${fmtTime(p.t, c)}</b><br>${t().tipModel} · ${p.v.toFixed(0)} µg/m³${b ? `<br>${t().tipNea} · ${b.lo}–${b.hi}` : ""}`;
      tip.style.display = "block"; tip.style.left = `${Math.min(ev.clientX - r.left + 14, r.width - 170)}px`; tip.style.top = `${ev.clientY - r.top + 10}px`;
    };
    hit.onmouseleave = () => { tip.style.display = "none"; cross.setAttribute("opacity", 0); };
    $("hzTrendSub").textContent = city === "singapore" ? t().trendSubSg : t().trendSub;
    $("hzChartLegend").innerHTML = `<li><span class="sw"></span>${t().lgModel}</li><li><span class="sw dash"></span>${t().lgForecast}</li>${
      band.length ? `<li><span class="sw band"></span>${t().lgBand}</li>` : ""}<li><span class="sw dash" style="border-top-color:var(--guide)"></span>${t().lgWho}</li>`;
  }

  function geo() {
    const [w, s, e, n] = SNAP.map_bbox, S = 24;
    return { MW: (e - w) * S, MH: (n - s) * S, X: lon => (lon - w) * S, Y: lat => (n - lat) * S };
  }
  function drawFires() {
    const cv = $("hzFires"), wrap = $("hzMapWrap"), dpr = window.devicePixelRatio || 1, g = geo();
    cv.width = wrap.clientWidth * dpr; cv.height = wrap.clientHeight * dpr;
    const ctx = cv.getContext("2d"), k = cv.width / g.MW;
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--fire"); ctx.globalAlpha = .6;
    for (const [lon, lat, cnt] of SNAP.fires.points) {
      ctx.beginPath(); ctx.arc(g.X(lon) * k, g.Y(lat) * k, Math.min(1.1 + Math.sqrt(cnt) * .45, 3.2) * dpr, 0, 6.283); ctx.fill();
    }
  }
  function renderMap() {
    const g = geo(), svg = $("hzMap"), base = $("hzBase"), wrap = $("hzMapWrap"), c = cities()[city];
    wrap.style.aspectRatio = `${g.MW} / ${g.MH}`; wrap.style.background = "var(--sea)";
    for (const el of [svg, base]) { el.setAttribute("viewBox", `0 0 ${g.MW} ${g.MH}`); el.replaceChildren(); }
    const land = svgEl("g", { fill: "var(--land)", stroke: "var(--coast)", "stroke-width": .8 });
    for (const ring of LAND.rings) land.append(svgEl("path", { d: ring.map((p, i) => `${i ? "L" : "M"}${g.X(p[0]).toFixed(1)},${g.Y(p[1]).toFixed(1)}`).join("") + "Z" }));
    base.append(land);
    const paths = (SNAP.trajectories || {})[city] || {};
    const d = p => p.map((q, i) => `${i ? "L" : "M"}${g.X(q[0])},${g.Y(q[1])}`).join("");
    for (const [lv, cls] of LEVELS) {
      const members = paths[lv] || [];
      members.slice(1).forEach(p => svg.append(svgEl("path", { d: d(p), fill: "none", stroke: `var(--${cls})`, "stroke-width": 1, opacity: .45 })));
      const central = members[0];
      if (!central) continue;
      svg.append(svgEl("path", { d: d(central), fill: "none", stroke: "var(--surface)", "stroke-width": 6, "stroke-linejoin": "round", opacity: .8 }));
      svg.append(svgEl("path", { d: d(central), fill: "none", stroke: `var(--${cls})`, "stroke-width": 2.5, "stroke-linejoin": "round" }));
      for (const q of central) if (q[2] && q[2] % 12 === 0) svg.append(svgEl("circle", { cx: g.X(q[0]), cy: g.Y(q[1]), r: 3.5, fill: `var(--${cls})`, stroke: "var(--surface)", "stroke-width": 1.5 }));
      const end = central[central.length - 1];
      svg.append(svgEl("text", { x: Math.min(g.X(end[0]) + 6, g.MW - 110), y: Math.max(g.Y(end[1]) - 6, 14), "font-size": 13, "font-weight": 700,
        fill: "var(--text)", stroke: "var(--sea)", "stroke-width": 3, "paint-order": "stroke" }, t().level[lv]));
    }
    svg.append(svgEl("circle", { cx: g.X(c.lon), cy: g.Y(c.lat), r: 6, fill: "var(--text)", stroke: "var(--sea)", "stroke-width": 2 }));
    svg.append(svgEl("text", { x: g.X(c.lon) + 10, y: g.Y(c.lat) + 18, "font-size": 15, "font-weight": 700, fill: "var(--text)", stroke: "var(--sea)", "stroke-width": 3.5, "paint-order": "stroke" }, c.name));
    svg.setAttribute("aria-label", `${t().hPath}: ${c.name}`);
    drawFires();
    $("hzMapLegend").innerHTML = `<li><span class="sw dot"></span>${t().lgFire(SNAP.fires.count)}</li>` +
      LEVELS.map(([lv, cls]) => `<li><span class="sw" style="border-top:3px solid var(--${cls})"></span>${t().level[lv]}</li>`).join("") +
      `<li><span class="sw dot" style="background:var(--text);width:7px;height:7px"></span>${t().lgDots}</li>`;
    const start = [c.lon, c.lat], up = (SNAP.upwind || {})[city] || {};
    $("hzPaths").innerHTML = LEVELS.map(([lv, cls]) => {
      const central = (paths[lv] || [])[0];
      if (!central) return "";
      const end = central[central.length - 1], stop = end[2] < 48 ? end[2] : 0;
      const dist = Math.round(km(start, end) / 10) * 10, dir = t().dirs[Math.round(bearing(start, end) / 45) % 8];
      return `<li><span class="key" style="border-color:var(--${cls})"></span><span><b>${t().level[lv]}.</b> ${t().pathLine(dist, dir, stop)} ${up[lv] ? t().upwindLine(up[lv]) : ""}</span></li>`;
    }).join("");
    if (!Object.values(paths).some(members => members.length)) $("hzPaths").textContent = t().noPaths;
  }

  function renderEvidence() {
    const c = cities()[city], nea = neaData(), paths = (SNAP.trajectories || {})[city] || {};
    const ends = LEVELS.map(([lv]) => (paths[lv] || [])[0]).filter(Boolean).map(p => p[p.length - 1]);
    let spread = 0; for (const a of ends) for (const b of ends) spread = Math.max(spread, km(a, b));
    const fireT = SNAP.fires.latest_utc ? fmtTime(new Date(SNAP.fires.latest_utc), c) : "–";
    const psi = nea ? Object.values(nea.psi_24h) : [];
    const known = [city === "singapore" && nea ? t().k1sg(Math.min(...psi), Math.max(...psi), fmtTime(new Date(nea.psi_time), c)) : t().k1(c.name),
      t().k2(SNAP.fires.count, fireT), ends.length ? t().k3 : t().noPaths];
    const unknown = [ends.length ? t().u1(Math.round(spread / 10) * 10) : t().noPaths, t().u2, city === "singapore" && SNAP.track ? t().u3sg(SNAP.track.ratio) : t().u3];
    const settle = [t().s1, t().s2(c.name), t().s3];
    const col = (h, items) => `<div><h3>${h}</h3><ul>${items.map(i => `<li>${i}</li>`).join("")}</ul></div>`;
    $("hzEvidence").innerHTML = col(t().know, known) + col(t().unknown, unknown) + col(t().settle, settle);
    const [url, en, id] = OFFICIAL[c.country];
    $("hzLinks").innerHTML = `<a href="${url}">${lang === "id" ? id : en}</a>`;
  }

  function render() {
    renderStatic();
    const c = cities()[city];
    $("hzTitle").textContent = t().title(c.name);
    $("hzUpdated").textContent = `${t().snapshot(fmtDay(new Date(SNAP.generated_at), c) + " " + fmtTime(new Date(SNAP.generated_at), c))}${live.at ? ` ${t().liveAt(fmtTime(live.at, c))}` : ""}`;
    renderNow(); renderChart(); renderMap(); renderEvidence();
    document.dispatchEvent(new CustomEvent("app:state", { detail: { city } }));
  }

  document.addEventListener("app:change", async e => {
    lang = e.detail.lang;
    if (e.detail.city) city = e.detail.city;
    if (panel.hidden) return;
    try { await load(); } catch (err) { $("hzTitle").textContent = T[lang].noData; return; }
    if (!cities()[city]) city = SNAP.cities[0].key;
    render();
    if (!live.cams[city]) refreshLive(city);
  });
  window.addEventListener("resize", () => { if (!panel.hidden && SNAP) drawFires(); });
})();
