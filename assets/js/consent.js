/* Tarteel House analytics consent. Basic Consent: GA4 loads only after acceptance. */
(function (factory) {
  const consent = factory();

  if (typeof module === 'object' && module.exports) {
    module.exports = consent;
    return;
  }

  window.TarteelHouseConsent = Object.freeze({
    readSavedPreference: consent.readSavedPreference,
  });

  const start = () => consent.init(window, document);
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
}(function () {
  'use strict';

  const STORAGE_KEY = 'tarteelhouse.analyticsConsent';
  const MEASUREMENT_ID = 'G-ZVLW7QGYR1';
  const VALID_STATUSES = new Set(['granted', 'denied']);
  const BANNER_ID = 'analytics-consent';
  const TITLE_ID = 'analytics-consent-title';

  function createPreference(status, now = Date.now()) {
    if (!VALID_STATUSES.has(status)) throw new TypeError('Invalid analytics consent status');

    const expiry = new Date(now);
    expiry.setFullYear(expiry.getFullYear() + 1);
    return { status, expiresAt: expiry.getTime() };
  }

  function parsePreference(raw, now = Date.now()) {
    if (!raw) return null;
    try {
      const preference = JSON.parse(raw);
      if (!VALID_STATUSES.has(preference.status)) return null;
      if (!Number.isFinite(preference.expiresAt) || preference.expiresAt <= now) return null;
      return { status: preference.status, expiresAt: preference.expiresAt };
    } catch (error) {
      return null;
    }
  }

  function readSavedPreference(storage, now = Date.now()) {
    if (!storage) return null;
    try {
      const raw = storage.getItem(STORAGE_KEY);
      const preference = parsePreference(raw, now);
      if (raw && !preference) storage.removeItem(STORAGE_KEY);
      return preference;
    } catch (error) {
      return null;
    }
  }

  function savePreference(storage, status, now = Date.now()) {
    const preference = createPreference(status, now);
    if (storage) {
      try {
        storage.setItem(STORAGE_KEY, JSON.stringify(preference));
      } catch (error) {
        // Consent still applies to this document when storage is unavailable.
      }
    }
    return preference;
  }

  function loadAnalytics(win, doc) {
    if (win.__tarteelHouseGa4Initialized) return;
    win.__tarteelHouseGa4Initialized = true;

    win.dataLayer = win.dataLayer || [];
    win.gtag = win.gtag || function () {
      win.dataLayer.push(arguments);
    };
    win.gtag('js', new Date());
    win.gtag('config', MEASUREMENT_ID);

    const src = `https://www.googletagmanager.com/gtag/js?id=${MEASUREMENT_ID}`;
    if (!doc.querySelector(`script[src="${src}"]`)) {
      const script = doc.createElement('script');
      script.async = true;
      script.src = src;
      doc.head.appendChild(script);
    }
  }

  function analyticsCookieNames(cookieString) {
    if (!cookieString) return [];
    return Array.from(new Set(
      cookieString
        .split(';')
        .map(cookie => cookie.split('=')[0].trim())
        .filter(name => name === '_ga' || name.startsWith('_ga_')),
    ));
  }

  function cookieDomains(hostname) {
    if (!hostname || hostname === 'localhost' || /^\d+(?:\.\d+){3}$/.test(hostname)) return [''];
    const parts = hostname.split('.');
    const domains = ['', hostname, `.${hostname}`];
    if (parts.length > 2) {
      const parent = parts.slice(1).join('.');
      domains.push(parent, `.${parent}`);
    }
    return Array.from(new Set(domains));
  }

  function clearAnalyticsCookies(win, doc) {
    const names = analyticsCookieNames(doc.cookie);
    const domains = cookieDomains(win.location.hostname);
    const expired = 'Thu, 01 Jan 1970 00:00:00 GMT';

    names.forEach(name => {
      domains.forEach(domain => {
        const domainAttribute = domain ? `; Domain=${domain}` : '';
        doc.cookie = `${name}=; Max-Age=0; Expires=${expired}; Path=/${domainAttribute}; SameSite=Lax`;
      });
    });
  }

  function makeElement(doc, tag, className, text) {
    const element = doc.createElement(tag);
    if (className) element.className = className;
    if (text) element.textContent = text;
    return element;
  }

  function buildInterface(doc) {
    const banner = makeElement(doc, 'section', 'consent-banner');
    banner.id = BANNER_ID;
    banner.hidden = true;
    banner.setAttribute('aria-labelledby', TITLE_ID);

    const inner = makeElement(doc, 'div', 'consent-banner__inner');
    const copy = makeElement(doc, 'div', 'consent-banner__copy');
    const title = makeElement(doc, 'h2', 'consent-banner__title', 'Your privacy choices');
    title.id = TITLE_ID;
    title.tabIndex = -1;
    const body = makeElement(
      doc,
      'p',
      'consent-banner__body',
      'We use optional analytics cookies to understand how visitors use our website and improve Tarteel House. You can accept or reject analytics. Your choice can be changed at any time.',
    );
    const privacy = makeElement(doc, 'a', 'consent-banner__privacy', 'Privacy Policy');
    privacy.href = '/privacy-policy/';

    const actions = makeElement(doc, 'div', 'consent-banner__actions');
    const accept = makeElement(doc, 'button', 'consent-banner__button', 'Accept analytics');
    accept.type = 'button';
    accept.dataset.consentChoice = 'granted';
    const reject = makeElement(doc, 'button', 'consent-banner__button', 'Reject analytics');
    reject.type = 'button';
    reject.dataset.consentChoice = 'denied';

    copy.append(title, body, privacy);
    actions.append(accept, reject);
    inner.append(copy, actions);
    banner.append(inner);
    doc.body.append(banner);

    const settings = makeElement(doc, 'button', 'footer__cookie-settings', 'Cookie settings');
    settings.type = 'button';
    settings.setAttribute('aria-controls', BANNER_ID);
    settings.setAttribute('aria-expanded', 'false');
    const footerBottom = doc.querySelector('.footer__bottom');
    if (footerBottom) footerBottom.append(settings);

    return { banner, title, accept, reject, settings };
  }

  function getStorage(win) {
    try {
      return win.localStorage;
    } catch (error) {
      return null;
    }
  }

  function init(win, doc) {
    const storage = getStorage(win);
    let preference = readSavedPreference(storage);
    const ui = buildInterface(doc);

    const show = (moveFocus = false) => {
      ui.banner.hidden = false;
      ui.settings.setAttribute('aria-expanded', 'true');
      if (moveFocus) ui.title.focus();
    };
    const hide = () => {
      ui.banner.hidden = true;
      ui.settings.setAttribute('aria-expanded', 'false');
    };

    ui.settings.addEventListener('click', () => show(true));
    ui.accept.addEventListener('click', () => {
      preference = savePreference(storage, 'granted');
      loadAnalytics(win, doc);
      hide();
      ui.settings.focus({ preventScroll: true });
    });
    ui.reject.addEventListener('click', () => {
      const analyticsWasActive = preference?.status === 'granted' || Boolean(win.__tarteelHouseGa4Initialized);
      preference = savePreference(storage, 'denied');
      clearAnalyticsCookies(win, doc);
      hide();

      if (analyticsWasActive) {
        win.location.reload();
      } else {
        ui.settings.focus({ preventScroll: true });
      }
    });

    if (!preference) {
      show();
    } else if (preference.status === 'granted') {
      loadAnalytics(win, doc);
    }
  }

  return {
    STORAGE_KEY,
    MEASUREMENT_ID,
    analyticsCookieNames,
    clearAnalyticsCookies,
    createPreference,
    init,
    loadAnalytics,
    parsePreference,
    readSavedPreference,
    savePreference,
  };
}));
