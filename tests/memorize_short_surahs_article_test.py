import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLE = ROOT / "blog" / "help-children-memorize-short-surahs" / "index.html"
BLOG_INDEX = ROOT / "blog" / "index.html"
CANONICAL = "https://www.tarteelhouse.com/blog/help-children-memorize-short-surahs/"
DESCRIPTION = (
    "Learn a simple way to help children memorise short surahs through listening, "
    "small sections, regular revision and a manageable 10-minute routine."
)
IMAGE = "https://www.tarteelhouse.com/assets/blog/help-children-memorize-short-surahs.png"


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.start_tags = []
        self.text_parts = []
        self.json_ld = []
        self._in_json_ld = False
        self._json_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.start_tags.append((tag, attrs))
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._in_json_ld = True
            self._json_parts = []

    def handle_endtag(self, tag):
        if tag == "script" and self._in_json_ld:
            self.json_ld.append(json.loads("".join(self._json_parts)))
            self._in_json_ld = False

    def handle_data(self, data):
        if self._in_json_ld:
            self._json_parts.append(data)
        elif data.strip():
            self.text_parts.append(data.strip())


def nodes_of_type(documents, schema_type):
    nodes = []
    for document in documents:
        candidates = document.get("@graph", [document])
        nodes.extend(node for node in candidates if node.get("@type") == schema_type)
    return nodes


class MemorizeShortSurahsArticleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ARTICLE.read_text(encoding="utf-8")
        cls.parser = ArticleParser()
        cls.parser.feed(cls.source)
        cls.text = " ".join(cls.parser.text_parts)

    def test_approved_sections_and_reviewer_are_present(self):
        headings = {
            "Start with a small and suitable section",
            "Listen before asking your child to repeat",
            "Break the verse into small parts",
            "Use a manageable 10-minute routine",
            "Ten-Minute Memorisation Routine",
            "Review before adding something new",
            "Correct mistakes clearly",
            "Keep older surahs active",
            "Example Weekly Routine",
            "What parents should avoid",
            "When memorisation feels difficult",
            "How Tarteel House supports memorisation",
            "Keep the routine small and clear",
        }
        for heading in headings:
            self.assertIn(heading, self.text)
        self.assertEqual(
            1,
            self.text.count("Reviewed by Sadiah Hamid, Tarteel House Quran Teacher"),
        )
        self.assertEqual(1, self.text.count("Reviewed: July 2026"))
        self.assertNotIn("Written by Sadiah Hamid", self.text)

    def test_semantic_headings_lists_and_tables_match_the_article(self):
        tags = [tag for tag, _ in self.parser.start_tags]
        self.assertEqual(1, tags.count("h1"))
        self.assertEqual(12, tags.count("h2"))
        self.assertEqual(5, tags.count("h3"))
        self.assertGreaterEqual(tags.count("ul"), 5)
        self.assertEqual(1, tags.count("ol"))
        self.assertEqual(2, tags.count("table"))
        self.assertEqual(4, tags.count("th"))
        ordered_list = re.search(r"<ol[^>]*>(.*?)</ol>", self.source, re.S)
        self.assertIsNotNone(ordered_list)
        self.assertEqual(6, ordered_list.group(1).count("<li>"))
        headers = [attrs for tag, attrs in self.parser.start_tags if tag == "th"]
        self.assertTrue(all(attrs.get("scope") == "col" for attrs in headers))
        wrappers = [
            attrs
            for tag, attrs in self.parser.start_tags
            if tag == "div" and "comparison-table-wrapper" in attrs.get("class", "").split()
        ]
        self.assertEqual(2, len(wrappers))
        self.assertEqual({"region"}, {wrapper.get("role") for wrapper in wrappers})
        self.assertEqual({"0"}, {wrapper.get("tabindex") for wrapper in wrappers})
        self.assertEqual(
            {"ten-minute-routine-heading", "weekly-routine-heading"},
            {wrapper.get("aria-labelledby") for wrapper in wrappers},
        )

    def test_flexible_routine_and_example_week_are_explicit(self):
        self.assertIn(
            "Ten minutes can be a useful starting point for home practice, but it is not a strict rule.",
            self.text,
        )
        self.assertIn(
            "Some children may need a shorter session, while others can continue a little longer.",
            self.text,
        )
        self.assertIn(
            "This is only an example. The teacher may recommend a different pace depending on the "
            "child’s age, level and current goal.",
            self.text,
        )
        for row in (
            "2 minutes Review an older verse or surah",
            "2 minutes Listen to the new short section",
            "3 minutes Repeat it in small parts",
            "2 minutes Join the parts and try without help",
            "1 minute End positively and agree on the next practice",
            "Weekend Calm review of older surahs",
        ):
            self.assertIn(row, self.text)

    def test_canonical_image_links_cta_and_card_are_correct(self):
        canonicals = [
            attrs.get("href")
            for tag, attrs in self.parser.start_tags
            if tag == "link" and attrs.get("rel") == "canonical"
        ]
        self.assertEqual([CANONICAL], canonicals)
        self.assertIn(IMAGE, self.source)
        self.assertIn(
            "/assets/blog/help-children-memorize-short-surahs-640.webp 640w, "
            "/assets/blog/help-children-memorize-short-surahs-1200.webp 1200w",
            self.source,
        )
        links = [attrs.get("href") for tag, attrs in self.parser.start_tags if tag == "a"]
        for href in (
            "/how-it-works/",
            "/blog/how-parents-can-track-their-childs-quran-progress/",
            "/blog/free-online-quran-trial-lesson-parent-checklist/",
            "/book-trial/",
        ):
            self.assertIn(href, links)
        self.assertIn("Find a suitable starting point for your child", self.text)
        self.assertIn(
            "In a free 40-minute trial, the teacher can listen to your child’s current reading and "
            "memorisation level and suggest a suitable next step.",
            self.text,
        )
        blog_index = BLOG_INDEX.read_text(encoding="utf-8")
        self.assertIn(
            "Learn a simple way to help children memorise short surahs through listening, small "
            "sections, regular revision and a manageable 10-minute routine.",
            blog_index,
        )

    def test_metadata_and_blogposting_match_the_approved_article(self):
        descriptions = [
            attrs.get("content")
            for tag, attrs in self.parser.start_tags
            if attrs.get("name") in {"description", "twitter:description"}
        ]
        og_descriptions = [
            attrs.get("content")
            for tag, attrs in self.parser.start_tags
            if attrs.get("property") == "og:description"
        ]
        self.assertEqual([DESCRIPTION, DESCRIPTION], descriptions)
        self.assertEqual([DESCRIPTION], og_descriptions)
        postings = nodes_of_type(self.parser.json_ld, "BlogPosting")
        self.assertEqual(1, len(postings))
        posting = postings[0]
        self.assertEqual("How to Help Children Memorize Short Surahs", posting["headline"])
        self.assertEqual(DESCRIPTION, posting["description"])
        self.assertEqual("2026-07-14", posting["dateModified"])
        self.assertNotIn("datePublished", posting)
        self.assertEqual(IMAGE, posting["image"]["url"])
        self.assertEqual(CANONICAL, posting["mainEntityOfPage"]["@id"])
        self.assertNotIn("reviewedBy", posting)
        self.assertNotIn("author", posting)
        self.assertEqual(1, len(nodes_of_type(self.parser.json_ld, "BreadcrumbList")))

    def test_global_shell_and_scripts_remain_present(self):
        self.assertIn('<header class="site-header" id="top">', self.source)
        self.assertIn('<footer class="site-footer">', self.source)
        self.assertIn('<script src="/assets/js/consent.js"></script>', self.source)
        self.assertIn('<script src="/assets/js/analytics-events.js"></script>', self.source)
        self.assertIn('<script src="/assets/js/main.js"></script>', self.source)


if __name__ == "__main__":
    unittest.main()
