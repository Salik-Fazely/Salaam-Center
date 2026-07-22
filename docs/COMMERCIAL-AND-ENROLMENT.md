# Salaam Center Commercial and Enrolment

## Status and authority

This is the internal operational source of truth for the Salaam Center production commercial and enrolment foundation. It records approved public facts, internal implementation definitions, completed launch decisions and capabilities reserved for later phases. It supports the public Terms and Privacy Policy but does not itself authorize collection of payment.

`SALAM-CENTER-APPROVED-FACTS.md` remains the concise factual authority. If later legal, accounting or operational approval changes this model, both documents and the public regression fixtures must be updated together.

## Approved initial contact and hosting architecture

- WhatsApp is the only initial public contact channel. The exact approved digits-only WhatsApp Business number is `34614401172`, displayed as `+34 614 401 172`, with `https://wa.me/34614401172` as the generic public destination.
- Domain email is not required. `hello@salaam.center`, public email links and telephone-call links are not part of the initial architecture.
- Formspree is superseded and inactive. There is no form provider, form endpoint, backend, database or WhatsApp Business Platform API.
- The website validates the eight approved fields and prepares the message locally in the adult visitor's browser. It does not submit or store the information on a Salaam Center server and does not send automatically. The visitor reviews the prepared message and must press Send inside WhatsApp.
- WhatsApp is a separate third-party service. The adult visitor should review the prepared message and WhatsApp's own privacy information before deliberately sending, and must not include sensitive information.
- A WhatsApp message is an enquiry, not a confirmed booking. It creates no payment obligation. A trial exists only after Salaam Center confirms a suitable teacher and schedule.
- A parent or guardian must make the enquiry and remain the primary contact for a minor; a child is never invited to contact a teacher privately.
- Initial launch has no analytics, no advertising pixels and no payments or public checkout.
- The approved operator is **Salaam Center**, the correspondence address is **Sabadell, Barcelona**, and the final Privacy Policy and Terms are effective **22 July 2026**.
- The manual WhatsApp test is complete, including the approved profile, mobile and WhatsApp Web/desktop handoff, message receiving and replies. The repository launch state records `whatsapp_live_link_tested` as `true`.
- Afghan Dari is the production default at root routes (`fa-AF`, RTL); the approved English site lives under `/en/` (`en`, LTR). There is no automatic language redirect. Equivalent-route switches, page-language WhatsApp messages, self-referencing canonicals, reciprocal hreflang, Dari `x-default` and the self-hosted Vazirmatn font are part of the approved architecture.
- Cloudflare Pages is the production hosting source of truth. Project `salaam-center` deploys automatically from GitHub `main` to `salaam.center` and `www.salaam.center`.
- Repository-root output is constrained by a fail-closed static `_redirects` public-route allowlist. Exact reviewed URLs proxy to distinct committed `site-runtime/` backing artifacts, whose bytes must match their reviewed sources. The `/en/*` and global catchalls proxy unknown paths to guaranteed-missing sentinels, causing Cloudflare Pages to render the nearest English or Dari styled template with HTTP 404 without serving the requested file. Preflight rejects route drift, mirror drift and unclassified files. This uses no Pages Function, `_worker.js`, form backend or Cloudflare dashboard change.
- The reconciled remote `Create CNAME` commit added only `salaam.center`; the unnecessary repository CNAME was removed through a forward change. GitHub Pages must not be configured, DNS must not be changed through this repository, and no Cloudflare or DNS configuration change belongs to this migration.
- The website is approved for production indexing: 28 intended localized canonical pages are indexable, while both Success pages and both 404 templates retain `noindex, nofollow`. Production `robots.txt` points to the canonical bilingual sitemap. The sitemap is available but has not been submitted manually, and Search Console is not enabled.

## Approved offer scope

The approved priced offer covers only:

- private one-to-one Quran lessons;
- private one-to-one Dari/Persian lessons.

Each price is in EUR, for one learner, for one selected program and for 40-minute paid classes. A plan is prepaid, non-transferable between learners, not exchangeable for cash and not automatically renewed. A learner taking both Quran and Dari/Persian needs a separate plan for each program unless a combined plan is approved later.

The offer does not create a combined-program, sibling, family, group, adult-group or Pashto plan. It does not cover Afghan Culture & Islamic Ethics group classes.

## Approved plan structure

### Flexible 4-week plan

| Frequency | Scheduled paid classes | Duration | Total |
|---|---:|---:|---:|
| 1 class per week | 4 paid classes | 40 minutes each | €49 total |
| 2 classes per week | 8 paid classes | 40 minutes each | €69 total |
| 4 classes per week | 16 paid classes | 40 minutes each | €99 total |

