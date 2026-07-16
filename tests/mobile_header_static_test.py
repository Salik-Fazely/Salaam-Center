import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def header_pages():
    return tuple(
        path
        for path in sorted(ROOT.rglob("*.html"))
        if "<!-- SHARED HEADER:START -->" in path.read_text(encoding="utf-8")
    )


class HeaderParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.header_depth = 0
        self.menu_attrs = []
        self.toggle_attrs = []
        self.ctas = []
        self.current_cta = None
        self.current_label = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set(attributes.get("class", "").split())

        if tag == "header" and "site-header" in classes:
            self.header_depth = 1
            return

        if not self.header_depth:
            return

        if tag == "header":
            self.header_depth += 1

        if tag == "ul" and attributes.get("id") == "nav-menu":
            self.menu_attrs.append(attributes)
        elif attributes.get("id") == "nav-toggle":
            self.toggle_attrs.append((tag, attributes))
        elif tag == "a" and "nav__cta" in classes:
            self.current_cta = {"attrs": attributes, "labels": {}, "text": []}
            self.ctas.append(self.current_cta)
        elif self.current_cta is not None and tag == "span":
            for class_name in classes:
                if class_name.startswith("nav__cta-label--"):
                    self.current_cta["labels"][class_name] = []
                    self.current_label = class_name

    def handle_data(self, data):
        if self.current_cta is None:
            return

        self.current_cta["text"].append(data)
        if self.current_label is not None:
            self.current_cta["labels"][self.current_label].append(data)

    def handle_endtag(self, tag):
        if not self.header_depth:
            return

        if tag == "a" and self.current_cta is not None:
            self.current_cta = None
            self.current_label = None
        elif tag == "span":
            self.current_label = None
        elif tag == "header":
            self.header_depth -= 1


def parse_header(path):
    parser = HeaderParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def normalized_text(parts):
    return " ".join("".join(parts).split())


class MobileHeaderStaticTests(unittest.TestCase):
    def test_canonical_headers_reuse_one_booking_cta_contract(self):
        pages = header_pages()
        self.assertEqual(16, len(pages))

        for page in pages:
            relative = page.relative_to(ROOT)
            parser = parse_header(page)
            self.assertEqual(1, len(parser.ctas), relative)

            cta = parser.ctas[0]
            self.assertEqual("/book-trial/", cta["attrs"].get("href"), relative)
            self.assertEqual("Book a free trial", cta["attrs"].get("aria-label"), relative)
            self.assertEqual(
                "Book a Free Trial",
                normalized_text(cta["labels"].get("nav__cta-label--full", [])),
                relative,
            )
            self.assertEqual(
                "Free trial",
                normalized_text(cta["labels"].get("nav__cta-label--short", [])),
                relative,
            )

    def test_canonical_headers_use_the_accessible_menu_trigger_contract(self):
        for page in header_pages():
            relative = page.relative_to(ROOT)
            parser = parse_header(page)
            self.assertEqual([{"id": "nav-menu", "class": "nav__links", "role": "list"}], parser.menu_attrs, relative)
            self.assertEqual(1, len(parser.toggle_attrs), relative)

            tag, attributes = parser.toggle_attrs[0]
            self.assertEqual("button", tag, relative)
            self.assertEqual("nav-menu", attributes.get("aria-controls"), relative)
            self.assertEqual("false", attributes.get("aria-expanded"), relative)
            self.assertEqual("Open navigation menu", attributes.get("aria-label"), relative)

    def test_mobile_css_keeps_cta_and_menu_button_visible_with_44px_targets(self):
        source = (ROOT / "assets/css/styles.css").read_text(encoding="utf-8")
        mobile_header = re.search(
            r"@media \(max-width: 767px\) \{(?P<body>.*?)\n\}",
            source,
            re.DOTALL,
        )
        self.assertIsNotNone(mobile_header)
        body = mobile_header.group("body")

        self.assertRegex(body, r"\.nav__cta\s*\{[^}]*display:\s*inline-flex;")
        self.assertRegex(body, r"\.nav__cta\s*\{[^}]*min-height:\s*44px;")
        self.assertRegex(body, r"\.nav__toggle\s*\{[^}]*width:\s*44px;[^}]*height:\s*44px;")
        self.assertIn(".nav__cta-label--short", source)
        self.assertRegex(
            source,
            r"@media \(max-width: 359px\) \{[^}]*\.nav__cta-label--full",
        )


if __name__ == "__main__":
    unittest.main()
