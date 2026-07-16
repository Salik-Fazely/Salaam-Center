const test = require('node:test');
const assert = require('node:assert/strict');

const analyticsEvents = require('../assets/js/analytics-events.js');
const consent = require('../assets/js/consent.js');

function createEventTarget(properties = {}) {
  const listeners = new Map();

  return Object.assign(properties, {
    addEventListener(type, listener) {
      const registered = listeners.get(type) || [];
      registered.push(listener);
      listeners.set(type, registered);
    },
    dispatch(type, event = {}) {
      if (!Object.hasOwn(event, 'defaultPrevented')) event.defaultPrevented = false;
      if (typeof event.preventDefault !== 'function') {
        event.preventDefault = () => {
          event.defaultPrevented = true;
        };
      }
      (listeners.get(type) || []).forEach(listener => listener.call(this, event));
      return event;
    },
    listenerCount(type) {
      return (listeners.get(type) || []).length;
    },
  });
}

function createStorage() {
  const values = new Map();
  return {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: key => values.delete(key),
  };
}

function createEnvironment({ preference = 'missing', valid = true, withGtag = true } = {}) {
  const calls = [];
  const localStorage = createStorage();

  if (preference === 'granted' || preference === 'denied') {
    consent.savePreference(localStorage, preference);
  } else if (preference === 'expired') {
    localStorage.setItem(consent.STORAGE_KEY, JSON.stringify({ status: 'granted', expiresAt: 1 }));
  }

  const window = {
    __tarteelHouseGa4Initialized: true,
    localStorage,
    location: {
      href: 'https://www.tarteelhouse.com/pricing/?email=visitor%40example.com#plans',
      origin: 'https://www.tarteelhouse.com',
      pathname: '/pricing/',
    },
  };
  if (withGtag) window.gtag = (...args) => calls.push(args);

  let form;
  form = createEventTarget({
    id: 'trial-form',
    valid,
    checkValidity() {
      return this.valid;
    },
    contains(control) {
      return control?.form === form;
    },
  });

  const document = createEventTarget({
    getElementById(id) {
      return id === 'trial-form' ? form : null;
    },
  });

  analyticsEvents.init(window, document, consent);
  return { calls, document, form, localStorage, window };
}

function createCta({
  href = '/book-trial/?email=visitor%40example.com#form',
  tagName = 'A',
  text = '  Book  a\nFree Trial  ',
} = {}) {
  const element = {
    dataset: tagName === 'BUTTON' ? { href } : {},
    getAttribute(name) {
      if (name === 'href' && tagName === 'A') return href;
      if (name === 'data-href' && tagName === 'BUTTON') return href;
      return null;
    },
    innerText: text,
    tagName,
    textContent: text,
  };
  return {
    element,
    target: { closest: () => element },
  };
}

function createControl(form, { disabled = false, readOnly = false, tagName = 'INPUT', type = 'text' } = {}) {
  return {
    disabled,
    form,
    name: 'child_name',
    readOnly,
    tagName,
    type,
    value: 'Private Child Name',
  };
}

test('exports a reusable analytics event initializer', () => {
  assert.equal(typeof analyticsEvents.init, 'function');
});

test('sends no events when consent is missing, denied, or expired', () => {
  for (const preference of ['missing', 'denied', 'expired']) {
    const { calls, document } = createEnvironment({ preference });
    document.dispatch('click', { target: createCta().target });
    assert.deepEqual(calls, [], preference);
  }
});

test('sends one privacy-safe CTA event without blocking navigation', () => {
  const { calls, document, window } = createEnvironment({ preference: 'granted' });
  analyticsEvents.init(window, document, consent);
  const event = document.dispatch('click', { target: createCta().target });

  assert.equal(event.defaultPrevented, false);
  assert.deepEqual(calls, [[
    'event',
    'trial_cta_click',
    {
      source_path: '/pricing/',
      destination_path: '/book-trial/',
      cta_text: 'Book a Free Trial',
    },
  ]]);
});

