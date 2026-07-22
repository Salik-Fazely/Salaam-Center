import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_JS = ROOT / "assets/js/main.js"
STYLES = ROOT / "assets/css/styles.css"
HOMEPAGE = ROOT / "index.html"
TEACHERS = ROOT / "teachers/index.html"
PRIVACY = ROOT / "privacy-policy/index.html"

EXPECTED_VIDEO_IDS = {
    "to3h-qq7_FM",
    "6WxiPdZNcCY",
    "iUMB3pKzS_A",
    "iurgyXOzqFU",
    "OtaIpKZpbMM",
    "fOzc2cM5Twk",
}

EXPECTED_TITLES = {
    "to3h-qq7_FM": "Student message 1",
    "6WxiPdZNcCY": "Student message 2",
    "iUMB3pKzS_A": "Farkhonda Jami lesson sample",
    "iurgyXOzqFU": "Foruhar Rahmani lesson sample",
    "OtaIpKZpbMM": "Fareshta Suroush lesson sample",
    "fOzc2cM5Twk": "Sadiah Hamid lesson sample",
}

EXPECTED_LABELS = {
    "to3h-qq7_FM": "Play student message 1",
    "6WxiPdZNcCY": "Play student message 2",
    "iUMB3pKzS_A": "Play Farkhonda Jami lesson sample",
    "iurgyXOzqFU": "Play Foruhar Rahmani lesson sample",
    "OtaIpKZpbMM": "Play Fareshta Suroush lesson sample",
    "fOzc2cM5Twk": "Play Sadiah Hamid lesson sample",
}


def source(path):
    return path.read_text(encoding="utf-8")


class VideoButtonParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.controls = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "button" and "data-youtube-id" in attributes:
            self.controls.append(attributes)


def controls(path):
    parser = VideoButtonParser()
    parser.feed(source(path))
    parser.close()
    return parser.controls


class VideoPrivacyAccessibilityTests(unittest.TestCase):
    def test_shared_player_uses_only_the_privacy_enhanced_embed_domain(self):
        script = source(MAIN_JS)
        self.assertIn("https://www.youtube-nocookie.com/embed/", script)
        self.assertNotIn("https://www.youtube.com/embed/", script)

    def test_no_iframe_exists_before_a_video_is_activated(self):
        for page in (HOMEPAGE, TEACHERS):
            self.assertNotRegex(source(page), r"<iframe\b", str(page))

    def test_all_six_approved_video_ids_remain(self):
        found = {item["data-youtube-id"] for item in controls(HOMEPAGE) + controls(TEACHERS)}
        self.assertEqual(EXPECTED_VIDEO_IDS, found)

    def test_each_page_has_unique_descriptive_video_names(self):
        for page in (HOMEPAGE, TEACHERS):
            items = controls(page)
            ids = [item["data-youtube-id"] for item in items]
            labels = [item.get("aria-label") for item in items]
            titles = [item.get("data-youtube-title") for item in items]
            self.assertEqual(len(ids), len(set(ids)), str(page))
            self.assertEqual(len(labels), len(set(labels)), str(page))
            self.assertEqual(len(titles), len(set(titles)), str(page))
            for item in items:
                video_id = item["data-youtube-id"]
                self.assertEqual(EXPECTED_TITLES[video_id], item.get("data-youtube-title"))
                self.assertEqual(EXPECTED_LABELS[video_id], item.get("aria-label"))

    def test_student_video_labels_and_captions_are_preserved(self):
        homepage = source(HOMEPAGE)
        for value in (
            "A student shares appreciation",
            "A short message of appreciation from a student sharing their learning experience.",
            "Thanks from a young learner",
            "A student shares thanks and happiness about their Quran learning journey.",
        ):
            self.assertIn(value, homepage)

    def test_generated_iframe_is_named_and_receives_focus(self):
        script = source(MAIN_JS)
        self.assertRegex(script, r"iframe\.title\s*=\s*title")
        self.assertRegex(script, re.compile(r"requestAnimationFrame\s*\(.*?iframe\.focus", re.S))
        css = source(STYLES)
        self.assertIn(".youtube-inline-player:focus", css)
        self.assertIn(".youtube-inline-player.has-focus", css)

    def test_player_validates_data_and_prevents_duplicate_activation(self):
        script = source(MAIN_JS)
        self.assertRegex(script, r"\^\[A-Za-z0-9_-\]\{11\}\$")
        self.assertIn("if (isActivated) return", script)
        self.assertIn("!title", script)

    def test_final_privacy_notice_describes_thumbnail_and_player_behavior_accurately(self):
        privacy = source(PRIVACY)
        self.assertIn("Pages with video samples use YouTube-hosted thumbnails.", privacy)
        self.assertIn("A privacy-enhanced YouTube player is created only after you choose to play a video.", privacy)
        lower = privacy.lower()
        for unsupported in (
            "youtube sets no cookies",
            "youtube does not set cookies",
            "youtube collects no data",
            "no data is collected by youtube",
        ):
            self.assertNotIn(unsupported, lower)


if __name__ == "__main__":
    unittest.main()
