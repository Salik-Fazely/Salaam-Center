const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');


const source = fs.readFileSync(path.join(__dirname, '../assets/js/main.js'), 'utf8');


function eventTarget() {
  const listeners = new Map();
  return {
    addEventListener(type, listener, options = {}) {
      const registered = listeners.get(type) || [];
      registered.push({ listener, once: Boolean(options.once) });
      listeners.set(type, registered);
    },
    dispatch(type, event = {}) {
      for (const entry of [...(listeners.get(type) || [])]) {
        entry.listener(event);
        if (entry.once) {
          const registered = listeners.get(type) || [];
          listeners.set(type, registered.filter(candidate => candidate !== entry));
        }
      }
    },
  };
}


function classList(initial = []) {
  const classes = new Set(initial);
  return {
    add(...names) { names.forEach(name => classes.add(name)); },
    remove(...names) { names.forEach(name => classes.delete(name)); },
    contains(name) { return classes.has(name); },
    toggle(name, force) {
      const enabled = force === undefined ? !classes.has(name) : Boolean(force);
      if (enabled) classes.add(name);
      else classes.delete(name);
      return enabled;
    },
  };
}


function element({ attrs = {}, classes = [], dataset = {} } = {}) {
  const target = eventTarget();
  const node = {
    ...target,
    attrs: new Map(Object.entries(attrs)),
    classList: classList(classes),
    className: classes.join(' '),
    children: [],
    dataset: { ...dataset },
    hidden: false,
    focused: false,
    focusOptions: null,
    replacement: null,
    style: {},
    append(...children) { node.children.push(...children); },
    focus(options = {}) {
      node.focused = true;
      node.focusOptions = options;
      node.dispatch('focus');
    },
    replaceWith(replacement) { node.replacement = replacement; },
    setAttribute(name, value) { node.attrs.set(name, String(value)); },
    getAttribute(name) { return node.attrs.get(name) ?? null; },
    hasAttribute(name) { return node.attrs.has(name); },
  };
  return node;
}


function fixture({ reducedMotion = true, videos = [] } = {}) {
  const documentTarget = eventTarget();
  const windowTarget = eventTarget();
  const animationFrames = [];
  const createdElements = [];
  const firstItem = element({ classes: ['faq-item'] });
  const secondItem = element({ classes: ['faq-item'] });
  const firstPanel = element({ attrs: { id: 'faq-panel-one' }, classes: ['faq-answer'] });
  const secondPanel = element({ attrs: { id: 'faq-panel-two' }, classes: ['faq-answer'] });
  firstPanel.hidden = true;
  secondPanel.hidden = true;

  const firstTrigger = element({
    attrs: { 'aria-controls': 'faq-panel-one', 'aria-expanded': 'false' },
    classes: ['faq-question'],
  });
  const secondTrigger = element({
    attrs: { 'aria-controls': 'faq-panel-two', 'aria-expanded': 'false' },
    classes: ['faq-question'],
  });
  firstTrigger.closest = selector => selector === '.faq-item' ? firstItem : null;
  secondTrigger.closest = selector => selector === '.faq-item' ? secondItem : null;

  const firstSection = element();
  const secondSection = element();
  const priceCard = element({ classes: ['price-card'] });
  const observed = [];
  class Observer {
    constructor(callback) { this.callback = callback; }
    observe(target) { observed.push(target); }
    unobserve() {}
  }

  const videoTriggers = videos.map(({ id, title }) => element({
    classes: ['video-preview'],
    dataset: { youtubeId: id, youtubeTitle: title },
  }));

  const selectorResults = new Map([
    ['.faq-question', [firstTrigger, secondTrigger]],
    ['.nav__link', []],
    ['[data-youtube-id]', videoTriggers],
    ['[data-feedback-carousel]', []],
    ['main > section', [firstSection, secondSection]],
    ['.teacher-card', []],
    ['.feedback-video-card', []],
    ['.price-card', [priceCard]],
    ['.trust-stats__item', []],
    ['.trust-stats__value[data-count-to]', []],
    ['.trust-stats', []],
  ]);
  const document = {
    ...documentTarget,
    body: element(),
    getElementById(id) {
      return {
        'faq-panel-one': firstPanel,
        'faq-panel-two': secondPanel,
      }[id] || null;
    },
    createElement(tagName) {
      const created = element();
      created.tagName = tagName.toUpperCase();
      createdElements.push(created);
      return created;
    },
    querySelectorAll(selector) { return selectorResults.get(selector) || []; },
  };
  const window = {
    ...windowTarget,
    IntersectionObserver: Observer,
    location: {
      pathname: '/',
      href: 'https://www.tarteelhouse.com/',
      origin: 'https://www.tarteelhouse.com',
      search: '',
      hash: '',
      replace() {},
    },
    matchMedia(query) {
      return {
        matches: query === '(prefers-reduced-motion: reduce)' ? reducedMotion : false,
        addEventListener() {},
        addListener() {},
      };
    },
    setTimeout() {},
  };

  vm.runInNewContext(source, {
    document,
    window,
    URL,
    IntersectionObserver: Observer,
    performance: { now: () => 0 },
    requestAnimationFrame(callback) { animationFrames.push(callback); },
  });
  document.dispatch('DOMContentLoaded');

  return {
    firstItem,
    firstPanel,
    firstSection,
    firstTrigger,
    createdElements,
    flushAnimationFrames() {
      while (animationFrames.length) animationFrames.shift()();
    },
    observed,
    priceCard,
    secondItem,
    secondPanel,
    secondSection,
    secondTrigger,
    videoTriggers,
  };
}