test('caps normalized CTA text at 100 characters without adding URL or form PII', () => {
  const { calls, document, form } = createEnvironment({ preference: 'granted' });
  const normalizedPrefix = `${'A'.repeat(60)} ${'B'.repeat(60)}`;
  form.value = 'Private Child Name';

  document.dispatch('click', {
    target: createCta({ text: `  ${'A'.repeat(60)}\n${'B'.repeat(60)}  ` }).target,
  });

  const parameters = calls[0][2];
  assert.equal(parameters.cta_text.length, 100);
  assert.equal(parameters.cta_text, normalizedPrefix.slice(0, 100));
  assert.deepEqual(Object.keys(parameters), ['source_path', 'destination_path', 'cta_text']);
  assert.doesNotMatch(JSON.stringify(parameters), /visitor|Private Child Name/);
});

test('tracks an internal button that leads to the canonical booking page', () => {
  const { calls, document } = createEnvironment({ preference: 'granted' });
  document.dispatch('click', { target: createCta({ tagName: 'BUTTON' }).target });

  assert.equal(calls.length, 1);
  assert.equal(calls[0][1], 'trial_cta_click');
});

test('does not queue a pre-consent CTA click and checks later denial', () => {
  const { calls, document, localStorage } = createEnvironment();
  const cta = createCta();

  document.dispatch('click', { target: cta.target });
  consent.savePreference(localStorage, 'granted');
  assert.deepEqual(calls, []);

  document.dispatch('click', { target: cta.target });
  consent.savePreference(localStorage, 'denied');
  document.dispatch('click', { target: cta.target });
  assert.equal(calls.length, 1);
});

test('does not create or initialize an analytics implementation', () => {
  const { document, window } = createEnvironment({ preference: 'granted', withGtag: false });
  document.dispatch('click', { target: createCta().target });

  assert.equal(window.gtag, undefined);
  assert.equal(window.dataLayer, undefined);
});

test('form start accepts input, change, or focus on an editable control', () => {
  for (const type of ['input', 'change', 'focusin']) {
    const { calls, form } = createEnvironment({ preference: 'granted' });
    form.dispatch(type, { target: createControl(form) });

    assert.deepEqual(calls, [[
      'event',
      'trial_form_start',
      { source_path: '/pricing/', form_id: 'trial-form' },
    ]], type);
  }
});

test('form start waits for a new post-consent interaction and fires at most once', () => {
  const { calls, form, localStorage } = createEnvironment();
  const control = createControl(form);

  form.dispatch('input', { target: control });
  consent.savePreference(localStorage, 'granted');
  assert.deepEqual(calls, []);

  form.dispatch('change', { target: control });
  form.dispatch('focusin', { target: control });
  assert.deepEqual(calls, [[
    'event',
    'trial_form_start',
    { source_path: '/pricing/', form_id: 'trial-form' },
  ]]);
});

test('form start ignores hidden, button, disabled, and read-only controls', () => {
  const { calls, form } = createEnvironment({ preference: 'granted' });
  const controls = [
    createControl(form, { type: 'hidden' }),
    createControl(form, { tagName: 'BUTTON' }),
    createControl(form, { disabled: true }),
    createControl(form, { readOnly: true }),
  ];

  controls.forEach(target => form.dispatch('focusin', { target }));
  assert.deepEqual(calls, []);
});

test('submit attempt fires only for a valid submit, at most once, without preventing it', () => {
  const { calls, form } = createEnvironment({ preference: 'granted', valid: false });

  const invalidEvent = form.dispatch('submit');
  assert.equal(invalidEvent.defaultPrevented, false);
  assert.deepEqual(calls, []);

  form.valid = true;
  const validEvent = form.dispatch('submit');
  form.dispatch('submit');

  assert.equal(validEvent.defaultPrevented, false);
  assert.deepEqual(calls, [[
    'event',
    'trial_form_submit_attempt',
    { source_path: '/pricing/', form_id: 'trial-form' },
  ]]);
});
