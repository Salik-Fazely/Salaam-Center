import html
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CORE_PAGES = (
    "index.html",
    "our-approach/index.html",
    "programs/index.html",
    "programs/quran/index.html",
    "programs/dari-persian/index.html",
    "programs/afghan-culture-islamic-ethics/index.html",
    "teachers/index.html",
    "how-it-works/index.html",
    "pricing/index.html",
    "about/index.html",
    "book-trial/index.html",
    "contact/index.html",
    "privacy-policy/index.html",
    "terms/index.html",
    "success/index.html",
    "404.html",
)
NOINDEX_PAGES = {"success/index.html", "404.html"}

EXPECTED_NAVIGATION = (
    ("Home", "/"),
    ("Our Approach", "/our-approach/"),
    ("Programs", "/programs/"),
    ("Teachers", "/teachers/"),
    ("How It Works", "/how-it-works/"),
    ("Pricing", "/pricing/"),
    ("About", "/about/"),
)

EXPECTED_TEACHERS = {
    "Farkhonda Jami": (
        "TURKISH &middot; PERSIAN",
        "2 years teaching Tajweed and Tafsir",
        "iUMB3pKzS_A",
    ),
    "Foruhar Rahmani": (
        "PERSIAN &middot; ENGLISH",
        "2 years teaching Tajweed",
        "iurgyXOzqFU",
    ),
    "Fareshta Suroush": (
        "PERSIAN &middot; ENGLISH &middot; TURKISH",
        "2 years teaching Tajweed",
        "OtaIpKZpbMM",
    ),
    "Sadiah Hamid": (
        "ENGLISH &middot; ARABIC &middot; TURKISH &middot; PERSIAN",
        "6 years teaching Tajweed, Hifz, and Quranic recitation",
        "fOzc2cM5Twk",
    ),
}

STUDENT_VIDEO_IDS = {"to3h-qq7_FM", "6WxiPdZNcCY"}


def source(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def visible_text(relative_path):
    value = re.sub(r"<script\b.*?</script>", " ", source(relative_path), flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(value).split())


def public_html_files():
    return tuple(ROOT / relative_path for relative_path in CORE_PAGES)


class HeadAndNavigationParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.capture_title = False
        self.title_parts = []
        self.metas = []
        self.links = []
        self.nav_depth = 0
        self.nav_links = []
        self.current_nav_link = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "title":
            self.capture_title = True
        elif tag == "meta":
            self.metas.append(attributes)
        elif tag == "link":
            self.links.append(attributes)
        elif tag == "nav":
            self.nav_depth += 1
        elif tag == "a" and self.nav_depth:
            self.current_nav_link = {"attrs": attributes, "text": []}
            self.nav_links.append(self.current_nav_link)

    def handle_endtag(self, tag):
        if tag == "title":
            self.capture_title = False
        elif tag == "a":
            self.current_nav_link = None
        elif tag == "nav":
            self.nav_depth -= 1

    def handle_data(self, data):
        if self.capture_title:
            self.title_parts.append(data)
        if self.current_nav_link is not None:
            self.current_nav_link["text"].append(data)

    @property
    def title(self):
        return " ".join("".join(self.title_parts).split())


def parse(relative_path):
    parser = HeadAndNavigationParser()
    parser.feed(source(relative_path))
    parser.close()
    return parser


class BrandAndArchitectureTests(unittest.TestCase):
    def test_all_approved_core_pages_exist(self):
        for relative_path in CORE_PAGES:
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)

    def test_shared_navigation_contains_only_the_approved_primary_links(self):
        parser = parse("index.html")
        navigation = []
        for item in parser.nav_links:
            classes = set(item["attrs"].get("class", "").split())
            if "nav__link" not in classes:
                continue
            navigation.append((" ".join("".join(item["text"]).split()), item["attrs"].get("href")))
        self.assertEqual(EXPECTED_NAVIGATION, tuple(navigation))
        self.assertIn("Pricing", visible_text("index.html"))

    def test_public_pages_use_salaam_center_without_inherited_business_identity(self):
        forbidden = (
            "Tarteel House",
            "tarteelhouse.com",
            "hello@tarteelhouse.com",
            "salaamcenter.org",
        )
        for path in public_html_files():
            page = path.read_text(encoding="utf-8")
            self.assertIn("Salaam Center", page, str(path.relative_to(ROOT)))
            for value in forbidden:
                self.assertNotIn(value, page, str(path.relative_to(ROOT)))

    def test_page_titles_are_unique_and_salaam_center_specific(self):
        titles = {}
        for relative_path in CORE_PAGES:
            title = parse(relative_path).title
            self.assertIn("Salaam Center", title, relative_path)
            self.assertNotIn(title, titles, relative_path)
            titles[title] = relative_path


