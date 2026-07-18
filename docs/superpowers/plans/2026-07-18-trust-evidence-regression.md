# Scope-Aware Trust-Evidence Regression Implementation Record

## Status

Implemented and verified on 2026-07-18. This document records the shipped architecture and provides the maintenance runbook for `scripts/trust_evidence_scanner.py` and `tests/trust_evidence_regression_test.py`.

The initial implementation phase was held uncommitted for review. Final repository integration is governed by separate explicit approval. This historical constraint does not prohibit an authorized local commit, and it never authorizes a push, deployment, publishing action, or external-service activation.

## Goal

Reject unsupported trust claims on Salaam Center's actual public surfaces while retaining approved teacher and student video evidence and useful documentation-only audit or migration provenance.

## Implemented architecture

The dependency-free Python scanner owns:

- an explicit 15-route public HTML manifest;
- public HTML, metadata, JSON-LD, inline-script, and referenced-local-script extraction;
- repository-contained local script resolution without following network URLs;
- scope classification as public, documentation only, or inactive;
- category-level trust-claim rules and structured findings;
- approved teacher/student evidence association by route, card, identity or video ID, and exact text;
- deterministic repository aggregation and public/documentation finding separation.

The focused `unittest` module covers isolated fixtures and the current repository. Existing Python accessibility, migration, layout, and video suites plus the Node runtime suites provide complementary regression coverage.

No dependency, build system, analytics, form, contact destination, payment path, deployment configuration, or publishing integration was added.

## Public-scope contract

`PUBLIC_HTML_PATHS` is the source of truth for public pages. The scanner requires every manifest path to exist and verifies that linked internal HTML routes remain covered. Shared navigation and footer content are covered because they are rendered into those pages.

Executable JavaScript scope includes inline public scripts and local scripts referenced from a manifest page. Unreferenced JavaScript and unlisted, unlinked HTML are inactive; file extension alone does not make either public.

`SALAM-CENTER-APPROVED-FACTS.md`, `MIGRATION-SOURCE.md`, `docs/COMMERCIAL-AND-ENROLMENT.md`, and test fixtures are documentation-only scope. Authority-document classification is path-based. Editors must nevertheless keep unsupported or retired references clearly labelled as internal, inherited, unsupported, unresolved, prohibited, or not approved for public use.

## Claim and evidence behavior

The scanner rejects unsupported public testimonial language, ratings/reviews, learner or family counts, success percentages, positive certificate promises, prices, currencies, percentage badges, automatic renewal, checkout or completed-payment states, free-paid-plan claims, tax-inclusion claims, named payment providers, combined teacher-experience totals, aggregate statistics/counters, and active inherited analytics, form, or contact behavior.

`APPROVED_TEACHER_EVIDENCE` associates each approved teacher name, individual experience statement, and video ID. `APPROVED_STUDENT_EVIDENCE` associates each approved student video ID and consent-sensitive caption. A matching evidence string is protected only inside the expected card on an approved route; unassociated reuse remains scannable and fails when it matches a prohibited category.

Positive certificate-promise patterns fail unless the matching predicate contains a recognized direct negative construction or the phrase is protected inside the exact eligible 12-week evidence card with its attendance, resolved-payment, participation-only and non-accreditation context. Exact commercial prices and savings are similarly protected only in their associated approved pricing card or homepage preview. Structured price and price-currency fields fail outside those HTML associations, and an unrelated negative phrase cannot mask renewal, checkout, free-paid-plan, tax or certificate evidence. Wording such as unresolved or prohibited is acceptable only when it does not make a positive promise. Documentation-only classification does not depend on these words.

These exact commercial associations are narrow public-evidence exceptions, not broad allowlists.

Each finding contains path, line, surface, category, matched rule, classification, and a sanitized excerpt capped at 180 characters. Public findings fail the audit; documentation-only findings remain visible for review without failing it.

## Maintained interfaces

- `classify_path(...)` classifies repository-contained paths.
- `extract_public_surfaces(...)` extracts public surfaces and referenced local scripts.
- `scan_surface(...)` returns structured findings for one surface.
- `format_finding(...)` produces actionable, sanitized output.
- `scan_repository(...)` validates the manifest and returns a deterministic `ScanReport`.
- `ScanReport.failures` contains public failures; `ScanReport.documentation` contains documentation-only findings.

## Maintenance workflow

1. Add or adjust focused fixtures before changing claim semantics, public scope, or approved evidence associations.
2. Make the smallest scanner change that satisfies the intended behavior without broad keyword exemptions.
3. Run the focused module, then the full Python and JavaScript suites.
4. Run layout, syntax, and diff checks.
5. Inspect the scanner inventory and every documentation-only finding; do not chase a repository-wide zero-match result.
6. Confirm all approved evidence and player behaviors remain present and no external integration or deployment surface was activated.

Use these verification commands from the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m unittest tests.trust_evidence_regression_test -v
python -m unittest tests.pricing_and_commercial_test -v
python -m unittest discover -s tests -p '*_test.py'
$testFiles = (Get-ChildItem -Path 'tests' -Filter '*.js' -File).FullName
node --test $testFiles
python scripts/sync_shared_layout.py --check
node --check assets/js/main.js
git diff --check
```

The commercial-foundation verification baseline recorded on 2026-07-18 is:

- 42 focused trust-evidence tests;
- 14 focused pricing and commercial tests;
- 106 full Python tests;
- 11 JavaScript tests;
- 15 public HTML pages;
- 1 referenced local JavaScript file;
- 0 public trust-evidence failures.

Totals may grow as coverage changes; maintenance reports must state the values actually observed.

## Review checklist

- The public route manifest covers all current linked HTML routes.
- Public HTML, metadata, structured data, navigation, and referenced JavaScript contain no prohibited trust claims.
- Documentation-only occurrences are classified as non-failing and retain clear internal-use labels.
- Approved teacher names, languages, and individual experience statements remain present; expected teacher and student card associations, video IDs, thumbnails, accessible labels and titles, and student captions remain present.
- The player retains `youtube-nocookie.com`, ID validation, duplicate activation prevention, native accessible controls, descriptive iframe naming, focus transfer, visible focus, and keyboard behavior.
- Focus restoration is required only where a closable interaction already provides a return target; the current inline replacement player is not a dialog.
- No authority/provenance record was removed merely to reduce search counts.
- No generated caches, secrets, live forms, analytics, contact destinations, payments, CNAME, workflows, or deployment files enter the change.
- `git diff --check` and all verification commands pass before integration.
