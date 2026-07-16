const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');


const html = fs.readFileSync(path.join(__dirname, '../book-trial/index.html'), 'utf8');
const inlineScripts = Array.from(html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g))
  .map(match => match[1])
  .filter(script => script.trim());
const source = inlineScripts.at(-1);


class FormPayload {
  constructor(entries) {
    this.entries = entries.slice();
  }
  delete(name) {
    this.entries = this.entries.filter(([key]) => key !== name);
  }
  append(name, value) {
    this.entries.push([name, value]);
  }
  getAll(name) {
    return this.entries.filter(([key]) => key === name).map(([, value]) => value);
  }
}


function loadBookingScript() {
  const document = {
    getElementById() { return null; },
    querySelectorAll() { return []; },
  };
  const context = {
    alert() {},
    document,
    fetch() {},
    FormData: FormPayload,
    URL,
    window: { location: { href: 'https://www.tarteelhouse.com/book-trial/' } },
  };
  vm.runInNewContext(source, context);
  return context;
}


test('preferred day checkboxes keep the existing single comma-separated payload value', () => {
  const context = loadBookingScript();
  assert.equal(typeof context.normalizePreferredDaysPayload, 'function');

  const selected = [
    { value: 'mon' },
    { value: 'wed' },
    { value: 'sun' },
  ];
  const form = {
    querySelectorAll(selector) {
      assert.equal(selector, 'input[name="preferred_days"]:checked');
      return selected;
    },
  };
  const payload = new FormPayload([
    ['quran_level', 'reading-short-words'],
    ['preferred_days', 'mon'],
    ['preferred_days', 'wed'],
    ['preferred_days', 'sun'],
    ['preferred_time', 'evening'],
  ]);

  context.normalizePreferredDaysPayload(payload, form);

  assert.deepEqual(payload.getAll('preferred_days'), ['mon,wed,sun']);
  assert.deepEqual(payload.getAll('quran_level'), ['reading-short-words']);
  assert.deepEqual(payload.getAll('preferred_time'), ['evening']);
});
