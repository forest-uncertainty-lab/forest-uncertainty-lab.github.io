/* Shared calculations for the fire-history views. */
((root) => {
  function classify(values, value, threshold) {
    if (value == null || !Number.isFinite(value)) return 'missing';
    const known = values.filter(v => v != null && Number.isFinite(v));
    if (!known.length) return 'missing';
    if (known.every(v => v === 0) && value === 0) return 'none';
    if (Math.max(...known, value) < threshold) return 'few';
    const less = known.filter(v => v < value).length;
    const equal = known.filter(v => v === value).length;
    const p = known.length > 1 ? (less + (equal - 1) / 2) / (known.length - 1) : .5;
    return p >= .9 ? 'highest' : p >= .65 ? 'above' : p > .35 ? 'usual' : p > .1 ? 'below' : 'lowest';
  }
  function yearTotal(series, weeks) {
    const values = series.slice(0, weeks);
    const known = values.filter(v => v != null && Number.isFinite(v));
    return {value: known.length ? known.reduce((a, b) => a + b, 0) : null, missing: values.length - known.length};
  }
  function resolveRow(rows, key) {
    if (rows.some(r => r.key === key)) return key;
    if (/^prov:\d+$/.test(key || '')) return rows.filter(r => r.level === 2 || r.key.startsWith('prov:'))[Number(key.slice(5))]?.key || 'total';
    return 'total';
  }
  const REGIONS = [
    {key:'sulawesi', en:'Sulawesi', id:'Sulawesi', island:'Sulawesi'},
    {key:'papua', en:'Papua', id:'Papua', provinces:['prov:Papua', 'prov:Papua Barat']},
    {key:'maluku', en:'Maluku', id:'Maluku', provinces:['prov:Maluku', 'prov:Maluku Utara']},
    {key:'kalimantan', en:'Kalimantan', id:'Kalimantan', island:'Kalimantan'},
    {key:'sumatra', en:'Sumatra', id:'Sumatera', island:'Sumatra'},
  ];
  const median = values => {
    const a = [...values].sort((a,b) => a-b), mid = Math.floor(a.length/2);
    return a.length ? a.length%2 ? a[mid] : (a[mid-1]+a[mid])/2 : null;
  };
  function memberIndices(history, region) {
    if (region.provinces) return history.rows.flatMap((r,i) => region.provinces.includes(r.key) ? [i] : []);
    const start = history.rows.findIndex(r => r.key === 'isl:' + region.island);
    if (start < 0) return [];
    const indices = [];
    for (let i=start+1; i<history.rows.length && history.rows[i].level===2; i++) indices.push(i);
    return indices;
  }
  function periodRecord(history, indices, {year, measure='count'}) {
    const weeks = history.running.week, yi = history.years.indexOf(Number(year));
    const unavailable = {total:null, usual:null, ratio:null, baselineYears:0, weeks, status:'unavailable'};
    if (!indices.length || yi < 0 || !history[measure]) return unavailable;
    if (weeks === 0) return {...unavailable, status:'no-completed-weeks'};
    function aggregate(k) {
      const series = indices.map(i => history[measure][i]?.[k]);
      if (series.some(s => !s)) return {value:null, complete:false};
      const sums = Array.from({length:weeks}, (_,w) => series.every(s => s[w]!=null && Number.isFinite(s[w])) ? series.reduce((sum,s)=>sum+s[w],0) : null);
      const total = yearTotal(sums,weeks);
      return {value:total.value, complete:total.missing===0 && !history.missing_days[k].slice(0,weeks).some(n=>n>0)};
    }
    const selected = aggregate(yi);
    const baseline = history.years.flatMap((y,k) => {
      if (y >= history.running.year || y === Number(year) || history.missing_days[k].some(n=>n>0)) return [];
      if (indices.some(i => history[measure][i]?.[k]?.some(v=>v==null))) return [];
      const value = aggregate(k); return value.complete && value.value!=null ? [value.value] : [];
    });
    const usual = median(baseline);
    const status = !selected.complete ? 'incomplete' : !baseline.length ? 'no-baseline' : usual===0 ? 'zero-baseline' : 'ok';
    return {total:selected.value, usual, ratio:status==='ok' ? selected.value/usual : null, baselineYears:baseline.length, weeks, status};
  }
  function comparisonRows(history, options) {
    return REGIONS.map(region => {
      const indices = memberIndices(history,region);
      return {...region, provinces:indices.map(i=>history.rows[i].key), ...periodRecord(history,indices,options)};
    });
  }
  function placeSummary(history, {year, row, measure='count'}) {
    const index = history.rows.findIndex(r=>r.key===row), place = history.rows[index];
    const record = periodRecord(history,index<0?[]:[index],{year,measure});
    const current = Number(year) === history.running.year;
    return {...record, key:row, en:place?.en||row, id:place?.id||row,
      interval:current && measure==='count' && record.status==='ok' ? history.unusual?.[measure]?.[index]?.ratio||null : null,
      nowcast:current ? history.nowcast?.[measure]?.[index]||null : null,
      observed:current ? history[measure]?.[index]?.[history.years.indexOf(Number(year))]?.[history.running.week]??null : null};
  }
  function methodExample(step) {
    const at = Math.max(0,Math.min(2,Math.trunc(Number(step)||0)));
    const base = [12,18,null,9,15,null,null];
    const days = base.map((value,i) => ({day:i+1,value,kind:value!=null?'observed':i===2?'missing':'future'}));
    if (at>=1) days[2] = {day:3,value:19.6,kind:'filled'};
    if (at>=2) for (const i of [5,6]) days[i] = {day:i+1,value:10,kind:'estimate'};
    return {step:at,days,total:Math.round(days.reduce((sum,d)=>sum+(d.value??0),0)*10)/10};
  }
  const api = { classify, yearTotal, resolveRow, comparisonRows, placeSummary, methodExample };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.FireData = api;
})(globalThis);
