const { test } = require('node:test');
const assert = require('node:assert/strict');
const { classify, yearTotal, resolveRow } = require('../site/fire-data.js');

test('Missing weeks remain missing instead of ranking as zero', () => {
  assert.equal(classify([null, 20, 30], null, 10), 'missing');
  assert.equal(classify([null, 20, 30], 0, 10), 'lowest');
  assert.equal(classify([0, 0, null], 0, 10), 'none');
  assert.equal(classify([1, 2, null], 2, 10), 'few');
});

test('Whole-year bars report incomplete coverage and separate projected totals', () => {
  assert.deepEqual(yearTotal([10, null, 20], 3), { value: 30, missing: 1 });
  assert.deepEqual(yearTotal([null, null], 2), { value: null, missing: 2 });
  assert.deepEqual(yearTotal([10, 20, 999], 2), { value: 30, missing: 0 });
});

test('Province links accept current keys and legacy numeric province keys', () => {
  const rows = [{key: 'total'}, {key: 'isl:Sulawesi'}, {key: 'prov:Aceh'}, {key: 'prov:Sulawesi Tengah'}];
  assert.equal(resolveRow(rows, 'prov:1'), 'prov:Sulawesi Tengah');
  assert.equal(resolveRow(rows, 'prov:Sulawesi Tengah'), 'prov:Sulawesi Tengah');
  assert.equal(resolveRow(rows, 'prov:unknown'), 'total');
});

const {comparisonRows, placeSummary, methodExample} = require('../site/fire-data.js');
function historyFixture() {
  return {
    years: [2024, 2025, 2026], running: {year:2026, week:2, days_seen:2, days_in_week:7}, latest_day:'2026-01-16',
    rows: [{key:'isl:Sulawesi',level:1,en:'Sulawesi',id:'Sulawesi'}, {key:'prov:Sulawesi Tengah',level:2,en:'Central Sulawesi',id:'Sulawesi Tengah'},
      {key:'isl:Maluku and Papua',level:1,en:'Maluku and Papua',id:'Maluku dan Papua'}, {key:'prov:Papua',level:2,en:'Papua',id:'Papua'}, {key:'prov:Papua Barat',level:2,en:'West Papua',id:'Papua Barat'}],
    count: [ [[1,1,1],[3,3,3],[5,5,5]], [[1,1,1],[3,3,3],[5,5,5]], [[3,4,2],[10,10,2],[30,30,2]], [[2,3,1],[10,10,1],[20,20,1]], [[1,1,1],[0,0,1],[10,10,1]] ],
    missing_days:[[0,0,0],[0,0,0],[0,0,0]], filled_days:[[0,0,0],[0,0,0],[0,0,0]],
    unusual:{count:[null,{ratio:[2.1,2.5,2.9]},null,null]}, nowcast:{count:[null,[5,8,12],null,null]}
  };
}
test('Papua aggregates province totals before comparing with historical median', () => {
  const p = comparisonRows(historyFixture(), {year:2026,measure:'count'}).find(r=>r.key==='papua');
  assert.equal(p.total,60);assert.equal(p.usual,13.5);assert.equal(p.ratio,60/13.5);
  assert.deepEqual(p.provinces,['prov:Papua','prov:Papua Barat']);
});
test('A historical comparison excludes its selected year and the unfinished year', () => {
  const p = comparisonRows(historyFixture(), {year:2025,measure:'count'}).find(r=>r.key==='papua');
  assert.equal(p.total,20);assert.equal(p.usual,7);assert.equal(p.baselineYears,1);
});
test('Missing days and zero baselines never produce a misleading relative value', () => {
  const h=historyFixture();h.missing_days[2][0]=1;
  assert.equal(comparisonRows(h,{year:2026,measure:'count'})[0].ratio,null);
  h.missing_days[2][0]=0;h.count[1][0]=[0,0,0];h.count[1][1]=[0,0,0];
  const s=placeSummary(h,{year:2026,row:'prov:Sulawesi Tengah',measure:'count'});
  assert.equal(s.ratio,null);assert.equal(s.status,'zero-baseline');
});
test('Only a current province with matching coverage receives a supplied model interval', () => {
  const h=historyFixture();
  assert.deepEqual(placeSummary(h,{year:2026,row:'prov:Sulawesi Tengah',measure:'count'}).interval,[2.1,2.5,2.9]);
  assert.equal(placeSummary(h,{year:2025,row:'prov:Sulawesi Tengah',measure:'count'}).interval,null);
});
test('The method illustration keeps observed, filled and projected values distinct', () => {
  assert.equal(methodExample(0).total,54);assert.equal(methodExample(1).total,73.6);assert.equal(methodExample(2).total,93.6);
  assert.equal(methodExample(0).days[2].value,null);
  assert.equal(methodExample(1).days[2].kind,'filled');
  assert.equal(methodExample(2).days[5].kind,'estimate');
});

test('The first January week has no completed-period comparison', () => {
  const h=historyFixture();h.running.week=0;
  const records=comparisonRows(h,{year:2026,measure:'count'});
  assert.equal(records[0].total,null);assert.equal(records[0].ratio,null);assert.equal(records[0].status,'no-completed-weeks');
});
test('A true zero selected total stays zero when its historical baseline is positive', () => {
  const h=historyFixture();h.count[1][2]=[0,0,0];
  const record=placeSummary(h,{year:2026,row:'prov:Sulawesi Tengah',measure:'count'});
  assert.equal(record.total,0);assert.equal(record.ratio,0);assert.equal(record.status,'ok');
});
