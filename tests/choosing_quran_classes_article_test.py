import json
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLE = ROOT / "blog/online-quran-classes-for-kids-parents-look-for/index.html"
CANONICAL = "https://www.tarteelhouse.com/blog/online-quran-classes-for-kids-parents-look-for/"
DESCRIPTION = (
    "Learn what to look for in online Quran classes for kids, from teacher communication "
    "and level assessment to corrections, progress and trial lessons."
)
VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


def normalise(value):
    return " ".join(value.split())


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.start_tags = []
        self.paragraphs = []
        self.list_items = []
        self.headings = {"h1": [], "h2": [], "h3": []}
        self.anchors = []
        self.table_rows = []
        self.json_ld = []
        self._paragraph_parts = None
        self._list_item_parts = None
        self._heading_tag = None
        self._heading_parts = None
        self._anchor_attrs = None
        self._anchor_parts = None
        self._table_depth = 0
        self._row = None
        self._cell_tag = None
        self._cell_attrs = None
        self._cell_parts = None
        self._json_parts = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.start_tags.append((tag, attributes))
        if tag == "p":
            self._paragraph_parts = []
        elif tag == "li":
            self._list_item_parts = []
        elif tag in self.headings:
            self._heading_tag = tag
            self._heading_parts = []
        elif tag == "a":
            self._anchor_attrs = attributes
            self._anchor_parts = []
        elif tag == "table":
            self._table_depth += 1
        elif tag == "tr" and self._table_depth:
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell_tag = tag
            self._cell_attrs = attributes
            self._cell_parts = []
        if tag == "script" and attributes.get("type") == "application/ld+json":
            self._json_parts = []

    def handle_endtag(self, tag):
        if tag == "p" and self._paragraph_parts is not None:
            self.paragraphs.append(normalise("".join(self._paragraph_parts)))
            self._paragraph_parts = None
        elif tag == "li" and self._list_item_parts is not None:
            self.list_items.append(normalise("".join(self._list_item_parts)))
            self._list_item_parts = None
        elif tag == self._heading_tag and self._heading_parts is not None:
            self.headings[tag].append(normalise("".join(self._heading_parts)))
            self._heading_tag = None
            self._heading_parts = None
        elif tag == "a" and self._anchor_parts is not None:
            self.anchors.append((normalise("".join(self._anchor_parts)), self._anchor_attrs))
            self._anchor_attrs = None
            self._anchor_parts = None
        elif tag in {"th", "td"} and tag == self._cell_tag:
            self._row.append(
                (self._cell_tag, self._cell_attrs, normalise("".join(self._cell_parts)))
            )
            self._cell_tag = None
            self._cell_attrs = None
            self._cell_parts = None
        elif tag == "tr" and self._row is not None:
            self.table_rows.append(self._row)
            self._row = None
        elif tag == "table":
            self._table_depth -= 1
        if tag == "script" and self._json_parts is not None:
            self.json_ld.append(json.loads("".join(self._json_parts)))
            self._json_parts = None

    def handle_data(self, data):
        if self._json_parts is not None:
            self._json_parts.append(data)
            return
        if self._paragraph_parts is not None:
            self._paragraph_parts.append(data)
        if self._list_item_parts is not None:
            self._list_item_parts.append(data)
        if self._heading_parts is not None:
            self._heading_parts.append(data)
        if self._anchor_parts is not None:
            self._anchor_parts.append(data)
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
            self.fail(f"Non-void element uses self-closing syntax: <{tag} />")

    def handle_endtag(self, tag):
        if not self.stack:
            self.fail(f"Unexpected closing tag: </{tag}>")
        expected = self.stack.pop()
        if tag != expected:
            self.fail(f"Mismatched closing tag: expected </{expected}>, found </{tag}>")

    @staticmethod
    def fail(message):
        raise AssertionError(message)


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


class ChoosingQuranClassesArticleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ARTICLE.read_text(encoding="utf-8")
        cls.parser = ArticleParser()
        cls.parser.feed(cls.source)
        cls.parser.close()
        cls.structure_parser = StrictStructureParser()
        cls.structure_parser.feed(cls.source)
        cls.structure_parser.close()

    def test_approved_sections_reviewer_and_copy_are_complete(self):
        self.assertEqual(
            ["Online Quran Classes for Kids: What Parents Should Look For"],
            self.parser.headings["h1"],
        )
        required_h2s = (
            "The teacher should help your child feel comfortable",
            "The lesson should match your child’s real level",
            "Corrections should be clear and manageable",
            "Parents should understand the learning plan",
            "What to watch during the trial lesson",
            "Look for clear and realistic information",
            "What Tarteel House offers",
            "Choose the class that fits your child",
        )
        for heading in required_h2s:
            self.assertIn(heading, self.parser.headings["h2"])
        self.assertIn("Parent’s Online Quran Class Checklist", self.parser.headings["h3"])
        self.assertEqual(
            1,
            self.parser.paragraphs.count(
                "Reviewed by Fareshta Suroush, Tarteel House Quran Teacher"
            ),
        )
        self.assertEqual(1, self.parser.paragraphs.count("Reviewed: July 2026"))

        required_paragraphs = (
            "It can be difficult to judge an online Quran class before your child has tried it.",
            "A professional website and a friendly message may create a good first impression, but they do not show what the lesson itself will feel like. During the trial, notice how the teacher communicates, checks your child’s level and responds to mistakes.",
            "A child does not need to feel completely confident in the first lesson. They may be shy, speak quietly or worry about making mistakes.",
            "A suitable teacher should speak directly to the child, give them enough time to answer and avoid making them feel embarrassed. When the child makes a mistake, the teacher should help them try again calmly.",
            "Comfort does not mean the lesson has no structure. It means the child can learn without feeling afraid of every mistake.",
            "Two children of the same age may need very different lessons. One may still be learning Arabic letters. Another may read independently but need support with pronunciation or Tajweed, the rules used for correct Quran recitation.",
            "A structured learning programme can be helpful, but the teacher should first decide where the child needs to begin and how quickly to move.",
            "Depending on the lesson, a teacher may focus on one or two important mistakes instead of stopping the child after every sound.",
            "The child should finish the correction knowing what to practise—not simply knowing that something was wrong.",
            "A simple plan helps the child, teacher and parent work towards the same goal. You can read more about how online lessons and progress reviews work at Tarteel House.",
            "A trial lesson is not an exam. Your child does not need to perform perfectly.",
            "A child may still feel nervous after one lesson. The goal is not instant excitement. The goal is to see whether there is enough comfort, understanding and communication to continue.",
            "Quran learning takes time. Progress can depend on the child’s current level, attendance, revision, confidence and home routine.",
            "Tarteel House provides one-to-one online Quran lessons for children aged 5–16.",
            "Trial and paid lessons are 40 minutes. Teachers are matched according to the child’s level, language needs and schedule. Parents can express a teacher preference and request a change if the teaching style is not suitable.",
            "Parents are invited to a 15-minute progress review every two months. When a meeting is not practical, a visual progress update can be shared through WhatsApp.",
            "You can also meet the Tarteel House teachers and learn about their teaching languages.",
            "A good online Quran class should help your child understand what they are learning, feel safe enough to make mistakes and know what to practise next.",
            "Pay attention to how the teacher listens, corrects, explains and responds to your child.",
        )
        for paragraph in required_paragraphs:
            self.assertIn(paragraph, self.parser.paragraphs)

        required_list_items = (
            "which letters, words or verses the child can read;",
            "what the child has already memorised;",
            "What is my child’s current learning goal?",
            "What should they practise at home?",
            "Did you understand the teacher?",
            "Would you feel comfortable meeting this teacher again?",
            "very fast results for every child;",
            "the same approach for every age and level.",
            "lesson duration;",
            "what happens if the teacher is not a good match;",
            "prices and package conditions.",
        )
        for item in required_list_items:
            self.assertIn(item, self.parser.list_items)

    def test_checklist_table_and_content_structure_are_semantic(self):
        tags = [tag for tag, _ in self.parser.start_tags]
        self.assertEqual(1, tags.count("h1"))
        self.assertEqual(1, tags.count("table"))
        wrappers = [
            attrs
            for tag, attrs in self.parser.start_tags
            if tag == "div" and "comparison-table-wrapper" in attrs.get("class", "").split()
        ]
        self.assertEqual(1, len(wrappers))
        self.assertEqual("region", wrappers[0].get("role"))
        self.assertEqual("0", wrappers[0].get("tabindex"))
        self.assertEqual("online-class-checklist-heading", wrappers[0].get("aria-labelledby"))
        tables = [attrs for tag, attrs in self.parser.start_tags if tag == "table"]
        self.assertEqual("online-class-checklist-heading", tables[0].get("aria-labelledby"))

        expected_rows = (
            ("What to check", "What to notice"),
            ("Teacher communication", "Did the teacher speak clearly and directly to your child?"),
            ("Level assessment", "Did the teacher listen before deciding what to teach?"),
            ("Lesson pace", "Was the lesson too fast, too slow or suitable?"),
            ("Corrections", "Did your child understand what to change?"),
            ("Teaching language", "Could your child understand the teacher’s explanations?"),
            ("Participation", "Did your child have enough time to read, answer and repeat?"),
            ("Emotional comfort", "Did your child feel safe enough to try after a mistake?"),
            ("Next step", "Did the teacher explain what your child should work on next?"),
        )
        actual_rows = tuple(tuple(cell[2] for cell in row) for row in self.parser.table_rows)
        self.assertEqual(expected_rows, actual_rows)
        self.assertTrue(all(cell[0] == "th" for cell in self.parser.table_rows[0]))
        self.assertTrue(all(cell[1].get("scope") == "col" for cell in self.parser.table_rows[0]))
        self.assertTrue(
            all(cell[0] == "td" for row in self.parser.table_rows[1:] for cell in row)
        )

    def test_html_tags_ids_and_aria_references_are_well_formed(self):
        self.assertEqual(["doctype html"], self.structure_parser.doctypes)
        self.assertEqual([], self.structure_parser.stack)
        ids = [attrs["id"] for _, attrs in self.parser.start_tags if attrs.get("id")]
        self.assertEqual(len(ids), len(set(ids)))
        for _, attrs in self.parser.start_tags:
            for referenced_id in attrs.get("aria-labelledby", "").split():
                self.assertIn(referenced_id, ids)

    def test_required_links_cta_cover_and_runtime_modules_are_preserved(self):
        links_by_text = {text: attrs.get("href") for text, attrs in self.parser.anchors}
        self.assertEqual(
            "/how-it-works/",
            links_by_text.get("how online lessons and progress reviews work at Tarteel House"),
        )
        self.assertEqual("/teachers/", links_by_text.get("meet the Tarteel House teachers"))
        self.assertEqual("/book-trial/", links_by_text.get("Book a Free Trial"))
        self.assertEqual(
            "/blog/one-to-one-quran-classes-vs-group-classes-for-children/",
            links_by_text.get("One-to-One Quran Classes vs Group Classes for Children"),
        )
        self.assertEqual(
            "/blog/how-parents-can-track-their-childs-quran-progress/",
            links_by_text.get("How Parents Can Track Their Child’s Quran Progress"),
        )
        self.assertIn("See the teaching style before you decide", self.parser.headings["h2"])
        self.assertIn(
            "A free 40-minute trial allows your child to meet a teacher, read at their current level and see whether the communication and teaching style feel suitable.",
            self.parser.paragraphs,
        )
        self.assertIn(
            '<source type="image/webp" srcset="/assets/blog/online-quran-classes-for-kids-parents-look-for-640.webp 640w, /assets/blog/online-quran-classes-for-kids-parents-look-for-1200.webp 1200w" sizes="(max-width: 720px) calc(90vw - 2px), 638px" />',
            self.source,
        )
        self.assertIn(
            '<img src="/assets/blog/online-quran-classes-for-kids-parents-look-for.png" alt="Adam joins an online Qur\'an lesson with Teacher Amina on a laptop in a calm home setting." width="1200" height="630" loading="eager" decoding="async" fetchpriority="high" />',
            self.source,
        )
        scripts = [
            attrs.get("src")
            for tag, attrs in self.parser.start_tags
            if tag == "script" and attrs.get("src")
        ]
        self.assertEqual(
            ["/assets/js/consent.js", "/assets/js/analytics-events.js", "/assets/js/main.js"],
            scripts,
        )

    def test_metadata_and_blogposting_match_the_expanded_article(self):
        canonicals = [
            attrs.get("href")
            for tag, attrs in self.parser.start_tags
            if tag == "link" and attrs.get("rel") == "canonical"
        ]
        self.assertEqual([CANONICAL], canonicals)
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
        self.assertEqual("Online Quran Classes for Kids: What Parents Should Look For", posting["headline"])
        self.assertEqual(DESCRIPTION, posting["description"])
        self.assertNotIn("datePublished", posting)
        self.assertEqual("2026-07-14", posting["dateModified"])
        self.assertNotIn("reviewedBy", posting)
        self.assertNotIn("author", posting)
        self.assertEqual(CANONICAL, posting["mainEntityOfPage"]["@id"])
        self.assertEqual(
            "https://www.tarteelhouse.com/assets/blog/online-quran-classes-for-kids-parents-look-for.png",
            posting["image"]["url"],
        )
        self.assertEqual("Tarteel House", posting["publisher"]["name"])

    def test_required_local_link_targets_exist(self):
        required_targets = (
            "/how-it-works/",
            "/teachers/",
            "/book-trial/",
            "/blog/one-to-one-quran-classes-vs-group-classes-for-children/",
            "/blog/how-parents-can-track-their-childs-quran-progress/",
        )
        for target in required_targets:
            self.assertTrue((ROOT / target.strip("/") / "index.html").is_file(), target)


if __name__ == "__main__":
    unittest.main()