The scheduled teaching period is four weeks. The plan is manually purchased and does not renew automatically.

### 12-week plan

| Frequency | Scheduled paid classes | Duration | Total | Public euro comparison |
|---|---:|---:|---:|---|
| 1 class per week | 12 paid classes | 40 minutes each | €119 total | Saves €28 compared with three consecutive 4-week plans at the same frequency |
| 2 classes per week | 24 paid classes | 40 minutes each | €129 total | Saves €78 compared with three consecutive 4-week plans at the same frequency |
| 4 classes per week | 48 paid classes | 40 minutes each | €229 total | Saves €68 compared with three consecutive 4-week plans at the same frequency |

The scheduled teaching period is twelve weeks. “Most Popular” may identify the two-classes-per-week option and “Best Value” may identify the section, without urgency or scarcity language.

Public copy uses euro savings, not percentage badges. The exact percentages are retained only in the internal unit-economics record below.

## Free trial

- One free 40-minute trial is available per learner.
- No payment is required and there is no obligation to buy.
- The discussion considers the learner's current direction, goals and suitable program.
- Availability depends on a suitable teacher and schedule; no teacher or time is guaranteed.
- A parent or guardian arranges the trial and remains the primary contact for a child or teenager.
- The parent or guardian should be available at the beginning and end when requested.
- An adult woman learner may be the primary contact.
- A child is never invited to submit personal contact information or contact a teacher privately.
- The website prepares a WhatsApp enquiry locally; the adult visitor must review it and press Send. The website cannot confirm that Send was pressed, and repeated free trials are not offered in public wording.

## Enrolment and payment sequence

1. Explore the programs.
2. Prepare a WhatsApp trial enquiry and deliberately press Send inside WhatsApp.
3. Confirm a suitable teacher and schedule; the enquiry itself is not a booking.
4. Attend the free 40-minute trial and discuss learning direction.
5. Receive an initial program and format recommendation.
6. Confirm the plan, then review the complete terms and payment information.
7. Pay the selected plan in full before the first paid class.
8. Begin paid lessons.

There is no automatic online enrolment, public checkout, saved-card subscription, instalment plan, payment button or named provider. Payment instructions are provided only after the trial, teacher availability and schedule are confirmed. EUR is the only approved displayed currency; no conversion or exchange-rate claim is approved. Any applicable tax treatment and service-specific price information must be settled and disclosed before payment is accepted.

## Plan validity

### Flexible 4-week plan

- Scheduled teaching period: four weeks.
- Final validity: six weeks from the first paid class.
- The extra two weeks exist only for eligible rescheduled classes.
- Unused classes expire after final validity.

### 12-week plan

- Scheduled teaching period: twelve weeks.
- Final validity: sixteen weeks from the first paid class.
- The extra four weeks exist only for eligible rescheduled or make-up classes.
- Unused classes expire after final validity.

Stopping attendance does not extend a plan. Exceptional circumstances may be reviewed individually, but there is no advertised general pause entitlement.

## Cancellation, rescheduling and absence rules

### Learner cancellation with at least 24 hours' notice

For either plan length, the class is not treated as used and may be rescheduled once. The new time depends on teacher availability and must occur before plan expiry.

### Learner cancellation with less than 24 hours' notice

- Flexible 4-week plan: the class is treated as used and has no automatic make-up.
- 12-week plan: the learner may use one of four late-cancellation make-up credits included across the entire plan. After all four are used, a late cancellation is treated as used. Any make-up depends on teacher availability and must occur before expiry.

The four credits are not four additional ordinary classes.

### No-show without communication

If neither the learner nor responsible adult communicates before the scheduled class ends, the class is treated as used. A 12-week late-cancellation credit is not automatically applied.

### Salaam Center or teacher cancellation

The class is rescheduled, is not treated as used and consumes no learner make-up credit. A replacement occurs within a mutually agreed reasonable period.

### Late arrival

The class normally ends at its original scheduled time. The teacher need not extend it, and late arrival creates no make-up entitlement.

### Technical problems

- Teacher or Salaam Center technical failure: reschedule without consuming the learner's class or credit.
- Learner-side technical failure: review the circumstances rather than promise automatic replacement.
- Repeated learner-side connection problems: discuss a practical solution with the parent or adult learner.

## Benefits included with both plan lengths

- One free 40-minute trial before a paid plan; it is not one of the paid classes.
- Private one-to-one lessons.
- A private family learning group: a private communication space involving the parent or guardian, the teacher and Salaam Center for lesson links, scheduling and essential learning updates. An adult woman learner may be the primary participant. This does not permit teacher-child private messaging.
- Interactive quizzes and Kahoot-style activities may be used where suitable for the learner, age and program; they are not promised in every class or identically for every learner.
- Parent or adult-learner communication.
- Teacher-cancellation protection.

