from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import unittest

from scripts.trust_evidence_scanner import (
    Classification,
    PUBLIC_HTML_PATHS,
    extract_public_surfaces,
    scan_repository,
)


ROOT = Path(__file__).resolve().parents[1]
TEACHER_RATE = Decimal("1.50")
AUTHORITY_PATHS = (
    "SALAM-CENTER-APPROVED-FACTS.md",
    "docs/COMMERCIAL-AND-ENROLMENT.md",
)
PLAN_ECONOMICS = (
    ("Flexible 4-week", "1 class per week", 4, "49", "6", "43", "87.76"),
    ("Flexible 4-week", "2 classes per week", 8, "69", "12", "57", "82.61"),
    ("Flexible 4-week", "4 classes per week", 16, "99", "24", "75", "75.76"),
    ("12-week", "1 class per week", 12, "119", "18", "101", "84.87"),
    ("12-week", "2 classes per week", 24, "129", "36", "93", "72.09"),
    ("12-week", "4 classes per week", 48, "229", "72", "157", "68.56"),
)


def source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class TeacherEconomicsTests(unittest.TestCase):
    def test_authority_documents_record_the_internal_teacher_rate(self):
        for relative_path in AUTHORITY_PATHS:
            document = source(relative_path)
            self.assertIn(
                "Teacher compensation is €1.50 for each eligible 40-minute lesson.",
                document,
            )
            self.assertIn("internal business information", document)
            self.assertIn("not approved for public use", document)

    def test_completed_lessons_and_used_learner_absences_are_eligible(self):
        operations = source("docs/COMMERCIAL-AND-ENROLMENT.md")
        for statement in (
            "Completed paid private lessons are eligible.",
            "Completed free trial lessons are eligible.",
            "A learner late cancellation or no-show that is treated as used is eligible when the teacher was present and available to teach.",
        ):
            self.assertIn(statement, operations)

    def test_ineligible_events_are_explicit(self):
        operations = source("docs/COMMERCIAL-AND-ENROLMENT.md")
        for statement in (
            "A class that was never scheduled is not eligible.",
            "Teacher unavailability is not eligible.",
            "A teacher-caused technical problem that requires a repeat is not eligible for an additional payment.",
        ):
            self.assertIn(statement, operations)

    def test_teacher_cancellation_is_paid_on_delivery_of_the_replacement(self):
        operations = source("docs/COMMERCIAL-AND-ENROLMENT.md")
        for statement in (
            "A teacher-cancelled class is not compensated at cancellation.",
            "Compensation attaches to the replacement class when that replacement is delivered.",
            "The original and replacement are not both paid.",
        ):
            self.assertIn(statement, operations)

    def test_all_plan_costs_contributions_and_margins_are_exact(self):
        documents = [source(relative_path) for relative_path in AUTHORITY_PATHS]
        for plan, frequency, classes, revenue, cost, contribution, margin in PLAN_ECONOMICS:
            calculated_cost = TEACHER_RATE * Decimal(classes)
            calculated_contribution = Decimal(revenue) - calculated_cost
            calculated_margin = (
                calculated_contribution / Decimal(revenue) * Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            self.assertEqual(Decimal(cost), calculated_cost)
            self.assertEqual(Decimal(contribution), calculated_contribution)
            self.assertEqual(Decimal(margin), calculated_margin)
            row = (
                f"| {plan} | {frequency} | €{revenue} | {classes} | "
                f"€{cost} | €{contribution} | {margin}% |"
            )
            for document in documents:
                self.assertIn(row, document)

    def test_free_trial_cost_is_a_separate_acquisition_cost(self):
        operations = source("docs/COMMERCIAL-AND-ENROLMENT.md")
        for statement in (
            "Each completed free 40-minute trial costs Salaam Center €1.50 in direct teacher compensation.",
            "This is a separate acquisition cost and is not included in the paid-class calculations.",
            "Allocating one trial to a learner's first paid plan reduces that plan's teacher-cost contribution by €1.50.",
            "The trial remains free to the learner.",
        ):
            self.assertIn(statement, operations)

    def test_contribution_is_not_profit_and_excluded_costs_remain_visible(self):
        operations = source("docs/COMMERCIAL-AND-ENROLMENT.md")
        self.assertIn(
            "Teacher-cost contribution is not final profit or net profit.",
            operations,
        )
        for excluded_cost in (
            "Payment-provider fees",
            "Taxes",
            "Accounting costs",
            "Administrative work",
            "Marketing costs",
            "Refunds or chargebacks",
            "Content-production costs",
            "Software or service costs",
            "The separate €1.50 acquisition cost of the free trial",
        ):
            self.assertIn(excluded_cost, operations)

    def test_teacher_compensation_review_is_resolved_with_remaining_considerations(self):
        documents = [source(relative_path) for relative_path in AUTHORITY_PATHS]
        for document in documents:
            self.assertIn("Teacher-compensation review", document)
            self.assertIn("resolved for current pre-launch pricing", document)
        operations = documents[1]
        for consideration in (
            "Payment-provider fees",
            "Tax and accounting treatment",
            "Administrative cost",
            "Marketing and acquisition cost",
            "Refund and chargeback exposure",
            "Consumer-law review",
            "Final minimum net-margin policy",
            "Future teacher-rate changes",
        ):
            self.assertIn(consideration, operations)

    def test_internal_economics_do_not_leak_to_public_surfaces(self):
        _, html_paths, script_paths = extract_public_surfaces(ROOT, PUBLIC_HTML_PATHS)
        public_text = "\n".join(
            path.read_text(encoding="utf-8") for path in (*html_paths, *script_paths)
        ).casefold()
        forbidden_values = (
            "€1.50",
            "teacher compensation",
            "teacher cost",
            "teacher-cost contribution",
            "contribution margin",
            "€43",
            "€57",
            "€75",
            "€101",
            "€93",
            "€157",
            "87.76%",
            "82.61%",
            "75.76%",
            "84.87%",
            "72.09%",
            "68.56%",
        )
        for value in forbidden_values:
            self.assertNotIn(value.casefold(), public_text, value)

    def test_authority_economics_are_documentation_only_in_the_scanner(self):
        report = scan_repository(ROOT)
        self.assertEqual((), report.failures)
        for relative_path in AUTHORITY_PATHS:
            expected_path = (ROOT / relative_path).resolve()
            findings = [
                finding
                for finding in report.documentation
                if finding.path.resolve() == expected_path and "€1.50" in finding.excerpt
            ]
            self.assertTrue(findings, relative_path)
            self.assertTrue(
                all(finding.classification is Classification.DOCUMENTATION_ONLY for finding in findings)
            )

    def test_public_plan_tuples_remain_unchanged(self):
        pricing = source("pricing/index.html")
        tuples = (
            (4, 1, 4, 49),
            (4, 2, 8, 69),
            (4, 4, 16, 99),
            (12, 1, 12, 119),
            (12, 2, 24, 129),
            (12, 4, 48, 229),
        )
        for weeks, frequency, classes, price in tuples:
            self.assertIn(
                f'data-plan-weeks="{weeks}" data-frequency="{frequency}" '
                f'data-paid-classes="{classes}" data-price-eur="{price}"',
                pricing,
            )

    def test_protected_teacher_and_student_evidence_remains_unchanged(self):
        home = source("index.html")
        teachers = source("teachers/index.html")
        for name, video_id in (
            ("Farkhonda Jami", "iUMB3pKzS_A"),
            ("Foruhar Rahmani", "iurgyXOzqFU"),
            ("Fareshta Suroush", "OtaIpKZpbMM"),
            ("Sadiah Hamid", "fOzc2cM5Twk"),
        ):
            self.assertIn(name, home)
            self.assertIn(video_id, home)
            self.assertIn(name, teachers)
            self.assertIn(video_id, teachers)
        for video_id in ("to3h-qq7_FM", "6WxiPdZNcCY"):
            self.assertIn(video_id, home)


if __name__ == "__main__":
    unittest.main()
