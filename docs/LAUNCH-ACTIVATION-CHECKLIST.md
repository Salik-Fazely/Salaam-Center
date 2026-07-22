# Salaam Center Launch Activation Checklist

This checklist records the approved Cloudflare Pages and WhatsApp handoff architecture. Do not place passwords, API keys, tokens, private DNS credentials or real child data in the repository.

Current approval state: the manual WhatsApp test is complete, the Privacy Policy is approved, the Terms are approved, and indexing is enabled for the 14 intended canonical pages. Success and 404 retain `noindex, nofollow`. The sitemap is available but has not been submitted manually, and Search Console is not enabled. Cloudflare Pages remains the hosting source of truth, automatic deployment from GitHub `main` remains active, and the apex and `www` domains and HTTPS are active. DNS was unchanged.

## A. Locked architecture

- [x] Cloudflare Pages is the production hosting source of truth: project `salaam-center`, empty build command, repository-root output and automatic deployment from GitHub `main`.
- [x] Root `_redirects` is the exact fail-closed static public-route allowlist. Reviewed URLs proxy only to byte-identical committed `site-runtime/` backing artifacts; every other path resolves through the missing sentinel to the styled HTTP 404. No Pages Function, `_worker.js` or form backend is introduced, and every future file must still be classified before push.
- [x] Production domains are `https://salaam.center` and `https://www.salaam.center`; HTTPS is active.
- [x] The remote `Create CNAME` commit `721337d6c53f289b6ca512a8d89439dfc1cacbc9` was inspected as a direct CNAME-only fast-forward whose file contained exactly `salaam.center`, then reconciled.
- [x] The unnecessary repository-root `CNAME` was removed through a normal forward change. Cloudflare holds the custom-domain configuration, so no replacement CNAME is required.
- [x] GitHub Pages must not be configured. DNS must not be changed through this repository. Do not change Cloudflare settings as part of an application release.
- [x] WhatsApp is the only initial public contact channel. The approved digits-only WhatsApp Business number is `34614401172`, displayed as `+34 614 401 172` and linked only through `https://wa.me/34614401172`.
- [x] Formspree is superseded and inactive. Domain email is not required; no public email address or `mailto:` link is part of initial launch.
- [x] The website prepares the message locally in the adult visitor's browser. It has no form backend or database, performs no website submission or personal-data storage, and does not automatically send a WhatsApp message.
- [x] The visitor must review the prepared message and press Send inside WhatsApp. A WhatsApp message is an enquiry, not a confirmed booking or payment obligation.
- [x] No WhatsApp Business Platform API, credential, token, analytics, advertising pixel, payment integration or public checkout is active.
- [x] A parent or guardian is the required contact for every minor. Children are not invited to contact teachers privately.

## B. Manual WhatsApp verification

Complete these checks with dummy adult data only. Automated tests and visual QA must not send a real WhatsApp message. A separately authorised human tester may send one non-sensitive dummy message when verifying receiving and replies.

- [x] Confirm the WhatsApp Business profile shows the intended Salaam Center name, profile image and exact number.
- [x] On Android or iPhone, open the generic contact link and the Free Trial `Continue in WhatsApp` handoff.
- [x] On WhatsApp Web/desktop, repeat both link checks and confirm the correct conversation opens.
- [x] Check the experience when WhatsApp is not installed; confirm the platform's normal click-to-chat guidance appears and the Salaam Center site makes no false success claim.
- [x] Confirm the prepared message is readable, has the approved line breaks and labels, uses trimmed values, and shows `Not provided` when the optional goal is empty.
- [x] Confirm the destination is exactly `34614401172`, with no tracking parameter, shortened URL, API wrapper or unexpected recipient.
- [x] Review the prepared message before sending and confirm it contains no hidden metadata, learner name, sensitive data, medical details, identity numbers, financial details or passwords.
- [x] Exercise the parent or guardian flow for a child age group and the Adult woman learner flow; confirm invalid role/age combinations are rejected accessibly.
- [x] Confirm popup-blocked behavior uses the current-tab fallback and rapid duplicate activation does not open repeated conversations.
- [x] Confirm validation identifies the field errors, moves focus to the error summary and restores the CTA after an opening failure.
- [x] Confirm no automatic sending occurs: WhatsApp opens with an editable draft and the tester must deliberately press Send.
- [x] The separately authorised receive-and-reply test confirms Salaam Center receives the dummy message and can reply successfully on the approved business account.
- [x] Confirm the generic non-JavaScript link contains no prepared form values.
- [x] Open `/success/` directly and confirm it says the website cannot know whether Send was pressed and that no trial is booked until teacher and schedule are confirmed.
- [x] `whatsapp_live_link_tested` is `true` after the applicable mobile, WhatsApp Web/desktop, receiving and reply checks succeeded.

