import html
import re
import struct
import unittest
import xml.etree.ElementTree as ET
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://www.tarteelhouse.com"
SOCIAL_IMAGE_PATH = ROOT / "assets/images/tarteel-house-social-card.png"
SOCIAL_IMAGE_URL = BASE_URL + "/assets/images/tarteel-house-social-card.png"
SOCIAL_IMAGE_ALT = "Tarteel House — one-to-one online Quran lessons for children"
OFFICIAL_WHATSAPP_URL = "https://wa.me/34614494311"

DEFAULT_IMAGE_PAGES = (
    "index.html",
    "about/index.html",
    "blog/index.html",
    "how-it-works/index.html",
    "pricing/index.html",
    "teachers/index.html",
)

ARTICLE_IMAGES = {
    "blog/free-online-quran-trial-lesson-parent-checklist/index.html": (
        BASE_URL + "/assets/blog/free-online-quran-trial-lesson-cover.png"
    ),
    "blog/help-children-memorize-short-surahs/index.html": (
        BASE_URL + "/assets/blog/help-children-memorize-short-surahs.png"
    ),
    "blog/how-parents-can-track-their-childs-quran-progress/index.html": (
        BASE_URL + "/assets/blog/track-child-quran-progress.png"
    ),
    "blog/one-to-one-quran-classes-vs-group-classes-for-children/index.html": (
        BASE_URL + "/assets/blog/one-to-one-vs-group-quran-classes.png"
    ),
    "blog/online-quran-classes-for-kids-parents-look-for/index.html": (
        BASE_URL + "/assets/blog/online-quran-classes-for-kids-parents-look-for.png"
    ),
}

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

FONT_STYLESHEET = (
    "https://fonts.googleapis.com/css2?"
    "family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;"
    "1,400;1,500;1,600&family=Inter:wght@300;400;500;600&"
    "family=Amiri:ital,wght@0,400;0,700;1,400&"
    "family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;"
    "0,9..144,500;1,9..144,300;1,9..144,400&display=swap"
)


class PageParser(HTMLParser):
    VOID_ELEMENTS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = defaultdict(list)
        self.properties = defaultdict(list)
        self.links = []
        self.stylesheets = []
        self.icons = []
        self.h1s = []
        self.titles = []
        self.main_parts = []
        self._capture = None
        self._parts = []
        self._main_depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "meta":
            name = attributes.get("name", "").lower()
            prop = attributes.get("property", "").lower()
            if name:
                self.meta[name].append(attributes.get("content", ""))
            if prop:
                self.properties[prop].append(attributes.get("content", ""))
        elif tag == "a":
            self.links.append(
                {
                    "href": attributes.get("href", ""),
                    "parts": [],
                }
            )
        elif tag == "link":
            rel = attributes.get("rel", "").lower().split()
            if "stylesheet" in rel:
                self.stylesheets.append(attributes.get("href", ""))
            if "icon" in rel or "apple-touch-icon" in rel:
                self.icons.append(attributes.get("href", ""))
        elif tag in {"title", "h1"}:
            self._capture = tag
            self._parts = []

        if tag == "main":
            self._main_depth += 1
        elif self._main_depth and tag not in self.VOID_ELEMENTS:
            self._main_depth += 1

    def handle_endtag(self, tag):
        if self._capture == "title" and tag == "title":
            self.titles.append(" ".join("".join(self._parts).split()))
            self._capture = None
        elif self._capture == "h1" and tag == "h1":
            self.h1s.append(" ".join("".join(self._parts).split()))
            self._capture = None

        if tag == "a" and self.links:
            self.links[-1]["text"] = " ".join(
                "".join(self.links[-1].pop("parts")).split()
            )

        if self._main_depth and tag not in self.VOID_ELEMENTS:
            self._main_depth -= 1

    def handle_data(self, data):
        if self._capture:
            self._parts.append(data)
        if self.links and "text" not in self.links[-1]:
            self.links[-1]["parts"].append(data)
        if self._main_depth:
            self.main_parts.append(data)


def parse_page(relative_path):
    parser = PageParser()
    parser.feed((ROOT / relative_path).read_text(encoding="utf-8"))
    parser.close()
    return parser


def png_chunks(path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"{path} is not a PNG file")

    offset = 8
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        yield kind, payload
        offset += 12 + length


def png_dimensions_and_text(path):
    dimensions = None
    text_chunks = {}
    for kind, payload in png_chunks(path):
        if kind == b"IHDR":
            dimensions = struct.unpack(">II", payload[:8])
        elif kind == b"tEXt":
            key, value = payload.split(b"\0", 1)
            text_chunks[key.decode("latin-1")] = value.decode("latin-1")
    return dimensions, text_chunks


