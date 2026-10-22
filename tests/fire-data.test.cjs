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
