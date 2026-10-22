// Fire history uses pipeline statistics. Missing weeks never become zero.
(() => {
let H = null, loading = null, LAST = null, FULL = 0, NY = 0;
const W = 52, FEW = {count: 10, frp: 300};
const CLASSES = ["lowest", "below", "usual", "above", "highest"];
const {classify: classifyValues, yearTotal, resolveRow} = FireData;
const panel = document.getElementById("tab-fires"), $ = id => document.getElementById(id);
const MONTHS = {en: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], id: ["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Agu","Sep","Okt","Nov","Des"]};
const dayOf = (y, d) => new Date(Date.UTC(y, 0, d));
const T = {
  en: {
    title: "Fire detections by province, week by week",
    lede: "Compare each place with its own history. Select a year, then choose a province to inspect its season.",
    hYears: "Indonesia, year by year", measure: "Measure", m_count: "Detections", m_frp: "Fire radiative power",
    period: "Period", p_same: d => `1 Jan to ${d}`, p_year: "Whole year",
    yearsSubSame: d => `Each bar counts 1 January to ${d}, the weeks ${LAST} has so far, so every year is compared over the same weeks. Click a bar to choose a year.`,
    yearsSubYear: () => `Whole-year totals. The dashed whisker is the ${LAST} season outlook, with its 80% range. Click a bar to choose a year.`,
    toDate: "To date",
    hHeat: (y, n) => `${y} against the other ${n} years`,
    heatSub: "Each row is a province, each column a week. The colour says how that week ranks against the same week in the other years. Click a row to see it in detail below.",
    hDetail: n => `${n}, week by week`,
    detailSub: "The line is the chosen year. The bands are the other years: the lighter band spans all of them, the darker band the middle half, and the dashed line is their median.",
    hMethod: "How this is counted",
    classes: { missing: "Missing data", lowest: "Lowest or second lowest", below: "Below usual", usual: "Usual for the week", above: "Above usual", highest: "Highest or second highest",
      none: "No detections in any year", gap: "Some days without satellite data", partial: "Week still running",
      few: (n, u) => `Under ${n} ${u} in every year; too few to rank` },
    rank: (r, n) => r === n ? `highest of ${n} years` : r === 1 ? `lowest of ${n} years` : `${ordinal(n - r + 1)} highest of ${n} years`,
    week: (a, b) => `${a} to ${b}`, usual: "Median of the other years", total: "Indonesia",
    unitCount: "detections", unitFrp: "MW of fire radiative power", gapNote: n => `${n} day${n > 1 ? "s" : ""} without satellite data`,
    partialNote: n => `Week still running. ${n} days observed`, nrtFrom: "Near-real-time data from here",
    lgMedian: "Median of other years", lgInner: "Middle half of other years", lgOuter: "Range of other years",
    nameKey: "en", islandKey: "island",
  },
  id: {
    title: "Deteksi api per provinsi, minggu demi minggu",
    lede: "Bandingkan setiap daerah dengan riwayatnya sendiri. Pilih tahun, lalu pilih provinsi untuk melihat musim apinya.",
    hYears: "Indonesia, tahun demi tahun", measure: "Ukuran", m_count: "Jumlah deteksi", m_frp: "Daya radiasi api",
    period: "Periode", p_same: d => `1 Jan sampai ${d}`, p_year: "Setahun penuh",
    yearsSubSame: d => `Setiap batang menghitung 1 Januari sampai ${d}, minggu-minggu yang sudah dimiliki ${LAST}, jadi setiap tahun dibandingkan pada minggu yang sama. Klik satu batang untuk memilih tahun.`,
    yearsSubYear: () => `Total setahun penuh. Garis rentang putus-putus adalah proyeksi musim ${LAST} dengan rentang 80%. Klik batang untuk memilih tahun.`,
    toDate: "Sejauh ini",
    hHeat: (y, n) => `${y} dibandingkan ${n} tahun lainnya`,
    heatSub: "Setiap baris adalah provinsi, setiap kolom satu minggu. Warna menunjukkan peringkat minggu itu dibandingkan minggu yang sama pada tahun-tahun lain. Klik satu baris untuk melihat rinciannya di bawah.",
    hDetail: n => `${n}, minggu demi minggu`,
    detailSub: "Garis adalah tahun yang dipilih. Pita adalah tahun-tahun lain: pita terang mencakup semuanya, pita gelap separuh tengahnya, dan garis putus-putus adalah mediannya.",
    hMethod: "Cara penghitungannya",
    classes: { missing: "Data hilang", lowest: "Terendah atau kedua terendah", below: "Di bawah biasanya", usual: "Biasa untuk minggu itu", above: "Di atas biasanya", highest: "Tertinggi atau kedua tertinggi",
      none: "Tidak ada deteksi di tahun mana pun", gap: "Ada hari tanpa data satelit", partial: "Minggu masih berjalan",
      few: (n, u) => `Di bawah ${n} ${u} setiap tahun; terlalu sedikit untuk diperingkat` },
    rank: (r, n) => r === n ? `tertinggi dari ${n} tahun` : r === 1 ? `terendah dari ${n} tahun` : `tertinggi ke-${n - r + 1} dari ${n} tahun`,
    week: (a, b) => `${a} sampai ${b}`, usual: "Median tahun-tahun lain", total: "Indonesia",
    unitCount: "deteksi", unitFrp: "MW daya radiasi api", gapNote: n => `${n} hari tanpa data satelit`,
    partialNote: n => `Minggu masih berjalan. ${n} hari teramati`, nrtFrom: "Data hampir waktu nyata mulai di sini",
    lgMedian: "Median tahun lain", lgInner: "Separuh tengah tahun lain", lgOuter: "Rentang tahun lain",
    nameKey: "id", islandKey: "island_id",
  },
};
function ordinal(n) { const s = ["th", "st", "nd", "rd"], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); }

