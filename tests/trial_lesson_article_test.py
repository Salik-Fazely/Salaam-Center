import json
import struct
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLE = ROOT / "blog/free-online-quran-trial-lesson-parent-checklist/index.html"
BLOG_INDEX = ROOT / "blog/index.html"
RELATED_ARTICLE = ROOT / "blog/online-quran-classes-for-kids-parents-look-for/index.html"
SITEMAP = ROOT / "sitemap.xml"
CANONICAL = "https://www.tarteelhouse.com/blog/free-online-quran-trial-lesson-parent-checklist/"
TITLE = "What Happens in a Free Online Quran Trial Lesson? | Tarteel House"
HEADLINE = "What Happens in a Free Online Quran Trial Lesson? A Parent Checklist"
DESCRIPTION = (
    "Learn what happens before, during and after a free online Quran trial lesson, "
    "with a simple checklist to help parents assess the experience."
)
IMAGE_URL = "https://www.tarteelhouse.com/assets/blog/free-online-quran-trial-lesson-cover.png"
IMAGE_ALT = "A child attending a one-to-one online Quran trial lesson with a female teacher"
IMAGE_FILES = (
    ROOT / "assets/blog/free-online-quran-trial-lesson-cover.png",
    ROOT / "assets/blog/free-online-quran-trial-lesson-cover-640.webp",
    ROOT / "assets/blog/free-online-quran-trial-lesson-cover-1200.webp",
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


def classes(attributes):
    return attributes.get("class", "").split()


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


def image_dimensions(path):
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return struct.unpack(">II", data[16:24])
    if not (data.startswith(b"RIFF") and data[8:12] == b"WEBP"):
        raise AssertionError(f"Unsupported image format: {path}")

    offset = 12
    while offset + 8 <= len(data):
        chunk_type = data[offset : offset + 4]
        chunk_size = struct.unpack("<I", data[offset + 4 : offset + 8])[0]
        payload = offset + 8
        if chunk_type == b"VP8X":
            width = 1 + int.from_bytes(data[payload + 4 : payload + 7], "little")
            height = 1 + int.from_bytes(data[payload + 7 : payload + 10], "little")
            return width, height
        if chunk_type == b"VP8 ":
            width = struct.unpack("<H", data[payload + 6 : payload + 8])[0] & 0x3FFF
            height = struct.unpack("<H", data[payload + 8 : payload + 10])[0] & 0x3FFF
            return width, height
        if chunk_type == b"VP8L":
            bits = int.from_bytes(data[payload + 1 : payload + 5], "little")
            width = (bits & 0x3FFF) + 1
            height = ((bits >> 14) & 0x3FFF) + 1
            return width, height
        offset = payload + chunk_size + (chunk_size % 2)
    raise AssertionError(f"No WebP dimensions found: {path}")


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.start_tags = []
        self.headings = {"h1": [], "h2": [], "h3": []}
        self.paragraphs = []
        self.anchors = []
        self.table_rows = []
        self.json_ld = []
        self.article_text_parts = []
        self._heading_tag = None
        self._heading_parts = None
        self._paragraph_attrs = None
        self._paragraph_parts = None
        self._anchor_attrs = None
        self._anchor_parts = None
        self._table_depth = 0
        self._row = None
        self._cell_tag = None
        self._cell_attrs = None
        self._cell_parts = None
        self._json_parts = None
        self._article_depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.start_tags.append((tag, attributes))

        if self._article_depth:
            if tag not in VOID_ELEMENTS:
                self._article_depth += 1
        elif tag == "div" and "blog-article" in classes(attributes):
            self._article_depth = 1

        if tag in self.headings:
            self._heading_tag = tag
            self._heading_parts = []
        elif tag == "p":
            self._paragraph_attrs = attributes
            self._paragraph_parts = []
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
        if tag == self._heading_tag and self._heading_parts is not None:
            self.headings[tag].append(normalise("".join(self._heading_parts)))
            self._heading_tag = None
            self._heading_parts = None
        elif tag == "p" and self._paragraph_parts is not None:
            self.paragraphs.append(
                (self._paragraph_attrs, normalise("".join(self._paragraph_parts)))
            )
            self._paragraph_attrs = None
            self._paragraph_parts = None
        elif tag == "a" and self._anchor_parts is not None:
            self.anchors.append(
                (normalise("".join(self._anchor_parts)), self._anchor_attrs)
            )
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

        if self._article_depth and tag not in VOID_ELEMENTS:
            self._article_depth -= 1

    def handle_data(self, data):
        if self._json_parts is not None:
            self._json_parts.append(data)
            return
        if self._article_depth:
            self.article_text_parts.append(data)
        if self._heading_parts is not None:
            self._heading_parts.append(data)
        if self._paragraph_parts is not None:
            self._paragraph_parts.append(data)
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
            raise AssertionError(f"Non-void element uses self-closing syntax: <{tag} />")

    def handle_endtag(self, tag):
        if not self.stack:
            raise AssertionError(f"Unexpected closing tag: </{tag}>")
        expected = self.stack.pop()
        if tag != expected:
            raise AssertionError(
                f"Mismatched closing tag: expected </{expected}>, found </{tag}>"
            )


EXPECTED_ARTICLE_TEXT = normalise(
    """
    What Happens in a Free Online Quran Trial Lesson? A Parent Checklist
    Booking an online Quran trial lesson can feel uncertain, especially when your child has never studied online before.
    You may wonder whether your child needs to prepare, what the teacher will ask or whether the lesson will feel like an exam.
    A trial lesson should not test whether your child is “good enough.” It should help the teacher understand your child’s starting point while giving your child a real experience of the teaching style.
    Here is what parents can usually expect before, during and after a trial lesson.
    Reviewed by Fareshta Suroush, Tarteel House Quran Teacher
    Reviewed: July 2026
    Before the trial: your child does not need to prepare perfectly
    Your child does not need to memorise a new surah or practise special material before the trial.
    It is more helpful for the teacher to hear what your child can currently do, including the parts they find difficult. Mistakes give the teacher useful information about where to begin.
    Before the lesson, prepare:
    a laptop, tablet or suitable device;
    a stable internet connection;
    a quiet place where your child can hear clearly;
    any Quran book or learning material your child already uses;
    a few basic details about your child’s previous learning.
    You can tell the teacher whether your child has learned Arabic letters, reads from the Quran, has memorised any short surahs or has studied Tajweed—the rules used for correct Quran recitation.
    It is also helpful to mention if your child is shy, easily distracted, worried about mistakes or more comfortable in a particular language.
    The lesson usually begins with a short introduction
    The teacher may spend the first few minutes greeting your child and helping them feel comfortable.
    Some children begin speaking or reading immediately. Others need a little time before they feel ready. Both reactions are normal.
    The teacher should speak directly to the child, explain the lesson simply and give them enough time to answer.
    A trial is not only about what the child can read. It also helps the teacher understand how the child communicates, follows instructions and responds to support.
    The teacher listens to your child’s current level
    The activities used during the trial depend on the child’s age and previous experience.
    The teacher may check:
    recognition of Arabic letters and vowel marks;
    reading of simple words, lines or verses;
    pronunciation;
    surahs the child has already memorised;
    repeated difficulties;
    how much help the child needs;
    confidence when reading aloud.
    Not every child will complete every activity. A beginner learning letters needs a different trial from a child who already reads independently.
    The goal is not to cover as much material as possible. It is to understand where the child should begin and what kind of support may help.
    Your child experiences part of the teaching style
    A useful trial should include some teaching, not only assessment.
    The teacher may correct a word, explain a sound, practise a short line or ask the child to repeat something after listening.
    Notice how the correction is given.
    Does the teacher explain what needs to change? Does your child have time to try again? Does the teacher adjust the explanation when the child does not understand?
    Your child should begin to experience what a normal lesson with that teacher might feel like.
    The aim is not to see how much the child can finish. It is to see how clearly the teacher supports the child and how the child responds.
    Parent’s Trial Lesson Checklist
    You do not need to judge every small detail. Use these questions to notice the most important parts of the lesson.
    What to notice Question for the parent
    Communication Did the teacher speak clearly and respectfully to my child?
    Comfort Did my child feel safe enough to try after making a mistake?
    Level assessment Did the teacher listen before deciding what to teach?
    Pace Was the lesson too fast, too slow or suitable?
    Corrections Did my child understand what needed to change?
    Participation Did my child have enough time to read, answer and repeat?
    Language Could my child understand the teacher’s explanations?
    Next step Was it clear what my child should work on next?
    A child does not need to appear completely relaxed during the first meeting. Look instead for signs that the teacher is patient, attentive and able to respond to your child’s needs.
    Ask your child a few simple questions afterwards
    After the trial, give your child a moment to think before asking how it went.
    You can ask:
    Did you understand the teacher?
    Did you feel comfortable asking for help?
    Was the lesson too easy, too difficult or about right?
    Did you understand the corrections?
    Would you feel comfortable meeting this teacher again?
    Try not to ask only, “Did you like it?”
    A child may say no because they felt shy, found one task difficult or were tired that day. Their answers can still help you understand what felt comfortable and what may need to change.
    What happens after the trial?
    After the trial, the family should receive a simple explanation of the child’s starting point and a suggested next step.
    This may include:
    what the child can currently do;
    the main area that needs support;
    a suitable learning focus;
    whether the teaching language and pace were appropriate;
    the recommended next step.
    At Tarteel House, families are contacted within two days of the trial. There is no payment or commitment for attending the trial.
    When the family is ready to continue, they can review the available lesson packages and decide whether one is suitable.
    How Tarteel House trial lessons work
    Tarteel House offers free, one-to-one trial lessons for children aged 5–16.
    The trial lasts 40 minutes. The teacher is matched according to the child’s level, language needs, learning needs and schedule. Parents may also express a teacher preference.
    During the lesson, the teacher listens to the child’s current level and introduces part of the teaching approach. If the match does not feel suitable, the parent can request a different teacher.
    You can learn more about how Tarteel House lessons work or meet the teachers before booking.
    A trial should help you make a clearer decision
    A trial lesson should give you more than a general promise.
    It should help your child experience the teaching style and help you understand whether the communication, level and pace feel suitable.
    The lesson does not need to be perfect. You should simply leave with a clearer understanding of where your child is now and what the next step could be.
    """
)


class TrialLessonArticleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ARTICLE.read_text(encoding="utf-8") if ARTICLE.is_file() else ""
        cls.parser = ArticleParser()
        cls.parser.feed(cls.source)
        cls.parser.close()

    def test_clean_url_article_exists_and_contains_exact_approved_text(self):
        self.assertTrue(ARTICLE.is_file(), ARTICLE)
        hero_subs = [
            text
            for attrs, text in self.parser.paragraphs
            if "blog-post-hero__sub" in classes(attrs)
        ]
        actual = normalise(
            " ".join(
                self.parser.headings["h1"]
                + hero_subs
                + ["".join(self.parser.article_text_parts)]
            )
        )
        self.assertEqual(EXPECTED_ARTICLE_TEXT, actual)

    def test_semantic_headings_table_and_html_structure(self):
        tags = [tag for tag, _ in self.parser.start_tags]
        self.assertEqual([HEADLINE], self.parser.headings["h1"])
        self.assertEqual(1, tags.count("h1"))
        self.assertEqual(1, tags.count("table"))
        required_h2s = (
            "Before the trial: your child does not need to prepare perfectly",
            "The lesson usually begins with a short introduction",
            "The teacher listens to your child’s current level",
            "Your child experiences part of the teaching style",
            "Parent’s Trial Lesson Checklist",
            "Ask your child a few simple questions afterwards",
            "What happens after the trial?",
            "How Tarteel House trial lessons work",
            "A trial should help you make a clearer decision",
            "Meet the teacher before you decide",
        )
        self.assertEqual(list(required_h2s), self.parser.headings["h2"])

        wrappers = [
            attrs
            for tag, attrs in self.parser.start_tags
            if tag == "div" and "comparison-table-wrapper" in classes(attrs)
        ]
        self.assertEqual(1, len(wrappers))
        self.assertEqual("region", wrappers[0].get("role"))
        self.assertEqual("0", wrappers[0].get("tabindex"))
        self.assertEqual("trial-lesson-checklist-heading", wrappers[0].get("aria-labelledby"))
        tables = [attrs for tag, attrs in self.parser.start_tags if tag == "table"]
        self.assertEqual("trial-lesson-checklist-heading", tables[0].get("aria-labelledby"))

        expected_rows = (
            ("What to notice", "Question for the parent"),
            ("Communication", "Did the teacher speak clearly and respectfully to my child?"),
            ("Comfort", "Did my child feel safe enough to try after making a mistake?"),
            ("Level assessment", "Did the teacher listen before deciding what to teach?"),
            ("Pace", "Was the lesson too fast, too slow or suitable?"),
            ("Corrections", "Did my child understand what needed to change?"),
            ("Participation", "Did my child have enough time to read, answer and repeat?"),
            ("Language", "Could my child understand the teacher’s explanations?"),
            ("Next step", "Was it clear what my child should work on next?"),
        )
        actual_rows = tuple(tuple(cell[2] for cell in row) for row in self.parser.table_rows)
        self.assertEqual(expected_rows, actual_rows)
        self.assertTrue(all(cell[0] == "th" for cell in self.parser.table_rows[0]))
        self.assertTrue(all(cell[1].get("scope") == "col" for cell in self.parser.table_rows[0]))

        structure = StrictStructureParser()
        structure.feed(self.source)
        structure.close()
        self.assertEqual(["doctype html"], structure.doctypes)
        self.assertEqual([], structure.stack)
        ids = [attrs["id"] for _, attrs in self.parser.start_tags if attrs.get("id")]
        self.assertEqual(len(ids), len(set(ids)))
        for _, attrs in self.parser.start_tags:
            for referenced_id in attrs.get("aria-labelledby", "").split():
                self.assertIn(referenced_id, ids)

    def test_reviewer_cta_links_related_reading_and_runtime_modules(self):
        paragraphs = [text for _, text in self.parser.paragraphs]
        self.assertEqual(
            1,
            paragraphs.count("Reviewed by Fareshta Suroush, Tarteel House Quran Teacher"),
        )
        self.assertEqual(1, paragraphs.count("Reviewed: July 2026"))
        self.assertNotIn("Written by", self.source)
        links_by_text = {text: attrs.get("href") for text, attrs in self.parser.anchors}
        self.assertEqual("/pricing/", links_by_text.get("lesson packages"))
        self.assertEqual(
            "/how-it-works/", links_by_text.get("how Tarteel House lessons work")
        )
        self.assertEqual("/teachers/", links_by_text.get("meet the teachers"))
        self.assertEqual("/book-trial/", links_by_text.get("Book a Free Trial"))
        self.assertEqual(
            "/blog/online-quran-classes-for-kids-parents-look-for/",
            links_by_text.get("Online Quran Classes for Kids: What Parents Should Look For"),
        )
        self.assertEqual(
            "/blog/how-parents-can-track-their-childs-quran-progress/",
            links_by_text.get("How Parents Can Track Their Child’s Quran Progress"),
        )
        self.assertIn(
            "Book a free 40-minute trial so your child can read at their current level and experience a one-to-one lesson without payment or commitment.",
            paragraphs,
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

    def test_metadata_social_metadata_and_schema_match(self):
        self.assertIn(f"<title>{TITLE}</title>", self.source)
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
        properties = {
            attrs.get("property"): attrs.get("content")
            for tag, attrs in self.parser.start_tags
            if tag == "meta" and attrs.get("property")
        }
        names = {
            attrs.get("name"): attrs.get("content")
            for tag, attrs in self.parser.start_tags
            if tag == "meta" and attrs.get("name")
        }
        self.assertEqual(TITLE, properties.get("og:title"))
        self.assertEqual(CANONICAL, properties.get("og:url"))
        self.assertEqual(IMAGE_URL, properties.get("og:image"))
        self.assertEqual("1200", properties.get("og:image:width"))
        self.assertEqual("630", properties.get("og:image:height"))
        self.assertEqual(IMAGE_ALT, properties.get("og:image:alt"))
        self.assertEqual(TITLE, names.get("twitter:title"))
        self.assertEqual(IMAGE_URL, names.get("twitter:image"))

        postings = nodes_of_type(self.parser.json_ld, "BlogPosting")
        breadcrumbs = nodes_of_type(self.parser.json_ld, "BreadcrumbList")
        self.assertEqual(1, len(postings))
        self.assertEqual(1, len(breadcrumbs))
        posting = postings[0]
        self.assertEqual(HEADLINE, posting["headline"])
        self.assertEqual(DESCRIPTION, posting["description"])
        self.assertEqual("2026-07-14", posting["datePublished"])
        self.assertEqual("2026-07-14", posting["dateModified"])
        self.assertNotIn("author", posting)
        self.assertNotIn("reviewedBy", posting)
        self.assertEqual(CANONICAL, posting["mainEntityOfPage"]["@id"])
        self.assertEqual(
            {"@type": "ImageObject", "url": IMAGE_URL, "width": 1200, "height": 630},
            posting["image"],
        )
        self.assertEqual("Tarteel House", posting["publisher"]["name"])
        items = breadcrumbs[0]["itemListElement"]
        self.assertEqual(["Home", "Blog", HEADLINE], [item["name"] for item in items])
        self.assertEqual(CANONICAL, items[-1]["item"])

    def test_responsive_cover_files_and_markup_preserve_dimensions(self):
        for image in IMAGE_FILES:
            self.assertTrue(image.is_file(), image)
            self.assertGreater(image.stat().st_size, 0)
        dimensions = tuple(image_dimensions(image) for image in IMAGE_FILES)
        self.assertEqual(((1200, 630), (640, 336), (1200, 630)), dimensions)
        source_ratio = 1731 / 909
        for width, height in dimensions:
            self.assertLess(abs((width / height) - source_ratio), 0.001)
        self.assertIn(
            '<source type="image/webp" srcset="/assets/blog/free-online-quran-trial-lesson-cover-640.webp 640w, /assets/blog/free-online-quran-trial-lesson-cover-1200.webp 1200w" sizes="(max-width: 720px) calc(90vw - 2px), 638px" />',
            self.source,
        )
        self.assertIn(
            f'<img src="/assets/blog/free-online-quran-trial-lesson-cover.png" alt="{IMAGE_ALT}" width="1200" height="630" loading="eager" decoding="async" fetchpriority="high" />',
            self.source,
        )

    def test_blog_index_places_the_new_card_first(self):
        source = BLOG_INDEX.read_text(encoding="utf-8")
        grid_start = source.index('<div class="blog-grid">')
        first_card_start = source.index('<article class="blog-card">', grid_start)
        second_card_start = source.index('<article class="blog-card">', first_card_start + 1)
        first_card = source[first_card_start:second_card_start]
        self.assertIn(
            'href="/blog/free-online-quran-trial-lesson-parent-checklist/"', first_card
        )
        self.assertIn("What Happens in a Free Online Quran Trial Lesson?", first_card)
        self.assertIn(
            "Learn what your child can expect before, during and after a free online Quran trial lesson, with a practical checklist for parents.",
            first_card,
        )
        self.assertIn(
            "/assets/blog/free-online-quran-trial-lesson-cover-640.webp 640w", first_card
        )
        self.assertIn(
            "/assets/blog/free-online-quran-trial-lesson-cover-1200.webp 1200w", first_card
        )
        self.assertIn(f'alt="{IMAGE_ALT}"', first_card)
        self.assertIn('loading="eager"', first_card)
        self.assertIn('fetchpriority="high"', first_card)

        third_card_start = source.index('<article class="blog-card">', second_card_start + 1)
        previous_first_card = source[second_card_start:third_card_start]
        self.assertIn('/blog/help-children-memorize-short-surahs/', previous_first_card)
        self.assertIn('loading="lazy"', previous_first_card)
        self.assertNotIn('fetchpriority="high"', previous_first_card)

    def test_sitemap_and_scoped_related_link_include_the_canonical_once(self):
        tree = ET.parse(SITEMAP)
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = [node.text for node in tree.findall("sm:url/sm:loc", namespace)]
        self.assertEqual(1, locations.count(CANONICAL))

        source = RELATED_ARTICLE.read_text(encoding="utf-8")
        self.assertEqual(
            1,
            source.count('href="/blog/free-online-quran-trial-lesson-parent-checklist/"'),
        )
        self.assertIn(
            '>What happens during a free Quran trial lesson</a>', source
        )

    def test_all_required_local_targets_exist(self):
        required_targets = (
            "/pricing/",
            "/how-it-works/",
            "/teachers/",
            "/book-trial/",
            "/blog/online-quran-classes-for-kids-parents-look-for/",
            "/blog/how-parents-can-track-their-childs-quran-progress/",
        )
        for target in required_targets:
            self.assertTrue((ROOT / target.strip("/") / "index.html").is_file(), target)


if __name__ == "__main__":
    unittest.main()