class Branded404SocialTests(unittest.TestCase):
    def test_root_404_has_required_metadata_and_actions(self):
        page_path = ROOT / "404.html"
        self.assertTrue(page_path.is_file(), "root 404.html is missing")
        page = parse_page("404.html")

        self.assertEqual(["Page Not Found | Tarteel House"], page.titles)
        self.assertEqual(["noindex, follow"], page.meta["robots"])
        self.assertEqual(["Page not found"], page.h1s)

        links = {(link["href"], link.get("text", "")) for link in page.links}
        self.assertIn(("/", "Go to homepage"), links)
        self.assertIn(("/book-trial/", "Book a free trial"), links)
        self.assertIn((OFFICIAL_WHATSAPP_URL, "WhatsApp us"), links)

    def test_404_uses_existing_font_favicon_styles_and_consent_pattern(self):
        page_path = ROOT / "404.html"
        self.assertTrue(page_path.is_file(), "root 404.html is missing")
        source = page_path.read_text(encoding="utf-8")
        page = parse_page("404.html")

        self.assertEqual(1, page.stylesheets.count(FONT_STYLESHEET))
        self.assertEqual(1, page.stylesheets.count("/assets/css/styles.css"))
        self.assertIn("/assets/logo/favicon.ico", page.icons)
        self.assertEqual(1, source.count('<script src="/assets/js/consent.js"></script>'))
        self.assertEqual(1, source.count('<script src="/assets/js/main.js"></script>'))

    def test_404_is_not_listed_in_sitemap(self):
        sitemap = ET.parse(ROOT / "sitemap.xml").getroot()
        locations = [node.text or "" for node in sitemap.findall(".//{*}loc")]
        self.assertNotIn(BASE_URL + "/404.html", locations)
        self.assertNotIn(BASE_URL + "/404/", locations)

    def test_default_social_image_is_exact_png_with_approved_copy(self):
        self.assertTrue(SOCIAL_IMAGE_PATH.is_file(), "default social image is missing")
        dimensions, text_chunks = png_dimensions_and_text(SOCIAL_IMAGE_PATH)

        self.assertEqual((1200, 630), dimensions)
        self.assertEqual("Tarteel House", text_chunks.get("Title"))
        self.assertEqual(
            "One-to-one online Quran lessons for children",
            text_chunks.get("Primary"),
        )
        self.assertEqual(
            "Calm, personal learning with dedicated teachers",
            text_chunks.get("Secondary"),
        )

    def test_core_pages_use_one_complete_default_social_image_set(self):
        for relative_path in DEFAULT_IMAGE_PAGES:
            with self.subTest(page=relative_path):
                page = parse_page(relative_path)
                self.assertEqual([SOCIAL_IMAGE_URL], page.properties["og:image"])
                self.assertEqual(["1200"], page.properties["og:image:width"])
                self.assertEqual(["630"], page.properties["og:image:height"])
                self.assertEqual([SOCIAL_IMAGE_ALT], page.properties["og:image:alt"])
                self.assertEqual(["summary_large_image"], page.meta["twitter:card"])
                self.assertEqual([SOCIAL_IMAGE_URL], page.meta["twitter:image"])
                self.assertEqual([SOCIAL_IMAGE_ALT], page.meta["twitter:image:alt"])

    def test_404_uses_one_complete_default_social_image_set(self):
        page_path = ROOT / "404.html"
        self.assertTrue(page_path.is_file(), "root 404.html is missing")
        page = parse_page("404.html")

        self.assertEqual([SOCIAL_IMAGE_URL], page.properties["og:image"])
        self.assertEqual(["1200"], page.properties["og:image:width"])
        self.assertEqual(["630"], page.properties["og:image:height"])
        self.assertEqual([SOCIAL_IMAGE_ALT], page.properties["og:image:alt"])
        self.assertEqual(["summary_large_image"], page.meta["twitter:card"])
        self.assertEqual([SOCIAL_IMAGE_URL], page.meta["twitter:image"])
        self.assertEqual([SOCIAL_IMAGE_ALT], page.meta["twitter:image:alt"])

    def test_blog_articles_keep_their_specific_social_images(self):
        for relative_path, expected_image in ARTICLE_IMAGES.items():
            with self.subTest(page=relative_path):
                page = parse_page(relative_path)
                self.assertEqual([expected_image], page.properties["og:image"])
                self.assertEqual([expected_image], page.meta["twitter:image"])
                self.assertEqual(["1200"], page.properties["og:image:width"])
                self.assertEqual(["630"], page.properties["og:image:height"])
                self.assertNotIn(SOCIAL_IMAGE_URL, page.properties["og:image"])

    def test_redirect_stubs_have_no_default_social_image_metadata(self):
        for relative_path in REDIRECT_STUBS:
            with self.subTest(page=relative_path):
                page = parse_page(relative_path)
                self.assertEqual([], page.properties["og:image"])
                self.assertEqual([], page.meta["twitter:image"])

    def test_404_and_card_copy_exclude_obsolete_or_unsupported_claims(self):
        page_path = ROOT / "404.html"
        self.assertTrue(page_path.is_file(), "root 404.html is missing")
        page = parse_page("404.html")
        main_text = " ".join(html.unescape(" ".join(page.main_parts)).split()).lower()
        self.assertIn(
            "the page you’re looking for may have moved or no longer exists.",
            main_text,
        )

        self.assertTrue(SOCIAL_IMAGE_PATH.is_file(), "default social image is missing")
        _, text_chunks = png_dimensions_and_text(SOCIAL_IMAGE_PATH)
        reviewed_copy = main_text + " " + " ".join(text_chunks.values()).lower()
        forbidden_patterns = (
            r"\b(?:5|10|20|five|ten|twenty)\s*(?:-| )\s*(?:lesson|session)s?\b",
            r"\b(?:3|three)\s+make[- ]?up\s+lessons?\b",
            r"\b(?:best|guaranteed|number one|#1)\b",
            r"\b(?:testimonial|student count|teacher count)\b",
            r"(?:€|£|\$)\s*\d+",
            r"\b(?:21\+ students|100% trusted by families)\b",
        )
        for pattern in forbidden_patterns:
            self.assertIsNone(re.search(pattern, reviewed_copy, re.IGNORECASE), pattern)


if __name__ == "__main__":
    unittest.main()
