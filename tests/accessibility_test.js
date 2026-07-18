const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const script = fs.readFileSync(path.join(__dirname, '..', 'assets', 'js', 'main.js'), 'utf8');

function classList(initial = []) {
  const values = new Set(initial);
  return {
    add(name) { values.add(name); },
    remove(name) { values.delete(name); },
    contains(name) { return values.has(name); },
    toggle(name, force) {
      const enabled = force === undefined ? !values.has(name) : Boolean(force);
      if (enabled) values.add(name); else values.delete(name);
      return enabled;
    },
  };
}

function element({ tagName = 'DIV', classes = [], attrs = {}, dataset = {} } = {}) {
  const attributes = new Map(Object.entries(attrs));
  const listeners = new Map();
  const node = {
    tagName,
    className: classes.join(' '),
    classList: classList(classes),
    dataset: { ...dataset },
    hidden: false,
    inert: false,
    children: [],
    focused: false,
    focusOptions: null,
    replacedBy: null,
    addEventListener(type, listener) {
      const current = listeners.get(type) || [];
      current.push(listener);
      listeners.set(type, current);
    },
    dispatch(type, event = {}) {
      for (const listener of listeners.get(type) || []) listener({ target: node, ...event });
    },
    setAttribute(name, value) { attributes.set(name, String(value)); },
    getAttribute(name) { return attributes.has(name) ? attributes.get(name) : null; },
    toggleAttribute(name, force) {
      if (force) attributes.set(name, ''); else attributes.delete(name);
    },
    querySelector(selector) { return selector === 'a[href]' ? node.firstLink || null : null; },
    append(...children) { node.children.push(...children); },
    replaceWith(replacement) { node.replacedBy = replacement; },
    focus(options) {
      node.focused = true;
      node.focusOptions = options || null;
      node.dispatch('focus');
    },
  };
  return node;
}

function createView(videoOptions = null) {
  const firstLink = element({ tagName: 'A' });
  const navMenu = element({ tagName: 'UL', classes: ['nav__links'], attrs: { id: 'nav-menu' } });
  navMenu.firstLink = firstLink;
  const navToggle = element({
    tagName: 'BUTTON',
    attrs: { id: 'nav-toggle', 'aria-expanded': 'false', 'aria-label': 'Open navigation menu' },
  });
  const trigger = videoOptions
    ? element({
        tagName: 'BUTTON',
        classes: ['teacher-card__portrait'],
        dataset: {
          youtubeId: videoOptions.id,
          youtubeTitle: videoOptions.title,
        },
      })
    : null;

  const documentListeners = new Map();
  const windowListeners = new Map();
  const createdElements = [];
  const mediaListeners = [];
  const media = {
    matches: true,
    addEventListener(type, listener) { mediaListeners.push({ type, listener }); },
    addListener(listener) { mediaListeners.push({ type: 'change', listener }); },
  };

  const document = {
    addEventListener(type, listener) {
      const current = documentListeners.get(type) || [];
      current.push(listener);
      documentListeners.set(type, current);
    },
    dispatch(type, event = {}) {
      for (const listener of documentListeners.get(type) || []) listener(event);
    },
    getElementById(id) {
      if (id === 'nav-toggle') return navToggle;
      if (id === 'nav-menu') return navMenu;
      return null;
    },
    querySelectorAll(selector) {
      if (selector === '[data-youtube-id]' && trigger) return [trigger];
      return [];
    },
    createElement(tagName) {
      const created = element({ tagName: tagName.toUpperCase() });
      createdElements.push(created);
      return created;
    },
  };

  const window = {
    document,
    location: {
      pathname: '/',
      search: '',
      hash: '',
      origin: 'https://local.test',
      replace() {},
    },
    matchMedia() { return media; },
    addEventListener(type, listener) {
      const current = windowListeners.get(type) || [];
      current.push(listener);
      windowListeners.set(type, current);
    },
  };

  const context = vm.createContext({
    document,
    window,
    URL,
    requestAnimationFrame(callback) { callback(); },
  });
  vm.runInContext(script, context);
  document.dispatch('DOMContentLoaded');

  return { document, window, media, navMenu, navToggle, firstLink, trigger, createdElements };
}

test('mobile navigation initializes closed, hidden, and inert', () => {
  const view = createView();
  assert.equal(view.navMenu.classList.contains('is-enhanced'), true);
  assert.equal(view.navToggle.classList.contains('is-enhanced'), true);
  assert.equal(view.navMenu.hidden, true);
  assert.equal(view.navMenu.inert, true);
  assert.equal(view.navMenu.classList.contains('is-open'), false);
  assert.equal(view.navToggle.getAttribute('aria-expanded'), 'false');
  assert.equal(view.navToggle.getAttribute('aria-label'), 'Open navigation menu');
});

test('mobile navigation moves focus in on open and returns it on Escape', () => {
  const view = createView();
  view.navToggle.dispatch('click');
  assert.equal(view.navMenu.hidden, false);
  assert.equal(view.navMenu.inert, false);
  assert.equal(view.navToggle.getAttribute('aria-expanded'), 'true');
  assert.equal(view.firstLink.focused, true);

  view.document.dispatch('keydown', { key: 'Escape' });
  assert.equal(view.navMenu.hidden, true);
  assert.equal(view.navToggle.getAttribute('aria-expanded'), 'false');
  assert.equal(view.navToggle.focused, true);
});

test('video activation creates one named privacy-enhanced player and transfers focus', () => {
  const view = createView({ id: 'iUMB3pKzS_A', title: 'Farkhonda Jami lesson sample' });
  view.trigger.dispatch('click');
  const iframe = view.createdElements.find(item => item.tagName === 'IFRAME');
  assert.ok(iframe);
  assert.match(iframe.src, /^https:\/\/www\.youtube-nocookie\.com\/embed\/iUMB3pKzS_A\?/);
  assert.equal(iframe.title, 'Farkhonda Jami lesson sample');
  assert.equal(iframe.tabIndex, 0);
  assert.equal(iframe.referrerPolicy, 'strict-origin-when-cross-origin');
  assert.equal(iframe.allowFullscreen, true);
  assert.equal(iframe.focused, true);
  assert.equal(iframe.focusOptions.preventScroll, true);
  assert.ok(view.trigger.replacedBy);

  view.trigger.dispatch('click');
  assert.equal(view.createdElements.filter(item => item.tagName === 'IFRAME').length, 1);
});

test('invalid video data leaves the preview reusable', () => {
  const view = createView({ id: 'bad', title: '' });
  view.trigger.dispatch('click');
  assert.equal(view.trigger.replacedBy, null);
  assert.equal(view.createdElements.filter(item => item.tagName === 'IFRAME').length, 0);

  view.trigger.dataset.youtubeId = 'iUMB3pKzS_A';
  view.trigger.dataset.youtubeTitle = 'Farkhonda Jami lesson sample';
  view.trigger.dispatch('click');
  assert.ok(view.trigger.replacedBy);
  assert.equal(view.createdElements.filter(item => item.tagName === 'IFRAME').length, 1);
});

test('video focus and blur expose a visible player focus state', () => {
  const view = createView({ id: 'iUMB3pKzS_A', title: 'Farkhonda Jami lesson sample' });
  view.trigger.dispatch('click');
  const iframe = view.createdElements.find(item => item.tagName === 'IFRAME');
  assert.equal(iframe.classList.contains('has-focus'), true);
  iframe.dispatch('blur');
  assert.equal(iframe.classList.contains('has-focus'), false);
  iframe.dispatch('focus');
  assert.equal(iframe.classList.contains('has-focus'), true);
});
