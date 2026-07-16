# Current Status

## Overall state
The static website, Blog, consent banner, booking form, and Apps Script source are present in the repository. The repository is configured for GitHub Pages and the `www.tarteelhouse.com` custom domain. The latest local commits are not assumed to be published, and booking reliability, backend hardening, and live end-to-end verification remain postponed/open.

## Completed pages
- `/`: homepage with hero, trust stats band, how-it-works preview, teacher preview, why-us section, pricing preview, student/family videos, final CTA, and footer.
- `/book-trial`: booking form with required WhatsApp, country dropdown, City / Region, chip-based preferences, consent, and success redirect field.
- `/success`: booking confirmation page with WhatsApp-first follow-up copy and WhatsApp CTA.
- `/pricing`: pricing packages and FAQ.
- `/how-it-works`: full process page.
- `/teachers`: teacher page with four real teacher profiles and language filter.
- `/about`: about page.
- `/blog`: Blog index plus five article pages.
- `/privacy-policy` and `/terms`: legal pages with current business identity, but still requiring founder/legal review.
- Complete public pages load the shared consent module and provide persistent cookie settings.

## Core files
- `assets/css/styles.css`: global brand tokens, typography, layout, components, responsive styles, and motion rules.
- `assets/js/main.js`: mobile nav, active nav link, scroll reveals, page transitions, stats count-up, and shared progressive enhancement.
- `assets/js/consent.js`: consent banner, analytics preference storage, and persistent cookie settings.
- `/book-trial`: includes small inline JS for booking chips and success redirect.
- `apps-script/Code.gs`: canonical Google Apps Script booking backend.
- `apps-script/README.md`: backend deployment and sheet documentation.

## Repository booking flow
The current frontend and Apps Script source describe this flow, but the deployed version and full live behaviour have not been verified in this phase.

1. The parent-facing form is available at `/book-trial`.
2. The form is configured to post to a Google Apps Script Web App.
3. The repository backend source is designed to validate required fields and allowed values.
4. The repository source is designed to append the booking to Google Sheets and send a plain-text notification to `hello@tarteelhouse.com`.
5. The intended completion path redirects the parent to `/success`.
6. The repository source is designed to return an error page when validation or backend completion fails.

## Current required booking fields
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

## Confirmed business details
- Public email: `hello@tarteelhouse.com`.
- Business location: Barcelona, Spain.
- WhatsApp / phone: `+34 614 494 311`.

## Verification status
- Automated Python and JavaScript tests cover the current static site.
- Local verification does not prove that the latest commits or Apps Script source are deployed.

## What remains
- Booking reliability and backend hardening remain postponed/open.
- When booking work resumes, confirm the deployed Apps Script version and manually test one real booking end to end: sheet row, notification email, and success redirect.
- Add the missing Open Graph image `assets/images/og-home.jpg` when provided.
- Final legal review of privacy policy and terms.
- Verify `hello@tarteelhouse.com` inbox and deliverability.
- Publish approved local changes through GitHub Pages when deployment is authorized, then test the live domain and SSL.
