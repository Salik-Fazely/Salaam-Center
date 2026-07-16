# Key Decisions

## Technical decisions
- The site is a static custom-coded HTML/CSS/JS site.
- No frontend framework is currently used.
- The launch booking backend is Google Apps Script, not PHP/MySQL.
- Booking submissions are stored in Google Sheets.
- Booking notifications are emailed to `hello@tarteelhouse.com`.
- `apps-script/Code.gs` is the canonical Apps Script source. Paste it into the bound Apps Script project and redeploy to update the live backend.
- GitHub Pages is the current static-hosting configuration, with `www.tarteelhouse.com` recorded in `CNAME`.
- Local commits are not assumed to be published to the live site.
- PHP/MySQL may be revisited later, but it is not the launch backend.

## Business identity decisions
- Public contact email: `hello@tarteelhouse.com`.
- Business location: Barcelona, Spain.
- Public WhatsApp / phone used in legal and success CTA: `+34 614 494 311`.
- WhatsApp is the preferred pre-booking question route.

## Booking flow decisions
- Free trial before any payment.
- WhatsApp number is required in the booking form.
- Country is a required dropdown shortlist:
  Germany, France, Netherlands, Belgium, Sweden, Norway, Denmark, Switzerland, Austria, United Kingdom, Ireland, Spain, Italy, Canada, United States, Other.
- City / Region is a required free-text field.
- City / Region replaced the older technical timezone field.
- Preferred days, preferred time, current Qur'an level, and session language are required chip fields.
- No separate teacher-preference field exists; parents can mention a preferred teacher in notes.
- Families are normally contacted within two days to arrange the next steps; this is not a guaranteed service-level deadline.
- Success redirect should land on the site's `/success`; verify this near final publish/staging.
- Launch lesson platform copy should say Zoom or Google Meet.

## Product and operations decisions
- Teacher matching is handled personally, not algorithmically.
- Founder-led, intentionally small team.
- Lessons normally continue with the same dedicated teacher, subject to availability and unavoidable changes.
- One package = one child.
- Tarteel House currently serves girls and boys aged 5 to 16 and does not advertise adult classes.
- The free trial and every paid lesson are 40 minutes.
- Every two months, we invite parents to a 15-minute progress review. If a parent is unavailable or does not want a meeting, we send a visual progress report through WhatsApp instead.
- Certificates require at least 30 completed lessons, completion of an identifiable learning stage, and teacher confirmation of that stage.
- Teacher matching considers language, level, learning needs, and scheduling availability. Parents may express a preference but do not select or reserve a teacher.
- Families may request a teacher change; another suitable teacher is proposed subject to availability, without a promise of an immediate replacement or the same schedule.
- Public homepage stats are approved:
  4 Teachers, 1-to-1 Lessons, 4 Teaching languages.

## Pricing decisions
- Starter: EUR 120 / 6 lessons (EUR 20 per lesson).
- Steady: EUR 220 / 12 lessons (approximately EUR 18.33 per lesson), most popular.
- Committed: EUR 400 / 25 lessons (EUR 16 per lesson).
- Every package is valid for one year from the purchase date.
- With at least 24 hours' notice, a lesson is rescheduled without using a make-up allowance.
- Teacher or Tarteel House cancellations or changes are always rescheduled and never use the family's allowance. The new time depends on teacher and family availability.
- The 6-lesson package has no make-up allowance for late-notice or unnotified absences; the missed lesson is counted as used.
- The 12-lesson and 25-lesson packages include up to four make-up lessons, including for absences without prior notice. After all four are used, another late-notice or unnotified absence is counted as used.
- Make-up allowances cover missed scheduled lessons; they are not additional free lessons.
- "Family" was renamed to "Steady" to avoid sibling-sharing confusion.

## Payment decisions
- The on-site payment system is not yet configured.
- The family takes the free trial first. If they continue, Tarteel House confirms the suitable package and shares payment instructions or a secure payment link through WhatsApp.
- Paid lessons are scheduled after payment confirmation.
- Do not publicly name a payment provider or payment method until it is configured and tested.

## Brand and design decisions
- Preserve the current minimal premium editorial design.
- Primary actions use forest green.
- Bronze is used for accents and quiet emphasis.
- Alternating ivory/paper section backgrounds define the layout rhythm.
- Avoid unnecessary redesigns, new style systems, and broad refactors.
- Motion should stay subtle and must respect reduced-motion preferences.

## Legal decisions
- Legal pages exist but still need proper founder/legal review.
- Approved refund wording: "Payments are generally non-refundable once a package has started. Lessons already delivered, missed without the required notice, or cancelled late are not refundable. This policy does not affect any mandatory consumer rights that apply under EU law."
- Earlier plan mentioned iubenda; this remains an option, not a confirmed final legal provider.
- Do not invent legal facts. Use confirmed business details only.

## Open decisions
- The missing social preview image `assets/images/og-home.jpg` will be provided later.
- Booking reliability, backend hardening, deployment confirmation, and a real end-to-end booking test remain postponed/open.
