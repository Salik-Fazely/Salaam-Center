from decimal import Decimal, ROUND_HALF_UP
import html
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PLAN_EVIDENCE = {
    (4, 1): (4, 49, None),
    (4, 2): (8, 69, None),
    (4, 4): (16, 99, None),
    (12, 1): (12, 119, 28),
    (12, 2): (24, 129, 78),
    (12, 4): (48, 229, 68),
}

EFFECTIVE_REVENUE = {
    (4, 1): "12.25",
    (4, 2): "8.63",
    (4, 4): "6.19",
    (12, 1): "9.92",
    (12, 2): "5.38",
    (12, 4): "4.77",
}


def source(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def visible(value):
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(value).split())


def attributes(value):
    return dict(re.findall(r'([:\w-]+)\s*=\s*["\']([^"\']*)["\']', value))


def pricing_cards():
    cards = []
    for match in re.finditer(
        r'<article\s+class="[^"]*\bpricing-card\b[^"]*"(?P<attrs>[^>]*)>'
        r'(?P<body>.*?)</article>',
        source("en/pricing/index.html"),
        flags=re.I | re.S,
    ):
        cards.append((attributes(match.group("attrs")), match.group("body")))
    return cards


class PricingPageTests(unittest.TestCase):
    def test_pricing_page_has_exact_metadata_scope_and_is_indexable(self):
        page = source("en/pricing/index.html")
        text = visible(page)
        self.assertIn(
            "<title>Pricing | Salaam Center Private Quran and Dari/Persian Classes</title>",
            page,
        )
        self.assertIn(
            '<meta name="description" content="Compare flexible 4-week and 12-week plans for private online Quran and Dari/Persian lessons. Every paid class is 40 minutes." />',
            page,
        )
        self.assertNotIn('<meta name="robots" content="noindex, nofollow" />', page)
        self.assertIn('<link rel="canonical" href="https://salaam.center/en/pricing/" />', page)
        self.assertIn("Private lesson plans", text)
        self.assertIn("Simple plans for consistent learning", text)
        self.assertIn(
            "These prices apply to one-to-one Quran and Dari/Persian lessons. "
            "Afghan Culture & Islamic Ethics group pricing will be published when "
            "cohort arrangements are confirmed.",
            text,
        )
        self.assertIn(
            "Private-plan pricing does not cover the Afghan Culture & Islamic Ethics group program.",
            text,
        )

    def test_six_pricing_cards_match_the_exact_approved_plan_tuples(self):
        cards = pricing_cards()
        self.assertEqual(6, len(cards))
        observed = {}
        for attrs, body in cards:
            key = (int(attrs["data-plan-weeks"]), int(attrs["data-frequency"]))
            self.assertNotIn(key, observed)
            observed[key] = (
                int(attrs["data-paid-classes"]),
                int(attrs["data-price-eur"]),
                int(attrs["data-saving-eur"]) if attrs.get("data-saving-eur") else None,
            )
            text = visible(body)
            weeks, frequency = key
            paid_classes, price, saving = PLAN_EVIDENCE[key]
            self.assertIn(
                "1 class per week" if frequency == 1 else f"{frequency} classes per week",
                text,
            )
            self.assertIn(f"{paid_classes} paid classes", text)
            self.assertIn("40 minutes each", text)
            self.assertIn(f"€{price} total", text)
            self.assertIn("Private Quran or Dari/Persian", text)
            self.assertIn("One learner", text)
            self.assertIn("One selected program", text)
            self.assertIn(f"{weeks}-week teaching period", text)
            self.assertIn(
                "6-week final validity" if weeks == 4 else "16-week final validity",
                text,
            )
            self.assertIn("Does not renew automatically", text)
            self.assertIn(
                '<a class="btn btn--secondary" href="/en/book-trial/">Start with a Free Trial</a>',
                body,
            )
            if saving is None:
                self.assertNotIn("Saves €", text)
            else:
                self.assertIn(
                    f"Saves €{saving} compared with three consecutive 4-week plans at the same frequency.",
                    text,
                )
        self.assertEqual(PLAN_EVIDENCE, observed)

    def test_pricing_page_has_no_discount_badges_checkout_or_data_collection(self):
        page = source("en/pricing/index.html")
        text = visible(page)
        main = re.search(r'<main id="main-content">.*?</main>', page, re.S).group(0)
        for value in (
            "20% off",
            "40% off",
            "30% off",
            "19.0%",
            "37.7%",
            "22.9%",
            "Buy Now",
            "Checkout",
            "Subscribe",
            "Pay Now",
            "Reserve with Payment",
            "USD",
            "CAD",
            "GBP",
            "PayPal",
            "Revolut",
            "Stripe",
        ):
            if value in ("USD", "CAD", "GBP"):
                self.assertNotRegex(text, rf"\b{value}\b", value)
            else:
                self.assertNotIn(value.casefold(), text.casefold(), value)
        self.assertNotRegex(main, r"<(?:form|input|select|textarea|button)\b")
        self.assertNotRegex(page, r"\$\s*\d")
        self.assertNotRegex(page, r"\b(?:tax|vat)\s+(?:is|are)\s+included\b")

    def test_benefits_and_certificate_eligibility_are_precise(self):
        text = visible(source("en/pricing/index.html"))
        for value in (
            "One free 40-minute trial per learner",
            "Private one-to-one lessons",
            "Private family learning group",
            "Interactive quizzes where suitable",
            "Parent or adult-learner communication",
            "Teacher cancellation protection",
            "Additional 12-week benefits",
            "Access to 12 short Culture & Character mini-lessons supporting practical values, identity and everyday learning.",
            "Four late-cancellation make-up credits",
            "Extended access to additional quizzes and revision activities.",
            "Progress summary every four weeks",
            "Additional age-appropriate educational videos and learning resources.",
            "Digital certificate of completion for eligible 12-week-plan learners.",
            "At least 80% of scheduled paid classes must be completed.",
            "Any outstanding payment obligation must be resolved.",
            "The certificate acknowledges participation and completion.",
            "It is not an academic accreditation, qualification or government-recognised certificate.",
            "The 12 Culture & Character mini-lessons are supplementary short resources, not 12 additional private 40-minute classes and not the Afghan Culture & Islamic Ethics group program.",
            "Four late-cancellation make-up credits are not four additional ordinary classes.",
        ):
            self.assertIn(value, text)
        self.assertNotIn("VIP quiz access", text)
        self.assertNotIn("€50 value", text)

    def test_policy_summary_covers_validity_absences_payment_and_consumer_rights(self):
        text = visible(source("en/pricing/index.html"))
        for value in (
            "At least 24 hours’ notice",
            "Each affected class may be rescheduled once",
            "Less than 24 hours’ notice",
            "Four late-cancellation make-up credits are included across the entire 12-week plan",
            "Each make-up is subject to teacher availability and must occur before plan expiry.",
            "A no-show without communication is treated as a used class",
            "If Salaam Center or the teacher cancels, the class is rescheduled without using a learner class or make-up credit.",
            "A late arrival does not extend the scheduled end time or create a make-up entitlement.",
            "Teacher or Salaam Center technical failure is rescheduled",
            "The 4-week plan has six-week final validity from the first paid class",
            "The 12-week plan has sixteen-week final validity from the first paid class",
            "After the trial and schedule confirmation, families receive the plan and payment information before paid lessons begin.",
            "Consumer cancellation, refund and withdrawal rights apply where required by applicable law.",
            "Any service-specific refund information is communicated before payment.",
        ):
            self.assertIn(value, text)

    def test_faq_uses_native_disclosures_and_locked_answers(self):
        page = source("en/pricing/index.html")
        summaries = [visible(value) for value in re.findall(r"<summary>(.*?)</summary>", page, re.S)]
        self.assertEqual(11, len(summaries))
        for question in (
            "Which programs do these prices cover?",
            "Are the prices per learner?",
            "Can one plan be divided between Quran and Dari/Persian?",
            "How long is each lesson?",
            "Is the first session free?",
            "Does the plan renew automatically?",
            "Can a learner reschedule?",
            "What happens if the teacher cancels?",
            "Are Culture & Islamic Ethics classes included?",
            "Can I pay on the website?",
            "What refund and withdrawal rights apply?",
        ):
            self.assertIn(question, summaries)
        self.assertEqual(11, page.count("<details"))
        self.assertEqual(11, page.count("</details>"))
        self.assertIn("A separate plan is required for each program", visible(page))
        self.assertIn(
            "No. Salaam Center does not collect online payments on this website. Payment information is provided after the trial and schedule confirmation.",
            visible(page),
        )