No lesson-delivery or private-family communication platform is approved or named by this benefit. The public WhatsApp enquiry channel does not decide the later lesson-delivery platform.

## Additional 12-week benefits

### Twelve Culture & Character mini-lessons

Access to 12 short Culture & Character mini-lessons supporting practical values, identity and everyday learning. These are supplementary digital lessons or guided resources, not 12 additional private 40-minute live classes and not a replacement for the Afghan Culture & Islamic Ethics group program. They may use age-appropriate video, quiz, discussion or activity material during the plan.

The inherited “€50 value”, “life coaching”, therapy and counselling formulations are prohibited for public use.

### Four late-cancellation make-up credits

These operate only under the late-cancellation rules above and are not additional ordinary classes.

### Extended quiz and revision access

This means extended access to additional quizzes and revision activities. The inherited label “VIP quiz access” is unsupported and prohibited for public use.

### Digital completion certificate

Eligibility applies only after the 12-week plan. At least 80% of scheduled paid classes must be completed and any outstanding payment obligation must be resolved. The certificate acknowledges participation and completion. It is not academic accreditation, a qualification or a government-recognised certificate.

### Progress summary every four weeks

For a minor, the summary is shared with the parent or guardian. An adult learner receives it directly. It may cover attendance, areas practised, teacher observations and suggested next steps. It is not a formal grade, examination, diagnosis or guaranteed outcome.

### Supplementary educational videos

Additional age-appropriate educational videos and learning resources may be provided. No fixed quantity is approved, and these are not private lessons.

## Afghan Culture & Islamic Ethics group pricing

Approved public wording: “Pricing for Afghan Culture & Islamic Ethics group classes will be published when cohort schedules and group arrangements are confirmed.”

Private-plan pricing does not cover the group program. The group program is not described as free, and no waitlist or information-collection control is active. Group enrolment follows a published cohort schedule when one becomes available.

## Refund and legal status

Consumer cancellation, refund and withdrawal rights apply where required by applicable law. Before accepting payment, Salaam Center must provide service-specific information appropriate to the learner's location, payment method and proposed service start, including any effect of asking for lessons to begin during a statutory withdrawal period.

The final public Terms and Privacy Policy are approved with an effective date of **22 July 2026**. The operator is **Salaam Center**, the correspondence address is **Sabadell, Barcelona**, and WhatsApp at **+34 614 401 172** is the only initial public contact route. The applicable version of the Terms and any service-specific payment information must be presented before payment is accepted.

## Internal teacher-compensation operations

This section is internal business information and is not approved for public use. Teacher compensation is €1.50 for each eligible 40-minute lesson.

### Eligible events

- Completed paid private lessons are eligible.
- Completed free trial lessons are eligible.
- A learner late cancellation or no-show that is treated as used is eligible when the teacher was present and available to teach.

The teacher's presence and availability must be recorded operationally before a learner absence is treated as an eligible compensation event.

### Ineligible events and replacements

- A teacher-cancelled class is not compensated at cancellation.
- Compensation attaches to the replacement class when that replacement is delivered.
- The original and replacement are not both paid.
- A class that was never scheduled is not eligible.
- Teacher unavailability is not eligible.
- A teacher-caused technical problem that requires a repeat is not eligible for an additional payment.

The €1.50 teacher payment, teacher cost per lesson, contribution calculations, internal revenue per lesson, profitability calculations and this compensation policy must not appear in public HTML, metadata, structured data, navigation or publicly referenced JavaScript.

## Internal-only unit economics

This section is internal business information and is not approved for public use. “Teacher-cost contribution” means plan revenue less direct teacher compensation for the plan's scheduled paid classes. Teacher-cost contribution is not final profit or net profit.

### Effective revenue per paid class

#### Flexible 4-week plans

- €49 ÷ 4 = €12.25 per paid class
- €69 ÷ 8 = €8.63 per paid class, rounded
- €99 ÷ 16 = €6.19 per paid class, rounded

#### 12-week plans

- €119 ÷ 12 = €9.92 per paid class, rounded
- €129 ÷ 24 = €5.38 per paid class, rounded
- €229 ÷ 48 = €4.77 per paid class, rounded

Internal percentage comparisons against three consecutive 4-week plans are approximately 19.0%, 37.7% and 22.9%. These are documentation-only calculations, not approved public discount badges.

### Direct teacher-cost contribution by plan

