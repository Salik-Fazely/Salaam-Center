import json
import re
import unittest
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from tests.commercial_truth_test import StructureParser


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://www.tarteelhouse.com"
PAGES = {
    "/": "index.html",
    "/about/": "about/index.html",
    "/blog/": "blog/index.html",
    "/blog/help-children-memorize-short-surahs/": "blog/help-children-memorize-short-surahs/index.html",
    "/blog/online-quran-classes-for-kids-parents-look-for/": "blog/online-quran-classes-for-kids-parents-look-for/index.html",
    "/blog/one-to-one-quran-classes-vs-group-classes-for-children/": "blog/one-to-one-quran-classes-vs-group-classes-for-children/index.html",
    "/blog/how-parents-can-track-their-childs-quran-progress/": "blog/how-parents-can-track-their-childs-quran-progress/index.html",
    "/blog/free-online-quran-trial-lesson-parent-checklist/": "blog/free-online-quran-trial-lesson-parent-checklist/index.html",
    "/book-trial/": "book-trial/index.html",
    "/how-it-works/": "how-it-works/index.html",
    "/pricing/": "pricing/index.html",
    "/privacy-policy/": "privacy-policy/index.html",
    "/success/": "success/index.html",
    "/teachers/": "teachers/index.html",
    "/terms/": "terms/index.html",
}
ARTICLES = {
    "/blog/help-children-memorize-short-surahs/": "/assets/blog/help-children-memorize-short-surahs.png",
    "/blog/online-quran-classes-for-kids-parents-look-for/": "/assets/blog/online-quran-classes-for-kids-parents-look-for.png",
    "/blog/one-to-one-quran-classes-vs-group-classes-for-children/": "/assets/blog/one-to-one-vs-group-quran-classes.png",
    "/blog/how-parents-can-track-their-childs-quran-progress/": "/assets/blog/track-child-quran-progress.png",
    "/blog/free-online-quran-trial-lesson-parent-checklist/": "/assets/blog/free-online-quran-trial-lesson-cover.png",
}
ARTICLE_PUBLISHED_DATES = {
    "/blog/free-online-quran-trial-lesson-parent-checklist/": "2026-07-14",
}
SHIMS = {
    "about.html": "/about/",
    "blog.html": "/blog/",
    "book-trial.html": "/book-trial/",
    "how-it-works.html": "/how-it-works/",
    "pricing.html": "/pricing/",
    "privacy-policy.html": "/privacy-policy/",
    "privacy.html": "/privacy-policy/",
    "success.html": "/success/",
    "teachers.html": "/teachers/",
    "terms.html": "/terms/",
}


class SeoParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titles = []
        self.h1s = []
        self.meta = defaultdict(list)
        self.properties = defaultdict(list)
        self.canonicals = []
        self.ids = []
        self.hrefs = []
        self.json_ld = []
        self._capture = None
        self._parts = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in {"title", "h1"}:
            self._capture = tag
            self._parts = []
        if tag == "meta":
            if attributes.get("name"):
                self.meta[attributes["name"].lower()].append(attributes.get("content", ""))
            if attributes.get("property"):
                self.properties[attributes["property"].lower()].append(attributes.get("content", ""))
        if tag == "link" and "canonical" in attributes.get("rel", "").lower().split():
            self.canonicals.append(attributes.get("href", ""))
        if tag == "a" and attributes.get("href"):
            self.hrefs.append(attributes["href"])
        if attributes.get("id"):
            self.ids.append(attributes["id"])
        if tag == "script" and attributes.get("type", "").lower() == "application/ld+json":
            self._capture = "json-ld"
            self._parts = []

    def handle_endtag(self, tag):
        if self._capture == "title" and tag == "title":
            self.titles.append(" ".join("".join(self._parts).split()))
            self._capture = None
        elif self._capture == "h1" and tag == "h1":
            self.h1s.append(" ".join("".join(self._parts).split()))
            self._capture = None
        elif self._capture == "json-ld" and tag == "script":
            self.json_ld.append(json.loads("".join(self._parts)))
            self._capture = None

    def handle_data(self, data):
        if self._capture:
            self._parts.append(data)


