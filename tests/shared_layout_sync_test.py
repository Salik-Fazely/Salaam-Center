import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/sync_shared_layout.py"
HEADER_PARTIAL = ROOT / "partials/header.html"
FOOTER_PARTIAL = ROOT / "partials/footer.html"

EXPECTED_COMPLETE_PAGES = (
    "404.html",
    "index.html",
    "about/index.html",
    "blog/index.html",
    "blog/free-online-quran-trial-lesson-parent-checklist/index.html",
    "blog/help-children-memorize-short-surahs/index.html",
    "blog/how-parents-can-track-their-childs-quran-progress/index.html",
    "blog/one-to-one-quran-classes-vs-group-classes-for-children/index.html",
    "blog/online-quran-classes-for-kids-parents-look-for/index.html",
    "book-trial/index.html",
    "how-it-works/index.html",
    "pricing/index.html",
    "privacy-policy/index.html",
    "success/index.html",
    "teachers/index.html",
    "terms/index.html",
)

REDIRECT_STUBS = (
    "about.html",
    "blog.html",
    "book-trial.html",
    "how-it-works.html",
    "pricing.html",
    "privacy-policy.html",
    "privacy.html",
    "success.html",
    "teachers.html",
    "terms.html",
)

ARTICLE_IMAGES = {
    "blog/free-online-quran-trial-lesson-parent-checklist/index.html": (
        "https://www.tarteelhouse.com/assets/blog/free-online-quran-trial-lesson-cover.png"
    ),
    "blog/help-children-memorize-short-surahs/index.html": (
        "https://www.tarteelhouse.com/assets/blog/help-children-memorize-short-surahs.png"
    ),
    "blog/how-parents-can-track-their-childs-quran-progress/index.html": (
        "https://www.tarteelhouse.com/assets/blog/track-child-quran-progress.png"
    ),
    "blog/one-to-one-quran-classes-vs-group-classes-for-children/index.html": (
        "https://www.tarteelhouse.com/assets/blog/one-to-one-vs-group-quran-classes.png"
    ),
    "blog/online-quran-classes-for-kids-parents-look-for/index.html": (
        "https://www.tarteelhouse.com/assets/blog/online-quran-classes-for-kids-parents-look-for.png"
    ),
}

CORE_METADATA = {
    "index.html": (
        "Online Quran Classes for Kids | Tarteel House",
        "https://www.tarteelhouse.com/",
    ),
    "about/index.html": (
        "About Tarteel House | Online Quran Learning for Kids",
        "https://www.tarteelhouse.com/about/",
    ),
    "book-trial/index.html": (
        "Book a Free Quran Trial Class | Tarteel House",
        "https://www.tarteelhouse.com/book-trial/",
    ),
    "pricing/index.html": (
        "Quran Classes Pricing for Kids | Tarteel House",
        "https://www.tarteelhouse.com/pricing/",
    ),
    "teachers/index.html": (
        "Online Female Quran Teachers for Kids | Tarteel House",
        "https://www.tarteelhouse.com/teachers/",
    ),
}

