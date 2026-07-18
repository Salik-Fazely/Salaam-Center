# Salaam Center Launch Activation Checklist

Use the dependency order below; the lettered sections are reference groups, not one linear pass. Do not place passwords, API keys, tokens, private DNS credentials or real child data in the repository.

1. Complete A, B, the preparation items in C, and D.
2. With separate deployment approval, complete **Stage 1** in E, then F. Keep the public form disabled and the site blocked from indexing. Production preflight must still report `EXPECTED BLOCKED PRODUCTION STATE` during this controlled infrastructure transition.
3. From the working production origin, complete the verification items in C with non-sensitive dummy data.
4. Complete **Stage 2** in E, then G. Production preflight must exit 0 before the final production-switch commit and normal push.

## A. Email

- [ ] Create `hello@salaam.center` with the chosen email provider.
- [ ] Verify inbound mail and outbound mail.
- [ ] Verify SPF, DKIM where supported, and DMARC where supported.
- [ ] Send a test from an unrelated address and reply successfully.
- [ ] Set `contact_email_verified` to `true` only after every check above succeeds.

## B. Legal information

- [ ] Obtain and publish the legal controller/operator name and a business or correspondence address suitable for legal disclosure; insert the approved values into the final notices and `legal_controller_name` / `legal_controller_address` configuration fields.
- [ ] Complete the privacy legal bases, retention rules, Formspree/provider and international-transfer disclosures where applicable, data-rights process, complaint route and operational contact process.
- [ ] Complete the consumer cancellation/withdrawal and refund review, taxes, applicable law and dispute process.
- [ ] Insert a final effective date.
- [ ] Set `privacy_policy_final_approved` and `terms_final_approved` to `true` only after actual legal review.

## C. Formspree

Preparation before infrastructure activation:

- [ ] Create a dedicated Salaam Center project and form.
- [ ] Use an HTTPS form-ID endpoint (`https://formspree.io/f/<real-form-id>`), never an email-address URL.
- [ ] Connect and verify the notification destination.
- [ ] Set Restrict to Domain to `salaam.center`.
- [ ] Confirm spam protection and retain the `_gotcha` honeypot.

Verification after Stage 1 in E and all of F are complete:

- [ ] From `https://salaam.center`, use a controlled developer test with non-sensitive dummy data to confirm the domain restriction and notification delivery while the public form remains disabled.
- [ ] Insert the endpoint into `config/launch-readiness.json` and the trial page activation data only after verification.
- [ ] Test with non-sensitive dummy data: successful submission, provider validation error, network failure and duplicate-click prevention.
- [ ] Confirm the Success page appears only after a real confirmed response and direct access remains truthful.
- [ ] Do not use real child data and do not load-test the provider endpoint.
- [ ] Set `booking_endpoint_verified` and `formspree_domain_restriction_confirmed` to `true` only after all tests succeed.

## D. GitHub domain security

- [ ] Verify ownership of `salaam.center` in GitHub before custom-domain activation; do not change DNS first.
- [ ] Confirm this repository is the intended GitHub Pages repository.
- [ ] Confirm no other Pages site can claim the domain and no takeover risk remains.
- [ ] Set `domain_verified_with_github` to `true` only after the ownership check succeeds.

## E. Production-mode repository changes

### Stage 1 — separately approved infrastructure while the site stays prelaunch

- [ ] Keep `site_mode` as `prelaunch`, retain `noindex, nofollow`, retain block-all `robots.txt`, and keep the trial form disabled.
- [ ] Add `CNAME` containing only `salaam.center`.
- [ ] Configure the approved GitHub Pages publishing source or an approved deployment workflow.
- [ ] Review, commit and normally push this infrastructure-only transition under separate authorization.
- [ ] Confirm production preflight still exits nonzero with `EXPECTED BLOCKED PRODUCTION STATE`; do not weaken it or treat this stage as production approval.
- [ ] Complete F, then return to the verification items in C.

### Stage 2 — final repository switch after A, B, C, D and F are verified

- [ ] Change `site_mode` to `production` and update only genuinely verified flags.
- [ ] Remove `noindex, nofollow` from all production pages.
- [ ] Change `robots.txt` from block-all to reviewed production crawl rules and add `Sitemap: https://salaam.center/sitemap.xml`.
- [ ] Reconfirm every canonical and Open Graph URL uses the exact approved route on `https://salaam.center`.
- [ ] Replace every prelaunch, pending, inactive and placeholder statement with approved production copy. Review the Contact page and footer, trial status and privacy acknowledgement, Privacy and Terms pages, direct Success state, 404 page and policy-link labels explicitly.
- [ ] Activate the verified endpoint in the trial page and remove native disabled controls only after privacy and provider approval; retain the truthful direct-Success state and confirmed-response marker protection.
- [ ] Update mode-specific scanner and regression expectations so they permit only the known production trial form with the exact verified Formspree form-ID endpoint and only the exact approved controller/operator name and disclosure address from configuration, while continuing to reject every other active form, placeholder endpoint, unsafe field, legal identity and postal address.
- [ ] Keep `analytics_mode` set to `none`; add no analytics, advertising pixel, optional-cookie control or conversion event.
- [ ] Run `python scripts/launch_preflight.py --mode production`; it must exit 0.
- [ ] Review, commit and push the production activation as a separately approved change.

## F. DNS and Pages

- [ ] Configure the custom domain in GitHub Pages before changing DNS.
- [ ] At activation time, check current official GitHub documentation and apply its current recommended DNS records; do not rely on copied historical IP values.
- [ ] Configure apex and `www` behavior deliberately.
- [ ] Wait for DNS propagation, then enable HTTPS only after GitHub makes it available.
- [ ] Verify HTTP/HTTPS and apex/`www` behavior, redirects and absence of mixed content.
- [ ] Reconfirm no domain takeover risk.
- [ ] Record `github_pages_enabled`, `dns_configured` and `https_confirmed` as `true` in the Stage 2 configuration only after each corresponding external check has actually succeeded.

## G. Final production tests

- [ ] Test form submission, email delivery, validation and network error states, duplicate clicks and protected success routing.
- [ ] Test mobile navigation, keyboard access, visible focus, the disabled/active form transition, and representative teacher and student videos.
- [ ] Test all internal links, the custom 404, sitemap, robots, canonicals and structured data.
- [ ] Test HTTPS, apex/`www` redirects, mixed content and removal of every `noindex` directive.
- [ ] Run the production preflight, full Python and JavaScript suites, public-source/trust scan, integration scan, internal-cost leakage scan and secrets scan.
- [ ] After the normal push, repeat the live form/email, HTTPS, redirect, mixed-content, robots, sitemap, canonical, 404 and noindex-removal smoke tests on the production origin.