class IntegrationAndMetadataSafetyTests(unittest.TestCase):
    def test_indexable_pages_are_open_while_status_and_error_pages_remain_noindex(self):
        for path in public_html_files():
            relative_path = path.relative_to(ROOT).as_posix()
            parser = parse(relative_path)
            robots = [
                item.get("content", "").lower().replace(" ", "")
                for item in parser.metas
                if item.get("name", "").lower() == "robots"
            ]
            self.assertEqual(
                ["noindex,nofollow"] if relative_path in NOINDEX_PAGES else [],
                robots,
                relative_path,
            )
            canonicals = [
                item.get("href")
                for item in parser.links
                if "canonical" in item.get("rel", "").lower().split()
            ]
            route = "/" if relative_path == "index.html" else (
                "/404.html" if relative_path == "404.html" else f"/{relative_path.removesuffix('index.html')}"
            )
            self.assertEqual([f"https://salaam.center{route}"], canonicals, relative_path)

    def test_no_inherited_analytics_or_conversion_code_remains_executable(self):
        executable = "\n".join(
            path.read_text(encoding="utf-8")
            for pattern in ("*.html", "*.js")
            for path in ROOT.rglob(pattern)
        )
        for value in (
            "G-ZVLW7QGYR1",
            "googletagmanager.com/gtag",
            "gtag(",
            "conversion_event",
        ):
            self.assertNotIn(value, executable)

    def test_only_the_approved_client_side_whatsapp_contact_destination_exists(self):
        public = "\n".join(path.read_text(encoding="utf-8") for path in public_html_files())
        trial = source("book-trial/index.html")
        self.assertEqual(1, len(re.findall(r"<form\b", public)))
        self.assertIn('data-whatsapp-handoff="true"', trial)
        self.assertNotRegex(trial, r'<form\b[^>]+action=')
        self.assertNotRegex(trial, r'<form\b[^>]+method=["\']?post')
        self.assertIn("https://wa.me/34614401172", public)
        for url in re.findall(r"https://wa\.me/[^\s\"'<>]+", public):
            self.assertEqual("https://wa.me/34614401172", url)
        for value in ("script.google.com", "api.whatsapp.com", "mailto:", "tel:"):
            self.assertNotIn(value, public)
        self.assertFalse((ROOT / "apps-script/Code.gs").exists())

    def test_no_production_or_deployment_files_are_present(self):
        self.assertFalse((ROOT / "CNAME").exists())
        self.assertTrue((ROOT / "sitemap.xml").is_file())
        self.assertFalse((ROOT / "pricing.html").exists())
        workflows = ROOT / ".github/workflows"
        self.assertFalse(workflows.exists() and any(workflows.iterdir()))


