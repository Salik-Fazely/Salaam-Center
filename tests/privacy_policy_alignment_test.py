import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "privacy-policy/index.html"


class PolicyParser(HTMLParser):
    VOID_ELEMENTS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.duplicate_ids = set()
        self.links = []
        self.table_captions = 0
        self.column_headers = 0
        self.open_elements = []
        self.structure_errors = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            if attributes["id"] in self.ids:
                self.duplicate_ids.add(attributes["id"])
            self.ids.add(attributes["id"])
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])
        if tag == "caption":
            self.table_captions += 1
        if tag == "th" and attributes.get("scope") == "col":
            self.column_headers += 1
        if tag not in self.VOID_ELEMENTS:
            self.open_elements.append(tag)

    def handle_endtag(self, tag):
        if not self.open_elements or self.open_elements[-1] != tag:
            actual = self.open_elements[-1] if self.open_elements else "nothing"
            self.structure_errors.append(f"closed {tag} while {actual} was open")
            return
        self.open_elements.pop()

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID_ELEMENTS:
            self.handle_endtag(tag)


class PrivacyPolicyAlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = POLICY.read_text(encoding="utf-8")
        cls.text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cls.source)).strip()
        cls.parser = PolicyParser()
        cls.parser.feed(cls.source)

    def test_date_and_optional_consent_behavior_are_disclosed(self):
        for wording in (
            "Last updated: 14 July 2026",
            "Analytics and cookie choices",
            "Google Analytics 4",
            "Accept analytics",
            "not loaded or contacted",
            "legal basis for optional analytics is your consent",
            "website, lesson information, booking form, or any Tarteel House service",
            "tarteelhouse.analyticsConsent",
            "browser local storage",
            "12 months",
            "not an advertising profile",
            "Cookie settings",
            "applies going forward",
            "attempts to remove first-party Google Analytics cookies",
            "reloads the page",
        ):
            self.assertIn(wording, self.text)

    def test_ga4_collection_and_provider_disclosures_are_present(self):
        for wording in (
            "page visits and page paths",
            "user and session statistics",
            "approximate geographic location",
            "browser, operating-system, and device information",
            "referral information",
            "website interaction events",
            "Google is our analytics provider",
            "servers outside your country",
        ):
            self.assertIn(wording, self.text)
        self.assertNotIn("exact GPS", self.text)

    def test_custom_events_and_only_their_approved_parameters_are_disclosed(self):
        expected = {
            "trial_cta_click": ("source_path", "destination_path", "cta_text"),
            "trial_form_start": ("source_path", "form_id"),
            "trial_form_submit_attempt": ("source_path", "form_id"),
        }
        for event, parameters in expected.items():
            self.assertIn(event, self.text)
            for parameter in parameters:
                self.assertRegex(
                    self.text,
                    rf"{event}.{{0,500}}{parameter}",
                    f"{event} does not describe {parameter}",
                )
        self.assertIn("valid client-side submission attempt", self.text)
        self.assertIn("does not prove that a booking was confirmed or received by our backend", self.text)

    def test_booking_form_values_are_explicitly_excluded_from_ga4(self):
        self.assertIn("We do not intentionally send Google Analytics", self.text)
        for value in (
            "parent or child names",
            "email addresses",
            "telephone or WhatsApp numbers",
            "ages",
            "city",
            "selected lesson language",
            "learning level",
            "preferred schedule",
            "notes",
            "any booking-form field value",
        ):
            self.assertIn(value, self.text)

    def test_storage_table_is_accessible_and_complete(self):
        self.assertEqual([], self.parser.structure_errors)
        self.assertEqual([], self.parser.open_elements)
        self.assertEqual(set(), self.parser.duplicate_ids)
        self.assertEqual(1, self.parser.table_captions)
        self.assertEqual(6, self.parser.column_headers)
        for name in ("tarteelhouse.analyticsConsent", "_ga", "_ga_&lt;container-id&gt;"):
            self.assertIn(name, self.source)
        for wording in (
            "Browser local storage",
            "First-party analytics cookie",
            "Remembers whether analytics was accepted or rejected",
            "Distinguishes users",
            "Persists session state",
            "Up to 2 years, subject to browser restrictions and Google Analytics configuration",
            "Only after analytics is accepted",
            "Google Analytics configuration changes",
        ):
            self.assertIn(wording, self.text)

    def test_policy_links_and_page_anchors_resolve(self):
        required_external = {
            "https://policies.google.com/privacy",
            "https://policies.google.com/privacy/frameworks",
        }
        self.assertTrue(required_external.issubset(self.parser.links))

        missing = []
        for href in self.parser.links:
            parsed = urlsplit(href)
            if parsed.scheme in ("http", "https", "mailto", "tel"):
                continue
            if href.startswith("#"):
                if href[1:] not in self.parser.ids:
                    missing.append(href)
                continue
            path = parsed.path
            target = ROOT / "index.html" if path == "/" else ROOT / path.lstrip("/")
            if path != "/" and path.endswith("/"):
                target /= "index.html"
            if not target.exists():
                missing.append(href)
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