def parse(relative_path):
    parser = SeoParser()
    parser.feed((ROOT / relative_path).read_text(encoding="utf-8"))
    parser.close()
    return parser


def json_nodes(documents):
    nodes = []

    def visit(value):
        if isinstance(value, dict):
            if value.get("@type"):
                nodes.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(documents)
    return nodes


def node_of_type(documents, schema_type):
    return next(node for node in json_nodes(documents) if node.get("@type") == schema_type)


def sitemap_urls():
    root = ET.parse(ROOT / "sitemap.xml").getroot()
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return root, {element.text for element in root.findall(".//sm:loc", namespace)}


class TechnicalSeoTests(unittest.TestCase):
    def test_canonical_metadata_indexability_and_headings(self):
        _, sitemap = sitemap_urls()
        titles = []
        descriptions = []
        for path, relative in PAGES.items():
            page = parse(relative)
            canonical = BASE_URL + path
            self.assertEqual([canonical], page.canonicals, path)
            self.assertEqual(1, len(page.titles), path)
            self.assertEqual(1, len(page.meta["description"]), path)
            self.assertEqual(1, len(page.h1s), path)
            self.assertFalse([key for key, count in Counter(page.ids).items() if count > 1], path)
            if path == "/success/":
                self.assertEqual(["noindex, follow"], page.meta["robots"])
                self.assertNotIn(canonical, sitemap)
            else:
                self.assertNotIn("noindex", " ".join(page.meta["robots"]).lower(), path)
                self.assertIn(canonical, sitemap)
                titles.extend(page.titles)
                descriptions.extend(page.meta["description"])
        self.assertEqual(len(titles), len(set(titles)))
        self.assertEqual(len(descriptions), len(set(descriptions)))

    def test_social_metadata_is_complete_without_invented_images(self):
        default_image = "/assets/images/tarteel-house-social-card.png"
        expected_images = {
            "/": default_image,
            "/about/": default_image,
            "/blog/": default_image,
            "/how-it-works/": default_image,
            "/pricing/": default_image,
            "/teachers/": default_image,
            **ARTICLES,
        }
        for path, relative in PAGES.items():
            if path == "/success/":
                continue
            page = parse(relative)
            expected_type = "article" if path in ARTICLES else "website"
            self.assertEqual([expected_type], page.properties["og:type"], path)
            self.assertEqual(page.titles, page.properties["og:title"], path)
            self.assertEqual([BASE_URL + path], page.properties["og:url"], path)
            self.assertEqual(1, len(page.properties["og:description"]), path)
            self.assertEqual(1, len(page.meta["twitter:title"]), path)
            self.assertEqual(1, len(page.meta["twitter:description"]), path)

            expected_image = expected_images.get(path)
            expected_card = "summary_large_image" if expected_image else "summary"
            self.assertEqual([expected_card], page.meta["twitter:card"], path)
            if expected_image:
                absolute = BASE_URL + expected_image
                self.assertEqual([absolute], page.properties["og:image"], path)
                self.assertEqual([absolute], page.meta["twitter:image"], path)
                self.assertTrue((ROOT / expected_image.lstrip("/")).is_file(), path)
            else:
                self.assertFalse(page.properties["og:image"], path)
                self.assertFalse(page.meta["twitter:image"], path)

    def test_homepage_and_articles_have_evidence_backed_json_ld(self):
        home = parse("index.html")
        organization = node_of_type(home.json_ld, "Organization")
        website = node_of_type(home.json_ld, "WebSite")
        self.assertEqual("Tarteel House", organization["name"])
        self.assertEqual(BASE_URL + "/", organization["url"])
        self.assertEqual(BASE_URL + "/assets/logo/tarteel-house@2x.png", organization["logo"]["url"])
        self.assertEqual(BASE_URL + "/", website["url"])

        for path, image_path in ARTICLES.items():
            page = parse(PAGES[path])
            posting = node_of_type(page.json_ld, "BlogPosting")
            breadcrumb = node_of_type(page.json_ld, "BreadcrumbList")
            self.assertEqual(page.h1s[0], posting["headline"], path)
            self.assertEqual(page.meta["description"][0], posting["description"], path)
            self.assertEqual(BASE_URL + image_path, posting["image"]["url"], path)
            self.assertEqual(BASE_URL + path, posting["mainEntityOfPage"]["@id"], path)
            self.assertEqual("Tarteel House", posting["publisher"]["name"], path)
            if path in ARTICLE_PUBLISHED_DATES:
                self.assertEqual(ARTICLE_PUBLISHED_DATES[path], posting["datePublished"], path)
            else:
                self.assertNotIn("datePublished", posting, path)
            self.assertEqual("2026-07-14", posting["dateModified"], path)
            crumbs = breadcrumb["itemListElement"]
            self.assertEqual([1, 2, 3], [crumb["position"] for crumb in crumbs], path)
            self.assertEqual(["Home", "Blog", page.h1s[0]], [crumb["name"] for crumb in crumbs], path)
            self.assertEqual(
                [BASE_URL + "/", BASE_URL + "/blog/", BASE_URL + path],
                [crumb["item"] for crumb in crumbs],
                path,
            )

        forbidden = {"address", "aggregateRating", "review", "award", "priceRange"}
        for relative in PAGES.values():
            for node in json_nodes(parse(relative).json_ld):
                self.assertFalse(forbidden.intersection(node), relative)

    def test_robots_sitemap_clean_links_and_redirect_shims(self):
        sitemap_root, sitemap = sitemap_urls()
        expected = {BASE_URL + path for path in PAGES if path != "/success/"}
        self.assertEqual(expected, sitemap)
        self.assertFalse(sitemap_root.findall(".//{*}lastmod"))
        self.assertFalse(sitemap_root.findall(".//{*}priority"))
        self.assertFalse(sitemap_root.findall(".//{*}changefreq"))

        robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
        self.assertRegex(robots, r"(?im)^User-agent:\s*\*$")
        self.assertRegex(robots, r"(?im)^Allow:\s*/$")
        self.assertNotRegex(robots, r"(?im)^Disallow:")
        self.assertIn(f"Sitemap: {BASE_URL}/sitemap.xml", robots)

        for path, relative in PAGES.items():
            page = parse(relative)
            for href in page.hrefs:
                target = urlsplit(href)
                if target.scheme or href.startswith(("#", "mailto:", "tel:")):
                    continue
                self.assertNotRegex(target.path, r"\.html$", f"{path}: {href}")
                if target.path.startswith("/assets/") or not target.path:
                    continue
                self.assertTrue(target.path.endswith("/"), f"{path}: {href}")
                local = ROOT / (target.path.lstrip("/") or "index.html")
                if local.is_dir():
                    local /= "index.html"
                self.assertTrue(local.is_file(), f"{path}: {href}")

        for relative, destination in SHIMS.items():
            source = (ROOT / relative).read_text(encoding="utf-8")
            shim = parse(relative)
            self.assertEqual(["noindex, follow"], shim.meta["robots"], relative)
            self.assertEqual([BASE_URL + destination], shim.canonicals, relative)
            self.assertIn(f'content="0; url={destination}"', source, relative)
            self.assertNotIn(BASE_URL + "/" + relative, sitemap)

    def test_changed_html_remains_structurally_balanced(self):
        for relative in PAGES.values():
            parser = StructureParser()
            parser.feed((ROOT / relative).read_text(encoding="utf-8"))
            parser.close()
            self.assertEqual([], parser.errors, f"{relative}: {parser.errors}")


if __name__ == "__main__":
    unittest.main()
