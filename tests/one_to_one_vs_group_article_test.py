import json
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLE = ROOT / "blog/one-to-one-quran-classes-vs-group-classes-for-children/index.html"
CANONICAL = "https://www.tarteelhouse.com/blog/one-to-one-quran-classes-vs-group-classes-for-children/"
TITLE = "One-to-One Quran Classes vs Group Classes for Children | Tarteel House"
HEADLINE = "One-to-One Quran Classes vs Group Classes for Children"
DESCRIPTION = (
    "Compare one-to-one and group Quran classes for children, including teacher "
    "attention, pace, corrections, participation and learning needs."
)
IMAGE_URL = "https://www.tarteelhouse.com/assets/blog/one-to-one-vs-group-quran-classes.png"
IMAGE_ALT = (
    "Adam receives focused one-to-one Qur'an guidance from Teacher Amina during an "
    "online lesson."
)
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


def normalise(value):
    return " ".join(value.split())


def classes(attributes):
    return set(attributes.get("class", "").split())


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


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.start_tags = []
        self.headings = {"h1": [], "h2": [], "h3": []}
        self.paragraphs = []
        self.list_items = []
        self.anchors = []
        self.table_rows = []
        self.json_ld = []
        self._capture_tag = None
        self._capture_attrs = None
        self._parts = None
        self._row = None
        self._cell = None
        self._cell_parts = None
        self._json_parts = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.start_tags.append((tag, attributes))
        if tag in {"h1", "h2", "h3", "p", "li", "a"}:
            self._capture_tag = tag
            self._capture_attrs = attributes
            self._parts = []
        elif tag == "tr":
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell = (tag, attributes)
            self._cell_parts = []
        if tag == "script" and attributes.get("type") == "application/ld+json":
            self._json_parts = []

    def handle_endtag(self, tag):
        if tag == self._capture_tag and self._parts is not None:
            text = normalise("".join(self._parts))
            if tag in self.headings:
                self.headings[tag].append(text)
            elif tag == "p":
                self.paragraphs.append((self._capture_attrs, text))
            elif tag == "li":
                self.list_items.append(text)
            elif tag == "a":
                self.anchors.append((text, self._capture_attrs))
            self._capture_tag = None
            self._capture_attrs = None
            self._parts = None
        elif tag in {"th", "td"} and self._cell is not None:
            self._row.append((*self._cell, normalise("".join(self._cell_parts))))
            self._cell = None
            self._cell_parts = None
        elif tag == "tr" and self._row is not None:
            self.table_rows.append(self._row)
            self._row = None
        if tag == "script" and self._json_parts is not None:
            self.json_ld.append(json.loads("".join(self._json_parts)))
            self._json_parts = None

    def handle_data(self, data):
        if self._json_parts is not None:
            self._json_parts.append(data)
            return
        if self._parts is not None:
            self._parts.append(data)
        if self._cell_parts is not None:
            self._cell_parts.append(data)


class StrictStructureParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.doctypes = []

    def handle_decl(self, decl):
        self.doctypes.append(decl.lower())

    def handle_starttag(self, tag, attrs):
        if tag not in VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag not in VOID_ELEMENTS:
            raise AssertionError(f"Non-void element uses self-closing syntax: <{tag} />")

    def handle_endtag(self, tag):
        if not self.stack:
            raise AssertionError(f"Unexpected closing tag: </{tag}>")
        expected = self.stack.pop()
        if tag != expected:
            raise AssertionError(f"Mismatched closing tag: expected </{expected}>, found </{tag}>")


class OneToOneVsGroupArticleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ARTICLE.read_text(encoding="utf-8")
        cls.parser = ArticleParser()
        cls.parser.feed(cls.source)
        cls.parser.close()

    def test_approved_sections_reviewer_and_decision_content_are_complete(self):
        self.assertEqual([HEADLINE], self.parser.headings["h1"])
        required_h2s = (
            "The main difference is how attention is shared",
            "One-to-one lessons can adapt more easily",
            "Group lessons can offer shared motivation",
            "Think about your child\u2019s confidence and personality",
            "Corrections work differently",
            "One-to-one and group classes compared",
            "Which option may suit your child?",
            "Questions to ask before choosing",
            "How Tarteel House lessons work",
            "Choose the format that gives your child the right support",
            "See whether one-to-one learning suits your child",
        )
        self.assertEqual(list(required_h2s), self.parser.headings["h2"])
        self.assertEqual(
            [
                "One-to-one lessons may suit your child when:",
                "A group class may suit your child when:",
            ],
            self.parser.headings["h3"][:2],
        )
        paragraphs = [text for _, text in self.parser.paragraphs]
        self.assertEqual(
            1,
            paragraphs.count("Reviewed by Sadiah Hamid, Tarteel House Quran Teacher"),
        )
        self.assertEqual(1, paragraphs.count("Reviewed: July 2026"))
        self.assertNotIn("Written by", self.source)
        self.assertIn(
            "Neither option is automatically right for every child. The better choice depends on the child\u2019s current level, confidence, learning pace, need for correction and comfort when reading in front of others.",
            paragraphs,
        )
        self.assertIn(
            "\u201cWhich type gives my child the best chance to read, understand corrections and stay involved in the lesson?\u201d",
            paragraphs,
        )

        required_items = (
            "they need close correction;",
            "their level is different from most children of the same age;",
            "they feel uncomfortable reading in front of others;",
            "they need lessons in a particular language;",
            "their learning goal requires flexibility;",
            "they lose focus while waiting for others;",
            "they need more time to read and respond.",
            "they enjoy learning with other children;",
            "they can follow a shared pace;",
            "they are comfortable reading in front of a group;",
            "social participation helps them stay interested;",
            "the group is small and students have similar levels;",
            "shared activities motivate them;",
            "cost is an important part of the family\u2019s decision.",
        )
        for item in required_items:
            self.assertEqual(1, self.parser.list_items.count(item), item)

        questions = (
            "How many children are in the group?",
            "Are the children at similar reading levels?",
            "How much time will my child spend reading during each lesson?",
            "How are individual pronunciation mistakes corrected?",
            "Can the pace or material be adjusted?",
            "How will parents receive progress feedback?",
            "What happens if the teacher or class format is not suitable?",
            "Can my child try a lesson before we decide?",
        )
        for question in questions:
            self.assertEqual(1, self.parser.list_items.count(question), question)

    def test_comparison_table_is_semantic_responsive_and_complete(self):
        wrappers = [
            attrs
            for tag, attrs in self.parser.start_tags
            if tag == "div" and "comparison-table-wrapper" in classes(attrs)
        ]
        self.assertEqual(1, len(wrappers))
        self.assertEqual("region", wrappers[0].get("role"))
        self.assertEqual("0", wrappers[0].get("tabindex"))
        self.assertEqual("class-comparison-heading", wrappers[0].get("aria-labelledby"))
        expected_rows = (
            ("Area", "One-to-one class", "Group class"),
            ("Teacher attention", "Focused on one child", "Shared between students"),
            ("Lesson pace", "Can follow the child\u2019s pace", "Usually follows the group"),
            ("Reading time", "More individual reading time", "Reading time is shared"),
            ("Corrections", "More immediate and personal", "Less time for each individual correction"),
            ("Social interaction", "Limited during the lesson", "Children learn alongside others"),
            ("Flexibility", "Easier to adjust goals and material", "Usually follows a shared plan"),
            ("Distraction", "Often easier to manage", "Depends on group size and behaviour"),
            ("Cost", "May cost more per child", "May be more affordable"),
        )
        actual_rows = tuple(tuple(cell[2] for cell in row) for row in self.parser.table_rows)
        self.assertEqual(expected_rows, actual_rows)
        self.assertTrue(all(cell[0] == "th" for cell in self.parser.table_rows[0]))
        self.assertTrue(all(cell[1].get("scope") == "col" for cell in self.parser.table_rows[0]))

    def test_html_structure_ids_and_heading_count_are_valid(self):
        structure = StrictStructureParser()
        structure.feed(self.source)
        structure.close()
        self.assertEqual(["doctype html"], structure.doctypes)
        self.assertEqual([], structure.stack)
        tags = [tag for tag, _ in self.parser.start_tags]
        self.assertEqual(1, tags.count("h1"))
        ids = [attrs["id"] for _, attrs in self.parser.start_tags if attrs.get("id")]
        self.assertEqual(len(ids), len(set(ids)))
        for _, attrs in self.parser.start_tags:
            for referenced_id in attrs.get("aria-labelledby", "").split():
                self.assertIn(referenced_id, ids)

    def test_metadata_schema_images_links_and_runtime_are_preserved(self):
        self.assertIn(f"<title>{TITLE}</title>", self.source)
        attributes = self.parser.start_tags
        canonicals = [
            attrs.get("href")
            for tag, attrs in attributes
            if tag == "link" and attrs.get("rel") == "canonical"
        ]
        self.assertEqual([CANONICAL], canonicals)
        descriptions = [
            attrs.get("content")
            for tag, attrs in attributes
            if tag == "meta"
            and (
                attrs.get("name") in {"description", "twitter:description"}
                or attrs.get("property") == "og:description"
            )
        ]
        self.assertEqual([DESCRIPTION, DESCRIPTION, DESCRIPTION], descriptions)
        postings = nodes_of_type(self.parser.json_ld, "BlogPosting")
        breadcrumbs = nodes_of_type(self.parser.json_ld, "BreadcrumbList")
        self.assertEqual(1, len(postings))
        self.assertEqual(1, len(breadcrumbs))
        posting = postings[0]
        self.assertEqual(HEADLINE, posting["headline"])
        self.assertEqual(DESCRIPTION, posting["description"])
        self.assertEqual("2026-07-14", posting["dateModified"])
        self.assertNotIn("author", posting)
        self.assertNotIn("reviewedBy", posting)
        self.assertEqual(CANONICAL, posting["mainEntityOfPage"]["@id"])
        self.assertEqual(IMAGE_URL, posting["image"]["url"])
        self.assertEqual("Tarteel House", posting["publisher"]["name"])

        self.assertIn(
            '<source type="image/webp" srcset="/assets/blog/one-to-one-vs-group-quran-classes-640.webp 640w, /assets/blog/one-to-one-vs-group-quran-classes-1200.webp 1200w" sizes="(max-width: 720px) calc(90vw - 2px), 638px" />',
            self.source,
        )
        self.assertIn(
            f'<img src="/assets/blog/one-to-one-vs-group-quran-classes.png" alt="{IMAGE_ALT}" width="1200" height="630" loading="eager" decoding="async" fetchpriority="high" />',
            self.source,
        )
        links = {text: attrs.get("href") for text, attrs in self.parser.anchors}
        self.assertEqual("/how-it-works/", links.get("how Tarteel House lessons work"))
        self.assertEqual(
            "/blog/free-online-quran-trial-lesson-parent-checklist/",
            links.get("free online Quran trial lesson"),
        )
        self.assertEqual("/book-trial/", links.get("Book a Free Trial"))
        self.assertEqual(
            "/blog/online-quran-classes-for-kids-parents-look-for/",
            links.get("Online Quran Classes for Kids: What Parents Should Look For"),
        )
        self.assertEqual(
            "/blog/free-online-quran-trial-lesson-parent-checklist/",
            links.get("What Happens in a Free Online Quran Trial Lesson? A Parent Checklist"),
        )
        scripts = [attrs.get("src") for tag, attrs in attributes if tag == "script" and attrs.get("src")]
        self.assertEqual(
            ["/assets/js/consent.js", "/assets/js/analytics-events.js", "/assets/js/main.js"],
            scripts,
        )

    def test_required_local_targets_exist(self):
        targets = (
            "/how-it-works/",
            "/blog/free-online-quran-trial-lesson-parent-checklist/",
            "/book-trial/",
            "/blog/online-quran-classes-for-kids-parents-look-for/",
        )
        for target in targets:
            self.assertTrue((ROOT / target.strip("/") / "index.html").is_file(), target)


if __name__ == "__main__":
    unittest.main()
