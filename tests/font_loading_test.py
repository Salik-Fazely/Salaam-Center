from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]

FONT_STYLESHEET = (
    "https://fonts.googleapis.com/css2?"
    "family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;"
    "1,400;1,500;1,600&family=Inter:wght@300;400;500;600&"
    "family=Amiri:ital,wght@0,400;0,700;1,400&"
    "family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;"
    "0,9..144,500;1,9..144,300;1,9..144,400&display=swap"
)

CANONICAL_PAGES = (
    "index.html",
    "about/index.html",
    "blog/index.html",
    "blog/help-children-memorize-short-surahs/index.html",
    "blog/how-parents-can-track-their-childs-quran-progress/index.html",
    "blog/online-quran-classes-for-kids-parents-look-for/index.html",
    "blog/one-to-one-quran-classes-vs-group-classes-for-children/index.html",
    "book-trial/index.html",
    "how-it-works/index.html",
    "pricing/index.html",
    "privacy-policy/index.html",
    "success/index.html",
    "teachers/index.html",
    "terms/index.html",
)


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "link":
            self.links.append(dict(attrs))


def parse_links(relative_path):
    parser = LinkParser()
    parser.feed((ROOT / relative_path).read_text(encoding="utf-8"))
    return parser.links


class FontLoadingTest(unittest.TestCase):
    def test_local_stylesheet_does_not_import_google_fonts(self):
        stylesheet = (ROOT / "assets/css/styles.css").read_text(encoding="utf-8")
        self.assertIsNone(
            re.search(r"@import[^;]*fonts\.googleapis\.com[^;]*;", stylesheet)
        )

    def test_canonical_pages_load_the_exact_font_query_once_in_order(self):
        for relative_path in CANONICAL_PAGES:
            with self.subTest(page=relative_path):
                links = parse_links(relative_path)
                font_links = [
                    (index, link)
                    for index, link in enumerate(links)
                    if link.get("rel") == "stylesheet"
                    and link.get("href", "").startswith(
                        "https://fonts.googleapis.com/css2?"
                    )
                ]
                google_preconnects = [
                    index
                    for index, link in enumerate(links)
                    if link.get("rel") == "preconnect"
                    and link.get("href") == "https://fonts.googleapis.com"
                ]
                gstatic_preconnects = [
                    index
                    for index, link in enumerate(links)
                    if link.get("rel") == "preconnect"
                    and link.get("href") == "https://fonts.gstatic.com"
                    and "crossorigin" in link
                ]
                local_stylesheets = [
                    index
                    for index, link in enumerate(links)
                    if link.get("rel") == "stylesheet"
                    and link.get("href") == "/assets/css/styles.css"
                ]

                self.assertEqual(1, len(font_links))
                self.assertEqual(FONT_STYLESHEET, font_links[0][1]["href"])
                self.assertEqual(1, len(google_preconnects))
                self.assertEqual(1, len(gstatic_preconnects))
                self.assertEqual(1, len(local_stylesheets))
                self.assertLess(google_preconnects[0], font_links[0][0])
                self.assertLess(gstatic_preconnects[0], font_links[0][0])
                self.assertLess(font_links[0][0], local_stylesheets[0])


if __name__ == "__main__":
    unittest.main()
