import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "partials/header.html"
STYLES = ROOT / "assets/css/styles.css"
MAIN_JS = ROOT / "assets/js/main.js"


def source(path):
    return path.read_text(encoding="utf-8")


class MobileHeaderStaticTests(unittest.TestCase):
    def test_header_uses_the_accessible_menu_trigger_contract(self):
        header = source(HEADER)
        self.assertIn('id="nav-menu"', header)
        self.assertIn('id="nav-toggle"', header)
        self.assertIn('type="button"', header)
        self.assertIn('aria-controls="nav-menu"', header)
        self.assertIn('aria-expanded="false"', header)
        self.assertIn('aria-label="Open navigation menu"', header)

    def test_trial_cta_accessible_name_comes_from_its_visible_label(self):
        header = source(HEADER)
        cta = re.search(r'<a href="/book-trial/" class="btn btn--primary nav__cta"([^>]*)>', header)
        self.assertIsNotNone(cta)
        self.assertNotIn("aria-label", cta.group(1))
        self.assertRegex(
            header,
            r'<a href="/book-trial/" class="btn btn--primary nav__cta">\s*Book a Free Trial\s*</a>',
        )

    def test_mobile_runtime_hides_inert_links_and_manages_focus(self):
        script = source(MAIN_JS)
        self.assertIn("window.matchMedia('(max-width: 1023px)')", script)
        self.assertIn("navMenu.hidden = isClosedMobile", script)
        self.assertIn("navMenu.inert = isClosedMobile", script)
        self.assertIn("navMenu.toggleAttribute('inert', isClosedMobile)", script)
        self.assertIn("navMenu.querySelector('a[href]')?.focus()", script)
        self.assertIn("event.key !== 'Escape'", script)
        self.assertIn("navToggle.focus()", script)
        self.assertIn("navMenu.classList.add('is-enhanced')", script)
        self.assertIn("navToggle.classList.add('is-enhanced')", script)

    def test_mobile_css_keeps_the_cta_and_menu_button_as_touch_targets(self):
        css = source(STYLES)
        self.assertIn("@media (max-width: 1023px)", css)
        self.assertIn(".nav__links.is-enhanced.is-open", css)
        self.assertIn(".nav__toggle", css)
        self.assertIn("width: 3rem", css)
        self.assertIn("height: 3rem", css)
        self.assertIn("min-height: 3rem", css)

    def test_navigation_remains_available_without_javascript(self):
        css = source(STYLES)
        tablet_rules = css.split("@media (max-width: 1023px)", 1)[1].split(
            "@media (max-width: 760px)", 1
        )[0]
        fallback = re.search(r"\n\s*\.nav__links\s*\{([^}]*)\}", tablet_rules, re.S)
        enhanced = re.search(r"\.nav__links\.is-enhanced\s*\{([^}]*)\}", tablet_rules, re.S)
        enhanced_toggle = re.search(r"\.nav__toggle\.is-enhanced\s*\{([^}]*)\}", tablet_rules, re.S)
        self.assertIsNotNone(fallback)
        self.assertIn("display: flex", fallback.group(1))
        self.assertNotIn("display: none", fallback.group(1))
        self.assertIsNotNone(enhanced)
        self.assertIn("display: none", enhanced.group(1))
        self.assertIsNotNone(enhanced_toggle)
        self.assertIn("display: flex", enhanced_toggle.group(1))

    def test_tablet_footer_reflows_before_its_columns_can_overflow(self):
        css = source(STYLES)
        tablet_rules = css.split("@media (max-width: 1023px)", 1)[1].split(
            "@media (max-width: 760px)", 1
        )[0]
        self.assertIn(".footer__grid", tablet_rules)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr));", tablet_rules)
        self.assertIn(".footer__col--brand", tablet_rules)
        self.assertIn("grid-column: 1 / -1;", tablet_rules)

    def test_mobile_menu_offsets_match_the_compact_container_gutter(self):
        css = source(STYLES)
        compact_rules = css.split("@media (max-width: 760px)", 1)[1].split(
            "@media (max-width: 540px)", 1
        )[0]
        menu = re.search(r"\.nav__links\.is-enhanced\s*\{([^}]*)\}", compact_rules, re.S)
        self.assertIsNotNone(menu)
        self.assertIn("right: -1rem", menu.group(1))
        self.assertIn("left: -1rem", menu.group(1))
        self.assertIn("padding-right: 1rem", menu.group(1))
        self.assertIn("padding-left: 1rem", menu.group(1))


if __name__ == "__main__":
    unittest.main()
