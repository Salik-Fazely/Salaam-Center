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
HEADER_FA = ROOT / "partials/header.fa-AF.html"
FOOTER_FA = ROOT / "partials/footer.fa-AF.html"

ROOT_COMPLETE_PAGES = (
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
    "404.html",
)
EXPECTED_COMPLETE_PAGES = tuple(
    localized
    for root_page in ROOT_COMPLETE_PAGES
    for localized in (root_page, f"en/{root_page}")
)

ACTIVE_HREFS = {
    "home": "/",
    "our-approach": "/our-approach/",
    "programs": "/programs/",
    "teachers": "/teachers/",
    "how-it-works": "/how-it-works/",
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
        for required in (SCRIPT, HEADER, FOOTER, HEADER_FA, FOOTER_FA):
            self.assertTrue(required.is_file(), required)

    def test_02_page_map_covers_all_thirty_two_localized_pages(self):
        sync = load_sync_module()
        configured = tuple(config.path for config in sync.page_configs(ROOT))
        self.assertEqual(EXPECTED_COMPLETE_PAGES, configured)
        self.assertEqual(32, len(configured))

    def test_03_each_configured_page_has_exactly_one_marker_pair(self):
        sync = load_sync_module()
        for config in sync.page_configs(ROOT):
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
        self.assertIn("32 page(s)", result.stdout)

    def test_05_rendering_is_idempotent_in_memory(self):
        sync = load_sync_module()
        for config in sync.page_configs(ROOT):
            committed = sync.read_exact(ROOT / config.path)
            self.assertEqual(committed, sync.expected_page(ROOT, config), config.path)

    def test_06_only_the_matching_primary_navigation_link_is_current(self):
        sync = load_sync_module()
        for config in sync.page_configs(ROOT):
            parser = NavParser()
            parser.feed((ROOT / config.path).read_text(encoding="utf-8"))
            current = [
                link.get("href")
                for link in parser.links
                if link.get("aria-current") == "page" and "is-active" in link.get("class", "").split()
            ]
            base_href = ACTIVE_HREFS.get(config.active_nav)
            active_href = (
                f"/en{base_href}"
                if base_href and config.language == "en"
                else base_href
            )
            expected = active_href if config.route_id == config.active_nav else None
            self.assertEqual([expected] if expected else [], current, config.path)

            active = [
                link.get("href")
                for link in parser.links
                if "is-active" in link.get("class", "").split()
            ]
            self.assertEqual([active_href] if active_href else [], active, config.path)

    def test_07_generated_pages_have_no_unresolved_placeholders(self):
        placeholder = re.compile(r"{{[^{}]+}}")
        for relative in EXPECTED_COMPLETE_PAGES:
            self.assertIsNone(placeholder.search((ROOT / relative).read_text(encoding="utf-8")), relative)

    def test_08_shared_headers_contain_the_localized_navigation_contracts(self):
        english = HEADER.read_text(encoding="utf-8")
        for label, href in (
            ("Home", "/en/"),
            ("Our Approach", "/en/our-approach/"),
            ("Programs", "/en/programs/"),
            ("Teachers", "/en/teachers/"),
            ("How It Works", "/en/how-it-works/"),
            ("Pricing", "/en/pricing/"),
            ("About", "/en/about/"),
            ("Book a Free Trial", "/en/book-trial/"),
        ):
            self.assertIn(f'href="{href}"', english, label)
            self.assertIn(label, english)
        self.assertLess(english.index("How It Works"), english.index("Pricing"))
        self.assertLess(english.index("Pricing"), english.index("About"))

        dari = HEADER_FA.read_text(encoding="utf-8")
        for href in (
            "/",
            "/our-approach/",
            "/programs/",
            "/teachers/",
            "/how-it-works/",
            "/pricing/",
            "/about/",
            "/book-trial/",
        ):
            self.assertIn(f'href="{href}"', dari)
        self.assertIn('lang="en" dir="ltr">English</a>', dari)

    def test_09_shared_footers_have_the_single_approved_contact_destination(self):
        for footer_path, prefix in ((FOOTER_FA, ""), (FOOTER, "/en")):
            footer = footer_path.read_text(encoding="utf-8")
            self.assertIn('href="https://wa.me/34614401172"', footer)
            self.assertIn('target="_blank"', footer)
            self.assertIn('rel="noopener noreferrer"', footer)
            self.assertIn(f'href="{prefix}/contact/"', footer)
            self.assertIn(f'href="{prefix}/pricing/"', footer)
            self.assertEqual(1, footer.count("https://wa.me/34614401172"))
            for value in ("mailto:", "tel:", "api.whatsapp.com"):
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
