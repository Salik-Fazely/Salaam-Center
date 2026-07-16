/**
 * Tarteel House — booking submission handler.
 *
 * Source of truth for the Apps Script Web App that receives form posts
 * from book-trial. Paste the contents of this file into the
 * Apps Script editor (Code.gs) that is bound to the Bookings spreadsheet,
 * save, and redeploy the existing Web App version.
 *
 * The form URL on the site does NOT change when you redeploy the same
 * project — only the script behind it is updated.
 */

// ---------------------------------------------------------------------------
// Config — change the email below to wherever bookings should be sent.
// ---------------------------------------------------------------------------
const CONFIG = {
  SHEET_NAME: 'Bookings',
  NOTIFICATION_EMAIL: 'hello@tarteelhouse.com',
  SUCCESS_REDIRECT: 'https://www.tarteelhouse.com/success/',
  ALLOWED_REDIRECT_HOSTS: [
    'www.tarteelhouse.com'
  ]
};

// Column order used when writing a new booking row. If the sheet already
// has a header row, any missing columns below are appended to the right
// so existing data is never disturbed.
const HEADERS = [
  'timestamp',
  'source',
  'parent_name',
  'child_name',
  'child_age',
  'quran_level',
  'session_language',
  'country',
  'email',
  'whatsapp',
  'preferred_days',
  'preferred_time',
  'city_region',
  'notes',
  'consent',
  // Operational columns — the founder fills these in manually.
  'status',
  'assigned_teacher',
  'follow_up_date',
  'internal_notes'
];

const REQUIRED_FIELDS = [
  { name: 'parent_name',      label: 'parent name' },
  { name: 'child_name',       label: 'child name' },
  { name: 'child_age',        label: 'child age' },
  { name: 'quran_level',      label: 'current Qur\'an level' },
  { name: 'session_language', label: 'preferred session language' },
  { name: 'country',          label: 'country' },
  { name: 'email',            label: 'email address' },
  { name: 'whatsapp',         label: 'WhatsApp number' },
  { name: 'preferred_days',   label: 'preferred days' },
  { name: 'preferred_time',   label: 'preferred time of day' },
  { name: 'city_region',      label: 'city / region' }
];

const ALLOWED_VALUES = {
  country: [
    'Germany',
    'France',
    'Netherlands',
    'Belgium',
    'Sweden',
    'Norway',
    'Denmark',
    'Switzerland',
    'Austria',
    'United Kingdom',
    'Ireland',
    'Spain',
    'Italy',
    'Canada',
    'United States',
    'Other'
  ],
  child_age: [
    '5', '6', '7', '8', '9', '10', '11',
    '12', '13', '14', '15', '16'
  ],
  quran_level: [
    'complete-beginner',
    'knows-arabic-letters',
    'reading-short-words',
    'reading-independently'
  ],
  session_language: ['english', 'arabic', 'turkish', 'persian'],
  preferred_days: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'],
  preferred_time: ['morning', 'afternoon', 'evening']
};

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------
function doPost(e) {
  try {
    const params = (e && e.parameter) || {};

    // Honeypot: real users never fill this field.
    if (params.website_field) {
      return htmlRedirect_(params);
    }

    const validation = validateBooking_(params);
    if (!validation.valid) {
      return htmlError_(validation.errors);
    }

    const sheet = getOrCreateSheet_();
    ensureHeaders_(sheet);
    appendRow_(sheet, params);
    sendNotification_(params);

    return htmlRedirect_(params);
  } catch (err) {
    console.error('Booking submission error:', err);
    // Do not show success unless the booking was saved and notification attempted.
    return htmlError_(
      ['We could not complete your booking request right now. Please try again, or message us on WhatsApp if the problem continues.'],
      'Booking request could not be completed',
      'Please go back and submit the form again. If the problem continues, contact us directly on WhatsApp.'
    );
  }
}

// Optional: also allow GET to the Web App URL to return a friendly page
// instead of a raw Apps Script error, in case someone pastes the URL.
function doGet() {
  return HtmlService
    .createHtmlOutput('<p>Tarteel House booking endpoint.</p>');
}

