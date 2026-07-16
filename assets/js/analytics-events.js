/* Tarteel House privacy-safe booking funnel events. */
(function (factory) {
  const analyticsEvents = factory();

  if (typeof module === 'object' && module.exports) {
    module.exports = analyticsEvents;
    return;
  }

  const start = () => analyticsEvents.init(window, document, window.TarteelHouseConsent);
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
}(function () {
  'use strict';

  const BOOKING_PATH = '/book-trial/';
  const FORM_ID = 'trial-form';
  const INIT_FLAG = '__tarteelHouseAnalyticsEventsInitialized';
  const NON_EDITABLE_INPUT_TYPES = new Set(['button', 'hidden', 'image', 'reset', 'submit']);

  function hasGrantedConsent(win, consentApi) {
    if (!consentApi || typeof consentApi.readSavedPreference !== 'function') return false;

    let storage;
    try {
      storage = win.localStorage;
    } catch (error) {
      return false;
    }

    const preference = consentApi.readSavedPreference(storage);
    return preference?.status === 'granted';
  }

  function sendEvent(win, consentApi, eventName, parameters) {
    if (!hasGrantedConsent(win, consentApi)) return false;
    if (!win.__tarteelHouseGa4Initialized || typeof win.gtag !== 'function') return false;

    try {
      win.gtag('event', eventName, parameters);
      return true;
    } catch (error) {
      return false;
    }
  }

  function normalizedBookingPath(pathname) {
    let normalized = pathname.replace(/\/index\.html$/i, '/');
    if (normalized.length > 1 && !normalized.endsWith('/')) normalized += '/';
    return normalized;
  }

  function ctaDestination(element) {
    if (element.tagName === 'A') return element.getAttribute('href');
    if (element.tagName === 'BUTTON') {
      return element.getAttribute('formaction') || element.getAttribute('data-href');
    }
    return null;
  }

  function bookingCta(win, target) {
    if (!target || typeof target.closest !== 'function') return null;

    const element = target.closest('a[href], button[formaction], button[data-href]');
    if (!element) return null;

    try {
      const destination = new URL(ctaDestination(element), win.location.href);
      if (destination.origin !== win.location.origin) return null;
      return normalizedBookingPath(destination.pathname) === BOOKING_PATH ? element : null;
    } catch (error) {
      return null;
    }
  }

  function normalizedCtaText(element) {
    const text = typeof element.innerText === 'string' ? element.innerText : element.textContent;
    return String(text || '').replace(/\s+/g, ' ').trim().slice(0, 100);
  }

  function isEditableControl(form, control) {
    if (!control || !form.contains(control) || control.disabled || control.readOnly) return false;

    const tagName = control.tagName?.toUpperCase();
    if (tagName === 'TEXTAREA' || tagName === 'SELECT') return true;
    if (tagName !== 'INPUT') return false;
    return !NON_EDITABLE_INPUT_TYPES.has(String(control.type || 'text').toLowerCase());
  }

  function init(win, doc, consentApi) {
    if (!win || !doc || win[INIT_FLAG]) return;
    win[INIT_FLAG] = true;

    doc.addEventListener('click', event => {
      const cta = bookingCta(win, event.target);
      if (!cta) return;

      sendEvent(win, consentApi, 'trial_cta_click', {
        source_path: win.location.pathname,
        destination_path: BOOKING_PATH,
        cta_text: normalizedCtaText(cta),
      });
    });

    const form = doc.getElementById(FORM_ID);
    if (!form) return;

    let formStarted = false;
    let submitAttempted = false;
    const handleFormStart = event => {
      if (formStarted || !isEditableControl(form, event.target)) return;
      formStarted = sendEvent(win, consentApi, 'trial_form_start', {
        source_path: win.location.pathname,
        form_id: FORM_ID,
      });
    };

    ['input', 'change', 'focusin'].forEach(type => form.addEventListener(type, handleFormStart));
    form.addEventListener('submit', () => {
      if (submitAttempted) return;
      if (typeof form.checkValidity === 'function' && !form.checkValidity()) return;

      submitAttempted = sendEvent(win, consentApi, 'trial_form_submit_attempt', {
        source_path: win.location.pathname,
        form_id: FORM_ID,
      });
    });
  }

  return { BOOKING_PATH, FORM_ID, init };
}));
