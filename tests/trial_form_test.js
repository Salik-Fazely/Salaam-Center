const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'book-trial/index.html'), 'utf8');
const successHtml = fs.readFileSync(path.join(root, 'success/index.html'), 'utf8');
const script = fs.readFileSync(path.join(root, 'assets/js/trial-form.js'), 'utf8');

function activeFormHarness(fetchImpl, storage = {}, validation = {}) {
  let submitHandler;
  let assigned = 0;
  let summaryFocused = false;
  const button = { disabled: false, textContent: 'Request a Free Trial' };
  const summary = {
    hidden: true,
    textContent: '',
    focus() { summaryFocused = true; },
  };
  const errors = {};
  const fields = {};
  function field(name, value = '') {
    const attributes = new Map();
    const item = {
      name,
      value,
      tagName: 'INPUT',
      getAttribute(key) { return attributes.get(key) || ''; },
      setAttribute(key, next) { attributes.set(key, next); },
      removeAttribute(key) { attributes.delete(key); },
    };
    fields[name] = item;
    errors[name] = { id: `${name}-error`, hidden: true, textContent: '' };
    return item;
  }
  field('contact_role', 'adult_woman');
  field('learner_group', 'adult_woman');
  field('program', 'quran');
  field('email', 'adult@example.test');
  const form = {
    dataset: { endpoint: 'https://formspree.io/f/abc123', endpointVerified: 'true' },
    elements: { namedItem(name) { return fields[name] || null; } },
    addEventListener(type, handler) { if (type === 'submit') submitHandler = handler; },
    querySelector(selector) { return selector === "[type='submit']" ? button : null; },
    querySelectorAll(selector) {
      if (selector === '.field-error') return Object.values(errors);
      if (selector === ':invalid') return validation.invalidFields || [];
      if (selector === "[aria-invalid='true']") {
        return Object.values(fields).filter(item => item.getAttribute('aria-invalid') === 'true');
      }
      return [];
    },
    checkValidity() { return validation.valid !== false; },
    setAttribute() {},
    removeAttribute() {},
  };
  const document = {
    querySelector(selector) { return selector === '[data-trial-form]' ? form : null; },
    getElementById(id) {
      if (id === 'error-summary') return summary;
      return Object.values(errors).find(item => item.id === id) || null;
    },
  };
  vm.runInNewContext(script, {
    document,
    window: { location: { assign() { assigned += 1; } } },
    sessionStorage: {
      getItem() { return null; },
      removeItem() {},
      setItem: storage.setItem || (() => {}),
    },
    fetch: fetchImpl,
    FormData: class {},
    URL,
  });
  return {
    button,
    errors,
    fields,
    form,
    summary,
    submit() { return submitHandler({ preventDefault() {} }); },
    get assigned() { return assigned; },
    get summaryFocused() { return summaryFocused; },
  };
}

test('prelaunch form has exact minimized inventory and cannot submit', () => {
  const approvedNames = ['contact_role', 'contact_name', 'email', 'country', 'timezone_city', 'learner_first_name', 'learner_group', 'program', 'frequency', 'availability', 'level_goals', 'privacy_acknowledgement', '_gotcha'];
  for (const name of approvedNames) {
    assert.match(html, new RegExp(`name="${name}"`));
  }
  const actualNames = new Set(
    [...html.matchAll(/<(?:input|select|textarea)\b[^>]*\bname="([^"]+)"/g)].map(match => match[1]),
  );
  assert.deepEqual([...actualNames].sort(), [...approvedNames].sort());
  for (const forbidden of ['child_email', 'child_phone', 'date_of_birth', 'passport', 'school_name', 'home_address', 'payment', 'file', 'marketing', 'whatsapp']) {
    assert.doesNotMatch(html, new RegExp(`name="${forbidden}`, 'i'));
  }
  assert.doesNotMatch(html, />Pashto</i);
  assert.match(html, /data-endpoint=""/);
  assert.match(html, /data-endpoint-verified="false"/);
  assert.match(html, /type="submit"[^>]*disabled/);
  assert.match(html, /name="privacy_acknowledgement"[^>]*required/);
  assert.doesNotMatch(html, /name="privacy_acknowledgement"[^>]*checked/);
  assert.match(html, /name="_gotcha"[^>]*tabindex="-1"[^>]*aria-hidden="true"/);
  assert.match(html, /Secure online trial booking is being prepared and is not yet open\./);
  const optionValues = name => [...html.matchAll(new RegExp(`name="${name}" value="([^"]+)"`, 'g'))].map(match => match[1]);
  assert.deepEqual(optionValues('contact_role'), ['parent_guardian', 'adult_woman']);
  assert.deepEqual(optionValues('learner_group'), ['age_5_7', 'age_8_11', 'age_12_16', 'adult_woman']);
  assert.deepEqual(optionValues('program'), ['quran', 'dari_persian', 'culture_ethics']);
  assert.deepEqual(
    [...html.matchAll(/<option value="([^"]*)">([^<]+)<\/option>/g)].map(match => [match[1], match[2]]),
    [['', 'Select one'], ['1_week', '1 class per week'], ['2_week', '2 classes per week'], ['4_week', '4 classes per week'], ['not_sure', 'Not sure yet']],
  );
});