class ProgramAndProductionContentTests(unittest.TestCase):
    def test_launch_programs_and_eligibility_match_approved_facts(self):
        expected = {
            "programs/quran/index.html": (
                "Private one-to-one",
                "Children and teenagers aged 5–16",
                "Women of any age",
                "40-minute lessons",
            ),
            "programs/dari-persian/index.html": (
                "Private one-to-one",
                "Children and teenagers aged 5–16",
                "Women of any age",
                "40-minute lessons",
            ),
            "programs/afghan-culture-islamic-ethics/index.html": (
                "Group classes",
                "Children and teenagers aged 5–16",
                "40-minute lessons",
            ),
        }
        for relative_path, facts in expected.items():
            page = visible_text(relative_path)
            for fact in facts:
                self.assertIn(fact, page, relative_path)

    def test_only_the_three_approved_launch_programs_are_present(self):
        public = " ".join(visible_text(path.relative_to(ROOT).as_posix()) for path in public_html_files())
        for name in ("Quran", "Dari/Persian", "Afghan Culture & Islamic Ethics"):
            self.assertIn(name, public)
        self.assertNotIn("Pashto", public)
        self.assertNotRegex(
            visible_text("programs/afghan-culture-islamic-ethics/index.html"),
            r"€\s*\d|\d\s*€",
        )

    def test_trial_page_prepares_whatsapp_locally_without_collecting_child_contact_data(self):
        page = source("book-trial/index.html")
        text = visible_text("book-trial/index.html")
        self.assertIn("Continue in WhatsApp", text)
        self.assertIn("prepared locally", text)
        self.assertIn('data-whatsapp-handoff="true"', page)
        self.assertNotRegex(page, r'<form\b[^>]+action=')
        self.assertNotRegex(page, r'(?i)name="(?:email|phone|learner_(?:name|first_name|surname))"')

    def test_submission_status_never_claims_a_request_was_sent(self):
        text = visible_text("success/index.html")
        self.assertIn("Continue your conversation in WhatsApp", text)
        self.assertIn("cannot confirm", text)
        for claim in ("Thank you", "successfully submitted", "we received your request", "message sent", "trial confirmed"):
            self.assertNotIn(claim.lower(), text.lower())

    def test_privacy_and_terms_are_final_operational_notices(self):
        privacy = visible_text("privacy-policy/index.html")
        terms = visible_text("terms/index.html")
        for value in (
            "Privacy Policy",
            "Salaam Center",
            "Sabadell, Barcelona",
            "+34 614 401 172",
            "does not submit or store",
            "locally in your browser",
            "22 July 2026",
        ):
            self.assertIn(value, privacy)
        for value in (
            "Terms and Conditions",
            "Salaam Center",
            "Sabadell, Barcelona",
            "+34 614 401 172",
            "A WhatsApp message is an enquiry",
            "consumer cancellation, refund and withdrawal rights",
            "22 July 2026",
        ):
            self.assertIn(value.casefold(), terms.casefold())
        for page in (privacy, terms):
            self.assertNotRegex(page, r"(?i)pre-?launch|not the final|\bpending\b|formspree")


class TeacherAndMediaPreservationTests(unittest.TestCase):
    def test_all_teacher_names_profile_facts_and_video_ids_are_preserved(self):
        teachers = source("teachers/index.html")
        for name, (languages, experience, video_id) in EXPECTED_TEACHERS.items():
            self.assertEqual(1, teachers.count(f'>{name}<'), name)
            self.assertIn(languages, teachers, name)
            self.assertIn(experience, teachers, name)
            self.assertIn(f'data-youtube-id="{video_id}"', teachers, name)
            self.assertIn(f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg', teachers, name)

    def test_student_video_ids_urls_and_accessible_labels_are_preserved(self):
        homepage = source("index.html")
        for index, video_id in enumerate(sorted(STUDENT_VIDEO_IDS), start=1):
            self.assertIn(f'data-youtube-id="{video_id}"', homepage)
            self.assertIn(f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg', homepage)
        self.assertIn('aria-label="Play student message 1"', homepage)
        self.assertIn('aria-label="Play student message 2"', homepage)

    def test_video_player_privacy_focus_and_duplicate_activation_guards_remain(self):
        script = source("assets/js/main.js")
        self.assertIn("https://www.youtube-nocookie.com/embed/", script)
        self.assertIn("if (isActivated) return", script)
        self.assertRegex(
            script,
            re.compile(r"requestAnimationFrame\s*\(.*?iframe\.focus", re.S),
        )
        self.assertNotIn("https://www.youtube.com/embed/", script)


if __name__ == "__main__":
    unittest.main()