test('FAQ disclosure keeps hidden, expanded, and visual states synchronized', () => {
  const view = fixture();

  view.firstTrigger.dispatch('click');
  assert.equal(view.firstTrigger.getAttribute('aria-expanded'), 'true');
  assert.equal(view.firstPanel.hidden, false);
  assert.equal(view.firstItem.classList.contains('is-open'), true);

  view.secondTrigger.dispatch('click');
  assert.equal(view.firstTrigger.getAttribute('aria-expanded'), 'false');
  assert.equal(view.firstPanel.hidden, true);
  assert.equal(view.firstItem.classList.contains('is-open'), false);
  assert.equal(view.secondTrigger.getAttribute('aria-expanded'), 'true');
  assert.equal(view.secondPanel.hidden, false);
  assert.equal(view.secondItem.classList.contains('is-open'), true);

  view.secondTrigger.dispatch('click');
  assert.equal(view.secondTrigger.getAttribute('aria-expanded'), 'false');
  assert.equal(view.secondPanel.hidden, true);
  assert.equal(view.secondItem.classList.contains('is-open'), false);
});


test('reduced motion leaves sections immediately visible and unobserved', () => {
  const view = fixture({ reducedMotion: true });

  assert.equal(view.firstSection.classList.contains('reveal-section'), false);
  assert.equal(view.secondSection.classList.contains('reveal-section'), false);
  assert.deepEqual(view.observed, []);
});


test('normal motion reveals sections and current price cards', () => {
  const view = fixture({ reducedMotion: false });

  assert.equal(view.firstSection.classList.contains('is-revealed'), true);
  assert.equal(view.secondSection.classList.contains('reveal-section'), true);
  assert.equal(view.priceCard.classList.contains('reveal-card'), true);
  assert.deepEqual(view.observed, [view.secondSection, view.priceCard]);
});


test('video activation uses the privacy-enhanced embed and transfers focus', () => {
  const view = fixture({
    videos: [{ id: 'to3h-qq7_FM', title: 'Student message 1' }],
  });
  const trigger = view.videoTriggers[0];

  trigger.dispatch('click');

  assert.ok(trigger.replacement);
  assert.equal(trigger.replacement.children.length, 1);
  const iframe = trigger.replacement.children[0];
  assert.match(iframe.src, /^https:\/\/www\.youtube-nocookie\.com\/embed\/to3h-qq7_FM\?/);
  assert.equal(iframe.title, 'Student message 1');
  assert.equal(iframe.tabIndex, 0);
  assert.equal(iframe.focused, false);

  view.flushAnimationFrames();

  assert.equal(iframe.focused, true);
  assert.equal(iframe.focusOptions.preventScroll, true);
  assert.equal(iframe.classList.contains('has-focus'), true);

  iframe.dispatch('blur');
  assert.equal(iframe.classList.contains('has-focus'), false);

  trigger.dispatch('click');
  assert.equal(view.createdElements.filter(node => node.tagName === 'IFRAME').length, 1);
});


test('invalid video data leaves the preview reusable and does not create an iframe', () => {
  const view = fixture({
    videos: [
      { id: 'bad-id', title: 'Student message 1' },
      { id: '6WxiPdZNcCY', title: '   ' },
    ],
  });
  const [badIdTrigger, missingTitleTrigger] = view.videoTriggers;

  badIdTrigger.dispatch('click');
  missingTitleTrigger.dispatch('click');

  assert.equal(badIdTrigger.replacement, null);
  assert.equal(missingTitleTrigger.replacement, null);
  assert.equal(view.createdElements.filter(node => node.tagName === 'IFRAME').length, 0);

  badIdTrigger.dataset.youtubeId = 'to3h-qq7_FM';
  missingTitleTrigger.dataset.youtubeTitle = 'Student message 2';
  badIdTrigger.dispatch('click');
  missingTitleTrigger.dispatch('click');

  assert.ok(badIdTrigger.replacement);
  assert.ok(missingTitleTrigger.replacement);
  assert.equal(view.createdElements.filter(node => node.tagName === 'IFRAME').length, 2);
});
