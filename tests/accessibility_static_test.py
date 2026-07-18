import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
STYLES = ROOT / "assets/css/styles.css"

PUBLIC_PAGES = (
    "404.html",
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
    "privacy-policy/index.html",
    "terms/index.html",
    "success/index.html",
)


def source(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def attributes(tag):
    return dict(re.findall(r'([:\w-]+)\s*=\s*["\']([^"\']*)["\']', tag))


def local_target_exists(href):
    path = urlsplit(href).path
    if not path or path == "/":
        return (ROOT / "index.html").is_file()
    target = ROOT / path.lstrip("/")
    if path.endswith("/"):
        target = target / "index.html"
    return target.is_file()


def relative_luminance(hex_color):
    channels = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first, second):
    lighter, darker = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


class AccessibilityStaticTests(unittest.TestCase):
    def test_every_page_has_language_viewport_skip_link_and_main_landmark(self):
        for relative in PUBLIC_PAGES:
            page = source(relative)
            self.assertRegex(page, r'<html\s+lang="en">', relative)
            self.assertIn('name="viewport"', page, relative)
            self.assertIn('<a class="skip-link" href="#main-content">Skip to main content</a>', page, relative)
            self.assertEqual(1, page.count('<main id="main-content">'), relative)
            self.assertEqual(1, page.count('</main>'), relative)

    def test_every_page_has_one_h1_and_no_heading_level_jumps(self):
        for relative in PUBLIC_PAGES:
            page = source(relative)
            headings = [int(level) for level in re.findall(r"<h([1-6])\b", page, flags=re.I)]
            self.assertEqual(1, headings.count(1), relative)
            for previous, current in zip(headings, headings[1:]):
                self.assertLessEqual(current - previous, 1, f"{relative}: h{previous} to h{current}")

    def test_ids_are_unique_and_skip_target_exists(self):
        for relative in PUBLIC_PAGES:
            page = source(relative)
            ids = re.findall(r'\bid="([^"]+)"', page)
            self.assertEqual(len(ids), len(set(ids)), relative)
            self.assertIn("main-content", ids, relative)

    def test_buttons_have_accessible_names_and_explicit_types(self):
        for relative in PUBLIC_PAGES:
            page = source(relative)
            for match in re.finditer(r"<button\b([^>]*)>(.*?)</button>", page, flags=re.I | re.S):
                opening = f"<button{match.group(1)}>"
                attrs = attributes(opening)
                text = " ".join(re.sub(r"<[^>]+>", " ", match.group(2)).split())
                self.assertEqual("button", attrs.get("type"), f"{relative}: {opening}")
                self.assertTrue(attrs.get("aria-label") or text, f"{relative}: unnamed button")

    def test_images_reserve_space_and_have_alt_attributes(self):
        for relative in PUBLIC_PAGES:
            page = source(relative)
            for image in re.findall(r"<img\b[^>]*>", page, flags=re.I):
                attrs = attributes(image)
                self.assertIn("alt", attrs, f"{relative}: {image}")
                self.assertRegex(attrs.get("width", ""), r"^\d+$", f"{relative}: {image}")
                self.assertRegex(attrs.get("height", ""), r"^\d+$", f"{relative}: {image}")

    def test_all_internal_links_resolve_to_local_files(self):
        for relative in PUBLIC_PAGES:
            page = source(relative)
            for href in re.findall(r'<a\b[^>]*\bhref="([^"]+)"', page, flags=re.I):
                if href.startswith("#"):
                    continue
                self.assertFalse(href.startswith(("http://", "https://", "mailto:", "tel:")), f"{relative}: {href}")
                self.assertTrue(local_target_exists(href), f"{relative}: unresolved {href}")

    def test_trial_page_has_no_interactive_personal_data_controls(self):
        trial = source("book-trial/index.html")
        self.assertNotRegex(trial, r"<(?:form|input|select|textarea)\b")
        self.assertIn("Online trial booking is being prepared and is not yet open.", trial)

    def test_pricing_disclosures_are_native_and_pricing_has_no_commercial_controls(self):
        pricing = source("pricing/index.html")
        main = re.search(r'<main id="main-content">.*?</main>', pricing, re.S).group(0)
        self.assertEqual(11, pricing.count("<details"))
        self.assertEqual(11, pricing.count("<summary>"))
        self.assertNotRegex(main, r"<(?:form|input|select|textarea|button)\b")
        self.assertNotRegex(main, r'role=["\'](?:button|tab|tabpanel)["\']')

    def test_public_copy_avoids_internal_migration_and_approval_language(self):
        internal_phrases = (
            "approved teacher",
            "approved video",
            "retained unchanged",
            "has been invented",
        )
        for relative in PUBLIC_PAGES:
            page = source(relative).lower()
            for phrase in internal_phrases:
                self.assertNotIn(phrase, page, relative)

    def test_css_keeps_focus_contrast_touch_targets_and_reduced_motion(self):
        css = source("assets/css/styles.css")
        for token in ("#2b87d5", "#173a5e", "#ffffff", "#eef5fc", "#f5f7fa", "#f4b400"):
            self.assertIn(token, css.lower())
        self.assertIn(":focus-visible", css)
        self.assertIn("outline: 3px solid var(--focus)", css)
        self.assertIn("--focus: #173a5e;", css.lower())
        self.assertRegex(
            css,
            re.compile(r":focus-visible\s*\{[^}]*box-shadow:\s*0 0 0 6px var\(--gold\)", re.S),
        )
        for selector in (r"\.btn--primary", r"\.nav__mark", r"\.process-list li::before"):
            self.assertRegex(
                css,
                re.compile(selector + r"[^\{]*\{[^}]*background:\s*var\(--blue-dark\)", re.S),
            )
        self.assertGreaterEqual(contrast_ratio("#ffffff", "#1e6fb5"), 4.5)
        self.assertGreaterEqual(contrast_ratio("#173a5e", "#ffffff"), 3.0)
        self.assertGreaterEqual(contrast_ratio("#f4b400", "#173a5e"), 3.0)
        self.assertIn("min-height: 3rem", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("overflow-x: auto", css)
        self.assertNotIn("fonts.googleapis.com", css)
        self.assertNotRegex(css, r"@import\s+url")


if __name__ == "__main__":
    unittest.main()