test('future integration validates, prevents duplicates, posts JSON-aware data, and protects success', () => {
  assert.match(script, /fetch\(/);
  assert.match(script, /Accept[^\n]+application\/json/);
  assert.match(script, /sessionStorage\.setItem/);
  assert.match(script, /sessionStorage\.removeItem/);
  assert.match(script, /window\.location\.assign\(["']\/success\//);
  assert.match(script, /response\.ok/);
  assert.match(script, /submitting/);
  assert.match(script, /error-summary/);
  assert.doesNotMatch(script, /localStorage/);
  assert.doesNotMatch(script, /URLSearchParams|location\.search/);
  assert.match(successHtml, /No request has been submitted/);
  assert.match(successHtml, /data-success-state/);
});

test('inactive endpoint causes no network request', () => {
  let fetched = false;
  const form = {
    dataset: { endpoint: '', endpointVerified: 'false' },
    addEventListener() { throw new Error('inactive form must not register submission'); },
    querySelectorAll() { return []; },
  };
  const document = { querySelector: selector => selector === '[data-trial-form]' ? form : null };
  vm.runInNewContext(script, {
    document,
    window: { location: { assign() {} } },
    sessionStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
    fetch() { fetched = true; },
    FormData: class {},
  });
  assert.equal(fetched, false);
});

test('valid session marker reveals confirmation once and direct access stays truthful', () => {
  let removed = false;
  let focused = false;
  const heading = { focus() { focused = true; } };
  const direct = { hidden: false };
  const confirmed = { hidden: true, querySelector() { return heading; } };
  const document = {
    querySelector(selector) {
      if (selector === "[data-success-state='confirmed']") return confirmed;
      if (selector === "[data-success-state='direct']") return direct;
      return null;
    }
  };
  vm.runInNewContext(script, {
    document,
    window: { location: { assign() {} } },
    sessionStorage: {
      getItem() { return JSON.stringify({ confirmed: true, at: Date.now() }); },
      removeItem() { removed = true; },
      setItem() {},
    },
    fetch() { throw new Error('not used'); },
    FormData: class {},
  });
  assert.equal(direct.hidden, true);
  assert.equal(confirmed.hidden, false);
  assert.equal(removed, true);
  assert.equal(focused, true);

  direct.hidden = false;
  confirmed.hidden = true;
  vm.runInNewContext(script, {
    document,
    window: { location: { assign() {} } },
    sessionStorage: { getItem() { return null; }, removeItem() {}, setItem() {} },
    fetch() { throw new Error('not used'); },
    FormData: class {},
  });
  assert.equal(direct.hidden, false);
  assert.equal(confirmed.hidden, true);
});

test('a confirmed provider response cannot be repeated when session storage fails', async () => {
  let submitHandler;
  let assigned = false;
  let busyRemoved = false;
  const button = { disabled: false, textContent: 'Request a Free Trial' };
  const summary = {
    hidden: true,
    textContent: '',
    focus() {},
  };
  const values = {
    contact_role: { value: 'adult_woman' },
    learner_group: { value: 'adult_woman' },
    program: { value: 'quran' },
  };
  const form = {
    dataset: { endpoint: 'https://formspree.io/f/abc123', endpointVerified: 'true' },
    elements: { namedItem(name) { return values[name] || null; } },
    addEventListener(type, handler) { if (type === 'submit') submitHandler = handler; },
    querySelector(selector) { return selector === "[type='submit']" ? button : null; },
    querySelectorAll() { return []; },
    checkValidity() { return true; },
    setAttribute() {},
    removeAttribute(name) { if (name === 'aria-busy') busyRemoved = true; },
  };
  const document = {
    querySelector(selector) { return selector === '[data-trial-form]' ? form : null; },
    getElementById(id) { return id === 'error-summary' ? summary : null; },
  };
  vm.runInNewContext(script, {
    document,
    window: { location: { assign() { assigned = true; } } },
    sessionStorage: {
      getItem() { return null; },
      removeItem() {},
      setItem() { throw new Error('storage unavailable'); },
    },
    fetch: async () => ({ ok: true, json: async () => ({ ok: true }) }),
    FormData: class {},
    URL,
  });

  await submitHandler({ preventDefault() {} });

  assert.equal(assigned, false);
  assert.equal(button.disabled, true);
  assert.equal(button.textContent, 'Request received');
  assert.equal(busyRemoved, true);
  assert.equal(summary.hidden, false);
  assert.match(summary.textContent, /do not submit it again/i);
});

test('concurrent duplicate submission triggers only one provider request', async () => {
  let fetchCount = 0;
  let resolveFetch;
  const response = new Promise(resolve => { resolveFetch = resolve; });
  const harness = activeFormHarness(() => {
    fetchCount += 1;
    return response;
  });

  const first = harness.submit();
  const duplicate = harness.submit();
  assert.equal(fetchCount, 1);
  assert.equal(harness.button.disabled, true);
  resolveFetch({ ok: true, json: async () => ({ ok: true }) });
  await Promise.all([first, duplicate]);

  assert.equal(fetchCount, 1);
  assert.equal(harness.assigned, 1);
});

test('provider validation failure restores submission and focuses accessible errors', async () => {
  const harness = activeFormHarness(async () => ({
    ok: true,
    json: async () => ({ ok: false, errors: [{ field: 'email', message: 'Email is invalid.' }] }),
  }));

  await harness.submit();

  assert.equal(harness.assigned, 0);
  assert.equal(harness.button.disabled, false);
  assert.equal(harness.button.textContent, 'Request a Free Trial');
  assert.equal(harness.summary.hidden, false);
  assert.equal(harness.summaryFocused, true);
  assert.match(harness.summary.textContent, /Email is invalid\./);
  assert.equal(harness.errors.email.hidden, false);
  assert.equal(harness.errors.email.textContent, 'Email is invalid.');
  assert.equal(harness.fields.email.getAttribute('aria-invalid'), 'true');
  assert.match(harness.fields.email.getAttribute('aria-describedby'), /email-error/);
});

test('network failure never redirects and restores an accessible retry state', async () => {
  const harness = activeFormHarness(async () => { throw new Error('Network unavailable.'); });

  await harness.submit();

  assert.equal(harness.assigned, 0);
  assert.equal(harness.button.disabled, false);
  assert.equal(harness.button.textContent, 'Request a Free Trial');
  assert.equal(harness.summary.hidden, false);
  assert.equal(harness.summaryFocused, true);
  assert.match(harness.summary.textContent, /Network unavailable\./);
});

test('native radio-group validation is reported once per field name', async () => {
  let fetchCount = 0;
  const invalidFields = Array.from({ length: 4 }, () => ({
    name: 'learner_group',
    validationMessage: 'Select one learner group.',
  }));
  const harness = activeFormHarness(
    async () => { fetchCount += 1; return { ok: true, json: async () => ({ ok: true }) }; },
    {},
    { valid: false, invalidFields },
  );

  await harness.submit();

  assert.equal(fetchCount, 0);
  assert.equal(harness.summaryFocused, true);
  assert.equal(
    harness.summary.textContent,
    'Please review: Select one learner group.',
  );
});
