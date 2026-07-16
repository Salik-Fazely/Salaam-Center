import math
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FAQ_PAGES = {
    Path("how-it-works/index.html"): 6,
    Path("pricing/index.html"): 9,
    Path("teachers/index.html"): 7,
}
BOOKING_ACTION = (
    "https://script.google.com/macros/s/"
    "AKfycbxdUb5dS1GDdlbJpjiFmBEW_aagYUlyYUhkEU068pkSYIrT24sw-RlGDmDTZJZ8X87DAA/exec"
)
CHOICE_VALUES = {
    "Current Qur’an level": (
        "radio",
        "quran_level",
        [
            "complete-beginner",
            "knows-arabic-letters",
            "reading-short-words",
            "reading-independently",
        ],
    ),
    "Preferred session language": (
        "radio",
        "session_language",
        ["english", "arabic", "turkish", "persian"],
    ),
    "Preferred days": (
        "checkbox",
        "preferred_days",
        ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
    ),
    "Preferred time of day": (
        "radio",
        "preferred_time",
        ["morning", "afternoon", "evening"],
    ),
}
EXPECTED_FORM_NAMES = {
    "source",
    "success_redirect",
    "website_field",
    "child_name",
    "child_age",
    "quran_level",
    "session_language",
    "parent_name",
    "country",
    "email",
    "whatsapp",
    "preferred_days",
    "preferred_time",
    "city_region",
    "notes",
    "consent",
}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.faq_triggers = []
        self.faq_panels = []
        self.form_action = None
        self.form_depth = 0
        self.form_controls = []
        self.choice_fieldsets = []
        self.current_fieldset = None
        self.in_legend = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set(attributes.get("class", "").split())

        if "faq-question" in classes:
            self.faq_triggers.append((tag, attributes))
        if "faq-answer" in classes:
            self.faq_panels.append((tag, attributes))

        if tag == "form" and attributes.get("id") == "trial-form":
            self.form_depth = 1
            self.form_action = attributes.get("action")
        elif self.form_depth and tag == "form":
            self.form_depth += 1

        if not self.form_depth:
            return

        if tag in {"input", "select", "textarea"}:
            self.form_controls.append((tag, attributes))

        if tag == "fieldset" and "choice-fieldset" in classes:
            self.current_fieldset = {
                "attrs": attributes,
                "legend": [],
                "inputs": [],
                "labels": [],
            }
            self.choice_fieldsets.append(self.current_fieldset)
        elif self.current_fieldset is not None:
            if tag == "legend":
                self.in_legend = True
            elif tag == "input":
                self.current_fieldset["inputs"].append(attributes)
            elif tag == "label" and attributes.get("for"):
                self.current_fieldset["labels"].append(attributes["for"])

    def handle_data(self, data):
        if self.current_fieldset is not None and self.in_legend:
            self.current_fieldset["legend"].append(data)

    def handle_endtag(self, tag):
        if tag == "legend":
            self.in_legend = False
        elif tag == "fieldset" and self.current_fieldset is not None:
            self.current_fieldset = None
        elif tag == "form" and self.form_depth:
            self.form_depth -= 1


def parse_page(path):
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def normalized_text(parts):
    return " ".join("".join(parts).split())


def rgb(hex_color):
    value = hex_color.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def composite(foreground, background, alpha):
    return tuple(
        foreground[index] * alpha + background[index] * (1 - alpha)
        for index in range(3)
    )


