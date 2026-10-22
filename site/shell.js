// Tabs, language and theme for Haze, Explained. Each tab's script listens for "app:change"
// ({lang, tab, city, year, row}) and renders when its panel is visible.
(() => {
  const S = {
    en: {
      byline: "A Forest Uncertainty Lab project", haze: "Haze", fires: "Fire history", sulteng: "Sulawesi Tengah monitor",
      draft: "Draft", draftNote: "The methods are still being reviewed. Please do not quote these numbers yet.",
      sources: {
        haze: "Sources include NEA Singapore (data.gov.sg), CAMS global forecasts from Copernicus via Open-Meteo, Open-Meteo winds, NASA FIRMS VIIRS detections, Natural Earth coastlines.",
        fires: "Sources include NASA FIRMS VIIRS Suomi NPP yearly archive (2013 to 2025) and FIRMS API (from 2026), NOAA-20 for days Suomi NPP missed, geoBoundaries province outlines.",
      },
      sections: "Sections", language: "Language", madeBy: "Made by", dark: "Dark", light: "Light",
    },
    id: {
      byline: "Proyek Forest Uncertainty Lab", haze: "Kabut asap", fires: "Riwayat api", sulteng: "Pemantau Sulawesi Tengah",
      draft: "Draf", draftNote: "Metodenya masih ditinjau. Mohon jangan mengutip angka-angka ini dulu.",
      sources: {
        haze: "Sumber meliputi NEA Singapura (data.gov.sg), prakiraan global CAMS dari Copernicus melalui Open-Meteo, angin Open-Meteo, deteksi VIIRS NASA FIRMS, garis pantai Natural Earth.",
        fires: "Sumber meliputi arsip tahunan VIIRS Suomi NPP NASA FIRMS (2013 sampai 2025) dan API FIRMS (sejak 2026), NOAA-20 untuk hari yang terlewat oleh Suomi NPP, batas provinsi geoBoundaries.",
      },
      sections: "Bagian", language: "Bahasa", madeBy: "Dibuat oleh", dark: "Gelap", light: "Terang",
    },
  };
  const state = { lang: "en", tab: "haze", city: "singapore" }, root = document.documentElement, $ = id => document.getElementById(id);
  const tabs = [...document.querySelectorAll("[role=tab]")];
  try { const saved = localStorage.getItem("haze-theme"); if (saved === "light" || saved === "dark") root.dataset.theme = saved; } catch (e) { /* storage blocked */ }

  function apply(extra = {}) {
    const s = S[state.lang];
    root.lang = state.lang;
    document.querySelector("nav.tabs").setAttribute("aria-label", s.sections);
    document.querySelector(".controls [role=group]").setAttribute("aria-label", s.language);
    document.querySelectorAll("[data-s]").forEach(e => { e.textContent = s[e.dataset.s]; });
    tabs.forEach(b => {
      const on = b.dataset.tab === state.tab;
      b.setAttribute("aria-selected", String(on));
      b.tabIndex = on ? 0 : -1;
      $(b.getAttribute("aria-controls")).hidden = !on;
    });
    document.querySelectorAll("[data-lang]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.lang === state.lang)));
    $("theme").textContent = root.dataset.theme === "dark" ? s.light : s.dark;
    const sourceLinks = state.tab === 'haze' ? [
      ['NEA / data.gov.sg', 'https://guide.data.gov.sg/developer-guide/real-time-apis'],
      ['CAMS / Open-Meteo', 'https://open-meteo.com/en/docs/air-quality-api'],
      ['NASA FIRMS', 'https://www.earthdata.nasa.gov/data/tools/firms'],
      ['Natural Earth', 'https://www.naturalearthdata.com/'],
      ['haze.json', 'data/haze.json'],
      ['WHO', 'https://www.who.int/publications/i/item/9789240034228'],
    ] : [
      ['NASA FIRMS', 'https://www.earthdata.nasa.gov/data/tools/firms'],
      ['geoBoundaries', 'https://www.geoboundaries.org/'],
    ];
    $('sources').textContent = s.sources[state.tab] + ' ';
    sourceLinks.forEach(([label, url], i) => {
      if (i) $('sources').append(' · ');
      const link = document.createElement('a'); link.href = url; link.textContent = label; $('sources').append(link);
    });
    Object.entries(extra).forEach(([key, value]) => { if (value != null) state[key] = value; });
    updateAddress();
    document.dispatchEvent(new CustomEvent("app:change", { detail: { ...state } }));
  }

  function updateAddress() {
    const params = new URLSearchParams({tab: state.tab, lang: state.lang, theme: root.dataset.theme});
    for (const key of ['city','year','row','measure','period']) if (state[key] != null) params.set(key, state[key]);
    history.replaceState(null, '', '#' + params.toString());
  }
  document.addEventListener('app:state', e => { Object.assign(state, e.detail); updateAddress(); });
  window.addEventListener('hashchange', () => readAddress());
  function readAddress() {
    const hash = new URLSearchParams(location.hash.slice(1));
    if (['haze','fires'].includes(hash.get('tab'))) state.tab = hash.get('tab');
    if (S[hash.get('lang')]) state.lang = hash.get('lang');
    if (['dark','light'].includes(hash.get('theme'))) root.dataset.theme = hash.get('theme');
    const extra = {};
    for (const key of ['city','year','row','measure','period']) if (hash.has(key)) extra[key] = hash.get(key);
    apply(extra);
  }

  tabs.forEach((b, i) => {
    b.onclick = () => { state.tab = b.dataset.tab; apply(); };
    b.onkeydown = e => {
      const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
      if (!step) return;
      const next = tabs[(i + step + tabs.length) % tabs.length];
      next.focus(); state.tab = next.dataset.tab; apply();
    };
  });
  document.querySelectorAll("[data-lang]").forEach(b => { b.onclick = () => { state.lang = b.dataset.lang; apply(); }; });
  $("theme").onclick = () => {
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    try { localStorage.setItem("haze-theme", root.dataset.theme); } catch (e) { /* storage blocked */ }
    apply();
  };

  readAddress();
})();
