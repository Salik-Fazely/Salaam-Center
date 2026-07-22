# Salaam Center Dari Localization Guide

This is the concise implementation reference for maintaining translation parity. Approved commercial, legal, safeguarding, teacher and media facts remain authoritative in `SALAM-CENTER-APPROVED-FACTS.md`.

## Language and routes

- Afghan Dari uses `fa-AF`, `dir="rtl"`, and the default root route tree.
- English uses `en`, `dir="ltr"`, and the equivalent `/en/` route tree.
- `config/localized-routes.json` is the route-pair source of truth. A switch must link to the exact counterpart, never a generic language homepage when a counterpart exists.
- Visitors control language with ordinary anchors. There is no browser/IP detection, automatic redirect, cookie, `localStorage`, or `sessionStorage` preference.

## Brand and glossary

- Keep the canonical Latin brand **Salaam Center**. It may be introduced naturally once as «سلام سنتر», but the organization and logo identity are not renamed.
- Use **دری** for the language, **برنامه‌ها** for programs, **قیمت‌ها** for pricing, **صنف خصوصی** for private class, **استاد/استادان** for teacher(s), **جلسهٔ آزمایشی رایگان** for free trial, **والد یا سرپرست** for parent or guardian, **شرایط و مقررات** for Terms, and **سیاست حفظ حریم خصوصی** for Privacy Policy.
- Write natural, calm Afghan Dari for families abroad. Avoid Iranian institutional wording where a familiar Afghan Dari expression exists, and do not add pressure, guilt, guarantees, or stronger legal/commercial promises.

## Numerals, names, and bidirectional text

- Retain Latin numerals for euro prices, established class counts, legal dates, telephone numbers, video IDs, and technical values: `€49`, `40 دقیقه`, `12 هفته`, `+34 614 401 172`.
- Wrap prices, telephone numbers, URLs, and substantial Latin fragments in LTR `<bdi>` or an equivalent isolated element.
- Keep canonical proper names exactly when no approved Dari spelling exists. Teacher identities remain `Farkhonda Jami`, `Foruhar Rahmani`, `Fareshta Suroush`, and `Sadiah Hamid`, isolated with `lang="en"` and `dir="ltr"`.
- Do not mirror logos, photographs, thumbnails, videos, play symbols, telephone numbers, or euro amounts.

## Font and interface

- Dari uses the self-hosted official Vazirmatn variable font at `/assets/fonts/vazirmatn/Vazirmatn-Variable.woff2`, weight range `100 900`, with `font-display: swap`; the official `OFL.txt` remains beside it.
- Preload Vazirmatn on Dari documents only. Do not add a font CDN or change the approved English font behavior.
- Prefer CSS logical properties. Focus order follows document order in both languages; labels, help, errors, status text, accessibility names, mobile navigation, footer, and 404 actions must follow the document language.

## WhatsApp and parity

- Root `/book-trial/` prepares a Dari message; `/en/book-trial/` preserves the approved English message. Both use `34614401172`, prepare text locally, and require the adult visitor to press Send inside WhatsApp.
- Do not add a backend, automatic sending, storage, analytics, personal data in a page URL, or a false booking/submission confirmation.
- Every localized page must preserve approved factual meaning. Prices, class counts, savings, duration, validity, cancellation rules, certificate limits, consumer rights, legal operator/location/date, safeguarding, teacher identities, biographies, and all six video IDs must remain equivalent.
- Canonicals are self-referencing. Each pair has reciprocal `fa-AF` and `en` hreflang; `x-default` points to Dari. The sitemap contains 28 indexable localized URLs; both Success routes and both 404 templates remain excluded and `noindex, nofollow`.
- Search Console submission remains a separate manual task. Cloudflare Pages remains the production host; this language architecture requires no DNS or Cloudflare dashboard change.