// ---------------------------------------------------------------------------
// Sheet helpers
// ---------------------------------------------------------------------------
function getOrCreateSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(CONFIG.SHEET_NAME);
  if (!sheet) sheet = ss.insertSheet(CONFIG.SHEET_NAME);
  return sheet;
}

function ensureHeaders_(sheet) {
  const lastCol = sheet.getLastColumn();

  if (lastCol === 0) {
    sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
    sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold');
    sheet.setFrozenRows(1);
    return;
  }

  const existing = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  const missing = HEADERS.filter(function (h) {
    return existing.indexOf(h) === -1;
  });

  if (missing.length) {
    sheet.getRange(1, lastCol + 1, 1, missing.length).setValues([missing]);
    sheet.getRange(1, 1, 1, lastCol + missing.length).setFontWeight('bold');
  }
  if (sheet.getFrozenRows() < 1) sheet.setFrozenRows(1);
}

function appendRow_(sheet, params) {
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const row = headers.map(function (h) {
    if (h === 'timestamp')        return new Date();
    if (h === 'status')           return 'New lead';
    if (h === 'assigned_teacher') return '';
    if (h === 'follow_up_date')   return '';
    if (h === 'internal_notes')   return '';
    return params[h] != null ? params[h] : '';
  });
  sheet.appendRow(row);
}

// ---------------------------------------------------------------------------
// Validation helpers.
// ---------------------------------------------------------------------------
function validateBooking_(params) {
  const errors = [];

  REQUIRED_FIELDS.forEach(function (field) {
    if (!hasValue_(params[field.name])) {
      errors.push('Missing ' + field.label + '.');
    }
  });

  if (params.consent !== 'yes') {
    errors.push('Privacy consent is required.');
  }

  if (hasValue_(params.email) && !isValidEmail_(params.email)) {
    errors.push('Email address is not valid.');
  }

  validateAllowedSingle_(params, 'child_age', 'child age', errors);
  validateAllowedSingle_(params, 'country', 'country', errors);
  validateAllowedSingle_(params, 'quran_level', 'current Qur\'an level', errors);
  validateAllowedSingle_(params, 'session_language', 'preferred session language', errors);
  validateAllowedSingle_(params, 'preferred_time', 'preferred time of day', errors);
  validateAllowedList_(params, 'preferred_days', 'preferred days', errors);

  return {
    valid: errors.length === 0,
    errors: errors
  };
}

function hasValue_(value) {
  return value != null && String(value).trim() !== '';
}

function isValidEmail_(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value).trim());
}

function validateAllowedSingle_(params, name, label, errors) {
  if (!hasValue_(params[name])) return;
  const value = String(params[name]).trim();
  if (ALLOWED_VALUES[name].indexOf(value) === -1) {
    errors.push('Invalid ' + label + '.');
  }
}

function validateAllowedList_(params, name, label, errors) {
  if (!hasValue_(params[name])) return;
  const values = String(params[name])
    .split(',')
    .map(function (value) { return value.trim(); })
    .filter(function (value) { return value !== ''; });

  if (!values.length) {
    errors.push('Missing ' + label + '.');
    return;
  }

  const hasInvalid = values.some(function (value) {
    return ALLOWED_VALUES[name].indexOf(value) === -1;
  });

  if (hasInvalid) {
    errors.push('Invalid ' + label + '.');
  }
}