class EnrolmentJourneyTests(unittest.TestCase):
    def test_home_has_one_concise_private_pricing_preview_before_protected_media(self):
        page = source("en/index.html")
        text = visible(page)
        preview_start = page.index('<section class="section pricing-preview"')
        teacher_start = page.index('<section class="section" aria-labelledby="teachers-title">')
        self.assertLess(preview_start, teacher_start)
        for value in (
            "Flexible plans for consistent learning",
            "Private Quran and Dari/Persian learners can choose a 4-week or 12-week plan",
            "From €49 for a 4-week plan",
            "40-minute private lessons",
            "Free first trial",
            "12-week plans include additional learning support",
            "View Plans and Pricing",
        ):
            self.assertIn(value, text)
        self.assertIn('href="/en/pricing/"', page)
        self.assertEqual(1, len(re.findall(r"€\s*\d+", text)))
        self.assertNotIn("Paid-plan details will be shared clearly before enrolment opens.", text)
        self.assertIn(
            "review the published plans after teacher and schedule availability are confirmed",
            text,
        )

    def test_program_pages_state_private_plan_scope_and_group_pricing_status(self):
        for relative in (
            "en/programs/quran/index.html",
            "en/programs/dari-persian/index.html",
        ):
            text = visible(source(relative))
            for value in (
                "1, 2 or 4 classes per week",
                "4-week and 12-week plans",
                "Every paid class is 40 minutes",
                "per learner and for one selected program",
                "The first 40-minute trial is free",
                "Compare Plans",
            ):
                self.assertIn(value, text, relative)
            self.assertIn('href="/en/pricing/"', source(relative), relative)

        culture_page = source("en/programs/afghan-culture-islamic-ethics/index.html")
        culture = visible(culture_page)
        self.assertIn(
            "Group pricing will be published when schedules and cohort arrangements are confirmed.",
            culture,
        )
        self.assertNotIn(
            "Pricing for Afghan Culture & Islamic Ethics group classes will be published when cohort schedules and group arrangements are confirmed.",
            culture,
        )
        self.assertIn("Private Quran and Dari/Persian plan pricing does not cover this group program.", culture)
        self.assertNotRegex(culture, r"€\s*\d")
        self.assertNotRegex(culture_page, r"<(?:form|input|select|textarea)\b")
        self.assertNotIn("waitlist", culture.casefold())

    def test_how_it_works_and_trial_page_define_the_non_submitting_path(self):
        process = visible(source("en/how-it-works/index.html"))
        steps = (
            "Explore the programs",
            "Attend a free 40-minute trial",
            "Receive an initial recommendation",
            "Confirm the teacher, schedule and plan",
            "Review payment information and begin learning",
        )
        positions = [process.index(value) for value in steps]
        self.assertEqual(sorted(positions), positions)
        for value in (
            "The plan is selected after teacher and schedule availability are confirmed.",
            "Payment is made before paid lessons begin.",
            "The website does not create an automatic online enrolment.",
            "Group enrolment follows a published cohort schedule when one becomes available.",
        ):
            self.assertIn(value, process)

        trial_page = source("en/book-trial/index.html")
        trial = visible(trial_page)
        for value in (
            "One free 40-minute trial is available per learner.",
            "No payment is required and there is no obligation to purchase a plan.",
            "A parent or guardian is the primary contact for a child or teenager.",
            "An adult woman learner may be the primary contact.",
            "Trial availability depends on teacher and schedule availability.",
            "What happens next?",
            "Trial and learning discussion",
            "Teacher and schedule availability confirmation",
            "Plan selection",
            "Review terms and payment information",
            "Paid classes begin",
            "Continue in WhatsApp",
            "prepared locally in your browser",
        ):
            self.assertIn(value, trial)
        self.assertIn('data-whatsapp-handoff="true"', trial_page)
        self.assertNotRegex(trial_page, r'<form\b[^>]+action=')

    def test_terms_privacy_and_success_are_truthful_production_surfaces(self):
        terms = visible(source("en/terms/index.html"))
        for value in (
            "Terms and Conditions",
            "Salaam Center",
            "Sabadell, Barcelona",
            "+34 614 401 172",
            "22 July 2026",
            "Prices are in EUR, per learner, for one selected program",
            "Every class is 40 minutes",
            "Plans are prepaid and do not renew automatically",
            "Paid lessons begin only after the plan, schedule, these Terms and payment are confirmed",
            "At least 24 hours’ notice",
            "Less than 24 hours’ notice",
            "up to four late-cancellation make-up credits",
            "A no-show is treated as a used class",
            "teacher or Salaam Center cancels",
            "six-week final validity",
            "sixteen-week final validity",
            "Consumer cancellation, refund and withdrawal rights apply where required by applicable law",
            "service-specific refund information is communicated before payment",
            "not an academic accreditation",
            "Progress summaries are provided every four weeks",
            "parent or guardian involvement and permission",
            "A WhatsApp message is an enquiry",
            "no payment obligation",
        ):
            self.assertIn(value, terms)
        self.assertNotRegex(terms, r"(?i)pre-?launch|not the final|\bpending\b|formspree")

        privacy_source = source("en/privacy-policy/index.html")
        self.assertEqual(
            3,
            privacy_source.count(
                "contact arrangements for learners under 18 and user-activated video content"
            ),
        )
        self.assertNotIn("minors' contact details", privacy_source)
        privacy = visible(privacy_source)
        self.assertIn("does not submit or store", privacy)
        self.assertIn("locally in your browser", privacy)
        self.assertIn("WhatsApp is a third-party service", privacy)
        self.assertIn("No online payment collection is active on this website.", privacy)
        self.assertIn("No analytics are used.", privacy)
        self.assertNotIn("Formspree", privacy)
        self.assertNotRegex(privacy, r"(?i)pre-?launch|not the final|\bpending\b")

        success = visible(source("en/success/index.html"))
        self.assertIn("Continue your conversation in WhatsApp", success)
        self.assertIn("cannot confirm", success)
        self.assertIn("not booked until Salaam Center confirms", success)

    def test_program_comparison_table_has_caption_and_keyboard_scroll_region(self):
        page = source("en/programs/index.html")
        self.assertIn('<div class="comparison-wrap" role="region" aria-labelledby="compare-title" tabindex="0">', page)
        self.assertIn("<caption>Compare Salaam Center launch programs</caption>", page)


