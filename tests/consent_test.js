const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const consent = require('../assets/js/consent.js');

test('exposes the shared consent API to browser modules', () => {
  const source = fs.readFileSync(path.join(__dirname, '../assets/js/consent.js'), 'utf8');
  const window = {};
  const document = {
    readyState: 'loading',
    addEventListener() {},
  };

  vm.runInNewContext(source, { document, window });

  assert.equal(typeof window.TarteelHouseConsent.readSavedPreference, 'function');
  assert.equal(window.TarteelHouseConsent.loadAnalytics, undefined);
  assert.equal(Object.keys(window.TarteelHouseConsent).join(','), 'readSavedPreference');
});

test('stores granted consent for one calendar year', () => {
  const now = Date.UTC(2026, 6, 13, 12);
  const preference = consent.createPreference('granted', now);

  assert.deepEqual(preference, {
    status: 'granted',
    expiresAt: Date.UTC(2027, 6, 13, 12),
  });
});

test('treats expired, malformed, and unknown preferences as missing', () => {
  const now = Date.UTC(2026, 6, 13, 12);

  assert.equal(consent.parsePreference(JSON.stringify({ status: 'denied', expiresAt: now }), now), null);
  assert.equal(consent.parsePreference('{bad json', now), null);
  assert.equal(consent.parsePreference(JSON.stringify({ status: 'maybe', expiresAt: now + 1 }), now), null);
  assert.deepEqual(
    consent.parsePreference(JSON.stringify({ status: 'denied', expiresAt: now + 1 }), now),
    { status: 'denied', expiresAt: now + 1 },
  );
});

test('removes expired storage and preserves a current choice', () => {
  const values = new Map();
  const storage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: key => values.delete(key),
  };
  const now = Date.UTC(2026, 6, 13, 12);

  values.set(consent.STORAGE_KEY, JSON.stringify({ status: 'granted', expiresAt: now }));
  assert.equal(consent.readSavedPreference(storage, now), null);
  assert.equal(values.has(consent.STORAGE_KEY), false);

  const saved = consent.savePreference(storage, 'denied', now);
  assert.deepEqual(consent.readSavedPreference(storage, now), saved);
});

test('loads and initializes GA4 exactly once', () => {
  const scripts = [];
  const document = {
    head: { appendChild: script => scripts.push(script) },
    createElement: () => ({}),
    querySelector: selector => scripts.find(script => selector.includes(script.src)) || null,
  };
  const window = {};

  consent.loadAnalytics(window, document);
  consent.loadAnalytics(window, document);

  assert.equal(scripts.length, 1);
  assert.equal(scripts[0].async, true);
  assert.equal(scripts[0].src, `https://www.googletagmanager.com/gtag/js?id=${consent.MEASUREMENT_ID}`);
  assert.deepEqual(window.dataLayer.map(args => Array.from(args).slice(0, 2)), [
    ['js', window.dataLayer[0][1]],
    ['config', consent.MEASUREMENT_ID],
  ]);
});

test('targets only first-party GA cookie names for deletion', () => {
  assert.deepEqual(
    consent.analyticsCookieNames('_ga=one; session=keep; _ga_ZVLW7QGYR1=two; _gid=keep'),
    ['_ga', '_ga_ZVLW7QGYR1'],
  );
});
