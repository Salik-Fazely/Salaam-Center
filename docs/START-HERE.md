# START HERE

This is the recovery and handoff file for Tarteel House. Read this first if context is lost or a new AI/session takes over.

## What this project is
Tarteel House is a premium online Qur'an learning website for Muslim families. Parents can learn about the service, view teachers, review pricing, and book a free trial for their child.

The product is trust-first: parents should feel calm, respected, and confident before submitting the booking form.

## Current stack
- Static HTML pages at the project root.
- One main stylesheet: `assets/css/styles.css`.
- Shared JavaScript: `assets/js/main.js`.
- Shared consent banner and preferences: `assets/js/consent.js`.
- Booking form page: `/book-trial`.
- Booking backend: Google Apps Script.
- Booking storage: Google Sheets.
- Backend source in repo: `apps-script/Code.gs`.
- Backend docs: `apps-script/README.md`.
- Static hosting configuration: GitHub Pages with the custom domain in `CNAME`.

## Current status
The static site, Blog, consent banner, booking form, and Apps Script source exist in the repository. Booking reliability, backend hardening, and a real end-to-end booking check remain postponed/open; repository code must not be treated as proof of current production behaviour.

The latest local code is not automatically live. Frontend changes must be pushed and published through the hosting workflow, and Apps Script changes require a separate manual deployment.

## Non-negotiable rules
- Do not change fonts casually.
- Do not change typography, spacing, colors, layout language, animations, or visual hierarchy unless explicitly asked.
- Do not redesign the site just because another design is possible.
- Preserve the current minimal, premium, warm, parent-friendly style.
- Keep edits small and practical.
- Prefer existing classes, tokens, and patterns.
- Do not introduce a new style system.
- Do not replace Google Apps Script as the launch backend unless explicitly requested.
- Do not invent business, legal, teacher, or operational facts.

## Confirmed facts
`docs/commercial-facts.md` is the authoritative source for public commercial and service claims.

- Public email: `hello@tarteelhouse.com`.
- Business location: Barcelona, Spain.
- Public WhatsApp / phone: `+34 614 494 311`.
- WhatsApp is the main contact method.
- WhatsApp is required in the booking form.
- Country is a required dropdown shortlist.
- City / Region is required and replaces the old timezone field.
- Families are normally contacted within two days to arrange the next steps. This is not a guaranteed service-level deadline.
- Lesson platform copy should say Zoom or Google Meet.
- Homepage stats are approved: 4 Teachers, 1-to-1 Lessons, 4 Teaching languages.
- Tarteel House serves girls and boys aged 5 to 16; adult classes are not currently offered.
- The free trial and every paid lesson are 40 minutes.
- Packages are EUR 120 / 6 lessons, EUR 220 / 12 lessons, and EUR 400 / 25 lessons. Every package is valid for one year from the purchase date.
- Every two months, we invite parents to a 15-minute progress review. If a parent is unavailable or does not want a meeting, we send a visual progress report through WhatsApp instead.
- The on-site payment system is not configured. After the trial, Tarteel House confirms the package and shares payment instructions or a secure payment link through WhatsApp; paid lessons are scheduled after payment confirmation.

## Main pages
- `/`: homepage.
- `/book-trial`: booking form.
- `/success`: post-booking confirmation page.
- `/teachers`: teacher profiles.
- `/pricing`: pricing.
- `/how-it-works`: process.
- `/about`: brand/about story.
- `/blog`: Blog index and published articles.
- `/privacy-policy`: legal privacy page.
- `/terms`: legal terms page.

## Repository booking flow (not production-verified)
Required fields:
- `parent_name`
- `child_name`
- `child_age`
- `quran_level`
- `session_language`
- `country`
- `email`
- `whatsapp`
- `preferred_days`
- `preferred_time`
- `city_region`
- `consent = yes`

Flow:
1. The parent-facing form is available at `/book-trial`.
2. The form is configured to post to a Google Apps Script Web App.
3. The repository Apps Script source is designed to validate required fields and allowed chip/dropdown values.
4. The repository source is designed to write a row to Google Sheets and email `hello@tarteelhouse.com`.
5. The intended completion path redirects the parent to `/success`.
6. The repository source is designed to return an error page when validation or backend completion fails.

## What is done
- Static site pages are built.
- Blog index and article pages are built.
- Visual brand system exists.
- Homepage trust stats band exists.
- Booking form has required WhatsApp, Country dropdown, City / Region, and chip validation.
- Apps Script source exists and includes server-side validation; live reliability and deployment remain unverified.
- Shared consent banner and persistent cookie settings control exist.
- Four teacher lesson-sample videos are present in the repository HTML.
- Unverified written testimonials were removed; the genuine student/family videos remain.
- Success page uses WhatsApp-first follow-up copy.
- Public email/location/WhatsApp are mostly consistent.
- Docs have been refreshed for handoff.

## What is left
- Booking reliability and backend hardening remain postponed/open.
- When booking work resumes, confirm the deployed Apps Script version and run a real end-to-end booking test.
- Verify `hello@tarteelhouse.com` inbox and deliverability.
- Add missing `assets/images/og-home.jpg` when the founder provides the social preview image.
- Final legal review of privacy/terms.
- Final desktop/mobile QA on live hosting.

## Important warnings
- Existing Google Sheets may still contain an old `timezone` column. Do not reorder existing sheets casually. The script appends missing columns to avoid disturbing old data.
- The public site is English-only for now. Do not add or imply other live site language versions unless they actually exist.
- Legal pages are not a substitute for professional legal review.
- The `success_redirect` setup must be checked on local, staging, and production before launch.
- Homepage OG image is currently referenced but missing; founder will provide it later.

## Shared Header and Footer workflow
The canonical Header is `partials/header.html`, and the standard Footer is `partials/footer.html`. `partials/footer-no-prebooking-contact.html` preserves the intentional Footer variant used by Blog articles and the post-booking Success page.

This is build-time synchronization, not a runtime include. Complete generated HTML must remain committed so browsers receive the full Header and Footer without depending on Python or JavaScript.

After editing a shared partial:
1. Run `python scripts/sync_shared_layout.py --write`.
2. Commit the generated public HTML together with the partial change.
3. Run `python scripts/sync_shared_layout.py --check` and the test suites before handoff.

## How to continue safely
1. Read this file.
2. Read `docs/current-status.md`.
3. Read `docs/next-tasks.md`.
4. Before editing, inspect the exact files involved.
5. Keep changes narrowly scoped to the task.
6. Run syntax checks for JS and Apps Script after editing:
   - `node --check assets/js/main.js`
   - `Get-Content -Raw apps-script/Code.gs | node --check --input-type=commonjs -`
7. If you change booking fields, update:
   - `/book-trial`
   - `apps-script/Code.gs`
   - `apps-script/README.md`
   - relevant legal/docs files
8. After meaningful work, update `docs/current-status.md`, `docs/decisions.md`, `docs/next-tasks.md`, and `docs/session-handoff.md`.
