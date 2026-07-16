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


def video_controls(path):
    parser = VideoButtonParser()
    parser.feed(source(path))
    parser.close()
    return parser.controls


class VideoPrivacyAccessibilityTests(unittest.TestCase):
    def test_shared_player_uses_only_the_privacy_enhanced_embed_domain(self):
        script = source(MAIN_JS)
        self.assertIn("https://www.youtube-nocookie.com/embed/", script)
        self.assertNotIn("https://www.youtube.com/embed/", script)

        for page in ROOT.rglob("index.html"):
            self.assertNotIn("https://www.youtube.com/embed/", source(page), str(page))

    def test_no_iframe_is_present_before_a_video_is_activated(self):
        for page in (HOMEPAGE, TEACHERS):
            self.assertNotRegex(source(page), r"<iframe\b", str(page))
        self.assertIn("trigger.addEventListener('click'", source(MAIN_JS))

    def test_all_six_expected_video_ids_remain_in_video_controls(self):
        controls = video_controls(HOMEPAGE) + video_controls(TEACHERS)
        self.assertEqual(EXPECTED_VIDEO_IDS, {item["data-youtube-id"] for item in controls})

    def test_each_page_has_unique_descriptive_video_names(self):
        for page in (HOMEPAGE, TEACHERS):
            controls = video_controls(page)
            labels = [item.get("aria-label") for item in controls]
            titles = [item.get("data-youtube-title") for item in controls]
            self.assertNotIn(None, labels, str(page))
            self.assertNotIn(None, titles, str(page))
            self.assertEqual(len(labels), len(set(labels)), str(page))
            self.assertEqual(len(titles), len(set(titles)), str(page))
            for item in controls:
                video_id = item["data-youtube-id"]
                self.assertEqual(EXPECTED_TITLES[video_id], item["data-youtube-title"])
                self.assertEqual(EXPECTED_LABELS[video_id], item["aria-label"])

    def test_student_video_labels_are_distinguishable(self):
        student_controls = {
            item["data-youtube-id"]: item
            for item in video_controls(HOMEPAGE)
            if item["data-youtube-id"] in {"to3h-qq7_FM", "6WxiPdZNcCY"}
        }
        self.assertEqual("Play student message 1", student_controls["to3h-qq7_FM"]["aria-label"])
        self.assertEqual("Play student message 2", student_controls["6WxiPdZNcCY"]["aria-label"])

    def test_generated_iframe_reuses_the_required_descriptive_title_and_receives_focus(self):
        script = source(MAIN_JS)
        self.assertRegex(script, r"title\s*=\s*trigger\.dataset\.youtubeTitle")
        self.assertRegex(script, r"iframe\.title\s*=\s*title")
        self.assertRegex(
            script,
            re.compile(r"requestAnimationFrame\s*\(.*?iframe\.focus", re.DOTALL),
        )
        self.assertIn(".youtube-inline-player:focus", source(STYLES))
        self.assertIn(".youtube-inline-player.has-focus", source(STYLES))

    def test_player_validates_required_video_data_before_replacement(self):
        script = source(MAIN_JS)
        self.assertRegex(script, r"\^\[A-Za-z0-9_-\]\{11\}\$")
        self.assertNotIn("|| 'Video message'", script)
        self.assertIn("if (isActivated) return", script)

    def test_privacy_policy_describes_activation_without_unsupported_claims(self):
        privacy = source(PRIVACY)
        self.assertIn(
            "YouTube video players load only after you choose to play a video, and the site uses YouTube&rsquo;s privacy-enhanced embed domain.",
            privacy,
        )
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