## C. Privacy, terms and safeguarding

- [x] Privacy wording explains browser-local preparation, deliberate transfer to WhatsApp, WhatsApp's third-party role, review before sending and the prohibition on sensitive information.
- [x] Privacy wording states that the Salaam Center website does not submit or store form values and that no analytics or advertising pixels are active.
- [x] Terms state that a WhatsApp enquiry is not a booking, creates no payment obligation and becomes a trial only after teacher and schedule confirmation.
- [x] Contact, Free Trial and message copy keep the parent or guardian as the contact for a minor.
- [x] The approved operator is **Salaam Center** and the approved correspondence address is **Sabadell, Barcelona**.
- [x] The final Privacy Policy covers browser-local handling, retention, third-party services, privacy requests, complaints and an effective date of **22 July 2026** without unsupported guarantees.
- [x] The final Terms cover the approved commercial facts, safeguarding, applicable consumer cancellation, refund and withdrawal rights, service-specific information before payment and an effective date of **22 July 2026** without inventing a jurisdiction or tax position.
- [x] `privacy_policy_final_approved` and `terms_final_approved` are `true`.

## D. Production indexing switch

The production indexing switch is approved with the following final state:

- [x] `site_mode` is `production` after the legal, indexing and manual live-link approvals were completed.
- [x] The 14 intended canonical content pages have no `noindex` directive; Success and 404 retain the exact `noindex, nofollow` directive.
- [x] `robots.txt` allows production crawling and references `https://salaam.center/sitemap.xml`.
- [x] `sitemap.xml` contains the 14 approved canonical routes and excludes `/success/` and `/404.html`.
- [x] Public production copy contains no stale launch placeholder or incomplete-approval wording.
- [x] Production preflight is the release gate and must exit 0 before the site is treated as ready for indexing.
- [x] Analytics, advertising pixels, payments, Search Console, GitHub Pages and repository CNAME remain absent unless each receives separate future approval.

## E. Release verification

- [ ] After any reviewed HTML, CSS, JavaScript, favicon, robots or sitemap source change, run `python -B scripts/sync_public_runtime.py --write` to refresh the committed backing artifacts.
- [ ] Run the focused WhatsApp, launch-readiness, trust-evidence, pricing, economics, accessibility, protected-media and shared-layout tests.
- [ ] Run full Python unittest discovery and every JavaScript test; run JavaScript syntax checks, `python -B scripts/sync_public_runtime.py --check` and `git diff --check`.
- [ ] Confirm public trust failures, broken internal links, public email, `mailto:`, Formspree, active network submission, personal-data storage, analytics, payments, internal teacher-cost leakage and secret findings are all zero.
- [ ] Confirm all 16 shared-layout source pages and all 21 public runtime backing artifacts remain synchronized, and all protected teacher identities, teacher videos, student videos and approved public prices remain unchanged.
- [ ] Confirm known internal-document, config, script, test, partial and unused-source-asset URLs return the styled HTTP 404 and never return the requested file contents on the apex, `www` and `pages.dev` domains. Include case-changed, encoded-slash, double-slash and query-string variants.
- [ ] Confirm both the backward-compatible prelaunch preflight command and production preflight exit 0 for the approved production state.

## F. Push and Cloudflare observation

- [ ] Fetch before pushing and confirm `origin/main` has not advanced, the local branch is ahead but not behind, and the remote is `Salik-Fazely/Salaam-Center`.
- [ ] Push normally to `main`; never force-push or rewrite the reconciled `Create CNAME` history.
- [ ] After the push, fetch and confirm local HEAD equals `origin/main`, ahead/behind is `0/0`, the working tree is clean, `CNAME` is absent and no GitHub Pages workflow exists.
- [ ] Observe the automatic Cloudflare Pages deployment without changing Cloudflare or DNS settings.
- [ ] Check the apex, `www`, Free Trial, Contact, Privacy and Terms URLs for the exact WhatsApp destination, no public email, no Formspree, no analytics, no false confirmation, intact styling and intact protected media.
- [ ] Check the deployment boundary on the apex, `www` and `pages.dev`: reviewed paths load, while internal documentation, config, partials, scripts, tests, unused assets and direct `site-runtime/` paths return the styled HTTP 404 without exposing their bytes.