| Plan | Frequency | Revenue | Paid classes | Teacher cost | Teacher-cost contribution | Teacher-cost contribution margin |
|---|---|---:|---:|---:|---:|---:|
| Flexible 4-week | 1 class per week | €49 | 4 | €6 | €43 | 87.76% |
| Flexible 4-week | 2 classes per week | €69 | 8 | €12 | €57 | 82.61% |
| Flexible 4-week | 4 classes per week | €99 | 16 | €24 | €75 | 75.76% |
| 12-week | 1 class per week | €119 | 12 | €18 | €101 | 84.87% |
| 12-week | 2 classes per week | €129 | 24 | €36 | €93 | 72.09% |
| 12-week | 4 classes per week | €229 | 48 | €72 | €157 | 68.56% |

These calculations exclude:

- Payment-provider fees
- Taxes
- Accounting costs
- Administrative work
- Marketing costs
- Refunds or chargebacks
- Content-production costs
- Software or service costs
- The separate €1.50 acquisition cost of the free trial

### Free-trial acquisition cost

Each completed free 40-minute trial costs Salaam Center €1.50 in direct teacher compensation. This is a separate acquisition cost and is not included in the paid-class calculations. Allocating one trial to a learner's first paid plan reduces that plan's teacher-cost contribution by €1.50. The trial remains free to the learner.

### Internal commercial conclusion

“At the approved teacher compensation of €1.50 per eligible 40-minute lesson, all six approved private plans have positive and currently acceptable direct teacher-cost contribution. The lowest direct contribution margin is 68.56% before payment fees, taxes, administration, marketing and other operating costs.”

This conclusion addresses direct teacher cost only. It is not a claim of final profit, net profit or authority to activate online payment collection.

## Internal operational status

- **Teacher-compensation review** — resolved for current production pricing.
- **Gross-margin review** — direct teacher-cost contribution is recorded; the Final minimum net-margin policy remains a future internal business decision.
- **Payment-provider selection** — no provider is approved or active; selecting one would require a separate review before any integration.
- **Payment-provider fees** — a future payment-workflow input, with no fees or provider claims included in the current website.
- **Tax and accounting treatment** — service-specific tax and price disclosures must be settled before payment is accepted.
- **Administrative cost** — a future internal operating-cost input.
- **Marketing and acquisition cost** — a future internal operating-cost input.
- **Refund and chargeback exposure** — a future internal payment-workflow input.
- **Consumer-law review** — final Terms preserve rights under applicable law; service-specific consumer information must be provided before payment.
- **Future teacher-rate changes** — require a new economics review before compensation or pricing changes.
- **Legal-entity information — approved**: operator **Salaam Center**, correspondence address **Sabadell, Barcelona**.
- **Final Terms and Conditions — approved**, effective **22 July 2026**.
- **Final Privacy Policy — approved**, effective **22 July 2026**.
- **Contact mailbox** — superseded for initial launch; domain email is not required because WhatsApp is the only public contact route.
- **Live form and backend** — Formspree is superseded; the approved browser-local WhatsApp handoff has no backend, endpoint, storage or automatic message sending.
- **Analytics** — production is approved with no analytics and no advertising pixels.
- **Production SEO — indexing enabled** for the 28 intended localized canonical pages; both Success pages and both 404 templates retain `noindex, nofollow`; the sitemap is available but has not been submitted manually; Search Console is not enabled.
- **Deployment approval — approved** for Cloudflare Pages deployment from GitHub `main`; the apex and `www` custom domains and HTTPS are active. GitHub Pages and a repository CNAME remain prohibited, and DNS was unchanged.
- **Manual WhatsApp verification — complete** for the approved Business profile, mobile and WhatsApp Web/desktop links, message receiving and replies.
- **Deployment-surface containment** — `_redirects` must remain the exact reviewed public-route allowlist, the `site-runtime/` backing artifacts must remain byte-identical to their sources, and the missing catchall sentinel must remain absent. Preflight and trust scanning must fail on route drift, mirror drift, unclassified files or any Pages Functions surface.

## Change control

Any change to price, scope, class count, validity, trial, absence rules, benefits or eligibility requires explicit approval plus coordinated updates to public copy, authority documentation, scanner associations and regression tests. Production approval does not authorize unreviewed changes or activate analytics, payments, Search Console, a backend, public email, GitHub Pages or a repository CNAME.

## Initial launch privacy and storage position

- Initial launch uses no analytics and no advertising pixels, so no analytics-consent banner is required.
- Trial-form values are not written to `localStorage` or `sessionStorage`, and there is no form-success marker. Values remain in the page only while the adult visitor prepares the handoff and are included in WhatsApp's click-to-chat URL only after deliberate activation.
- Video playback remains user-activated and uses the privacy-enhanced YouTube domain.
- Any future analytics proposal requires a separate future approval and privacy review.
