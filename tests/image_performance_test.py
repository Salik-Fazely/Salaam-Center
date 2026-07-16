from html.parser import HTMLParser
from pathlib import Path
import struct
import unittest


ROOT = Path(__file__).resolve().parents[1]

INDEX_IMAGES = [
    (
        "free-online-quran-trial-lesson-cover",
        "A child attending a one-to-one online Quran trial lesson with a female teacher",
    ),
    (
        "help-children-memorize-short-surahs",
        "Maryam reviews a short surah at a calm home desk with a Qur'an and practice notebook.",
    ),
    (
        "online-quran-classes-for-kids-parents-look-for",
        "Adam joins an online Qur'an lesson with Teacher Amina on a laptop in a calm home setting.",
    ),
    (
        "one-to-one-vs-group-quran-classes",
        "Adam receives focused one-to-one Qur'an guidance from Teacher Amina during an online lesson.",
    ),
    (
        "track-child-quran-progress",
        "A parent reviews a Qur'an progress update while Maryam studies quietly at home.",
    ),
]

ARTICLE_IMAGES = {
    "blog/help-children-memorize-short-surahs/index.html": INDEX_IMAGES[1],
    "blog/online-quran-classes-for-kids-parents-look-for/index.html": INDEX_IMAGES[2],
    "blog/one-to-one-quran-classes-vs-group-classes-for-children/index.html": INDEX_IMAGES[3],
    "blog/how-parents-can-track-their-childs-quran-progress/index.html": INDEX_IMAGES[4],
}

REQUIRED_PAGES = [
    "index.html",
    "blog/index.html",
    *ARTICLE_IMAGES,
    "teachers/index.html",
    "pricing/index.html",
    "book-trial/index.html",
]

INDEX_SIZES = (
    "(max-width: 720px) calc(90vw - 2px), "
    "(max-width: 1160px) calc(45vw - 14px), 526px"
)
ARTICLE_SIZES = "(max-width: 720px) calc(90vw - 2px), 638px"


class ImageMarkupParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self._sources = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "picture":
            self._sources = []
        elif tag == "source" and self._sources is not None:
            self._sources.append(values)
        elif tag == "img":
            self.images.append(
                {"attrs": values, "sources": list(self._sources or [])}
            )

    def handle_endtag(self, tag):
        if tag == "picture":
            self._sources = None


def parse_images(relative_path):
    parser = ImageMarkupParser()
    parser.feed((ROOT / relative_path).read_text(encoding="utf-8"))
    return parser.images


def webp_dimensions(path):
    data = path.read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise AssertionError(f"Not a WebP file: {path}")
    chunk = data[12:16]
    if chunk == b"VP8 ":
        return (
            struct.unpack_from("<H", data, 26)[0] & 0x3FFF,
            struct.unpack_from("<H", data, 28)[0] & 0x3FFF,
        )
    if chunk == b"VP8L":
        bits = int.from_bytes(data[21:25], "little")
        return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
    if chunk == b"VP8X":
        return (
            int.from_bytes(data[24:27], "little") + 1,
            int.from_bytes(data[27:30], "little") + 1,
        )
    raise AssertionError(f"Unsupported WebP chunk {chunk!r}: {path}")


def find_image(images, src):
    matches = [image for image in images if image["attrs"].get("src") == src]
    if len(matches) != 1:
        raise AssertionError(f"Expected one image with src={src!r}, found {len(matches)}")
    return matches[0]


class ImagePerformanceTest(unittest.TestCase):
    def test_webp_variants_are_correctly_sized_and_meaningfully_smaller(self):
        for stem, _ in INDEX_IMAGES:
            original = ROOT / "assets" / "blog" / f"{stem}.png"
            for width, height in ((640, 336), (1200, 630)):
                variant = ROOT / "assets" / "blog" / f"{stem}-{width}.webp"
                self.assertTrue(variant.is_file(), variant)
                self.assertEqual(webp_dimensions(variant), (width, height), variant)
                self.assertLess(variant.stat().st_size, original.stat().st_size * 0.4)

    def test_blog_index_uses_responsive_webp_with_one_high_priority_image(self):
        images = parse_images("blog/index.html")
        for index, (stem, alt) in enumerate(INDEX_IMAGES):
            src = f"/assets/blog/{stem}.png"
            image = find_image(images, src)
            attrs = image["attrs"]
            self.assertEqual(attrs.get("alt"), alt)
            self.assertEqual((attrs.get("width"), attrs.get("height")), ("1200", "630"))
            self.assertEqual(attrs.get("decoding"), "async")
            self.assertEqual(attrs.get("loading"), "eager" if index == 0 else "lazy")
            self.assertEqual(attrs.get("fetchpriority"), "high" if index == 0 else None)
            self.assertEqual(
                image["sources"],
                [
                    {
                        "type": "image/webp",
                        "srcset": (
                            f"/assets/blog/{stem}-640.webp 640w, "
                            f"/assets/blog/{stem}-1200.webp 1200w"
                        ),
                        "sizes": INDEX_SIZES,
                    }
                ],
            )

    def test_article_covers_use_responsive_high_priority_webp(self):
        for page, (stem, alt) in ARTICLE_IMAGES.items():
            src = f"/assets/blog/{stem}.png"
            image = find_image(parse_images(page), src)
            attrs = image["attrs"]
            self.assertEqual(attrs.get("alt"), alt)
            self.assertEqual((attrs.get("width"), attrs.get("height")), ("1200", "630"))
            self.assertEqual(attrs.get("loading"), "eager")
            self.assertEqual(attrs.get("decoding"), "async")
            self.assertEqual(attrs.get("fetchpriority"), "high")
            self.assertEqual(
                image["sources"],
                [
                    {
                        "type": "image/webp",
                        "srcset": (
                            f"/assets/blog/{stem}-640.webp 640w, "
                            f"/assets/blog/{stem}-1200.webp 1200w"
                        ),
                        "sizes": ARTICLE_SIZES,
                    }
                ],
            )

    def test_required_pages_reserve_logo_space_and_defer_only_footer_logo(self):
        for page in REQUIRED_PAGES:
            images = parse_images(page)
            header = find_image(images, "/assets/logo/tarteel-house.svg")["attrs"]
            footer = find_image(images, "/assets/logo/tarteel-house-reversed.svg")["attrs"]
            self.assertEqual((header.get("width"), header.get("height")), ("276", "175"), page)
            self.assertIsNone(header.get("loading"), page)
            self.assertEqual((footer.get("width"), footer.get("height")), ("276", "175"), page)
            self.assertEqual(footer.get("loading"), "lazy", page)
            self.assertEqual(footer.get("decoding"), "async", page)

    def test_only_blog_pages_have_one_high_priority_image(self):
        blog_pages = {"blog/index.html", *ARTICLE_IMAGES}
        for page in REQUIRED_PAGES:
            images = parse_images(page)
            high_priority = [
                image for image in images if image["attrs"].get("fetchpriority") == "high"
            ]
            self.assertEqual(len(high_priority), 1 if page in blog_pages else 0, page)
            for image in high_priority:
                self.assertNotEqual(image["attrs"].get("loading"), "lazy", page)


if __name__ == "__main__":
    unittest.main()
