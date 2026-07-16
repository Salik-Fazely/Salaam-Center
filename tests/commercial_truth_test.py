import html
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PAGES = (
    "index.html",
    "pricing/index.html",
    "how-it-works/index.html",
    "terms/index.html",
    "about/index.html",
    "teachers/index.html",
)
COMMERCIAL_DOCS = tuple(
    path.relative_to(ROOT).as_posix()
    for path in sorted((ROOT / "docs").rglob("*.md"))
) + ("assets/Characters/character-usage-guide.txt",)


def visible_text(relative_path):
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    if relative_path.endswith(".html"):
        source = re.sub(r"<[^>]+>", " ", source)
        source = html.unescape(source)
    source = source.replace("’", "'")
    return re.sub(r"\s+", " ", source).strip().lower()


class StructureParser(HTMLParser):
    VOID_ELEMENTS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID_ELEMENTS:
            return
        if not self.stack:
            self.errors.append(f"unexpected closing </{tag}>")
            return
        expected = self.stack.pop()
        if expected != tag:
            self.errors.append(f"expected </{expected}>, found </{tag}>")

    def close(self):
        super().close()
        if self.stack:
            self.errors.append("unclosed tags: " + ", ".join(self.stack))


class CommercialTruthTests(unittest.TestCase):
    def assert_contains(self, relative_path, *phrases):
        text = visible_text(relative_path)
        for phrase in phrases:
            self.assertIn(phrase.lower(), text, f"{relative_path}: missing {phrase!r}")

    def test_package_arithmetic(self):
        packages = ((120, 6, 20.00), (220, 12, 18.33), (400, 25, 16.00))
        for price, lessons, expected_unit_price in packages:
            self.assertAlmostEqual(price / lessons, expected_unit_price, places=2)

    def test_stale_claims_are_absent_from_editable_scope(self):
        text = "\n".join(visible_text(path) for path in PUBLIC_PAGES + COMMERCIAL_DOCS)
        forbidden = {
            "old 5/10/20 lesson quantities": r"\b(?:5|10|20|five|ten|twenty)\s+(?:one-to-one\s+)?(?:qur'an\s+)?(?:lesson|lessons|session|sessions)\b",
            "old lesson durations": r"\b(?:30|thirty)(?:\s*(?:to|[-–—])\s*(?:45|forty-five))?[ -]?(?:minute|minutes)\b|\b(?:45|forty-five)[ -]?(?:minute|minutes)\b",
            "three make-up allowances": r"\b(?:3|three)\s+make[ -]?up",
            "old progress reporting": r"monthly.{0,40}progress|progress.{0,40}monthly|after (?:each|every) (?:lesson|session)|after[ -]?session notes?",
            "monthly cancellation terms": r"month[ -]?to[ -]?month|cancel anytime|monthly.{0,40}cancel|cancel.{0,40}monthly",
            "old response claims": r"working days?|business days?|within 48 hours",
            "direct teacher selection": r"choose (?:the|your own) teacher|teacher we chose",
            "unsupported public payment methods": r"stripe|card payments?|bank transfers?|payment link.{0,30}email|email.{0,30}payment link",
        }
        for label, pattern in forbidden.items():
            self.assertIsNone(re.search(pattern, text, re.IGNORECASE), label)

    def test_homepage_and_pricing_show_the_approved_packages(self):
        for path in ("index.html", "pricing/index.html"):
            self.assert_contains(
                path,
                "6 lessons · €20 per lesson",
                "12 lessons · approximately €18.33 per lesson",
                "25 lessons · €16 per lesson",
                "valid for one year from the purchase date",
                "40-minute",
            )

    def test_service_rules_are_present_on_public_pages(self):
        self.assert_contains(
            "how-it-works/index.html",
            "girls and boys aged 5 to 16",
            "normally contact families within two days to arrange the next steps",
            "40-minute",
            "every two months",
            "15-minute progress review",
            "visual progress report through whatsapp instead",
        )
        self.assert_contains(
            "pricing/index.html",
            "at least 24 hours' notice",
            "does not use a make-up allowance",
            "up to four make-up lessons",
            "always rescheduled",
            "subject to teacher and family availability",
            "payment instructions or a secure payment link",
            "through whatsapp",
            "at least 30 lessons",
            "identifiable learning stage",
            "teacher has confirmed",
        )
        self.assert_contains(
            "teachers/index.html",
            "parents may express a preference",
            "subject to availability",
            "request a teacher change",
            "every two months",
        )
        self.assert_contains(
            "terms/index.html",
            "children aged 5 to 16",
            "every paid lesson is 40 minutes",
            "valid for one year from the purchase date",
            "four make-up lessons",
            "payments are generally non-refundable once a package has started",
            "this policy does not affect any mandatory consumer rights that apply under eu law",
        )

    def test_progress_review_is_universal_and_initial_contact_language_is_scoped(self):
        fallback = "if a parent is unavailable or does not want a meeting"
        for path in PUBLIC_PAGES:
            self.assert_contains(path, fallback)
        for path in ("docs/START-HERE.md", "docs/decisions.md", "docs/project-brief.md"):
            self.assert_contains(path, fallback)

        for path in ("index.html", "pricing/index.html"):
            source = (ROOT / path).read_text(encoding="utf-8")
            match = re.search(
                r'<article class="price-card">\s*<p class="price-card__bundle">STARTER</p>.*?</article>',
                source,
                re.DOTALL,
            )
            self.assertIsNotNone(match, f"{path}: Starter card not found")
            starter_text = html.unescape(re.sub(r"<[^>]+>", " ", match.group()))
            self.assertIn("Progress review every two months", starter_text)

        how_source = (ROOT / "how-it-works/index.html").read_text(encoding="utf-8")
        matching_step = re.search(
            r'<h3 class="step-item__title">We match your teacher</h3>(.*?)</li>',
            how_source,
            re.DOTALL,
        )
        communication_block = re.search(
            r'<p class="editorial-block__eyebrow">OPEN COMMUNICATION</p>(.*?)</div>',
            how_source,
            re.DOTALL,
        )
        self.assertIsNotNone(matching_step, "initial matching step not found")
        self.assertIsNotNone(communication_block, "open communication block not found")
        matching_text = html.unescape(re.sub(r"<[^>]+>", " ", matching_step.group(1))).lower()
        communication_text = html.unescape(re.sub(r"<[^>]+>", " ", communication_block.group(1))).lower()
        self.assertIn("normally contact families within two days", matching_text)
        self.assertNotIn("respond on weekends", matching_text)
        self.assertNotIn("within two days", communication_text)
        self.assertNotIn("respond on weekends", communication_text)

    def test_policy_distinctions_and_exact_refund_wording(self):
        self.assert_contains(
            "terms/index.html",
            "6-lesson package has no make-up allowance",
            "unnotified or late-notice absence is counted as a used lesson",
            "allowances may be used even when the child misses a lesson without prior notice",
            "after all four allowances have been used",
            "they are not additional free lessons",
        )

        for path in ("index.html", "pricing/index.html", "how-it-works/index.html", "terms/index.html"):
            self.assert_contains(path, "paid lessons are scheduled after payment confirmation")

        refund = (
            "Payments are generally non-refundable once a package has started. "
            "Lessons already delivered, missed without the required notice, or cancelled late are not refundable. "
            "This policy does not affect any mandatory consumer rights that apply under EU law."
        )
        for path in ("pricing/index.html", "terms/index.html"):
            self.assert_contains(path, refund)

    def test_commercial_decisions_are_documented(self):
        self.assert_contains(
            "docs/decisions.md",
            "eur 120 / 6 lessons",
            "eur 220 / 12 lessons",
            "eur 400 / 25 lessons",
            "40 minutes",
            "one year from the purchase date",
            "within two days",
            "on-site payment system is not yet configured",
        )

    def test_trial_and_backend_accept_only_ages_5_to_16(self):
        expected_ages = [str(age) for age in range(5, 17)]

        trial_source = (ROOT / "book-trial/index.html").read_text(encoding="utf-8")
        age_select = re.search(
            r'<select id="child-age" name="child_age".*?</select>',
            trial_source,
            re.DOTALL,
        )
        self.assertIsNotNone(age_select, "book-trial age select not found")
        option_values = re.findall(r'<option value="([^"]*)"', age_select.group())
        self.assertEqual([""] + expected_ages, option_values)

        backend_source = (ROOT / "apps-script/Code.gs").read_text(encoding="utf-8")
        age_validation = re.search(
            r"child_age:\s*\[(.*?)\]\s*,\s*quran_level:",
            backend_source,
            re.DOTALL,
        )
        self.assertIsNotNone(age_validation, "Apps Script child_age validation not found")
        allowed_ages = re.findall(r"'([^']+)'", age_validation.group(1))
        self.assertEqual(expected_ages, allowed_ages)

    def test_success_page_uses_within_two_days_three_times(self):
        source = (ROOT / "success/index.html").read_text(encoding="utf-8").lower()
        self.assertNotRegex(source, r"working days?")
        self.assertEqual(3, source.count("within two days"))

    def test_edited_html_is_structurally_balanced(self):
        for relative_path in PUBLIC_PAGES:
            parser = StructureParser()
            parser.feed((ROOT / relative_path).read_text(encoding="utf-8"))
            parser.close()
            self.assertEqual([], parser.errors, f"{relative_path}: {parser.errors}")


if __name__ == "__main__":
    unittest.main()
