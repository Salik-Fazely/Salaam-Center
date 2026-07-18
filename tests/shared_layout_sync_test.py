import importlib.util
import re
import subprocess
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/sync_shared_layout.py"
HEADER = ROOT / "partials/header.html"
FOOTER = ROOT / "partials/footer.html"

EXPECTED_COMPLETE_PAGES = (
    "404.html",
    "index.html",
    "our-approach/index.html",
    "programs/index.html",
    "programs/quran/index.html",
    "programs/dari-persian/index.html",
    "programs/afghan-culture-islamic-ethics/index.html",
    "teachers/index.html",
    "how-it-works/index.html",
    "pricing/index.html",
    "about/index.html",
    "book-trial/index.html",
    "contact/index.html",
    "privacy-policy/index.html",
    "terms/index.html",
    "success/index.html",
)

ACTIVE_HREFS = {
    "home": "/",
    "our_approach": "/our-approach/",
    "programs": "/programs/",
    "teachers": "/teachers/",
    "how_it_works": "/how-it-works/",
    "pricing": "/pricing/",
    "about": "/about/",
}


def load_sync_module(script_path=SCRIPT):
    spec = importlib.util.spec_from_file_location("sync_shared_layout", script_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class NavParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_header = False
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set(attributes.get("class", "").split())
        if tag == "header" and "site-header" in classes:
            self.in_header = True
        elif self.in_header and tag == "a" and "nav__link" in classes:
            self.links.append(attributes)

    def handle_endtag(self, tag):
        if tag == "header":
            self.in_header = False


class SharedLayoutSyncTests(unittest.TestCase):
    def test_01_required_shared_layout_files_exist(self):
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(HEADER.is_file())
        self.assertTrue(FOOTER.is_file())

    def test_02_page_map_covers_the_sixteen_complete_pages(self):
        sync = load_sync_module()
        configured = tuple(config.path for config in sync.PAGE_CONFIGS)
        self.assertEqual(EXPECTED_COMPLETE_PAGES, configured)
        self.assertEqual(16, len(configured))

    def test_03_each_configured_page_has_exactly_one_marker_pair(self):
        sync = load_sync_module()
        for config in sync.PAGE_CONFIGS:
            page = (ROOT / config.path).read_text(encoding="utf-8")
            self.assertEqual(1, page.count(sync.HEADER_START), config.path)
            self.assertEqual(1, page.count(sync.HEADER_END), config.path)
            self.assertEqual(1, page.count(sync.FOOTER_START), config.path)
            self.assertEqual(1, page.count(sync.FOOTER_END), config.path)

    def test_04_check_mode_accepts_committed_generated_html(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--check"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("16 page(s)", result.stdout)

    def test_05_rendering_is_idempotent_in_memory(self):
        sync = load_sync_module()
        for config in sync.PAGE_CONFIGS:
            committed = sync.read_exact(ROOT / config.path)
            self.assertEqual(committed, sync.expected_page(ROOT, config), config.path)

    def test_06_only_the_matching_primary_navigation_link_is_current(self):
        sync = load_sync_module()
        current_page_paths = {
            "home": "index.html",
            "our_approach": "our-approach/index.html",
            "programs": "programs/index.html",
            "teachers": "teachers/index.html",
            "how_it_works": "how-it-works/index.html",
            "pricing": "pricing/index.html",
            "about": "about/index.html",
        }
        for config in sync.PAGE_CONFIGS:
            parser = NavParser()
            parser.feed((ROOT / config.path).read_text(encoding="utf-8"))
            current = [
                link.get("href")
                for link in parser.links
                if link.get("aria-current") == "page" and "is-active" in link.get("class", "").split()
            ]
            expected = (
                ACTIVE_HREFS.get(config.active_nav)
                if current_page_paths.get(config.active_nav) == config.path
                else None
            )
            self.assertEqual([expected] if expected else [], current, config.path)

            active = [
                link.get("href")
                for link in parser.links
                if "is-active" in link.get("class", "").split()
            ]
            active_expected = ACTIVE_HREFS.get(config.active_nav)
            self.assertEqual([active_expected] if active_expected else [], active, config.path)

    def test_07_generated_pages_have_no_unresolved_placeholders(self):
        placeholder = re.compile(r"{{[^{}]+}}")
        for relative in EXPECTED_COMPLETE_PAGES:
            self.assertIsNone(placeholder.search((ROOT / relative).read_text(encoding="utf-8")), relative)

    def test_08_shared_header_contains_the_approved_navigation_contract(self):
        header = HEADER.read_text(encoding="utf-8")
        for label, href in (
            ("Home", "/"),
            ("Our Approach", "/our-approach/"),
            ("Programs", "/programs/"),
            ("Teachers", "/teachers/"),
            ("How It Works", "/how-it-works/"),
            ("Pricing", "/pricing/"),
            ("About", "/about/"),
            ("Book a Free Trial", "/book-trial/"),
        ):
            self.assertIn(f'href="{href}"', header, label)
            self.assertIn(label, header)
        self.assertLess(header.index("How It Works"), header.index("Pricing"))
        self.assertLess(header.index("Pricing"), header.index("About"))

    def test_09_shared_footer_has_the_single_approved_contact_destination(self):
        footer = FOOTER.read_text(encoding="utf-8")
        self.assertIn('href="mailto:hello@salaam.center"', footer)
        self.assertIn('href="/contact/"', footer)
        self.assertIn('href="/pricing/"', footer)
        self.assertIn("Pricing", footer)
        self.assertEqual(1, footer.count("mailto:"))
        for value in ("tel:", "wa.me/", "http://", "https://"):
            self.assertNotIn(value, footer)

    def test_10_shared_sections_have_no_trailing_whitespace(self):
        sync = load_sync_module()
        for relative in EXPECTED_COMPLETE_PAGES:
            page = (ROOT / relative).read_text(encoding="utf-8")
            for start, end in ((sync.HEADER_START, sync.HEADER_END), (sync.FOOTER_START, sync.FOOTER_END)):
                section = page.split(start, 1)[1].split(end, 1)[0]
                for line in section.splitlines()[1:-1]:
                    self.assertEqual(line.rstrip(" \t"), line, relative)


if __name__ == "__main__":
    unittest.main()
