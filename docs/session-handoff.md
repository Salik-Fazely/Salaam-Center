# Session Handoff

## Latest completed work
- Homepage teacher preview was aligned with real teacher data from `/teachers`.
- Business location was standardized as Barcelona, Spain.
- Public email was standardized as `hello@tarteelhouse.com`.
- Booking form and repository source were aligned around:
  - WhatsApp is required.
  - Country is a dropdown shortlist.
  - City / Region replaced the old timezone field.
- Booking reliability, backend hardening, deployment confirmation, and real end-to-end verification remain postponed/open. Do not describe the booking flow as completed or production-verified.
- Success page now describes WhatsApp follow-up and has a WhatsApp CTA.
- Lesson platform copy now says Zoom or Google Meet.
- Homepage trust stats band was added and refined:
  - 4 Teachers
  - 1-to-1 Lessons
  - 4 Teaching languages
  - Staggered reveal and count-up animation respect reduced-motion preferences.
- The Blog index and five articles are present.
- Complete public pages use the shared consent module and persistent cookie settings.
- Four teacher lesson-sample videos are present, including Sadiah Hamid's current video.
- Unverified written testimonials were removed; genuine student/family videos remain.
- Documentation was refreshed for continuity, including `docs/START-HERE.md`.

## Current priorities
1. Keep booking reliability and backend hardening marked postponed/open until that work is explicitly resumed.
2. When booking work resumes, confirm the deployed Apps Script version and run a real end-to-end booking test.
3. Confirm `hello@tarteelhouse.com` is fully operational.
4. Add `assets/images/og-home.jpg` when the founder provides it.
5. Complete legal review and final pre-launch QA.

## Warnings
- Do not redesign the site casually. Preserve current fonts, spacing, colors, layout language, and visual hierarchy.
- Do not replace the Google Apps Script backend unless explicitly requested.
- Do not reintroduce the old timezone field.
- Do not mark booking success unless the backend completed the booking flow.
- Existing Google Sheets may still have a legacy `timezone` column; the script will append `city_region` if missing rather than reorder old sheets.
- `apps-script/Code.gs` changes are not live until manually redeployed in Google Apps Script.
- Frontend commits are not live until they are published through GitHub Pages; do not infer deployment from local Git history.
- `assets/images/og-home.jpg` is referenced but missing; founder will provide it later.
- Legal pages still need founder/legal confirmation.

## How to resume
Start with `docs/START-HERE.md`, then read:
1. `docs/current-status.md`
2. `docs/next-tasks.md`
3. `docs/decisions.md`
4. `docs/brand-rules.md`

After any significant work, update these docs again.
