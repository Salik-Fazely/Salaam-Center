import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLE = ROOT / "blog/how-parents-can-track-their-childs-quran-progress/index.html"
BLOG_INDEX = ROOT / "blog/index.html"
CANONICAL = "https://www.tarteelhouse.com/blog/how-parents-can-track-their-childs-quran-progress/"
DESCRIPTION = (
    "Learn simple ways to track your child’s Quran progress through reading, revision, "
    "confidence, home practice and clear teacher feedback."
)


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.start_tags = []
        self.text_parts = []
        self.json_ld = []
        self._json_parts = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.start_tags.append((tag, attributes))
        if tag == "script" and attributes.get("type") == "application/ld+json":
            self._json_parts = []

    def handle_endtag(self, tag):
        if tag == "script" and self._json_parts is not None:
            self.json_ld.append(json.loads("".join(self._json_parts)))
            self._json_parts = None

    def handle_data(self, data):
        if self._json_parts is not None:
            self._json_parts.append(data)
        else:
            self.text_parts.append(data)


def nodes_of_type(value, schema_type):
    matches = []
    if isinstance(value, dict):
        if value.get("@type") == schema_type:
            matches.append(value)
        for child in value.values():
            matches.extend(nodes_of_type(child, schema_type))
    elif isinstance(value, list):
        for child in value:
            matches.extend(nodes_of_type(child, schema_type))
    return matches


class QuranProgressArticleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ARTICLE.read_text(encoding="utf-8")
        cls.parser = ArticleParser()
        cls.parser.feed(cls.source)
        cls.parser.close()
        cls.text = " ".join(" ".join(cls.parser.text_parts).split())

    def test_approved_sections_reviewer_and_teacher_questions_are_present(self):
        required_headings = (
            "Progress is more than memorising new surahs",
            "Start with a simple baseline",
            "Use a simple six-to-eight-week check-in",
            "Simple Quran Progress Check-in",
            "Ask the teacher these four questions",
            "What to do when progress feels slow",
            "How Tarteel House keeps parents informed",
            "A clear picture is better than constant pressure",
        )
        for heading in required_headings:
            self.assertIn(heading, self.text)
        self.assertIn("Reviewed by Forouhar Rahmani, Tarteel House Quran Teacher", self.text)
        self.assertIn("Reviewed: July 2026", self.text)
        for question in (
            "What is my child’s main learning goal right now?",
            "What improvement have you noticed since the last review?",
            "Which mistake or difficulty needs the most attention?",
            "What should we practise at home before the next lesson?",
        ):
            self.assertIn(question, self.text)

    def test_heading_list_and_progress_table_structure_is_semantic(self):
        tags = [tag for tag, _ in self.parser.start_tags]
        self.assertEqual(1, tags.count("h1"))
        self.assertGreaterEqual(tags.count("h2"), 8)
        self.assertGreaterEqual(tags.count("h3"), 1)
        self.assertGreaterEqual(tags.count("ul"), 3)
        self.assertGreaterEqual(tags.count("ol"), 1)
        self.assertEqual(1, tags.count("table"))
        self.assertEqual(2, tags.count("th"))
        wrappers = [attrs for tag, attrs in self.parser.start_tags if tag == "div"]
        table_wrapper = next(
            attrs for attrs in wrappers if "comparison-table-wrapper" in attrs.get("class", "").split()
        )
        self.assertEqual("region", table_wrapper.get("role"))
        self.assertEqual("0", table_wrapper.get("tabindex"))
        self.assertEqual("progress-check-in-heading", table_wrapper.get("aria-labelledby"))
        content_sections = [
            attrs for tag, attrs in self.parser.start_tags
            if tag == "section" and "legal-section" in attrs.get("class", "").split()
        ]
        self.assertEqual(7, len(content_sections))
        headers = [attrs for tag, attrs in self.parser.start_tags if tag == "th"]
        self.assertTrue(all(attrs.get("scope") == "col" for attrs in headers))
        for label in ("Area", "What to notice", "Current learning goal", "Home practice", "Next step"):
            self.assertIn(label, self.text)

    def test_canonical_cover_links_and_cta_are_preserved_or_updated_as_approved(self):
        canonicals = [
            attrs.get("href")
            for tag, attrs in self.parser.start_tags
            if tag == "link" and attrs.get("rel") == "canonical"
        ]
        self.assertEqual([CANONICAL], canonicals)
        self.assertIn('/assets/blog/track-child-quran-progress.png', self.source)
        links = [attrs.get("href") for tag, attrs in self.parser.start_tags if tag == "a"]
        self.assertIn("/how-it-works/", links)
        self.assertIn("/book-trial/", links)
        self.assertIn("/blog/help-children-memorize-short-surahs/", links)
        self.assertIn("Understand your child’s starting point", self.text)
        self.assertIn(
            "A free trial gives the teacher time to listen to your child, understand their "
            "current level and suggest a suitable next step.",
            self.text,
        )

    def test_metadata_and_blogposting_match_the_approved_article(self):
        descriptions = [
            attrs.get("content")
            for tag, attrs in self.parser.start_tags
            if tag == "meta" and attrs.get("name") in {"description", "twitter:description"}
        ]
        og_descriptions = [
            attrs.get("content")
            for tag, attrs in self.parser.start_tags
            if tag == "meta" and attrs.get("property") == "og:description"
        ]
        self.assertEqual([DESCRIPTION, DESCRIPTION], descriptions)
        self.assertEqual([DESCRIPTION], og_descriptions)
        postings = nodes_of_type(self.parser.json_ld, "BlogPosting")
        self.assertEqual(1, len(postings))
        posting = postings[0]
        self.assertEqual(DESCRIPTION, posting["description"])
        self.assertNotIn("datePublished", posting)
        self.assertEqual("2026-07-14", posting["dateModified"])
        reviewer = posting.get("reviewedBy")
        if reviewer is not None:
            self.assertEqual(
                {"@type": "Person", "name": "Forouhar Rahmani", "jobTitle": "Tarteel House Quran Teacher"},
                reviewer,
            )
        self.assertNotRegex(self.source, r"Forouhar Rahmani.{0,100}(?:https?://|credential|qualification|biograph)")

    def test_blog_card_description_matches_the_expanded_article(self):
        blog_index = BLOG_INDEX.read_text(encoding="utf-8")
        self.assertIn(
            "How to look beyond memorised surahs and notice reading, revision, confidence, "
            "consistency, and independence.",
            blog_index,
        )
        self.assertNotIn(
            "How to look beyond memorized surahs and notice consistency, confidence, recitation, and connection.",
            blog_index,
        )


if __name__ == "__main__":
    unittest.main()