// Email notification.
function sendNotification_(p) {
  const subject =
    'New trial booking — ' +
    (p.parent_name || 'Unknown parent') +
    ' / ' + (p.child_name || '');

  const lines = [
    'A new trial booking has come in.',
    '',
    '— Parent —',
    'Name:      ' + (p.parent_name || '—'),
    'Email:     ' + (p.email || '—'),
    'WhatsApp:  ' + (p.whatsapp || '—'),
    'Country:   ' + (p.country || '—'),
    'City / Region: ' + (p.city_region || '—'),
    '',
    '— Child —',
    'Name:      ' + (p.child_name || '—'),
    'Age:       ' + (p.child_age || '—'),
    'Level:     ' + (p.quran_level || '—'),
    'Language:  ' + (p.session_language || '—'),
    '',
    '— Scheduling —',
    'Days:      ' + (p.preferred_days || '—'),
    'Time:      ' + (p.preferred_time || '—'),
    '',
    '— Notes —',
    (p.notes && String(p.notes).trim()) ? p.notes : '(none)',
    '',
    '—',
    'Submitted: ' + new Date().toString()
  ];

  MailApp.sendEmail({
    to: CONFIG.NOTIFICATION_EMAIL,
    subject: subject,
    body: lines.join('\n'),
    replyTo: p.email || undefined,
    name: 'Tarteel House bookings'
  });
}

// ---------------------------------------------------------------------------
// Redirect response — shown briefly on script.googleusercontent.com before
// the browser lands on success.
// ---------------------------------------------------------------------------
function htmlRedirect_(params) {
  const url = getSuccessRedirect_(params);
  const safe = JSON.stringify(url);
  const escaped = escapeHtml_(url);
  const html =
    '<!doctype html>' +
    '<meta charset="utf-8">' +
    '<meta http-equiv="refresh" content="0;url=' + escaped + '">' +
    '<title>Redirecting…</title>' +
    '<script>window.location.replace(' + safe + ');</script>' +
    '<p style="font-family:system-ui;padding:2rem;">' +
      'Thank you. Redirecting to <a href="' + escaped + '">' + escaped + '</a>…' +
    '</p>';
  return HtmlService
    .createHtmlOutput(html)
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// ---------------------------------------------------------------------------
// Error response and redirect helpers.
// ---------------------------------------------------------------------------
function htmlError_(errors, title, message) {
  const pageTitle = title || 'Booking details missing';
  const heading = title || 'Some booking details are missing';
  const body = message || 'Please go back, complete the required details, and submit the form again.';
  const items = errors.map(function (error) {
    return '<li>' + escapeHtml_(error) + '</li>';
  }).join('');

  const html =
    '<!doctype html>' +
    '<meta charset="utf-8">' +
    '<title>' + escapeHtml_(pageTitle) + '</title>' +
    '<div style="font-family:system-ui;padding:2rem;line-height:1.6;max-width:42rem;">' +
      '<h1 style="font-size:1.25rem;">' + escapeHtml_(heading) + '</h1>' +
      '<p>' + escapeHtml_(body) + '</p>' +
      '<ul>' + items + '</ul>' +
      '<p><button onclick="history.back()">Go back to the form</button></p>' +
    '</div>';

  return HtmlService
    .createHtmlOutput(html)
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function getSuccessRedirect_(params) {
  const candidate = params && params.success_redirect;
  if (isAllowedSuccessRedirect_(candidate)) return String(candidate).trim();
  return CONFIG.SUCCESS_REDIRECT;
}

function isAllowedSuccessRedirect_(value) {
  if (!hasValue_(value)) return false;

  const match = String(value).trim().match(/^(https?):\/\/([^/?#]+)(\/[^?#]*)/i);
  if (!match) return false;

  const protocol = match[1].toLowerCase() + ':';
  const host = match[2].toLowerCase().split(':')[0];
  const path = match[3].toLowerCase().replace(/\/+$/, '');

  if (protocol !== 'https:' && protocol !== 'http:') return false;
  if (path !== '/success') return false;
  if (host === 'localhost' || host === '127.0.0.1') return true;

  return CONFIG.ALLOWED_REDIRECT_HOSTS.indexOf(host) !== -1;
}

function escapeHtml_(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ---------------------------------------------------------------------------
// Run once manually to seed the header row on an empty sheet, or to add
// operational columns (status / assigned_teacher / follow_up_date /
// internal_notes) to an existing sheet without submitting a test booking.
// In the Apps Script editor: select `initializeSheet` in the function
// dropdown, then click Run.
// ---------------------------------------------------------------------------
function initializeSheet() {
  const sheet = getOrCreateSheet_();
  ensureHeaders_(sheet);
}