def luminance(color):
    channels = []
    for channel in color:
        value = channel / 255
        channels.append(
            value / 12.92
            if value <= 0.04045
            else math.pow((value + 0.055) / 1.055, 2.4)
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(foreground, background):
    lighter, darker = sorted(
        (luminance(foreground), luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def css_token(source, name):
    match = re.search(rf"--{re.escape(name)}:\s*([^;]+);", source)
    if not match:
        raise AssertionError(f"Missing CSS token --{name}")
    return match.group(1).strip()


def rgba_value(value):
    match = re.fullmatch(
        r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)",
        value,
    )
    if not match:
        raise AssertionError(f"Expected rgba() value, got {value}")
    return tuple(map(int, match.groups()[:3])), float(match.group(4))


class AccordionStaticTests(unittest.TestCase):
    def test_every_canonical_faq_has_connected_native_disclosures(self):
        all_ids = []

        for relative, expected_count in FAQ_PAGES.items():
            parser = parse_page(ROOT / relative)
            self.assertEqual(expected_count, len(parser.faq_triggers), relative)
            self.assertEqual(expected_count, len(parser.faq_panels), relative)

            panels = {
                attributes.get("id"): attributes
                for _, attributes in parser.faq_panels
                if attributes.get("id")
            }
            self.assertEqual(expected_count, len(panels), relative)

            for tag, attributes in parser.faq_triggers:
                self.assertEqual("button", tag, relative)
                self.assertEqual("button", attributes.get("type"), relative)
                self.assertEqual("false", attributes.get("aria-expanded"), relative)
                panel_id = attributes.get("aria-controls")
                self.assertIn(panel_id, panels, relative)
                all_ids.append(panel_id)

                panel = panels[panel_id]
                self.assertIn("hidden", panel, relative)
                self.assertNotIn("aria-hidden", panel, relative)
                self.assertNotIn("inert", panel, relative)
                self.assertNotIn("style", panel, relative)

        self.assertEqual(len(all_ids), len(set(all_ids)))


class BookingChoiceStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "book-trial/index.html"
        cls.source = cls.path.read_text(encoding="utf-8")
        cls.parser = parse_page(cls.path)

    def test_booking_action_and_field_name_contract_are_unchanged(self):
        self.assertEqual(BOOKING_ACTION, self.parser.form_action)
        names = {
            attributes["name"]
            for _, attributes in self.parser.form_controls
            if attributes.get("name")
        }
        self.assertEqual(EXPECTED_FORM_NAMES, names)

    def test_choice_groups_use_fieldsets_legends_and_native_controls(self):
        groups = {
            normalized_text(group["legend"]): group
            for group in self.parser.choice_fieldsets
        }
        self.assertEqual(set(CHOICE_VALUES), set(groups))

        control_ids = []
        for legend, (control_type, name, values) in CHOICE_VALUES.items():
            group = groups[legend]
            inputs = group["inputs"]
            self.assertEqual(values, [control.get("value") for control in inputs], legend)
            self.assertTrue(inputs, legend)
            self.assertTrue(all(control.get("type") == control_type for control in inputs), legend)
            self.assertTrue(all(control.get("name") == name for control in inputs), legend)

            ids = [control.get("id") for control in inputs]
            self.assertTrue(all(ids), legend)
            self.assertEqual(ids, group["labels"], legend)
            control_ids.extend(ids)

            if control_type == "radio":
                self.assertTrue(all("required" in control for control in inputs), legend)
            else:
                self.assertEqual("true", group["attrs"].get("data-required"), legend)
                self.assertEqual(
                    "preferred-days-requirement",
                    group["attrs"].get("aria-describedby"),
                    legend,
                )

        self.assertEqual(len(control_ids), len(set(control_ids)))
        self.assertNotIn('role="radio"', self.source)
        self.assertNotIn('role="checkbox"', self.source)
        self.assertNotIn("aria-checked", self.source)
        self.assertNotRegex(self.source, r'<button[^>]+class="chip"')
        self.assertIn('id="preferred-days-requirement"', self.source)
        self.assertIn("Choose at least one preferred day.", self.source)
        self.assertIn("setCustomValidity", self.source)

    def test_preferred_days_are_collapsed_to_the_existing_comma_separated_payload(self):
        self.assertIn("function normalizePreferredDaysPayload(formData, form)", self.source)
        self.assertIn("formData.delete('preferred_days');", self.source)
        self.assertIn("formData.append('preferred_days', selectedDays.join(','));", self.source)


class FocusContrastAndMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "assets/css/styles.css").read_text(encoding="utf-8")

    def test_muted_text_tokens_meet_normal_text_contrast(self):
        foreground, alpha = rgba_value(css_token(self.source, "muted"))
        paper = rgb(css_token(self.source, "paper"))
        ivory = rgb(css_token(self.source, "ivory"))
        self.assertGreaterEqual(contrast(composite(foreground, paper, alpha), paper), 4.5)
        self.assertGreaterEqual(contrast(composite(foreground, ivory, alpha), ivory), 4.5)

        dark_foreground, dark_alpha = rgba_value(css_token(self.source, "on-dark-muted"))
        ink = rgb(css_token(self.source, "ink"))
        self.assertGreaterEqual(
            contrast(composite(dark_foreground, ink, dark_alpha), ink), 4.5
        )
        footer_copy = re.search(r"\.footer__copy\s*\{(?P<body>[^}]+)\}", self.source)
        self.assertIsNotNone(footer_copy)
        self.assertIn("color: var(--on-dark-muted);", footer_copy.group("body"))

    def test_control_boundaries_and_focus_indicator_meet_three_to_one(self):
        border_foreground, border_alpha = rgba_value(css_token(self.source, "control-border"))
        focus = rgb(css_token(self.source, "bronze-2"))
        backgrounds = [
            rgb(css_token(self.source, name))
            for name in ("paper", "ivory", "forest", "ink")
        ]
        paper = backgrounds[0]

        self.assertGreaterEqual(
            contrast(composite(border_foreground, paper, border_alpha), paper), 3
        )
        for background in backgrounds:
            self.assertGreaterEqual(contrast(focus, background), 3)

        self.assertNotRegex(self.source, r"outline\s*:\s*(?:none|0)\b")
        self.assertRegex(
            self.source,
            r":focus-visible\s*\{[^}]*outline:\s*3px solid var\(--bronze-2\);",
        )
        self.assertRegex(
            self.source,
            r"\.chip-control:focus-visible\s*\+\s*\.chip\s*\{[^}]*outline:",
        )

    def test_selected_booking_choices_have_a_non_color_indicator(self):
        self.assertIn(".chip-control:checked + .chip", self.source)
        self.assertRegex(
            self.source,
            r"\.chip-control\[type=['\"]checkbox['\"]\]:checked\s*\+\s*\.chip::before\s*\{[^}]*content:",
        )
        self.assertRegex(
            self.source,
            r"\.chip-control\[type=['\"]radio['\"]\]:checked\s*\+\s*\.chip::before\s*\{[^}]*box-shadow:",
        )

    def test_reduced_motion_forces_immediate_static_visibility(self):
        marker = "@media (prefers-reduced-motion: reduce)"
        self.assertIn(marker, self.source)
        reduced = self.source[self.source.index(marker) :]
        self.assertRegex(reduced, r"html\s*\{[^}]*scroll-behavior:\s*auto;")
        self.assertRegex(
            reduced,
            r"\.reveal-section,\s*\.reveal-card\s*\{[^}]*opacity:\s*1;[^}]*transform:\s*none;[^}]*transition:\s*none;",
        )
        self.assertRegex(reduced, r"body\.is-leaving\s*\{[^}]*opacity:\s*1;")
        self.assertIn("@media (prefers-reduced-motion: no-preference)", self.source)


if __name__ == "__main__":
    unittest.main()
