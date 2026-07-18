# Scope-Aware Trust-Evidence Regression Design

## Status and authority

This design was approved and implemented on 2026-07-18. The maintained implementation is `scripts/trust_evidence_scanner.py` with regression coverage in `tests/trust_evidence_regression_test.py`. It enforces the trust-evidence rules in `SALAM-CENTER-APPROVED-FACTS.md`, `MIGRATION-SOURCE.md`, `docs/COMMERCIAL-AND-ENROLMENT.md`, and the user's final implementation guardrails. Repository integration does not authorize a push, deployment, or external-service activation.

## Objective

Maintain a dependency-free regression system that rejects unsupported trust claims only when they occur on a public surface. It retains approved teacher and student evidence and permits internal audit, provenance, unresolved, prohibited, and negative-test references in documentation-only scope.

## Scope classification

The scanner assigns repository inputs to explicit scopes:

- **Public HTML:** pages in an explicit public-route manifest, covering every current public endpoint. Shared header and footer content are covered because they are rendered into those pages. An unlisted, unlinked source file is not public merely because it has an `.html` extension.
- **Metadata:** title, standard metadata, Open Graph metadata, Twitter metadata, and similar head content in public HTML.
- **Structured data:** JSON-LD and other structured-data blocks in public HTML.
- **Executable JavaScript:** local JavaScript files referenced by public HTML, plus inline public scripts. Local references are resolved within the repository. Unreferenced JavaScript is inactive and outside this public-executable scope.
- **Documentation only:** `SALAM-CENTER-APPROVED-FACTS.md`, `MIGRATION-SOURCE.md`, `docs/COMMERCIAL-AND-ENROLMENT.md`, negative regression fixtures, and denylist values used only to test scanner behavior.

Documentation-only occurrences are classified by their repository path and reported as such; they do not fail the public-surface audit. Authors must still clearly label those records as internal, inherited, unsupported, unresolved, prohibited, or not approved for public use. Those labels are editorial safeguards, not the scanner's classification mechanism.

## Protected approved evidence

Regression protection preserves the required approved values and behavior.

### Teachers

- Farkhonda Jami
- Foruhar Rahmani
- Fareshta Suroush
- Sadiah Hamid

The teachers' approved profiles, specifically names, languages, individual experience statements, video IDs, thumbnails, accessible labels, titles, and lesson-sample cards, remain allowed and protected.

### Video IDs

Teacher videos:

- `iUMB3pKzS_A`
- `iurgyXOzqFU`
- `OtaIpKZpbMM`
- `fOzc2cM5Twk`

Student videos:

- `to3h-qq7_FM`
- `6WxiPdZNcCY`

The existing student captions and consent-sensitive wording remain unchanged. The implementation must also preserve `youtube-nocookie.com`, video-ID validation, duplicate-player prevention, accessible native controls, descriptive player naming, focus transfer, focus visibility, focus restoration where currently present, and keyboard behavior. This regression task does not invent a new dialog or player-control system.

Protected evidence uses exact values or tightly scoped fixtures. An approved teacher experience or student caption is exempted only when it is associated with its matching identity or video ID inside the expected card on an approved route. There is no broad keyword exception for teacher, student, experience, video, pricing or certificate terms. Exact commercial evidence is protected only in the associated pricing card, homepage preview or eligible 12-week certificate-benefit card on its approved route.

The exact commercial associations are regression boundaries, not general price or certificate allowlists.

## Prohibited public claims

Category-level rules reject unsupported public claims, including:

- written testimonials or endorsements outside the exact approved video context;
- star ratings, review scores, review counts, and aggregate-rating or review structured data;
- unsupported learner, student, family, or enrollment counts;
- success rates and success percentages;
- positive certificate promises outside the exact eligible 12-week evidence context;
- unapproved pricing, currencies, percentage badges, automatic renewal, checkout, completed-payment, paid-plan-free, tax-inclusion or named-provider claims;
- combined teacher-experience totals;
- unsupported aggregate statistics;
- dynamically injected counters or trust claims;
- active inherited analytics, forms, or contact integrations.

