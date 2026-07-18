from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from scripts.trust_evidence_scanner import (
    Classification,
    Finding,
    ScanReport,
    SurfaceText,
    SurfaceType,
    classify_path,
    extract_public_surfaces,
    format_finding,
    scan_repository,
    scan_surface,
)


ROOT = Path(__file__).resolve().parents[1]


def findings(
    text: str,
    surface: SurfaceType = SurfaceType.HTML,
    classification: Classification = Classification.PUBLIC,
):
    return scan_surface(
        SurfaceText(Path("fixture.html"), surface, text, classification=classification)
    )


class SurfaceClassificationTests(unittest.TestCase):
    def test_authority_documents_and_tests_are_documentation_only(self):
        root = Path("C:/repo")
        self.assertEqual(
            Classification.DOCUMENTATION_ONLY,
            classify_path(root, root / "SALAM-CENTER-APPROVED-FACTS.md"),
        )
        self.assertEqual(
            Classification.DOCUMENTATION_ONLY,
            classify_path(root, root / "MIGRATION-SOURCE.md"),
        )
        self.assertEqual(
            Classification.DOCUMENTATION_ONLY,
            classify_path(root, root / "tests/negative_fixture.py"),
        )

    def test_only_referenced_local_javascript_is_executable(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets/js").mkdir(parents=True)
            (root / "index.html").write_text(
                '<main>Safe</main><script src="/assets/js/live.js"></script>',
                encoding="utf-8",
            )
            (root / "assets/js/live.js").write_text(
                'const state = "safe";', encoding="utf-8"
            )
            (root / "assets/js/inactive.js").write_text(
                'const claim = "500+ learners";', encoding="utf-8"
            )
            surfaces, _, scripts = extract_public_surfaces(root, ("index.html",))
            self.assertEqual({root / "assets/js/live.js"}, set(scripts))
            self.assertNotIn("inactive.js", " ".join(str(item.path) for item in surfaces))
            self.assertIn(
                SurfaceType.EXECUTABLE_JAVASCRIPT,
                {item.surface for item in surfaces},
            )


class ClaimRuleTests(unittest.TestCase):
    def test_split_visible_html_claims_are_coalesced_with_source_lines(self):
        cases = (
            ("Trusted by <strong>500+</strong> learners", "learner or family count"),
            ("Rated <strong>4.8</strong> stars", "rating or review evidence"),
            ("<span>Receive</span> a <em>certificate</em>", "certificate promise"),
            (
                "Our teachers have <strong>12+</strong> years teaching experience",
                "combined teacher experience",
            ),
            ("<strong>98%</strong> completion rate", "success percentage"),
        )
        for markup, category in cases:
            with self.subTest(category=category), TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "index.html").write_text(
                    f"<p>Safe introduction.</p>\n<p>{markup}</p>",
                    encoding="utf-8",
                )

                surfaces, _, _ = extract_public_surfaces(root, ("index.html",))
                extracted = tuple(
                    item for surface in surfaces for item in scan_surface(surface)
                )
                matching = tuple(item for item in extracted if item.category == category)

                self.assertEqual(1, len(matching))
                self.assertEqual(2, matching[0].line)

    def test_certificate_negation_is_limited_to_the_matching_clause(self):
        for value in (
            "No prior experience required; every learner will receive a certificate.",
            "No certificate is included, but every learner will receive a certificate.",
            "Not only will learners receive a certificate, they also receive feedback.",
        ):
            with self.subTest(value=value):
                result = findings(value)
                self.assertTrue(result)
                self.assertIn("certificate promise", {item.category for item in result})

        self.assertEqual((), findings("No certificate is included."))
        self.assertEqual((), findings("Learners do not receive a certificate."))

    def test_certificate_contractions_and_cannot_are_negative(self):
        negative = (
            "We don't provide certificates.",
            "She doesn't provide certificates.",
            "We didn't provide certificates.",
            "We won't provide certificates.",
            "We can't provide certificates.",
            "We cannot provide certificates.",
            "The certificate isn't included.",
            "Certificates aren't included.",
        )
        for value in negative:
            with self.subTest(value=value):
                self.assertEqual((), findings(value))

        positive = (
            "Not only will learners receive a certificate.",
            "Certificates are included.",
            "Students will receive a certificate.",
        )
        for value in positive:
            with self.subTest(value=value):
                self.assertTrue(findings(value))

    def test_json_ld_is_parsed_recursively_with_malformed_fallback(self):
        nested_review = (
            '{"@context":"https://schema.org","@graph":['
            '{"@type":"EducationalOrganization","subjectOf":'
            '{"@type":"Review","reviewBody":"Wonderful school"}}]}'
        )
        malformed_review = '{"@type":"Review","reviewBody":"Wonderful school"'
        for value in (nested_review, malformed_review):
            with self.subTest(value=value):
                result = findings(value, SurfaceType.STRUCTURED_DATA)
                self.assertTrue(result)
                self.assertIn(
                    "structured rating or review",
                    {item.category for item in result},
                )

        self.assertEqual(
            (),
            findings(
                '{"@type":"EducationalOrganization",'
                '"description":"Review the lesson plan before class"}',
                SurfaceType.STRUCTURED_DATA,
            ),
        )

    def test_json_ld_type_iris_are_matched_by_terminal_schema_term(self):
        prohibited = (
            '{"@type":"https://schema.org/Review"}',
            '{"@type":"https://schema.org#Review"}',
            '{"@type":"schema:Review"}',
            '{"@type":"https://schema.org/AggregateRating"}',
            '{"@type":"schema:AggregateRating"',
        )
        for value in prohibited:
            with self.subTest(value=value):
                result = findings(value, SurfaceType.STRUCTURED_DATA)
                self.assertTrue(result)
                self.assertIn(
                    "structured rating or review",
                    {item.category for item in result},
                )

        safe = (
            '{"@type":"https://schema.org/Organization"}',
            '{"@type":"https://schema.org/Preview"}',
            '{"@type":"schema:ReviewPolicy"}',
        )
        for value in safe:
            with self.subTest(value=value):
                self.assertEqual((), findings(value, SurfaceType.STRUCTURED_DATA))

    def test_javascript_dynamic_claims_are_detected_only_in_rendering_sinks(self):
        unsafe = (
            "node.textContent = 'Trusted by ' + learnerCount + ' learners';",
            "node.innerHTML = `Rated ${ratingValue} stars`;",
            "node.insertAdjacentText('beforeend', reviewCount + ' reviews');",
            "node.textContent = `${successRate}% success rate`;",
            "node.replaceChildren(counter.dataset.count + ' students');",
            "node.innerHTML += '<b>' + familyTotal + ' families</b>';",
        )
        for value in unsafe:
            with self.subTest(value=value):
                self.assertTrue(findings(value, SurfaceType.EXECUTABLE_JAVASCRIPT))

        safe = (
            "const learnerCount = records.length;",
            "node.textContent = 'Choose a learner';",
            "node.insertAdjacentText('beforeend', 'Read the reviews policy');",
            "const reviewCount = auditRows.length; status.textContent = 'Ready';",
        )
        for value in safe:
            with self.subTest(value=value):
                self.assertEqual(
                    (),
                    findings(value, SurfaceType.EXECUTABLE_JAVASCRIPT),
                )

    def test_javascript_direct_dynamic_rendering_and_split_literals_fail(self):
        unsafe = (
            "node.innerText = `${learnerCount} learners`;",
            "node.appendChild(document.createTextNode(`${learnerCount} learners`));",
            "node.textContent = `${learners.length} learners`;",
            "node.textContent = '500+' + ' learners';",
        )
        for value in unsafe:
            with self.subTest(value=value):
                result = findings(value, SurfaceType.EXECUTABLE_JAVASCRIPT)
                self.assertTrue(result)
                self.assertIn("learner or family count", {item.category for item in result})

        safe = (
            "node.innerText = 'Choose a learner';",
            "node.appendChild(document.createTextNode('Ready'));",
            "node.appendChild(learnerCard);",
            "const learnerCount = learners.length;",
            "node.textContent = `${learner.name}`;",
            "node.textContent = '500+';",
            "node.textContent = 'learners';",
        )
        for value in safe:
            with self.subTest(value=value):
                self.assertEqual((), findings(value, SurfaceType.EXECUTABLE_JAVASCRIPT))

    def test_javascript_sink_literal_rendering_is_normalized_without_length_leakage(self):
        unsafe = (
            "node.innerText = '4.9' + ' stars';",
            "node.textContent = '97%' + ' success rate';",
            "node.innerHTML = '12+' + ' years teaching experience';",
        )
        for value in unsafe:
            with self.subTest(value=value):
                self.assertTrue(findings(value, SurfaceType.EXECUTABLE_JAVASCRIPT))

        self.assertEqual(
            (),
            findings(
                "status.textContent = `${selectedLessons.length} lessons selected "
                "for this learner`;",
                SurfaceType.EXECUTABLE_JAVASCRIPT,
            ),
        )

    def test_javascript_call_sinks_select_each_rendered_text_argument(self):
        unsafe = (
            "node.insertAdjacentText('beforeend', '4.9' + ' stars');",
            "node.appendChild(document.createTextNode('97%' + ' success rate'));",
            "node.append('Ready', '4.9' + ' stars');",
            "node.prepend('97%' + ' success rate', 'Ready');",
            "node.before('Ready', '12+' + ' years teaching experience');",
            "node.after('4.9' + ' stars', 'Ready');",
            "node.replaceWith('Ready', '97%' + ' success rate');",
            "node.replaceChildren('12+' + ' years teaching experience', 'Ready');",
        )
        for value in unsafe:
            with self.subTest(value=value):
                self.assertTrue(findings(value, SurfaceType.EXECUTABLE_JAVASCRIPT))

        safe = (
            "node.insertAdjacentText('beforeend', 'Ready');",
            "node.insertAdjacentHTML('afterbegin', '<span>Ready</span>');",
            "node.appendChild(document.createTextNode('Ready'));",
            "node.append('Ready', statusNode);",
            "node.prepend(statusNode, 'Ready');",
            "node.before('Ready', statusNode);",
            "node.after(statusNode, 'Ready');",
            "node.replaceWith('Ready', statusNode);",
            "node.replaceChildren(statusNode, 'Ready');",
        )
        for value in safe:
            with self.subTest(value=value):
                self.assertEqual((), findings(value, SurfaceType.EXECUTABLE_JAVASCRIPT))

    def test_javascript_adjacent_rendered_arguments_form_one_virtual_expression(self):
        unsafe = (
            "node.append(reviewCount, ' reviews');",
            "node.replaceChildren(learnerCount, ' learners');",
            "node.prepend(ratingValue, ' stars');",
            "node.before(learnerCount, ' learners');",
            "node.after(reviewCount, ' reviews');",
            "node.replaceWith(experienceTotal, ' years teaching experience');",
        )
        for value in unsafe:
            with self.subTest(value=value):
                self.assertTrue(findings(value, SurfaceType.EXECUTABLE_JAVASCRIPT))

        safe = (
            "node.append(iconNode, ' learner profile');",
            "node.append(selectedLessons.length, ' lessons selected');",
            "node.prepend(learnerAvatar, ' learner profile');",
            "node.replaceChildren(reviewIcon, ' reviews panel');",
        )
        for value in safe:
            with self.subTest(value=value):
                self.assertEqual((), findings(value, SurfaceType.EXECUTABLE_JAVASCRIPT))

    def test_protected_evidence_requires_its_approved_card_association(self):
        teacher_experience = "2 years teaching Tajweed and Tafsir"
        student_caption = (
            "A short message of appreciation from a student sharing their "
            "learning experience."
        )
        self.assertTrue(
            scan_surface(
                SurfaceText(
                    Path("teachers/index.html"),
                    SurfaceType.HTML,
                    teacher_experience,
                )
            )
        )
        self.assertTrue(
            scan_surface(
                SurfaceText(
                    Path("index.html"),
                    SurfaceType.HTML,
                    student_caption,
                )
            )
        )

        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text(
                '<article class="teacher-card">'
                '<button data-youtube-id="iUMB3pKzS_A"></button>'
                f'<p class="teacher-card__name">Farkhonda Jami</p>'
                f'<p class="teacher-card__specialty">{teacher_experience}</p>'
                '</article>'
                '<article class="feedback-video-card">'
                '<button data-youtube-id="to3h-qq7_FM"></button>'
                f'<p class="feedback-video-card__text">{student_caption}</p>'
                '</article>',
                encoding="utf-8",
            )
            surfaces, _, _ = extract_public_surfaces(root, ("index.html",))
            extracted = tuple(
                item for surface in surfaces for item in scan_surface(surface)
            )
            self.assertEqual((), extracted)

            (root / "index.html").write_text(
                '<article class="teacher-card">'
                '<button data-youtube-id="iurgyXOzqFU"></button>'
                '<p class="teacher-card__name">Another Teacher</p>'
                f'<p class="teacher-card__specialty">{teacher_experience}</p>'
                '</article>'
                '<article class="feedback-video-card">'
                '<button data-youtube-id="6WxiPdZNcCY"></button>'
                f'<p class="feedback-video-card__text">{student_caption}</p>'
                '</article>',
                encoding="utf-8",
            )
            surfaces, _, _ = extract_public_surfaces(root, ("index.html",))
            misuse = tuple(
                item for surface in surfaces for item in scan_surface(surface)
            )
            self.assertIn("combined teacher experience", {item.category for item in misuse})
            self.assertIn("testimonial or endorsement", {item.category for item in misuse})

    def test_excerpt_is_centered_on_match_and_redacts_query_secrets(self):
        text = (
            "x" * 220
            + " https://example.test/capture?token=TOPSECRET&campaign=HIDDEN "
            + "Trusted by 500+ learners "
            + "z" * 220
        )
        item = findings(text)[0]

        self.assertIn("500+ learners", item.excerpt)
        self.assertLessEqual(len(item.excerpt), 180)
        self.assertNotIn("TOPSECRET", item.excerpt)
        self.assertNotIn("HIDDEN", item.excerpt)
        self.assertIn("[redacted]", item.excerpt)

    def test_visible_metadata_structured_data_and_javascript_claims_fail(self):
        cases = (
            (SurfaceType.HTML, "Trusted by 500+ learners"),
            (SurfaceType.METADATA, "Rated 4.9/5 by families"),
            (SurfaceType.STRUCTURED_DATA, '{"@type":"AggregateRating","ratingValue":"4.9"}'),
            (SurfaceType.EXECUTABLE_JAVASCRIPT, 'node.textContent = "97% success rate";'),
        )
        for surface, value in cases:
            with self.subTest(surface=surface):
                result = findings(value, surface)
                self.assertTrue(result)
                self.assertTrue(all(item.is_failure for item in result))

    def test_documentation_and_negative_fixtures_are_non_failing(self):
        for path in (
            Path("SALAM-CENTER-APPROVED-FACTS.md"),
            Path("MIGRATION-SOURCE.md"),
            Path("tests/fixture.py"),
        ):
            result = scan_surface(
                SurfaceText(
                    path,
                    SurfaceType.HTML,
                    "12+ years of teaching experience",
                    classification=Classification.DOCUMENTATION_ONLY,
                )
            )
            self.assertTrue(result)
            self.assertTrue(all(not item.is_failure for item in result))

    def test_unassociated_individual_experience_and_combined_total_fail(self):
        for value in (
            "2 years teaching Tajweed and Tafsir",
            "Our team has 12+ years of teaching experience",
        ):
            with self.subTest(value=value):
                result = findings(value)
                self.assertEqual("combined teacher experience", result[0].category)

    def test_certificate_promises_fail_but_negative_or_unresolved_copy_passes(self):
        for value in (
            "Certificate included.",
            "Receive a certificate.",
            "End-of-course certificate included.",
        ):
            self.assertTrue(findings(value), value)
        for value in (
            "Certificates are not currently promised.",
            "Certificate requirements remain unresolved.",
            "Do not publish certificate claims.",
            "No certificate is included.",
            "Do not receive a certificate.",
        ):
            self.assertEqual((), findings(value), value)

    def test_testimonial_and_rating_evidence_fails(self):
        for value in (
            "What families say",
            "Recommended by parents",
            "★★★★★",
            "Read 72 reviews",
        ):
            with self.subTest(value=value):
                self.assertTrue(findings(value))

    def test_aggregate_statistics_and_counter_attributes_fail(self):
        for surface, value in (
            (SurfaceType.HTML, '<span data-count-to="250">'),
            (SurfaceType.HTML, "98% completion rate"),
            (SurfaceType.STRUCTURED_DATA, '{"reviewCount": 120}'),
        ):
            with self.subTest(value=value):
                self.assertTrue(findings(value, surface))

    def test_active_analytics_forms_and_contact_integrations_fail(self):
        for value in (
            "https://www.googletagmanager.com/gtag/js?id=G-TEST",
            "gtag('config', 'G-TEST')",
            '<form action="https://example.test/contact">',
            "https://wa.me/123456789",
            "mailto:hello@example.test",
            "tel:+34123456789",
            "https://script.google.com/macros/s/DEPLOYMENT/exec",
        ):
            with self.subTest(value=value):
                self.assertTrue(findings(value))

    def test_approved_video_ids_pass_but_collective_reuse_fails(self):
        approved_video_ids = (
            "iUMB3pKzS_A",
            "iurgyXOzqFU",
            "OtaIpKZpbMM",
            "fOzc2cM5Twk",
            "to3h-qq7_FM",
            "6WxiPdZNcCY",
        )
        for value in approved_video_ids:
            with self.subTest(value=value):
                self.assertEqual(
                    (),
                    scan_surface(
                        SurfaceText(
                            Path("success/index.html"),
                            SurfaceType.HTML,
                            f"https://www.youtube-nocookie.com/embed/{value}",
                        )
                    ),
                )

        misuse = findings("Our team has 2 years teaching Tajweed and Tafsir")
        self.assertTrue(misuse)
        self.assertEqual("combined teacher experience", misuse[0].category)

    def test_review_language_variants_fail(self):
        for value in (
            "Rated 4.8 stars",
            "Parents recommend us",
            "Success rate: 97%",
            "Certificate will be provided on completion.",
        ):
            with self.subTest(value=value):
                self.assertTrue(findings(value))

    def test_operational_recommendation_copy_passes_but_endorsements_fail(self):
        for value in (
            "Receive a recommendation",
            "A recommendation, not a guarantee",
        ):
            with self.subTest(value=value):
                self.assertEqual((), findings(value))
        self.assertTrue(findings("Parents recommend us"))

    def test_audience_recommendation_headings_fail(self):
        headings = (
            "Parent recommendations",
            "Parents recommendations",
            "Family recommendations",
            "Families recommendations",
            "Student recommendations",
            "Students recommendations",
            "Recommendations from parent",
            "Recommendations from parents",
            "Recommendations from family",
            "Recommendations from families",
            "Recommendations from student",
            "Recommendations from students",
        )
        for heading in headings:
            with self.subTest(heading=heading):
                self.assertTrue(findings(heading))

    def test_finding_line_excerpt_and_public_classification(self):
        result = findings("Safe line\nTrusted by 500+ learners")
        self.assertEqual(2, result[0].line)
        self.assertIn("Trusted by 500+ learners", result[0].excerpt)
        self.assertLessEqual(len(result[0].excerpt), 180)
        self.assertEqual(Classification.PUBLIC, result[0].classification)
        self.assertIsInstance(result[0], Finding)

    def test_failure_format_contains_remediation_fields(self):
        item = findings("Trusted by 500+ learners")[0]
        message = format_finding(item)
        for value in ("fixture.html", "HTML", "learner or family count", item.rule, "line 1"):
            self.assertIn(value, message)

    def test_extractor_surfaces_counter_attribute_names_for_scanning(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text(
                '<span data-count-to="250">250</span>', encoding="utf-8"
            )
            surfaces, _, _ = extract_public_surfaces(root, ("index.html",))
            findings_from_extraction = tuple(
                finding for surface in surfaces for finding in scan_surface(surface)
            )
            self.assertTrue(findings_from_extraction)
            self.assertEqual("aggregate statistic", findings_from_extraction[0].category)

    def test_extractor_emits_external_analytics_scripts_for_scanning(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text(
                '<script src="https://www.googletagmanager.com/gtag/js?id=G-TEST"></script>',
                encoding="utf-8",
            )
            surfaces, _, scripts = extract_public_surfaces(root, ("index.html",))
            findings_from_extraction = tuple(
                finding for surface in surfaces for finding in scan_surface(surface)
            )
            self.assertEqual((), scripts)
            self.assertIn(SurfaceType.EXECUTABLE_JAVASCRIPT, {item.surface for item in surfaces})
            self.assertTrue(findings_from_extraction)
            self.assertEqual("analytics integration", findings_from_extraction[0].category)

    def test_extractor_detects_real_relative_form_actions_but_not_form_prose(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text(
                '<form><button>Book</button></form>'
                '<form action="/book-trial"><button>Book</button></form>',
                encoding="utf-8",
            )
            surfaces, _, _ = extract_public_surfaces(root, ("index.html",))
            findings_from_extraction = tuple(
                finding for surface in surfaces for finding in scan_surface(surface)
            )
            self.assertTrue(findings_from_extraction)
            self.assertEqual(2, len(findings_from_extraction))
            self.assertEqual(
                "active form or contact destination", findings_from_extraction[0].category
            )
        self.assertEqual((), findings("Complete the form when you are ready."))

    def test_each_form_has_one_finding_and_actionless_forms_remain_in_scope(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text(
                '<form action="https://example.test/contact"></form>\n'
                '<form action="mailto:hello@example.test"></form>\n'
                '<form><button type="submit">Send</button></form>',
                encoding="utf-8",
            )
            surfaces, _, _ = extract_public_surfaces(root, ("index.html",))
            form_findings = tuple(
                item
                for surface in surfaces
                for item in scan_surface(surface)
                if item.category == "active form or contact destination"
            )

            # Missing action is not an inert form: browsers submit to the current URL.
            self.assertEqual(3, len(form_findings))
            self.assertEqual([1, 2, 3], [item.line for item in form_findings])


class RepositoryTrustEvidenceTests(unittest.TestCase):
    def test_linked_html_routes_require_an_explicit_manifest_decision(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "new-route").mkdir()
            (root / "index.html").write_text(
                '<a href="#main-content">Skip</a>'
                '<a href="/new-route/">New public page</a>',
                encoding="utf-8",
            )
            (root / "new-route/index.html").write_text(
                '<main id="main-content">Safe</main>',
                encoding="utf-8",
            )
            for path in (
                "SALAM-CENTER-APPROVED-FACTS.md",
                "MIGRATION-SOURCE.md",
            ):
                (root / path).write_text("documentation", encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError,
                r"Unlisted internal HTML route.*new-route/index\.html",
            ):
                scan_repository(root, ("index.html",))

            report = scan_repository(root, ("index.html", "new-route/index.html"))
            self.assertEqual(
                (root / "index.html", root / "new-route/index.html"),
                report.public_html_paths,
            )

    def test_current_public_surfaces_have_no_prohibited_trust_claims(self):
        report = scan_repository(ROOT)
        self.assertIsInstance(report, ScanReport)
        self.assertEqual(
            [],
            list(report.failures),
            "\n".join(format_finding(item, ROOT) for item in report.failures),
        )
        self.assertEqual(
            tuple(ROOT / path for path in (
                "index.html",
                "our-approach/index.html",
                "programs/index.html",
                "programs/quran/index.html",
                "programs/dari-persian/index.html",
                "programs/afghan-culture-islamic-ethics/index.html",
                "teachers/index.html",
                "how-it-works/index.html",
                "about/index.html",
                "book-trial/index.html",
                "privacy-policy/index.html",
                "terms/index.html",
                "success/index.html",
                "404.html",
            )),
            report.public_html_paths,
        )
        self.assertEqual(
            (ROOT / "assets/js/main.js",),
            report.public_script_paths,
        )
        self.assertTrue(all(
            item.classification is Classification.DOCUMENTATION_ONLY
            for item in report.documentation
        ))

    def test_referenced_script_claim_fails_but_unreferenced_script_is_inactive(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets/js").mkdir(parents=True)
            (root / "index.html").write_text(
                '<script src="/assets/js/live.js"></script>', encoding="utf-8"
            )
            (root / "assets/js/live.js").write_text(
                'const claim = "500+ learners";', encoding="utf-8"
            )
            (root / "assets/js/inactive.js").write_text(
                'const claim = "500+ learners";', encoding="utf-8"
            )
            for path in (
                "SALAM-CENTER-APPROVED-FACTS.md",
                "MIGRATION-SOURCE.md",
            ):
                (root / path).write_text("500+ learners", encoding="utf-8")

            report = scan_repository(root, ("index.html",))

            self.assertEqual((root / "index.html",), report.public_html_paths)
            self.assertEqual((root / "assets/js/live.js",), report.public_script_paths)
            self.assertEqual([root / "assets/js/live.js"], [item.path for item in report.failures])
            self.assertEqual(
                [root / "MIGRATION-SOURCE.md", root / "SALAM-CENTER-APPROVED-FACTS.md"],
                [item.path for item in report.documentation],
            )

    def test_manifest_path_outside_root_is_rejected_before_existence_validation(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as outside_directory:
            root = Path(directory)
            outside_path = Path(outside_directory) / "outside.html"
            outside_path.write_text("500+ learners", encoding="utf-8")
            for path in (
                "SALAM-CENTER-APPROVED-FACTS.md",
                "MIGRATION-SOURCE.md",
            ):
                (root / path).write_text("documentation", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "outside the repository root"):
                scan_repository(root, (str(outside_path),))

    def test_all_approved_teacher_and_student_evidence_remain(self):
        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        teachers = (ROOT / "teachers/index.html").read_text(encoding="utf-8")
        script = (ROOT / "assets/js/main.js").read_text(encoding="utf-8")
        styles = (ROOT / "assets/css/styles.css").read_text(encoding="utf-8")

        teacher_evidence = (
            ("Farkhonda Jami", "TURKISH &middot; PERSIAN", "2 years teaching Tajweed and Tafsir", "iUMB3pKzS_A"),
            ("Foruhar Rahmani", "PERSIAN &middot; ENGLISH", "2 years teaching Tajweed", "iurgyXOzqFU"),
            ("Fareshta Suroush", "PERSIAN &middot; ENGLISH &middot; TURKISH", "2 years teaching Tajweed", "OtaIpKZpbMM"),
            ("Sadiah Hamid", "ENGLISH &middot; ARABIC &middot; TURKISH &middot; PERSIAN", "6 years teaching Tajweed, Hifz, and Quranic recitation", "fOzc2cM5Twk"),
        )
        for page_name, page in (("homepage", homepage), ("teachers page", teachers)):
            cards = re.findall(
                r'<article class="teacher-card"[^>]*>(.*?)</article>',
                page,
                re.DOTALL,
            )
            self.assertEqual(4, len(cards), page_name)
            video_ids = []
            for name, languages, experience, video_id in teacher_evidence:
                with self.subTest(page=page_name, name=name):
                    card = next(card for card in cards if name in card)
                    video_ids.append(video_id)
                    for value in (name, languages, experience, "Lesson sample available above."):
                        self.assertIn(value, card)
                    self.assertIn(
                        f'<button type="button" class="teacher-card__portrait teacher-card__portrait--youtube" data-youtube-id="{video_id}" data-youtube-title="{name} lesson sample" aria-label="Play {name} lesson sample">',
                        card,
                    )
                    self.assertIn(
                        f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                        card,
                    )
            self.assertEqual(4, len(set(video_ids)), page_name)

        student_evidence = (
            ("to3h-qq7_FM", "Student message 1", "Play student message 1", "A student shares appreciation", "A short message of appreciation from a student sharing their learning experience."),
            ("6WxiPdZNcCY", "Student message 2", "Play student message 2", "Thanks from a young learner", "A student shares thanks and happiness about their Quran learning journey."),
        )
        student_cards = re.findall(
            r'<article class="feedback-video-card"[^>]*>(.*?)</article>',
            homepage,
            re.DOTALL,
        )
        self.assertEqual(2, len(student_cards))
        for video_id, title, label, heading, caption in student_evidence:
            with self.subTest(video_id=video_id):
                card = next(card for card in student_cards if video_id in card)
                for value in ("Student message", heading, caption):
                    self.assertIn(value, card)
                self.assertIn(
                    f'<button type="button" class="feedback-video-card__media" data-youtube-id="{video_id}" data-youtube-title="{title}" aria-label="{label}">',
                    card,
                )
                self.assertIn(
                    f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                    card,
                )

        for page in (homepage, teachers):
            video_ids = re.findall(r'data-youtube-id="([A-Za-z0-9_-]+)"', page)
            self.assertEqual(len(video_ids), len(set(video_ids)))
            for video_id in video_ids:
                self.assertRegex(video_id, r"^[A-Za-z0-9_-]{11}$")
            self.assertNotIn("<div class=\"teacher-card__portrait", page)
            self.assertNotIn("<div class=\"feedback-video-card__media", page)

        handler_start = script.index("document.querySelectorAll('[data-youtube-id]').forEach(trigger => {")
        handler = script[handler_start:]
        for value in (
            "trigger.addEventListener('click', () => {",
            "if (isActivated) return",
            "/^[A-Za-z0-9_-]{11}$/.test(videoId || '')",
            "iframe.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(videoId)}?autoplay=1&rel=0&playsinline=1${origin}`",
            "iframe.title = title",
            "iframe.tabIndex = 0",
            "iframe.referrerPolicy = 'strict-origin-when-cross-origin'",
            "iframe.allowFullscreen = true",
            "player.setAttribute('aria-label', title)",
            "isActivated = true",
            "trigger.replaceWith(player)",
            "iframe.focus({ preventScroll: true })",
        ):
            self.assertIn(value, handler)
        self.assertLess(handler.index("if (isActivated) return"), handler.index("const videoId"))
        self.assertLess(handler.index("/^[A-Za-z0-9_-]{11}$/.test(videoId || '')"), handler.index("const iframe"))
        self.assertLess(handler.index("isActivated = true"), handler.index("trigger.replaceWith(player)"))
        self.assertLess(handler.index("trigger.replaceWith(player)"), handler.index("iframe.focus({ preventScroll: true })"))
        self.assertNotIn("https://www.youtube.com/embed/", script)
        self.assertIn(":focus-visible", styles)
        self.assertIn(".youtube-inline-player:focus,", styles)
        self.assertIn(".youtube-inline-player.has-focus", styles)


if __name__ == "__main__":
    unittest.main()
