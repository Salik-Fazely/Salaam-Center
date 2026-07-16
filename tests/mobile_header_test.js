const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');


const source = fs.readFileSync(path.join(__dirname, '../assets/js/main.js'), 'utf8');


function createEventTarget() {
  const listeners = new Map();

  return {
    addEventListener(type, listener) {
      const registered = listeners.get(type) || [];
      registered.push(listener);
      listeners.set(type, registered);
    },
    dispatch(type, event = {}) {
      for (const listener of listeners.get(type) || []) {
        listener(event);
      }
    },
  };
}


function createClassList(initial = []) {
  const classes = new Set(initial);

  return {
    add(...names) {
      names.forEach(name => classes.add(name));
    },
    remove(...names) {
      names.forEach(name => classes.delete(name));
    },
    contains(name) {
      return classes.has(name);
    },
    toggle(name, force) {
      const enabled = force === undefined ? !classes.has(name) : Boolean(force);
      if (enabled) classes.add(name);
      else classes.delete(name);
      return enabled;
    },
  };
}


function createFixture({ mobile = true } = {}) {
  const documentTarget = createEventTarget();
  const mediaTarget = createEventTarget();
  const windowTarget = createEventTarget();
  const attributes = element => ({
    setAttribute(name, value) {
      element.attrs.set(name, String(value));
    },
    getAttribute(name) {
      return element.attrs.get(name) ?? null;
    },
    removeAttribute(name) {
      element.attrs.delete(name);
    },
    toggleAttribute(name, force) {
      if (force) element.attrs.set(name, '');
      else element.attrs.delete(name);
    },
    hasAttribute(name) {
      return element.attrs.has(name);
    },
  });

  const document = {
    ...documentTarget,
    activeElement: null,
    querySelectorAll(selector) {
      return selector === '.nav__link' ? links : [];
    },
  };

  function element({ tagName = 'DIV', attrs = {}, classes = [] } = {}) {
    const target = createEventTarget();
    const node = {
      ...target,
      tagName,
      attrs: new Map(Object.entries(attrs)),
      classList: createClassList(classes),
      hidden: false,
      inert: false,
      focus() {
        document.activeElement = node;
      },
      closest(selector) {
        return selector === 'a[href]' && tagName === 'A' ? node : null;
      },
    };
    return Object.assign(node, attributes(node));
  }

  const firstLink = element({ tagName: 'A', attrs: { href: '/how-it-works/' }, classes: ['nav__link'] });
  const secondLink = element({ tagName: 'A', attrs: { href: '/teachers/' }, classes: ['nav__link'] });
  const links = [firstLink, secondLink];
  const navMenu = element({ tagName: 'UL', attrs: { id: 'nav-menu' }, classes: ['nav__links'] });
  navMenu.querySelector = selector => selector === 'a[href]' ? firstLink : null;
  const navToggle = element({
    tagName: 'BUTTON',
    attrs: {
      id: 'nav-toggle',
      'aria-controls': 'nav-menu',
      'aria-expanded': 'false',
      'aria-label': 'Open navigation menu',
    },
    classes: ['nav__toggle'],
  });

  document.getElementById = id => ({ 'nav-toggle': navToggle, 'nav-menu': navMenu })[id] || null;

  const mobileQuery = {
    ...mediaTarget,
    matches: mobile,
    setMatches(matches) {
      mobileQuery.matches = matches;
      mobileQuery.dispatch('change', { matches });
    },
  };
  const window = {
    ...windowTarget,
    location: {
      pathname: '/',
      href: 'https://www.tarteelhouse.com/',
      origin: 'https://www.tarteelhouse.com',
      replace() {},
    },
    matchMedia(query) {
      if (query === '(max-width: 767px)') return mobileQuery;
      return { matches: true, addEventListener() {} };
    },
  };

  vm.runInNewContext(source, { document, window, URL });
  document.dispatch('DOMContentLoaded');

  return { document, firstLink, mobileQuery, navMenu, navToggle, window };
}


test('mobile menu initializes closed and unavailable to focus or assistive technology', () => {
  const { navMenu, navToggle } = createFixture();

  assert.equal(navToggle.getAttribute('aria-expanded'), 'false');
  assert.equal(navToggle.getAttribute('aria-label'), 'Open navigation menu');
  assert.equal(navMenu.hidden, true);
  assert.equal(navMenu.inert, true);
  assert.equal(navMenu.hasAttribute('inert'), true);
  assert.equal(navMenu.classList.contains('is-open'), false);
});


test('opening the mobile menu synchronizes state and focuses the first navigation link', () => {
  const { document, firstLink, navMenu, navToggle } = createFixture();

  navToggle.dispatch('click');

  assert.equal(navToggle.getAttribute('aria-expanded'), 'true');
  assert.equal(navToggle.getAttribute('aria-label'), 'Close navigation menu');
  assert.equal(navMenu.hidden, false);
  assert.equal(navMenu.inert, false);
  assert.equal(navMenu.hasAttribute('inert'), false);
  assert.equal(navMenu.classList.contains('is-open'), true);
  assert.equal(document.activeElement, firstLink);
});


test('Escape closes the mobile menu and returns focus to its trigger', () => {
  const { document, navMenu, navToggle } = createFixture();
  navToggle.dispatch('click');

  document.dispatch('keydown', { key: 'Escape' });

  assert.equal(navToggle.getAttribute('aria-expanded'), 'false');
  assert.equal(navMenu.hidden, true);
  assert.equal(navMenu.inert, true);
  assert.equal(navMenu.classList.contains('is-open'), false);
  assert.equal(document.activeElement, navToggle);
});


test('activating a mobile navigation link closes the menu', () => {
  const { firstLink, navMenu, navToggle } = createFixture();
  navToggle.dispatch('click');

  navMenu.dispatch('click', { target: firstLink });

  assert.equal(navToggle.getAttribute('aria-expanded'), 'false');
  assert.equal(navMenu.hidden, true);
  assert.equal(navMenu.inert, true);
  assert.equal(navMenu.classList.contains('is-open'), false);
});


test('crossing to desktop clears stale mobile state and exposes desktop links', () => {
  const { mobileQuery, navMenu, navToggle, window } = createFixture();
  navToggle.dispatch('click');

  mobileQuery.matches = false;
  window.dispatch('resize');

  assert.equal(navToggle.getAttribute('aria-expanded'), 'false');
  assert.equal(navToggle.getAttribute('aria-label'), 'Open navigation menu');
  assert.equal(navMenu.classList.contains('is-open'), false);
  assert.equal(navMenu.hidden, false);
  assert.equal(navMenu.inert, false);
  assert.equal(navMenu.hasAttribute('inert'), false);
});


test('desktop initialization leaves the navigation available without stale mobile state', () => {
  const { navMenu, navToggle } = createFixture({ mobile: false });

  assert.equal(navToggle.getAttribute('aria-expanded'), 'false');
  assert.equal(navMenu.classList.contains('is-open'), false);
  assert.equal(navMenu.hidden, false);
  assert.equal(navMenu.inert, false);
  assert.equal(navMenu.hasAttribute('inert'), false);
});