let lang = "en", measure = "count", year = null, row = "total", period = "same";
const t = () => T[lang];
const svgEl = (tag, attrs, text) => { const e = document.createElementNS("http://www.w3.org/2000/svg", tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (text != null) e.textContent = text; return e; };
const fmt = v => Math.round(v).toLocaleString(lang === "id" ? "id-ID" : "en-GB");
const dm = d => d.toLocaleDateString(lang === "id" ? "id-ID" : "en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
const yi = () => H.years.indexOf(year);
const unit = () => measure === "count" ? t().unitCount : t().unitFrp;
// A value is usable for week w of year k when it exists and, for the latest year, the week is complete.
const usable = (k, w, v) => v != null && Number.isFinite(v) && !(H.years[k] === LAST && w >= FULL);

function rows() {
  return H.rows.map((r, i) => ({...r, index: i, label: r[lang], data: H[measure][i]}));
}
function classify(series, w, k0) {
  const value = H.years[k0] === LAST && w === FULL ? H.nowcast[measure][rows().findIndex(r => r.data === series)]?.[1] : series[k0][w];
  const vals = series.map((s, k) => usable(k, w, s[w]) ? s[w] : null);
  if (H.years[k0] === LAST && w > FULL) return ["future", null];
  if (H.years[k0] === LAST && w === FULL && value == null) return ["missing", null];
  if (H.years[k0] === LAST && w === FULL) vals[k0] = value;
  const cls = classifyValues(vals, value, FEW[measure]);
  const known = vals.filter(v => v != null), rank = value == null ? null : 1 + known.filter(v => v > value).length;
  return [cls, rank, known.length];
}
const weekDates = (y, w) => {
  const last = w === W - 1 ? (y % 4 === 0 ? 366 : 365) : 7 * w + 7;
  return t().week(dm(dayOf(y, 1 + 7 * w)), `${dm(dayOf(y, last))} ${y}`);
};
const median = a => { const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const quant = (a, q) => { const s = [...a].sort((x, y) => x - y), i = (s.length - 1) * q, lo = Math.floor(i); return s[lo] + (s[Math.ceil(i)] - s[lo]) * (i - lo); };
function placeTip(tip, ev, box) {
  const r = box.getBoundingClientRect(); tip.style.display = "block";
  tip.style.left = `${Math.min(ev.clientX - r.left + 14, r.width - tip.offsetWidth - 8)}px`; tip.style.top = `${ev.clientY - r.top + 12}px`;
}
function seg(id, options, current, set) {
  $(id).replaceChildren(...options.map(([value, label]) => { const b = document.createElement("button"); b.type = "button"; b.id = `${id}-${value}`; b.textContent = label;
    b.setAttribute("aria-pressed", String(value === current)); b.onclick = () => { set(value); render(); }; return b; }));
}

function renderStatic() {
  panel.querySelectorAll("[data-t]").forEach(e => { const v = t()[e.dataset.t]; if (typeof v === "string") e.textContent = v; });
  seg("fMeasure", [["count", t().m_count], ["frp", t().m_frp]], measure, v => { measure = v; });
  seg("fPeriod", [["same", t().p_same(dm(dayOf(LAST, Math.max(1, 7 * FULL))))], ["year", t().p_year]], period, v => { period = v; });
  $("fYearsSub").textContent = period === "same" ? t().yearsSubSame(dm(dayOf(LAST, Math.max(1, 7 * FULL)))) : t().yearsSubYear();
  $("fMethod").innerHTML = methods().map(([h, d]) => `<dt>${h}</dt><dd>${d}</dd>`).join("");
}


const extra = {
  en: {
    provinces: y => `${y}, unusual for which provinces?`,
    provSub: "Each province is compared with its own median over the same completed weeks. The dot is the middle estimate; whiskers show the 80% model interval. The vertical line marks the usual level. Select a province to inspect its season below.",
    frpSub: "Each province is compared with its own median over the same completed weeks. Fire radiative power uses a plain ratio without a probability interval.",
    tableView: "Read the province values as a table", province: "Province", ratio: "Times usual", interval: "80% interval", rank: "Rank, highest first", probability: "Probability above historical maximum", noBaseline: "No non-zero historical median", noData: "Fire history data could not be loaded. Try reloading the page, or download the data below.",
    observed: "Recorded", estimate: "Running-week estimate", outlook: "Season outlook, 80% range", filled: "Filled from NOAA-20", missing: "Missing days", future: "Future week", chooseYear: "Choose year", chooseRow: "Inspect a place", download: "Download the fire history data", updated: "Data through", generated: "Built", modelWarning: "Probabilities describe the count model only. They do not include weather, cloud cover, detection errors or uncertainty in the historical baseline.",
    incomplete: "Incomplete coverage; recorded values may undercount", noWeeks: "No completed weeks yet; a same-week comparison is unavailable", boundary: "The comparison uses the 34 historical province boundaries. Newer Papua provinces are grouped into Papua and West Papua.",
  },
  id: {
    provinces: y => `${y}, provinsi mana yang tidak biasa?`,
    provSub: "Setiap provinsi dibandingkan dengan median riwayatnya pada minggu lengkap yang sama. Titik adalah perkiraan tengah; garis rentang menunjukkan interval model 80%. Garis tegak menandai tingkat biasanya. Pilih provinsi untuk melihat musim apinya di bawah.",
    frpSub: "Setiap provinsi dibandingkan dengan median riwayatnya pada minggu lengkap yang sama. Daya radiasi api memakai rasio biasa tanpa interval probabilitas.",
    tableView: "Baca nilai provinsi dalam tabel", province: "Provinsi", ratio: "Kali tingkat biasa", interval: "Interval 80%", rank: "Peringkat, tertinggi dahulu", probability: "Probabilitas melampaui maksimum riwayat", noBaseline: "Median riwayat tidak lebih dari nol", noData: "Data riwayat api tidak dapat dimuat. Muat ulang halaman atau unduh data di bawah.",
    observed: "Tercatat", estimate: "Perkiraan minggu berjalan", outlook: "Proyeksi musim, rentang 80%", filled: "Diisi dari NOAA-20", missing: "Hari tanpa data", future: "Minggu mendatang", chooseYear: "Pilih tahun", chooseRow: "Lihat suatu daerah", download: "Unduh data riwayat api", updated: "Data sampai", generated: "Dibuat", modelWarning: "Probabilitas hanya menggambarkan model hitungan. Probabilitas ini tidak mencakup cuaca, tutupan awan, kesalahan deteksi, atau ketidakpastian acuan riwayat.",
    incomplete: "Cakupan belum lengkap; nilai tercatat mungkin lebih rendah dari sebenarnya", noWeeks: "Belum ada minggu lengkap; perbandingan minggu yang sama belum tersedia", boundary: "Perbandingan memakai 34 batas provinsi historis. Provinsi Papua yang baru dikelompokkan ke Papua dan Papua Barat.",
  },
};
const ex = () => extra[lang];
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ratioFmt = n => Number(n).toLocaleString(lang === 'id' ? 'id-ID' : 'en-GB', {maximumFractionDigits: 2});
const range = q => q ? `${ratioFmt(q[0])}–${ratioFmt(q[2])}` : '—';
const currentIndex = () => H.years.indexOf(LAST);
function methods() {
  return lang === 'id' ? [
    ['Apa yang dihitung', 'Deteksi adalah piksel panas yang terlihat saat satelit lewat. Satu kebakaran bisa menghasilkan banyak deteksi. Angka ini tidak mengukur luas terbakar atau memastikan vegetasi hutan terbakar. Sumber panas industri dan gunung api yang dikenal disaring, tetapi sumber baru bisa lolos. Awan dan asap tebal dapat menutupi api.'],
    ['Perbandingan yang konsisten', 'Suomi NPP menjadi dasar perbandingan sejak 2013. Satelit NOAA-20 hanya mengisi hari ketika Suomi NPP tidak mencatat satu pun deteksi di seluruh wilayah. Hitungan NOAA-20 dikalikan rasio tahunan antarsatelit. Arsir menandai minggu yang diisi; hari yang tetap hilang ditandai terpisah dan tidak dianggap nol.'],
    ['Daya radiasi api', 'Daya radiasi api mengukur panas yang dipancarkan, dalam megawatt. Halaman ini menjumlahkan nilai pada setiap deteksi. Penjumlahan ini bukan energi, luas terbakar, atau jumlah kebakaran yang berbeda.'],
    ['Perkiraan minggu berjalan', 'Perkiraan ini melengkapi minggu yang belum selesai memakai 14 hari lengkap terbaru yang tersedia. Bootstrap Bayesian memberi bobot acak pada hari-hari tersebut, lalu model Poisson memperkirakan hitungan hari yang hilang atau tersisa. Daya panas kontinu memakai laju harian berbobot secara langsung. Garis putus-putus membedakannya dari catatan. Rentang adalah persentil ke-10 sampai ke-90 model, bukan jaminan hasil.'],
    ['Proyeksi sisa musim', 'Setiap tahun lampau menjadi satu kemungkinan pola sisa musim, setelah diskalakan menurut perbandingan total pada minggu lengkap yang sama. Pita mencakup persentil ke-10 sampai ke-90 dari pola tersebut. Ini bukan prakiraan cuaca. Median tiap minggu tidak harus berjumlah sama dengan median total setahun.'],
    ['Tidak biasa untuk daerah ini', 'Untuk hitungan n, model laju Poisson dengan prior Jeffreys memakai distribusi posterior Gamma(n + ½, 1). Distribusi ini dibandingkan dengan median riwayat pada minggu lengkap yang sama. Hitungan kecil mendapat interval relatif lebih lebar. Perbandingan dan proyeksi musim ditunda bila minggu lengkap masih memiliki hari tanpa data. Probabilitas melampaui maksimum memakai maksimum teramati pada minggu yang sama. Model ini menganggap acuan riwayat tetap dan tidak memasukkan variasi cuaca, korelasi spasial, atau kesalahan deteksi. Untuk daya radiasi api, hanya rasio biasa yang ditampilkan.'],
    ['Minggu dan batas wilayah', 'Semua minggu dihitung sejak 1 Januari dalam UTC+8. Minggu ke-52 mencakup sisa hari sampai 31 Desember. Perbandingan tahunan hanya memakai minggu lengkap yang sama. Batas mengikuti 34 provinsi historis geoBoundaries; provinsi Papua yang baru masih digabung. Data hampir waktu nyata dapat berubah setelah diproses ulang.'],
  ] : [
    ['What a detection means', 'A detection is a hot pixel seen during a satellite pass. One fire can produce many detections. These counts do not measure burned area or establish that forest vegetation burned. Known industrial heat and volcanoes are filtered, but new sources can escape the masks. Clouds and thick smoke can hide fires.'],
    ['Consistent comparisons and gap filling', 'Suomi NPP provides the comparison from 2013 onwards. NOAA-20 fills only days when Suomi NPP recorded no detections anywhere in the area. NOAA-20 counts are scaled by the annual ratio between satellites. Hatching marks filled weeks. Days still missing are marked separately and never treated as zero.'],
    ['Fire radiative power', 'Fire radiative power measures emitted heat in megawatts. This page sums the values at each detection. That sum is not energy, burned area or a count of distinct fires.'],
    ['The unfinished week', 'The running-week estimate completes missing and future days using the most recent 14 available complete days. A Bayesian bootstrap gives those days random weights, then a Poisson model predicts counts for the remaining days. Continuous heat power uses the weighted daily rate directly. Dashed marks distinguish estimates from recorded values. The range is the model’s 10th to 90th percentiles, not a guarantee.'],
    ['The rest of the season', 'Each past year supplies a possible pattern for the remaining season, scaled by this year’s total relative to that year over the same completed weeks. The band covers the 10th to 90th percentiles of these patterns. This is not a weather forecast. Weekly medians need not sum to the median full-year total.'],
    ['Unusual for this place', 'For count n, a Poisson rate model with a Jeffreys prior gives a Gamma(n + ½, 1) posterior distribution. This distribution is divided by the historical median over the same completed weeks. Small counts have wider relative intervals. Comparisons and season outlooks are withheld when completed weeks have unresolved missing days. The probability above the previous maximum compares with the observed maximum over those weeks. The model treats the historical baseline as fixed and excludes weather variation, spatial dependence and detection errors. Fire radiative power uses a plain ratio only.'],
    ['Weeks and boundaries', 'Weeks start on 1 January in UTC+8. Week 52 includes the remaining days through 31 December. Year comparisons use the same completed weeks. Boundaries follow the 34 historical geoBoundaries provinces; newer Papua provinces remain grouped. Near-real-time values may change after reprocessing.'],
  ];
}
function selectYear(y) { year = y; render(); }
function selectRow(key) { row = resolveRow(H.rows, key); render(); }
function tooltip(el, label, tip, box) {
  el.append(svgEl('title', {}, label));
  el.onmousemove = ev => { tip.textContent = label; placeTip(tip, ev, box); };
  el.onmouseleave = () => { tip.style.display = 'none'; };
}
function activate(el, action, label) {
  el.setAttribute('role', 'button'); el.setAttribute('tabindex', '0'); el.setAttribute('aria-label', label);
  el.onclick = action;
  el.onkeydown = ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); action(); } };
}
function renderYears() {
  const svg = $('fYears'), width = 1000, height = 240, bottom = 42, top = 28;
  const series = H[measure][0], upto = period === 'same' ? FULL : W;
  const totals = series.map((s, i) => {
    const weeks = H.years[i] === LAST && period === 'year' ? FULL + 1 : upto;
    const result = yearTotal(s, weeks);
    result.missing += H.missing_days[i].slice(0, weeks).filter(n => n > 0).length;
    return result;
  });
  const out = period === 'year' ? H.outlook[measure][0] : null;
  const max = Math.max(1, ...totals.map(t => t.value || 0), out?.year_end[2] || 0) * 1.08;
  const Y = v => height - bottom - v / max * (height - bottom - top), bw = width / NY;
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`); svg.replaceChildren();
  H.years.forEach((y, i) => {
    const {value, missing} = totals[i], x = i * bw + 10, cx = x + (bw - 20) / 2;
    const g = svgEl('g', {'class': 'chart-action', id: `year-${y}`});
    g.append(svgEl('rect', {x: i * bw, y: 0, width: bw, height, fill: 'transparent'}));
    if (value != null) g.append(svgEl('rect', {x, y: Y(value), width: bw - 20, height: height - bottom - Y(value), rx: 3, fill: y === year ? 'var(--c-highest)' : 'var(--c-usual)', opacity: missing ? .55 : 1}));
    if (y === LAST && out) {
      const q = out.year_end;
      g.append(svgEl('line', {x1: cx, x2: cx, y1: Y(q[0]), y2: Y(q[2]), stroke: 'var(--text)', 'stroke-dasharray': '4 3', 'stroke-width': 2}));
      [q[0], q[2]].forEach(v => g.append(svgEl('line', {x1: cx - 7, x2: cx + 7, y1: Y(v), y2: Y(v), stroke: 'var(--text)'})));
      g.append(svgEl('circle', {cx, cy: Y(q[1]), r: 4, fill: 'var(--surface)', stroke: 'var(--text)', 'stroke-dasharray': '2 1'}));
    }
    g.append(svgEl('text', {x: cx, y: height - 22, 'text-anchor': 'middle', 'font-size': 13, fill: 'var(--text)', 'font-weight': y === year ? 700 : 400}, y));
    if (y === LAST && period === 'year') g.append(svgEl('text', {x: cx, y: height - 6, 'text-anchor': 'middle', 'font-size': 11, fill: 'var(--muted)'}, t().toDate));
    if (y === year && value != null) g.append(svgEl('text', {x: cx, y: Y(value) - 8, 'text-anchor': 'middle', 'font-size': 12, fill: 'var(--text)'}, fmt(value)));
    const label = `${y} · ${value == null ? ex().noWeeks : fmt(value) + ' ' + unit()}${missing ? ' · ' + ex().incomplete : ''}${y === LAST && out ? ' · ' + ex().outlook + ' ' + range(out.year_end) : ''}`;
    tooltip(g, label, $('fYearsTip'), svg.parentNode); activate(g, () => selectYear(y), label); svg.append(g);
  });
  svg.setAttribute('aria-label', t().hYears);
}
function renderProvinces() {
  const svg = $('fDots'), width = 1000, left = 230, right = 35, top = 35, rh = 25;
  const list = rows().filter(r => r.level === 2).map(r => ({...r, stats: H.unusual[measure][r.index]}))
    .sort((a,b) => (b.stats.ratio?.[1] ?? -1) - (a.stats.ratio?.[1] ?? -1));
  const valid = list.filter(r => r.stats.ratio && r.stats.ratio[0] > 0);
  const low = Math.min(.5, ...valid.map(r => r.stats.ratio[0]));
  const high = Math.max(2, ...valid.map(r => r.stats.ratio[2]));
  const lo = Math.floor(Math.log10(low)), hi = Math.ceil(Math.log10(high)), height = top + rh * list.length + 32;
  const X = v => left + (Math.log10(Math.max(v, 10 ** lo)) - lo) / (hi - lo) * (width - left - right);
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`); svg.replaceChildren();
  for (let p = lo; p <= hi; p++) {
    for (const k of [1,2,5]) {
      const v = k * 10 ** p; if (v > 10 ** hi) continue;
      svg.append(svgEl('line', {x1: X(v), x2: X(v), y1: top - 10, y2: height - 25, stroke: v === 1 ? 'var(--text)' : 'var(--line)', 'stroke-dasharray': v === 1 ? '3 3' : ''}));
      svg.append(svgEl('text', {x: X(v), y: 15, 'text-anchor': 'middle', 'font-size': 12, fill: 'var(--muted)'}, `${ratioFmt(v)}×`));
    }
  }
  const table = document.createElement('table'), caption = document.createElement('caption');
  caption.textContent = `${ex().provinces(LAST)} · ${measure === 'count' ? ex().provSub : ex().frpSub}`; table.append(caption);
  const head = document.createElement('thead'); head.innerHTML = `<tr>${[ex().province,ex().ratio,ex().interval,ex().rank,ex().probability].map(h => `<th scope="col">${h}</th>`).join('')}</tr>`; table.append(head);
  const tbody = document.createElement('tbody');
  list.forEach((r,i) => {
    const y = top + i * rh + rh / 2, s = r.stats, q = s.ratio;
    const g = svgEl('g', {'class': 'chart-action', id: `province-${r.index}`});
    g.append(svgEl('rect', {x: 0, y: y - rh / 2, width, height: rh, fill: r.key === row ? 'var(--surface-soft)' : 'transparent'}));
    g.append(svgEl('text', {x: 4, y: y + 4, 'font-size': 13, fill: r.key === row ? 'var(--text)' : 'var(--muted)', 'font-weight': r.key === row ? 700 : 400}, r.label));
    if (q && q[0] > 0) {
      const colour = q[1] > 1 ? 'var(--c-highest)' : 'var(--c-lowest)';
      if (measure === 'count') {
        g.append(svgEl('line', {x1: X(q[0]), x2: X(q[2]), y1: y, y2: y, stroke: colour, 'stroke-width': 2}));
        [q[0],q[2]].forEach(v => g.append(svgEl('line', {x1: X(v), x2: X(v), y1: y-4, y2: y+4, stroke: colour})));
      }
      g.append(svgEl('circle', {cx: X(q[1]), cy: y, r: 4, fill: colour}));
      g.append(svgEl('text', {x: Math.min(X(q[2])+9, width-right), y: y+4, 'font-size': 11, fill: 'var(--text)'}, `${ratioFmt(q[1])}×`));
    } else g.append(svgEl('text', {x: left, y: y+4, 'font-size': 12, fill: 'var(--muted)'}, s.incomplete ? ex().incomplete : ex().noBaseline));
    const probability = s.p_above_max == null ? '—' : `${ratioFmt(s.p_above_max * 100)}%`;
    const label = `${r.label} · ${fmt(s.to_date)} ${unit()} · ${ex().ratio} ${q ? ratioFmt(q[1]) : '—'} · ${ex().interval} ${measure === 'count' ? range(q) : '—'} · ${ex().rank} ${s.rank == null ? '—' : s.rank+'/'+s.years} · ${ex().probability} ${probability}`;
    tooltip(g, label, $('fDotsTip'), svg.parentNode); activate(g, () => selectRow(r.key), label); svg.append(g);
    const tr = document.createElement('tr');
    tr.innerHTML = `<th scope="row"><button type="button" class="text-button">${escape(r.label)}</button></th><td>${q ? ratioFmt(q[1])+'×' : '—'}</td><td>${measure === 'count' ? range(q) : '—'}</td><td>${s.rank == null ? '—' : s.rank+'/'+s.years}</td><td>${probability}</td>`;
    tr.querySelector('button').onclick = () => selectRow(r.key); tbody.append(tr);
  });
  table.append(tbody); $('fTable').replaceChildren(table);
  $('fh-provinces').textContent = ex().provinces(LAST);
  $('fProvSub').textContent = (measure === 'count' ? ex().provSub : ex().frpSub) + ' ' + ex().modelWarning;
  svg.setAttribute('aria-label', ex().provinces(LAST));
}
function renderHeat() {
  const svg = $('fHeat'), R = rows(), cw = 16, ch = 20, left = 205, top = 25, k0 = yi();
  const width = left + W * cw, height = top + R.length * ch + 8;
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`); svg.setAttribute('width', width); svg.setAttribute('height', height); svg.replaceChildren();
  const defs = svgEl('defs', {}), pattern = svgEl('pattern', {id:'fhatch', width:4, height:4, patternUnits:'userSpaceOnUse', patternTransform:'rotate(45)'});
  pattern.append(svgEl('line', {x1:0,x2:0,y1:0,y2:4,stroke:'var(--hatch)','stroke-width':1.4})); defs.append(pattern); svg.append(defs);
  MONTHS[lang].forEach((m,i) => svg.append(svgEl('text', {x:left+Math.floor((Date.UTC(year,i,1)-Date.UTC(year,0,1))/864e5/7)*cw,y:15,'font-size':11,fill:'var(--muted)'},m)));
  R.forEach((r,ri) => {
    const y = top + ri * ch, g = svgEl('g', {'class':'chart-action', id:`heat-row-${r.index}`});
    if (r.level < 2 && ri) svg.append(svgEl('line',{x1:0,x2:width,y1:y-2,y2:y-2,stroke:'var(--line)'}));
    g.append(svgEl('text',{x:r.level===2?14:0,y:y+14,'font-size':12,'font-weight':r.level<2||r.key===row?700:400,fill:r.level<2||r.key===row?'var(--text)':'var(--muted)'},r.label));
    for(let w=0;w<W;w++) {
      const [cls] = classify(r.data,w,k0), x=left+w*cw, running=year===LAST&&w===FULL;
      const filled=H.filled_days[k0][w], missing=H.missing_days[k0][w];
      if(cls==='future') continue;
      const cell=svgEl('g',{});
      cell.append(svgEl('rect',{x,y,width:cw-2,height:ch-3,rx:2,fill:['none','missing'].includes(cls)?'var(--surface)':`var(--c-${cls})`,stroke:running?'var(--text)':cls==='missing'?'var(--muted)':'none','stroke-dasharray':running?'3 2':cls==='missing'?'1 2':''}));
      if(filled) cell.append(svgEl('rect',{x,y,width:cw-2,height:ch-3,fill:'url(#fhatch)'}));
      if(missing) cell.append(svgEl('line',{x1:x+2,x2:x+cw-4,y1:y+ch-6,y2:y+3,stroke:'var(--text)','stroke-width':1.5}));
      const value=running?H.nowcast[measure][r.index]?.[1]:r.data[k0][w];
      const q=running?H.nowcast[measure][r.index]:null;
      const label=`${r.label} · ${weekDates(year,w)} · ${value==null?'—':fmt(value)+' '+unit()}${running?' · '+ex().estimate+' '+range(q):''}${filled?' · '+ex().filled+' '+filled:''}${missing?' · '+ex().missing+' '+missing:''}`;
      tooltip(cell,label,$('fHeatTip'),svg.closest('.box')); g.append(cell);
    }
    activate(g,()=>selectRow(r.key),`${ex().chooseRow} ${r.label}`); svg.append(g);
  });
  $('fh-heat').textContent=t().hHeat(year,NY-1); svg.setAttribute('aria-label',t().hHeat(year,NY-1));
  $('fHeatLegend').innerHTML=CLASSES.map(c=>`<li><span class="chip" style="background:var(--c-${c})"></span>${t().classes[c]}</li>`).join('')+
    `<li><span class="chip" style="background:var(--c-few)"></span>${t().classes.few(FEW[measure],unit())}</li><li><span class="chip hatch-key"></span>${ex().filled}</li><li><span class="chip missing-key">/</span>${ex().missing}</li><li><span class="chip" style="border:1px dashed var(--text)"></span>${ex().estimate}</li>`;
}
function renderDetail() {
  const r=rows().find(r=>r.key===row)||rows()[0], svg=$('fDetail'), width=1000,height=320,m={l:65,r:20,t:25,b:32},k0=yi();
  const others=Array.from({length:W},(_,w)=>r.data.map((s,k)=>k!==k0&&usable(k,w,s[w])?s[w]:null).filter(v=>v!=null));
  const mine=r.data[k0].map((v,w)=>usable(k0,w,v)?v:null), q=year===LAST?H.nowcast[measure][r.index]:null, out=year===LAST?H.outlook[measure][r.index]:null;
  const maximum=Math.max(1,...others.flat(),...mine.filter(v=>v!=null),q?.[2]||0,...(out?.weekly.map(v=>v[2])||[]))*1.08;
  const X=w=>m.l+w/(W-1)*(width-m.l-m.r),Y=v=>height-m.b-v/maximum*(height-m.t-m.b);
  svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.replaceChildren();
  const step=[1,2,5].flatMap(k=>[1,10,100,1000,1e4,1e5,1e6,1e7].map(p=>k*p)).sort((a,b)=>a-b).find(v=>maximum/v<=5)||1e8;
  for(let v=0;v<=maximum;v+=step) { svg.append(svgEl('line',{x1:m.l,x2:width-m.r,y1:Y(v),y2:Y(v),stroke:'var(--line)'}));svg.append(svgEl('text',{x:m.l-8,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:'var(--muted)'},fmt(v))); }
  MONTHS[lang].forEach((mo,i)=>svg.append(svgEl('text',{x:X((Date.UTC(year,i,1)-Date.UTC(year,0,1))/864e5/7),y:height-10,'font-size':12,fill:'var(--muted)'},mo)));
  const drawBand=(points,fill)=>{if(!points.length)return;svg.append(svgEl('path',{d:points.map((p,i)=>`${i?'L':'M'}${X(p[0])},${Y(p[2])}`).join('')+points.slice().reverse().map(p=>`L${X(p[0])},${Y(p[1])}`).join('')+'Z',fill}));};
  drawBand(others.map((a,w)=>a.length?[w,Math.min(...a),Math.max(...a)]:null).filter(Boolean),'var(--band-outer)');
  drawBand(others.map((a,w)=>a.length?[w,quant(a,.25),quant(a,.75)]:null).filter(Boolean),'var(--band-inner)');
  const line=(values,colour,dash='')=>{let pen=false,d='';values.forEach((v,w)=>{if(v==null){pen=false;return;}d+=`${pen?'L':'M'}${X(w)},${Y(v)}`;pen=true;});svg.append(svgEl('path',{d,fill:'none',stroke:colour,'stroke-width':2,'stroke-dasharray':dash,'stroke-linejoin':'round'}));};
  line(others.map(a=>a.length?median(a):null),'var(--median)','4 4');
  if(out) {
    drawBand(out.weekly.map((q,i)=>[FULL+i,q[0],q[2]]),'var(--band)');
    line(Array.from({length:W},(_,w)=>w>=FULL?out.weekly[w-FULL]?.[1]??null:null),'var(--model)','5 4');
  }
  line(mine,'var(--c-highest)');
  if(q) {
    svg.append(svgEl('line',{x1:X(FULL),x2:X(FULL),y1:Y(q[0]),y2:Y(q[2]),stroke:'var(--c-highest)','stroke-width':2,'stroke-dasharray':'3 2'}));
    if(FULL>0&&mine[FULL-1]!=null) svg.append(svgEl('line',{x1:X(FULL-1),x2:X(FULL),y1:Y(mine[FULL-1]),y2:Y(q[1]),stroke:'var(--c-highest)','stroke-width':2,'stroke-dasharray':'4 3'}));
    svg.append(svgEl('circle',{cx:X(FULL),cy:Y(q[1]),r:5,fill:'var(--surface)',stroke:'var(--c-highest)','stroke-width':2,'stroke-dasharray':'3 2'}));
  }
  svg.append(svgEl('text',{x:m.l,y:13,'font-size':12,fill:'var(--muted)'},unit()));
  const cross=svgEl('line',{y1:m.t,y2:height-m.b,stroke:'var(--text)',opacity:0});svg.append(cross);
  const hit=svgEl('rect',{x:m.l,y:m.t,width:width-m.l-m.r,height:height-m.t-m.b,fill:'transparent',tabindex:0,role:'img','aria-label':lang==='id'?'Gunakan tombol panah untuk memeriksa minggu':'Use arrow keys to inspect weeks'});svg.append(hit);
  const tip=$('fDetailTip');let selected=0;
  function show(w,ev) {
    selected=w;cross.setAttribute('x1',X(w));cross.setAttribute('x2',X(w));cross.setAttribute('opacity',.5);
    const estimate=year===LAST&&w===FULL?q:year===LAST&&w>FULL?out?.weekly[w-FULL]:null;
    const label=`${r.label} · ${weekDates(year,w)} · ${estimate?ex().estimate+' '+range(estimate):ex().observed+' '+(mine[w]==null?'—':fmt(mine[w]))} · ${t().usual} ${others[w].length?fmt(median(others[w])):'—'}`;
    tip.textContent=label;
    if(ev)placeTip(tip,ev,svg.parentNode);else {tip.style.display='block';tip.style.left='12px';tip.style.top='12px';}
    hit.setAttribute('aria-label',label);
  }
  hit.onmousemove=ev=>{const b=svg.getBoundingClientRect();show(Math.max(0,Math.min(W-1,Math.round(((ev.clientX-b.left)/b.width*width-m.l)/(width-m.l-m.r)*(W-1)))),ev);};
  hit.onkeydown=ev=>{if(['ArrowLeft','ArrowRight'].includes(ev.key)){ev.preventDefault();show(Math.max(0,Math.min(W-1,selected+(ev.key==='ArrowRight'?1:-1))));}};
  hit.onfocus=()=>show(selected);hit.onblur=hit.onmouseleave=()=>{tip.style.display='none';cross.setAttribute('opacity',0);};
  $('fh-detail').textContent=`${t().hDetail(r.label)} · ${year}`;svg.setAttribute('aria-label',$('fh-detail').textContent);
  $('fDetailLegend').innerHTML=`<li><span class="sw" style="border-color:var(--c-highest)"></span>${year} · ${ex().observed}</li><li><span class="sw dash"></span>${t().lgMedian}</li><li><span class="sw band" style="background:var(--band-inner)"></span>${t().lgInner}</li><li><span class="sw band" style="background:var(--band-outer)"></span>${t().lgOuter}</li>${q?`<li><span class="sw dash" style="border-color:var(--c-highest)"></span>${ex().estimate}</li>`:''}${out?`<li><span class="sw band"></span>${ex().outlook}</li>`:''}`;
}
function render() {
  const focusId = document.activeElement?.id;
  renderStatic();
  const R=rows();
  $('fLede').textContent=t().lede+' '+ex().boundary;
  $('fUpdated').textContent=`${ex().updated} ${H.latest_day} · ${ex().generated} ${new Date(H.generated_at).toLocaleString(lang==='id'?'id-ID':'en-GB',{timeZone:'Asia/Makassar'})} UTC+8`;
  $('fYearSelect').replaceChildren(...H.years.map(y=>new Option(String(y),String(y),false,y===year)));
  $('fRowSelect').replaceChildren(...R.map(r=>new Option(r.label,r.key,false,r.key===row)));
  $('fYearSelect').setAttribute('aria-label',ex().chooseYear);$('fRowSelect').setAttribute('aria-label',ex().chooseRow);
  $('fYearLabel').textContent=ex().chooseYear;$('fRowLabel').textContent=ex().chooseRow;
  $('fYearSelect').onchange=ev=>selectYear(Number(ev.target.value));$('fRowSelect').onchange=ev=>selectRow(ev.target.value);
  panel.querySelector('[data-t="tableView"]').textContent=ex().tableView;
  $('fDownload').textContent=ex().download;
  if(!FULL&&period==='same')$('fYearsSub').textContent=ex().noWeeks;
  renderYears();renderProvinces();renderHeat();renderDetail();
  if (focusId) $(focusId)?.focus({preventScroll:true});
  document.dispatchEvent(new CustomEvent('app:state',{detail:{year,row,measure,period}}));
}
document.addEventListener('app:change',async ev=>{
  lang=ev.detail.lang;
  if(panel.hidden)return;
  try {
    loading=loading||fetch('data/history.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(data=>{H=data;NY=H.years.length;LAST=H.running.year;FULL=H.running.week;});
    await loading;
    year=H.years.includes(Number(ev.detail.year))?Number(ev.detail.year):(year||LAST);
    row=resolveRow(H.rows,ev.detail.row||row);
    if(['count','frp'].includes(ev.detail.measure))measure=ev.detail.measure;
    if(['same','year'].includes(ev.detail.period))period=ev.detail.period;
    render();
  }catch(error){loading=null;$('fLede').textContent=ex().noData;$('fDownload').textContent=ex().download;}
});
})();