Approved individual teacher experience remains valid. A combined statement such as `12+ years of teaching experience` fails even though each teacher's exact individual experience statement passes.

## Certificate semantics

The scanner distinguishes positive promises from negative, unresolved, or prohibitive statements. Negative handling is tied to the matching predicate so an unrelated negative phrase in the same sentence cannot suppress a prohibited certificate or commercial claim. Structured price and price-currency fields remain prohibited because the approved evidence associations are HTML-card specific.

The approved exception is an eligible 12-week completion certificate associated with the exact attendance, resolved-payment, participation-only and non-accreditation context. Statements attaching it to a 4-week plan or omitting that context still fail. Negative, unresolved and prohibitive certificate statements also remain allowed. Other positive certificate promises fail.

Internal wording is still required to be clearly labelled as unsupported, inherited, unresolved, prohibited, or not approved for public use.

## Components and data flow

One focused Python scanner module does the following:

1. load the explicit manifest of public HTML routes;
2. parse each page into visible HTML, metadata, structured data, inline JavaScript, and local script references;
3. follow only referenced local JavaScript;
4. apply category rules to each public surface;
5. classify the three authority and operational documents plus test fixtures as documentation only;
6. return structured findings with scope, category, rule, path, line, and sanitized excerpt.

One focused `unittest` module tests both scanner behavior with isolated fixtures and the current repository state. The implementation follows existing Python conventions and adds no dependency or external tooling.

## Failure output

Every failing public finding identifies:

- repository-relative file path;
- public surface type: HTML, metadata, structured data, or executable JavaScript;
- claim category;
- matched rule or value;
- line number and a short sanitized excerpt.

Output must make the offending claim and remediation location clear while avoiding unnecessary disclosure of surrounding content.

## Testing strategy

Scanner-classification tests cover these guarantees:

- prohibited visible HTML, metadata, JSON-LD, and referenced-JavaScript claims fail;
- the same phrase in each approved authority document is documentation only;
- negative test fixtures do not contaminate repository scans;
- exact approved individual teacher experience passes only in its matching teacher card on an approved route;
- exact private-plan prices, class counts and euro savings pass only in their matching pricing cards, while the homepage starting price passes only in its approved preview;
- the eligible 12-week certificate passes only with its complete eligibility context;
- a combined experience total fails;
- approved teacher and student video evidence passes;
- positive certificate promises fail while negative or unresolved wording passes;
- unreferenced inactive JavaScript is not public executable content.

Repository regression tests also protect approved teacher names, languages, and individual experience statements; expected teacher and student card associations, video IDs, thumbnails, accessible labels and titles, and student captions; plus privacy-enhanced embeds, validation, duplicate prevention, focus behavior, and keyboard controls.

## Verification and completion

Maintenance verification runs:

1. the focused scanner-classification tests;
2. full Python unittest discovery;
3. all JavaScript tests;
4. shared-layout synchronization in check mode;
5. JavaScript syntax validation;
6. `git diff --check`.

The commercial-foundation verification baseline is 42 focused trust-evidence tests, 14 focused pricing and commercial tests, 106 full Python tests, and 11 JavaScript tests. The repository scan covers 15 public HTML pages and one referenced local JavaScript file with zero public failures; documentation-only findings remain reviewable and non-failing. Future reports state the observed totals and confirm that all required approved teacher and student evidence remains present, documentation and provenance records remain available, and no external service, push, or deployment was activated without explicit authorization.

## Non-goals

- No repository-wide zero-match requirement.
- No scanning of unlinked inactive JavaScript as public executable content.
- No dependencies, build system, integration activation, deployment, or push.
- No rewriting or removal of approved teacher/student evidence or useful internal audit records.
