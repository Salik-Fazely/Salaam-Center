const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'book-trial/index.html'), 'utf8');
const successHtml = fs.readFileSync(path.join(root, 'success/index.html'), 'utf8');
const script = fs.readFileSync(path.join(root, 'assets/js/trial-form.js'), 'utf8');
const whatsappNumber = '34614401172';

function createHarness(options = {}) {
  const fields = {};
  const errors = {};
  const timers = [];
  const opened = [];
  const assigned = [];
  let clickHandler;
  let summaryFocused = false;

  function field(name, value, tagName = 'INPUT') {
    const attributes = new Map();
    const item = {
      name,
      value,
      tagName,
      validationMessage: `Complete ${name}.`,
      getAttribute(key) { return attributes.get(key) || ''; },
      setAttribute(key, next) { attributes.set(key, String(next)); },
      removeAttribute(key) { attributes.delete(key); },
    };
    fields[name] = item;
    errors[name] = { id: `${name}-error`, hidden: true, textContent: '' };
    return item;
  }

  field('contact_role', 'parent_guardian');
  field('contact_name', '  Samira Rahimi  ');
  field('country_timezone', '  Spain / Madrid time  ');
  field('learner_age_group', 'age_8_11');
  field('program', 'quran');
  field('frequency', '2_week', 'SELECT');
  field('preferred_schedule', '  Tuesdays and Thursdays after 18:00 Madrid time  ', 'TEXTAREA');
  field('learning_goal', '  Build confident Quran reading  ', 'TEXTAREA');

  Object.assign(
    fields,
    Object.fromEntries(
      Object.entries(options.values || {}).map(([name, value]) => [name, { ...fields[name], value }]),
    ),
  );

  const button = {
    disabled: false,
    textContent: 'Continue in WhatsApp',
    addEventListener(type, handler) {
      if (type === 'click') clickHandler = handler;
    },
    setAttribute() {},
    removeAttribute() {},
  };
  const summary = {
    hidden: true,
    textContent: '',
    focus() { summaryFocused = true; },
  };
  const form = {
    elements: { namedItem(name) { return fields[name] || null; } },
    querySelector(selector) {
      return selector === '[data-whatsapp-submit]' ? button : null;
    },
    querySelectorAll(selector) {
      if (selector === '.field-error') return Object.values(errors);
      if (selector === ':invalid') return options.invalidFields || [];
      if (selector === "[aria-invalid='true']") {
        return Object.values(fields).filter(item => item.getAttribute('aria-invalid') === 'true');
      }
      return [];
    },
    checkValidity() { return options.nativeValid !== false; },
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
  const popup = { opener: {} };
  const window = {
    open(url, target, features) {
      opened.push({ url, target, features });
      if (options.openThrows) throw new Error('Popup failed.');
      return options.popupBlocked ? null : popup;
    },
    location: {
      assign(url) {
        if (options.assignThrows) throw new Error('Navigation failed.');
        assigned.push(url);
      },
    },
    setTimeout(callback) {
      timers.push(callback);
      return timers.length;
    },
  };

  vm.runInNewContext(script, { document, window, URL, encodeURIComponent });

  return {
    assigned,
    button,
    errors,
    fields,
    form,
    opened,
    popup,
    summary,
    click() {
      assert.equal(typeof clickHandler, 'function', 'WhatsApp CTA must register a click handler');
      return clickHandler({ preventDefault() {} });
    },
    runTimers() { timers.splice(0).forEach(callback => callback()); },
    get summaryFocused() { return summaryFocused; },
  };
}

test('trial form exposes exactly the approved minimized WhatsApp fields', () => {
  const approvedNames = [
    'contact_role',
    'contact_name',
    'country_timezone',
    'learner_age_group',
    'program',
    'frequency',
    'preferred_schedule',
    'learning_goal',
  ];
  const actualNames = new Set(
    [...html.matchAll(/<(?:input|select|textarea)\b[^>]*\bname="([^"]+)"/g)]
      .map(match => match[1]),
  );
  assert.deepEqual([...actualNames].sort(), [...approvedNames].sort());

  const formStart = html.match(/<form\b[^>]*data-trial-form[^>]*>/i)?.[0] || '';
  assert.match(formStart, /data-whatsapp-handoff="true"/);
  assert.doesNotMatch(formStart, /\baction\s*=/i);
  assert.doesNotMatch(formStart, /\bmethod\s*=\s*["']?post/i);
  assert.match(html, /data-whatsapp-submit[^>]*>\s*Continue in WhatsApp\s*</);
  assert.doesNotMatch(html, /<fieldset\b[^>]*\bdisabled\b/i);

  for (const forbidden of [
    'email', 'learner_name', 'learner_first_name', 'learner_surname', 'phone',
    'date_of_birth', 'address', 'medical', 'privacy_acknowledgement', '_gotcha',
    'file', 'marketing', 'payment',
  ]) {
    assert.doesNotMatch(html, new RegExp(`name="${forbidden}"`, 'i'));
  }
  assert.doesNotMatch(html, />\s*Pashto\s*</i);
});

test('trial form options and maximum lengths exactly match the approved contract', () => {
  const optionValues = name => [...html.matchAll(
    new RegExp(`name="${name}" value="([^"]+)"`, 'g'),
  )].map(match => match[1]);
  assert.deepEqual(optionValues('contact_role'), ['parent_guardian', 'adult_woman']);
  assert.deepEqual(optionValues('learner_age_group'), [
    'age_5_7', 'age_8_11', 'age_12_16', 'adult_woman',
  ]);
  assert.deepEqual(optionValues('program'), ['quran', 'dari_persian', 'culture_ethics']);
  assert.deepEqual(
    [...html.matchAll(/<option value="([^"]*)">([^<]+)<\/option>/g)]
      .map(match => [match[1], match[2]]),
    [
      ['', 'Select one'],
      ['1_week', '1 class per week'],
      ['2_week', '2 classes per week'],
      ['4_week', '4 classes per week'],
      ['not_sure', 'Not sure yet'],
    ],
  );
  assert.match(html, /name="contact_name"[^>]*maxlength="80"/);
  assert.match(html, /name="country_timezone"[^>]*maxlength="100"/);
  assert.match(html, /name="preferred_schedule"[^>]*maxlength="400"/);
  assert.match(html, /name="learning_goal"[^>]*maxlength="500"/);
});

test('script is a local-only WhatsApp handoff with no network or storage submission', () => {
  assert.match(html, /<meta name="referrer" content="no-referrer"\s*\/?>/);
  assert.match(script, /https:\/\/wa\.me\/34614401172\?text=/);
  assert.match(script, /encodeURIComponent\(message\)/);
  assert.match(script, /window\.open\(/);
  assert.match(script, /window\.location\.assign\(/);
  assert.doesNotMatch(script, /\bfetch\s*\(/);
  assert.doesNotMatch(script, /XMLHttpRequest/);
  assert.doesNotMatch(script, /\bFormData\b/);
  assert.doesNotMatch(script, /localStorage|sessionStorage/);
  assert.doesNotMatch(script, /URLSearchParams|location\.search|history\.(?:push|replace)State/);
  assert.doesNotMatch(script, /formspree/i);
});

test('valid data opens an exact encoded wa.me message with trimmed human-readable values', () => {
  const harness = createHarness();
  harness.click();

  assert.equal(harness.opened.length, 1);
  assert.equal(harness.opened[0].target, '_blank');
  assert.equal(harness.opened[0].features, undefined);
  const target = new URL(harness.opened[0].url);
  assert.equal(target.origin, 'https://wa.me');
  assert.equal(target.pathname, `/${whatsappNumber}`);
  assert.deepEqual([...target.searchParams.keys()], ['text']);
  assert.equal(target.searchParams.get('text'), [
    'Hello Salaam Center,',
    '',
    'I would like to request a free 40-minute trial.',
    '',
    'Contact role: Parent or guardian',
    'Contact name: Samira Rahimi',
    'Country / time zone: Spain / Madrid time',
    'Learner age group: Age 8–11',
    'Program: Quran',
    'Preferred frequency: 2 classes per week',
    'Preferred schedule: Tuesdays and Thursdays after 18:00 Madrid time',
    'Learning goal: Build confident Quran reading',
    '',
    'I understand that teacher and schedule availability must be confirmed before the trial.',
  ].join('\n'));
  assert.equal(harness.popup.opener, null);
  assert.equal(harness.assigned.length, 0);
});

test('blank optional learning goal becomes Not provided', () => {
  const harness = createHarness({ values: { learning_goal: '   ' } });
  harness.click();
  const message = new URL(harness.opened[0].url).searchParams.get('text');
  assert.match(message, /Learning goal: Not provided/);
});

test('whitespace-only required values and overlong values fail with focused accessible errors', () => {
  for (const [name, value] of [
    ['contact_name', '   '],
    ['country_timezone', 'x'.repeat(101)],
    ['preferred_schedule', 'x'.repeat(401)],
    ['learning_goal', 'x'.repeat(501)],
  ]) {
    const harness = createHarness({ values: { [name]: value } });
    harness.click();
    assert.equal(harness.opened.length, 0, name);
    assert.equal(harness.assigned.length, 0, name);
    assert.equal(harness.summary.hidden, false, name);
    assert.equal(harness.summaryFocused, true, name);
    assert.equal(harness.errors[name].hidden, false, name);
    assert.equal(harness.fields[name].getAttribute('aria-invalid'), 'true', name);
    assert.match(harness.fields[name].getAttribute('aria-describedby'), new RegExp(`${name}-error`));
  }
});

test('contact role and learner age group must be consistent', () => {
  for (const values of [
    { contact_role: 'adult_woman', learner_age_group: 'age_12_16' },
    { contact_role: 'parent_guardian', learner_age_group: 'adult_woman' },
  ]) {
    const harness = createHarness({ values });
    harness.click();
    assert.equal(harness.opened.length, 0);
    assert.equal(harness.summaryFocused, true);
    assert.equal(harness.errors.learner_age_group.hidden, false);
  }
});

test('Afghan Culture and Islamic Ethics remains limited to child age groups', () => {
  const harness = createHarness({
    values: {
      contact_role: 'adult_woman',
      learner_age_group: 'adult_woman',
      program: 'culture_ethics',
    },
  });
  harness.click();
  assert.equal(harness.opened.length, 0);
  assert.equal(harness.errors.program.hidden, false);
});

test('manipulated enum values are rejected before a message can be built', () => {
  for (const name of ['contact_role', 'learner_age_group', 'program', 'frequency']) {
    const harness = createHarness({ values: { [name]: 'unexpected_value' } });
    harness.click();
    assert.equal(harness.opened.length, 0, name);
    assert.equal(harness.assigned.length, 0, name);
    assert.equal(harness.summaryFocused, true, name);
    assert.equal(harness.errors[name].hidden, false, name);
    assert.doesNotMatch(harness.summary.textContent, /undefined/, name);
  }
});

test('native radio errors are reported once and focus moves to the summary', () => {
  const invalidFields = Array.from({ length: 4 }, () => ({
    name: 'learner_age_group',
    validationMessage: 'Select one learner age group.',
  }));
  const harness = createHarness({ nativeValid: false, invalidFields });
  harness.click();
  assert.equal(harness.opened.length, 0);
  assert.equal(harness.summaryFocused, true);
  assert.equal(
    harness.summary.textContent,
    'Please review: Select one learner age group.',
  );
});

test('rapid duplicate activation opens WhatsApp once and then restores the button', () => {
  const harness = createHarness();
  harness.click();
  harness.click();
  assert.equal(harness.opened.length, 1);
  assert.equal(harness.button.disabled, true);
  assert.equal(harness.button.textContent, 'Opening WhatsApp…');
  harness.runTimers();
  assert.equal(harness.button.disabled, false);
  assert.equal(harness.button.textContent, 'Continue in WhatsApp');
});

test('blocked popup falls back to the current tab and complete opening failure restores the button', () => {
  const fallback = createHarness({ popupBlocked: true });
  fallback.click();
  assert.equal(fallback.opened.length, 1);
  assert.equal(fallback.assigned.length, 1);
  assert.equal(fallback.assigned[0], fallback.opened[0].url);

  const failure = createHarness({ openThrows: true, assignThrows: true });
  failure.click();
  assert.equal(failure.button.disabled, false);
  assert.equal(failure.button.textContent, 'Continue in WhatsApp');
  assert.equal(failure.summary.hidden, false);
  assert.equal(failure.summaryFocused, true);
  assert.match(failure.summary.textContent, /could not open WhatsApp/i);
});

test('generic fallback and direct Success access remain truthful and safe', () => {
  assert.match(
    html,
    new RegExp(`href="https://wa\\.me/${whatsappNumber}"[^>]*target="_blank"[^>]*rel="noopener noreferrer"`),
  );
  assert.match(successHtml, /Continue your conversation in WhatsApp/);
  assert.match(successHtml, /cannot (?:confirm|know)[^<]*(?:sent|press(?:ed)? Send)/i);
  assert.match(successHtml, /not booked until Salaam Center confirms/i);
  assert.match(
    successHtml,
    new RegExp(`href="https://wa\\.me/${whatsappNumber}"[^>]*target="_blank"[^>]*rel="noopener noreferrer"`),
  );
  assert.doesNotMatch(successHtml, /data-success-state|Request received|Your trial request was submitted/i);
  assert.doesNotMatch(successHtml, /sessionStorage|submitted values/i);
});
