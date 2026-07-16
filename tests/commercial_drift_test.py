import html
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PAGES = tuple(sorted(ROOT.rglob("index.html")))
PRICING_PAGES = (ROOT / "index.html", ROOT / "pricing/index.html")

OBSOLETE_PATTERNS = {
    "5-session package wording": r"\b(?:5|five)\s*(?:-| )\s*(?:lesson|session)s?\b",
    "10-session package wording": r"\b(?:10|ten)\s*(?:-| )\s*(?:lesson|session)s?\b",
    "20-session package wording": r"\b(?:20|twenty)\s*(?:-| )\s*(?:lesson|session)s?\b",
    "three make-up lessons": r"\b(?:3|three)\s+make[- ]?up\s+lessons?\b",
    "30-minute paid lessons": (
        r"\bpaid\s+(?:lesson|session)s?\b.{0,50}\b(?:30|thirty)[ -]?minutes?\b"
        r"|\b(?:30|thirty)[ -]?minute\s+paid\s+(?:lesson|session)s?\b"
    ),
    "month-to-month packages": r"\bmonth[- ]to[- ]month\b",
}


def normalize(value):
    value = html.unescape(value).translate(
        str.maketrans({"\u00a0": " ", "’": "'", "–": "-", "—": "-"})
    )
    return re.sub(r"\s+", " ", value).strip().lower()


class VisibleTextParser(HTMLParser):
    IGNORED_ELEMENTS = {"script", "style", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ignored_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.IGNORED_ELEMENTS:
            self.ignored_depth += 1

    def handle_endtag(self, tag):
        if tag in self.IGNORED_ELEMENTS and self.ignored_depth:
            self.ignored_depth -= 1

    def handle_data(self, data):
        if not self.ignored_depth:
            self.parts.append(data)


def page_content(path):
    source = path.read_text(encoding="utf-8")
    parser = VisibleTextParser()
    parser.feed(source)
    parser.close()
    return normalize(" ".join(parser.parts)), normalize(source)


class CommercialDriftTests(unittest.TestCase):
    def test_complete_public_pages_exclude_obsolete_commercial_claims(self):
        self.assertTrue(PUBLIC_PAGES, "No complete public pages were discovered")

        for page in PUBLIC_PAGES:
            relative_path = page.relative_to(ROOT).as_posix()
            visible_text, normalized_source = page_content(page)

            for label, pattern in OBSOLETE_PATTERNS.items():
                with self.subTest(page=relative_path, claim=label):
                    self.assertIsNone(re.search(pattern, visible_text), label)

            for claim in ("21+ Students", "100% Trusted by Families"):
                with self.subTest(page=relative_path, claim=claim):
                    self.assertNotIn(normalize(claim), visible_text)

            self.assertNotIn(
                "gtcrak_mojc",
                normalized_source,
                f"{relative_path}: obsolete Sadiah video ID",
            )

    def test_obsolete_patterns_recognize_representative_stale_copy(self):
        examples = {
            "5-session package wording": "Choose the 5-session package.",
            "10-session package wording": "Choose the ten lesson package.",
            "20-session package wording": "Choose the 20 lessons package.",
            "three make-up lessons": "Includes three make-up lessons.",
            "30-minute paid lessons": "Paid lessons are 30 minutes.",
            "month-to-month packages": "Current packages run month-to-month.",
        }

        for label, example in examples.items():
            with self.subTest(claim=label):
                self.assertRegex(normalize(example), OBSOLETE_PATTERNS[label])

    def test_primary_pricing_pages_contain_current_packages(self):
        for page in PRICING_PAGES:
            visible_text, _ = page_content(page)
            relative_path = page.relative_to(ROOT).as_posix()

            for lessons, price in ((6, 120), (12, 220), (25, 400)):
                pattern = (
                    rf"(?:€\s*{price}.{{0,120}}\b{lessons}\s+lessons\b"
                    rf"|\b{lessons}\s+lessons\b.{{0,120}}€\s*{price})"
                )
                with self.subTest(page=relative_path, package=lessons):
                    self.assertRegex(visible_text, pattern)


if __name__ == "__main__":
    unittest.main()