ACTIVE_HREFS = {
    "how_it_works": "/how-it-works/",
    "teachers": "/teachers/",
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


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_header = False
        self.in_head = False
        self.capture_title = False
        self.title_parts = []
        self.nav_links = []
        self.meta = []
        self.canonicals = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set(attributes.get("class", "").split())
        if tag == "head":
            self.in_head = True
        elif tag == "header" and "site-header" in classes:
            self.in_header = True
        elif self.in_header and tag == "a" and "nav__link" in classes:
            self.nav_links.append(attributes)

        if self.in_head and tag == "title":
            self.capture_title = True
        elif self.in_head and tag == "meta":
            self.meta.append(attributes)
        elif self.in_head and tag == "link" and "canonical" in attributes.get("rel", "").split():
            self.canonicals.append(attributes.get("href"))

    def handle_endtag(self, tag):
        if tag == "header":
            self.in_header = False
        elif tag == "head":
            self.in_head = False
        elif tag == "title":
            self.capture_title = False

    def handle_data(self, data):
        if self.capture_title:
            self.title_parts.append(data)

    @property
    def title(self):
        return " ".join("".join(self.title_parts).split())

    def meta_content(self, attribute, value):
        return [item.get("content") for item in self.meta if item.get(attribute) == value]


def parse_page(relative_path, root=ROOT):
    parser = PageParser()
    parser.feed((root / relative_path).read_text(encoding="utf-8"))
    parser.close()
    return parser


class SharedLayoutSyncTests(unittest.TestCase):
    def test_01_required_shared_layout_files_exist(self):
        self.assertTrue(HEADER_PARTIAL.is_file())
        self.assertTrue(FOOTER_PARTIAL.is_file())
        self.assertTrue(SCRIPT.is_file())

    def test_02_page_map_covers_complete_pages_and_each_has_one_marker_pair(self):
        sync = load_sync_module()
        configured = tuple(config.path for config in sync.PAGE_CONFIGS)
        self.assertEqual(EXPECTED_COMPLETE_PAGES, configured)

        for config in sync.PAGE_CONFIGS:
            source = (ROOT / config.path).read_text(encoding="utf-8")
            if config.sync_header:
                self.assertEqual(1, source.count(sync.HEADER_START), config.path)
                self.assertEqual(1, source.count(sync.HEADER_END), config.path)
            if config.sync_footer:
                self.assertEqual(1, source.count(sync.FOOTER_START), config.path)
                self.assertEqual(1, source.count(sync.FOOTER_END), config.path)

    def test_03_check_mode_accepts_committed_generated_html(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--check"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_04_write_mode_is_idempotent_in_an_isolated_copy(self):
        sync = load_sync_module()
        with tempfile.TemporaryDirectory() as directory:
            isolated_root = Path(directory)
            paths_to_copy = {
                Path("scripts/sync_shared_layout.py"),
                *(Path(path) for path in sync.HEADER_FRAGMENTS.values()),
                *(Path(path) for path in sync.FOOTER_FRAGMENTS.values()),
                *(Path(config.path) for config in sync.PAGE_CONFIGS),
            }
            for relative_path in paths_to_copy:
                destination = isolated_root / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative_path, destination)

            drifted_page = isolated_root / "about/index.html"
            drifted_source = drifted_page.read_text(encoding="utf-8")
            drifted_source = drifted_source.replace(
                'aria-label="Main navigation"',
                'aria-label="Drifted navigation"',
                1,
            )
            drifted_page.write_text(drifted_source, encoding="utf-8", newline="")

            command = [
                sys.executable,
                str(isolated_root / "scripts/sync_shared_layout.py"),
                "--write",
            ]
            first = subprocess.run(
                command,
                cwd=isolated_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            after_first = {
                config.path: (isolated_root / config.path).read_bytes()
                for config in sync.PAGE_CONFIGS
            }

            second = subprocess.run(
                command,
                cwd=isolated_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            after_second = {
                config.path: (isolated_root / config.path).read_bytes()
                for config in sync.PAGE_CONFIGS
            }
            self.assertEqual(after_first, after_second)

    def test_05_generated_pages_have_no_unresolved_placeholders(self):
        sync = load_sync_module()
        placeholder = re.compile(r"{{[^{}]+}}")
        for config in sync.PAGE_CONFIGS:
            source = (ROOT / config.path).read_text(encoding="utf-8")
            self.assertIsNone(placeholder.search(source), config.path)

    def test_06_redirect_stubs_are_not_synchronized(self):
        sync = load_sync_module()
        configured = {config.path for config in sync.PAGE_CONFIGS}
        for relative_path in REDIRECT_STUBS:
            self.assertNotIn(relative_path, configured)
            source = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertNotIn(sync.HEADER_START, source, relative_path)
            self.assertNotIn(sync.FOOTER_START, source, relative_path)

    def test_07_only_the_matching_navigation_link_is_current(self):
        sync = load_sync_module()
        for config in sync.PAGE_CONFIGS:
            page = parse_page(config.path)
            expected_href = ACTIVE_HREFS.get(config.active_nav)
            current_links = []
            for link in page.nav_links:
                classes = set(link.get("class", "").split())
                is_current = link.get("aria-current") == "page"
                is_active = "is-active" in classes
                self.assertEqual(is_current, is_active, config.path)
                if is_current:
                    current_links.append(link.get("href"))
            self.assertEqual(
                [expected_href] if expected_href else [],
                current_links,
                config.path,
            )

    def test_08_core_metadata_and_indexing_status_are_preserved(self):
        for relative_path, (title, canonical) in CORE_METADATA.items():
            page = parse_page(relative_path)
            self.assertEqual(title, page.title, relative_path)
            self.assertEqual([canonical], page.canonicals, relative_path)

        not_found = parse_page("404.html")
        success = parse_page("success/index.html")
        self.assertEqual(["noindex, follow"], not_found.meta_content("name", "robots"))
        self.assertEqual(["noindex, follow"], success.meta_content("name", "robots"))

    def test_09_blog_articles_keep_their_specific_social_images(self):
        for relative_path, expected_image in ARTICLE_IMAGES.items():
            page = parse_page(relative_path)
            self.assertEqual(
                [expected_image],
                page.meta_content("property", "og:image"),
                relative_path,
            )
            self.assertEqual(
                [expected_image],
                page.meta_content("name", "twitter:image"),
                relative_path,
            )

    def test_10_standard_footer_keeps_the_official_whatsapp_url(self):
        footer = FOOTER_PARTIAL.read_text(encoding="utf-8")
        self.assertIn('href="https://wa.me/34614494311"', footer)

    def test_11_generated_shared_sections_have_no_trailing_whitespace(self):
        sync = load_sync_module()
        for config in sync.PAGE_CONFIGS:
            source = (ROOT / config.path).read_text(encoding="utf-8")
            marker_pairs = (
                (sync.HEADER_START, sync.HEADER_END),
                (sync.FOOTER_START, sync.FOOTER_END),
            )
            for start_marker, end_marker in marker_pairs:
                shared_section = source.split(start_marker, 1)[1].split(end_marker, 1)[0]
                generated_lines = shared_section.splitlines()[1:-1]
                for line_number, line in enumerate(generated_lines, start=1):
                    self.assertEqual(
                        line.rstrip(" \t"),
                        line,
                        f"{config.path}:{start_marker}:{line_number}",
                    )


if __name__ == "__main__":
    unittest.main()
