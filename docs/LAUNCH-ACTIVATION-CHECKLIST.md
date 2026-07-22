# Salaam Center Launch Activation Checklist

This checklist records the approved Cloudflare Pages and WhatsApp handoff architecture. Do not place passwords, API keys, tokens, private DNS credentials or real child data in the repository.

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

- [ ] Confirm the WhatsApp Business profile shows the intended Salaam Center name, profile image and exact number.
- [ ] On Android or iPhone, open the generic contact link and the Free Trial `Continue in WhatsApp` handoff.
- [ ] On WhatsApp Web/desktop, repeat both link checks and confirm the correct conversation opens.
- [ ] Check the experience when WhatsApp is not installed; confirm the platform's normal click-to-chat guidance appears and the Salaam Center site makes no false success claim.
- [ ] Confirm the prepared message is readable, has the approved line breaks and labels, uses trimmed values, and shows `Not provided` when the optional goal is empty.
- [ ] Confirm the destination is exactly `34614401172`, with no tracking parameter, shortened URL, API wrapper or unexpected recipient.
- [ ] Review the prepared message before sending and confirm it contains no hidden metadata, learner name, sensitive data, medical details, identity numbers, financial details or passwords.
- [ ] Exercise the parent or guardian flow for a child age group and the Adult woman learner flow; confirm invalid role/age combinations are rejected accessibly.
- [ ] Confirm popup-blocked behavior uses the current-tab fallback and rapid duplicate activation does not open repeated conversations.
- [ ] Confirm validation identifies the field errors, moves focus to the error summary and restores the CTA after an opening failure.
- [ ] Confirm no automatic sending occurs: WhatsApp opens with an editable draft and the tester must deliberately press Send.
- [ ] When the separately authorised receive-and-reply test is performed, confirm Salaam Center receives the dummy message and can reply successfully on the approved business account.
- [ ] Confirm the generic non-JavaScript link contains no prepared form values.
- [ ] Open `/success/` directly and confirm it says the website cannot know whether Send was pressed and that no trial is booked until teacher and schedule are confirmed.
- [ ] Set `whatsapp_live_link_tested` to `true` only after all applicable mobile, WhatsApp Web/desktop, receiving and reply checks succeed.

## C. Privacy, terms and safeguarding

- [x] Privacy wording explains browser-local preparation, deliberate transfer to WhatsApp, WhatsApp's third-party role, review before sending and the prohibition on sensitive information.
- [x] Privacy wording states that the Salaam Center website does not submit or store form values and that no analytics or advertising pixels are active.
- [x] Terms state that a WhatsApp enquiry is not a booking, creates no payment obligation and becomes a trial only after teacher and schedule confirmation.
- [x] Contact, Free Trial and message copy keep the parent or guardian as the contact for a minor.
- [ ] Obtain the approved legal controller/operator identity and a suitable disclosure address.
- [ ] Complete legal bases, retention, third-party/transfer disclosures, rights, complaints, consumer withdrawal, refunds, taxes, applicable law, dispute process and effective date.
- [ ] Set `privacy_policy_final_approved` and `terms_final_approved` to `true` only after real legal review.

## D. Production indexing switch

The live Cloudflare deployment may remain deliberately noindex while the legal and operational checks are incomplete. In the final approved production-indexing change:

- [ ] Change `site_mode` to `production` only when every genuine blocker is resolved.
- [ ] Remove noindex and `nofollow` from every public HTML page.
- [ ] Change `robots.txt` from `Disallow: /` to the approved production crawl policy.
- [ ] Confirm `sitemap.xml` contains the approved canonical routes and continues to exclude `/success/` and `/404.html`.
- [ ] Remove remaining pre-launch, placeholder and pending wording only when approved facts replace it.
- [ ] Run `python scripts/launch_preflight.py --mode production`; it must exit 0 before treating the site as production-ready for indexing.
- [ ] Keep analytics, advertising pixels, payments, Search Console, GitHub Pages and repository CNAME absent unless each receives separate future approval.

## E. Release verification

- [ ] After any reviewed HTML, CSS, JavaScript, favicon, robots or sitemap source change, run `python -B scripts/sync_public_runtime.py --write` to refresh the committed backing artifacts.
- [ ] Run the focused WhatsApp, launch-readiness, trust-evidence, pricing, economics, accessibility, protected-media and shared-layout tests.
- [ ] Run full Python unittest discovery and every JavaScript test; run JavaScript syntax checks, `python -B scripts/sync_public_runtime.py --check` and `git diff --check`.
- [ ] Confirm public trust failures, broken internal links, public email, `mailto:`, Formspree, active network submission, personal-data storage, analytics, payments, internal teacher-cost leakage and secret findings are all zero.
- [ ] Confirm all 16 shared-layout source pages and all 21 public runtime backing artifacts remain synchronized, and all protected teacher identities, teacher videos, student videos and approved public prices remain unchanged.
- [ ] Confirm known internal-document, config, script, test, partial and unused-source-asset URLs return the styled HTTP 404 and never return the requested file contents on the apex, `www` and `pages.dev` domains. Include case-changed, encoded-slash, double-slash and query-string variants.
- [ ] Confirm prelaunch preflight exits 0. Until section C and D approvals and the final manual live-link test are complete, production preflight must report only those genuine blockers.

## F. Push and Cloudflare observation

- [ ] Fetch before pushing and confirm `origin/main` has not advanced, the local branch is ahead but not behind, and the remote is `Salik-Fazely/Salaam-Center`.
- [ ] Push normally to `main`; never force-push or rewrite the reconciled `Create CNAME` history.
- [ ] After the push, fetch and confirm local HEAD equals `origin/main`, ahead/behind is `0/0`, the working tree is clean, `CNAME` is absent and no GitHub Pages workflow exists.
- [ ] Observe the automatic Cloudflare Pages deployment without changing Cloudflare or DNS settings.
- [ ] Check the apex, `www`, Free Trial, Contact, Privacy and Terms URLs for the exact WhatsApp destination, no public email, no Formspree, no analytics, no false confirmation, intact styling and intact protected media.
- [ ] Check the deployment boundary on the apex, `www` and `pages.dev`: reviewed paths load, while internal documentation, config, partials, scripts, tests, unused assets and direct `site-runtime/` paths return the styled HTTP 404 without exposing their bytes.