class CommercialDocumentationTests(unittest.TestCase):
    def test_approved_facts_promote_exact_pricing_and_resolved_public_rules(self):
        facts = source("SALAM-CENTER-APPROVED-FACTS.md")
        self.assertIn("## 9. Approved production private-plan pricing", facts)
        self.assertIn("## Approved public commercial facts", facts)
        for (weeks, frequency), (classes, price, saving) in PLAN_EVIDENCE.items():
            self.assertIn(f"{frequency} class{'es' if frequency != 1 else ''} per week", facts)
            self.assertIn(f"{classes} paid classes", facts)
            self.assertIn(f"€{price} total", facts)
            if saving is not None:
                self.assertIn(f"Saves €{saving}", facts)
        for value in (
            "One free 40-minute trial per learner",
            "No automatic renewal",
            "6 weeks from the first paid class",
            "16 weeks from the first paid class",
            "At least 80% of scheduled paid classes",
            "Progress summary every four weeks",
            "Pricing for Afghan Culture & Islamic Ethics group classes will be published when cohort schedules and group arrangements are confirmed.",
            "## Internal operational status",
            "approved for production indexing",
            "Privacy Policy is approved",
            "Terms and Conditions are approved",
        ):
            self.assertIn(value, facts)
        self.assertNotIn("## 10. Unresolved pricing rules", facts)

    def test_operational_source_records_unit_economics_and_all_statuses(self):
        document = source("docs/COMMERCIAL-AND-ENROLMENT.md")
        self.assertIn("# Salaam Center Commercial and Enrolment", document)
        self.assertIn("## Internal-only unit economics", document)
        for key, expected in EFFECTIVE_REVENUE.items():
            classes, price, _ = PLAN_EVIDENCE[key]
            calculated = (
                Decimal(price) / Decimal(classes)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            self.assertEqual(Decimal(expected), calculated, key)
            self.assertIn(f"€{price} ÷ {classes} = €{expected} per paid class", document)
        for value in ("19.0%", "37.7%", "22.9%"):
            self.assertIn(value, document)
        self.assertIn("Teacher-compensation review", document)
        self.assertIn("resolved for current production pricing", document)
        self.assertIn("Final minimum net-margin policy", document)
        for status in (
            "Teacher-compensation review",
            "Gross-margin review",
            "Payment-provider selection",
            "Payment-provider fees",
            "Tax and accounting treatment",
            "Administrative cost",
            "Marketing and acquisition cost",
            "Refund and chargeback exposure",
            "Consumer-law review",
            "Future teacher-rate changes",
            "Legal-entity information",
            "Final Terms and Conditions",
            "Final Privacy Policy",
            "Contact mailbox",
            "Live form and backend",
            "Analytics",
            "Production SEO",
            "Deployment approval",
        ):
            self.assertIn(status, document)
        for approved in (
            "Final Terms and Conditions — approved",
            "Final Privacy Policy — approved",
            "Legal-entity information — approved",
            "Production SEO — indexing enabled",
            "Deployment approval — approved",
        ):
            self.assertIn(approved, document)

    def test_migration_and_scanner_docs_distinguish_new_approval_from_inherited_rules(self):
        migration = source("MIGRATION-SOURCE.md")
        self.assertIn("independently approved Salaam Center private-plan pricing", migration)
        self.assertIn("docs/COMMERCIAL-AND-ENROLMENT.md", migration)
        self.assertIn("inherited percentage badges and legal rules remain prohibited", migration)

        design = source("docs/superpowers/specs/2026-07-18-trust-evidence-regression-design.md")
        record = source("docs/superpowers/plans/2026-07-18-trust-evidence-regression.md")
        for document in (design, record):
            self.assertIn("eligible 12-week", document)
            self.assertIn("exact commercial", document)


if __name__ == "__main__":
    unittest.main()
