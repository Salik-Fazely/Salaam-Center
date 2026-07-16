import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
CONSENT_SCRIPT = '<script src="/assets/js/consent.js"></script>'
GA_PATTERNS = (
    "googletagmanager.com",
    "google-analytics.com",
    "G-ZVLW7QGYR1",
    "gtag(",
)


def public_pages():
    return tuple(
        path
        for path in sorted(ROOT.rglob("*.html"))
        if "<!-- SHARED FOOTER:START -->" in path.read_text(encoding="utf-8")
    )


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])


class ConsentStaticTests(unittest.TestCase):
    def test_all_public_pages_use_the_shared_consent_module(self):
        pages = public_pages()
        self.assertEqual(16, len(pages))

        for page in pages:
            source = page.read_text(encoding="utf-8")
            relative = page.relative_to(ROOT)
            self.assertEqual(1, source.count(CONSENT_SCRIPT), relative)
            self.assertLess(source.index(CONSENT_SCRIPT), source.index('<script src="/assets/js/main.js"></script>'), relative)

    def test_no_html_contains_an_unconditional_ga_loader(self):
        for page in ROOT.rglob("*.html"):
            source = page.read_text(encoding="utf-8")
            for pattern in GA_PATTERNS:
                self.assertNotIn(pattern, source, f"{page.relative_to(ROOT)} contains {pattern}")

    def test_banner_copy_and_semantic_controls_are_centralized(self):
        source = (ROOT / "assets/js/consent.js").read_text(encoding="utf-8")
        for copy in (
            "Your privacy choices",
            "We use optional analytics cookies to understand how visitors use our website and improve Tarteel House. You can accept or reject analytics. Your choice can be changed at any time.",
            "Accept analytics",
            "Reject analytics",
            "Privacy Policy",
            "Cookie settings",
        ):
            self.assertIn(copy, source)
        self.assertEqual(3, len(re.findall(r"makeElement\(doc, ['\"]button['\"]", source)))

    def test_consent_choice_focus_does_not_scroll_the_page(self):
        source = (ROOT / "assets/js/consent.js").read_text(encoding="utf-8")

        self.assertEqual(2, source.count("ui.settings.focus({ preventScroll: true });"))
        self.assertNotIn("ui.settings.focus();", source)

    def test_existing_local_links_resolve(self):
        missing = []
        for page in public_pages():
            parser = LinkParser()
            parser.feed(page.read_text(encoding="utf-8"))
            for href in parser.links:
                parsed = urlsplit(href)
                if parsed.scheme or href.startswith(("#", "mailto:", "tel:")):
                    continue
                path = parsed.path
                if not path or path == "/":
                    target = ROOT / "index.html"
                elif path.startswith("/"):
                    target = ROOT / path.lstrip("/")
                else:
                    target = page.parent / path
                if path != "/" and path.endswith("/"):
                    target /= "index.html"
                if not target.exists():
                    missing.append(f"{page.relative_to(ROOT)} -> {href}")
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
