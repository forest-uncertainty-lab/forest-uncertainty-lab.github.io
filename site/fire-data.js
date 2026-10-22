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
  const api = { classify, yearTotal, resolveRow };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.FireData = api;
})(globalThis);
